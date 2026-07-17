from __future__ import annotations

import io
import json
import os
import py_compile
import shutil
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_catalog import (
    ArtifactValidatorCapability,
    ExistingCommandCapability,
    FileInvariantCapability,
    ProofCapabilityPolicy,
    ProofCatalog,
    ProofCatalogEntry,
    PytestNodeCapability,
    PythonCallCapability,
)
from faber.proof_executors import (
    ProcessCapture,
    ProofExecutionError,
    execute_catalog_entry,
    launch_bounded_process,
    resolve_catalog_path,
)
from faber.proof_runtime_helper import PROTOCOL_VERSION, ProtocolError, execute_payload
from faber.proof_workflow import (
    ProofExecutionPolicy,
    ProofWorkflowError,
    run_proof_workflow,
    workspace_snapshot_digest,
)
from faber.proofs import (
    ModelRunEvidence,
    ProofClaim,
    ProofEvidence,
    ProofPlan,
    ProofPolicy,
    ProofTemplateSelection,
    decide_proof,
    proof_authority_binding_digest,
)
from faber.receipts import VerificationReceipt
from faber.runner.local import LocalVerifierResult, RunnerPolicy
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec

CREATED_AT = "2026-07-17T00:00:00Z"
BASE_REVISION = "base-revision"
CANDIDATE_REVISION = "candidate-revision"
PATCH_DIGEST = sha256_digest("executor patch")
PROMPT_VERSION = "faber-proof-planner.v1"


def _task(*verifier_ids: str) -> TaskContract:
    return TaskContract(
        id="task-contract_executor-fixture",
        created_at=CREATED_AT,
        title="Execute bounded proofs",
        description="Exercise only repository-owner-approved proof capabilities.",
        requirements=["Every selected proof must produce authoritative evidence."],
        verifier_ids=list(verifier_ids),
    )


def _attempt(task: TaskContract, *, suffix: str = "main") -> Attempt:
    return Attempt(
        id=f"attempt_executor-{suffix}",
        created_at=CREATED_AT,
        task_contract_id=task.id,
        worker_id="worker.executor-fixture",
        base_revision=BASE_REVISION,
        candidate_revision=CANDIDATE_REVISION,
        summary="Implemented the candidate patch.",
        patch_digest=PATCH_DIGEST,
    )


def _model_run() -> ModelRunEvidence:
    return ModelRunEvidence(
        provider_adapter_id="adapter.openai.proof-planner",
        requested_model_id="gpt-5.6",
        returned_model_id="gpt-5.6-2026-07-01",
        response_id="resp_executor-fixture",
        prompt_template_version=PROMPT_VERSION,
        request_digest=sha256_digest("executor request"),
        structured_response_digest=sha256_digest("executor structured response"),
        response_schema_version="faber.openai.proof_planning_response.v1",
        mode="replay",
    )


def _claim(claim_id: str) -> ProofClaim:
    return ProofClaim(
        id=claim_id,
        statement=f"{claim_id} is demonstrated by its approved proof.",
        severity="high",
        requirement_refs=["requirement:0"],
        evidence_required=True,
        risk_rationale="Missing or contradictory evidence must fail closed.",
    )


def _selection(
    template_id: str,
    *,
    claim_id: str | None = None,
    version: str = "1",
    parameters: dict[str, object] | None = None,
) -> ProofTemplateSelection:
    resolved_claim_id = claim_id or f"claim.{template_id}"
    return ProofTemplateSelection(
        claim_id=resolved_claim_id,
        template_id=template_id,
        template_version=version,
        parameters=parameters or {},
        expected_behavior="The catalog-owned proof passes.",
        rationale="The approved capability directly covers this claim.",
    )


def _plan(
    task: TaskContract,
    attempt: Attempt,
    *,
    catalog_digest: str,
    selections: list[ProofTemplateSelection],
) -> ProofPlan:
    claims = [_claim(selection.claim_id) for selection in selections]
    return ProofPlan(
        task_contract_id=task.id,
        task_contract_digest=task.digest(),
        attempt_id=attempt.id,
        attempt_digest=attempt.digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        diff_digest=attempt.patch_digest,
        proof_catalog_digest=catalog_digest,
        prompt_template_version=PROMPT_VERSION,
        claims=claims,
        selections=selections,
        mandatory_claim_ids=[claim.id for claim in claims],
        mandatory_template_ids=[selection.template_id for selection in selections],
        uncovered_claim_ids=[],
        human_review_recommended=False,
        model_run=_model_run(),
    )


def _proof_policy(
    selections: list[ProofTemplateSelection],
    verifier_ids: list[str],
) -> ProofPolicy:
    return ProofPolicy(
        name="executor-fixture-policy",
        version="1",
        approved_verifier_ids=verifier_ids,
        mandatory_claim_ids=[selection.claim_id for selection in selections],
        mandatory_template_ids=[selection.template_id for selection in selections],
        mandatory_verifier_ids=verifier_ids,
        minimum_authoritative_outcomes=len(selections),
    )


def _registry(*specs: VerifierSpec) -> VerifierRegistry:
    registry = VerifierRegistry()
    for spec in specs:
        registry.register(spec)
    return registry


def _existing_spec(*, verifier_id: str = "verifier.existing") -> VerifierSpec:
    return VerifierSpec(
        id=f"verifier-spec_{verifier_id}",
        created_at=CREATED_AT,
        verifier_id=verifier_id,
        name="Existing verifier fixture",
        version="1",
        description="Runs one exact owner-approved command.",
        command_template=[sys.executable, "-c", "print('ok')"],
        allowed_timeout_seconds=5,
    )


def _object_schema(
    properties: dict[str, object] | None = None,
    *,
    required: list[str] | None = None,
) -> dict[str, object]:
    actual_properties = properties or {}
    actual_required = required or []
    return {
        "type": "object",
        "properties": actual_properties,
        "required": actual_required,
        "additionalProperties": False,
        "minProperties": len(actual_required),
        "maxProperties": len(actual_properties),
    }


def _capability_policy(
    spec: VerifierSpec,
    *,
    working_directory: str = ".",
    environment_variables: dict[str, str] | None = None,
    trusted_file_digests: dict[str, str] | None = None,
    timeout_seconds: int = 5,
    max_output_bytes: int = 4_096,
) -> ProofCapabilityPolicy:
    return ProofCapabilityPolicy(
        verifier_id=spec.verifier_id,
        verifier_version=spec.version,
        verifier_spec_digest=spec.digest(),
        working_directory=working_directory,
        environment_variables=environment_variables or {},
        trusted_file_digests=trusted_file_digests or {},
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
    )


def _entry(
    entry_id: str,
    capability: object,
    *,
    schema: dict[str, object] | None = None,
    defaults: dict[str, object] | None = None,
    version: str = "1",
) -> ProofCatalogEntry:
    return ProofCatalogEntry(
        id=entry_id,
        version=version,
        description=f"Owner-approved {entry_id} capability.",
        execution_parameter_schema=schema or _object_schema(),
        parameter_defaults=defaults or {},
        capability=capability,  # type: ignore[arg-type]
    )


def _existing_entry(
    *,
    entry_id: str = "proof.existing",
    verifier_id: str = "verifier.existing",
    environment_variables: dict[str, str] | None = None,
) -> tuple[ProofCatalogEntry, VerifierSpec]:
    spec = _existing_spec(verifier_id=verifier_id)
    capability = ExistingCommandCapability(
        _capability_policy(spec, environment_variables=environment_variables)
    )
    return _entry(entry_id, capability), spec


def _pytest_entry(
    repository_root: Path,
    *,
    entry_id: str = "proof.pytest",
    verifier_id: str = "verifier.pytest",
    node_id: str = "test_executor_node.py::test_node",
    environment_variables: dict[str, str] | None = None,
    timeout_seconds: int = 5,
    max_output_bytes: int = 4_096,
) -> tuple[ProofCatalogEntry, VerifierSpec]:
    spec = _existing_spec(verifier_id=verifier_id)
    node_path = node_id.split("::", 1)[0]
    capability = PytestNodeCapability(
        policy=_capability_policy(
            spec,
            environment_variables=environment_variables,
            trusted_file_digests={
                node_path: sha256_digest((repository_root / node_path).read_bytes())
            },
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        ),
        node_ids=[node_id],
    )
    return _entry(entry_id, capability), spec


def _python_entry(
    repository_root: Path,
    *,
    entry_id: str = "proof.python",
    verifier_id: str = "verifier.python",
    module: str = "proof_executor_fixture",
    callable_name: str = "echo",
    assertion: str = "equals",
    value_type: str = "integer",
    additional_trusted_paths: list[str] | None = None,
) -> tuple[ProofCatalogEntry, VerifierSpec]:
    spec = _existing_spec(verifier_id=verifier_id)
    module_parts = module.split(".")
    module_file = f"{module.replace('.', '/')}.py"
    trusted_paths = [
        "/".join((*module_parts[:index], "__init__.py")) for index in range(1, len(module_parts))
    ]
    trusted_paths.append(module_file)
    trusted_paths.extend(additional_trusted_paths or [])
    trusted_file_digests = {
        path: sha256_digest((repository_root / Path(path)).read_bytes()) for path in trusted_paths
    }
    scalar_schema: dict[str, object] = {"type": value_type}
    if value_type == "integer":
        scalar_schema.update({"minimum": -1_000, "maximum": 1_000})
    else:
        scalar_schema["maxLength"] = 256
    expected_schema = dict(scalar_schema)
    if assertion == "raises":
        if value_type != "string":
            raise AssertionError("raises fixtures require string inputs")
        expected_schema["enum"] = ["builtins.ValueError"]
    schema = _object_schema(
        {
            "inputs": {
                "type": "array",
                "items": scalar_schema,
                "minItems": 1,
                "maxItems": 4,
            },
            "expected": expected_schema,
        },
        required=["inputs", "expected"],
    )
    capability = PythonCallCapability(
        policy=_capability_policy(
            spec,
            trusted_file_digests=trusted_file_digests,
        ),
        module=module,
        callable_name=callable_name,
        module_file=module_file,
        positional_parameter="inputs",
        keyword_parameter=None,
        assertion_parameter=None,
        expected_parameter="expected",
        default_assertion=assertion,
        allowed_assertions=[assertion],
    )
    return _entry(entry_id, capability, schema=schema), spec


