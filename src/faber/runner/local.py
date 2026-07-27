"""Local approved-verifier runner."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import VerifierError
from faber.validation import require_digest
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec

PIPE_READ_BYTES = 8_192
PIPE_DRAIN_GRACE_SECONDS = 0.2
PIPE_CLOSE_GRACE_SECONDS = 0.05
PROCESS_KILL_GRACE_SECONDS = 1.0
LOCAL_VERIFIER_INVOCATION_SCHEMA = "faber.local_verifier_invocation.v1"
LOCAL_VERIFIER_INVOCATION_NONCE_BYTES = 32


def new_local_verifier_invocation_nonce() -> str:
    """Return a fresh caller-owned nonce for one verifier invocation."""

    return secrets.token_hex(LOCAL_VERIFIER_INVOCATION_NONCE_BYTES)


def local_verifier_invocation_digest(
    *,
    invocation_nonce: str,
    invocation_context_digest: str,
) -> str:
    """Commit one fresh invocation to its exact pre-execution context."""

    if (
        not isinstance(invocation_nonce, str)
        or len(invocation_nonce) != LOCAL_VERIFIER_INVOCATION_NONCE_BYTES * 2
        or any(character not in "0123456789abcdef" for character in invocation_nonce)
    ):
        raise VerifierError("invocation_nonce must be a 256-bit lowercase hexadecimal nonce")
    require_digest(invocation_context_digest, "invocation_context_digest")
    return sha256_digest(
        {
            "schema": LOCAL_VERIFIER_INVOCATION_SCHEMA,
            "invocation_nonce": invocation_nonce,
            "invocation_context_digest": invocation_context_digest,
        }
    )


@dataclass(frozen=True)
class LocalVerifierResult:
    """Structured local runner output before receipt creation."""

    verifier_run: VerifierRun
    invocation_nonce: str
    invocation_context_digest: str
    invocation_digest: str
    stdout_digest: str
    stderr_digest: str
    elapsed_seconds: float
    exit_code: int | None
    timed_out: bool
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    stdout_overflow: bool = False
    stderr_overflow: bool = False
    stdout_capture_incomplete: bool = False
    stderr_capture_incomplete: bool = False
    error_code: str | None = None

    def __post_init__(self) -> None:
        expected_invocation_digest = local_verifier_invocation_digest(
            invocation_nonce=self.invocation_nonce,
            invocation_context_digest=self.invocation_context_digest,
        )
        require_digest(self.invocation_digest, "invocation_digest")
        if self.invocation_digest != expected_invocation_digest:
            raise VerifierError("invocation_digest does not match the invocation binding")
        metadata = self.verifier_run.metadata
        if (
            metadata.get("invocation_nonce") != self.invocation_nonce
            or metadata.get("invocation_context_digest") != self.invocation_context_digest
            or metadata.get("invocation_digest") != self.invocation_digest
        ):
            raise VerifierError("verifier_run metadata does not match the invocation binding")

    @property
    def output_limit_exceeded(self) -> bool:
        return self.stdout_overflow or self.stderr_overflow

    @property
    def capture_incomplete(self) -> bool:
        return self.stdout_capture_incomplete or self.stderr_capture_incomplete

    @property
    def status(self) -> str:
        if (
            self.error_code is not None
            or self.timed_out
            or self.output_limit_exceeded
            or self.capture_incomplete
        ):
            return "error"
        return "passed" if self.verifier_run.passed else "failed"

    def to_dict(self) -> dict[str, object]:
        return {
            "verifier_run": self.verifier_run.to_dict(),
            "invocation_nonce": self.invocation_nonce,
            "invocation_context_digest": self.invocation_context_digest,
            "invocation_digest": self.invocation_digest,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "elapsed_seconds": self.elapsed_seconds,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "stdout_overflow": self.stdout_overflow,
            "stderr_overflow": self.stderr_overflow,
            "stdout_capture_incomplete": self.stdout_capture_incomplete,
            "stderr_capture_incomplete": self.stderr_capture_incomplete,
            "output_limit_exceeded": self.output_limit_exceeded,
            "capture_incomplete": self.capture_incomplete,
            "error_code": self.error_code,
            "status": self.status,
        }


def _default_allowed_env() -> list[str]:
    return [
        "COMSPEC",
        "HOME",
        "PATH",
        "PATHEXT",
        "PYTHONPATH",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    ]


@dataclass(frozen=True)
class RunnerPolicy:
    """Explicit local runner execution policy."""

    allowed_working_directory_root: str | None = None
    network_isolation: str = "none-local-runner-does-not-isolate-network"
    allowed_environment_variables: list[str] = field(default_factory=_default_allowed_env)
    timeout_seconds: int = 30
    max_capture_bytes: int = 64_000
    allow_shell: bool = False
    schema: str = schemas.RUNNER_POLICY

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise VerifierError("timeout_seconds must be positive")
        if self.max_capture_bytes <= 0:
            raise VerifierError("max_capture_bytes must be positive")
        if self.allow_shell:
            raise VerifierError("shell execution is not allowed by the local runner")
        if self.allowed_working_directory_root is not None:
            Path(self.allowed_working_directory_root).resolve()

    def validate_working_directory(self, working_directory: str | Path) -> Path:
        cwd = Path(working_directory).resolve()
        if not cwd.exists() or not cwd.is_dir():
            raise VerifierError(f"working_directory must exist: {cwd}")
        if self.allowed_working_directory_root is not None:
            root = Path(self.allowed_working_directory_root).resolve()
            try:
                cwd.relative_to(root)
            except ValueError as exc:
                raise VerifierError(
                    f"working_directory {cwd} is outside allowed root {root}"
                ) from exc
        return cwd

    def environment(self, extra_environment: dict[str, str] | None = None) -> dict[str, str]:
        allowed = set(self.allowed_environment_variables)
        environment = {key: value for key, value in os.environ.items() if key in allowed}
        if extra_environment:
            for key, value in extra_environment.items():
                if key not in allowed:
                    raise VerifierError(f"environment variable {key!r} is not allowed")
                environment[key] = value
        return environment

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "allowed_working_directory_root": self.allowed_working_directory_root,
            "network_isolation": self.network_isolation,
            "allowed_environment_variables": self.allowed_environment_variables,
            "timeout_seconds": self.timeout_seconds,
            "max_capture_bytes": self.max_capture_bytes,
            "allow_shell": self.allow_shell,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


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


@dataclass(frozen=True)
class _CaptureSnapshot:
    value: bytes
    observed_bytes: int
    truncated: bool
    overflow: bool
    incomplete: bool


class _BoundedStreamCapture:
    """Thread-safe byte capture that continues draining after its memory limit."""

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        self._value = bytearray()
        self._observed_bytes = 0
        self._truncated = False
        self._overflow = False
        self._incomplete = False
        self._lock = threading.Lock()

    def add(self, value: bytes) -> None:
        with self._lock:
            self._observed_bytes += len(value)
            remaining = self._max_bytes - len(self._value)
            if remaining > 0:
                self._value.extend(value[:remaining])
            if len(value) > remaining:
                self._truncated = True
                self._overflow = True

    def mark_incomplete(self) -> None:
        with self._lock:
            self._truncated = True
            self._incomplete = True

    def snapshot(self) -> _CaptureSnapshot:
        with self._lock:
            return _CaptureSnapshot(
                value=bytes(self._value),
                observed_bytes=self._observed_bytes,
                truncated=self._truncated,
                overflow=self._overflow,
                incomplete=self._incomplete,
            )


def _drain_stream(stream: object, capture: _BoundedStreamCapture) -> None:
    reader = getattr(stream, "read", None)
    if not callable(reader):
        capture.mark_incomplete()
        return
    try:
        while True:
            value = reader(PIPE_READ_BYTES)
            if not value:
                return
            capture.add(_coerce_bytes(value))
    except (OSError, ValueError):
        capture.mark_incomplete()
        return


def _interrupt_stream(stream: object) -> None:
    """Interrupt a blocked pipe read without waiting on buffered-I/O locks."""

    raw_stream = getattr(stream, "raw", None)
    close = getattr(raw_stream, "close", None)
    if not callable(close):
        close = getattr(stream, "close", None)
    if callable(close):
        try:
            close()
        except (OSError, ValueError):
            pass


def _finish_stream_capture(
    readers: tuple[threading.Thread, threading.Thread],
    streams: tuple[object, object],
    captures: tuple[_BoundedStreamCapture, _BoundedStreamCapture],
) -> tuple[_CaptureSnapshot, _CaptureSnapshot]:
    drain_deadline = time.perf_counter() + PIPE_DRAIN_GRACE_SECONDS
    for reader in readers:
        reader.join(timeout=max(0.0, drain_deadline - time.perf_counter()))
    lingering: list[threading.Thread] = []
    for reader, stream, capture in zip(
        readers,
        streams,
        captures,
        strict=True,
    ):
        if reader.is_alive():
            capture.mark_incomplete()
            threading.Thread(
                target=_interrupt_stream,
                args=(stream,),
                daemon=True,
            ).start()
            lingering.append(reader)
    close_deadline = time.perf_counter() + PIPE_CLOSE_GRACE_SECONDS
    for reader in lingering:
        reader.join(timeout=max(0.0, close_deadline - time.perf_counter()))
    return captures[0].snapshot(), captures[1].snapshot()


class LocalVerifierRunner:
    """Run registered verifier specs with Python's subprocess module."""

    def __init__(self, registry: VerifierRegistry, policy: RunnerPolicy | None = None) -> None:
        self._registry = registry
        self._policy = policy or RunnerPolicy()

    @property
    def runner_policy_digest(self) -> str:
        """Expose the exact policy commitment for pre-execution adapter binding."""

        return self._policy.digest()

    def run(
        self,
        verifier_id: str,
        *,
        working_directory: str | Path,
        invocation_nonce: str,
        invocation_context_digest: str,
        timeout_seconds: int | None = None,
        extra_environment: dict[str, str] | None = None,
    ) -> LocalVerifierResult:
        invocation_digest = local_verifier_invocation_digest(
            invocation_nonce=invocation_nonce,
            invocation_context_digest=invocation_context_digest,
        )
        spec = self._registry.resolve(verifier_id)
        cwd = self._policy.validate_working_directory(working_directory)
        requested_timeout = timeout_seconds or spec.allowed_timeout_seconds
        timeout = min(
            requested_timeout,
            spec.allowed_timeout_seconds,
            self._policy.timeout_seconds,
        )
        command = spec.command()
        environment = self._policy.environment(extra_environment)
        started = time.perf_counter()
        timed_out = False
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        if process.stdout is None or process.stderr is None:
            process.kill()
            raise VerifierError("verifier process capture pipes are unavailable")
        stdout_stream = process.stdout
        stderr_stream = process.stderr
        stdout_capture = _BoundedStreamCapture(self._policy.max_capture_bytes)
        stderr_capture = _BoundedStreamCapture(self._policy.max_capture_bytes)
        readers = (
            threading.Thread(
                target=_drain_stream,
                args=(stdout_stream, stdout_capture),
                daemon=True,
            ),
            threading.Thread(
                target=_drain_stream,
                args=(stderr_stream, stderr_capture),
                daemon=True,
            ),
        )
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=PROCESS_KILL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        stdout_snapshot, stderr_snapshot = _finish_stream_capture(
            readers,
            (stdout_stream, stderr_stream),
            (stdout_capture, stderr_capture),
        )
        elapsed = time.perf_counter() - started
        stdout = stdout_snapshot.value
        stderr = stderr_snapshot.value
        exit_code = None if timed_out else process.returncode
        output_limit_exceeded = stdout_snapshot.overflow or stderr_snapshot.overflow
        capture_incomplete = stdout_snapshot.incomplete or stderr_snapshot.incomplete
        missing_exit_status = not timed_out and exit_code is None
        reason_codes: list[str] = []
        failure_reasons: list[str] = []
        if exit_code not in {None, 0}:
            reason_codes.append("nonzero_exit")
            failure_reasons.append(f"verifier exited with code {exit_code}")
        if timed_out:
            reason_codes.append("timeout")
            failure_reasons.append(f"verifier timed out after {timeout} seconds")
        if output_limit_exceeded:
            reason_codes.append("output_limit")
            failure_reasons.append("output_limit")
        if capture_incomplete:
            reason_codes.append("output_capture_incomplete")
            failure_reasons.append("output_capture_incomplete")
        if missing_exit_status:
            reason_codes.append("operational_error")
            failure_reasons.append("operational_error")
        error_code: str | None = None
        if output_limit_exceeded:
            error_code = "output_limit"
        elif timed_out:
            error_code = "timeout"
        elif capture_incomplete:
            error_code = "output_capture_incomplete"
        elif missing_exit_status:
            error_code = "operational_error"
        passed = exit_code == 0 and error_code is None
        stdout_digest = sha256_digest(stdout)
        stderr_digest = sha256_digest(stderr)
        metrics = _extract_metrics(stdout) if passed else {}
        metrics.update(
            {
                "exit_code": exit_code,
                "elapsed_seconds": round(elapsed, 6),
                "timed_out": timed_out,
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
                "stdout_observed_bytes": stdout_snapshot.observed_bytes,
                "stderr_observed_bytes": stderr_snapshot.observed_bytes,
                "stdout_truncated": stdout_snapshot.truncated,
                "stderr_truncated": stderr_snapshot.truncated,
                "stdout_overflow": stdout_snapshot.overflow,
                "stderr_overflow": stderr_snapshot.overflow,
                "stdout_capture_incomplete": stdout_snapshot.incomplete,
                "stderr_capture_incomplete": stderr_snapshot.incomplete,
                "runner_status": (
                    "error" if error_code is not None else ("passed" if passed else "failed")
                ),
                "runner_reason_codes": sorted(reason_codes),
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
                "stdout_truncated": stdout_snapshot.truncated,
                "stderr_truncated": stderr_snapshot.truncated,
                "stdout_overflow": stdout_snapshot.overflow,
                "stderr_overflow": stderr_snapshot.overflow,
                "stdout_capture_incomplete": stdout_snapshot.incomplete,
                "stderr_capture_incomplete": stderr_snapshot.incomplete,
                "runner_error_code": error_code,
                "runner_reason_codes": sorted(reason_codes),
                "runner": "local",
                "shell": False,
                "runner_policy_digest": self._policy.digest(),
                "network_isolation": self._policy.network_isolation,
                "invocation_nonce": invocation_nonce,
                "invocation_context_digest": invocation_context_digest,
                "invocation_digest": invocation_digest,
            },
        )
        return LocalVerifierResult(
            verifier_run=verifier_run,
            invocation_nonce=invocation_nonce,
            invocation_context_digest=invocation_context_digest,
            invocation_digest=invocation_digest,
            stdout_digest=stdout_digest,
            stderr_digest=stderr_digest,
            elapsed_seconds=elapsed,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_truncated=stdout_snapshot.truncated,
            stderr_truncated=stderr_snapshot.truncated,
            stdout_overflow=stdout_snapshot.overflow,
            stderr_overflow=stderr_snapshot.overflow,
            stdout_capture_incomplete=stdout_snapshot.incomplete,
            stderr_capture_incomplete=stderr_snapshot.incomplete,
            error_code=error_code,
        )


def run_registered_verifier(
    registry: VerifierRegistry,
    verifier_id: str,
    *,
    working_directory: str | Path,
    timeout_seconds: int | None = None,
    policy: RunnerPolicy | None = None,
) -> VerifierRun:
    runner = LocalVerifierRunner(registry, policy=policy)
    invocation_context_digest = sha256_digest(
        {
            "schema": "faber.registered_verifier_invocation_context.v1",
            "verifier_registry_digest": registry.digest(),
            "verifier_id": verifier_id,
            "working_directory": str(Path(working_directory).resolve()),
            "timeout_seconds": timeout_seconds,
            "runner_policy_digest": runner.runner_policy_digest,
        }
    )
    return runner.run(
        verifier_id,
        working_directory=working_directory,
        invocation_nonce=new_local_verifier_invocation_nonce(),
        invocation_context_digest=invocation_context_digest,
        timeout_seconds=timeout_seconds,
    ).verifier_run


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
