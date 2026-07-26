"""Bounded executors for repository-owner-approved proof catalog capabilities.

The model-facing selection contributes only schema-validated JSON values.  Every
operational identity used below -- verifier, node ID, module, callable, path, timeout,
environment, and assertion policy -- comes from a typed ``ProofCatalogEntry``.

These local executors are development infrastructure, not a production sandbox.  They
disable shell execution, use a minimal environment, bound process I/O, and preserve the
existing authoritative ``VerifierRun``/receipt boundary for the workflow layer.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

from faber.artifact_validation import (
    ArtifactValidationResult,
    validate_attempt_file,
    validate_trace_file,
    validate_trajectory_file,
)
from faber.canonical_json import canonical_json, canonical_json_bytes
from faber.digests import sha256_digest
from faber.errors import ValidationError, VerifierError
from faber.proof_catalog import (
    ArtifactValidatorCapability,
    ExistingCommandCapability,
    FileInvariantCapability,
    ProofCatalogEntry,
    PytestNodeCapability,
    PythonCallCapability,
)
from faber.proof_runtime_helper import PROTOCOL_VERSION, json_values_equal
from faber.redaction import default_sensitive_patterns, detect_sensitive_fields
from faber.runner.local import LocalVerifierResult, LocalVerifierRunner, RunnerPolicy
from faber.validation import require_digest, require_non_empty_string
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec

EXECUTION_STATUSES = frozenset({"passed", "failed", "error", "missing"})
EXECUTION_ERROR_CODES = frozenset(
    {
        "invalid_capability",
        "invalid_parameters",
        "invalid_path",
        "registry_mismatch",
        "environment_not_allowed",
        "timeout",
        "input_limit",
        "output_limit",
        "output_capture_incomplete",
        "operational_error",
    }
)
MAX_DIAGNOSTIC_BYTES = 16_384
DEFAULT_MAX_INPUT_BYTES = 1_048_576
MAX_PROCESS_OUTPUT_BYTES = 1_048_576
MAX_PROCESS_INPUT_BYTES = 65_536
MAX_TRUSTED_SOURCE_BYTES = 4_194_304
MAX_PROCESS_TIMEOUT_SECONDS = 300
PROCESS_PIPE_DRAIN_GRACE_SECONDS = 1.0
MAX_JSON_DEPTH = 16
MAX_JSON_ITEMS = 512
MAX_JSON_INTEGER = (1 << 63) - 1
_PYTEST_MODULE = "pytest"
_HELPER_REASON_CODES_BY_STATUS = {
    "passed": frozenset({"assertion_passed"}),
    "failed": frozenset(
        {
            "assertion_failed",
            "expected_exception_mismatch",
            "expected_exception_not_raised",
            "unexpected_exception",
        }
    ),
    "error": frozenset(
        {
            "helper_output_too_large",
            "protocol_error",
            "result_serialization_error",
            "target_import_error",
            "target_not_callable",
        }
    ),
}
_HELPER_PATH = Path(__file__).with_name("proof_runtime_helper.py").resolve()
_MODULE_NAME = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$", re.ASCII)
_SAFE_INTERNAL_ENVIRONMENT = {
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
_ESSENTIAL_HOST_ENVIRONMENT = frozenset({"SYSTEMROOT", "WINDIR"})


class ProofExecutionError(ValidationError):
    """Preflight or execution-boundary failure with a stable public code."""

    def __init__(self, code: str, public_message: str) -> None:
        if code not in EXECUTION_ERROR_CODES:
            raise ValidationError(f"unknown proof execution error code {code!r}")
        self.code = code
        self.public_message = require_non_empty_string(public_message, "public_message")
        super().__init__(f"{code}: {self.public_message}")


@dataclass(frozen=True)
class ProcessCapture:
    """Bounded result from one fixed, shell-free child process invocation."""

    argv: Sequence[str]
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float
    timed_out: bool
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    stdin_incomplete: bool = False
    stdout_capture_incomplete: bool = False
    stderr_capture_incomplete: bool = False

    def __post_init__(self) -> None:
        argv = tuple(self.argv)
        if not argv or any(not isinstance(item, str) or not item for item in argv):
            raise ValidationError("argv must contain non-empty strings")
        if self.exit_code is not None and (
            isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int)
        ):
            raise ValidationError("exit_code must be an integer or null")
        if not isinstance(self.stdout, bytes) or not isinstance(self.stderr, bytes):
            raise ValidationError("captured stdout and stderr must be bytes")
        if (
            isinstance(self.elapsed_seconds, bool)
            or not isinstance(self.elapsed_seconds, int | float)
            or not math.isfinite(self.elapsed_seconds)
            or self.elapsed_seconds < 0
        ):
            raise ValidationError("elapsed_seconds must be finite and non-negative")
        for field in (
            "timed_out",
            "stdout_truncated",
            "stderr_truncated",
            "stdin_incomplete",
            "stdout_capture_incomplete",
            "stderr_capture_incomplete",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ValidationError(f"{field} must be a boolean")
        object.__setattr__(self, "argv", argv)
        object.__setattr__(self, "elapsed_seconds", float(self.elapsed_seconds))

    @property
    def output_truncated(self) -> bool:
        return self.stdout_truncated or self.stderr_truncated

    @property
    def capture_incomplete(self) -> bool:
        return (
            self.stdin_incomplete
            or self.stdout_capture_incomplete
            or self.stderr_capture_incomplete
        )


class ProcessLauncher(Protocol):
    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
        stdin: bytes | None,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> ProcessCapture: ...


class ExistingVerifierRunner(Protocol):
    def run(
        self,
        verifier_id: str,
        *,
        working_directory: str | Path,
        timeout_seconds: int | None = None,
        extra_environment: dict[str, str] | None = None,
    ) -> LocalVerifierResult | VerifierRun: ...


@dataclass(frozen=True)
class ProofExecutionResult:
    """One bounded family outcome before workflow receipt/evidence construction."""

    family: str
    verifier_id: str
    verifier_version: str
    status: str
    reason_codes: Sequence[str]
    expected_summary: object
    observed_summary: object
    counterexample_summary: object | None
    verifier_run: VerifierRun | None
    elapsed_seconds: float
    timed_out: bool
    output_truncated: bool = False

    def __post_init__(self) -> None:
        require_non_empty_string(self.family, "family")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_non_empty_string(self.verifier_version, "verifier_version")
        if self.status not in EXECUTION_STATUSES:
            raise ValidationError(f"status must be one of {sorted(EXECUTION_STATUSES)}")
        if not isinstance(self.reason_codes, Sequence) or isinstance(
            self.reason_codes, str | bytes | bytearray
        ):
            raise ValidationError("reason_codes must be a sequence of strings")
        reasons = tuple(
            sorted({require_non_empty_string(item, "reason_code") for item in self.reason_codes})
        )
        if self.status == "passed" and reasons:
            raise ValidationError("passed execution cannot contain reason codes")
        if self.status != "passed" and not reasons:
            raise ValidationError("non-passing execution requires a reason code")
        if self.status == "passed" and self.counterexample_summary is not None:
            raise ValidationError("passed execution cannot contain a counterexample")
        if self.verifier_run is not None and not isinstance(self.verifier_run, VerifierRun):
            raise ValidationError("verifier_run must be VerifierRun or null")
        if (
            isinstance(self.elapsed_seconds, bool)
            or not isinstance(self.elapsed_seconds, int | float)
            or not math.isfinite(self.elapsed_seconds)
            or self.elapsed_seconds < 0
        ):
            raise ValidationError("elapsed_seconds must be finite and non-negative")
        for field in ("timed_out", "output_truncated"):
            if not isinstance(getattr(self, field), bool):
                raise ValidationError(f"{field} must be a boolean")
        for field in ("expected_summary", "observed_summary", "counterexample_summary"):
            value = getattr(self, field)
            try:
                size = len(canonical_json_bytes(value))
            except (TypeError, ValueError, RecursionError):
                raise ValidationError(f"{field} must be bounded canonical JSON") from None
            if size > MAX_DIAGNOSTIC_BYTES:
                raise ValidationError(f"{field} exceeds the diagnostic byte limit")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "elapsed_seconds", float(self.elapsed_seconds))

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "verifier_id": self.verifier_id,
            "verifier_version": self.verifier_version,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "expected_summary": self.expected_summary,
            "observed_summary": self.observed_summary,
            "counterexample_summary": self.counterexample_summary,
            "verifier_run": self.verifier_run.to_dict() if self.verifier_run else None,
            "elapsed_seconds": self.elapsed_seconds,
            "timed_out": self.timed_out,
            "output_truncated": self.output_truncated,
        }


class _BoundedCapture:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._parts: list[bytes] = []
        self._size = 0
        self.truncated = False
        self.incomplete = False
        self._lock = threading.Lock()

    def add(self, value: bytes) -> None:
        with self._lock:
            remaining = self._limit - self._size
            if remaining > 0:
                kept = value[:remaining]
                self._parts.append(kept)
                self._size += len(kept)
            if len(value) > remaining:
                self.truncated = True

    def mark_incomplete(self) -> None:
        with self._lock:
            self.incomplete = True

    def value(self) -> bytes:
        with self._lock:
            return b"".join(self._parts)


def _close_process_stream(stream: object) -> None:
    raw_stream = getattr(stream, "raw", None)
    close = getattr(raw_stream, "close", None)
    if not callable(close):
        close = getattr(stream, "close", None)
    if callable(close):
        try:
            close()
        except (OSError, ValueError):
            pass


def launch_bounded_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    stdin: bytes | None,
    timeout_seconds: int,
    max_output_bytes: int,
) -> ProcessCapture:
    """Launch a fixed argv with shell disabled and bounded concurrent pipe drains."""

    command = tuple(argv)
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ProofExecutionError("invalid_capability", "child argv is invalid")
    if not isinstance(cwd, Path) or not cwd.is_absolute() or not cwd.is_dir():
        raise ProofExecutionError("invalid_path", "child working directory is invalid")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or not 1 <= timeout_seconds <= MAX_PROCESS_TIMEOUT_SECONDS
    ):
        raise ProofExecutionError("invalid_capability", "child timeout is invalid")
    if (
        isinstance(max_output_bytes, bool)
        or not isinstance(max_output_bytes, int)
        or not 1 <= max_output_bytes <= MAX_PROCESS_OUTPUT_BYTES
    ):
        raise ProofExecutionError("invalid_capability", "child output limit is invalid")
    if stdin is not None and (not isinstance(stdin, bytes) or len(stdin) > MAX_PROCESS_INPUT_BYTES):
        raise ProofExecutionError("input_limit", "child input exceeds the byte limit")
    child_environment: dict[str, str] = {}
    for key, value in environment.items():
        if not isinstance(key, str) or not key or not isinstance(value, str):
            raise ProofExecutionError("environment_not_allowed", "child environment is invalid")
        child_environment[key] = value

    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=child_environment,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError:
        raise ProofExecutionError("operational_error", "child process could not start") from None
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ProofExecutionError("operational_error", "child process pipes are unavailable")

    stdout_capture = _BoundedCapture(max_output_bytes)
    stderr_capture = _BoundedCapture(max_output_bytes)

    def drain(stream: object, capture: _BoundedCapture) -> None:
        reader = getattr(stream, "read", None)
        if not callable(reader):
            capture.mark_incomplete()
            return
        try:
            while True:
                chunk = reader(8192)
                if not chunk:
                    return
                if type(chunk) is not bytes:
                    capture.mark_incomplete()
                    return
                capture.add(chunk)
        except (OSError, ValueError):
            capture.mark_incomplete()
            return

    readers = (
        threading.Thread(target=drain, args=(process.stdout, stdout_capture), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr_capture), daemon=True),
    )
    for reader_thread in readers:
        reader_thread.start()

    writer: threading.Thread | None = None
    input_incomplete = threading.Event()
    if stdin is not None and process.stdin is not None:
        input_bytes = stdin
        input_stream = process.stdin

        def write_input() -> None:
            try:
                input_stream.write(input_bytes)
                input_stream.flush()
            except (OSError, ValueError):
                input_incomplete.set()
            finally:
                try:
                    input_stream.close()
                except (OSError, ValueError):
                    pass

        writer = threading.Thread(target=write_input, daemon=True)
        writer.start()

    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
    drain_deadline = time.perf_counter() + PROCESS_PIPE_DRAIN_GRACE_SECONDS
    for reader_thread in readers:
        reader_thread.join(timeout=max(0.0, drain_deadline - time.perf_counter()))
    for reader_thread, stream, capture in zip(
        readers,
        (process.stdout, process.stderr),
        (stdout_capture, stderr_capture),
        strict=True,
    ):
        if reader_thread.is_alive():
            capture.mark_incomplete()
            threading.Thread(
                target=_close_process_stream,
                args=(stream,),
                daemon=True,
            ).start()
    close_deadline = time.perf_counter() + 0.1
    for reader_thread in readers:
        if reader_thread.is_alive():
            reader_thread.join(timeout=max(0.0, close_deadline - time.perf_counter()))
    if writer is not None:
        writer.join(timeout=max(0.0, drain_deadline - time.perf_counter()))
        if writer.is_alive() and process.stdin is not None:
            input_incomplete.set()
            threading.Thread(
                target=_close_process_stream,
                args=(process.stdin,),
                daemon=True,
            ).start()
    elapsed = time.perf_counter() - started
    return ProcessCapture(
        argv=command,
        exit_code=None if timed_out else process.returncode,
        stdout=stdout_capture.value(),
        stderr=stderr_capture.value(),
        elapsed_seconds=elapsed,
        timed_out=timed_out,
        stdout_truncated=stdout_capture.truncated,
        stderr_truncated=stderr_capture.truncated,
        stdin_incomplete=input_incomplete.is_set(),
        stdout_capture_incomplete=stdout_capture.incomplete,
        stderr_capture_incomplete=stderr_capture.incomplete,
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_catalog_path(
    repository_root: str | Path,
    relative_location: str,
    *,
    must_exist: bool = False,
    require_file: bool | None = None,
) -> Path:
    """Resolve one normalized catalog-owned relative path without repository escape."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError):
        raise ProofExecutionError("invalid_path", "repository root is unavailable") from None
    if not root.is_dir():
        raise ProofExecutionError("invalid_path", "repository root must be a directory")
    if not isinstance(relative_location, str) or not relative_location.strip():
        raise ProofExecutionError("invalid_path", "catalog path must be non-empty text")
    if "\x00" in relative_location or "\\" in relative_location or ":" in relative_location:
        raise ProofExecutionError("invalid_path", "catalog path is not normalized")
    posix = PurePosixPath(relative_location)
    windows = PureWindowsPath(relative_location)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise ProofExecutionError("invalid_path", "catalog path must be repository-relative")
    if ".." in posix.parts or any(part in {"", "."} for part in posix.parts[:-1]):
        raise ProofExecutionError("invalid_path", "catalog path contains traversal")
    normalized = posix.as_posix()
    if normalized not in {".", relative_location.rstrip("/")}:
        raise ProofExecutionError("invalid_path", "catalog path is not normalized")
    candidate = root.joinpath(*posix.parts)
    try:
        resolved = candidate.resolve(strict=must_exist)
    except (OSError, RuntimeError):
        raise ProofExecutionError("invalid_path", "catalog path is unavailable") from None
    if not _is_within(resolved, root):
        raise ProofExecutionError("invalid_path", "catalog path escapes the repository root")
    if must_exist and not resolved.exists():
        raise ProofExecutionError("invalid_path", "catalog path does not exist")
    if require_file is True and resolved.exists() and not resolved.is_file():
        raise ProofExecutionError("invalid_path", "catalog path must be a file")
    if require_file is False and resolved.exists() and not resolved.is_dir():
        raise ProofExecutionError("invalid_path", "catalog path must be a directory")
    return resolved


