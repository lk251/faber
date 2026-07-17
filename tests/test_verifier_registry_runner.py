import io
import sys
import threading
import time
from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import VerifierError
from faber.receipts import VerificationReceipt
from faber.runner.local import LocalVerifierRunner, RunnerPolicy
from faber.verifiers import VerifierRegistry, VerifierSpec


def _spec(
    command: list[str],
    *,
    verifier_id: str = "verifier.local",
    timeout_seconds: int = 30,
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


def test_verifier_registry_digest_binds_exact_specs_in_stable_order() -> None:
    first = VerifierSpec(
        id="verifier-spec_first",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.first",
        name="First verifier",
        version="1",
        description="First deterministic check.",
        command_template=[sys.executable, "-c", "print('first')"],
    )
    second = VerifierSpec(
        id="verifier-spec_second",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.second",
        name="Second verifier",
        version="1",
        description="Second deterministic check.",
        command_template=[sys.executable, "-c", "print('second')"],
    )
    left = VerifierRegistry()
    right = VerifierRegistry()
    left.register(second)
    left.register(first)
    right.register(first)
    right.register(second)

    assert left.snapshot() == right.snapshot()
    assert left.digest() == right.digest()
    assert left.digest() != VerifierRegistry().digest()


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


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_local_verifier_output_overflow_is_bounded_and_cannot_pass(
    tmp_path: Path,
    stream_name: str,
) -> None:
    registry = VerifierRegistry()
    command = (
        f"import sys; sys.{stream_name}.buffer.write(b'x' * 4096); sys.{stream_name}.buffer.flush()"
    )
    spec = _spec([sys.executable, "-c", command])
    registry.register(spec)
    runner = LocalVerifierRunner(
        registry,
        RunnerPolicy(max_capture_bytes=64),
    )

    result = runner.run(spec.verifier_id, working_directory=tmp_path)

    assert result.status == "error"
    assert result.error_code == "output_limit"
    assert result.output_limit_exceeded is True
    assert result.verifier_run.passed is False
    assert "output_limit" in result.verifier_run.failure_reasons
    assert result.verifier_run.metrics[f"{stream_name}_bytes"] == 64
    assert result.verifier_run.metrics[f"{stream_name}_observed_bytes"] == 4096
    assert getattr(result, f"{stream_name}_truncated") is True
    assert getattr(result, f"{stream_name}_overflow") is True


def test_local_verifier_closes_inherited_pipe_without_hanging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import faber.runner.local as local_runner_module

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
    popen_options: dict[str, object] = {}

    class ExitedProcessWithInheritedPipe:
        def __init__(self, _argv: list[str], **kwargs: object) -> None:
            popen_options.update(kwargs)
            self.stdout = blocking_stdout
            self.stderr = io.BytesIO(b"")
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None
            return self.returncode

        def kill(self) -> None:
            raise AssertionError("an already-exited verifier must not be killed")

    monkeypatch.setattr(local_runner_module, "PIPE_DRAIN_GRACE_SECONDS", grace_seconds)
    monkeypatch.setattr(local_runner_module.subprocess, "Popen", ExitedProcessWithInheritedPipe)
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", "print('ok')"])
    registry.register(spec)

    started = time.perf_counter()
    result = LocalVerifierRunner(registry).run(
        spec.verifier_id,
        working_directory=tmp_path,
    )
    elapsed = time.perf_counter() - started

    assert blocking_stdout.entered.is_set()
    assert blocking_stdout.finished.wait(timeout=0.5)
    assert elapsed < grace_seconds + 0.25
    assert popen_options["shell"] is False
    assert result.status == "error"
    assert result.error_code == "output_capture_incomplete"
    assert result.stdout_capture_incomplete is True
    assert result.stdout_truncated is True
    assert result.stdout_overflow is False
    assert result.verifier_run.passed is False
    assert "output_capture_incomplete" in result.verifier_run.failure_reasons


def test_local_verifier_pipe_read_error_is_incomplete_and_cannot_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import faber.runner.local as local_runner_module

    class FailingStream:
        def __init__(self) -> None:
            self.reads = 0

        def read(self, _size: int) -> bytes:
            self.reads += 1
            if self.reads == 1:
                return b"partial"
            raise OSError("simulated pipe read failure")

        def close(self) -> None:
            return None

    failing_stdout = FailingStream()

    class ExitedProcessWithBrokenPipe:
        def __init__(self, _argv: list[str], **_kwargs: object) -> None:
            self.stdout = failing_stdout
            self.stderr = io.BytesIO(b"")
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None
            return self.returncode

        def kill(self) -> None:
            raise AssertionError("an already-exited verifier must not be killed")

    monkeypatch.setattr(local_runner_module.subprocess, "Popen", ExitedProcessWithBrokenPipe)
    registry = VerifierRegistry()
    spec = _spec([sys.executable, "-c", "print('ok')"])
    registry.register(spec)

    result = LocalVerifierRunner(registry).run(
        spec.verifier_id,
        working_directory=tmp_path,
    )

    assert failing_stdout.reads == 2
    assert result.status == "error"
    assert result.error_code == "output_capture_incomplete"
    assert result.stdout_capture_incomplete is True
    assert result.stdout_truncated is True
    assert result.verifier_run.passed is False
    assert "output_capture_incomplete" in result.verifier_run.failure_reasons


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