def _file_entry(
    *,
    entry_id: str = "proof.file",
    verifier_id: str = "verifier.file",
    repository_path: str = "evidence.txt",
    operation: str = "contains_literal",
) -> tuple[ProofCatalogEntry, VerifierSpec]:
    spec = _existing_spec(verifier_id=verifier_id)
    if operation in {"exists", "absent", "valid_json"}:
        schema = _object_schema()
        expected_parameter = None
        pointer_parameter = None
    elif operation == "json_pointer_equals":
        schema = _object_schema(
            {
                "expected": {"type": "string", "maxLength": 256},
                "json_pointer": {"type": "string", "maxLength": 256},
            },
            required=["expected", "json_pointer"],
        )
        expected_parameter = "expected"
        pointer_parameter = "json_pointer"
    else:
        schema = _object_schema(
            {"expected": {"type": "string", "maxLength": 256}},
            required=["expected"],
        )
        expected_parameter = "expected"
        pointer_parameter = None
    capability = FileInvariantCapability(
        policy=_capability_policy(spec),
        repository_path=repository_path,
        operation=operation,
        expected_parameter=expected_parameter,
        json_pointer_parameter=pointer_parameter,
    )
    return _entry(entry_id, capability, schema=schema), spec


def _artifact_entry(
    *,
    entry_id: str = "proof.artifact",
    verifier_id: str = "verifier.artifact",
    repository_path: str = "trajectory.json",
) -> tuple[ProofCatalogEntry, VerifierSpec]:
    spec = _existing_spec(verifier_id=verifier_id)
    capability = ArtifactValidatorCapability(
        policy=_capability_policy(spec),
        artifact_kind="trajectory",
        repository_path=repository_path,
    )
    return _entry(entry_id, capability), spec


def _execution_policy(
    root: Path,
    catalog: ProofCatalog,
    registry: VerifierRegistry,
    attempt: Attempt,
    *,
    allowed_environment_variables: list[str] | None = None,
    **overrides: object,
) -> ProofExecutionPolicy:
    values: dict[str, object] = {
        "allowed_repository_root": str(root),
        "allowed_catalog_digest": catalog.digest(),
        "verifier_registry_digest": registry.digest(),
        "expected_attempt_digest": attempt.digest(),
        "expected_workspace_digest": workspace_snapshot_digest(root),
        "maximum_obligations": 32,
        "per_obligation_timeout_seconds": 5,
        "total_timeout_seconds": 30,
        "max_input_bytes": 65_536,
        "max_output_bytes": 4_096,
        "allowed_environment_variables": allowed_environment_variables or [],
    }
    values.update(overrides)
    return ProofExecutionPolicy(**values)  # type: ignore[arg-type]


def _entry_runner_policy(
    root: Path,
    entry: ProofCatalogEntry,
    *,
    execution_policy: ProofExecutionPolicy | None = None,
) -> RunnerPolicy:
    capability_policy = entry.capability.policy
    allowed_environment_variables = {
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONHASHSEED",
        *capability_policy.environment_variables,
    }
    if execution_policy is not None:
        allowed = set(execution_policy.allowed_environment_variables)
        allowed_environment_variables.update(
            name
            for name in {"SYSTEMROOT", "WINDIR"}
            if name in allowed and os.environ.get(name) is not None
        )
    return RunnerPolicy(
        allowed_working_directory_root=str(root.resolve()),
        network_isolation=(
            execution_policy.isolation_disclosure
            if execution_policy is not None
            else "none-local-runner-does-not-isolate-network"
        ),
        allowed_environment_variables=sorted(allowed_environment_variables),
        timeout_seconds=capability_policy.timeout_seconds,
        max_capture_bytes=capability_policy.max_output_bytes,
        allow_shell=False,
    )


class RecordingLauncher:
    def __init__(
        self,
        *,
        exit_code: int | None = 0,
        stdout: bytes = b"",
        stderr: bytes = b"",
        timed_out: bool = False,
        stdout_truncated: bool = False,
        error: Exception | None = None,
    ) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.stdout_truncated = stdout_truncated
        self.error = error
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        argv: object,
        *,
        cwd: Path,
        environment: object,
        stdin: bytes | None,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> ProcessCapture:
        command = tuple(argv)  # type: ignore[arg-type]
        self.calls.append(
            {
                "argv": command,
                "cwd": cwd,
                "environment": dict(environment),  # type: ignore[arg-type]
                "stdin": stdin,
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": max_output_bytes,
            }
        )
        if self.error is not None:
            raise self.error
        return ProcessCapture(
            argv=command,
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            elapsed_seconds=0.01,
            timed_out=self.timed_out,
            stdout_truncated=self.stdout_truncated,
        )


