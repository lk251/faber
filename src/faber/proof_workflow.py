"""Two-phase execution of advisory proof plans through owner-approved capabilities."""

from __future__ import annotations

import hashlib
import math
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

from faber.attempts import Attempt
from faber.canonical_json import canonical_json_bytes
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_catalog import (
    ArtifactValidatorCapability,
    FileInvariantCapability,
    ProofCapabilityPolicy,
    ProofCatalog,
    ProofCatalogEntry,
)
from faber.proof_executors import (
    EXECUTION_ERROR_CODES,
    ProcessCapture,
    ProofExecutionResult,
    execute_catalog_entry,
    launch_bounded_process,
    preflight_catalog_execution,
    resolve_catalog_path,
)
from faber.proofs import (
    ProofDecision,
    ProofEvidence,
    ProofPlan,
    ProofPolicy,
    ProofTemplateSelection,
    decide_proof,
    proof_authority_binding_digest,
)
from faber.receipts import VerificationReceipt
from faber.runner.local import LocalVerifierRunner, RunnerPolicy
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_sequence,
)
from faber.verifiers import VerifierRegistry, VerifierRun

PROOF_EXECUTION_POLICY_SCHEMA = "faber.proof_execution_policy.v1"
PROOF_WORKFLOW_RESULT_SCHEMA = "faber.proof_workflow_result.v1"
WORKSPACE_SNAPSHOT_SCHEMA = "faber.proof_workspace_snapshot.v1"
LOCAL_ISOLATION_DISCLOSURE = (
    "development-local-runner; no operating-system, container, or network isolation"
)
MAX_POLICY_OBLIGATIONS = 256
MAX_POLICY_PER_OBLIGATION_SECONDS = 300
MAX_POLICY_TIMEOUT_SECONDS = 3_600
MAX_POLICY_IO_BYTES = 1_048_576
MAX_WORKSPACE_FILES = 100_000
MAX_WORKSPACE_FILE_BYTES = 67_108_864
MAX_WORKSPACE_TOTAL_BYTES = 536_870_912
WORKSPACE_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".direnv",
        ".faber",
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "htmlcov",
    }
)
WORKSPACE_EXCLUDED_FILES = frozenset({".coverage", "coverage.xml"})

ProcessLauncher = Callable[..., ProcessCapture]

_WORKFLOW_REASON_CODES = frozenset(
    set(EXECUTION_ERROR_CODES)
    | {
        "capability_preflight_failed",
        "input_limit_exceeded",
        "output_limit_exceeded",
        "timeout_limit_exceeded",
        "total_timeout_limit_exceeded",
        "authoritative_run_reused",
        "workspace_changed_during_execution",
        "workspace_mismatch",
    }
)


class ProofWorkflowError(ValidationError):
    """Stable fail-closed error raised before any proof capability is executed."""

    def __init__(self, code: str, public_message: str) -> None:
        self.code = require_non_empty_string(code, "code")
        self.public_message = require_non_empty_string(public_message, "public_message")
        super().__init__(f"{self.code}: {self.public_message}")

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "public_message": self.public_message}


def _positive_int(value: object, field: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field} must be a positive integer")
    if value > maximum:
        raise ValidationError(f"{field} exceeds its supported maximum")
    return value


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def _environment_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError("allowed_environment_variables must be a sequence")
    names: list[str] = []
    for index, item in enumerate(value):
        name = require_non_empty_string(item, f"allowed_environment_variables[{index}]")
        if "=" in name or "\x00" in name or any(character.isspace() for character in name):
            raise ValidationError("environment allowlist entries must be plain variable names")
        names.append(name)
    if len({name.casefold() for name in names}) != len(names):
        raise ValidationError(
            "allowed_environment_variables must not contain case-insensitive duplicates"
        )
    return tuple(sorted(names))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _workspace_root_entry_excluded(name: str) -> bool:
    return name == "result" or name.startswith("result-")


def _workspace_file_record(path: Path, relative_path: str, root: Path) -> dict[str, object]:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValidationError("workspace file is unavailable") from None
    if not _is_within(resolved, root) or path.is_symlink() or not resolved.is_file():
        raise ValidationError("workspace snapshots require regular in-root files")
    hasher = hashlib.sha256()
    size = 0
    try:
        with resolved.open("rb") as stream:
            before = os.fstat(stream.fileno())
            while chunk := stream.read(1_048_576):
                size += len(chunk)
                if size > MAX_WORKSPACE_FILE_BYTES:
                    raise ValidationError("workspace file exceeds the snapshot byte limit")
                hasher.update(chunk)
            after = os.fstat(stream.fileno())
    except OSError:
        raise ValidationError("workspace file could not be read") from None
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ValidationError("workspace changed while it was being snapshotted")
    return {
        "path": relative_path,
        "size_bytes": size,
        "digest": f"sha256:{hasher.hexdigest()}",
    }