def _policy_environment(
    raw_environment: object,
    allowed_environment_variables: Sequence[str],
) -> dict[str, str]:
    if not isinstance(raw_environment, Mapping):
        raise ProofExecutionError(
            "environment_not_allowed", "catalog environment must be a mapping"
        )
    allowed = set(allowed_environment_variables)
    result = dict(_SAFE_INTERNAL_ENVIRONMENT)
    for key in _ESSENTIAL_HOST_ENVIRONMENT:
        value = os.environ.get(key) if key in allowed else None
        if value is not None:
            result[key] = value
    for key, value in raw_environment.items():
        if not isinstance(key, str) or not isinstance(value, str) or key not in allowed:
            raise ProofExecutionError(
                "environment_not_allowed",
                "catalog environment is outside the execution-policy allowlist",
            )
        if detect_sensitive_fields({key: value}, patterns=default_sensitive_patterns()):
            raise ProofExecutionError(
                "environment_not_allowed", "catalog environment contains secret-like data"
            )
        result[key] = value
    return result


def _resolve_registered_spec(
    entry: ProofCatalogEntry,
    registry: VerifierRegistry,
) -> VerifierSpec:
    policy = entry.capability.policy
    try:
        spec = registry.resolve(policy.verifier_id)
    except (ValidationError, VerifierError):
        raise ProofExecutionError(
            "registry_mismatch", "catalog verifier is not registered"
        ) from None
    if spec.version != policy.verifier_version:
        raise ProofExecutionError(
            "registry_mismatch", "catalog verifier version does not match the registry"
        )
    try:
        expected_digest = require_digest(
            policy.verifier_spec_digest,
            "verifier_spec_digest",
        )
    except ValidationError:
        raise ProofExecutionError(
            "registry_mismatch", "catalog verifier-spec digest is invalid"
        ) from None
    if spec.digest() != expected_digest:
        raise ProofExecutionError(
            "registry_mismatch", "catalog verifier spec does not match the registry"
        )
    return spec


