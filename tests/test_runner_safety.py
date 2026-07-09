import sys
from pathlib import Path

import pytest

from faber.errors import VerifierError
from faber.runner.local import LocalVerifierRunner, RunnerPolicy
from faber.verifiers import VerifierRegistry, VerifierSpec


def _registry(command: list[str], *, timeout: int = 30) -> VerifierRegistry:
    registry = VerifierRegistry()
    registry.register(
        VerifierSpec(
            verifier_id="verifier.safe",
            name="Safe verifier",
            version="1",
            description="Safety test verifier.",
            command_template=command,
            allowed_timeout_seconds=timeout,
        )
    )
    return registry


def test_runner_executes_command_list_without_shell(tmp_path: Path) -> None:
    runner = LocalVerifierRunner(
        _registry([sys.executable, "-c", "print('ok')"]),
        policy=RunnerPolicy(allowed_working_directory_root=str(tmp_path)),
    )

    result = runner.run("verifier.safe", working_directory=tmp_path)

    assert result.verifier_run.passed is True
    assert result.verifier_run.metadata["shell"] is False


def test_runner_rejects_unregistered_command(tmp_path: Path) -> None:
    runner = LocalVerifierRunner(VerifierRegistry())

    with pytest.raises(VerifierError, match="not registered"):
        runner.run("candidate-owned-command", working_directory=tmp_path)


def test_runner_rejects_path_outside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    runner = LocalVerifierRunner(
        _registry([sys.executable, "-c", "print('ok')"]),
        policy=RunnerPolicy(allowed_working_directory_root=str(allowed)),
    )

    with pytest.raises(VerifierError, match="outside allowed root"):
        runner.run("verifier.safe", working_directory=outside)


def test_runner_rejects_unapproved_environment_variable(tmp_path: Path) -> None:
    runner = LocalVerifierRunner(
        _registry([sys.executable, "-c", "print('ok')"]),
        policy=RunnerPolicy(
            allowed_working_directory_root=str(tmp_path),
            allowed_environment_variables=["PATH", "SYSTEMROOT"],
        ),
    )

    with pytest.raises(VerifierError, match="not allowed"):
        runner.run(
            "verifier.safe",
            working_directory=tmp_path,
            extra_environment={"SECRET_TOKEN": "nope"},
        )


def test_runner_timeout_and_digest_capture(tmp_path: Path) -> None:
    runner = LocalVerifierRunner(
        _registry([sys.executable, "-c", "import time; time.sleep(2)"], timeout=1),
        policy=RunnerPolicy(allowed_working_directory_root=str(tmp_path), timeout_seconds=1),
    )

    result = runner.run("verifier.safe", working_directory=tmp_path)

    assert result.timed_out is True
    assert result.stdout_digest.startswith("sha256:")
    assert result.stderr_digest.startswith("sha256:")


def test_runner_policy_serialization_and_digest_are_stable(tmp_path: Path) -> None:
    policy = RunnerPolicy(
        allowed_working_directory_root=str(tmp_path),
        allowed_environment_variables=["PATH"],
        timeout_seconds=5,
        max_capture_bytes=100,
    )
    same = RunnerPolicy(
        allowed_working_directory_root=str(tmp_path),
        allowed_environment_variables=["PATH"],
        timeout_seconds=5,
        max_capture_bytes=100,
    )

    assert policy.to_dict()["allow_shell"] is False
    assert policy.digest() == same.digest()


def test_runner_docs_include_local_limitation() -> None:
    docs = Path("src/faber/runner/README.md").read_text(encoding="utf-8")

    assert "not a production sandbox" in docs
    assert "does not provide complete network" in docs