class HelperLauncher(RecordingLauncher):
    def __call__(self, argv: object, **kwargs: Any) -> ProcessCapture:
        stdin = kwargs.get("stdin")
        assert isinstance(stdin, bytes)
        payload = json.loads(stdin.decode("utf-8"))
        module_name = payload["module"]
        assert isinstance(module_name, str)
        previously_loaded = sys.modules.pop(module_name, None)
        try:
            helper_result = execute_payload(payload)
        finally:
            sys.modules.pop(module_name, None)
            if previously_loaded is not None:
                sys.modules[module_name] = previously_loaded
        self.stdout = (
            json.dumps(helper_result, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        self.exit_code = 0 if helper_result["status"] in {"passed", "failed"} else 2
        return super().__call__(argv, **kwargs)


class RecordingRunner:
    def __init__(
        self,
        spec: VerifierSpec,
        *,
        passed: bool,
        timed_out: bool = False,
        error: Exception | None = None,
        runner_policy: RunnerPolicy | None = None,
    ) -> None:
        self.spec = spec
        self.passed = passed
        self.timed_out = timed_out
        self.error = error
        self.runner_policy = runner_policy
        self.runner_policy_digest = runner_policy.digest() if runner_policy is not None else None
        self.calls: list[dict[str, object]] = []

    def run(self, verifier_id: str, **kwargs: object) -> LocalVerifierResult:
        self.calls.append({"verifier_id": verifier_id, **kwargs})
        if self.error is not None:
            raise self.error
        working_directory = str(Path(str(kwargs["working_directory"])).resolve())
        metadata: dict[str, object] = {
            "approved_verifier_spec_digest": self.spec.digest(),
            "shell": False,
            "working_directory": working_directory,
        }
        if self.runner_policy is not None:
            metadata["runner_policy_digest"] = self.runner_policy.digest()
        run = VerifierRun(
            id="verifier-run_executor-fixture",
            created_at=CREATED_AT,
            verifier_id=self.spec.verifier_id,
            name=self.spec.name,
            version=self.spec.version,
            command=self.spec.command(),
            passed=self.passed,
            metrics={"timed_out": self.timed_out},
            failure_reasons=[] if self.passed else ["fixture failure"],
            logs_digest=sha256_digest("executor fixture logs"),
            metadata=metadata,
        )
        return LocalVerifierResult(
            verifier_run=run,
            stdout_digest=sha256_digest(b""),
            stderr_digest=sha256_digest(b""),
            elapsed_seconds=0.01,
            exit_code=0 if self.passed else 1,
            timed_out=self.timed_out,
        )


def test_catalog_and_capability_digests_are_stable_and_order_independent() -> None:
    existing, _ = _existing_entry()
    file_entry, _ = _file_entry()
    left = ProofCatalog([existing, file_entry])
    right = ProofCatalog([file_entry, existing])
    same_existing, _ = _existing_entry()
    changed_existing, _ = _existing_entry(environment_variables={"MODE": "strict"})

    assert left.digest() == right.digest()
    assert left.canonical_bytes() == right.canonical_bytes()
    assert existing.capability_digest() == same_existing.capability_digest()
    assert existing.capability_digest() != changed_existing.capability_digest()
    assert existing.planner_view().capability_digest == existing.capability_digest()
    assert "command_template" not in json.dumps(existing.planner_view().to_dict())


def test_catalog_rejects_duplicate_and_stale_active_entries() -> None:
    entry, _ = _existing_entry()

    with pytest.raises(ValidationError, match="duplicate"):
        ProofCatalog([entry, entry])
    with pytest.raises(ValidationError, match="one active version"):
        ProofCatalog([entry, replace(entry, version="2")])

    catalog = ProofCatalog([entry])
    with pytest.raises(ValidationError, match="stale version"):
        catalog.resolve(entry.id, "2")


def test_required_parameters_and_owner_defaults_are_closed_and_revalidated() -> None:
    base_entry, _ = _existing_entry()
    schema = _object_schema(
        {
            "case": {"type": "string", "enum": ["empty", "unicode"], "maxLength": 16},
            "serializer": {"type": "string", "enum": ["json"], "maxLength": 8},
        },
        required=["case"],
    )
    entry = _entry(
        "proof.parameters",
        base_entry.capability,
        schema=schema,
        defaults={"serializer": "json"},
    )

    assert entry.validate_parameters({"case": "empty"}) == {"case": "empty"}
    assert dict(entry.bind_parameters({"case": "unicode"})) == {
        "case": "unicode",
        "serializer": "json",
    }
    assert set(entry.planner_view().parameter_schema_dict()["properties"]) == {"case"}
    with pytest.raises(ValidationError):
        entry.validate_parameters({})
    with pytest.raises(ValidationError):
        entry.validate_parameters({"case": "empty", "unknown": True})
    with pytest.raises(ValidationError, match="cannot override"):
        entry.bind_parameters({"case": "empty", "serializer": "yaml"})
    with pytest.raises(ValidationError):
        entry.validate_parameters({"case": "x" * 17})


@pytest.mark.parametrize(
    "schema,defaults",
    [
        (
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
                "minProperties": 0,
                "maxProperties": 0,
            },
            {},
        ),
        (
            _object_schema({"optional": {"type": "boolean"}}, required=[]),
            {},
        ),
        (
            {
                "type": "object",
                "properties": {},
                "required": ["missing"],
                "additionalProperties": False,
                "minProperties": 0,
                "maxProperties": 0,
            },
            {},
        ),
        (
            _object_schema(
                {"command": {"type": "string", "maxLength": 32}},
                required=["command"],
            ),
            {},
        ),
    ],
)
def test_malformed_or_operational_parameter_schemas_are_rejected(
    schema: dict[str, object],
    defaults: dict[str, object],
) -> None:
    base_entry, _ = _existing_entry()

    with pytest.raises(ValidationError):
        _entry(
            "proof.malformed-schema",
            base_entry.capability,
            schema=schema,
            defaults=defaults,
        )


def test_raises_capability_rejects_unqualified_exception_names(tmp_path: Path) -> None:
    _write_python_fixture(tmp_path)
    module_path = tmp_path / "proof_executor_fixture.py"
    spec = _existing_spec(verifier_id="verifier.python.raises")
    capability = PythonCallCapability(
        policy=_capability_policy(
            spec,
            trusted_file_digests={
                module_path.name: sha256_digest(module_path.read_bytes()),
            },
        ),
        module="proof_executor_fixture",
        callable_name="raise_value_error",
        positional_parameter="inputs",
        keyword_parameter=None,
        assertion_parameter=None,
        expected_parameter="expected",
        default_assertion="raises",
        allowed_assertions=["raises"],
    )
    schema = _object_schema(
        {
            "inputs": {
                "type": "array",
                "items": {"type": "string", "maxLength": 32},
                "minItems": 1,
                "maxItems": 1,
            },
            "expected": {
                "type": "string",
                "enum": ["ValueError"],
                "maxLength": 32,
            },
        },
        required=["inputs", "expected"],
    )

    with pytest.raises(ValidationError, match="approved exception types"):
        _entry("proof.python.raises", capability, schema=schema)


def test_selection_constructor_rejects_an_explicit_command_field() -> None:
    with pytest.raises(ValidationError, match="executable-looking"):
        _selection("proof.existing", parameters={"command": "python attacker.py"})


@pytest.mark.parametrize(
    "location",
    [
        "/etc/passwd",
        "../outside.txt",
        "nested/../../outside.txt",
        "C:/outside.txt",
        "C:outside.txt",
        "//server/share/file.txt",
        "\\\\server\\share\\file.txt",
        "nested\\file.txt",
    ],
)
def test_catalog_path_rejects_absolute_traversal_unc_drive_and_backslash_forms(
    tmp_path: Path,
    location: str,
) -> None:
    with pytest.raises(ProofExecutionError) as captured:
        resolve_catalog_path(tmp_path, location)

    assert captured.value.code == "invalid_path"


def test_catalog_path_rejects_a_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    repository.mkdir()
    outside.mkdir()
    (outside / "evidence.txt").write_text("outside", encoding="utf-8")
    link = repository / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        escaped_candidate = repository / "escape" / "evidence.txt"
        original_resolve = Path.resolve

        def resolve_with_simulated_symlink(
            path: Path,
            strict: bool = False,
        ) -> Path:
            if path == escaped_candidate:
                return (outside / "evidence.txt").resolve(strict=True)
            return original_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", resolve_with_simulated_symlink)

    with pytest.raises(ProofExecutionError) as captured:
        resolve_catalog_path(repository, "escape/evidence.txt", must_exist=True)

    assert captured.value.code == "invalid_path"


def test_bounded_process_launcher_uses_no_shell_and_exact_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    class FakeProcess:
        def __init__(self, argv: list[str], **kwargs: object) -> None:
            observed["argv"] = tuple(argv)
            observed.update(kwargs)
            self.stdout = io.BytesIO(b"ok")
            self.stderr = io.BytesIO(b"")
            self.stdin = None
            self.returncode = 0

        def wait(self, timeout: int | None = None) -> int:
            observed["timeout"] = timeout
            return self.returncode

        def kill(self) -> None:
            observed["killed"] = True

    monkeypatch.setattr("faber.proof_executors.subprocess.Popen", FakeProcess)

    capture = launch_bounded_process(
        [sys.executable, "--version"],
        cwd=tmp_path.resolve(),
        environment={"SAFE_FIXED": "1"},
        stdin=None,
        timeout_seconds=2,
        max_output_bytes=32,
    )

    assert observed["shell"] is False
    assert observed["env"] == {"SAFE_FIXED": "1"}
    assert observed["cwd"] == tmp_path.resolve()
    assert capture.stdout == b"ok"
    assert capture.output_truncated is False


def test_pytest_executor_uses_fixed_argv_and_minimal_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(
        tmp_path,
        environment_variables={"SAFE_FIXED": "1"},
    )
    registry = _registry(spec)
    launcher = RecordingLauncher(exit_code=0, stdout=b"1 passed")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross-the-boundary")
    monkeypatch.setenv("UNRELATED_PARENT_VALUE", "also-must-not-cross")

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=registry,
        launcher=launcher,
        allowed_environment_variables=["SAFE_FIXED"],
    )

    assert result.status == "passed"
    assert len(launcher.calls) == 1
    call = launcher.calls[0]
    argv = call["argv"]
    assert isinstance(argv, tuple)
    assert argv[:4] == (
        sys.executable,
        "-I",
        "-B",
        "-X",
    )
    pycache_option = argv[4]
    assert isinstance(pycache_option, str)
    assert pycache_option.startswith("pycache_prefix=")
    pycache_root = Path(pycache_option.removeprefix("pycache_prefix="))
    assert pycache_root.name == "pycache"
    assert pycache_root.parent.name.startswith("faber-proof-runtime-")
    assert pycache_root.exists() is False
    assert argv[5:8] == (
        "-m",
        "pytest",
        "-c",
    )
    config_path = Path(argv[8])
    assert config_path.name == "pytest.ini"
    assert config_path.parent == pycache_root.parent
    assert config_path.exists() is False
    assert argv[9:] == (
        "--noconftest",
        "-p",
        "no:cacheprovider",
        "--quiet",
        "--",
        "test_executor_node.py::test_node",
    )
    environment = call["environment"]
    assert isinstance(environment, dict)
    assert environment["SAFE_FIXED"] == "1"
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert environment["PYTHONHASHSEED"] == "0"
    assert "OPENAI_API_KEY" not in environment
    assert "UNRELATED_PARENT_VALUE" not in environment
    assert set(environment) <= {
        "SAFE_FIXED",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONHASHSEED",
        "PYTEST_ADDOPTS",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "PYTEST_PLUGINS",
        "SYSTEMROOT",
        "WINDIR",
    }
    assert call["stdin"] is None


def test_pytest_executor_ignores_adjacent_unchecked_hash_bytecode(tmp_path: Path) -> None:
    source = tmp_path / "test_executor_node.py"
    source.write_text("def test_node():\n    assert True\n", encoding="utf-8")
    py_compile.compile(
        str(source),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    source.write_text("def test_node():\n    assert False\n", encoding="utf-8")
    entry, spec = _pytest_entry(tmp_path)
    captures: list[ProcessCapture] = []

    def recording_launcher(*args: Any, **kwargs: Any) -> ProcessCapture:
        capture = launch_bounded_process(*args, **kwargs)
        captures.append(capture)
        return capture

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=recording_launcher,
    )

    assert captures[0].exit_code == 1, (captures[0].stdout + captures[0].stderr).decode(
        errors="replace"
    )
    assert result.status == "failed"
    assert result.reason_codes == ("pytest_failed",)


@pytest.mark.parametrize(("passed", "expected_status"), [(True, "passed"), (False, "failed")])
def test_existing_command_family_passes_and_fails_authoritatively(
    tmp_path: Path,
    passed: bool,
    expected_status: str,
) -> None:
    entry, spec = _existing_entry()
    runner_policy = _entry_runner_policy(tmp_path, entry)
    runner = RecordingRunner(spec, passed=passed, runner_policy=runner_policy)

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        runner=runner,
        runner_policy=runner_policy,
    )

    assert result.status == expected_status
    assert result.verifier_run is not None
    assert result.verifier_run.passed is passed
    assert result.verifier_run.verifier_id == spec.verifier_id
    assert len(runner.calls) == 1


def test_existing_command_output_overflow_cannot_become_authoritative(
    tmp_path: Path,
) -> None:
    entry, spec = _existing_entry()
    runner_policy = _entry_runner_policy(tmp_path, entry)

    class OverflowingRunner(RecordingRunner):
        def run(self, verifier_id: str, **kwargs: object) -> LocalVerifierResult:
            result = super().run(verifier_id, **kwargs)
            return replace(
                result,
                stdout_truncated=True,
                stdout_overflow=True,
                error_code=None,
            )

    runner = OverflowingRunner(spec, passed=True, runner_policy=runner_policy)

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        runner=runner,
        runner_policy=runner_policy,
    )

    assert result.status == "error"
    assert result.reason_codes == ("output_limit",)
    assert result.verifier_run is None
    assert result.output_truncated is True