def _verify_trusted_files(
    entry: ProofCatalogEntry,
    repository_root: Path,
    *,
    max_input_bytes: int,
) -> None:
    trusted_total_bytes = 0
    for relative_path, expected_digest in entry.capability.policy.trusted_file_digests.items():
        path = resolve_catalog_path(
            repository_root,
            relative_path,
            must_exist=True,
            require_file=True,
        )
        hasher = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                while chunk := stream.read(1_048_576):
                    trusted_total_bytes += len(chunk)
                    if trusted_total_bytes > min(
                        max_input_bytes,
                        MAX_TRUSTED_SOURCE_BYTES,
                    ):
                        raise ProofExecutionError(
                            "input_limit",
                            "trusted verifier files exceed the execution input limit",
                        )
                    hasher.update(chunk)
        except OSError:
            raise ProofExecutionError(
                "invalid_capability", "trusted verifier file is unavailable"
            ) from None
        actual_digest = f"sha256:{hasher.hexdigest()}"
        if actual_digest != expected_digest:
            raise ProofExecutionError(
                "registry_mismatch", "trusted verifier file digest does not match the catalog"
            )


def _trusted_file_payload(
    entry: ProofCatalogEntry,
    repository_root: Path,
) -> dict[str, str]:
    return {
        str(
            resolve_catalog_path(
                repository_root,
                relative_path,
                must_exist=True,
                require_file=True,
            )
        ): digest
        for relative_path, digest in entry.capability.policy.trusted_file_digests.items()
    }


def _capability_paths(entry: ProofCatalogEntry, repository_root: Path) -> None:
    capability = entry.capability
    working_directory = resolve_catalog_path(
        repository_root,
        capability.policy.working_directory,
        must_exist=True,
        require_file=False,
    )
    if isinstance(capability, PytestNodeCapability):
        if capability.python_module != _PYTEST_MODULE:
            raise ProofExecutionError(
                "invalid_capability", "pytest capability must use the fixed pytest module"
            )
        for node_id in capability.node_ids:
            node_path = node_id.split("::", 1)[0]
            resolve_catalog_path(
                working_directory,
                node_path,
                must_exist=True,
                require_file=True,
            )
    elif isinstance(capability, PythonCallCapability):
        import_root = resolve_catalog_path(
            repository_root,
            capability.import_root,
            must_exist=True,
            require_file=False,
        )
        resolve_catalog_path(
            import_root,
            capability.module_import_path,
            must_exist=True,
            require_file=True,
        )
        if not _MODULE_NAME.fullmatch(capability.module) or not _MODULE_NAME.fullmatch(
            capability.callable_name
        ):
            raise ProofExecutionError(
                "invalid_capability", "python-call target identity is malformed"
            )
        if capability.result_serializer != "json":
            raise ProofExecutionError(
                "invalid_capability", "python-call result serializer must be json"
            )
    elif isinstance(capability, FileInvariantCapability | ArtifactValidatorCapability):
        resolve_catalog_path(
            repository_root,
            capability.repository_path,
            must_exist=False,
            require_file=True,
        )


