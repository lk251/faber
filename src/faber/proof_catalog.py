"""Authoritative, provider-neutral proof catalog and parameter binding.

Planner catalog views are deliberately lossy.  Every view contains a digest of the
owner-controlled capability represented here, while none of the executable fields in
that capability are exposed to a model.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import TypeAlias

from faber.canonical_json import canonical_json_bytes
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_planning import (
    PlannerCatalogEntryView,
    planner_catalog_digest,
    validate_parameter_schema,
    validate_planner_parameters,
)
from faber.validation import require_digest, require_non_empty_string

PROOF_CATALOG_SCHEMA = "faber.proof_catalog.v1"
PROOF_CATALOG_ENTRY_SCHEMA = "faber.proof_catalog_entry.v1"
PROOF_CAPABILITY_SCHEMA = "faber.proof_capability.v1"

PROOF_FAMILIES = {
    "artifact-validator",
    "existing-command",
    "file-invariant",
    "pytest-node",
    "python-call",
}
PYTHON_ASSERTIONS = {
    "contains",
    "equals",
    "falsey",
    "is_none",
    "is_not_none",
    "not_equals",
    "raises",
    "truthy",
}
PYTHON_EXCEPTION_TYPES = {
    "builtins.ArithmeticError",
    "builtins.AssertionError",
    "builtins.IndexError",
    "builtins.KeyError",
    "builtins.RuntimeError",
    "builtins.TypeError",
    "builtins.ValueError",
    "builtins.ZeroDivisionError",
}
FILE_INVARIANT_OPERATIONS = {
    "absent",
    "contains_literal",
    "digest_equals",
    "excludes_literal",
    "exists",
    "json_pointer_equals",
    "valid_json",
}
ARTIFACT_KINDS = {"attempt_manifest", "trace", "trajectory"}

MAX_IDENTIFIER_BYTES = 256
MAX_PATH_BYTES = 2048
MAX_TEXT_BYTES = 4096
MAX_ENVIRONMENT_VALUE_BYTES = 4096
MAX_TIMEOUT_SECONDS = 3600
MAX_OUTPUT_BYTES = 16 * 1024 * 1024

_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DOTTED_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z")


def _bounded_text(value: object, field_name: str, *, max_bytes: int) -> str:
    text = require_non_empty_string(value, field_name)
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValidationError(f"{field_name} must be valid UTF-8 text") from None
    if size > max_bytes:
        raise ValidationError(f"{field_name} exceeds its UTF-8 byte limit")
    if "\x00" in text:
        raise ValidationError(f"{field_name} must not contain NUL")
    return text


def _positive_int(value: object, field_name: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{field_name} must be a positive integer")
    if value > maximum:
        raise ValidationError(f"{field_name} exceeds its allowed maximum")
    return value


def _string_tuple(
    value: object,
    field_name: str,
    *,
    allow_empty: bool = True,
    sort: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError(f"{field_name} must be a sequence of strings")
    values = tuple(
        _bounded_text(item, f"{field_name}[{index}]", max_bytes=MAX_TEXT_BYTES)
        for index, item in enumerate(value)
    )
    if not allow_empty and not values:
        raise ValidationError(f"{field_name} must not be empty")
    if len(set(values)) != len(values):
        raise ValidationError(f"{field_name} must not contain duplicate values")
    return tuple(sorted(values)) if sort else values


def _optional_parameter_name(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field_name, max_bytes=MAX_IDENTIFIER_BYTES)


def _repository_path(value: object, field_name: str, *, allow_root: bool) -> str:
    text = _bounded_text(value, field_name, max_bytes=MAX_PATH_BYTES)
    if "\\" in text:
        raise ValidationError(f"{field_name} must use normalized POSIX separators")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text)
    if windows.drive or windows.root or posix.is_absolute():
        raise ValidationError(f"{field_name} must be repository-relative")
    if any(part in {"", ".."} for part in posix.parts):
        raise ValidationError(f"{field_name} must not contain traversal")
    normalized = posix.as_posix()
    if normalized != text:
        raise ValidationError(f"{field_name} must already be normalized")
    if normalized == "." and not allow_root:
        raise ValidationError(f"{field_name} must identify a repository file")
    return normalized


def _dotted_identifier(value: object, field_name: str) -> str:
    text = _bounded_text(value, field_name, max_bytes=MAX_IDENTIFIER_BYTES)
    if _DOTTED_IDENTIFIER.fullmatch(text) is None:
        raise ValidationError(f"{field_name} must be a dotted Python identifier")
    return text


def _freeze_json(value: object) -> object:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return tuple(_freeze_json(item) for item in value)
    raise ValidationError("value must contain only JSON-compatible data")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _mapping_dict(value: Mapping[str, object]) -> dict[str, object]:
    thawed = _thaw_json(value)
    if not isinstance(thawed, dict):
        raise AssertionError("frozen mapping must thaw to a dict")
    return thawed


def _environment_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ValidationError("environment_variables must be a mapping")
    result: dict[str, str] = {}
    casefolded: set[str] = set()
    for raw_name, raw_value in sorted(value.items()):
        if not isinstance(raw_name, str) or _ENVIRONMENT_NAME.fullmatch(raw_name) is None:
            raise ValidationError("environment variable names must be portable identifiers")
        folded = raw_name.casefold()
        if folded in casefolded:
            raise ValidationError("environment variable names must be case-insensitively unique")
        casefolded.add(folded)
        result[raw_name] = _bounded_text(
            raw_value,
            f"environment_variables.{raw_name}",
            max_bytes=MAX_ENVIRONMENT_VALUE_BYTES,
        )
    return MappingProxyType(result)


def _trusted_file_digest_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ValidationError("trusted_file_digests must be a mapping")
    if len(value) > 256:
        raise ValidationError("trusted_file_digests exceeds the file-count limit")
    result: dict[str, str] = {}
    casefolded_paths: set[str] = set()
    for raw_path, raw_digest in sorted(value.items()):
        if not isinstance(raw_path, str):
            raise ValidationError("trusted_file_digests must use string paths")
        path = _repository_path(
            raw_path,
            f"trusted_file_digests.{raw_path}",
            allow_root=False,
        )
        folded = path.casefold()
        if folded in casefolded_paths:
            raise ValidationError("trusted_file_digests paths must be case-insensitively unique")
        casefolded_paths.add(folded)
        result[path] = require_digest(
            raw_digest,
            f"trusted_file_digests.{path}",
        )
    return MappingProxyType(result)


@dataclass(frozen=True)
class ProofCapabilityPolicy:
    """Owner-controlled settings shared by every proof capability."""

    verifier_id: str
    verifier_version: str
    working_directory: str = "."
    timeout_seconds: int = 30
    max_output_bytes: int = 64_000
    environment_variables: Mapping[str, str] = field(default_factory=dict)
    trusted_file_digests: Mapping[str, str] = field(default_factory=dict)
    verifier_spec_digest: str | None = None

    def __post_init__(self) -> None:
        _bounded_text(self.verifier_id, "verifier_id", max_bytes=MAX_IDENTIFIER_BYTES)
        _bounded_text(self.verifier_version, "verifier_version", max_bytes=MAX_IDENTIFIER_BYTES)
        object.__setattr__(
            self,
            "working_directory",
            _repository_path(self.working_directory, "working_directory", allow_root=True),
        )
        _positive_int(
            self.timeout_seconds,
            "timeout_seconds",
            maximum=MAX_TIMEOUT_SECONDS,
        )
        _positive_int(
            self.max_output_bytes,
            "max_output_bytes",
            maximum=MAX_OUTPUT_BYTES,
        )
        object.__setattr__(
            self,
            "environment_variables",
            _environment_mapping(self.environment_variables),
        )
        object.__setattr__(
            self,
            "trusted_file_digests",
            _trusted_file_digest_mapping(self.trusted_file_digests),
        )
        if self.verifier_spec_digest is not None:
            require_digest(self.verifier_spec_digest, "verifier_spec_digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "verifier_id": self.verifier_id,
            "verifier_version": self.verifier_version,
            "verifier_spec_digest": self.verifier_spec_digest,
            "working_directory": self.working_directory,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "environment_variables": dict(self.environment_variables),
            "trusted_file_digests": dict(self.trusted_file_digests),
        }


@dataclass(frozen=True)
class ExistingCommandCapability:
    policy: ProofCapabilityPolicy
    family: str = field(default="existing-command", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProofCapabilityPolicy):
            raise ValidationError("policy must be ProofCapabilityPolicy")

    def to_dict(self) -> dict[str, object]:
        return {"family": self.family, "policy": self.policy.to_dict()}


@dataclass(frozen=True)
class PytestNodeCapability:
    policy: ProofCapabilityPolicy
    node_ids: Sequence[str]
    python_module: str = "pytest"
    family: str = field(default="pytest-node", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProofCapabilityPolicy):
            raise ValidationError("policy must be ProofCapabilityPolicy")
        object.__setattr__(
            self,
            "node_ids",
            _string_tuple(self.node_ids, "node_ids", allow_empty=False),
        )
        module = _dotted_identifier(self.python_module, "python_module")
        if module != "pytest":
            raise ValidationError("python_module must be the fixed 'pytest' module")
        object.__setattr__(self, "python_module", module)
        node_paths: set[str] = set()
        for index, node_id in enumerate(self.node_ids):
            raw_node_path = node_id.split("::", 1)[0]
            if raw_node_path.startswith("-"):
                raise ValidationError(f"node_ids[{index}] must not be option-like")
            normalized_node_path = _repository_path(
                raw_node_path,
                f"node_ids[{index}] file",
                allow_root=False,
            )
            node_paths.add(
                PurePosixPath(self.policy.working_directory, normalized_node_path).as_posix()
            )
        missing_digests = sorted(node_paths - set(self.policy.trusted_file_digests))
        if missing_digests:
            raise ValidationError(
                f"pytest node files require owner-pinned trusted_file_digests: {missing_digests}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "policy": self.policy.to_dict(),
            "node_ids": list(self.node_ids),
            "python_module": self.python_module,
        }


@dataclass(frozen=True)
class PythonCallCapability:
    policy: ProofCapabilityPolicy
    module: str
    callable_name: str
    module_file: str | None = None
    import_root: str = "."
    positional_parameter: str | None = "inputs"
    keyword_parameter: str | None = "options"
    assertion_parameter: str | None = "assertion"
    expected_parameter: str | None = "expected"
    default_assertion: str = "equals"
    allowed_assertions: Sequence[str] = field(
        default_factory=lambda: tuple(sorted(PYTHON_ASSERTIONS))
    )
    result_serializer: str = "json"
    family: str = field(default="python-call", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProofCapabilityPolicy):
            raise ValidationError("policy must be ProofCapabilityPolicy")
        object.__setattr__(self, "module", _dotted_identifier(self.module, "module"))
        object.__setattr__(
            self,
            "callable_name",
            _dotted_identifier(self.callable_name, "callable_name"),
        )
        module_file = self.module_file or f"{self.module.replace('.', '/')}.py"
        object.__setattr__(
            self,
            "module_file",
            _repository_path(module_file, "module_file", allow_root=False),
        )
        module_stem = self.module.replace(".", "/")
        if self.module_file not in {f"{module_stem}.py", f"{module_stem}/__init__.py"}:
            raise ValidationError(
                "module_file must be the approved module's .py file or package __init__.py"
            )
        object.__setattr__(
            self,
            "import_root",
            _repository_path(self.import_root, "import_root", allow_root=True),
        )
        for name in (
            "positional_parameter",
            "keyword_parameter",
            "assertion_parameter",
            "expected_parameter",
        ):
            object.__setattr__(
                self,
                name,
                _optional_parameter_name(getattr(self, name), name),
            )
        assertions = _string_tuple(
            self.allowed_assertions,
            "allowed_assertions",
            allow_empty=False,
        )
        unknown = sorted(set(assertions) - PYTHON_ASSERTIONS)
        if unknown:
            raise ValidationError(f"allowed_assertions contains unsupported values: {unknown}")
        object.__setattr__(self, "allowed_assertions", assertions)
        if self.default_assertion not in assertions:
            raise ValidationError("default_assertion must be in allowed_assertions")
        if self.result_serializer != "json":
            raise ValidationError("result_serializer must be the bounded 'json' serializer")
        missing_module_digests = sorted(
            set(self.required_module_repository_paths) - set(self.policy.trusted_file_digests)
        )
        if missing_module_digests:
            raise ValidationError(
                "module files require owner-pinned trusted_file_digests entries: "
                f"{missing_module_digests}"
            )

    @property
    def module_repository_path(self) -> str:
        if not isinstance(self.module_file, str):
            raise AssertionError("validated module_file must be text")
        return PurePosixPath(self.import_root, self.module_file).as_posix()

    @property
    def module_import_path(self) -> str:
        if not isinstance(self.module_file, str):
            raise AssertionError("validated module_file must be text")
        return self.module_file

    @property
    def required_module_repository_paths(self) -> tuple[str, ...]:
        parts = self.module.split(".")
        required = [
            PurePosixPath(self.import_root, *parts[:index], "__init__.py").as_posix()
            for index in range(1, len(parts))
        ]
        required.append(self.module_repository_path)
        return tuple(required)

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "policy": self.policy.to_dict(),
            "module": self.module,
            "callable_name": self.callable_name,
            "module_file": self.module_file,
            "import_root": self.import_root,
            "positional_parameter": self.positional_parameter,
            "keyword_parameter": self.keyword_parameter,
            "assertion_parameter": self.assertion_parameter,
            "expected_parameter": self.expected_parameter,
            "default_assertion": self.default_assertion,
            "allowed_assertions": list(self.allowed_assertions),
            "result_serializer": self.result_serializer,
        }


@dataclass(frozen=True)
class FileInvariantCapability:
    policy: ProofCapabilityPolicy
    repository_path: str
    operation: str
    expected_parameter: str | None = "expected"
    json_pointer_parameter: str | None = "json_pointer"
    family: str = field(default="file-invariant", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProofCapabilityPolicy):
            raise ValidationError("policy must be ProofCapabilityPolicy")
        object.__setattr__(
            self,
            "repository_path",
            _repository_path(self.repository_path, "repository_path", allow_root=False),
        )
        if self.operation not in FILE_INVARIANT_OPERATIONS:
            raise ValidationError(f"operation must be one of {sorted(FILE_INVARIANT_OPERATIONS)}")
        object.__setattr__(
            self,
            "expected_parameter",
            _optional_parameter_name(self.expected_parameter, "expected_parameter"),
        )
        object.__setattr__(
            self,
            "json_pointer_parameter",
            _optional_parameter_name(
                self.json_pointer_parameter,
                "json_pointer_parameter",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "policy": self.policy.to_dict(),
            "repository_path": self.repository_path,
            "operation": self.operation,
            "expected_parameter": self.expected_parameter,
            "json_pointer_parameter": self.json_pointer_parameter,
        }


@dataclass(frozen=True)
class ArtifactValidatorCapability:
    policy: ProofCapabilityPolicy
    artifact_kind: str
    repository_path: str
    quality_only: bool = False
    family: str = field(default="artifact-validator", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProofCapabilityPolicy):
            raise ValidationError("policy must be ProofCapabilityPolicy")
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise ValidationError(f"artifact_kind must be one of {sorted(ARTIFACT_KINDS)}")
        object.__setattr__(
            self,
            "repository_path",
            _repository_path(self.repository_path, "repository_path", allow_root=False),
        )
        if not isinstance(self.quality_only, bool):
            raise ValidationError("quality_only must be a boolean")
        if self.quality_only and self.artifact_kind != "trajectory":
            raise ValidationError("quality_only is supported only for trajectory artifacts")

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "policy": self.policy.to_dict(),
            "artifact_kind": self.artifact_kind,
            "repository_path": self.repository_path,
            "quality_only": self.quality_only,
        }


ProofCapability: TypeAlias = (
    ExistingCommandCapability
    | PytestNodeCapability
    | PythonCallCapability
    | FileInvariantCapability
    | ArtifactValidatorCapability
)
_CAPABILITY_TYPES = (
    ExistingCommandCapability,
    PytestNodeCapability,
    PythonCallCapability,
    FileInvariantCapability,
    ArtifactValidatorCapability,
)


def _schema_dict(value: Mapping[str, object]) -> dict[str, object]:
    thawed = _thaw_json(value)
    if not isinstance(thawed, dict):
        raise AssertionError("validated schema must thaw to a dict")
    return thawed


def _root_schema_parts(
    schema: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object], tuple[str, ...]]:
    full = _schema_dict(schema)
    raw_properties = full.get("properties")
    raw_required = full.get("required")
    if not isinstance(raw_properties, dict) or not isinstance(raw_required, list):
        raise AssertionError("validated root object schema has invalid structure")
    required = tuple(str(item) for item in raw_required)
    return full, raw_properties, required


def _object_projection_schema(
    full: Mapping[str, object],
    properties: Mapping[str, object],
    names: Sequence[str],
) -> dict[str, object]:
    result: dict[str, object] = {
        "type": "object",
        "properties": {name: copy.deepcopy(properties[name]) for name in names},
        "required": list(names),
        "additionalProperties": False,
    }
    if "description" in full:
        result["description"] = full["description"]
    return result


def _prepare_parameter_contract(
    execution_parameter_schema: object,
    parameter_defaults: object,
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    execution_schema = validate_parameter_schema(execution_parameter_schema)
    full, properties, required = _root_schema_parts(execution_schema)
    optional = tuple(sorted(set(properties) - set(required)))
    if not isinstance(parameter_defaults, Mapping):
        raise ValidationError("parameter_defaults must be a mapping")
    if any(not isinstance(key, str) for key in parameter_defaults):
        raise ValidationError("parameter_defaults must use string keys")
    default_keys = set(parameter_defaults)
    if default_keys != set(optional):
        raise ValidationError(
            "parameter_defaults must provide exactly every optional execution parameter"
        )

    minimum = full.get("minProperties", 0)
    maximum = full.get("maxProperties", len(properties))
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise AssertionError("validated property bounds must be integers")
    if not minimum <= len(properties) <= maximum:
        raise ValidationError(
            "execution_parameter_schema must accept the fully default-bound parameter object"
        )

    defaults_schema = _object_projection_schema(full, properties, optional)
    defaults = validate_planner_parameters(defaults_schema, dict(parameter_defaults))
    planner_schema_dict = _object_projection_schema(full, properties, required)
    planner_schema = validate_parameter_schema(planner_schema_dict)
    frozen_defaults = _freeze_json(defaults)
    if not isinstance(frozen_defaults, Mapping):
        raise AssertionError("validated parameter defaults must freeze to a mapping")
    return execution_schema, frozen_defaults, planner_schema


def _parameter_property(
    entry: ProofCatalogEntry,
    parameter_name: str | None,
    field_name: str,
) -> Mapping[str, object] | None:
    if parameter_name is None:
        return None
    schema = entry.execution_parameter_schema_dict()
    properties = schema["properties"]
    if not isinstance(properties, Mapping) or parameter_name not in properties:
        raise ValidationError(f"{field_name} must name a declared execution parameter")
    node = properties[parameter_name]
    if not isinstance(node, Mapping):
        raise AssertionError("validated parameter property must be an object")
    return node


def _validate_parameter_bindings(entry: ProofCatalogEntry) -> None:
    capability = entry.capability
    if isinstance(capability, PythonCallCapability):
        positional = _parameter_property(
            entry, capability.positional_parameter, "positional_parameter"
        )
        if positional is not None and positional.get("type") != "array":
            raise ValidationError("positional_parameter must use an array schema")
        keyword = _parameter_property(entry, capability.keyword_parameter, "keyword_parameter")
        if keyword is not None and keyword.get("type") != "object":
            raise ValidationError("keyword_parameter must use an object schema")
        assertion = _parameter_property(
            entry, capability.assertion_parameter, "assertion_parameter"
        )
        if assertion is not None:
            if assertion.get("type") != "string" or "enum" not in assertion:
                raise ValidationError("assertion_parameter must use a closed string enum")
            raw_enum = assertion.get("enum")
            if not isinstance(raw_enum, Sequence) or isinstance(raw_enum, str | bytes):
                raise AssertionError("validated assertion enum must be a sequence")
            exposed_assertions = set(raw_enum)
            allowed_assertions = set(capability.allowed_assertions)
            if exposed_assertions != allowed_assertions:
                raise ValidationError(
                    "assertion_parameter enum must exactly match the capability assertions"
                )
        elif set(capability.allowed_assertions) != {capability.default_assertion}:
            raise ValidationError(
                "a fixed assertion capability must expose only its default assertion"
            )
        expected = _parameter_property(
            entry,
            capability.expected_parameter,
            "expected_parameter",
        )
        if "raises" in capability.allowed_assertions:
            if expected is None or expected.get("type") != "string":
                raise ValidationError(
                    "raises requires an expected_parameter with a closed string enum"
                )
            raw_expected_enum = expected.get("enum")
            if (
                not isinstance(raw_expected_enum, Sequence)
                or isinstance(raw_expected_enum, str | bytes)
                or not raw_expected_enum
                or any(not isinstance(item, str) for item in raw_expected_enum)
                or not set(raw_expected_enum) <= PYTHON_EXCEPTION_TYPES
            ):
                raise ValidationError(
                    "raises expected_parameter must enumerate approved exception types"
                )
    elif isinstance(capability, FileInvariantCapability):
        expected = _parameter_property(entry, capability.expected_parameter, "expected_parameter")
        pointer = _parameter_property(
            entry, capability.json_pointer_parameter, "json_pointer_parameter"
        )
        no_value_operations = {"exists", "absent", "valid_json"}
        if capability.operation in no_value_operations:
            if expected is not None or pointer is not None:
                raise ValidationError(
                    f"{capability.operation} must not bind expected or JSON-pointer parameters"
                )
        elif capability.operation == "json_pointer_equals":
            if expected is None or pointer is None:
                raise ValidationError(
                    "json_pointer_equals requires expected and JSON-pointer parameters"
                )
            if pointer.get("type") != "string":
                raise ValidationError("json_pointer_parameter must use a string schema")
        else:
            if expected is None or pointer is not None:
                raise ValidationError(f"{capability.operation} requires only an expected parameter")
            if expected.get("type") != "string":
                raise ValidationError(
                    f"{capability.operation} expected parameter must use a string schema"
                )


@dataclass(frozen=True)
class ProofCatalogEntry:
    """One immutable owner-controlled capability and its strict planner projection."""

    id: str
    version: str
    description: str
    execution_parameter_schema: Mapping[str, object]
    capability: ProofCapability
    parameter_defaults: Mapping[str, object] = field(default_factory=dict)
    assertion_operators: Sequence[str] = ()
    capability_limits: Mapping[str, object] = field(default_factory=dict)
    schema: str = PROOF_CATALOG_ENTRY_SCHEMA
    planner_parameter_schema: Mapping[str, object] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.schema != PROOF_CATALOG_ENTRY_SCHEMA:
            raise ValidationError(f"schema must be {PROOF_CATALOG_ENTRY_SCHEMA!r}")
        _bounded_text(self.id, "id", max_bytes=MAX_IDENTIFIER_BYTES)
        _bounded_text(self.version, "version", max_bytes=MAX_IDENTIFIER_BYTES)
        _bounded_text(self.description, "description", max_bytes=MAX_TEXT_BYTES)
        if not isinstance(self.capability, _CAPABILITY_TYPES):
            raise ValidationError("capability must be a supported typed proof capability")

        execution_schema, defaults, planner_schema = _prepare_parameter_contract(
            self.execution_parameter_schema,
            self.parameter_defaults,
        )
        object.__setattr__(self, "execution_parameter_schema", execution_schema)
        object.__setattr__(self, "parameter_defaults", defaults)
        object.__setattr__(self, "planner_parameter_schema", planner_schema)

        operators = tuple(self.assertion_operators)
        if not operators and isinstance(self.capability, PythonCallCapability):
            operators = tuple(self.capability.allowed_assertions)
        elif not operators and isinstance(self.capability, FileInvariantCapability):
            operators = (self.capability.operation,)
        if isinstance(self.capability, PythonCallCapability):
            if set(operators) != set(self.capability.allowed_assertions):
                raise ValidationError("assertion_operators must exactly match allowed_assertions")
        elif isinstance(self.capability, FileInvariantCapability):
            if set(operators) != {self.capability.operation}:
                raise ValidationError(
                    "assertion_operators must contain only the fixed file operation"
                )
        elif operators:
            raise ValidationError(
                "assertion_operators are supported only for Python and file capabilities"
            )

        limits = dict(self.capability_limits)
        policy = self.capability.policy
        authoritative_limits: dict[str, object] = {
            "max_output_bytes": policy.max_output_bytes,
            "network_isolated": False,
            "descendant_isolated": False,
            "timeout_seconds": policy.timeout_seconds,
        }
        for key, value in authoritative_limits.items():
            if key in limits and limits[key] != value:
                raise ValidationError(f"capability_limits.{key} contradicts owner execution policy")
            limits[key] = value

        view = PlannerCatalogEntryView(
            id=self.id,
            version=self.version,
            description=self.description,
            parameter_schema=self.planner_parameter_schema_dict(),
            assertion_operators=operators,
            capability_limits=limits,
            capability_digest=self.capability_digest(),
        )
        object.__setattr__(self, "assertion_operators", view.assertion_operators)
        object.__setattr__(self, "capability_limits", view.capability_limits)
        _validate_parameter_bindings(self)

    @property
    def family(self) -> str:
        return self.capability.family

    @property
    def policy(self) -> ProofCapabilityPolicy:
        return self.capability.policy

    def execution_parameter_schema_dict(self) -> dict[str, object]:
        return _schema_dict(self.execution_parameter_schema)

    def planner_parameter_schema_dict(self) -> dict[str, object]:
        return _schema_dict(self.planner_parameter_schema)

    def parameter_defaults_dict(self) -> dict[str, object]:
        return _mapping_dict(self.parameter_defaults)

    def capability_digest(self) -> str:
        """Commit to every owner-only field without revealing it to the planner."""

        return sha256_digest(
            {
                "schema": PROOF_CAPABILITY_SCHEMA,
                "entry_id": self.id,
                "entry_version": self.version,
                "family": self.family,
                "execution_parameter_schema": self.execution_parameter_schema_dict(),
                "parameter_defaults": self.parameter_defaults_dict(),
                "capability": self.capability.to_dict(),
            }
        )

    def planner_view(self) -> PlannerCatalogEntryView:
        return PlannerCatalogEntryView(
            id=self.id,
            version=self.version,
            description=self.description,
            parameter_schema=self.planner_parameter_schema_dict(),
            assertion_operators=self.assertion_operators,
            capability_limits=self.capability_limits,
            capability_digest=self.capability_digest(),
        )

    def validate_parameters(self, parameters: object) -> dict[str, object]:
        """Validate only the data fields that the planner was allowed to supply."""

        if isinstance(parameters, Mapping):
            supplied = dict(parameters)
            defaults = self.parameter_defaults_dict()
            default_keys = set(defaults)
            present_defaults = default_keys & set(supplied)
            if present_defaults:
                for key in present_defaults:
                    if sha256_digest(supplied[key]) != sha256_digest(defaults[key]):
                        raise ValidationError(
                            f"parameters.{key} cannot override a catalog-owned default"
                        )
                    supplied.pop(key)
            parameters = supplied
        return validate_planner_parameters(self.planner_parameter_schema, parameters)

    def bind_parameters(self, parameters: object) -> Mapping[str, object]:
        """Merge immutable owner defaults after planner validation and revalidate fully.

        Supplying already-bound defaults is idempotent only when their exact values
        match the catalog. This supports a workflow-wide preflight followed by executor
        dispatch without creating a second path for overriding operational defaults.
        """

        validated = self.validate_parameters(parameters)
        bound = self.parameter_defaults_dict()
        bound.update(validated)
        fully_validated = validate_planner_parameters(
            self.execution_parameter_schema,
            bound,
        )
        frozen = _freeze_json(fully_validated)
        if not isinstance(frozen, Mapping):
            raise AssertionError("bound parameters must freeze to a mapping")
        return frozen

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "family": self.family,
            "execution_parameter_schema": self.execution_parameter_schema_dict(),
            "parameter_defaults": self.parameter_defaults_dict(),
            "assertion_operators": list(self.assertion_operators),
            "capability_limits": _thaw_json(self.capability_limits),
            "capability": self.capability.to_dict(),
            "capability_digest": self.capability_digest(),
        }


@dataclass(frozen=True)
class ProofCatalog:
    """Exact active owner catalog whose digest is the planner-visible catalog digest."""

    entries: Sequence[ProofCatalogEntry]
    schema: str = PROOF_CATALOG_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROOF_CATALOG_SCHEMA:
            raise ValidationError(f"schema must be {PROOF_CATALOG_SCHEMA!r}")
        if not isinstance(self.entries, Sequence) or isinstance(
            self.entries, str | bytes | bytearray
        ):
            raise ValidationError("entries must be a sequence")
        entries = list(self.entries)
        if not entries or any(not isinstance(entry, ProofCatalogEntry) for entry in entries):
            raise ValidationError("entries must contain ProofCatalogEntry records")
        keys = [(entry.id, entry.version) for entry in entries]
        if len(set(keys)) != len(keys):
            raise ValidationError("catalog contains a duplicate id/version entry")
        ids = [entry.id for entry in entries]
        if len(set(ids)) != len(ids):
            raise ValidationError("catalog must expose only one active version per id")
        object.__setattr__(self, "entries", tuple(sorted(entries, key=lambda item: item.id)))

    def resolve(self, entry_id: str, version: str) -> ProofCatalogEntry:
        _bounded_text(entry_id, "entry_id", max_bytes=MAX_IDENTIFIER_BYTES)
        _bounded_text(version, "version", max_bytes=MAX_IDENTIFIER_BYTES)
        for entry in self.entries:
            if entry.id == entry_id and entry.version == version:
                return entry
        if any(entry.id == entry_id for entry in self.entries):
            raise ValidationError(f"catalog entry {entry_id!r} has a stale version")
        raise ValidationError(f"catalog entry {entry_id!r} is not approved")

    def planner_views(self) -> tuple[PlannerCatalogEntryView, ...]:
        return tuple(entry.planner_view() for entry in self.entries)

    def digest(self) -> str:
        return planner_catalog_digest(self.planner_views())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "entries": [entry.to_dict() for entry in self.entries],
            "planner_catalog_digest": self.digest(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())