def workspace_snapshot_digest(repository_root: str | Path) -> str:
    """Digest the executable repository state, excluding declared local build state."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValidationError("workspace root is unavailable") from None
    if not root.is_dir():
        raise ValidationError("workspace root must be a directory")
    records: list[dict[str, object]] = []
    casefolded_paths: set[str] = set()
    total_bytes = 0
    pending: list[tuple[Path, tuple[str, ...]]] = [(root, ())]
    while pending:
        directory, relative_parts = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(
                    iterator,
                    key=lambda item: (item.name.casefold(), item.name),
                )
        except OSError:
            raise ValidationError("workspace directory could not be read") from None
        for entry in entries:
            if not relative_parts and _workspace_root_entry_excluded(entry.name):
                continue
            if entry.name in WORKSPACE_EXCLUDED_DIRECTORIES:
                continue
            child_parts = (*relative_parts, entry.name)
            relative_path = "/".join(child_parts)
            try:
                relative_size = len(relative_path.encode("utf-8"))
            except UnicodeEncodeError:
                raise ValidationError("workspace path is not valid UTF-8") from None
            if relative_size > 2_048 or relative_path.casefold() in casefolded_paths:
                raise ValidationError("workspace paths are invalid or case-colliding")
            casefolded_paths.add(relative_path.casefold())
            if entry.is_symlink():
                raise ValidationError("workspace snapshots do not follow symbolic links")
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                raise ValidationError("workspace entry is unavailable") from None
            if is_directory:
                pending.append((Path(entry.path), child_parts))
                continue
            if not is_file:
                raise ValidationError("workspace contains an unsupported filesystem entry")
            if entry.name in WORKSPACE_EXCLUDED_FILES:
                continue
            record = _workspace_file_record(Path(entry.path), relative_path, root)
            record_size = record["size_bytes"]
            if not isinstance(record_size, int):
                raise AssertionError("workspace record size must be an integer")
            total_bytes += record_size
            if len(records) >= MAX_WORKSPACE_FILES or total_bytes > MAX_WORKSPACE_TOTAL_BYTES:
                raise ValidationError("workspace snapshot exceeds its bounded size")
            records.append(record)
    records.sort(key=lambda item: str(item["path"]))
    return sha256_digest(
        {
            "schema": WORKSPACE_SNAPSHOT_SCHEMA,
            "excluded_directories": sorted(WORKSPACE_EXCLUDED_DIRECTORIES),
            "excluded_files": sorted(WORKSPACE_EXCLUDED_FILES),
            "excluded_root_outputs": ["result", "result-*"],
            "files": records,
        }
    )


@dataclass(frozen=True)
class ProofExecutionPolicy:
    """Repository-owner policy for one bounded local proof workflow."""

    allowed_repository_root: str
    allowed_catalog_digest: str
    verifier_registry_digest: str
    expected_attempt_digest: str
    expected_workspace_digest: str
    maximum_obligations: int = 32
    per_obligation_timeout_seconds: int = 30
    total_timeout_seconds: int = 120
    max_input_bytes: int = 65_536
    max_output_bytes: int = 64_000
    allowed_environment_variables: Sequence[str] = ()
    allow_shell: bool = False
    reject_symlink_escape: bool = True
    isolation_disclosure: str = LOCAL_ISOLATION_DISCLOSURE
    authoritative_receipts_required: bool = True
    schema: str = PROOF_EXECUTION_POLICY_SCHEMA

    def __post_init__(self) -> None:
        require_schema(self.schema, PROOF_EXECUTION_POLICY_SCHEMA)
        root_text = require_non_empty_string(
            self.allowed_repository_root,
            "allowed_repository_root",
        )
        try:
            root = Path(root_text).resolve(strict=True)
        except OSError as exc:
            raise ValidationError("allowed_repository_root must exist") from exc
        if not root.is_dir():
            raise ValidationError("allowed_repository_root must be a directory")
        object.__setattr__(self, "allowed_repository_root", str(root))
        require_digest(self.allowed_catalog_digest, "allowed_catalog_digest")
        require_digest(self.verifier_registry_digest, "verifier_registry_digest")
        require_digest(self.expected_attempt_digest, "expected_attempt_digest")
        require_digest(self.expected_workspace_digest, "expected_workspace_digest")
        _positive_int(
            self.maximum_obligations,
            "maximum_obligations",
            maximum=MAX_POLICY_OBLIGATIONS,
        )
        _positive_int(
            self.per_obligation_timeout_seconds,
            "per_obligation_timeout_seconds",
            maximum=MAX_POLICY_PER_OBLIGATION_SECONDS,
        )
        _positive_int(
            self.total_timeout_seconds,
            "total_timeout_seconds",
            maximum=MAX_POLICY_TIMEOUT_SECONDS,
        )
        for field_name in ("max_input_bytes", "max_output_bytes"):
            _positive_int(
                getattr(self, field_name),
                field_name,
                maximum=MAX_POLICY_IO_BYTES,
            )
        object.__setattr__(
            self,
            "allowed_environment_variables",
            _environment_names(self.allowed_environment_variables),
        )
        _bool(self.allow_shell, "allow_shell")
        if self.allow_shell:
            raise ValidationError("shell execution is disabled for proof workflows")
        _bool(self.reject_symlink_escape, "reject_symlink_escape")
        if not self.reject_symlink_escape:
            raise ValidationError("proof workflows must reject symlink escape")
        require_non_empty_string(self.isolation_disclosure, "isolation_disclosure")
        if self.isolation_disclosure != LOCAL_ISOLATION_DISCLOSURE:
            raise ValidationError("local proof workflows must use the honest isolation disclosure")
        _bool(self.authoritative_receipts_required, "authoritative_receipts_required")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "allowed_repository_root": self.allowed_repository_root,
            "allowed_catalog_digest": self.allowed_catalog_digest,
            "verifier_registry_digest": self.verifier_registry_digest,
            "expected_attempt_digest": self.expected_attempt_digest,
            "expected_workspace_digest": self.expected_workspace_digest,
            "maximum_obligations": self.maximum_obligations,
            "per_obligation_timeout_seconds": self.per_obligation_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "max_input_bytes": self.max_input_bytes,
            "max_output_bytes": self.max_output_bytes,
            "allowed_environment_variables": list(self.allowed_environment_variables),
            "allow_shell": self.allow_shell,
            "reject_symlink_escape": self.reject_symlink_escape,
            "isolation_disclosure": self.isolation_disclosure,
            "authoritative_receipts_required": self.authoritative_receipts_required,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    def authority_digest(self) -> str:
        """Bind proof authority to policy semantics rather than a host-local path."""

        payload = self.to_dict()
        del payload["allowed_repository_root"]
        return sha256_digest(
            {
                "schema": "faber.proof_execution_authority_policy.v1",
                **payload,
            }
        )

    def portable_dict(self) -> dict[str, object]:
        """Serialize the selected repository root without a machine-specific path."""

        payload = self.to_dict()
        payload["allowed_repository_root"] = "."
        return payload


def _frozen_diagnostics(
    value: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    result: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or any(not isinstance(key, str) for key in item):
            raise ValidationError(f"diagnostics[{index}] must be a string-key mapping")
        detached = _freeze_diagnostic_value(dict(item), f"diagnostics[{index}]", depth=0)
        if not isinstance(detached, Mapping):
            raise AssertionError("a frozen diagnostic record must remain a mapping")
        if len(canonical_json_bytes(detached)) > 4_096:
            raise ValidationError(f"diagnostics[{index}] exceeds the byte limit")
        result.append(detached)
    return tuple(result)


def _freeze_diagnostic_value(value: object, field: str, *, depth: int) -> object:
    if depth > 12:
        raise ValidationError(f"{field} exceeds the nesting limit")
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValidationError(f"{field} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        if len(value) > 256 or any(type(key) is not str for key in value):
            raise ValidationError(f"{field} must be a bounded string-key mapping")
        return MappingProxyType(
            {
                str(key): _freeze_diagnostic_value(
                    item,
                    f"{field}.{key}",
                    depth=depth + 1,
                )
                for key, item in sorted(value.items())
            }
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        if len(value) > 256:
            raise ValidationError(f"{field} contains too many items")
        return tuple(
            _freeze_diagnostic_value(
                item,
                f"{field}[{index}]",
                depth=depth + 1,
            )
            for index, item in enumerate(value)
        )
    raise ValidationError(f"{field} must contain only bounded JSON data")


def _thaw_diagnostic_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_diagnostic_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_diagnostic_value(item) for item in value]
    return value


@dataclass(frozen=True)
class ProofWorkflowResult:
    """Replayable proof records and deterministic aggregate decision."""

    plan: ProofPlan
    catalog_digest: str
    verifier_registry_digest: str
    proof_policy_digest: str
    execution_policy_digest: str
    workspace_digest: str
    evidence: Sequence[ProofEvidence]
    verifier_runs: Sequence[VerifierRun]
    verification_receipts: Sequence[VerificationReceipt]
    decision: ProofDecision
    execution_order: Sequence[str]
    timings: Mapping[str, float]
    diagnostics: Sequence[Mapping[str, object]]
    short_circuited: bool
    schema: str = PROOF_WORKFLOW_RESULT_SCHEMA

    def __post_init__(self) -> None:
        require_schema(self.schema, PROOF_WORKFLOW_RESULT_SCHEMA)
        if not isinstance(self.plan, ProofPlan):
            raise ValidationError("plan must be ProofPlan")
        for field_name in (
            "catalog_digest",
            "verifier_registry_digest",
            "proof_policy_digest",
            "execution_policy_digest",
            "workspace_digest",
        ):
            require_digest(getattr(self, field_name), field_name)
        if self.catalog_digest != self.plan.proof_catalog_digest:
            raise ValidationError("catalog_digest must match the proof plan")
        evidence = tuple(self.evidence)
        runs = tuple(self.verifier_runs)
        receipts = tuple(self.verification_receipts)
        if any(not isinstance(item, ProofEvidence) for item in evidence):
            raise ValidationError("evidence must contain only ProofEvidence records")
        if any(not isinstance(item, VerifierRun) for item in runs):
            raise ValidationError("verifier_runs must contain only VerifierRun records")
        if any(not isinstance(item, VerificationReceipt) for item in receipts):
            raise ValidationError(
                "verification_receipts must contain only VerificationReceipt records"
            )
        if not isinstance(self.decision, ProofDecision):
            raise ValidationError("decision must be ProofDecision")
        plan_digest = self.plan.digest()
        if self.decision.proof_plan_digest != plan_digest:
            raise ValidationError("decision must bind the supplied proof plan")
        if any(item.proof_plan_digest != plan_digest for item in evidence):
            raise ValidationError("every evidence record must bind the supplied proof plan")
        if tuple(self.decision.evidence_digests) != tuple(
            sorted({item.digest() for item in evidence})
        ):
            raise ValidationError("decision must bind exactly the supplied evidence")
        run_digests = {item.digest() for item in runs}
        receipt_digests = {item.digest() for item in receipts}
        if len({item.id for item in runs}) != len(runs) or len(run_digests) != len(runs):
            raise ValidationError("verifier_runs must not reuse authority records")
        if len({item.id for item in receipts}) != len(receipts) or len(receipt_digests) != len(
            receipts
        ):
            raise ValidationError("verification_receipts must not reuse authority records")
        if any(
            item.verifier_run_digest is not None and item.verifier_run_digest not in run_digests
            for item in evidence
        ):
            raise ValidationError("evidence references an unavailable verifier run")
        if any(
            item.verification_receipt_digest is not None
            and item.verification_receipt_digest not in receipt_digests
            for item in evidence
        ):
            raise ValidationError("evidence references an unavailable verification receipt")
        if not set(self.decision.authoritative_receipt_digests) <= receipt_digests:
            raise ValidationError("decision references an unavailable verification receipt")
        execution_order = tuple(self.execution_order)
        for index, digest in enumerate(execution_order):
            require_digest(digest, f"execution_order[{index}]")
        if len(execution_order) != len(evidence):
            raise ValidationError("execution_order must contain one entry per evidence record")
        if execution_order != tuple(item.selection_digest for item in evidence):
            raise ValidationError("execution_order must match evidence selection order")
        timing_values: dict[str, float] = {}
        for key, value in self.timings.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError("timings must use non-empty string keys")
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValidationError("timings values must be finite non-negative numbers")
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValidationError("timings values must be finite non-negative numbers")
            timing_values[key] = number
        _bool(self.short_circuited, "short_circuited")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "verifier_runs", runs)
        object.__setattr__(self, "verification_receipts", receipts)
        object.__setattr__(self, "execution_order", execution_order)
        object.__setattr__(self, "timings", MappingProxyType(timing_values))
        object.__setattr__(self, "diagnostics", _frozen_diagnostics(self.diagnostics))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "plan": self.plan.to_dict(),
            "catalog_digest": self.catalog_digest,
            "verifier_registry_digest": self.verifier_registry_digest,
            "proof_policy_digest": self.proof_policy_digest,
            "execution_policy_digest": self.execution_policy_digest,
            "workspace_digest": self.workspace_digest,
            "evidence": [item.to_dict() for item in self.evidence],
            "verifier_runs": [item.to_dict() for item in self.verifier_runs],
            "verification_receipts": [item.to_dict() for item in self.verification_receipts],
            "decision": self.decision.to_dict(),
            "execution_order": list(self.execution_order),
            "timings": dict(self.timings),
            "diagnostics": [_thaw_diagnostic_value(item) for item in self.diagnostics],
            "short_circuited": self.short_circuited,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofWorkflowResult:
        fields = {
            "schema",
            "plan",
            "catalog_digest",
            "verifier_registry_digest",
            "proof_policy_digest",
            "execution_policy_digest",
            "workspace_digest",
            "evidence",
            "verifier_runs",
            "verification_receipts",
            "decision",
            "execution_order",
            "timings",
            "diagnostics",
            "short_circuited",
        }
        if set(payload) != fields:
            raise ValidationError("ProofWorkflowResult must use the exact supported field set")
        plan = ProofPlan.from_dict(require_mapping(payload.get("plan"), "plan"))
        decision = ProofDecision.from_dict(require_mapping(payload.get("decision"), "decision"))
        evidence = [
            ProofEvidence.from_dict(require_mapping(item, f"evidence[{index}]"))
            for index, item in enumerate(require_sequence(payload.get("evidence"), "evidence"))
        ]
        verifier_runs = [
            VerifierRun.from_dict(require_mapping(item, f"verifier_runs[{index}]"))
            for index, item in enumerate(
                require_sequence(payload.get("verifier_runs"), "verifier_runs")
            )
        ]
        receipts = [
            VerificationReceipt.from_dict(require_mapping(item, f"verification_receipts[{index}]"))
            for index, item in enumerate(
                require_sequence(
                    payload.get("verification_receipts"),
                    "verification_receipts",
                )
            )
        ]
        timings: dict[str, float] = {}
        for key, value in require_mapping(payload.get("timings"), "timings").items():
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValidationError("timings values must be finite non-negative numbers")
            timings[key] = float(value)
        diagnostics = [
            dict(require_mapping(item, f"diagnostics[{index}]"))
            for index, item in enumerate(
                require_sequence(payload.get("diagnostics"), "diagnostics")
            )
        ]
        short_circuited = payload.get("short_circuited")
        if not isinstance(short_circuited, bool):
            raise ValidationError("short_circuited must be a boolean")
        result = cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            plan=plan,
            catalog_digest=require_digest(payload.get("catalog_digest"), "catalog_digest"),
            verifier_registry_digest=require_digest(
                payload.get("verifier_registry_digest"),
                "verifier_registry_digest",
            ),
            proof_policy_digest=require_digest(
                payload.get("proof_policy_digest"), "proof_policy_digest"
            ),
            execution_policy_digest=require_digest(
                payload.get("execution_policy_digest"),
                "execution_policy_digest",
            ),
            workspace_digest=require_digest(payload.get("workspace_digest"), "workspace_digest"),
            evidence=evidence,
            verifier_runs=verifier_runs,
            verification_receipts=receipts,
            decision=decision,
            execution_order=[
                require_digest(item, f"execution_order[{index}]")
                for index, item in enumerate(
                    require_sequence(payload.get("execution_order"), "execution_order")
                )
            ],
            timings=timings,
            diagnostics=diagnostics,
            short_circuited=short_circuited,
        )
        if result.to_dict() != dict(payload):
            raise ValidationError("ProofWorkflowResult fields do not round-trip exactly")
        return result


@dataclass(frozen=True)
class _PreparedSelection:
    selection: ProofTemplateSelection
    entry: ProofCatalogEntry
    parameters: Mapping[str, object]


def _fail(code: str, message: str) -> None:
    raise ProofWorkflowError(code, message)


def _safe_exception_code(exc: Exception, fallback: str) -> str:
    value = getattr(exc, "code", None)
    return value if isinstance(value, str) and value in _WORKFLOW_REASON_CODES else fallback


def _entry_policy(entry: ProofCatalogEntry) -> ProofCapabilityPolicy:
    capability = entry.capability
    policy = capability.policy
    if not isinstance(policy, ProofCapabilityPolicy):
        _fail("missing_capability", "catalog capability has no execution policy")
    return policy


def _bind_parameters(
    entry: ProofCatalogEntry,
    parameters: Mapping[str, object],
) -> Mapping[str, object]:
    try:
        bound = entry.bind_parameters(parameters)
    except ValidationError as exc:
        raise ProofWorkflowError("invalid_parameters", "selection parameters are invalid") from exc
    if not isinstance(bound, Mapping):
        _fail("invalid_parameters", "catalog parameter binding did not return an object")
    return MappingProxyType(dict(bound))


def _preflight_workflow(
    *,
    task_contract: TaskContract,
    attempt: Attempt,
    plan: ProofPlan,
    catalog: ProofCatalog,
    verifier_registry: VerifierRegistry,
    proof_policy: ProofPolicy,
    execution_policy: ProofExecutionPolicy,
) -> tuple[_PreparedSelection, ...]:
    if not isinstance(task_contract, TaskContract):
        _fail("invalid_context", "task_contract must be a validated TaskContract")
    if not isinstance(attempt, Attempt):
        _fail("invalid_context", "attempt must be a validated Attempt")
    if not isinstance(plan, ProofPlan):
        _fail("invalid_context", "plan must be a validated ProofPlan")
    if not isinstance(catalog, ProofCatalog):
        _fail("invalid_catalog", "catalog must be a validated ProofCatalog")
    if not isinstance(verifier_registry, VerifierRegistry):
        _fail("invalid_registry", "verifier_registry must be VerifierRegistry")
    if not isinstance(proof_policy, ProofPolicy):
        _fail("invalid_policy", "proof_policy must be a validated ProofPolicy")
    if not isinstance(execution_policy, ProofExecutionPolicy):
        _fail("invalid_policy", "execution_policy must be ProofExecutionPolicy")

    if (
        task_contract.id != plan.task_contract_id
        or task_contract.digest() != plan.task_contract_digest
    ):
        _fail("task_binding_mismatch", "proof plan does not bind the task contract")
    if (
        attempt.id != plan.attempt_id
        or attempt.digest() != plan.attempt_digest
        or attempt.task_contract_id != task_contract.id
        or attempt.base_revision != plan.base_revision
        or attempt.candidate_revision != plan.candidate_revision
        or attempt.patch_digest != plan.diff_digest
    ):
        _fail("attempt_binding_mismatch", "proof plan does not bind the attempt and patch")
    if execution_policy.expected_attempt_digest != attempt.digest():
        _fail("attempt_binding_mismatch", "execution policy does not bind the exact attempt")
    try:
        actual_workspace_digest = workspace_snapshot_digest(
            execution_policy.allowed_repository_root
        )
    except ValidationError as exc:
        raise ProofWorkflowError(
            "workspace_mismatch",
            "repository workspace could not be bound safely",
        ) from exc
    if actual_workspace_digest != execution_policy.expected_workspace_digest:
        _fail("workspace_mismatch", "repository workspace does not match execution policy")

    catalog_digest = catalog.digest()
    if (
        plan.proof_catalog_digest != catalog_digest
        or execution_policy.allowed_catalog_digest != catalog_digest
    ):
        _fail("catalog_mismatch", "proof catalog commitment does not match the plan and policy")
    registry_digest = verifier_registry.digest()
    if execution_policy.verifier_registry_digest != registry_digest:
        _fail("registry_mismatch", "verifier registry commitment does not match policy")
    if len(plan.selections) > execution_policy.maximum_obligations:
        _fail("obligation_limit_exceeded", "proof plan exceeds the obligation limit")

    claim_ids = {claim.id for claim in plan.claims}
    selected_template_ids = {selection.template_id for selection in plan.selections}
    if set(proof_policy.mandatory_claim_ids) - claim_ids:
        _fail("mandatory_obligation_missing", "proof plan omits a mandatory claim")
    if set(proof_policy.mandatory_template_ids) - selected_template_ids:
        _fail("mandatory_obligation_missing", "proof plan omits a mandatory template")
    if set(proof_policy.mandatory_claim_ids) - set(plan.mandatory_claim_ids):
        _fail("mandatory_obligation_weakened", "proof plan weakens mandatory claims")
    if set(proof_policy.mandatory_template_ids) - set(plan.mandatory_template_ids):
        _fail("mandatory_obligation_weakened", "proof plan weakens mandatory templates")

    prepared: list[_PreparedSelection] = []
    for selection in plan.selections:
        try:
            entry = catalog.resolve(selection.template_id, selection.template_version)
        except (KeyError, ValidationError) as exc:
            raise ProofWorkflowError(
                "missing_capability",
                "selection does not resolve to an exact active catalog entry",
            ) from exc
        bound_parameters = _bind_parameters(entry, selection.parameters)
        if len(canonical_json_bytes(dict(bound_parameters))) > execution_policy.max_input_bytes:
            _fail("input_limit_exceeded", "selection input exceeds execution policy")
        capability_policy = _entry_policy(entry)
        verifier_id = capability_policy.verifier_id
        timeout_seconds = capability_policy.timeout_seconds
        max_output_bytes = capability_policy.max_output_bytes
        environment_variables = capability_policy.environment_variables
        if verifier_id not in proof_policy.approved_verifier_ids:
            _fail("verifier_not_approved", "catalog verifier is not approved by proof policy")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or timeout_seconds > execution_policy.per_obligation_timeout_seconds
        ):
            _fail("timeout_limit_exceeded", "catalog capability exceeds the timeout policy")
        if (
            isinstance(max_output_bytes, bool)
            or not isinstance(max_output_bytes, int)
            or max_output_bytes > execution_policy.max_output_bytes
        ):
            _fail("output_limit_exceeded", "catalog capability exceeds the output policy")
        if not isinstance(environment_variables, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in environment_variables.items()
        ):
            _fail("invalid_environment_policy", "catalog environment policy is malformed")
        if set(environment_variables) - set(execution_policy.allowed_environment_variables):
            _fail("environment_not_allowed", "catalog environment exceeds the allowlist")
        try:
            fully_preflighted = preflight_catalog_execution(
                entry,
                bound_parameters,
                repository_root=execution_policy.allowed_repository_root,
                verifier_registry=verifier_registry,
                allowed_environment_variables=execution_policy.allowed_environment_variables,
                max_input_bytes=execution_policy.max_input_bytes,
            )
            capability = entry.capability
            content_path: str | None = None
            if isinstance(capability, ArtifactValidatorCapability):
                content_path = capability.repository_path
            elif isinstance(capability, FileInvariantCapability) and capability.operation not in {
                "exists",
                "absent",
            }:
                content_path = capability.repository_path
            if content_path is not None:
                artifact_path = resolve_catalog_path(
                    execution_policy.allowed_repository_root,
                    content_path,
                    must_exist=False,
                    require_file=True,
                )
                if (
                    artifact_path.exists()
                    and artifact_path.stat().st_size > execution_policy.max_input_bytes
                ):
                    _fail("input_limit_exceeded", "catalog artifact exceeds input policy")
        except Exception as exc:
            code = _safe_exception_code(exc, "capability_preflight_failed")
            raise ProofWorkflowError(code, "catalog capability failed preflight") from exc
        prepared.append(
            _PreparedSelection(
                selection=selection,
                entry=entry,
                parameters=MappingProxyType(dict(fully_preflighted)),
            )
        )
    if (
        sum(item.entry.capability.policy.timeout_seconds for item in prepared)
        > execution_policy.total_timeout_seconds
    ):
        _fail("total_timeout_limit_exceeded", "catalog obligations exceed total timeout policy")
    return tuple(prepared)


def _counterexample(
    *,
    parameters: Mapping[str, object],
    expected_summary: object,
    observed_summary: object,
    reason_code: str,
    exception_type: str | None = None,
) -> dict[str, object]:
    return {
        "input_summary": {"parameters_digest": sha256_digest(dict(parameters))},
        "expected_summary": expected_summary,
        "observed_summary": observed_summary,
        "exception_type": exception_type,
        "reason_code": reason_code,
    }


def _workspace_matches_execution_policy(execution_policy: ProofExecutionPolicy) -> bool:
    try:
        return (
            workspace_snapshot_digest(execution_policy.allowed_repository_root)
            == execution_policy.expected_workspace_digest
        )
    except ValidationError:
        return False


def _proof_invocation_context_digest(
    *,
    task_contract: TaskContract,
    attempt: Attempt,
    plan: ProofPlan,
    prepared: _PreparedSelection,
    verifier_registry: VerifierRegistry,
    proof_policy: ProofPolicy,
    execution_policy: ProofExecutionPolicy,
) -> str:
    """Bind a raw verifier call to the complete validated workflow context."""

    policy = _entry_policy(prepared.entry)
    return sha256_digest(
        {
            "schema": "faber.proof_invocation_context.v1",
            "task_contract_id": task_contract.id,
            "task_contract_digest": task_contract.digest(),
            "attempt_id": attempt.id,
            "attempt_digest": attempt.digest(),
            "base_revision": attempt.base_revision,
            "candidate_revision": attempt.candidate_revision,
            "patch_digest": attempt.patch_digest,
            "proof_plan_digest": plan.digest(),
            "selection_digest": prepared.selection.digest(),
            "parameters_digest": sha256_digest(dict(prepared.parameters)),
            "proof_catalog_digest": plan.proof_catalog_digest,
            "catalog_entry_id": prepared.entry.id,
            "catalog_entry_version": prepared.entry.version,
            "family": prepared.entry.family,
            "capability_digest": prepared.entry.capability_digest(),
            "verifier_id": policy.verifier_id,
            "verifier_version": policy.verifier_version,
            "verifier_registry_digest": verifier_registry.digest(),
            "proof_policy_digest": proof_policy.digest(),
            "execution_policy_digest": execution_policy.authority_digest(),
            "workspace_digest": execution_policy.expected_workspace_digest,
        }
    )


def _not_executed_evidence(
    plan: ProofPlan,
    prepared: _PreparedSelection,
    *,
    status: str,
    reason_code: str,
) -> ProofEvidence:
    policy = _entry_policy(prepared.entry)
    expected = {"behavior": prepared.selection.expected_behavior}
    observed = {"status": "not_executed"}
    return ProofEvidence(
        proof_plan_digest=plan.digest(),
        claim_id=prepared.selection.claim_id,
        selection_digest=prepared.selection.digest(),
        status=status,
        verifier_id=policy.verifier_id,
        verifier_version=policy.verifier_version,
        verifier_run_digest=None,
        verification_receipt_digest=None,
        expected_summary=expected,
        observed_summary=observed,
        counterexample_summary=_counterexample(
            parameters=prepared.parameters,
            expected_summary=expected,
            observed_summary=observed,
            reason_code=reason_code,
        ),
        failure_reason_codes=[reason_code],
    )


def _portable_verifier_command(
    raw_command: Sequence[str],
    repository_root: Path,
) -> list[str]:
    portable: list[str] = []
    for index, argument in enumerate(raw_command):
        argument_path = Path(argument)
        label = argument_path.name or "runtime"
        if index == 0 and label.casefold() in {
            "python",
            "python.exe",
            "python3",
            "python3.exe",
            "python3.11",
            "python3.11.exe",
        }:
            portable.append("python")
            continue
        if not argument_path.is_absolute():
            portable.append(argument)
            continue
        try:
            relative = argument_path.resolve(strict=False).relative_to(repository_root)
        except ValueError:
            portable.append(label if index == 0 else f"<runtime>/{label}")
        else:
            portable.append(f"./{relative.as_posix()}")
    return portable


def _evidence_from_execution(
    *,
    task_contract: TaskContract,
    attempt: Attempt,
    plan: ProofPlan,
    prepared: _PreparedSelection,
    result: ProofExecutionResult,
    authoritative_receipts_required: bool,
    execution_policy_digest: str,
    repository_root: str,
    workspace_digest: str,
) -> tuple[ProofEvidence, VerifierRun | None, VerificationReceipt | None]:
    policy = _entry_policy(prepared.entry)
    status = result.status
    run = result.verifier_run
    executor_binding_valid = (
        result.family == prepared.entry.family
        and result.verifier_id == policy.verifier_id
        and result.verifier_version == policy.verifier_version
    )
    if run is not None:
        raw_metadata = dict(run.metadata)
        executor_binding_valid = executor_binding_valid and (
            raw_metadata.get("family") == prepared.entry.family
            and raw_metadata.get("capability_digest") == prepared.entry.capability_digest()
        )
    if not executor_binding_valid:
        status = "error"
        run = None
    if result.timed_out:
        status = "error"
        run = None
    if status not in {"passed", "failed"}:
        run = None
    if status in {"passed", "failed"}:
        if run is None:
            status = "error"
        elif (
            run.verifier_id != result.verifier_id
            or run.version != result.verifier_version
            or run.passed != (status == "passed")
        ):
            status = "error"
            run = None
    if run is not None:
        raw_command = list(run.command)
        root = Path(repository_root).resolve(strict=True)
        portable_command = _portable_verifier_command(raw_command, root)
        run = replace(
            run,
            command=portable_command,
            metadata={
                **run.metadata,
                "raw_command_digest": sha256_digest(raw_command),
            },
        )
        if plan.model_run.mode == "replay":
            # Replay authority binds the portable command identity. Retaining the raw
            # executable digest here would make the same evidence host-path-specific.
            replay_metadata = {
                key: value
                for key, value in run.metadata.items()
                if key
                not in {
                    "invocation_digest",
                    "invocation_nonce",
                    "raw_command_digest",
                    "raw_verifier_run_digest",
                    "raw_verifier_run_id",
                }
            }
            replay_identity = sha256_digest(
                {
                    "schema": "faber.proof_replay_verifier_run_identity.v1",
                    "verifier_id": run.verifier_id,
                    "name": run.name,
                    "version": run.version,
                    "command": run.command,
                    "passed": run.passed,
                    "metrics": run.metrics,
                    "failure_reasons": run.failure_reasons,
                    "logs_digest": run.logs_digest,
                    "metadata": replay_metadata,
                }
            )
            run = replace(
                run,
                id=f"verifier-run_replay-{replay_identity.removeprefix('sha256:')[:24]}",
                created_at=attempt.created_at,
                metadata=replay_metadata,
            )
        raw_run = run
        raw_run_metadata = dict(raw_run.metadata)
        raw_authority_digest = raw_run_metadata.get(
            "raw_verifier_run_digest",
            raw_run.digest(),
        )
        raw_authority_id = raw_run_metadata.get("raw_verifier_run_id", raw_run.id)
        authority_binding_digest = proof_authority_binding_digest(
            task_contract_digest=task_contract.digest(),
            attempt_digest=attempt.digest(),
            proof_plan_digest=plan.digest(),
            selection_digest=prepared.selection.digest(),
            catalog_digest=plan.proof_catalog_digest,
            catalog_entry_id=prepared.entry.id,
            catalog_entry_version=prepared.entry.version,
            family=prepared.entry.family,
            capability_digest=prepared.entry.capability_digest(),
            execution_policy_digest=execution_policy_digest,
            workspace_digest=workspace_digest,
            verifier_id=raw_run.verifier_id,
            verifier_version=raw_run.version,
            raw_verifier_run_digest=raw_authority_digest,
            raw_verifier_run_id=raw_authority_id,
        )
        run = VerifierRun(
            id=raw_run.id,
            created_at=raw_run.created_at,
            schema=raw_run.schema,
            verifier_id=raw_run.verifier_id,
            name=raw_run.name,
            version=raw_run.version,
            command=list(raw_run.command),
            passed=raw_run.passed,
            metrics={
                **raw_run.metrics,
                "proof_authority_binding_digest": authority_binding_digest,
            },
            failure_reasons=list(raw_run.failure_reasons),
            logs_digest=raw_run.logs_digest,
            metadata={
                **raw_run_metadata,
                "attempt_digest": attempt.digest(),
                "capability_digest": prepared.entry.capability_digest(),
                "catalog_digest": plan.proof_catalog_digest,
                "catalog_entry_id": prepared.entry.id,
                "catalog_entry_version": prepared.entry.version,
                "execution_policy_digest": execution_policy_digest,
                "proof_plan_digest": plan.digest(),
                "proof_authority_binding_digest": authority_binding_digest,
                "raw_verifier_run_digest": raw_authority_digest,
                "raw_verifier_run_id": raw_authority_id,
                "selection_digest": prepared.selection.digest(),
                "task_contract_digest": task_contract.digest(),
                "workspace_digest": workspace_digest,
            },
        )
    receipt: VerificationReceipt | None = None
    if authoritative_receipts_required and run is not None and status in {"passed", "failed"}:
        receipt = VerificationReceipt.from_verifier_run(task_contract, attempt, run)
        if plan.model_run.mode == "replay":
            receipt_identity = sha256_digest(
                {
                    "schema": "faber.proof_replay_receipt_identity.v1",
                    "task_contract_digest": task_contract.digest(),
                    "attempt_digest": attempt.digest(),
                    "verifier_run_digest": run.digest(),
                }
            )
            receipt = replace(
                receipt,
                id=(f"verification-receipt_replay-{receipt_identity.removeprefix('sha256:')[:24]}"),
                created_at=attempt.created_at,
            )

    reason_codes = [] if status == "passed" else list(result.reason_codes)
    if status == "failed" and not reason_codes:
        reason_codes = ["assertion_failed"]
    if status == "error" and not reason_codes:
        reason_codes = ["operational_error"]
    if not executor_binding_valid:
        reason_codes = ["executor_binding_mismatch"]
    if result.timed_out and "timeout" not in reason_codes:
        reason_codes.append("timeout")
    counterexample = result.counterexample_summary
    if status != "passed" and counterexample is None:
        counterexample = _counterexample(
            parameters=prepared.parameters,
            expected_summary=result.expected_summary,
            observed_summary=result.observed_summary,
            reason_code=sorted(reason_codes)[0],
        )
    evidence = ProofEvidence(
        proof_plan_digest=plan.digest(),
        claim_id=prepared.selection.claim_id,
        selection_digest=prepared.selection.digest(),
        status=status,
        verifier_id=policy.verifier_id,
        verifier_version=policy.verifier_version,
        verifier_run_digest=run.digest() if run is not None else None,
        verification_receipt_digest=receipt.digest() if receipt is not None else None,
        expected_summary=result.expected_summary,
        observed_summary=result.observed_summary,
        counterexample_summary=counterexample,
        failure_reason_codes=reason_codes,
    )
    return evidence, run, receipt


def run_proof_workflow(
    *,
    task_contract: TaskContract,
    attempt: Attempt,
    plan: ProofPlan,
    catalog: ProofCatalog,
    verifier_registry: VerifierRegistry,
    proof_policy: ProofPolicy,
    execution_policy: ProofExecutionPolicy,
    runner: LocalVerifierRunner | None = None,
    launcher: ProcessLauncher = launch_bounded_process,
) -> ProofWorkflowResult:
    """Preflight every obligation, then execute in canonical plan order."""

    started = time.perf_counter()
    prepared = _preflight_workflow(
        task_contract=task_contract,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=verifier_registry,
        proof_policy=proof_policy,
        execution_policy=execution_policy,
    )
    preflight_elapsed = time.perf_counter() - started
    runner_policy = RunnerPolicy(
        allowed_working_directory_root=execution_policy.allowed_repository_root,
        network_isolation=execution_policy.isolation_disclosure,
        allowed_environment_variables=list(execution_policy.allowed_environment_variables),
        timeout_seconds=execution_policy.per_obligation_timeout_seconds,
        max_capture_bytes=execution_policy.max_output_bytes,
        allow_shell=False,
    )
    effective_runner = runner
    execution_policy_digest = execution_policy.authority_digest()

    execution_started = time.perf_counter()
    evidence: list[ProofEvidence] = []
    runs: list[VerifierRun] = []
    receipts: list[VerificationReceipt] = []
    execution_order: list[str] = []
    diagnostics: list[Mapping[str, object]] = []
    short_circuited = False
    workspace_invalidated = False
    consumed_raw_run_authorities: set[str] = set()

    for index, item in enumerate(prepared):
        selection_digest = item.selection.digest()
        family = item.entry.family
        obligation_started = time.perf_counter()
        execution_order.append(selection_digest)
        if workspace_invalidated or not _workspace_matches_execution_policy(execution_policy):
            workspace_invalidated = True
            short_circuited = True
            proof = _not_executed_evidence(
                plan,
                item,
                status="error",
                reason_code="workspace_changed_during_execution",
            )
            evidence.append(proof)
            diagnostics.append(
                {
                    "selection_digest": selection_digest,
                    "family": family,
                    "status": "error",
                    "reason_codes": ["workspace_changed_during_execution"],
                    "order": index,
                    "elapsed_seconds": 0.0,
                }
            )
            continue
        elapsed_total = time.perf_counter() - execution_started
        if elapsed_total >= execution_policy.total_timeout_seconds:
            short_circuited = True
            proof = _not_executed_evidence(
                plan,
                item,
                status="missing",
                reason_code="total_timeout",
            )
            evidence.append(proof)
            diagnostics.append(
                {
                    "selection_digest": selection_digest,
                    "family": family,
                    "status": "missing",
                    "reason_codes": ["total_timeout"],
                    "order": index,
                    "elapsed_seconds": 0.0,
                }
            )
            continue
        try:
            invocation_context_digest = _proof_invocation_context_digest(
                task_contract=task_contract,
                attempt=attempt,
                plan=plan,
                prepared=item,
                verifier_registry=verifier_registry,
                proof_policy=proof_policy,
                execution_policy=execution_policy,
            )
            result = execute_catalog_entry(
                item.entry,
                item.parameters,
                repository_root=execution_policy.allowed_repository_root,
                verifier_registry=verifier_registry,
                runner=effective_runner,
                runner_policy=runner_policy,
                launcher=launcher,
                allowed_environment_variables=execution_policy.allowed_environment_variables,
                max_input_bytes=execution_policy.max_input_bytes,
                invocation_context_digest=invocation_context_digest,
            )
            family = result.family
            obligation_elapsed = result.elapsed_seconds
            if not _workspace_matches_execution_policy(execution_policy):
                workspace_invalidated = True
                short_circuited = True
                raise ProofWorkflowError(
                    "workspace_changed_during_execution",
                    "repository workspace changed during proof execution",
                )
            raw_run_authorities: set[str] = set()
            if result.verifier_run is not None:
                raw_run_metadata = dict(result.verifier_run.metadata)
                raw_digest = raw_run_metadata.get(
                    "raw_verifier_run_digest",
                    result.verifier_run.digest(),
                )
                raw_id = raw_run_metadata.get(
                    "raw_verifier_run_id",
                    result.verifier_run.id,
                )
                raw_run_authorities = {
                    f"digest:{raw_digest}",
                    f"id:{raw_id}",
                }
            if (
                raw_run_authorities
                and result.status in {"passed", "failed"}
                and raw_run_authorities & consumed_raw_run_authorities
            ):
                raise ProofWorkflowError(
                    "authoritative_run_reused",
                    "one verifier run cannot authorize multiple proof selections",
                )
            proof, run, receipt = _evidence_from_execution(
                task_contract=task_contract,
                attempt=attempt,
                plan=plan,
                prepared=item,
                result=result,
                authoritative_receipts_required=(execution_policy.authoritative_receipts_required),
                execution_policy_digest=execution_policy_digest,
                repository_root=execution_policy.allowed_repository_root,
                workspace_digest=execution_policy.expected_workspace_digest,
            )
            if run is not None:
                consumed_raw_run_authorities.update(raw_run_authorities)
        except Exception as exc:
            reason_code = _safe_exception_code(exc, "operational_error")
            if not _workspace_matches_execution_policy(execution_policy):
                workspace_invalidated = True
                short_circuited = True
                reason_code = "workspace_changed_during_execution"
            proof = _not_executed_evidence(
                plan,
                item,
                status="error",
                reason_code=reason_code,
            )
            run = None
            receipt = None
            obligation_elapsed = time.perf_counter() - obligation_started
        evidence.append(proof)
        if run is not None:
            runs.append(run)
        if receipt is not None:
            receipts.append(receipt)
        diagnostics.append(
            {
                "selection_digest": selection_digest,
                "family": family,
                "status": proof.status,
                "reason_codes": list(proof.failure_reason_codes),
                "order": index,
                "elapsed_seconds": round(obligation_elapsed, 6),
            }
        )

    decision = decide_proof(
        plan,
        evidence,
        proof_policy,
        task_contract=task_contract,
        attempt=attempt,
        verifier_runs=runs,
        verification_receipts=receipts,
    )
    execution_elapsed = time.perf_counter() - execution_started
    return ProofWorkflowResult(
        plan=plan,
        catalog_digest=catalog.digest(),
        verifier_registry_digest=verifier_registry.digest(),
        proof_policy_digest=proof_policy.digest(),
        execution_policy_digest=execution_policy.authority_digest(),
        workspace_digest=execution_policy.expected_workspace_digest,
        evidence=evidence,
        verifier_runs=runs,
        verification_receipts=receipts,
        decision=decision,
        execution_order=execution_order,
        timings={
            "preflight_seconds": round(preflight_elapsed, 6),
            "execution_seconds": round(execution_elapsed, 6),
            "total_seconds": round(time.perf_counter() - started, 6),
        },
        diagnostics=diagnostics,
        short_circuited=short_circuited,
    )
