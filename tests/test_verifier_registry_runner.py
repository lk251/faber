import sys
from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import VerifierError
from faber.receipts import VerificationReceipt
from faber.runner.local import LocalVerifierRunner
from faber.verifiers import VerifierRegistry, VerifierSpec


def _spec(
    command: list[str],
    *,
    verifier_id: str = "verifier.local",
    timeout_seconds: int = 5,
) -> VerifierSpec:
    return VerifierSpec(
        verifier_id=verifier_id,
        name="Local verifier",
        version="1",
        description="Runs a deterministic local check.",
        command_template=command,
        allowed_timeout_seconds=timeout_seconds,
    )


def test_verifier_registry_registers_and_resolves_specs() -> None:
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", "print('ok')"])

    registry.register(spec)

    assert registry.resolve(spec.verifier_id) == spec
    assert registry.list_specs() == [spec]


def test_verifier_spec_digest_is_stable() -> None:
    left = VerifierSpec(
        id="verifier-spec_stable",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.local",
        name="Local verifier",
        version="1",
        description="Runs a deterministic local check.",
        command_template=[sys.executable, "-c", "print('ok')"],
    )
    right = VerifierSpec(
        id="verifier-spec_stable",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.local",
        name="Local verifier",
        version="1",
        description="Runs a deterministic local check.",
        command_template=[sys.executable, "-c", "print('ok')"],
    )

    assert left.digest() == right.digest()


def test_local_verifier_success_captures_metrics_and_digests(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", 'print(\'{"metrics":{"checks":1}}\')'])
    registry.register(spec)

    result = LocalVerifierRunner(registry).run(spec.verifier_id, working_directory=tmp_path)

    assert result.verifier_run.passed is True
    assert result.verifier_run.metrics["checks"] == 1
    assert result.stdout_digest.startswith("sha256:")
    assert result.stderr_digest.startswith("sha256:")
    assert result.verifier_run.logs_digest is not None
    assert result.verifier_run.metadata["shell"] is False


def test_local_verifier_failure_records_exit_code(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", "import sys; sys.exit(7)"])
    registry.register(spec)

    result = LocalVerifierRunner(registry).run(spec.verifier_id, working_directory=tmp_path)

    assert result.verifier_run.passed is False
    assert result.exit_code == 7
    assert result.verifier_run.failure_reasons == ["verifier exited with code 7"]


def test_local_verifier_timeout_records_failure(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    spec = _spec(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout_seconds=1,
    )
    registry.register(spec)

    result = LocalVerifierRunner(registry).run(spec.verifier_id, working_directory=tmp_path)

    assert result.verifier_run.passed is False
    assert result.timed_out is True
    assert "timed out" in result.verifier_run.failure_reasons[0]


def test_unregistered_verifier_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(VerifierError, match="not registered"):
        LocalVerifierRunner(VerifierRegistry()).run("missing", working_directory=tmp_path)


def test_receipt_creation_from_approved_verifier_run(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", "print('ok')"])
    registry.register(spec)
    verifier_run = (
        LocalVerifierRunner(registry)
        .run(
            spec.verifier_id,
            working_directory=tmp_path,
        )
        .verifier_run
    )
    contract = TaskContract(
        id="task-contract_verifier",
        created_at="2026-01-01T00:00:00Z",
        title="Verifier task",
        description="Run an approved verifier.",
        requirements=["pass verifier"],
        verifier_ids=[spec.verifier_id],
    )
    attempt = Attempt(
        id="attempt_verifier",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker",
        base_revision="base",
        candidate_revision="candidate",
        summary="Done",
        patch_digest=sha256_digest("patch"),
    )

    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)

    assert receipt.accepted is True
    assert receipt.verifier_id == spec.verifier_id
    assert receipt.verifier_digest == verifier_run.verifier_digest()