@pytest.mark.parametrize(("exit_code", "expected_status"), [(0, "passed"), (1, "failed")])
def test_pytest_node_family_passes_and_fails_exact_nodes(
    tmp_path: Path,
    exit_code: int,
    expected_status: str,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    launcher = RecordingLauncher(exit_code=exit_code)

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=launcher,
    )

    assert result.status == expected_status
    assert result.verifier_run is not None
    assert result.verifier_run.command[-2:] == ["--", "test_executor_node.py::test_node"]
    assert result.verifier_run.metadata["shell"] is False


@pytest.mark.parametrize(("expected", "expected_status"), [(7, "passed"), (8, "failed")])
def test_python_call_family_passes_and_fails_through_the_fixed_helper(
    tmp_path: Path,
    expected: int,
    expected_status: str,
) -> None:
    _write_python_fixture(tmp_path)
    entry, spec = _python_entry(tmp_path)
    launcher = HelperLauncher()

    result = execute_catalog_entry(
        entry,
        {"inputs": [7], "expected": expected},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=launcher,
    )

    assert result.status == expected_status
    assert result.verifier_run is not None
    assert result.verifier_run.command[1:3] == [
        "-I",
        str(Path("src/faber/proof_runtime_helper.py").resolve()),
    ]
    assert len(launcher.calls) == 1
    payload = json.loads(launcher.calls[0]["stdin"])
    assert payload["module"] == "proof_executor_fixture"
    assert payload["callable_name"] == "echo"
    assert payload["positional_arguments"] == [7]


def test_python_call_family_accepts_only_catalog_approved_exception_types(
    tmp_path: Path,
) -> None:
    _write_python_fixture(tmp_path)
    entry, spec = _python_entry(
        tmp_path,
        assertion="raises",
        callable_name="raise_value_error",
        value_type="string",
    )
    launcher = HelperLauncher()

    result = execute_catalog_entry(
        entry,
        {"inputs": ["ignored"], "expected": "builtins.ValueError"},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=launcher,
    )

    assert result.status == "passed"
    assert result.verifier_run is not None
    payload = json.loads(launcher.calls[0]["stdin"])
    assert payload["assertion"] == "raises"
    assert payload["expected"] == "builtins.ValueError"


@pytest.mark.parametrize(
    ("expected", "expected_status"),
    [("approved literal", "passed"), ("missing literal", "failed")],
)
def test_file_invariant_family_passes_and_fails(
    tmp_path: Path,
    expected: str,
    expected_status: str,
) -> None:
    (tmp_path / "evidence.txt").write_text("the approved literal is present", encoding="utf-8")
    entry, spec = _file_entry()

    result = execute_catalog_entry(
        entry,
        {"expected": expected},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
    )

    assert result.status == expected_status
    assert result.verifier_run is not None
    assert result.verifier_run.metadata["family"] == "file-invariant"


@pytest.mark.parametrize(
    ("document_value", "expected_schema", "expected", "expected_status"),
    [
        (1, {"type": "integer", "minimum": 0, "maximum": 10}, 1, "passed"),
        (1, {"type": "boolean"}, True, "failed"),
        (1.0, {"type": "integer", "minimum": 0, "maximum": 10}, 1, "failed"),
        (
            [1],
            {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 10},
                "minItems": 1,
                "maxItems": 2,
            },
            [1],
            "passed",
        ),
        (
            {"items": [1]},
            {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 10},
                        "minItems": 1,
                        "maxItems": 2,
                    }
                },
                "required": ["items"],
                "additionalProperties": False,
                "minProperties": 1,
                "maxProperties": 1,
            },
            {"items": [1]},
            "passed",
        ),
    ],
)
def test_json_pointer_invariant_preserves_exact_json_types(
    tmp_path: Path,
    document_value: object,
    expected_schema: dict[str, object],
    expected: object,
    expected_status: str,
) -> None:
    (tmp_path / "evidence.json").write_text(
        json.dumps({"value": document_value}),
        encoding="utf-8",
    )
    spec = _existing_spec(verifier_id="verifier.file.pointer")
    capability = FileInvariantCapability(
        policy=_capability_policy(spec),
        repository_path="evidence.json",
        operation="json_pointer_equals",
        expected_parameter="expected",
        json_pointer_parameter="json_pointer",
    )
    entry = _entry(
        "proof.file.pointer",
        capability,
        schema=_object_schema(
            {
                "expected": expected_schema,
                "json_pointer": {"type": "string", "maxLength": 64},
            },
            required=["expected", "json_pointer"],
        ),
    )

    result = execute_catalog_entry(
        entry,
        {"expected": expected, "json_pointer": "/value"},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
    )

    assert result.status == expected_status


@pytest.mark.parametrize(("valid", "expected_status"), [(True, "passed"), (False, "failed")])
def test_artifact_validator_family_passes_and_fails(
    tmp_path: Path,
    valid: bool,
    expected_status: str,
) -> None:
    destination = tmp_path / "trajectory.json"
    if valid:
        shutil.copyfile(
            Path("tests/fixtures/golden/trajectory-human-reviewed.json"),
            destination,
        )
    else:
        destination.write_text("{not valid JSON", encoding="utf-8")
    entry, spec = _artifact_entry()

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
    )

    assert result.status == expected_status
    assert result.verifier_run is not None
    assert result.verifier_run.metadata["family"] == "artifact-validator"


@pytest.mark.parametrize("field", ["module", "callable", "test_node", "location"])
def test_operational_field_injection_is_rejected_before_launch(
    tmp_path: Path,
    field: str,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofExecutionError) as captured:
        execute_catalog_entry(
            entry,
            {field: "attacker-controlled"},
            repository_root=tmp_path,
            verifier_registry=_registry(spec),
            launcher=launcher,
        )

    assert captured.value.code == "invalid_parameters"
    assert launcher.calls == []


def test_oversized_parameter_is_rejected_before_launch(tmp_path: Path) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    base_entry, spec = _pytest_entry(tmp_path)
    entry = _entry(
        "proof.pytest-with-label",
        base_entry.capability,
        schema=_object_schema(
            {"label": {"type": "string", "maxLength": 4}},
            required=["label"],
        ),
    )
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofExecutionError) as captured:
        execute_catalog_entry(
            entry,
            {"label": "oversized"},
            repository_root=tmp_path,
            verifier_registry=_registry(spec),
            launcher=launcher,
        )

    assert captured.value.code == "invalid_parameters"
    assert launcher.calls == []


@pytest.mark.parametrize("family", ["pytest-node", "python-call"])
def test_oversized_owner_pinned_source_is_rejected_before_launch(
    tmp_path: Path,
    family: str,
) -> None:
    if family == "pytest-node":
        (tmp_path / "test_executor_node.py").write_text(
            "def test_node():\n    assert True\n" + ("# padding\n" * 32),
            encoding="utf-8",
        )
        entry, spec = _pytest_entry(tmp_path)
        parameters: dict[str, object] = {}
    else:
        module_name = "oversized_proof_fixture"
        (tmp_path / f"{module_name}.py").write_text(
            "def echo(value):\n    return value\n" + ("# padding\n" * 32),
            encoding="utf-8",
        )
        entry, spec = _python_entry(tmp_path, module=module_name)
        parameters = {"inputs": [7], "expected": 7}
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofExecutionError) as captured:
        execute_catalog_entry(
            entry,
            parameters,
            repository_root=tmp_path,
            verifier_registry=_registry(spec),
            launcher=launcher,
            max_input_bytes=64,
        )

    assert captured.value.code == "input_limit"
    assert launcher.calls == []


def test_failing_python_call_emits_a_bounded_redacted_counterexample(tmp_path: Path) -> None:
    _write_python_fixture(tmp_path)
    secret = "sk-proj-AAAAAAAAAAAAAAAAAAAAAAAA"
    entry, spec = _python_entry(tmp_path, value_type="string")

    result = execute_catalog_entry(
        entry,
        {"inputs": [secret], "expected": "different"},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=HelperLauncher(),
    )
    serialized = json.dumps(result.counterexample_summary, sort_keys=True)

    assert result.status == "failed"
    assert isinstance(result.counterexample_summary, dict)
    assert set(result.counterexample_summary) == {
        "input_summary",
        "expected_summary",
        "observed_summary",
        "exception_type",
        "reason_code",
    }
    assert result.counterexample_summary["reason_code"] == "assertion_failed"
    assert secret not in serialized
    assert "[redacted]" in serialized
    assert len(serialized.encode("utf-8")) < 16_384


@pytest.mark.parametrize(
    ("launcher", "reason_code"),
    [
        (RecordingLauncher(exit_code=None, timed_out=True), "timeout"),
        (RecordingLauncher(exit_code=0, stdout=b"x" * 32, stdout_truncated=True), "output_limit"),
    ],
)
def test_timeout_and_output_cap_are_terminal_executor_errors(
    tmp_path: Path,
    launcher: RecordingLauncher,
    reason_code: str,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
        launcher=launcher,
    )

    assert result.status == "error"
    assert result.reason_codes == (reason_code,)
    assert result.verifier_run is not None
    assert result.verifier_run.passed is False