def preflight_catalog_entry(
    entry: ProofCatalogEntry,
    *,
    repository_root: str | Path,
    verifier_registry: VerifierRegistry,
    allowed_environment_variables: Sequence[str] = (),
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> None:
    """Validate operational authority without launching or creating temporary data."""

    if not isinstance(entry, ProofCatalogEntry):
        raise ProofExecutionError("invalid_capability", "entry must be ProofCatalogEntry")
    if not isinstance(verifier_registry, VerifierRegistry):
        raise ProofExecutionError("registry_mismatch", "verifier_registry must be VerifierRegistry")
    if (
        isinstance(max_input_bytes, bool)
        or not isinstance(max_input_bytes, int)
        or max_input_bytes < 1
    ):
        raise ProofExecutionError("input_limit", "max_input_bytes must be positive")
    root = resolve_catalog_path(repository_root, ".", must_exist=True, require_file=False)
    _resolve_registered_spec(entry, verifier_registry)
    _verify_trusted_files(entry, root, max_input_bytes=max_input_bytes)
    policy = entry.capability.policy
    _policy_environment(policy.environment_variables, allowed_environment_variables)
    if (
        isinstance(policy.timeout_seconds, bool)
        or not isinstance(policy.timeout_seconds, int)
        or not 1 <= policy.timeout_seconds <= MAX_PROCESS_TIMEOUT_SECONDS
    ):
        raise ProofExecutionError("invalid_capability", "capability timeout is invalid")
    if (
        isinstance(policy.max_output_bytes, bool)
        or not isinstance(policy.max_output_bytes, int)
        or not 1 <= policy.max_output_bytes <= MAX_PROCESS_OUTPUT_BYTES
    ):
        raise ProofExecutionError("invalid_capability", "capability output limit is invalid")
    _capability_paths(entry, root)


def _parameter(bound: Mapping[str, object], selector: str | None) -> object:
    if selector is None:
        return None
    if selector not in bound:
        raise ProofExecutionError(
            "invalid_parameters", "catalog parameter selector did not resolve"
        )
    return bound[selector]


def _python_call_values(
    capability: PythonCallCapability,
    bound: Mapping[str, object],
) -> tuple[list[object], dict[str, object], str, object]:
    positional_value = _parameter(bound, capability.positional_parameter)
    if capability.positional_parameter is None:
        positional: list[object] = []
    elif isinstance(positional_value, Sequence) and not isinstance(
        positional_value, str | bytes | bytearray
    ):
        positional = list(positional_value)
    else:
        positional = [positional_value]
    keyword_value = _parameter(bound, capability.keyword_parameter)
    if capability.keyword_parameter is None:
        keyword: dict[str, object] = {}
    elif isinstance(keyword_value, Mapping) and all(isinstance(key, str) for key in keyword_value):
        keyword = {str(key): value for key, value in keyword_value.items()}
    else:
        raise ProofExecutionError(
            "invalid_parameters", "python-call keyword parameter must be an object"
        )
    assertion_value = _parameter(bound, capability.assertion_parameter)
    assertion = (
        capability.default_assertion if capability.assertion_parameter is None else assertion_value
    )
    if not isinstance(assertion, str) or assertion not in set(capability.allowed_assertions):
        raise ProofExecutionError(
            "invalid_parameters", "python-call assertion is not catalog-approved"
        )
    expected = _parameter(bound, capability.expected_parameter)
    return positional, keyword, assertion, expected


def preflight_catalog_execution(
    entry: ProofCatalogEntry,
    parameters: Mapping[str, object],
    *,
    repository_root: str | Path,
    verifier_registry: VerifierRegistry,
    allowed_environment_variables: Sequence[str] = (),
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> Mapping[str, object]:
    """Bind inert parameters and preflight every family-specific value without launch."""

    if (
        isinstance(max_input_bytes, bool)
        or not isinstance(max_input_bytes, int)
        or max_input_bytes < 1
    ):
        raise ProofExecutionError("input_limit", "max_input_bytes must be positive")

    preflight_catalog_entry(
        entry,
        repository_root=repository_root,
        verifier_registry=verifier_registry,
        allowed_environment_variables=allowed_environment_variables,
        max_input_bytes=max_input_bytes,
    )
    try:
        bound = entry.bind_parameters(parameters)
    except ValidationError:
        raise ProofExecutionError(
            "invalid_parameters", "selection parameters failed catalog validation"
        ) from None
    capability = entry.capability
    if isinstance(capability, PythonCallCapability):
        positional, keyword, assertion, expected = _python_call_values(capability, bound)
        root = resolve_catalog_path(
            repository_root,
            ".",
            must_exist=True,
            require_file=False,
        )
        import_root = resolve_catalog_path(
            root,
            capability.import_root,
            must_exist=True,
            require_file=False,
        )
        module_file = resolve_catalog_path(
            import_root,
            capability.module_import_path,
            must_exist=True,
            require_file=True,
        )
        payload = {
            "protocol": PROTOCOL_VERSION,
            "repository_root": str(root),
            "import_root": str(import_root),
            "module": capability.module,
            "callable_name": capability.callable_name,
            "module_file": str(module_file),
            "trusted_file_digests": _trusted_file_payload(entry, root),
            "trusted_source_byte_limit": min(
                max_input_bytes,
                MAX_TRUSTED_SOURCE_BYTES,
            ),
            "positional_arguments": positional,
            "keyword_arguments": keyword,
            "assertion": assertion,
            "expected": expected,
            "result_serializer": capability.result_serializer,
        }
        try:
            encoded = canonical_json(payload).encode("utf-8")
        except (ValueError, RecursionError):
            raise ProofExecutionError(
                "invalid_parameters", "python-call payload is not bounded JSON"
            ) from None
        if len(encoded) > min(MAX_PROCESS_INPUT_BYTES, max_input_bytes):
            raise ProofExecutionError("input_limit", "python-call payload exceeds its byte limit")
    elif isinstance(capability, FileInvariantCapability):
        expected = _parameter(bound, capability.expected_parameter)
        pointer = _parameter(bound, capability.json_pointer_parameter)
        if capability.operation in {"contains_literal", "excludes_literal"} and not isinstance(
            expected, str
        ):
            raise ProofExecutionError(
                "invalid_parameters", "literal file invariant requires string expected data"
            )
        if capability.operation == "digest_equals":
            try:
                require_digest(expected, "expected")
            except ValidationError:
                raise ProofExecutionError(
                    "invalid_parameters", "digest invariant requires a digest expected value"
                ) from None
        if capability.operation == "json_pointer_equals" and not isinstance(pointer, str):
            raise ProofExecutionError(
                "invalid_parameters", "JSON pointer invariant requires a pointer string"
            )
    return bound


def _safe_diagnostic(value: object, *, field: str = "value", depth: int = 0) -> object:
    if depth > 6:
        return {"type": "depth_limited", "digest": sha256_digest(str(type(value)))}
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else "[non-finite]"
    if isinstance(value, str):
        findings = detect_sensitive_fields(
            {field: value},
            patterns=default_sensitive_patterns(),
        )
        encoded = value.encode("utf-8", errors="replace")
        if findings:
            return {"value": "[redacted]", "digest": sha256_digest(encoded), "bytes": len(encoded)}
        if len(encoded) > 512:
            return {"value": "[truncated]", "digest": sha256_digest(encoded), "bytes": len(encoded)}
        return value
    if isinstance(value, Mapping):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        mapping_result: dict[str, object] = {}
        for key, nested in items[:32]:
            key_text = str(key)
            if detect_sensitive_fields(
                {key_text: "present"}, patterns=default_sensitive_patterns()
            ):
                mapping_result[key_text] = "[redacted]"
            else:
                mapping_result[key_text] = _safe_diagnostic(nested, field=key_text, depth=depth + 1)
        if len(items) > 32:
            mapping_result["_truncated_fields"] = len(items) - 32
        return mapping_result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence_result = [
            _safe_diagnostic(item, field=f"{field}[{index}]", depth=depth + 1)
            for index, item in enumerate(value[:32])
        ]
        if len(value) > 32:
            sequence_result.append({"truncated_items": len(value) - 32})
        return sequence_result
    return {"type": type(value).__name__}


def _counterexample(
    *,
    input_summary: object,
    expected_summary: object,
    observed_summary: object,
    exception_type: str | None,
    reason_code: str,
) -> dict[str, object]:
    return {
        "input_summary": _safe_diagnostic(input_summary, field="input_summary"),
        "expected_summary": _safe_diagnostic(expected_summary, field="expected_summary"),
        "observed_summary": _safe_diagnostic(observed_summary, field="observed_summary"),
        "exception_type": _safe_diagnostic(exception_type, field="exception_type"),
        "reason_code": reason_code,
    }


def _process_observation(capture: ProcessCapture) -> dict[str, object]:
    return {
        "exit_code": capture.exit_code,
        "timed_out": capture.timed_out,
        "stdout_bytes": len(capture.stdout),
        "stderr_bytes": len(capture.stderr),
        "stdout_digest": sha256_digest(capture.stdout),
        "stderr_digest": sha256_digest(capture.stderr),
        "stdout_truncated": capture.stdout_truncated,
        "stderr_truncated": capture.stderr_truncated,
        "stdin_incomplete": capture.stdin_incomplete,
        "stdout_capture_incomplete": capture.stdout_capture_incomplete,
        "stderr_capture_incomplete": capture.stderr_capture_incomplete,
    }


def _make_process_run(
    entry: ProofCatalogEntry,
    capture: ProcessCapture,
    *,
    passed: bool,
    reason_codes: Sequence[str],
    extra_metrics: Mapping[str, object] | None = None,
) -> VerifierRun:
    observation = _process_observation(capture)
    metrics = dict(observation)
    if extra_metrics:
        metrics.update(extra_metrics)
    logs_digest = sha256_digest(
        {
            "stdout_digest": observation["stdout_digest"],
            "stderr_digest": observation["stderr_digest"],
        }
    )
    return VerifierRun(
        verifier_id=entry.capability.policy.verifier_id,
        name=f"Faber proof {entry.family}",
        version=entry.capability.policy.verifier_version,
        command=list(capture.argv),
        passed=passed,
        metrics=metrics,
        failure_reasons=list(sorted(set(reason_codes))),
        logs_digest=logs_digest,
        metadata={
            "family": entry.family,
            "capability_digest": entry.capability_digest(),
            "shell": False,
            "isolation": "local-development-runner-no-network-isolation",
        },
    )


def _make_internal_run(
    entry: ProofCatalogEntry,
    *,
    passed: bool,
    reason_codes: Sequence[str],
    observed_summary: object,
    elapsed_seconds: float,
) -> VerifierRun:
    del elapsed_seconds
    return VerifierRun(
        verifier_id=entry.capability.policy.verifier_id,
        name=f"Faber proof {entry.family}",
        version=entry.capability.policy.verifier_version,
        command=["faber-proof", entry.family],
        passed=passed,
        metrics={
            "observation_digest": sha256_digest(observed_summary),
        },
        failure_reasons=list(sorted(set(reason_codes))),
        logs_digest=sha256_digest(observed_summary),
        metadata={
            "family": entry.family,
            "capability_digest": entry.capability_digest(),
            "shell": False,
            "isolation": "in-process-bounded-observation",
        },
    )


def _result(
    entry: ProofCatalogEntry,
    *,
    status: str,
    reasons: Sequence[str],
    expected: object,
    observed: object,
    counterexample: object | None,
    run: VerifierRun | None,
    elapsed_seconds: float,
    timed_out: bool = False,
    output_truncated: bool = False,
) -> ProofExecutionResult:
    return ProofExecutionResult(
        family=entry.family,
        verifier_id=entry.capability.policy.verifier_id,
        verifier_version=entry.capability.policy.verifier_version,
        status=status,
        reason_codes=reasons,
        expected_summary=_safe_diagnostic(expected, field="expected"),
        observed_summary=_safe_diagnostic(observed, field="observed"),
        counterexample_summary=(
            _safe_diagnostic(counterexample, field="counterexample")
            if counterexample is not None
            else None
        ),
        verifier_run=run,
        elapsed_seconds=elapsed_seconds,
        timed_out=timed_out,
        output_truncated=output_truncated,
    )


def _execute_existing_command(
    entry: ProofCatalogEntry,
    *,
    root: Path,
    registry: VerifierRegistry,
    runner: ExistingVerifierRunner | None,
    runner_policy: RunnerPolicy | None,
    allowed_environment_variables: Sequence[str],
) -> ProofExecutionResult:
    capability = entry.capability
    if not isinstance(capability, ExistingCommandCapability):
        raise AssertionError("existing-command dispatcher received wrong capability")
    policy = capability.policy
    registered_spec = _resolve_registered_spec(entry, registry)
    cwd = resolve_catalog_path(root, policy.working_directory, must_exist=True, require_file=False)
    environment = _policy_environment(policy.environment_variables, allowed_environment_variables)
    entry_runner_policy = RunnerPolicy(
        allowed_working_directory_root=str(root),
        network_isolation=(
            runner_policy.network_isolation
            if runner_policy is not None
            else "none-local-runner-does-not-isolate-network"
        ),
        allowed_environment_variables=sorted(environment),
        timeout_seconds=policy.timeout_seconds,
        max_capture_bytes=policy.max_output_bytes,
        allow_shell=False,
    )
    expected_runner_policy_digest = entry_runner_policy.digest()
    actual_runner: ExistingVerifierRunner
    if runner is None:
        actual_runner = LocalVerifierRunner(registry, entry_runner_policy)
    else:
        if getattr(runner, "runner_policy_digest", None) != expected_runner_policy_digest:
            return _result(
                entry,
                status="error",
                reasons=["registry_mismatch"],
                expected={"runner_policy_digest": expected_runner_policy_digest},
                observed={"runner_policy_bound": False},
                counterexample=_counterexample(
                    input_summary={"family": entry.family},
                    expected_summary={"runner_policy_bound": True},
                    observed_summary={"runner_policy_bound": False},
                    exception_type=None,
                    reason_code="registry_mismatch",
                ),
                run=None,
                elapsed_seconds=0.0,
            )
        actual_runner = runner
    started = time.perf_counter()
    try:
        raw_result = actual_runner.run(
            policy.verifier_id,
            working_directory=cwd,
            timeout_seconds=policy.timeout_seconds,
            extra_environment=dict(environment),
        )
    except (OSError, ValidationError, VerifierError):
        elapsed = time.perf_counter() - started
        return _result(
            entry,
            status="error",
            reasons=["operational_error"],
            expected={"passed": True},
            observed={"available": False},
            counterexample=_counterexample(
                input_summary={"family": entry.family},
                expected_summary={"passed": True},
                observed_summary={"available": False},
                exception_type=None,
                reason_code="operational_error",
            ),
            run=None,
            elapsed_seconds=elapsed,
        )
    elapsed = time.perf_counter() - started
    if isinstance(raw_result, LocalVerifierResult):
        local_result: LocalVerifierResult | None = raw_result
        verifier_run = raw_result.verifier_run
    else:
        local_result = None
        verifier_run = raw_result
    if not isinstance(verifier_run, VerifierRun) or (
        verifier_run.verifier_id != policy.verifier_id
        or verifier_run.version != policy.verifier_version
    ):
        return _result(
            entry,
            status="error",
            reasons=["registry_mismatch"],
            expected={"passed": True},
            observed={"available": False},
            counterexample=_counterexample(
                input_summary={"family": entry.family},
                expected_summary={"passed": True},
                observed_summary={"available": False},
                exception_type=None,
                reason_code="registry_mismatch",
            ),
            run=None,
            elapsed_seconds=elapsed,
        )
    raw_verifier_run_digest = verifier_run.digest()
    raw_verifier_run_id = verifier_run.id
    metadata = dict(verifier_run.metadata)
    runner_binding_valid = (
        verifier_run.name == registered_spec.name
        and verifier_run.command == registered_spec.command()
        and metadata.get("approved_verifier_spec_digest") == registered_spec.digest()
        and metadata.get("shell") is False
        and metadata.get("runner_policy_digest") == expected_runner_policy_digest
        and metadata.get("working_directory") == str(cwd)
    )
    if not runner_binding_valid:
        return _result(
            entry,
            status="error",
            reasons=["registry_mismatch"],
            expected={"registered_spec_digest": registered_spec.digest()},
            observed={"runner_binding_valid": False},
            counterexample=_counterexample(
                input_summary={"family": entry.family},
                expected_summary={"runner_binding_valid": True},
                observed_summary={"runner_binding_valid": False},
                exception_type=None,
                reason_code="registry_mismatch",
            ),
            run=None,
            elapsed_seconds=elapsed,
        )
    verifier_run = VerifierRun(
        id=verifier_run.id,
        created_at=verifier_run.created_at,
        verifier_id=verifier_run.verifier_id,
        name=verifier_run.name,
        version=verifier_run.version,
        command=list(verifier_run.command),
        passed=verifier_run.passed,
        metrics=dict(verifier_run.metrics),
        failure_reasons=list(verifier_run.failure_reasons),
        logs_digest=verifier_run.logs_digest,
        metadata={
            **metadata,
            "family": entry.family,
            "catalog_entry_id": entry.id,
            "catalog_entry_version": entry.version,
            "capability_digest": entry.capability_digest(),
            "raw_verifier_run_digest": raw_verifier_run_digest,
            "raw_verifier_run_id": raw_verifier_run_id,
        },
    )
    timed_out = (
        local_result.timed_out
        if local_result is not None
        else bool(verifier_run.metrics.get("timed_out", False))
    )
    output_truncated = (
        local_result.stdout_truncated or local_result.stderr_truncated
        if local_result is not None
        else bool(
            metadata.get("stdout_truncated", False) or metadata.get("stderr_truncated", False)
        )
    )
    runner_error = (
        local_result.error_code if local_result is not None else metadata.get("runner_error_code")
    )
    if local_result is not None and local_result.status == "error" and runner_error is None:
        if local_result.output_limit_exceeded:
            runner_error = "output_limit"
        elif local_result.capture_incomplete:
            runner_error = "output_capture_incomplete"
        else:
            runner_error = "operational_error"
    if output_truncated and runner_error is None:
        runner_error = "output_limit"
    if runner_error not in {
        None,
        "operational_error",
        "output_capture_incomplete",
        "output_limit",
        "timeout",
    }:
        runner_error = "operational_error"
    if timed_out:
        runner_error = "timeout"
    if runner_error is not None:
        status = "error"
        reason = str(runner_error)
    else:
        status = "passed" if verifier_run.passed else "failed"
        reason = "" if status == "passed" else "verifier_failed"
    observed = {
        "passed": verifier_run.passed,
        "result_digest": verifier_run.result_digest(),
        "logs_digest": verifier_run.logs_digest,
        "timed_out": timed_out,
        "output_truncated": output_truncated,
        "runner_error_code": runner_error,
    }
    return _result(
        entry,
        status=status,
        reasons=[] if status == "passed" else [reason],
        expected={"passed": True},
        observed=observed,
        counterexample=(
            None
            if status == "passed"
            else _counterexample(
                input_summary={"family": entry.family},
                expected_summary={"passed": True},
                observed_summary=observed,
                exception_type=None,
                reason_code=reason,
            )
        ),
        run=verifier_run if status in {"passed", "failed"} else None,
        elapsed_seconds=(local_result.elapsed_seconds if local_result else elapsed),
        timed_out=timed_out,
        output_truncated=output_truncated,
    )


def _launch_child(
    entry: ProofCatalogEntry,
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    stdin: bytes | None,
    launcher: ProcessLauncher,
) -> ProcessCapture:
    try:
        capture = launcher(
            argv,
            cwd=cwd,
            environment=environment,
            stdin=stdin,
            timeout_seconds=entry.capability.policy.timeout_seconds,
            max_output_bytes=entry.capability.policy.max_output_bytes,
        )
    except ProofExecutionError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise ProofExecutionError("operational_error", "proof child process failed") from None
    if tuple(capture.argv) != tuple(argv):
        raise ProofExecutionError(
            "operational_error", "proof child capture does not bind the requested argv"
        )
    limit = entry.capability.policy.max_output_bytes
    stdout_truncated = capture.stdout_truncated or len(capture.stdout) > limit
    stderr_truncated = capture.stderr_truncated or len(capture.stderr) > limit
    if stdout_truncated or stderr_truncated:
        return ProcessCapture(
            argv=capture.argv,
            exit_code=capture.exit_code,
            stdout=capture.stdout[:limit],
            stderr=capture.stderr[:limit],
            elapsed_seconds=capture.elapsed_seconds,
            timed_out=capture.timed_out,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stdin_incomplete=capture.stdin_incomplete,
            stdout_capture_incomplete=capture.stdout_capture_incomplete,
            stderr_capture_incomplete=capture.stderr_capture_incomplete,
        )
    return capture


def _execute_pytest(
    entry: ProofCatalogEntry,
    *,
    root: Path,
    launcher: ProcessLauncher,
    allowed_environment_variables: Sequence[str],
) -> ProofExecutionResult:
    capability = entry.capability
    if not isinstance(capability, PytestNodeCapability):
        raise AssertionError("pytest dispatcher received wrong capability")
    cwd = resolve_catalog_path(
        root,
        capability.policy.working_directory,
        must_exist=True,
        require_file=False,
    )
    environment = _policy_environment(
        capability.policy.environment_variables,
        allowed_environment_variables,
    )
    environment = {
        **environment,
        "PYTEST_ADDOPTS": "",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_PLUGINS": "",
    }
    try:
        with tempfile.TemporaryDirectory(prefix="faber-proof-runtime-") as runtime_root:
            runtime_path = Path(runtime_root)
            cache_root = runtime_path / "pycache"
            cache_root.mkdir()
            config_path = runtime_path / "pytest.ini"
            config_path.write_text("[pytest]\n", encoding="utf-8")
            argv = [
                sys.executable,
                "-I",
                "-B",
                "-X",
                f"pycache_prefix={cache_root}",
                "-m",
                _PYTEST_MODULE,
                "-c",
                str(config_path),
                "--noconftest",
                "-p",
                "no:cacheprovider",
                "--quiet",
                "--",
                *capability.node_ids,
            ]
            capture = _launch_child(
                entry,
                argv,
                cwd=cwd,
                environment=environment,
                stdin=None,
                launcher=launcher,
            )
    except OSError:
        raise ProofExecutionError(
            "operational_error",
            "pytest runtime directory could not be prepared",
        ) from None
    observation = _process_observation(capture)
    if capture.timed_out:
        status, reason = "error", "timeout"
    elif capture.capture_incomplete:
        status, reason = "error", "output_capture_incomplete"
    elif capture.output_truncated:
        status, reason = "error", "output_limit"
    elif capture.exit_code == 0:
        status, reason = "passed", ""
    elif capture.exit_code == 1:
        status, reason = "failed", "pytest_failed"
    else:
        status, reason = "error", "operational_error"
    reasons = [] if status == "passed" else [reason]
    run = _make_process_run(
        entry,
        capture,
        passed=status == "passed",
        reason_codes=reasons,
        extra_metrics={"approved_node_count": len(capability.node_ids)},
    )
    expected = {"exit_code": 0, "approved_node_count": len(capability.node_ids)}
    return _result(
        entry,
        status=status,
        reasons=reasons,
        expected=expected,
        observed=observation,
        counterexample=(
            None
            if status == "passed"
            else _counterexample(
                input_summary={"approved_node_count": len(capability.node_ids)},
                expected_summary=expected,
                observed_summary=observation,
                exception_type=None,
                reason_code=reason,
            )
        ),
        run=run,
        elapsed_seconds=capture.elapsed_seconds,
        timed_out=capture.timed_out,
        output_truncated=capture.output_truncated,
    )


def _strict_helper_response(value: bytes) -> Mapping[str, object]:
    if len(value) > MAX_PROCESS_INPUT_BYTES:
        raise ProofExecutionError("output_limit", "python helper output exceeds its limit")

    def closed(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = item
        return result

    try:
        payload = json.loads(
            value.decode("utf-8", errors="strict"),
            object_pairs_hook=closed,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
        )
        canonical_json_bytes(payload)
    except (ValueError, RecursionError):
        raise ProofExecutionError(
            "operational_error", "python helper returned malformed output"
        ) from None
    fields = {
        "protocol",
        "status",
        "reason_code",
        "input_summary",
        "expected_summary",
        "observed_summary",
        "exception_type",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ProofExecutionError(
            "operational_error", "python helper returned the wrong protocol shape"
        )
    if payload.get("protocol") != PROTOCOL_VERSION:
        raise ProofExecutionError("operational_error", "python helper protocol version mismatch")
    status = payload.get("status")
    reason = payload.get("reason_code")
    if (
        status not in _HELPER_REASON_CODES_BY_STATUS
        or not isinstance(reason, str)
        or reason not in _HELPER_REASON_CODES_BY_STATUS[str(status)]
    ):
        raise ProofExecutionError("operational_error", "python helper returned an invalid outcome")
    return payload


def _execute_python_call(
    entry: ProofCatalogEntry,
    bound: Mapping[str, object],
    *,
    root: Path,
    launcher: ProcessLauncher,
    allowed_environment_variables: Sequence[str],
    max_input_bytes: int,
) -> ProofExecutionResult:
    capability = entry.capability
    if not isinstance(capability, PythonCallCapability):
        raise AssertionError("python-call dispatcher received wrong capability")
    positional, keyword, assertion, expected = _python_call_values(capability, bound)
    cwd = resolve_catalog_path(
        root,
        capability.policy.working_directory,
        must_exist=True,
        require_file=False,
    )
    import_root = resolve_catalog_path(
        root,
        capability.import_root,
        must_exist=True,
        require_file=False,
    )
    module_file = resolve_catalog_path(
        import_root,
        capability.module_import_path,
        must_exist=True,
        require_file=True,
    )
    environment = _policy_environment(
        capability.policy.environment_variables,
        allowed_environment_variables,
    )
    payload = {
        "protocol": PROTOCOL_VERSION,
        "repository_root": str(root),
        "import_root": str(import_root),
        "module": capability.module,
        "callable_name": capability.callable_name,
        "module_file": str(module_file),
        "trusted_file_digests": _trusted_file_payload(entry, root),
        "trusted_source_byte_limit": min(
            max_input_bytes,
            MAX_TRUSTED_SOURCE_BYTES,
        ),
        "positional_arguments": positional,
        "keyword_arguments": keyword,
        "assertion": assertion,
        "expected": expected,
        "result_serializer": capability.result_serializer,
    }
    try:
        stdin = canonical_json(payload).encode("utf-8")
    except (ValueError, RecursionError):
        raise ProofExecutionError(
            "invalid_parameters", "python-call payload is not bounded JSON"
        ) from None
    if len(stdin) > min(MAX_PROCESS_INPUT_BYTES, max_input_bytes):
        raise ProofExecutionError("input_limit", "python-call payload exceeds its byte limit")
    argv = [sys.executable, "-I", str(_HELPER_PATH)]
    capture = _launch_child(
        entry,
        argv,
        cwd=cwd,
        environment=environment,
        stdin=stdin,
        launcher=launcher,
    )
    process_observation = _process_observation(capture)
    if capture.timed_out:
        reason = "timeout"
        run = _make_process_run(
            entry,
            capture,
            passed=False,
            reason_codes=[reason],
        )
        return _result(
            entry,
            status="error",
            reasons=[reason],
            expected={"assertion": assertion},
            observed=process_observation,
            counterexample=_counterexample(
                input_summary={"parameters_digest": sha256_digest(bound)},
                expected_summary={"assertion": assertion},
                observed_summary=process_observation,
                exception_type=None,
                reason_code=reason,
            ),
            run=run,
            elapsed_seconds=capture.elapsed_seconds,
            timed_out=True,
        )
    if capture.capture_incomplete:
        reason = "output_capture_incomplete"
        run = _make_process_run(
            entry,
            capture,
            passed=False,
            reason_codes=[reason],
        )
        return _result(
            entry,
            status="error",
            reasons=[reason],
            expected={"assertion": assertion},
            observed=process_observation,
            counterexample=_counterexample(
                input_summary={"parameters_digest": sha256_digest(bound)},
                expected_summary={"assertion": assertion},
                observed_summary=process_observation,
                exception_type=None,
                reason_code=reason,
            ),
            run=run,
            elapsed_seconds=capture.elapsed_seconds,
            output_truncated=capture.output_truncated,
        )
    if capture.output_truncated:
        reason = "output_limit"
        run = _make_process_run(
            entry,
            capture,
            passed=False,
            reason_codes=[reason],
        )
        return _result(
            entry,
            status="error",
            reasons=[reason],
            expected={"assertion": assertion},
            observed=process_observation,
            counterexample=_counterexample(
                input_summary={"parameters_digest": sha256_digest(bound)},
                expected_summary={"assertion": assertion},
                observed_summary=process_observation,
                exception_type=None,
                reason_code=reason,
            ),
            run=run,
            elapsed_seconds=capture.elapsed_seconds,
            output_truncated=True,
        )
    helper = _strict_helper_response(capture.stdout)
    helper_status = str(helper["status"])
    if (helper_status in {"passed", "failed"} and capture.exit_code != 0) or (
        helper_status == "error" and capture.exit_code not in {0, 2}
    ):
        raise ProofExecutionError(
            "operational_error", "python helper exit status contradicted its output"
        )
    reason = str(helper["reason_code"])
    reasons = [] if helper_status == "passed" else [reason]
    run = _make_process_run(
        entry,
        capture,
        passed=helper_status == "passed",
        reason_codes=reasons,
        extra_metrics={"assertion": assertion},
    )
    expected_summary = helper["expected_summary"]
    observed_summary = helper["observed_summary"]
    counterexample = (
        None
        if helper_status == "passed"
        else _counterexample(
            input_summary=helper["input_summary"],
            expected_summary=expected_summary,
            observed_summary=observed_summary,
            exception_type=(
                str(helper["exception_type"]) if helper["exception_type"] is not None else None
            ),
            reason_code=reason,
        )
    )
    return _result(
        entry,
        status=helper_status,
        reasons=reasons,
        expected=expected_summary,
        observed={
            "assertion": assertion,
            "result": observed_summary,
            "exception_type": helper["exception_type"],
            "process": process_observation,
        },
        counterexample=counterexample,
        run=run,
        elapsed_seconds=capture.elapsed_seconds,
    )


def _strict_json_bytes(value: bytes) -> object:
    def closed(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = item
        return result

    def integer(raw: str) -> int:
        parsed = int(raw)
        if abs(parsed) > MAX_JSON_INTEGER:
            raise ValueError("integer limit")
        return parsed

    def floating(raw: str) -> float:
        parsed = float(raw)
        if not math.isfinite(parsed):
            raise ValueError("finite numbers only")
        return parsed

    parsed = json.loads(
        value.decode("utf-8", errors="strict"),
        object_pairs_hook=closed,
        parse_int=integer,
        parse_float=floating,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
    )
    _validate_json_shape(parsed)
    return parsed


def _validate_json_shape(value: object, *, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("JSON nesting limit exceeded")
    if value is None or isinstance(value, bool | str):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_JSON_INTEGER:
            raise ValueError("JSON integer limit exceeded")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON number must be finite")
        return
    if isinstance(value, list):
        if len(value) > MAX_JSON_ITEMS:
            raise ValueError("JSON array item limit exceeded")
        for item in value:
            _validate_json_shape(item, depth=depth + 1)
        return
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_ITEMS:
            raise ValueError("JSON object field limit exceeded")
        for item in value.values():
            _validate_json_shape(item, depth=depth + 1)
        return
    raise ValueError("unsupported JSON value")


def _json_pointer(document: object, pointer: str) -> object:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with slash")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if "~" in token and re.search(r"~(?![01])", raw_token):
            raise ValueError("invalid JSON pointer escape")
        if isinstance(current, Mapping):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise KeyError(token)
            index = int(token)
            if index >= len(current):
                raise KeyError(token)
            current = current[index]
        else:
            raise KeyError(token)
    return current


def _execute_file_invariant(
    entry: ProofCatalogEntry,
    bound: Mapping[str, object],
    *,
    root: Path,
    max_input_bytes: int,
) -> ProofExecutionResult:
    capability = entry.capability
    if not isinstance(capability, FileInvariantCapability):
        raise AssertionError("file dispatcher received wrong capability")
    started = time.perf_counter()
    path = resolve_catalog_path(
        root,
        capability.repository_path,
        must_exist=False,
        require_file=True,
    )
    operation = capability.operation
    expected = _parameter(bound, capability.expected_parameter)
    pointer = _parameter(bound, capability.json_pointer_parameter)
    exists = path.exists() or path.is_symlink()
    status = "failed"
    reason = "file_invariant_failed"
    observed: object = {"exists": exists}
    try:
        if operation == "exists":
            passed = exists and path.is_file()
        elif operation == "absent":
            passed = not exists
        elif not exists or not path.is_file():
            passed = False
            reason = "file_missing"
        else:
            with path.open("rb") as stream:
                content = stream.read(max_input_bytes + 1)
            if len(content) > max_input_bytes:
                elapsed = time.perf_counter() - started
                return _result(
                    entry,
                    status="error",
                    reasons=["input_limit"],
                    expected={"operation": operation},
                    observed={"exists": True, "bytes": f">{max_input_bytes}"},
                    counterexample=_counterexample(
                        input_summary={"operation": operation},
                        expected_summary={"max_input_bytes": max_input_bytes},
                        observed_summary={"bytes": f">{max_input_bytes}"},
                        exception_type=None,
                        reason_code="input_limit",
                    ),
                    run=None,
                    elapsed_seconds=elapsed,
                )
            digest = sha256_digest(content)
            observed = {"exists": True, "bytes": len(content), "digest": digest}
            if operation == "digest_equals":
                passed = digest == expected
            elif operation in {"contains_literal", "excludes_literal"}:
                text = content.decode("utf-8", errors="strict")
                assert isinstance(expected, str)
                contains = expected in text
                observed = {**observed, "contains": contains}
                passed = contains if operation == "contains_literal" else not contains
            elif operation == "valid_json":
                _strict_json_bytes(content)
                observed = {**observed, "valid_json": True}
                passed = True
            elif operation == "json_pointer_equals":
                document = _strict_json_bytes(content)
                assert isinstance(pointer, str)
                value = _json_pointer(document, pointer)
                expected_json = _strict_json_bytes(canonical_json_bytes(expected))
                observed = {**observed, "pointer_value": _safe_diagnostic(value)}
                passed = json_values_equal(value, expected_json)
            else:
                raise ProofExecutionError(
                    "invalid_capability", "file invariant operation is unsupported"
                )
    except (ValueError, KeyError, RecursionError):
        passed = False
        reason = "file_content_invalid"
        observed = {"exists": exists, "valid": False}
    except OSError:
        elapsed = time.perf_counter() - started
        return _result(
            entry,
            status="error",
            reasons=["operational_error"],
            expected={"operation": operation},
            observed={"available": False},
            counterexample=_counterexample(
                input_summary={"operation": operation},
                expected_summary={"available": True},
                observed_summary={"available": False},
                exception_type=None,
                reason_code="operational_error",
            ),
            run=None,
            elapsed_seconds=elapsed,
        )
    if passed:
        status = "passed"
        reasons: list[str] = []
    else:
        reasons = [reason]
    elapsed = time.perf_counter() - started
    expected_summary = {
        "operation": operation,
        "expected": _safe_diagnostic(expected, field="expected"),
        "json_pointer": pointer if isinstance(pointer, str) else None,
    }
    run = _make_internal_run(
        entry,
        passed=passed,
        reason_codes=reasons,
        observed_summary=observed,
        elapsed_seconds=elapsed,
    )
    return _result(
        entry,
        status=status,
        reasons=reasons,
        expected=expected_summary,
        observed=observed,
        counterexample=(
            None
            if passed
            else _counterexample(
                input_summary={"operation": operation},
                expected_summary=expected_summary,
                observed_summary=observed,
                exception_type=None,
                reason_code=reason,
            )
        ),
        run=run,
        elapsed_seconds=elapsed,
    )


def _artifact_validator(
    capability: ArtifactValidatorCapability,
) -> Callable[[Path], ArtifactValidationResult]:
    if capability.artifact_kind == "attempt_manifest":
        return validate_attempt_file
    if capability.artifact_kind == "trace":
        return validate_trace_file
    if capability.artifact_kind == "trajectory":
        return lambda path: validate_trajectory_file(path, quality_only=capability.quality_only)
    raise ProofExecutionError("invalid_capability", "artifact validator kind is unsupported")


def _execute_artifact_validator(
    entry: ProofCatalogEntry,
    *,
    root: Path,
    max_input_bytes: int,
) -> ProofExecutionResult:
    capability = entry.capability
    if not isinstance(capability, ArtifactValidatorCapability):
        raise AssertionError("artifact dispatcher received wrong capability")
    started = time.perf_counter()
    path = resolve_catalog_path(
        root,
        capability.repository_path,
        must_exist=False,
        require_file=True,
    )
    validator = _artifact_validator(capability)
    try:
        if path.exists() and path.is_file() and path.stat().st_size > max_input_bytes:
            elapsed = time.perf_counter() - started
            return _result(
                entry,
                status="error",
                reasons=["input_limit"],
                expected={"max_input_bytes": max_input_bytes},
                observed={"bytes": path.stat().st_size},
                counterexample=_counterexample(
                    input_summary={"artifact_kind": capability.artifact_kind},
                    expected_summary={"max_input_bytes": max_input_bytes},
                    observed_summary={"bytes": path.stat().st_size},
                    exception_type=None,
                    reason_code="input_limit",
                ),
                run=None,
                elapsed_seconds=elapsed,
            )
        report = validator(path)
    except (OSError, ValidationError):
        elapsed = time.perf_counter() - started
        return _result(
            entry,
            status="error",
            reasons=["operational_error"],
            expected={"artifact_status": "valid"},
            observed={"available": False},
            counterexample=_counterexample(
                input_summary={"artifact_kind": capability.artifact_kind},
                expected_summary={"artifact_status": "valid"},
                observed_summary={"available": False},
                exception_type=None,
                reason_code="operational_error",
            ),
            run=None,
            elapsed_seconds=elapsed,
        )
    if report.status == "valid":
        status, reasons = "passed", []
    elif report.status == "warning":
        status, reasons = "error", ["artifact_warning"]
    else:
        status, reasons = "failed", ["artifact_invalid"]
    observed = {
        "artifact_type": report.artifact_type,
        "status": report.status,
        "report_digest": sha256_digest(_safe_diagnostic(report.to_dict())),
        "warning_count": len(report.warnings),
        "error_count": len(report.errors),
    }
    elapsed = time.perf_counter() - started
    run = _make_internal_run(
        entry,
        passed=status == "passed",
        reason_codes=reasons,
        observed_summary=observed,
        elapsed_seconds=elapsed,
    )
    expected = {"artifact_status": "valid"}
    return _result(
        entry,
        status=status,
        reasons=reasons,
        expected=expected,
        observed=observed,
        counterexample=(
            None
            if status == "passed"
            else _counterexample(
                input_summary={"artifact_kind": capability.artifact_kind},
                expected_summary=expected,
                observed_summary=observed,
                exception_type=None,
                reason_code=reasons[0],
            )
        ),
        run=run,
        elapsed_seconds=elapsed,
    )


def execute_catalog_entry(
    entry: ProofCatalogEntry,
    parameters: Mapping[str, object],
    *,
    repository_root: str | Path,
    verifier_registry: VerifierRegistry,
    runner: ExistingVerifierRunner | None = None,
    runner_policy: RunnerPolicy | None = None,
    launcher: ProcessLauncher = launch_bounded_process,
    allowed_environment_variables: Sequence[str] = (),
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> ProofExecutionResult:
    """Preflight then execute one exact typed catalog capability."""

    if (
        isinstance(max_input_bytes, bool)
        or not isinstance(max_input_bytes, int)
        or max_input_bytes < 1
    ):
        raise ProofExecutionError("input_limit", "max_input_bytes must be positive")
    bound = preflight_catalog_execution(
        entry,
        parameters,
        repository_root=repository_root,
        verifier_registry=verifier_registry,
        allowed_environment_variables=allowed_environment_variables,
        max_input_bytes=max_input_bytes,
    )
    root = resolve_catalog_path(repository_root, ".", must_exist=True, require_file=False)
    capability = entry.capability
    if isinstance(capability, ExistingCommandCapability):
        return _execute_existing_command(
            entry,
            root=root,
            registry=verifier_registry,
            runner=runner,
            runner_policy=runner_policy,
            allowed_environment_variables=allowed_environment_variables,
        )
    if isinstance(capability, PytestNodeCapability):
        return _execute_pytest(
            entry,
            root=root,
            launcher=launcher,
            allowed_environment_variables=allowed_environment_variables,
        )
    if isinstance(capability, PythonCallCapability):
        return _execute_python_call(
            entry,
            bound,
            root=root,
            launcher=launcher,
            allowed_environment_variables=allowed_environment_variables,
            max_input_bytes=max_input_bytes,
        )
    if isinstance(capability, FileInvariantCapability):
        return _execute_file_invariant(
            entry,
            bound,
            root=root,
            max_input_bytes=max_input_bytes,
        )
    if isinstance(capability, ArtifactValidatorCapability):
        return _execute_artifact_validator(
            entry,
            root=root,
            max_input_bytes=max_input_bytes,
        )
    raise ProofExecutionError("invalid_capability", "catalog capability family is unsupported")


class ProofExecutorRegistry:
    """Dependency-injected facade used by the provider-neutral proof workflow."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        verifier_registry: VerifierRegistry,
        runner: ExistingVerifierRunner | None = None,
        runner_policy: RunnerPolicy | None = None,
        launcher: ProcessLauncher = launch_bounded_process,
        allowed_environment_variables: Sequence[str] = (),
        max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    ) -> None:
        self.repository_root = resolve_catalog_path(
            repository_root,
            ".",
            must_exist=True,
            require_file=False,
        )
        self.verifier_registry = verifier_registry
        self.runner = runner
        self.runner_policy = runner_policy
        self.launcher = launcher
        self.allowed_environment_variables = tuple(allowed_environment_variables)
        self.max_input_bytes = max_input_bytes

    def preflight(
        self,
        entry: ProofCatalogEntry,
        parameters: Mapping[str, object],
    ) -> Mapping[str, object]:
        return preflight_catalog_execution(
            entry,
            parameters,
            repository_root=self.repository_root,
            verifier_registry=self.verifier_registry,
            allowed_environment_variables=self.allowed_environment_variables,
            max_input_bytes=self.max_input_bytes,
        )

    def execute(
        self,
        entry: ProofCatalogEntry,
        parameters: Mapping[str, object],
    ) -> ProofExecutionResult:
        return execute_catalog_entry(
            entry,
            parameters,
            repository_root=self.repository_root,
            verifier_registry=self.verifier_registry,
            runner=self.runner,
            runner_policy=self.runner_policy,
            launcher=self.launcher,
            allowed_environment_variables=self.allowed_environment_variables,
            max_input_bytes=self.max_input_bytes,
        )
