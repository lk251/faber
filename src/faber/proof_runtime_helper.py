"""Fixed child-process protocol for catalog-approved Python proof calls.

This module intentionally uses only the Python standard library.  The executor starts
it with isolated-mode Python and supplies one bounded JSON document on standard input.
Operational fields in that document are assembled from repository-owner-approved
catalog capability records; model output never supplies an import or callable name.

The helper is development infrastructure, not an operating-system sandbox.  Its job is
to keep the protocol small, serialize results deterministically, and ensure candidate
return values or exceptions cannot become unbounded persisted diagnostics.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import math
import re
import sys
import tempfile
import types
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import NoReturn, cast

PROTOCOL_VERSION = "faber.proof.python-call.v1"
ASSERTIONS = frozenset(
    {
        "equals",
        "not_equals",
        "is_none",
        "is_not_none",
        "raises",
        "contains",
        "truthy",
        "falsey",
    }
)
MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_BYTES = 32_768
MAX_JSON_DEPTH = 12
MAX_JSON_ITEMS = 256
MAX_TEXT_BYTES = 16_384
MAX_SUMMARY_DEPTH = 4
MAX_SUMMARY_ITEMS = 16
MAX_SUMMARY_TEXT_BYTES = 512
MAX_INTEGER = (1 << 63) - 1
MAX_TRUSTED_TOTAL_BYTES = 4_194_304

_PAYLOAD_FIELDS = {
    "protocol",
    "repository_root",
    "import_root",
    "module",
    "callable_name",
    "module_file",
    "trusted_file_digests",
    "trusted_source_byte_limit",
    "positional_arguments",
    "keyword_arguments",
    "assertion",
    "expected",
    "result_serializer",
}
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$", re.ASCII)
_DOTTED_IDENTIFIER = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$", re.ASCII)
_APPROVED_EXCEPTION_TYPES: Mapping[str, type[BaseException]] = {
    "builtins.ZeroDivisionError": ZeroDivisionError,
    "builtins.ArithmeticError": ArithmeticError,
    "builtins.AssertionError": AssertionError,
    "builtins.IndexError": IndexError,
    "builtins.KeyError": KeyError,
    "builtins.RuntimeError": RuntimeError,
    "builtins.TypeError": TypeError,
    "builtins.ValueError": ValueError,
}
_APPROVED_EXCEPTION_IDENTIFIERS = {
    exception_type: identifier for identifier, exception_type in _APPROVED_EXCEPTION_TYPES.items()
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_SECRET_FIELD_PATTERN = re.compile(
    r"(^|[_-])(api[_-]?key|authorization|password|secret|token)($|[_-])",
    re.IGNORECASE,
)


class ProtocolError(ValueError):
    """A stable, detail-free protocol failure."""


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate object key")
        result[key] = value
    return result


def _strict_integer(value: str) -> int:
    parsed = int(value)
    if abs(parsed) > MAX_INTEGER:
        raise ProtocolError("integer outside supported range")
    return parsed


def _strict_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ProtocolError("number must be finite")
    return parsed


def _reject_constant(_: str) -> NoReturn:
    raise ProtocolError("non-standard JSON constant")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _normalize_json(value: object, field: str, *, depth: int = 0) -> object:
    if depth > MAX_JSON_DEPTH:
        raise ProtocolError(f"{field} exceeds the nesting limit")
    value_type = type(value)
    if value is None or value_type is bool:
        return value
    if value_type is int:
        integer = cast(int, value)
        if abs(integer) > MAX_INTEGER:
            raise ProtocolError(f"{field} contains an integer outside the supported range")
        return integer
    if value_type is float:
        number = cast(float, value)
        if not math.isfinite(number):
            raise ProtocolError(f"{field} contains a non-finite number")
        return number
    if value_type is str:
        text = cast(str, value)
        try:
            size = len(text.encode("utf-8"))
        except UnicodeEncodeError:
            raise ProtocolError(f"{field} contains invalid UTF-8 text") from None
        if size > MAX_TEXT_BYTES:
            raise ProtocolError(f"{field} contains oversized text")
        return text
    if value_type is dict:
        if not isinstance(value, dict):
            raise AssertionError("exact dict type check must narrow to dict")
        if len(value) > MAX_JSON_ITEMS:
            raise ProtocolError(f"{field} contains too many object fields")
        result: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str or not key:
                raise ProtocolError(f"{field} must use non-empty string keys")
            result[key] = _normalize_json(item, f"{field}.{key}", depth=depth + 1)
        return result
    if value_type is list:
        if not isinstance(value, list):
            raise AssertionError("exact list type check must narrow to list")
        if len(value) > MAX_JSON_ITEMS:
            raise ProtocolError(f"{field} contains too many array items")
        return [
            _normalize_json(item, f"{field}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    raise ProtocolError(f"{field} is not JSON serializable")


def _parse_payload(raw: bytes) -> Mapping[str, object]:
    if len(raw) > MAX_INPUT_BYTES:
        raise ProtocolError("input exceeds the byte limit")
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(
            text,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_constant,
            parse_int=_strict_integer,
            parse_float=_strict_float,
        )
    except (ValueError, RecursionError):
        raise ProtocolError("input is not strict JSON") from None
    normalized = _normalize_json(payload, "payload")
    if not isinstance(normalized, Mapping):
        raise ProtocolError("payload root must be an object")
    if set(normalized) != _PAYLOAD_FIELDS:
        raise ProtocolError("payload does not match the closed protocol")
    if normalized.get("protocol") != PROTOCOL_VERSION:
        raise ProtocolError("protocol version mismatch")
    return normalized


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{field} must be non-empty text")
    return value


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validated_runtime_roots(payload: Mapping[str, object]) -> tuple[Path, Path]:
    repository_text = _required_text(payload, "repository_root")
    import_text = _required_text(payload, "import_root")
    repository_root = Path(repository_text)
    import_root = Path(import_text)
    if not repository_root.is_absolute() or not import_root.is_absolute():
        raise ProtocolError("runtime roots must be absolute")
    repository_root = repository_root.resolve(strict=True)
    import_root = import_root.resolve(strict=True)
    if not repository_root.is_dir() or not import_root.is_dir():
        raise ProtocolError("runtime roots must be directories")
    if not _is_within(import_root, repository_root):
        raise ProtocolError("import root is outside the repository root")
    return repository_root, import_root


def _read_trusted_file(
    path: Path,
    expected_digest: str,
    *,
    byte_limit: int,
    retain_source: bool,
) -> tuple[bytes | None, int]:
    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1_048_576):
                size += len(chunk)
                if size > byte_limit:
                    raise ProtocolError("trusted module file exceeds the byte limit")
                hasher.update(chunk)
                if retain_source:
                    chunks.append(chunk)
    except OSError:
        raise ProtocolError("trusted module file is unavailable") from None
    if f"sha256:{hasher.hexdigest()}" != expected_digest:
        raise ProtocolError("trusted module file digest mismatch")
    return (b"".join(chunks) if retain_source else None), size


def _validated_module_files(
    payload: Mapping[str, object],
    *,
    repository_root: Path,
    import_root: Path,
    module_name: str,
) -> tuple[Path, Mapping[str, Path], Mapping[Path, bytes]]:
    module_file_text = _required_text(payload, "module_file")
    module_file = Path(module_file_text)
    if not module_file.is_absolute():
        raise ProtocolError("module_file must be absolute")
    try:
        module_file = module_file.resolve(strict=True)
    except OSError:
        raise ProtocolError("module_file is unavailable") from None
    if not module_file.is_file() or not _is_within(module_file, import_root):
        raise ProtocolError("module_file is outside the approved import root")

    parts = module_name.split(".")
    module_stem = import_root.joinpath(*parts)
    allowed_targets = {
        module_stem.with_suffix(".py").resolve(strict=False),
        module_stem.joinpath("__init__.py").resolve(strict=False),
    }
    if module_file not in allowed_targets:
        raise ProtocolError("module_file does not match the approved module identity")

    prefix_origins: dict[str, Path] = {}
    for index in range(1, len(parts)):
        prefix = ".".join(parts[:index])
        origin = import_root.joinpath(*parts[:index], "__init__.py").resolve(strict=False)
        prefix_origins[prefix] = origin
    prefix_origins[module_name] = module_file
    required_origins = set(prefix_origins.values())

    trusted_source_byte_limit = payload.get("trusted_source_byte_limit")
    if (
        isinstance(trusted_source_byte_limit, bool)
        or not isinstance(trusted_source_byte_limit, int)
        or not 1 <= trusted_source_byte_limit <= MAX_TRUSTED_TOTAL_BYTES
    ):
        raise ProtocolError("trusted_source_byte_limit is invalid")

    raw_digests = payload.get("trusted_file_digests")
    if not isinstance(raw_digests, Mapping) or len(raw_digests) > 256:
        raise ProtocolError("trusted_file_digests must be a bounded object")
    trusted: dict[Path, str] = {}
    trusted_sources: dict[Path, bytes] = {}
    trusted_total_bytes = 0
    for raw_path, raw_digest in raw_digests.items():
        if type(raw_path) is not str or type(raw_digest) is not str:
            raise ProtocolError("trusted_file_digests is malformed")
        path = Path(raw_path)
        if not path.is_absolute() or _DIGEST.fullmatch(raw_digest) is None:
            raise ProtocolError("trusted_file_digests is malformed")
        try:
            path = path.resolve(strict=True)
        except OSError:
            raise ProtocolError("trusted module file is unavailable") from None
        if not path.is_file() or not _is_within(path, repository_root):
            raise ProtocolError("trusted module file escapes the repository root")
        if path in trusted:
            raise ProtocolError("trusted_file_digests contains duplicate paths")
        source, size = _read_trusted_file(
            path,
            raw_digest,
            byte_limit=trusted_source_byte_limit,
            retain_source=path in required_origins,
        )
        trusted_total_bytes += size
        if trusted_total_bytes > trusted_source_byte_limit:
            raise ProtocolError("trusted module files exceed the total byte limit")
        if source is not None:
            trusted_sources[path] = source
        trusted[path] = raw_digest
    if module_file not in trusted:
        raise ProtocolError("module_file is not owner-pinned")

    if not required_origins <= set(trusted_sources):
        raise ProtocolError("parent package is not owner-pinned")
    for prefix, expected_origin in prefix_origins.items():
        loaded = sys.modules.get(prefix)
        if loaded is None:
            continue
        raw_origin = getattr(loaded, "__file__", None)
        if not isinstance(raw_origin, str):
            raise ProtocolError("approved module name is already loaded externally")
        try:
            loaded_origin = Path(raw_origin).resolve(strict=True)
        except OSError:
            raise ProtocolError("approved module origin is unavailable") from None
        if loaded_origin != expected_origin:
            raise ProtocolError("approved module name is already loaded externally")
    return module_file, prefix_origins, trusted_sources


def _load_pinned_module(
    module_name: str,
    prefix_origins: Mapping[str, Path],
    trusted_sources: Mapping[Path, bytes],
) -> tuple[types.ModuleType, tuple[str, ...]]:
    loaded_names: list[str] = []
    modules: dict[str, types.ModuleType] = {}
    try:
        ordered_origins = sorted(
            prefix_origins.items(),
            key=lambda item: (item[0].count("."), item[0]),
        )
        for name, origin in ordered_origins:
            is_package = origin.name == "__init__.py"
            search_locations = [str(origin.parent)] if is_package else None
            spec = importlib.util.spec_from_file_location(
                name,
                origin,
                submodule_search_locations=search_locations,
            )
            if spec is None:
                raise ProtocolError("approved module cannot be loaded")
            module = types.ModuleType(name)
            module.__file__ = str(origin)
            module.__loader__ = spec.loader
            module.__package__ = name if is_package else name.rpartition(".")[0]
            module.__spec__ = spec
            if is_package:
                module.__path__ = [str(origin.parent)]
            sys.modules[name] = module
            loaded_names.append(name)
            modules[name] = module
        for name, module in modules.items():
            if "." in name:
                parent_name, _, child_name = name.rpartition(".")
                parent = modules.get(parent_name)
                if parent is None:
                    raise ProtocolError("approved parent package is unavailable")
                setattr(parent, child_name, module)
        for name, origin in ordered_origins:
            module = modules[name]
            is_package = origin.name == "__init__.py"
            spec = module.__spec__
            if spec is None:
                raise ProtocolError("approved module has no import specification")
            source = trusted_sources.get(origin)
            if source is None:
                raise ProtocolError("approved module source is unavailable")
            exec(compile(source, str(origin), "exec", dont_inherit=True), module.__dict__)
            if sys.modules.get(name) is not module:
                raise ProtocolError("approved module replaced its pinned module identity")
            module.__file__ = str(origin)
            module.__loader__ = spec.loader
            module.__package__ = name if is_package else name.rpartition(".")[0]
            module.__spec__ = spec
        loaded = sys.modules.get(module_name)
        if not isinstance(loaded, types.ModuleType):
            raise ProtocolError("approved module did not load")
        return loaded, tuple(loaded_names)
    except BaseException:
        for name in reversed(loaded_names):
            sys.modules.pop(name, None)
        raise


class _RepositoryImportGuard(importlib.abc.MetaPathFinder):
    """Reject non-pinned imports whose resolved origin is inside the repository."""

    def __init__(self, repository_root: Path, approved_module_names: set[str]) -> None:
        self._repository_root = repository_root
        self._approved_module_names = frozenset(approved_module_names)

    def _repository_local(self, value: object) -> bool:
        if not isinstance(value, str) or value in {"built-in", "frozen"}:
            return False
        try:
            return _is_within(Path(value).resolve(strict=False), self._repository_root)
        except (OSError, RuntimeError):
            return False

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del target
        if fullname in self._approved_module_names:
            raise ImportError("approved modules must use the pinned source loader")
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None:
            return None
        locations = tuple(spec.submodule_search_locations or ())
        if self._repository_local(spec.origin) or any(
            self._repository_local(location) for location in locations
        ):
            raise ImportError("repository-local imports require explicit source pinning")
        return None


def _valid_dotted_identifier(value: str) -> bool:
    return bool(_DOTTED_IDENTIFIER.fullmatch(value)) and all(
        part not in {"__builtins__", "__loader__", "__spec__"} for part in value.split(".")
    )


def _contains_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS)


def _safe_summary(value: object, *, depth: int = 0, field_name: str = "value") -> object:
    """Return a bounded JSON summary without secret-like text."""

    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "number", "value": value}
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        if _SECRET_FIELD_PATTERN.search(field_name) or _contains_secret(value):
            return {
                "type": "string",
                "utf8_bytes": len(encoded),
                "digest": digest,
                "value": "[redacted]",
            }
        if len(encoded) <= MAX_SUMMARY_TEXT_BYTES:
            return {
                "type": "string",
                "utf8_bytes": len(encoded),
                "digest": digest,
                "value": value,
            }
        return {
            "type": "string",
            "utf8_bytes": len(encoded),
            "digest": digest,
            "value": "[truncated]",
        }
    if isinstance(value, list):
        if depth >= MAX_SUMMARY_DEPTH:
            return {"type": "array", "items": len(value), "value": "[depth-limited]"}
        shown = value[:MAX_SUMMARY_ITEMS]
        return {
            "type": "array",
            "items": len(value),
            "value": [
                _safe_summary(item, depth=depth + 1, field_name=f"{field_name}[{index}]")
                for index, item in enumerate(shown)
            ],
            "truncated": len(shown) != len(value),
        }
    if isinstance(value, Mapping):
        if depth >= MAX_SUMMARY_DEPTH:
            return {"type": "object", "fields": len(value), "value": "[depth-limited]"}
        keys = sorted(value)[:MAX_SUMMARY_ITEMS]
        return {
            "type": "object",
            "fields": len(value),
            "value": {
                key: _safe_summary(value[key], depth=depth + 1, field_name=key) for key in keys
            },
            "truncated": len(keys) != len(value),
        }
    return {"type": "unsupported"}


def _exception_type(exc: BaseException) -> str:
    exact = _APPROVED_EXCEPTION_IDENTIFIERS.get(type(exc))
    if exact is not None:
        return exact
    for identifier, exception_class in _APPROVED_EXCEPTION_TYPES.items():
        if isinstance(exc, exception_class):
            return identifier
    return "unapproved_exception"


def _matches_exception(expected: object, exc: BaseException) -> bool:
    if type(expected) is not str:
        return False
    expected_class = _APPROVED_EXCEPTION_TYPES.get(expected)
    return expected_class is not None and isinstance(exc, expected_class)


def json_values_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is list:
        left_items = cast(list[object], left)
        right_items = cast(list[object], right)
        return len(left_items) == len(right_items) and all(
            json_values_equal(left_item, right_item)
            for left_item, right_item in zip(left_items, right_items, strict=True)
        )
    if type(left) is dict:
        left_mapping = cast(dict[str, object], left)
        right_mapping = cast(dict[str, object], right)
        return set(left_mapping) == set(right_mapping) and all(
            json_values_equal(left_mapping[key], right_mapping[key]) for key in left_mapping
        )
    return left == right


def _assertion_passes(assertion: str, observed: object, expected: object) -> bool:
    if assertion == "equals":
        return json_values_equal(observed, expected)
    if assertion == "not_equals":
        return not json_values_equal(observed, expected)
    if assertion == "is_none":
        return observed is None
    if assertion == "is_not_none":
        return observed is not None
    if assertion == "contains":
        if isinstance(observed, str) and isinstance(expected, str):
            return expected in observed
        if isinstance(observed, list):
            return any(json_values_equal(item, expected) for item in observed)
        if isinstance(observed, Mapping) and isinstance(expected, str):
            return expected in observed
        return False
    if assertion == "truthy":
        return bool(observed)
    if assertion == "falsey":
        return not bool(observed)
    raise ProtocolError("unknown assertion")


def _result(
    *,
    status: str,
    reason_code: str,
    input_value: object,
    expected: object,
    observed: object,
    exception_type: str | None,
) -> dict[str, object]:
    return {
        "protocol": PROTOCOL_VERSION,
        "status": status,
        "reason_code": reason_code,
        "input_summary": _safe_summary(input_value),
        "expected_summary": _safe_summary(expected, field_name="expected"),
        "observed_summary": _safe_summary(observed, field_name="observed"),
        "exception_type": exception_type,
    }


def _invoke_target(
    target: Callable[..., object],
    *,
    positional: list[object],
    keyword: dict[str, object],
    assertion: str,
    expected: object,
    call_input: Mapping[str, object],
) -> dict[str, object]:
    call_exception: BaseException | None = None
    observed_raw: object = None
    try:
        observed_raw = target(*positional, **dict(keyword))
    except BaseException as exc:
        call_exception = exc

    if assertion == "raises":
        if call_exception is None:
            return _result(
                status="failed",
                reason_code="expected_exception_not_raised",
                input_value=call_input,
                expected=expected,
                observed=None,
                exception_type=None,
            )
        passed = _matches_exception(expected, call_exception)
        return _result(
            status="passed" if passed else "failed",
            reason_code="assertion_passed" if passed else "expected_exception_mismatch",
            input_value=call_input,
            expected=expected,
            observed=None,
            exception_type=_exception_type(call_exception),
        )

    if call_exception is not None:
        return _result(
            status="failed",
            reason_code="unexpected_exception",
            input_value=call_input,
            expected=expected,
            observed=None,
            exception_type=_exception_type(call_exception),
        )
    try:
        observed = _normalize_json(observed_raw, "result")
        if len(_canonical_json(observed).encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ProtocolError("result exceeds the byte limit")
    except ProtocolError:
        return _result(
            status="error",
            reason_code="result_serialization_error",
            input_value=call_input,
            expected=expected,
            observed=None,
            exception_type=None,
        )
    passed = _assertion_passes(assertion, observed, expected)
    return _result(
        status="passed" if passed else "failed",
        reason_code="assertion_passed" if passed else "assertion_failed",
        input_value=call_input,
        expected=expected,
        observed=observed,
        exception_type=None,
    )


def execute_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Execute one already-parsed, closed helper request."""

    if set(payload) != _PAYLOAD_FIELDS or payload.get("protocol") != PROTOCOL_VERSION:
        raise ProtocolError("payload does not match the closed protocol")
    repository_root, import_root = _validated_runtime_roots(payload)
    module_name = _required_text(payload, "module")
    callable_name = _required_text(payload, "callable_name")
    if not _valid_dotted_identifier(module_name) or not _valid_dotted_identifier(callable_name):
        raise ProtocolError("target identity is malformed")
    _, prefix_origins, trusted_sources = _validated_module_files(
        payload,
        repository_root=repository_root,
        import_root=import_root,
        module_name=module_name,
    )
    assertion = _required_text(payload, "assertion")
    if assertion not in ASSERTIONS:
        raise ProtocolError("unknown assertion")
    if payload.get("result_serializer") != "json":
        raise ProtocolError("result serializer must be json")

    positional_value = _normalize_json(payload.get("positional_arguments"), "positional_arguments")
    keyword_value = _normalize_json(payload.get("keyword_arguments"), "keyword_arguments")
    if type(positional_value) is not list:
        raise ProtocolError("positional_arguments must be an array")
    if type(keyword_value) is not dict:
        raise ProtocolError("keyword_arguments must be an object")
    expected = _normalize_json(payload.get("expected"), "expected")
    call_input = {"positional": positional_value, "keyword": keyword_value}
    positional = cast(
        list[object],
        _normalize_json(positional_value, "invocation.positional_arguments"),
    )
    keyword = cast(
        dict[str, object],
        _normalize_json(keyword_value, "invocation.keyword_arguments"),
    )

    original_sys_path = list(sys.path)
    original_meta_path = list(sys.meta_path)
    original_pycache_prefix = sys.pycache_prefix
    original_dont_write_bytecode = sys.dont_write_bytecode
    loaded_names: tuple[str, ...] = ()
    try:
        with tempfile.TemporaryDirectory(prefix="faber-proof-pycache-") as cache_root:
            sys.path.insert(0, str(import_root))
            sys.meta_path.insert(
                0,
                _RepositoryImportGuard(repository_root, set(prefix_origins)),
            )
            sys.pycache_prefix = cache_root
            sys.dont_write_bytecode = True
            try:
                module, loaded_names = _load_pinned_module(
                    module_name,
                    prefix_origins,
                    trusted_sources,
                )
                target: object = module
                for part in callable_name.split("."):
                    target = getattr(target, part)
                if not callable(target):
                    return _result(
                        status="error",
                        reason_code="target_not_callable",
                        input_value=call_input,
                        expected=expected,
                        observed=None,
                        exception_type=None,
                    )
            except BaseException as exc:
                return _result(
                    status="error",
                    reason_code="target_import_error",
                    input_value=call_input,
                    expected=expected,
                    observed=None,
                    exception_type=_exception_type(exc),
                )
            return _invoke_target(
                target,
                positional=positional,
                keyword=keyword,
                assertion=assertion,
                expected=expected,
                call_input=call_input,
            )
    finally:
        for name in reversed(loaded_names):
            sys.modules.pop(name, None)
        sys.path[:] = original_sys_path
        sys.meta_path[:] = original_meta_path
        sys.pycache_prefix = original_pycache_prefix
        sys.dont_write_bytecode = original_dont_write_bytecode


def _error_result(reason_code: str) -> dict[str, object]:
    return {
        "protocol": PROTOCOL_VERSION,
        "status": "error",
        "reason_code": reason_code,
        "input_summary": {"type": "unavailable"},
        "expected_summary": {"type": "unavailable"},
        "observed_summary": {"type": "unavailable"},
        "exception_type": None,
    }


def main() -> int:
    try:
        payload = _parse_payload(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        result = execute_payload(payload)
    except (ProtocolError, OSError, RecursionError):
        result = _error_result("protocol_error")
    encoded = (_canonical_json(result) + "\n").encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        encoded = (_canonical_json(_error_result("helper_output_too_large")) + "\n").encode("utf-8")
        result = _error_result("helper_output_too_large")
    sys.stdout.buffer.write(encoded)
    return 0 if result["status"] in {"passed", "failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