def test_python_executor_rejects_unapproved_helper_reason_without_persisting_it(
    tmp_path: Path,
) -> None:
    secret_reason = "sk-proj-AAAAAAAAAAAAAAAAAAAAAAAA"
    helper_payload = {
        "protocol": PROTOCOL_VERSION,
        "status": "failed",
        "reason_code": secret_reason,
        "input_summary": {"type": "integer", "value": 7},
        "expected_summary": {"type": "integer", "value": 8},
        "observed_summary": {"type": "integer", "value": 7},
        "exception_type": None,
    }
    launcher = RecordingLauncher(
        exit_code=0,
        stdout=(json.dumps(helper_payload, sort_keys=True) + "\n").encode("utf-8"),
    )
    _write_python_fixture(tmp_path)
    entry, spec = _python_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id, parameters={"inputs": [7], "expected": 8})
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])

    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([selection], [spec.verifier_id]),
        execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
        launcher=launcher,
    )
    persisted = json.dumps(result.to_dict(), sort_keys=True)

    assert len(launcher.calls) == 1
    assert result.evidence[0].status == "error"
    assert result.evidence[0].failure_reason_codes == ("operational_error",)
    assert result.verifier_runs == ()
    assert result.verification_receipts == ()
    assert result.decision.verdict == "human_review"
    assert secret_reason not in persisted


def test_bounded_launcher_closes_a_pipe_that_outlives_the_exited_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import faber.proof_executors as executor_module

    grace_seconds = 0.02

    class BlockingStream:
        def __init__(self) -> None:
            self.entered = threading.Event()
            self.released = threading.Event()
            self.finished = threading.Event()

        def read(self, _size: int) -> bytes:
            self.entered.set()
            self.released.wait()
            self.finished.set()
            return b""

        def close(self) -> None:
            self.released.set()

    blocking_stdout = BlockingStream()

    class ExitedProcessWithInheritedPipe:
        def __init__(self, _argv: list[str], **_kwargs: object) -> None:
            self.stdout = blocking_stdout
            self.stderr = io.BytesIO(b"")
            self.stdin = None
            self.returncode = 0

        def wait(self, timeout: int | None = None) -> int:
            assert timeout is not None
            return self.returncode

        def kill(self) -> None:
            raise AssertionError("an already-exited parent must not be killed")

    monkeypatch.setattr(executor_module, "PROCESS_PIPE_DRAIN_GRACE_SECONDS", grace_seconds)
    monkeypatch.setattr(executor_module.subprocess, "Popen", ExitedProcessWithInheritedPipe)

    started = time.perf_counter()
    capture = launch_bounded_process(
        [sys.executable, "--version"],
        cwd=tmp_path.resolve(),
        environment={},
        stdin=None,
        timeout_seconds=2,
        max_output_bytes=32,
    )
    elapsed = time.perf_counter() - started

    assert blocking_stdout.entered.is_set()
    assert blocking_stdout.finished.wait(timeout=0.5)
    assert elapsed < grace_seconds + 0.25
    assert capture.exit_code == 0
    assert capture.timed_out is False
    assert capture.stdout_truncated is False
    assert capture.stdout_capture_incomplete is True
    assert capture.capture_incomplete is True


def test_bounded_launcher_pipe_read_error_cannot_authorize_pytest_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import faber.proof_executors as executor_module

    class FailingStream:
        def __init__(self) -> None:
            self.reads = 0

        def read(self, _size: int) -> bytes:
            self.reads += 1
            if self.reads == 1:
                return b"partial"
            raise OSError("simulated read failure")

        def close(self) -> None:
            return None

    failing_stdout = FailingStream()

    class ExitedProcessWithBrokenPipe:
        def __init__(self, _argv: list[str], **_kwargs: object) -> None:
            self.stdout = failing_stdout
            self.stderr = io.BytesIO(b"")
            self.stdin = None
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None
            return self.returncode

        def kill(self) -> None:
            raise AssertionError("an already-exited child must not be killed")

    monkeypatch.setattr(executor_module.subprocess, "Popen", ExitedProcessWithBrokenPipe)
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)

    result = execute_catalog_entry(
        entry,
        {},
        repository_root=tmp_path,
        verifier_registry=_registry(spec),
    )

    assert failing_stdout.reads == 2
    assert result.status == "error"
    assert result.reason_codes == ("output_capture_incomplete",)
    assert result.verifier_run is not None
    assert result.verifier_run.passed is False


def test_passing_workflow_binds_evidence_runs_receipts_and_all_authority_context(
    tmp_path: Path,
) -> None:
    (tmp_path / "evidence.txt").write_text("approved literal", encoding="utf-8")
    entry, spec = _file_entry()
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id, parameters={"expected": "approved literal"})
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    proof_policy = _proof_policy([selection], [spec.verifier_id])
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)

    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=proof_policy,
        execution_policy=execution_policy,
    )

    assert result.decision.verdict == "pass"
    assert result.decision.reason_codes == ("proof_passed",)
    assert result.catalog_digest == catalog.digest() == plan.proof_catalog_digest
    assert result.verifier_registry_digest == registry.digest()
    assert result.workspace_digest == execution_policy.expected_workspace_digest
    assert (
        len(result.evidence) == len(result.verifier_runs) == len(result.verification_receipts) == 1
    )
    evidence = result.evidence[0]
    run = result.verifier_runs[0]
    receipt = result.verification_receipts[0]
    assert evidence.proof_plan_digest == plan.digest()
    assert evidence.claim_id == selection.claim_id
    assert evidence.selection_digest == selection.digest()
    assert evidence.verifier_run_digest == run.digest()
    assert evidence.verification_receipt_digest == receipt.digest()
    assert run.metadata["workspace_digest"] == execution_policy.expected_workspace_digest
    assert run.metadata["execution_policy_digest"] == execution_policy.digest()
    assert receipt.task_contract_id == task.id
    assert receipt.task_contract_digest == task.digest()
    assert receipt.attempt_id == attempt.id
    assert receipt.base_revision == attempt.base_revision
    assert receipt.candidate_revision == attempt.candidate_revision
    assert receipt.verifier_digest == run.verifier_digest()
    assert receipt.result_digest == run.result_digest()
    assert result.execution_order == (selection.digest(),)
    workflow_digest = result.digest()
    diagnostic_reasons = result.diagnostics[0]["reason_codes"]
    assert isinstance(diagnostic_reasons, tuple)
    with pytest.raises(AttributeError):
        diagnostic_reasons.append("forged_reason")  # type: ignore[attr-defined]
    thawed = result.to_dict()
    thawed_diagnostics = thawed["diagnostics"]
    assert isinstance(thawed_diagnostics, list)
    assert result.digest() == workflow_digest


def test_direct_executor_run_without_plan_selection_metadata_cannot_authorize_replay(
    tmp_path: Path,
) -> None:
    (tmp_path / "evidence.txt").write_text("approved literal", encoding="utf-8")
    entry, spec = _file_entry()
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id, parameters={"expected": "approved literal"})
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    policy = _proof_policy([selection], [spec.verifier_id])

    execution = execute_catalog_entry(
        entry,
        {"expected": "approved literal"},
        repository_root=tmp_path,
        verifier_registry=registry,
    )
    run = execution.verifier_run
    assert run is not None
    assert execution.status == "passed"
    receipt = VerificationReceipt.from_verifier_run(task, attempt, run)
    evidence = ProofEvidence(
        proof_plan_digest=plan.digest(),
        claim_id=selection.claim_id,
        selection_digest=selection.digest(),
        status="passed",
        verifier_id=run.verifier_id,
        verifier_version=run.version,
        verifier_run_digest=run.digest(),
        verification_receipt_digest=receipt.digest(),
        expected_summary=execution.expected_summary,
        observed_summary=execution.observed_summary,
        counterexample_summary=None,
        failure_reason_codes=[],
    )

    decision = decide_proof(
        plan,
        [evidence],
        policy,
        task_contract=task,
        attempt=attempt,
        verifier_runs=[run],
        verification_receipts=[receipt],
    )

    assert decision.verdict == "human_review"
    assert "verifier_run_binding_mismatch" in decision.reason_codes


def test_stale_executor_run_cannot_satisfy_current_mandatory_verifier(
    tmp_path: Path,
) -> None:
    (tmp_path / "evidence.txt").write_text("approved literal", encoding="utf-8")
    stale_entry, stale_spec = _file_entry(
        entry_id="proof.file.stale",
        verifier_id="verifier.file.stale",
    )
    current_entry, current_spec = _file_entry(
        entry_id="proof.file.current",
        verifier_id="verifier.file.current",
    )
    catalog = ProofCatalog([stale_entry, current_entry])
    registry = _registry(stale_spec, current_spec)
    stale_selection = _selection(
        stale_entry.id,
        claim_id="claim.file.stale",
        parameters={"expected": "approved literal"},
    )
    current_selection = _selection(
        current_entry.id,
        claim_id="claim.file.current",
        parameters={"expected": "approved literal"},
    )
    task = _task(stale_spec.verifier_id, current_spec.verifier_id)
    attempt = _attempt(task)
    stale_plan = _plan(
        task,
        attempt,
        catalog_digest=catalog.digest(),
        selections=[stale_selection],
    )
    current_plan = _plan(
        task,
        attempt,
        catalog_digest=catalog.digest(),
        selections=[current_selection],
    )
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)

    stale_result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=stale_plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([stale_selection], [stale_spec.verifier_id]),
        execution_policy=execution_policy,
    )
    current_result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=current_plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([current_selection], [current_spec.verifier_id]),
        execution_policy=execution_policy,
    )
    decision = decide_proof(
        current_plan,
        current_result.evidence,
        _proof_policy(
            [current_selection],
            [stale_spec.verifier_id, current_spec.verifier_id],
        ),
        task_contract=task,
        attempt=attempt,
        verifier_runs=[*current_result.verifier_runs, *stale_result.verifier_runs],
        verification_receipts=[
            *current_result.verification_receipts,
            *stale_result.verification_receipts,
        ],
    )

    assert decision.verdict == "human_review"
    assert "verifier_run_binding_mismatch" in decision.reason_codes
    assert "mandatory_verifier_evidence_missing" in decision.reason_codes


