"""Local approved-verifier runner."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from faber.digests import sha256_digest
from faber.errors import VerifierError
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec


@dataclass(frozen=True)
class LocalVerifierResult:
    """Structured local runner output before receipt creation."""

    verifier_run: VerifierRun
    stdout_digest: str
    stderr_digest: str
    elapsed_seconds: float
    exit_code: int | None
    timed_out: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "verifier_run": self.verifier_run.to_dict(),
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "elapsed_seconds": self.elapsed_seconds,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
        }


@dataclass(frozen=True)
class LocalVerifierSpec:
    """Compatibility helper for manually recording local verifier results."""

    verifier_id: str
    name: str
    version: str
    command: list[str]

    def to_spec(self, *, description: str = "Local verifier") -> VerifierSpec:
        return VerifierSpec(
            verifier_id=self.verifier_id,
            name=self.name,
            version=self.version,
            description=description,
            command_template=self.command,
        )

    def record_result(
        self,
        *,
        passed: bool,
        metrics: dict[str, object] | None = None,
        failure_reasons: list[str] | None = None,
        logs_digest: str | None = None,
    ) -> VerifierRun:
        return VerifierRun(
            verifier_id=self.verifier_id,
            name=self.name,
            version=self.version,
            command=self.command,
            passed=passed,
            metrics=metrics or {},
            failure_reasons=failure_reasons or [],
            logs_digest=logs_digest,
        )


class LocalVerifierRunner:
    """Run registered verifier specs with Python's subprocess module."""

    def __init__(self, registry: VerifierRegistry) -> None:
        self._registry = registry

    def run(
        self,
        verifier_id: str,
        *,
        working_directory: str | Path,
        timeout_seconds: int | None = None,
        extra_environment: dict[str, str] | None = None,
    ) -> LocalVerifierResult:
        spec = self._registry.resolve(verifier_id)
        cwd = Path(working_directory).resolve()
        if not cwd.exists() or not cwd.is_dir():
            raise VerifierError(f"working_directory must exist: {cwd}")
        timeout = timeout_seconds or spec.allowed_timeout_seconds
        timeout = min(timeout, spec.allowed_timeout_seconds)
        command = spec.command()
        environment = os.environ.copy()
        if extra_environment:
            environment.update(extra_environment)
        started = time.perf_counter()
        stdout = b""
        stderr = b""
        exit_code: int | None = None
        timed_out = False
        failure_reasons: list[str] = []
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                capture_output=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
            passed = completed.returncode == 0
            if not passed:
                failure_reasons.append(f"verifier exited with code {completed.returncode}")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            passed = False
            stdout = _coerce_bytes(exc.stdout)
            stderr = _coerce_bytes(exc.stderr)
            failure_reasons.append(f"verifier timed out after {timeout} seconds")
        elapsed = time.perf_counter() - started
        stdout_digest = sha256_digest(stdout)
        stderr_digest = sha256_digest(stderr)
        metrics = _extract_metrics(stdout)
        metrics.update(
            {
                "exit_code": exit_code,
                "elapsed_seconds": round(elapsed, 6),
                "timed_out": timed_out,
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
            }
        )
        logs_digest = sha256_digest(
            {
                "stdout_digest": stdout_digest,
                "stderr_digest": stderr_digest,
            }
        )
        verifier_run = VerifierRun(
            verifier_id=spec.verifier_id,
            name=spec.name,
            version=spec.version,
            command=command,
            passed=passed,
            metrics=metrics,
            failure_reasons=failure_reasons,
            logs_digest=logs_digest,
            metadata={
                "approved_verifier_spec_digest": spec.digest(),
                "working_directory": str(cwd),
                "stdout_digest": stdout_digest,
                "stderr_digest": stderr_digest,
                "runner": "local",
                "shell": False,
            },
        )
        return LocalVerifierResult(
            verifier_run=verifier_run,
            stdout_digest=stdout_digest,
            stderr_digest=stderr_digest,
            elapsed_seconds=elapsed,
            exit_code=exit_code,
            timed_out=timed_out,
        )


def run_registered_verifier(
    registry: VerifierRegistry,
    verifier_id: str,
    *,
    working_directory: str | Path,
    timeout_seconds: int | None = None,
) -> VerifierRun:
    return (
        LocalVerifierRunner(registry)
        .run(
            verifier_id,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
        )
        .verifier_run
    )


def _coerce_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _extract_metrics(stdout: bytes) -> dict[str, object]:
    if not stdout:
        return {}
    try:
        parsed = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    metrics = parsed.get("metrics")
    if isinstance(metrics, dict):
        return {str(key): value for key, value in metrics.items()}
    return {}
