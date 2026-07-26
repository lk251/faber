"""Original, deterministic Faber Proof Build Week demonstration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from faber.adapters import (
    build_planning_request,
    capture_live_planning_replay_record,
    create_planning_replay_record,
    validate_planning_replay,
)
from faber.canonical_json import canonical_json
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import FaberError, ValidationError
from faber.proof_catalog import (
    FileInvariantCapability,
    ProofCapabilityPolicy,
    ProofCatalog,
    ProofCatalogEntry,
    PythonCallCapability,
)
from faber.proof_configuration import (
    ProofConfiguration,
    ProofExecutionSettings,
    load_proof_configuration,
    load_task_contract,
)
from faber.proof_context import DEFAULT_MAX_DIFF_BYTES, collect_git_proof_context
from faber.proof_planning import ProofPlanningRequest
from faber.proof_privacy import ProofArtifactPrivacyReport, audit_proof_artifacts
from faber.proof_product import (
    ProofProductError,
    _attempt_for_context,
    run_proof_product,
)
from faber.proof_workflow import workspace_snapshot_digest
from faber.proofs import ProofClaim, ProofPolicy
from faber.verifiers import VerifierSpec

DEMO_SCHEMA = "faber.proof_build_week_demo.v1"
DEMO_PROVENANCE_SCHEMA = "faber.proof_demo_replay_provenance.v1"
DEMO_CAPTURE_SCHEMA = "faber.proof_demo_live_capture.v1"
DEMO_CREATED_AT = "2026-07-17T00:00:00+00:00"
DEMO_MODEL = "gpt-5.6"
DEMO_RETURNED_MODEL = "development-fixture-not-live"
DEMO_EXPECTED_FAILED_CLAIM = "claim.boundary-final-report"
DEMO_FIXTURE_RELATIVE = Path("examples") / "build-week-proof"
_REPLAY_NAMES = ("bad", "repaired")
_SECRET_MARKERS = (
    "api_key=",
    "api-key=",
    "authorization:",
    "bearer ",
    "password=",
    "secret=",
    "sk-proj-",
)


class ProofDemoError(FaberError):
    """Safe failure raised when the decisive demo cannot prove its expected contrast."""


@dataclass(frozen=True)
class DemoRepository:
    root: Path
    base_revision: str
    bad_revision: str
    repaired_revision: str


@dataclass(frozen=True)
class ProofDemoOutcome:
    summary: Mapping[str, object]
    output_directory: Path

    def human_lines(self) -> list[str]:
        bad = _mapping(self.summary.get("bad"), "bad")
        repaired = _mapping(self.summary.get("repaired"), "repaired")
        provenance = str(self.summary.get("provenance"))
        return [
            "Faber Proof Build Week demo",
            "",
            "                         BAD PATCH   REPAIRED PATCH",
            f"Ordinary tests        {str(bad['ordinary_tests']).upper():>10}"
            f"{str(repaired['ordinary_tests']).upper():>14}",
            f"Faber Proof verdict   {str(bad['verdict']).upper():>10}"
            f"{str(repaired['verdict']).upper():>14}",
            f"Failed required claims{_count(bad['failed_required_claims']):>10}"
            f"{_count(repaired['failed_required_claims']):>14}",
            f"Concrete counterexamples{_count(bad['concrete_counterexamples']):>7}"
            f"{_count(repaired['concrete_counterexamples']):>14}",
            "",
            f"Replay provenance: {provenance.upper()}",
            f"Blocked report:  {self.output_directory / 'bad' / 'report.html'}",
            f"Passing report:  {self.output_directory / 'repaired' / 'report.html'}",
        ]


PlanningReplayCapture = Callable[..., tuple[Mapping[str, object], str]]
DemoRunner = Callable[..., ProofDemoOutcome]


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProofDemoError(f"{label} must be an object")
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProofDemoError("demo comparison count is invalid")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8", newline="\n")


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProofDemoError(f"could not load demo JSON {path.name}: {exc}") from None
    return _mapping(value, path.name)


def resolve_demo_fixture_root(repository_root: str | Path = ".") -> Path:
    root = Path(repository_root).resolve(strict=True)
    source_fixture = root / DEMO_FIXTURE_RELATIVE
    installed_fixture = Path(sysconfig.get_path("data")) / "share" / "faber" / DEMO_FIXTURE_RELATIVE
    fixture = source_fixture if source_fixture.is_dir() else installed_fixture
    required = (
        fixture / "OWNERSHIP.md",
        fixture / "README.md",
        fixture / "source" / "__init__.py",
        fixture / "source" / "scheduler.py",
        fixture / "ordinary-tests" / "test_scheduler.py",
        fixture / "proof_harness.py",
        fixture / "revisions" / "bad" / "scheduler.py",
        fixture / "revisions" / "repaired" / "scheduler.py",
    )
    if not fixture.is_dir() or any(not path.is_file() for path in required):
        raise ProofDemoError(
            "the Build Week proof fixture is unavailable from the checkout or installed wheel"
        )
    return fixture


def _normalized_fixture_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeError) as exc:
        raise ProofDemoError(f"could not read fixture file {path.name}: {exc}") from None


def _copy_fixture_text(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        _normalized_fixture_text(source),
        encoding="utf-8",
        newline="\n",
    )


def _git(
    repository: Path,
    *arguments: str,
    commit_date: str | None = None,
) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Faber Proof Fixture",
            "GIT_AUTHOR_EMAIL": "proof-fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Faber Proof Fixture",
            "GIT_COMMITTER_EMAIL": "proof-fixture@example.invalid",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    if commit_date is not None:
        environment["GIT_AUTHOR_DATE"] = commit_date
        environment["GIT_COMMITTER_DATE"] = commit_date
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ProofDemoError("the isolated demo Git operation could not run") from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "unknown Git failure"
        raise ProofDemoError(f"isolated demo Git operation failed: {message}")
    return result.stdout.strip()


def materialize_demo_repository(fixture_root: Path, destination: Path) -> DemoRepository:
    """Create byte-stable base, bad, and repaired commits in an isolated repository."""

    fixture = fixture_root.resolve(strict=True)
    root = destination.resolve(strict=False)
    if root.exists():
        raise ProofDemoError("isolated demo repository destination already exists")
    root.mkdir(parents=True)
    _git(root, "init", "-q", "--object-format=sha1")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "config", "core.filemode", "false")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", ".git/no-hooks")

    files = {
        fixture / "README.md": root / "README.md",
        fixture / "OWNERSHIP.md": root / "OWNERSHIP.md",
        fixture / "source" / "__init__.py": root / "source" / "__init__.py",
        fixture / "source" / "scheduler.py": root / "source" / "scheduler.py",
        fixture / "ordinary-tests" / "test_scheduler.py": (
            root / "ordinary-tests" / "test_scheduler.py"
        ),
        fixture / "proof_harness.py": root / "proof_harness.py",
    }
    for source, target in files.items():
        _copy_fixture_text(source, target)
    _git(root, "add", "--", ".")
    _git(
        root,
        "commit",
        "-q",
        "-m",
        "Original bounded scheduler",
        commit_date="2026-07-17T00:01:00+00:00",
    )
    base = _git(root, "rev-parse", "HEAD")

    _copy_fixture_text(
        fixture / "revisions" / "bad" / "scheduler.py",
        root / "source" / "scheduler.py",
    )
    _git(root, "add", "--", "source/scheduler.py")
    _git(
        root,
        "commit",
        "-q",
        "-m",
        "Add explicit budget exhaustion handling",
        commit_date="2026-07-17T00:02:00+00:00",
    )
    bad = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-q", "--detach", base)
    _copy_fixture_text(
        fixture / "revisions" / "repaired" / "scheduler.py",
        root / "source" / "scheduler.py",
    )
    _git(root, "add", "--", "source/scheduler.py")
    _git(
        root,
        "commit",
        "-q",
        "-m",
        "Preserve final report at budget boundary",
        commit_date="2026-07-17T00:03:00+00:00",
    )
    repaired = _git(root, "rev-parse", "HEAD")
    return DemoRepository(root, base, bad, repaired)


def _object_schema(
    properties: Mapping[str, object] | None = None,
    *,
    required: Sequence[str] = (),
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": dict(properties or {}),
        "required": list(required),
        "additionalProperties": False,
    }


def _result_schema() -> dict[str, object]:
    return _object_schema(
        {
            "status": {"type": "string", "enum": ["complete"], "maxLength": 16},
            "report": {"type": "string", "maxLength": 256},
        },
        required=("status", "report"),
    )


def _boundary_inputs_schema() -> dict[str, object]:
    return {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 80},
        "minItems": 3,
        "maxItems": 3,
    }


def _boundary_schema() -> dict[str, object]:
    return _object_schema(
        {
            "inputs": _boundary_inputs_schema(),
            "expected": _result_schema(),
        },
        required=("inputs", "expected"),
    )


def _verifier(suffix: str, description: str) -> VerifierSpec:
    return VerifierSpec(
        id=f"verifier-spec_demo-{suffix}",
        created_at=DEMO_CREATED_AT,
        verifier_id=f"verifier.demo.{suffix}",
        name=f"Demo {suffix.replace('-', ' ')} proof",
        version="1",
        description=description,
        command_template=["python", "-c", "pass"],
        allowed_timeout_seconds=10,
    )


def _python_entry(
    *,
    entry_id: str,
    description: str,
    schema: Mapping[str, object],
    spec: VerifierSpec,
    harness_digest: str,
    callable_name: str,
    positional_parameter: str | None,
) -> ProofCatalogEntry:
    capability = PythonCallCapability(
        policy=ProofCapabilityPolicy(
            verifier_id=spec.verifier_id,
            verifier_version=spec.version,
            verifier_spec_digest=spec.digest(),
            working_directory=".",
            timeout_seconds=10,
            max_output_bytes=16_384,
            trusted_file_digests={"proof_harness.py": harness_digest},
        ),
        module="proof_harness",
        callable_name=callable_name,
        module_file="proof_harness.py",
        import_root=".",
        positional_parameter=positional_parameter,
        keyword_parameter=None,
        assertion_parameter=None,
        expected_parameter="expected",
        default_assertion="equals",
        allowed_assertions=["equals"],
    )
    return ProofCatalogEntry(
        id=entry_id,
        version="1",
        description=description,
        execution_parameter_schema=schema,
        capability=capability,
    )


def build_demo_records(
    fixture_root: Path,
    *,
    approved_replay_bundle_digests: Sequence[str] = (),
) -> tuple[TaskContract, ProofConfiguration]:
    """Build the owner-controlled task, capabilities, claims, and policy."""

    harness_digest = sha256_digest(
        _normalized_fixture_text(fixture_root / "proof_harness.py").encode("utf-8")
    )
    boundary_spec = _verifier(
        "boundary-report", "Exercise a bounded transcript at the exact final permitted turn."
    )
    failures_spec = _verifier(
        "failure-paths", "Check incomplete and cancelled paths remain explicit failures."
    )
    regression_spec = _verifier(
        "ordinary-regressions", "Re-run the ordinary early and rejection behaviors."
    )
    serialization_spec = _verifier(
        "serialization", "Check a result projection remains JSON-compatible."
    )
    source_spec = _verifier(
        "source-invariant", "Check one source-text invariant without executing it."
    )

    boundary_entry = _python_entry(
        entry_id="proof.boundary-final-report",
        description=(
            "Call the approved scheduler harness with bounded responses and assert the exact "
            "complete report at the turn boundary."
        ),
        schema=_boundary_schema(),
        spec=boundary_spec,
        harness_digest=harness_digest,
        callable_name="boundary_report",
        positional_parameter="inputs",
    )
    failure_entry = _python_entry(
        entry_id="proof.failure-paths",
        description=(
            "Run catalog-owned incomplete and cancellation scenarios and compare their exact "
            "rejection reasons."
        ),
        schema=_object_schema(
            {
                "expected": _object_schema(
                    {
                        "incomplete": {"type": "string", "maxLength": 32},
                        "cancelled": {"type": "string", "maxLength": 32},
                    },
                    required=("incomplete", "cancelled"),
                )
            },
            required=("expected",),
        ),
        spec=failures_spec,
        harness_digest=harness_digest,
        callable_name="failure_paths",
        positional_parameter=None,
    )
    regression_entry = _python_entry(
        entry_id="proof.ordinary-regressions",
        description=(
            "Run the approved early-completion, incomplete, cancellation, and composition "
            "regression matrix."
        ),
        schema=_object_schema(
            {
                "expected": _object_schema(
                    {
                        "passed": {"type": "integer", "minimum": 0, "maximum": 4},
                        "total": {"type": "integer", "minimum": 4, "maximum": 4},
                    },
                    required=("passed", "total"),
                )
            },
            required=("expected",),
        ),
        spec=regression_spec,
        harness_digest=harness_digest,
        callable_name="ordinary_regressions",
        positional_parameter=None,
    )
    serialization_entry = _python_entry(
        entry_id="proof.serialization-preview",
        description=(
            "Check that one scheduler result has a small JSON-compatible projection; this does "
            "not establish the boundary requirement."
        ),
        schema=_object_schema(
            {
                "inputs": _boundary_inputs_schema(),
                "expected": _object_schema(
                    {
                        "json_compatible": {"type": "boolean"},
                        "field_count": {"type": "integer", "minimum": 1, "maximum": 4},
                    },
                    required=("json_compatible", "field_count"),
                ),
            },
            required=("inputs", "expected"),
        ),
        spec=serialization_spec,
        harness_digest=harness_digest,
        callable_name="serialization_preview",
        positional_parameter="inputs",
    )
    source_entry = ProofCatalogEntry(
        id="proof.no-broad-exception-suppression",
        version="1",
        description=(
            "Check that the scheduler does not add a broad exception handler; useful but not a "
            "substitute for the behavioral boundary proof."
        ),
        execution_parameter_schema=_object_schema(
            {"expected": {"type": "string", "maxLength": 64}},
            required=("expected",),
        ),
        capability=FileInvariantCapability(
            policy=ProofCapabilityPolicy(
                verifier_id=source_spec.verifier_id,
                verifier_version=source_spec.version,
                verifier_spec_digest=source_spec.digest(),
                working_directory=".",
                timeout_seconds=5,
                max_output_bytes=8_192,
            ),
            repository_path="source/scheduler.py",
            operation="excludes_literal",
            expected_parameter="expected",
            json_pointer_parameter=None,
        ),
    )

    boundary_claim = ProofClaim(
        id=DEMO_EXPECTED_FAILED_CLAIM,
        statement=(
            "A complete final report produced on the last permitted turn is preserved and returned."
        ),
        severity="critical",
        requirement_refs=["requirement:0"],
        evidence_required=True,
        risk_rationale="An ordering error can discard useful completed work at the exact budget.",
    )
    failure_claim = ProofClaim(
        id="claim.failure-paths-remain-explicit",
        statement="Incomplete and cancelled runs remain explicit failures.",
        severity="high",
        requirement_refs=["requirement:1", "requirement:3"],
        evidence_required=True,
        risk_rationale="A broad suppression fix could falsely accept unsuccessful runs.",
    )
    regression_claim = ProofClaim(
        id="claim.ordinary-behavior-preserved",
        statement="Early completion, rejection, and deterministic composition remain unchanged.",
        severity="medium",
        requirement_refs=["requirement:2"],
        evidence_required=True,
        risk_rationale="The boundary repair must not regress ordinary scheduler behavior.",
    )
    mandatory_specs = (boundary_spec, failures_spec, regression_spec)
    catalog = ProofCatalog(
        [
            boundary_entry,
            failure_entry,
            regression_entry,
            serialization_entry,
            source_entry,
        ]
    )
    policy = ProofPolicy(
        name="build-week-original-scheduler-proof",
        version="1",
        approved_verifier_ids=[
            boundary_spec.verifier_id,
            failures_spec.verifier_id,
            regression_spec.verifier_id,
            serialization_spec.verifier_id,
            source_spec.verifier_id,
        ],
        mandatory_claim_ids=[boundary_claim.id, failure_claim.id, regression_claim.id],
        mandatory_template_ids=[boundary_entry.id, failure_entry.id, regression_entry.id],
        mandatory_verifier_ids=[spec.verifier_id for spec in mandatory_specs],
        minimum_authoritative_outcomes=3,
    )
    task = TaskContract(
        id="task-contract_build-week-boundary-report",
        created_at=DEMO_CREATED_AT,
        title="Preserve a completed report at the exact turn budget",
        description=(
            "Distinguish exhausted incomplete work from a complete final report without "
            "weakening existing rejection behavior."
        ),
        requirements=[
            "Preserve and return a complete final report produced on the last permitted turn.",
            "Keep empty, incomplete, cancelled, and unrelated failed runs explicit failures.",
            "Preserve ordinary early completion and deterministic report composition.",
            "Do not broadly suppress scheduler failures.",
        ],
        verifier_ids=[spec.verifier_id for spec in mandatory_specs],
        repository="faber-proof-build-week-demo",
    )
    configuration = ProofConfiguration(
        catalog=catalog,
        verifier_specs=[
            boundary_spec,
            failures_spec,
            regression_spec,
            serialization_spec,
            source_spec,
        ],
        proof_policy=policy,
        mandatory_claims=[boundary_claim, failure_claim, regression_claim],
        execution=ProofExecutionSettings(
            maximum_obligations=8,
            per_obligation_timeout_seconds=10,
            total_timeout_seconds=60,
            max_input_bytes=65_536,
            max_output_bytes=16_384,
        ),
        approved_replay_bundle_digests=approved_replay_bundle_digests,
    )
    return task, configuration


def _checkout(repository: DemoRepository, revision: str) -> None:
    _git(repository.root, "checkout", "-q", "--detach", revision)


def _planning_request(
    repository: DemoRepository,
    revision: str,
    task: TaskContract,
    configuration: ProofConfiguration,
) -> ProofPlanningRequest:
    _checkout(repository, revision)
    context = collect_git_proof_context(
        repository.root,
        base_revision=repository.base_revision,
        candidate_revision=revision,
    )
    attempt = _attempt_for_context(
        context,
        task_contract_id=task.id,
        workspace_digest=workspace_snapshot_digest(repository.root),
        dry_run=False,
    )
    return build_planning_request(
        task,
        attempt,
        diff_text=context.planning_diff_text,
        catalog_entries=configuration.catalog.planner_views(),
        proof_catalog_digest=configuration.catalog.digest(),
        mandatory_claims=configuration.mandatory_claims,
        mandatory_template_ids=configuration.proof_policy.mandatory_template_ids,
        max_diff_bytes=DEFAULT_MAX_DIFF_BYTES,
    )


def _claim_payload(claim: ProofClaim) -> dict[str, object]:
    return {
        "id": claim.id,
        "statement": claim.statement,
        "severity": claim.severity,
        "requirement_refs": list(claim.requirement_refs),
        "evidence_required": claim.evidence_required,
        "risk_rationale": claim.risk_rationale,
    }


def _structured_response(configuration: ProofConfiguration) -> dict[str, object]:
    claims = {claim.id: claim for claim in configuration.mandatory_claims}
    return {
        "claims": [_claim_payload(claims[key]) for key in sorted(claims)],
        "selections": [
            {
                "claim_id": DEMO_EXPECTED_FAILED_CLAIM,
                "template_id": "proof.boundary-final-report",
                "template_version": "1",
                "parameters": {
                    "inputs": ["turn_budget=2", "NOTE: premise", "FINAL: summary"],
                    "expected": {"status": "complete", "report": "premise\nsummary"},
                },
                "expected_behavior": (
                    "The complete final report survives at the exact budget boundary."
                ),
                "rationale": "The catalog-owned call directly exercises the missing edge case.",
            },
            {
                "claim_id": "claim.failure-paths-remain-explicit",
                "template_id": "proof.failure-paths",
                "template_version": "1",
                "parameters": {"expected": {"incomplete": "incomplete", "cancelled": "cancelled"}},
                "expected_behavior": "Incomplete and cancelled scenarios remain rejected.",
                "rationale": "This detects a broad failure-suppression repair.",
            },
            {
                "claim_id": "claim.ordinary-behavior-preserved",
                "template_id": "proof.ordinary-regressions",
                "template_version": "1",
                "parameters": {"expected": {"passed": 4, "total": 4}},
                "expected_behavior": "All four ordinary behavior checks remain green.",
                "rationale": "The ordinary matrix guards existing behavior around the repair.",
            },
        ],
        "uncovered_claim_ids": [],
        "human_review_recommended": False,
        "uncertainty_notes": [],
    }


def generate_development_fixture_payloads(fixture_root: Path) -> Mapping[str, object]:
    """Generate deterministic fake-development replays without any provider call."""

    task, configuration = build_demo_records(fixture_root)
    with tempfile.TemporaryDirectory(prefix="faber-proof-fixture-") as temporary:
        repository = materialize_demo_repository(fixture_root, Path(temporary) / "repository")
        requests = {
            "bad": _planning_request(repository, repository.bad_revision, task, configuration),
            "repaired": _planning_request(
                repository, repository.repaired_revision, task, configuration
            ),
        }
        replays: dict[str, Mapping[str, object]] = {}
        digests: dict[str, str] = {}
        for index, name in enumerate(_REPLAY_NAMES, start=1):
            replay, digest = create_planning_replay_record(
                requests[name],
                _structured_response(configuration),
                created_at=DEMO_CREATED_AT,
                requested_model=DEMO_MODEL,
                returned_model=DEMO_RETURNED_MODEL,
                response_id=f"resp_fake_development_{index}",
                input_tokens=256,
                output_tokens=192,
                latency_ms=10 + index,
            )
            replays[name] = replay
            digests[name] = digest
        approved = replace(
            configuration,
            approved_replay_bundle_digests=[digests[name] for name in _REPLAY_NAMES],
        )
        provenance = {
            "schema": DEMO_PROVENANCE_SCHEMA,
            "status": "fake-development",
            "description": (
                "Deterministic injected planner fixtures for no-key development; not a live "
                "model result and not eligible as final submission provenance."
            ),
            "bundles": {
                name: {
                    "path": f"replays/{name}.json",
                    "bundle_digest": digests[name],
                    "request_digest": requests[name].digest(),
                    "requested_model": DEMO_MODEL,
                    "returned_model": DEMO_RETURNED_MODEL,
                    "response_id": f"resp_fake_development_{index}",
                }
                for index, name in enumerate(_REPLAY_NAMES, start=1)
            },
        }
    return {
        "task_contract": task.to_dict(),
        "proof_catalog": approved.to_dict(),
        "bad_replay": replays["bad"],
        "repaired_replay": replays["repaired"],
        "provenance": provenance,
    }


def write_development_fixtures(fixture_root: Path) -> Mapping[str, object]:
    payloads = generate_development_fixture_payloads(fixture_root)
    _write_json(fixture_root / "task-contract.json", payloads["task_contract"])
    _write_json(fixture_root / "proof-catalog.json", payloads["proof_catalog"])
    _write_json(fixture_root / "replays" / "bad.json", payloads["bad_replay"])
    _write_json(fixture_root / "replays" / "repaired.json", payloads["repaired_replay"])
    _write_json(fixture_root / "replays" / "provenance.json", payloads["provenance"])
    return payloads


def _secret_safe(value: object) -> bool:
    lowered = canonical_json(value).casefold()
    return not any(marker in lowered for marker in _SECRET_MARKERS)


def review_demo_replays(
    fixture_root: Path,
    *,
    require_live_reviewed: bool = False,
) -> Mapping[str, object]:
    """Validate committed replays against exact deterministic requests and provenance."""

    provenance = _read_json(fixture_root / "replays" / "provenance.json")
    status = provenance.get("status")
    if status not in {"fake-development", "live-reviewed"}:
        raise ProofDemoError("replay provenance status is invalid")
    if require_live_reviewed and status != "live-reviewed":
        raise ProofDemoError("final demo requires live-reviewed replay provenance")
    if not _secret_safe(provenance):
        raise ProofDemoError("replay provenance contains secret-like text")
    task = load_task_contract(fixture_root / "task-contract.json")
    configuration = load_proof_configuration(fixture_root / "proof-catalog.json")
    provenance_bundles = _mapping(provenance.get("bundles"), "provenance.bundles")
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="faber-proof-review-") as temporary:
        repository = materialize_demo_repository(fixture_root, Path(temporary) / "repository")
        revisions = {
            "bad": repository.bad_revision,
            "repaired": repository.repaired_revision,
        }
        for name in _REPLAY_NAMES:
            request = _planning_request(repository, revisions[name], task, configuration)
            replay_path = fixture_root / "replays" / f"{name}.json"
            record = _read_json(replay_path)
            if not _secret_safe(record):
                raise ProofDemoError(f"{name} replay contains secret-like text")
            digest = sha256_digest(record)
            if digest not in configuration.approved_replay_bundle_digests:
                raise ProofDemoError(f"{name} replay is not owner-approved by configuration")
            metadata = validate_planning_replay(
                replay_path,
                request=request,
                expected_bundle_digest=digest,
                expected_requested_model=DEMO_MODEL,
            )
            recorded = _mapping(provenance_bundles.get(name), f"provenance.bundles.{name}")
            if (
                recorded.get("bundle_digest") != digest
                or recorded.get("request_digest") != request.digest()
                or recorded.get("requested_model") != DEMO_MODEL
                or recorded.get("returned_model") != metadata.get("returned_model")
                or recorded.get("response_id") != metadata.get("response_id")
            ):
                raise ProofDemoError(f"{name} replay provenance does not match its bundle")
            results[name] = metadata
    return {
        "schema": "faber.proof_demo_replay_review.v1",
        "status": "valid",
        "provenance": status,
        "bundles": results,
    }


def _ordinary_test(repository: DemoRepository, revision: str) -> Mapping[str, object]:
    _checkout(repository, revision)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "ordinary-tests",
                "-p",
                "test_*.py",
            ],
            cwd=repository.root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ProofDemoError("ordinary demo tests could not run") from None
    record = {
        "schema": "faber.proof_demo_ordinary_tests.v1",
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "command": "python -m unittest discover -s ordinary-tests -p test_*.py",
        "stdout": result.stdout[-4_096:],
        "stderr": result.stderr[-4_096:],
    }
    if result.returncode != 0:
        raise ProofDemoError("ordinary tests failed for a demo candidate")
    return record


def _proof_summary(
    summary: Mapping[str, object],
    *,
    ordinary_status: str,
    report_path: str,
) -> dict[str, object]:
    counts = _mapping(summary.get("obligation_counts"), "obligation_counts")
    counterexample_count = 1 if summary.get("counterexample") is not None else 0
    return {
        "ordinary_tests": ordinary_status,
        "verdict": summary.get("verdict"),
        "required_claims": counts.get("required"),
        "passed_required_claims": counts.get("passed"),
        "failed_required_claims": counts.get("failed"),
        "missing_required_claims": counts.get("missing"),
        "concrete_counterexamples": counterexample_count,
        "failed_claim_ids": summary.get("failed_claim_ids"),
        "failed_claim": summary.get("failed_claim"),
        "counterexample": summary.get("counterexample"),
        "candidate_revision": summary.get("candidate_revision"),
        "proof_plan_digest": _mapping(summary.get("record_digests"), "record_digests").get(
            "proof_plan"
        ),
        "decision_digest": _mapping(summary.get("record_digests"), "record_digests").get(
            "proof_decision"
        ),
        "report": report_path,
    }


def _validate_demo_contrast(bad: Mapping[str, object], repaired: Mapping[str, object]) -> None:
    counterexample = canonical_json(bad.get("counterexample"))
    if (
        bad.get("ordinary_tests") != "pass"
        or bad.get("verdict") != "block"
        or bad.get("failed_required_claims") != 1
        or bad.get("failed_claim_ids") != [DEMO_EXPECTED_FAILED_CLAIM]
        or bad.get("concrete_counterexamples") != 1
        or "turn_budget" not in counterexample
        or "FINAL: summary" not in counterexample
        or repaired.get("ordinary_tests") != "pass"
        or repaired.get("verdict") != "pass"
        or repaired.get("failed_required_claims") != 0
        or repaired.get("missing_required_claims") != 0
        or repaired.get("concrete_counterexamples") != 0
    ):
        raise ProofDemoError(
            "the demo did not produce the required PASS/BLOCK contrast: "
            + canonical_json({"bad": bad, "repaired": repaired})
        )


def _publish_demo(stage: Path, target: Path) -> None:
    backup = target.parent / f".{target.name}.faber-demo-backup-{os.getpid()}"
    if backup.exists():
        raise ProofDemoError("a stale demo output backup blocks safe publication")
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise ProofDemoError("demo output path is not a safe directory")
        marker = _read_json(target / "demo-summary.json")
        if marker.get("schema") != DEMO_SCHEMA or marker.get("managed_by") != "faber-proof-demo":
            raise ProofDemoError("existing demo output is not managed by Faber Proof")
        if any(path.is_symlink() for path in target.rglob("*")):
            raise ProofDemoError("existing demo output contains a symlink")
        target.replace(backup)
    try:
        stage.replace(target)
    except OSError:
        if backup.exists() and not target.exists():
            backup.replace(target)
        raise ProofDemoError("validated demo output could not be published") from None
    if backup.exists():
        shutil.rmtree(backup)


def run_proof_demo(
    *,
    repository_root: str | Path = ".",
    mode: str = "replay",
    output_directory: str | Path = ".faber/build-week-demo",
) -> ProofDemoOutcome:
    """Run ordinary tests and Faber Proof for the bad and repaired candidates."""

    if mode not in {"live", "replay"}:
        raise ProofDemoError("demo mode must be live or replay")
    fixture = resolve_demo_fixture_root(repository_root)
    review = review_demo_replays(fixture) if mode == "replay" else None
    provenance = str(review["provenance"]) if review is not None else "live-unrecorded"
    task_path = fixture / "task-contract.json"
    catalog_path = fixture / "proof-catalog.json"
    output = Path(output_directory)
    if not output.is_absolute():
        output = Path(repository_root).resolve(strict=True) / output
    output = output.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.faber-demo-stage-", dir=output.parent))
    try:
        with tempfile.TemporaryDirectory(prefix="faber-proof-demo-") as temporary:
            repository = materialize_demo_repository(fixture, Path(temporary) / "repository")
            revisions = {
                "bad": repository.bad_revision,
                "repaired": repository.repaired_revision,
            }
            proof_records: dict[str, Mapping[str, object]] = {}
            ordinary_records: dict[str, Mapping[str, object]] = {}
            for name in _REPLAY_NAMES:
                revision = revisions[name]
                ordinary = _ordinary_test(repository, revision)
                ordinary_records[name] = ordinary
                _write_json(stage / "ordinary-tests" / f"{name}.json", ordinary)
                replay_path = fixture / "replays" / f"{name}.json" if mode == "replay" else None
                proof = run_proof_product(
                    repository=repository.root,
                    task_path=task_path,
                    catalog_path=catalog_path,
                    base_revision=repository.base_revision,
                    candidate_revision=revision,
                    mode=mode,
                    replay_path=replay_path,
                    model=DEMO_MODEL,
                    output_directory=stage / name,
                )
                proof_records[name] = proof.summary
            bad = _proof_summary(
                proof_records["bad"],
                ordinary_status=str(ordinary_records["bad"]["status"]),
                report_path="bad/report.html",
            )
            repaired = _proof_summary(
                proof_records["repaired"],
                ordinary_status=str(ordinary_records["repaired"]["status"]),
                report_path="repaired/report.html",
            )
            _validate_demo_contrast(bad, repaired)
            summary = {
                "schema": DEMO_SCHEMA,
                "managed_by": "faber-proof-demo",
                "status": "complete",
                "mode": mode,
                "provenance": provenance,
                "bad": bad,
                "repaired": repaired,
            }
            _write_json(stage / "demo-summary.json", summary)
        _publish_demo(stage, output)
        return ProofDemoOutcome(summary=summary, output_directory=output)
    except (ProofProductError, ValidationError, OSError) as exc:
        raise ProofDemoError(f"demo execution failed closed: {exc}") from None
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def capture_live_demo_replays(
    fixture_root: Path,
    output_directory: Path,
    *,
    capture_record: PlanningReplayCapture = capture_live_planning_replay_record,
) -> Mapping[str, object]:
    """Capture exact live planner responses into an unreviewed external staging directory."""

    if output_directory.exists():
        raise ProofDemoError("live capture output directory must not already exist")
    task, configuration = build_demo_records(fixture_root)
    output_directory.mkdir(parents=True)
    captured_at = datetime.now(UTC).isoformat()
    with tempfile.TemporaryDirectory(prefix="faber-proof-live-capture-") as temporary:
        repository = materialize_demo_repository(fixture_root, Path(temporary) / "repository")
        revisions = {
            "bad": repository.bad_revision,
            "repaired": repository.repaired_revision,
        }
        bundles: dict[str, object] = {}
        for name in _REPLAY_NAMES:
            request = _planning_request(repository, revisions[name], task, configuration)
            replay, digest = capture_record(
                request,
                model=DEMO_MODEL,
                created_at=captured_at,
            )
            _write_json(output_directory / f"{name}.json", replay)
            bundles[name] = {
                "path": f"{name}.json",
                "bundle_digest": digest,
                "request_digest": request.digest(),
                "requested_model": replay.get("requested_model"),
                "returned_model": replay.get("returned_model"),
                "response_id": replay.get("response_id"),
            }
    manifest = {
        "schema": DEMO_CAPTURE_SCHEMA,
        "status": "live-captured-unreviewed",
        "captured_at": captured_at,
        "warning": "Do not install or describe these captures as reviewed until human review.",
        "bundles": bundles,
    }
    _write_json(output_directory / "capture-manifest.json", manifest)
    return manifest


def _fixture_file_digests(fixture_root: Path) -> dict[str, str]:
    return {
        path.relative_to(fixture_root).as_posix(): sha256_digest(path.read_bytes())
        for path in sorted(fixture_root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and not path.is_symlink()
    }


def _preflight_live_demo_capture(
    fixture_root: Path,
    *,
    expected_branch: str,
) -> Mapping[str, object]:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ProofDemoError("OPENAI_API_KEY is required for guarded live capture")
    repository_root = fixture_root.parents[1].resolve(strict=True)
    branch = _git(repository_root, "branch", "--show-current")
    if branch != expected_branch:
        raise ProofDemoError("live capture must run from the expected clean branch")
    if _git(repository_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ProofDemoError("live capture requires a clean Git worktree")

    committed_task = load_task_contract(fixture_root / "task-contract.json")
    committed_configuration = load_proof_configuration(fixture_root / "proof-catalog.json")
    task, configuration = build_demo_records(fixture_root)
    if (
        task.digest() != committed_task.digest()
        or configuration.catalog.digest() != committed_configuration.catalog.digest()
        or configuration.proof_policy.digest() != committed_configuration.proof_policy.digest()
    ):
        raise ProofDemoError("live capture authority does not match the committed demo definition")
    replay_review = review_demo_replays(fixture_root)
    return {
        "schema": "faber.proof_demo_live_capture_preflight.v1",
        "status": "pass",
        "branch": branch,
        "source_commit": _git(repository_root, "rev-parse", "HEAD"),
        "task_contract_digest": task.digest(),
        "catalog_digest": configuration.catalog.digest(),
        "proof_policy_digest": configuration.proof_policy.digest(),
        "replay_provenance": replay_review["provenance"],
        "requested_model": DEMO_MODEL,
    }


def _restore_fixture_directory(fixture_root: Path, backup: Path) -> None:
    failed = fixture_root.parent / f".{fixture_root.name}.failed-live-capture-{os.getpid()}"
    try:
        fixture_root.replace(failed)
        backup.replace(fixture_root)
    except OSError:
        if failed.exists() and not fixture_root.exists():
            failed.replace(fixture_root)
        raise ProofDemoError("live capture failed and fixture rollback was unsuccessful") from None
    shutil.rmtree(failed, ignore_errors=True)


def run_guarded_live_demo_capture(
    fixture_root: Path,
    *,
    reviewer: str,
    reviewed_at: str | None = None,
    expected_branch: str = "build-week/faber-proof",
    review_manifest_path: Path | None = None,
    capture_record: PlanningReplayCapture = capture_live_planning_replay_record,
    demo_runner: DemoRunner = run_proof_demo,
) -> Mapping[str, object]:
    """Capture, review, install, replay, and audit both demo candidates transactionally."""

    fixture = fixture_root.resolve(strict=True)
    repository_root = fixture.parents[1].resolve(strict=True)
    review_time = (reviewed_at or datetime.now(UTC).isoformat()).strip()
    if not reviewer.strip() or not review_time:
        raise ProofDemoError("reviewer identity and review time are required")
    preflight = _preflight_live_demo_capture(
        fixture,
        expected_branch=expected_branch,
    )
    before = _fixture_file_digests(fixture)
    key = os.environ["OPENAI_API_KEY"]
    transaction = Path(
        tempfile.mkdtemp(prefix=".faber-proof-live-transaction-", dir=fixture.parent)
    )
    backup = transaction / "fixture-backup"
    shutil.copytree(fixture, backup)
    installed = False
    try:
        capture_directory = transaction / "capture"
        capture = capture_live_demo_replays(
            fixture,
            capture_directory,
            capture_record=capture_record,
        )
        review = review_live_demo_capture(
            fixture,
            capture_directory,
            reviewer=reviewer,
            reviewed_at=review_time,
            install=True,
        )
        installed = True
        demo = demo_runner(
            repository_root=repository_root,
            mode="replay",
            output_directory=transaction / "offline-demo",
        )
        bad = _mapping(demo.summary.get("bad"), "offline demo bad result")
        repaired = _mapping(demo.summary.get("repaired"), "offline demo repaired result")
        _validate_demo_contrast(bad, repaired)
        privacy = audit_proof_artifacts(
            [demo.output_directory, fixture / "expected"],
            forbidden_literals=(key,),
        )
        if not privacy.passed:
            raise ProofDemoError("post-install demo artifacts failed the privacy audit")

        after = _fixture_file_digests(fixture)
        changed = sorted(
            path for path in set(before) | set(after) if before.get(path) != after.get(path)
        )
        manifest: dict[str, object] = {
            "schema": "faber.proof_demo_live_capture_review_manifest.v1",
            "status": "installed-live-reviewed",
            "preflight": dict(preflight),
            "reviewer": reviewer.strip(),
            "reviewed_at": review_time,
            "capture": dict(capture),
            "review": dict(review),
            "offline_demo": {
                "bad": dict(bad),
                "repaired": dict(repaired),
            },
            "privacy_audit": privacy.to_dict(),
            "changed_paths": changed,
            "before_digests": {path: before.get(path) for path in changed},
            "after_digests": {path: after.get(path) for path in changed},
        }
        destination = review_manifest_path or (
            repository_root / ".faber" / "live-gpt56-review-manifest.json"
        )
        _write_json(destination, manifest)
        return manifest
    except Exception:
        if installed:
            _restore_fixture_directory(fixture, backup)
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def _install_reviewed_demo_files(
    fixture_root: Path,
    files: Mapping[str, object],
    *,
    forbidden_literals: Sequence[str] = (),
) -> ProofArtifactPrivacyReport:
    stage_parent = Path(tempfile.mkdtemp(prefix=".faber-proof-reviewed-", dir=fixture_root.parent))
    stage = stage_parent / "candidate"
    stage.mkdir()
    backup = Path(tempfile.mkdtemp(prefix=".faber-proof-backup-", dir=fixture_root.parent))
    installed: list[Path] = []
    moved: list[tuple[Path, Path]] = []
    try:
        for relative, value in files.items():
            path = stage / relative
            if relative.endswith((".html", ".md")):
                if not isinstance(value, str):
                    raise ProofDemoError("reviewed text report payload is invalid")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value, encoding="utf-8", newline="\n")
            else:
                _write_json(path, value)
        privacy = audit_proof_artifacts(
            [stage],
            forbidden_literals=forbidden_literals,
        )
        if not privacy.passed:
            raise ProofDemoError(
                "reviewed demo fixture candidate failed the artifact privacy audit"
            )
        for relative in sorted(files):
            target = fixture_root / relative
            staged = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                target.replace(saved)
                moved.append((target, saved))
            staged.replace(target)
            installed.append(target)
    except OSError:
        for target in reversed(installed):
            if target.exists():
                target.unlink()
        for target, saved in reversed(moved):
            if saved.exists():
                saved.replace(target)
        raise ProofDemoError("reviewed demo fixtures could not be installed atomically") from None
    finally:
        shutil.rmtree(stage_parent, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
    return privacy


def _audit_reviewed_demo_files(
    parent: Path,
    files: Mapping[str, object],
    *,
    forbidden_literals: Sequence[str] = (),
) -> ProofArtifactPrivacyReport:
    candidate = parent / "candidate"
    candidate.mkdir(parents=True)
    for relative, value in files.items():
        path = candidate / relative
        if relative.endswith((".html", ".md")):
            if not isinstance(value, str):
                raise ProofDemoError("reviewed text report payload is invalid")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8", newline="\n")
        else:
            _write_json(path, value)
    report = audit_proof_artifacts(
        [candidate],
        forbidden_literals=forbidden_literals,
    )
    if not report.passed:
        raise ProofDemoError("reviewed demo fixture candidate failed the artifact privacy audit")
    return report


def review_live_demo_capture(
    fixture_root: Path,
    capture_directory: Path,
    *,
    reviewer: str,
    reviewed_at: str,
    install: bool = False,
) -> Mapping[str, object]:
    """Validate staged live captures and optionally install them as reviewed authority."""

    reviewer = reviewer.strip()
    reviewed_at = reviewed_at.strip()
    if not reviewer or not reviewed_at:
        raise ProofDemoError("reviewer and reviewed-at are required for a live review")
    capture = _read_json(capture_directory / "capture-manifest.json")
    if (
        capture.get("schema") != DEMO_CAPTURE_SCHEMA
        or capture.get("status") != "live-captured-unreviewed"
    ):
        raise ProofDemoError("candidate capture manifest is not an unreviewed live capture")
    capture_bundles = _mapping(capture.get("bundles"), "capture.bundles")
    committed_task = load_task_contract(fixture_root / "task-contract.json")
    committed_configuration = load_proof_configuration(fixture_root / "proof-catalog.json")
    task, base_configuration = build_demo_records(fixture_root)
    if (
        task.digest() != committed_task.digest()
        or base_configuration.catalog.digest() != committed_configuration.catalog.digest()
        or base_configuration.proof_policy.digest() != committed_configuration.proof_policy.digest()
    ):
        raise ProofDemoError("committed demo authority differs from the reviewed definition")

    records: dict[str, Mapping[str, object]] = {}
    digests: dict[str, str] = {}
    metadata: dict[str, Mapping[str, object]] = {}
    requests: dict[str, ProofPlanningRequest] = {}
    with tempfile.TemporaryDirectory(prefix="faber-proof-live-review-") as temporary:
        review_root = Path(temporary)
        repository = materialize_demo_repository(fixture_root, review_root / "repository")
        revisions = {
            "bad": repository.bad_revision,
            "repaired": repository.repaired_revision,
        }
        for name in _REPLAY_NAMES:
            record = _read_json(capture_directory / f"{name}.json")
            if not _secret_safe(record):
                raise ProofDemoError(f"{name} live capture contains secret-like text")
            digest = sha256_digest(record)
            manifest_record = _mapping(capture_bundles.get(name), f"capture.bundles.{name}")
            request = _planning_request(repository, revisions[name], task, base_configuration)
            if (
                manifest_record.get("bundle_digest") != digest
                or manifest_record.get("request_digest") != request.digest()
            ):
                raise ProofDemoError(f"{name} capture manifest does not match its replay")
            validated = validate_planning_replay(
                capture_directory / f"{name}.json",
                request=request,
                expected_bundle_digest=digest,
                expected_requested_model=DEMO_MODEL,
            )
            if validated.get("returned_model") in {None, "", DEMO_RETURNED_MODEL} or validated.get(
                "response_id"
            ) in {None, ""}:
                raise ProofDemoError(f"{name} capture lacks real returned model metadata")
            records[name] = record
            digests[name] = digest
            metadata[name] = validated
            requests[name] = request

        reviewed_configuration = replace(
            base_configuration,
            approved_replay_bundle_digests=[digests[name] for name in _REPLAY_NAMES],
        )
        candidate_catalog = review_root / "proof-catalog.json"
        _write_json(candidate_catalog, reviewed_configuration.to_dict())
        summaries: dict[str, Mapping[str, object]] = {}
        ordinary: dict[str, Mapping[str, object]] = {}
        for name in _REPLAY_NAMES:
            ordinary[name] = _ordinary_test(repository, revisions[name])
            outcome = run_proof_product(
                repository=repository.root,
                task_path=fixture_root / "task-contract.json",
                catalog_path=candidate_catalog,
                base_revision=repository.base_revision,
                candidate_revision=revisions[name],
                mode="replay",
                replay_path=capture_directory / f"{name}.json",
                model=DEMO_MODEL,
                output_directory=review_root / name,
            )
            summaries[name] = outcome.summary
        bad = _proof_summary(
            summaries["bad"],
            ordinary_status=str(ordinary["bad"]["status"]),
            report_path="expected/blocked-report.html",
        )
        repaired = _proof_summary(
            summaries["repaired"],
            ordinary_status=str(ordinary["repaired"]["status"]),
            report_path="expected/passing-report.html",
        )
        _validate_demo_contrast(bad, repaired)
        reports = {
            "blocked": (review_root / "bad" / "report.html").read_text(encoding="utf-8"),
            "passing": (review_root / "repaired" / "report.html").read_text(encoding="utf-8"),
        }
        for label, report in reports.items():
            if not _secret_safe(report) or str(repository.root).casefold() in report.casefold():
                raise ProofDemoError(f"{label} reviewed report is not portable and secret-safe")

        provenance = {
            "schema": DEMO_PROVENANCE_SCHEMA,
            "status": "live-reviewed",
            "description": "Sanitized live planner responses reviewed against exact demo requests.",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "bundles": {
                name: {
                    "path": f"replays/{name}.json",
                    "bundle_digest": digests[name],
                    "request_digest": requests[name].digest(),
                    "requested_model": metadata[name]["requested_model"],
                    "returned_model": metadata[name]["returned_model"],
                    "response_id": metadata[name]["response_id"],
                }
                for name in _REPLAY_NAMES
            },
        }
        generation_manifest = {
            "schema": "faber.proof_demo_sample_reports.v1",
            "command": (
                "python examples/build-week-proof/scripts/review_replays.py "
                "--candidate-dir <capture> --reviewer <name> --reviewed-at <timestamp> --install"
            ),
            "source_commit": _git(fixture_root.parents[1], "rev-parse", "HEAD"),
            "generator_version": "faber-proof-report.v1",
            "replay_digests": {name: digests[name] for name in _REPLAY_NAMES},
            "report_digests": {
                "expected/blocked-report.html": sha256_digest(reports["blocked"].encode("utf-8")),
                "expected/passing-report.html": sha256_digest(reports["passing"].encode("utf-8")),
            },
            "determinism_note": (
                "Semantic inputs, revisions, replay and decision bindings are deterministic; "
                "runtime timing remains non-authoritative performance evidence."
            ),
        }
        forbidden_literals = tuple(value for value in (os.environ.get("OPENAI_API_KEY"),) if value)
        reviewed_files: dict[str, object] = {
            "proof-catalog.json": reviewed_configuration.to_dict(),
            "replays/bad.json": records["bad"],
            "replays/repaired.json": records["repaired"],
            "replays/provenance.json": provenance,
            "expected/generation-manifest.json": generation_manifest,
            "expected/blocked-report.html": reports["blocked"],
            "expected/passing-report.html": reports["passing"],
        }
        privacy = _audit_reviewed_demo_files(
            review_root / "privacy-review",
            reviewed_files,
            forbidden_literals=forbidden_literals,
        )
        generation_manifest["privacy_audit_digest"] = sha256_digest(privacy.to_dict())
        reviewed_files["expected/generation-manifest.json"] = generation_manifest
        reviewed_files["expected/privacy-audit.json"] = privacy.to_dict()
        reviewed_files["expected/privacy-audit.md"] = privacy.markdown()
        if install:
            _install_reviewed_demo_files(
                fixture_root,
                reviewed_files,
                forbidden_literals=forbidden_literals,
            )
    return {
        "schema": "faber.proof_demo_live_review.v1",
        "status": "installed-live-reviewed" if install else "valid-live-uninstalled",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "bundles": metadata,
        "bad": bad,
        "repaired": repaired,
        "privacy_audit": privacy.to_dict(),
    }