def test_receipt_rejects_metadata_only_relabeling_to_another_plan(tmp_path: Path) -> None:
    (tmp_path / "evidence.txt").write_text("approved literal", encoding="utf-8")
    first, spec = _file_entry(entry_id="proof.file.first")
    second, duplicate_spec = _file_entry(entry_id="proof.file.second")
    assert duplicate_spec.digest() == spec.digest()
    catalog = ProofCatalog([first, second])
    registry = _registry(spec)
    first_selection = _selection(
        first.id,
        claim_id="claim.file.first",
        parameters={"expected": "approved literal"},
    )
    second_selection = _selection(
        second.id,
        claim_id="claim.file.second",
        parameters={"expected": "approved literal"},
    )
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    first_plan = _plan(
        task,
        attempt,
        catalog_digest=catalog.digest(),
        selections=[first_selection],
    )
    second_plan = _plan(
        task,
        attempt,
        catalog_digest=catalog.digest(),
        selections=[second_selection],
    )
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)
    first_result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=first_plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([first_selection], [spec.verifier_id]),
        execution_policy=execution_policy,
    )
    run = first_result.verifier_runs[0]
    receipt = first_result.verification_receipts[0]
    forged_metadata = dict(run.metadata)
    forged_binding = proof_authority_binding_digest(
        task_contract_digest=task.digest(),
        attempt_digest=attempt.digest(),
        proof_plan_digest=second_plan.digest(),
        selection_digest=second_selection.digest(),
        catalog_digest=catalog.digest(),
        catalog_entry_id=second.id,
        catalog_entry_version=second.version,
        family=second.family,
        capability_digest=second.capability_digest(),
        execution_policy_digest=execution_policy.digest(),
        workspace_digest=execution_policy.expected_workspace_digest,
        verifier_id=run.verifier_id,
        verifier_version=run.version,
        raw_verifier_run_digest=forged_metadata["raw_verifier_run_digest"],
        raw_verifier_run_id=forged_metadata["raw_verifier_run_id"],
    )
    forged_metadata.update(
        {
            "proof_plan_digest": second_plan.digest(),
            "selection_digest": second_selection.digest(),
            "catalog_entry_id": second.id,
            "catalog_entry_version": second.version,
            "capability_digest": second.capability_digest(),
            "proof_authority_binding_digest": forged_binding,
        }
    )
    forged_run = replace(run, metadata=forged_metadata)
    forged_evidence = ProofEvidence(
        proof_plan_digest=second_plan.digest(),
        claim_id=second_selection.claim_id,
        selection_digest=second_selection.digest(),
        status="passed",
        verifier_id=forged_run.verifier_id,
        verifier_version=forged_run.version,
        verifier_run_digest=forged_run.digest(),
        verification_receipt_digest=receipt.digest(),
        expected_summary={"contains": True},
        observed_summary={"contains": True},
        counterexample_summary=None,
        failure_reason_codes=[],
    )
    assert receipt.result_digest == forged_run.result_digest()

    decision = decide_proof(
        second_plan,
        [forged_evidence],
        _proof_policy([second_selection], [spec.verifier_id]),
        task_contract=task,
        attempt=attempt,
        verifier_runs=[forged_run],
        verification_receipts=[receipt],
    )

    assert decision.verdict == "human_review"
    assert "verifier_run_binding_mismatch" in decision.reason_codes


def test_one_raw_verifier_run_cannot_authorize_two_proof_selections(
    tmp_path: Path,
) -> None:
    first, spec = _existing_entry(entry_id="proof.existing.first")
    second, duplicate_spec = _existing_entry(entry_id="proof.existing.second")
    assert duplicate_spec.digest() == spec.digest()
    catalog = ProofCatalog([first, second])
    registry = _registry(spec)
    selections = [
        _selection(first.id, claim_id="claim.existing.first"),
        _selection(second.id, claim_id="claim.existing.second"),
    ]
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)
    runner = RecordingRunner(
        spec,
        passed=True,
        runner_policy=_entry_runner_policy(
            tmp_path,
            first,
            execution_policy=execution_policy,
        ),
    )

    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy(selections, [spec.verifier_id]),
        execution_policy=execution_policy,
        runner=runner,
    )

    assert len(runner.calls) == 2
    assert [item.status for item in result.evidence] == ["passed", "error"]
    assert result.evidence[1].failure_reason_codes == ("authoritative_run_reused",)
    assert len(result.verifier_runs) == 1
    assert len(result.verification_receipts) == 1
    assert result.decision.verdict != "pass"


def test_workspace_digest_mismatch_is_rejected_before_launch(tmp_path: Path) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id)
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)
    initial_digest = execution_policy.expected_workspace_digest
    (tmp_path / "candidate-mutation.txt").write_text("changed\n", encoding="utf-8")
    launcher = RecordingLauncher(exit_code=0)

    assert workspace_snapshot_digest(tmp_path) != initial_digest
    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy([selection], [spec.verifier_id]),
            execution_policy=execution_policy,
            launcher=launcher,
        )

    assert captured.value.code == "workspace_mismatch"
    assert launcher.calls == []


def test_workspace_mutation_during_execution_can_never_authorize_pass(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id)
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)

    class MutatingLauncher(RecordingLauncher):
        def __call__(self, argv: object, **kwargs: Any) -> ProcessCapture:
            (tmp_path / "candidate-mutation.txt").write_text(
                "changed during proof execution\n",
                encoding="utf-8",
            )
            return super().__call__(argv, **kwargs)

    launcher = MutatingLauncher(exit_code=0, stdout=b"1 passed")
    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([selection], [spec.verifier_id]),
        execution_policy=execution_policy,
        launcher=launcher,
    )

    assert len(launcher.calls) == 1
    assert result.evidence[0].status == "error"
    assert result.evidence[0].failure_reason_codes == ("workspace_changed_during_execution",)
    assert result.verifier_runs == ()
    assert result.verification_receipts == ()
    assert result.short_circuited is True
    assert result.decision.verdict != "pass"


@pytest.mark.parametrize(
    ("mismatch", "error_code"),
    [
        ("task_id", "task_binding_mismatch"),
        ("task_digest", "task_binding_mismatch"),
        ("attempt_id", "attempt_binding_mismatch"),
        ("attempt_digest", "attempt_binding_mismatch"),
        ("base_revision", "attempt_binding_mismatch"),
        ("candidate_revision", "attempt_binding_mismatch"),
        ("diff_digest", "attempt_binding_mismatch"),
        ("plan_catalog", "catalog_mismatch"),
        ("policy_catalog", "catalog_mismatch"),
        ("policy_registry", "registry_mismatch"),
        ("policy_attempt", "attempt_binding_mismatch"),
        ("proof_policy", "verifier_not_approved"),
    ],
)
def test_workflow_binding_and_policy_mismatches_make_zero_launcher_calls(
    tmp_path: Path,
    mismatch: str,
    error_code: str,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id)
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    proof_policy = _proof_policy([selection], [spec.verifier_id])
    execution_policy = _execution_policy(tmp_path, catalog, registry, attempt)

    wrong_digest = sha256_digest(f"wrong {mismatch}")
    if mismatch == "task_id":
        plan = replace(plan, task_contract_id="task-contract_wrong")
    elif mismatch == "task_digest":
        plan = replace(plan, task_contract_digest=wrong_digest)
    elif mismatch == "attempt_id":
        plan = replace(plan, attempt_id="attempt_wrong")
    elif mismatch == "attempt_digest":
        plan = replace(plan, attempt_digest=wrong_digest)
    elif mismatch == "base_revision":
        plan = replace(plan, base_revision="wrong-base")
    elif mismatch == "candidate_revision":
        plan = replace(plan, candidate_revision="wrong-candidate")
    elif mismatch == "diff_digest":
        plan = replace(plan, diff_digest=wrong_digest)
    elif mismatch == "plan_catalog":
        plan = replace(plan, proof_catalog_digest=wrong_digest)
    elif mismatch == "policy_catalog":
        execution_policy = replace(execution_policy, allowed_catalog_digest=wrong_digest)
    elif mismatch == "policy_registry":
        execution_policy = replace(execution_policy, verifier_registry_digest=wrong_digest)
    elif mismatch == "policy_attempt":
        execution_policy = replace(execution_policy, expected_attempt_digest=wrong_digest)
    elif mismatch == "proof_policy":
        proof_policy = replace(
            proof_policy,
            approved_verifier_ids=["verifier.not-approved"],
            mandatory_verifier_ids=[],
        )
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=proof_policy,
            execution_policy=execution_policy,
            launcher=launcher,
        )

    assert captured.value.code == error_code
    assert launcher.calls == []


def test_stale_registered_verifier_is_rejected_before_launch(tmp_path: Path) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, approved_spec = _pytest_entry(tmp_path)
    stale_spec = replace(
        approved_spec,
        id="verifier-spec_stale",
        command_template=[sys.executable, "-c", "print('different')"],
    )
    catalog = ProofCatalog([entry])
    registry = _registry(stale_spec)
    selection = _selection(entry.id)
    task = _task(approved_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy([selection], [approved_spec.verifier_id]),
            execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
            launcher=launcher,
        )

    assert captured.value.code == "registry_mismatch"
    assert launcher.calls == []


@pytest.mark.parametrize("version", ["2", "missing"])
def test_missing_or_stale_catalog_capability_is_rejected_before_launch(
    tmp_path: Path,
    version: str,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(
        entry.id if version == "2" else "proof.not-approved",
        version=version if version == "2" else "1",
    )
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy([selection], [spec.verifier_id]),
            execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
            launcher=launcher,
        )

    assert captured.value.code == "missing_capability"
    assert launcher.calls == []


def test_global_preflight_validates_later_family_semantics_before_first_launch(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "evidence.txt").write_text("evidence", encoding="utf-8")
    runnable, runnable_spec = _pytest_entry(
        tmp_path,
        entry_id="proof.1-runnable",
    )
    invalid, invalid_spec = _file_entry(
        entry_id="proof.2-invalid",
        verifier_id="verifier.invalid-digest",
        operation="digest_equals",
    )
    catalog = ProofCatalog([invalid, runnable])
    registry = _registry(runnable_spec, invalid_spec)
    selections = [
        _selection(runnable.id, claim_id="claim.1-runnable"),
        _selection(
            invalid.id,
            claim_id="claim.2-invalid",
            parameters={"expected": "not-a-digest"},
        ),
    ]
    task = _task(runnable_spec.verifier_id, invalid_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy(
                selections, [runnable_spec.verifier_id, invalid_spec.verifier_id]
            ),
            execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
            launcher=launcher,
        )

    assert captured.value.code == "invalid_parameters"
    assert launcher.calls == []


@pytest.mark.parametrize("family", ["pytest-node", "python-call"])
def test_global_preflight_rejects_tampered_owner_pinned_source_before_launch(
    tmp_path: Path,
    family: str,
) -> None:
    if family == "pytest-node":
        source = tmp_path / "test_executor_node.py"
        source.write_text("def test_node():\n    assert True\n", encoding="utf-8")
        entry, spec = _pytest_entry(tmp_path)
        parameters: dict[str, object] = {}
    else:
        module_name = _write_python_fixture(tmp_path)
        source = tmp_path / f"{module_name}.py"
        entry, spec = _python_entry(tmp_path)
        parameters = {"inputs": [7], "expected": 7}
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id, parameters=parameters)
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    source.write_text(source.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy([selection], [spec.verifier_id]),
            execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
            launcher=launcher,
        )

    assert captured.value.code == "registry_mismatch"
    assert launcher.calls == []


def test_global_preflight_caps_the_full_later_helper_payload_before_any_launch(
    tmp_path: Path,
) -> None:
    _write_python_fixture(tmp_path, module_name="small_proof_fixture")
    large_module = _write_python_fixture(tmp_path, module_name="large_proof_fixture")
    trusted_directory = tmp_path / "trusted"
    trusted_directory.mkdir()
    additional_paths: list[str] = []
    for index in range(24):
        relative_path = f"trusted/owner_pin_{index:02d}.txt"
        (tmp_path / relative_path).write_text(f"pin {index}\n", encoding="utf-8")
        additional_paths.append(relative_path)
    first, first_spec = _python_entry(
        tmp_path,
        entry_id="proof.1-small",
        verifier_id="verifier.python.small",
        module="small_proof_fixture",
    )
    second, second_spec = _python_entry(
        tmp_path,
        entry_id="proof.2-large",
        verifier_id="verifier.python.large",
        module=large_module,
        additional_trusted_paths=additional_paths,
    )
    catalog = ProofCatalog([first, second])
    registry = _registry(first_spec, second_spec)
    selections = [
        _selection(
            first.id,
            claim_id="claim.1-small",
            parameters={"inputs": [7], "expected": 7},
        ),
        _selection(
            second.id,
            claim_id="claim.2-large",
            parameters={"inputs": [7], "expected": 7},
        ),
    ]

    def payload_size(entry: ProofCatalogEntry) -> int:
        capability = entry.capability
        assert isinstance(capability, PythonCallCapability)
        root = tmp_path.resolve()
        payload = {
            "protocol": PROTOCOL_VERSION,
            "repository_root": str(root),
            "import_root": str(root),
            "module": capability.module,
            "callable_name": capability.callable_name,
            "module_file": str((root / capability.module_file).resolve()),
            "trusted_file_digests": {
                str((root / path).resolve()): digest
                for path, digest in capability.policy.trusted_file_digests.items()
            },
            "trusted_source_byte_limit": 65_536,
            "positional_arguments": [7],
            "keyword_arguments": {},
            "assertion": "equals",
            "expected": 7,
            "result_serializer": "json",
        }
        return len(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )

    first_size = payload_size(first)
    second_size = payload_size(second)
    input_limit = (first_size + second_size) // 2
    assert first_size < input_limit < second_size
    task = _task(first_spec.verifier_id, second_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy(
                selections,
                [first_spec.verifier_id, second_spec.verifier_id],
            ),
            execution_policy=_execution_policy(
                tmp_path,
                catalog,
                registry,
                attempt,
                max_input_bytes=input_limit,
            ),
            launcher=launcher,
        )

    assert captured.value.code == "input_limit"
    assert launcher.calls == []


def test_obligation_and_capability_policy_limits_fail_before_launch(tmp_path: Path) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    first, first_spec = _pytest_entry(tmp_path, entry_id="proof.first")
    second, second_spec = _pytest_entry(
        tmp_path,
        entry_id="proof.second",
        verifier_id="verifier.pytest.second",
    )
    catalog = ProofCatalog([first, second])
    registry = _registry(first_spec, second_spec)
    selections = [_selection(first.id), _selection(second.id)]
    task = _task(first_spec.verifier_id, second_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)
    launcher = RecordingLauncher(exit_code=0)

    with pytest.raises(ProofWorkflowError) as captured:
        run_proof_workflow(
            task_contract=task,
            attempt=attempt,
            plan=plan,
            catalog=catalog,
            verifier_registry=registry,
            proof_policy=_proof_policy(
                selections, [first_spec.verifier_id, second_spec.verifier_id]
            ),
            execution_policy=_execution_policy(
                tmp_path,
                catalog,
                registry,
                attempt,
                maximum_obligations=1,
            ),
            launcher=launcher,
        )

    assert captured.value.code == "obligation_limit_exceeded"
    assert launcher.calls == []


def test_workflow_execution_and_reason_order_are_deterministic(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("approved", encoding="utf-8")
    (tmp_path / "z.txt").write_text("approved", encoding="utf-8")
    first, first_spec = _file_entry(
        entry_id="proof.z",
        verifier_id="verifier.z",
        repository_path="z.txt",
    )
    second, second_spec = _file_entry(
        entry_id="proof.a",
        verifier_id="verifier.a",
        repository_path="a.txt",
    )
    catalog = ProofCatalog([first, second])
    registry = _registry(first_spec, second_spec)
    selections = [
        _selection(first.id, claim_id="claim.z", parameters={"expected": "approved"}),
        _selection(second.id, claim_id="claim.a", parameters={"expected": "approved"}),
    ]
    task = _task(first_spec.verifier_id, second_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)

    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy(selections, [first_spec.verifier_id, second_spec.verifier_id]),
        execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
    )

    expected_order = tuple(selection.digest() for selection in plan.selections)
    assert result.execution_order == expected_order
    assert tuple(item.selection_digest for item in result.evidence) == expected_order
    assert [diagnostic["order"] for diagnostic in result.diagnostics] == [0, 1]
    assert result.decision.reason_codes == tuple(sorted(result.decision.reason_codes))
    assert result.decision.verdict == "pass"


def test_demonstrated_failure_then_total_timeout_missing_evidence_still_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import faber.proof_workflow as workflow_module

    (tmp_path / "first.txt").write_text("does not contain target", encoding="utf-8")
    (tmp_path / "second.txt").write_text("approved", encoding="utf-8")
    failed_entry, failed_spec = _file_entry(
        entry_id="proof.1-failed",
        verifier_id="verifier.failed",
        repository_path="first.txt",
    )
    later_entry, later_spec = _file_entry(
        entry_id="proof.2-later",
        verifier_id="verifier.later",
        repository_path="second.txt",
    )
    catalog = ProofCatalog([failed_entry, later_entry])
    registry = _registry(failed_spec, later_spec)
    selections = [
        _selection(
            failed_entry.id,
            claim_id="claim.1-failed",
            parameters={"expected": "approved"},
        ),
        _selection(
            later_entry.id,
            claim_id="claim.2-later",
            parameters={"expected": "approved"},
        ),
    ]
    task = _task(failed_spec.verifier_id, later_spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=selections)

    class FakeTime:
        def __init__(self) -> None:
            self.values = iter([0.0, 0.0, 0.0, 0.0, 0.0, 11.0, 11.0, 11.0])

        def perf_counter(self) -> float:
            return next(self.values, 11.0)

    monkeypatch.setattr(workflow_module, "time", FakeTime())
    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy(selections, [failed_spec.verifier_id, later_spec.verifier_id]),
        execution_policy=_execution_policy(
            tmp_path,
            catalog,
            registry,
            attempt,
            total_timeout_seconds=10,
        ),
    )

    assert [item.status for item in result.evidence] == ["failed", "missing"]
    assert result.short_circuited is True
    assert result.decision.verdict == "block"
    assert result.decision.failed_claim_ids == ("claim.1-failed",)
    assert result.decision.missing_claim_ids == ("claim.2-later",)
    assert "authoritative_claim_failure" in result.decision.reason_codes
    assert "required_claim_evidence_incomplete" in result.decision.reason_codes


def test_operational_error_only_can_never_yield_pass(tmp_path: Path) -> None:
    (tmp_path / "test_executor_node.py").write_text(
        "def test_node():\n    assert True\n",
        encoding="utf-8",
    )
    entry, spec = _pytest_entry(tmp_path)
    catalog = ProofCatalog([entry])
    registry = _registry(spec)
    selection = _selection(entry.id)
    task = _task(spec.verifier_id)
    attempt = _attempt(task)
    plan = _plan(task, attempt, catalog_digest=catalog.digest(), selections=[selection])
    launcher = RecordingLauncher(error=OSError("fixture launch failure"))

    result = run_proof_workflow(
        task_contract=task,
        attempt=attempt,
        plan=plan,
        catalog=catalog,
        verifier_registry=registry,
        proof_policy=_proof_policy([selection], [spec.verifier_id]),
        execution_policy=_execution_policy(tmp_path, catalog, registry, attempt),
        launcher=launcher,
    )

    assert [item.status for item in result.evidence] == ["error"]
    assert result.verifier_runs == ()
    assert result.verification_receipts == ()
    assert result.decision.verdict == "human_review"
    assert result.decision.verdict != "pass"
    assert "required_evidence_error" in result.decision.reason_codes


def _write_python_fixture(
    root: Path,
    *,
    module_name: str = "proof_executor_fixture",
) -> str:
    (root / f"{module_name}.py").write_text(
        "\n".join(
            (
                "def echo(value):",
                "    return value",
                "",
                "def raise_value_error(_value):",
                "    raise ValueError('fixture failure')",
                "",
            )
        ),
        encoding="utf-8",
    )
    return module_name


def _runtime_payload(
    root: Path,
    *,
    module_name: str,
    callable_name: str,
    assertion: str,
    expected: object,
    positional_arguments: list[object] | None = None,
    keyword_arguments: dict[str, object] | None = None,
) -> dict[str, object]:
    module_file = (root / f"{module_name.replace('.', '/')}.py").resolve()
    trusted_paths = [
        (root / Path(*module_name.split(".")[:index]) / "__init__.py").resolve()
        for index in range(1, len(module_name.split(".")))
    ]
    trusted_paths.append(module_file)
    return {
        "protocol": PROTOCOL_VERSION,
        "repository_root": str(root.resolve()),
        "import_root": str(root.resolve()),
        "module": module_name,
        "callable_name": callable_name,
        "module_file": str(module_file),
        "trusted_file_digests": {
            str(path): sha256_digest(path.read_bytes()) for path in trusted_paths
        },
        "trusted_source_byte_limit": 65_536,
        "positional_arguments": positional_arguments or [],
        "keyword_arguments": keyword_arguments or {},
        "assertion": assertion,
        "expected": expected,
        "result_serializer": "json",
    }


def _helper_payload(
    root: Path,
    *,
    assertion: str,
    argument: object,
    expected: object,
    callable_name: str = "echo",
) -> dict[str, object]:
    module_name = f"proof_executor_fixture_{sha256_digest(str(root.resolve()))[-12:]}"
    _write_python_fixture(root, module_name=module_name)
    return _runtime_payload(
        root,
        module_name=module_name,
        callable_name=callable_name,
        assertion=assertion,
        expected=expected,
        positional_arguments=[argument],
    )


@pytest.mark.parametrize(
    ("assertion", "argument", "expected", "callable_name"),
    [
        ("equals", 7, 7, "echo"),
        ("not_equals", 7, 8, "echo"),
        ("is_none", None, None, "echo"),
        ("is_not_none", 7, None, "echo"),
        ("raises", "ignored", "builtins.ValueError", "raise_value_error"),
        ("contains", "abcdef", "bcd", "echo"),
        ("truthy", [1], None, "echo"),
        ("falsey", [], None, "echo"),
    ],
)
def test_python_runtime_helper_supports_the_closed_assertion_set(
    tmp_path: Path,
    assertion: str,
    argument: object,
    expected: object,
    callable_name: str,
) -> None:
    result = execute_payload(
        _helper_payload(
            tmp_path,
            assertion=assertion,
            argument=argument,
            expected=expected,
            callable_name=callable_name,
        )
    )

    assert result["status"] == "passed"
    assert result["reason_code"] == "assertion_passed"


@pytest.mark.parametrize(
    ("assertion", "argument", "expected", "expected_status"),
    [
        ("equals", 1, True, "failed"),
        ("equals", 1.0, 1, "failed"),
        ("equals", {"value": [1]}, {"value": [True]}, "failed"),
        ("contains", [1], True, "failed"),
        ("not_equals", 1, True, "passed"),
    ],
)
def test_python_runtime_helper_comparisons_preserve_exact_json_types(
    tmp_path: Path,
    assertion: str,
    argument: object,
    expected: object,
    expected_status: str,
) -> None:
    result = execute_payload(
        _helper_payload(
            tmp_path,
            assertion=assertion,
            argument=argument,
            expected=expected,
        )
    )

    assert result["status"] == expected_status


def test_python_runtime_helper_counterexample_is_bounded_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    secret = "sk-proj-AAAAAAAAAAAAAAAAAAAAAAAA"

    result = execute_payload(
        _helper_payload(
            tmp_path,
            assertion="equals",
            argument=secret,
            expected="a different value",
        )
    )
    serialized = json.dumps(result, sort_keys=True)

    assert result["status"] == "failed"
    assert result["reason_code"] == "assertion_failed"
    assert secret not in serialized
    assert "[redacted]" in serialized
    assert len(serialized.encode("utf-8")) < 8_192


def test_python_runtime_helper_rejects_a_preloaded_stdlib_module_before_target_call(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "target-called.txt"
    module_file = tmp_path / "json.py"
    module_file.write_text(
        "\n".join(
            (
                "from pathlib import Path",
                "def target():",
                f"    Path({str(marker)!r}).write_text('called', encoding='utf-8')",
                "    return True",
                "",
            )
        ),
        encoding="utf-8",
    )
    loaded_json = sys.modules.get("json")
    assert loaded_json is not None
    assert Path(str(getattr(loaded_json, "__file__", ""))).resolve() != module_file.resolve()

    with pytest.raises(ProtocolError, match="already loaded externally"):
        execute_payload(
            _runtime_payload(
                tmp_path,
                module_name="json",
                callable_name="target",
                assertion="truthy",
                expected=None,
            )
        )

    assert marker.exists() is False


@pytest.mark.parametrize(
    ("callable_name", "assertion", "expected"),
    [
        ("spoof_equals", "equals", 999),
        ("spoof_truthy", "truthy", None),
        ("spoof_contains", "contains", "missing"),
        ("spoof_string_contains", "contains", "missing"),
        ("spoof_mapping_contains", "contains", "missing"),
        ("spoof_nested_equals", "equals", [999]),
    ],
)
def test_python_runtime_helper_rejects_scalar_container_and_nested_subclass_spoofs(
    tmp_path: Path,
    callable_name: str,
    assertion: str,
    expected: object,
) -> None:
    module_name = f"subclass_spoof_{sha256_digest(str(tmp_path.resolve()))[-12:]}"
    (tmp_path / f"{module_name}.py").write_text(
        "\n".join(
            (
                "class SpoofInt(int):",
                "    def __eq__(self, _other):",
                "        return True",
                "    def __bool__(self):",
                "        return True",
                "",
                "class SpoofList(list):",
                "    def __contains__(self, _item):",
                "        return True",
                "",
                "class SpoofStr(str):",
                "    def __contains__(self, _item):",
                "        return True",
                "",
                "class SpoofDict(dict):",
                "    def __contains__(self, _item):",
                "        return True",
                "",
                "def spoof_equals():",
                "    return SpoofInt(1)",
                "",
                "def spoof_truthy():",
                "    return SpoofInt(0)",
                "",
                "def spoof_contains():",
                "    return SpoofList([])",
                "",
                "def spoof_string_contains():",
                "    return SpoofStr('present')",
                "",
                "def spoof_mapping_contains():",
                "    return SpoofDict({})",
                "",
                "def spoof_nested_equals():",
                "    return [SpoofInt(1)]",
                "",
            )
        ),
        encoding="utf-8",
    )

    result = execute_payload(
        _runtime_payload(
            tmp_path,
            module_name=module_name,
            callable_name=callable_name,
            assertion=assertion,
            expected=expected,
        )
    )

    assert result["status"] == "error"
    assert result["reason_code"] == "result_serialization_error"


def test_python_runtime_helper_does_not_trust_mutable_exception_names(
    tmp_path: Path,
) -> None:
    module_name = f"exception_spoof_{sha256_digest(str(tmp_path.resolve()))[-12:]}"
    (tmp_path / f"{module_name}.py").write_text(
        "\n".join(
            (
                "class MutableNameError(Exception):",
                "    pass",
                "",
                "MutableNameError.__name__ = 'ValueError'",
                "MutableNameError.__qualname__ = 'ValueError'",
                "MutableNameError.__module__ = 'builtins'",
                "",
                "def raise_spoof():",
                "    raise MutableNameError('not a builtins.ValueError')",
                "",
            )
        ),
        encoding="utf-8",
    )

    result = execute_payload(
        _runtime_payload(
            tmp_path,
            module_name=module_name,
            callable_name="raise_spoof",
            assertion="raises",
            expected="builtins.ValueError",
        )
    )

    assert result["status"] == "failed"
    assert result["reason_code"] == "expected_exception_mismatch"
    assert result["exception_type"] == "unapproved_exception"


def test_python_runtime_helper_rejects_unpinned_repository_sibling_imports(
    tmp_path: Path,
) -> None:
    package = tmp_path / "approved_package"
    package.mkdir()
    marker = tmp_path / "unpinned-sibling-executed.txt"
    (package / "__init__.py").write_text("from . import sibling\n", encoding="utf-8")
    (package / "target.py").write_text(
        "def echo(value):\n    return value\n",
        encoding="utf-8",
    )
    (package / "sibling.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )

    result = execute_payload(
        _runtime_payload(
            tmp_path,
            module_name="approved_package.target",
            callable_name="echo",
            assertion="equals",
            expected=7,
            positional_arguments=[7],
        )
    )

    assert result["status"] == "error"
    assert result["reason_code"] == "target_import_error"
    assert marker.exists() is False
