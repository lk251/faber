"""Provider-neutral, data-only proof-planning boundary."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from faber import schemas
from faber.canonical_json import canonical_json_bytes
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proofs import ModelRunEvidence, ProofClaim, ProofPlan, ProofTemplateSelection
from faber.validation import require_digest, require_non_empty_string, require_schema

PLANNER_CATALOG_SCHEMA = "faber.proof_planner_catalog.v1"
MAX_JSON_DEPTH = 12
MAX_JSON_ITEMS = 256
MAX_JSON_BYTES = 32_768
MAX_TEXT_BYTES = 16_384
MAX_REQUEST_BYTES = 131_072
MAX_PATTERN_LENGTH = 256
MAX_INTEGER = (1 << 63) - 1

PLANNING_ERROR_CODES = {
    "configuration_error",
    "redaction_error",
    "request_too_large",
    "authentication_error",
    "permission_error",
    "rate_limit_error",
    "transient_provider_error",
    "timeout",
    "refusal",
    "invalid_structured_output",
    "unknown_template",
    "invalid_parameters",
    "replay_mismatch",
    "unknown_requirement",
    "mandatory_claim_conflict",
    "missing_mandatory_template",
    "policy_error",
}

_EXECUTABLE_FIELD_NAMES = {
    "arg",
    "args",
    "argument",
    "arguments",
    "argv",
    "binary",
    "cmd",
    "code",
    "command",
    "commandtemplate",
    "cwd",
    "entrypoint",
    "env",
    "environment",
    "executable",
    "import",
    "importtarget",
    "interpreter",
    "module",
    "path",
    "process",
    "program",
    "python",
    "script",
    "shell",
    "source",
    "target",
    "workingdirectory",
}


class ProofPlanningError(ValidationError):
    """Stable, secret-safe failure at the advisory planner boundary."""

    def __init__(
        self,
        code: str,
        public_message: str,
        *,
        retryable: bool = False,
        model_run: ModelRunEvidence | None = None,
    ) -> None:
        if code not in PLANNING_ERROR_CODES:
            raise ValidationError(f"unknown proof-planning error code {code!r}")
        self.code = code
        self.public_message = require_non_empty_string(public_message, "public_message")
        if not isinstance(retryable, bool):
            raise ValidationError("retryable must be a boolean")
        if model_run is not None and not isinstance(model_run, ModelRunEvidence):
            raise ValidationError("model_run must be ModelRunEvidence or null")
        self.retryable = retryable
        self.model_run = model_run
        super().__init__(f"{self.code}: {self.public_message}")

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "public_message": self.public_message,
            "retryable": self.retryable,
            "model_run": self.model_run.to_dict() if self.model_run else None,
        }


def _compact_field_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(character for character in normalized.casefold() if character.isalnum())


def _field_name_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value)
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", normalized)
    return {
        token.casefold() for token in re.split(r"[^\w]+|_+", separated, flags=re.UNICODE) if token
    }


def _is_executable_field_name(value: str) -> bool:
    compact = _compact_field_name(value)
    if compact in _EXECUTABLE_FIELD_NAMES:
        return True
    dangerous_tokens = {
        "arg",
        "args",
        "argument",
        "arguments",
        "argv",
        "binary",
        "cmd",
        "code",
        "command",
        "cwd",
        "entrypoint",
        "env",
        "environment",
        "executable",
        "import",
        "interpreter",
        "module",
        "path",
        "process",
        "program",
        "python",
        "script",
        "shell",
        "source",
        "target",
    }
    return bool(_field_name_tokens(value) & dangerous_tokens)


def _bounded_text(value: object, field: str, *, max_bytes: int = MAX_TEXT_BYTES) -> str:
    text = require_non_empty_string(value, field)
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValidationError(f"{field} must be valid UTF-8 text") from None
    if size > max_bytes:
        raise ValidationError(f"{field} exceeds its UTF-8 byte limit")
    return text


def _closed_payload(
    value: object,
    name: str,
    fields: set[str],
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValidationError(f"{name} must use the exact supported field set")
    return value


def _string_tuple(
    value: object,
    field: str,
    *,
    allow_empty: bool = True,
    unique: bool = True,
    sort: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError(f"{field} must be a sequence of strings")
    result = tuple(_bounded_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if not allow_empty and not result:
        raise ValidationError(f"{field} must contain at least one string")
    if unique and len(set(result)) != len(result):
        raise ValidationError(f"{field} must not contain duplicate values")
    return tuple(sorted(result)) if sort else result


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field} must be a non-negative integer")
    if value > MAX_INTEGER:
        raise ValidationError(f"{field} exceeds the signed 64-bit limit")
    return value


def _optional_nonnegative_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, field)


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field)


def _freeze_json(
    value: object,
    field: str,
    *,
    depth: int = 0,
    reject_executable_keys: bool = False,
) -> object:
    if depth > MAX_JSON_DEPTH:
        raise ValidationError(f"{field} exceeds the JSON nesting limit")
    if value is None or isinstance(value, bool | str):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValidationError(f"{field} contains invalid UTF-8 text") from None
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_INTEGER:
            raise ValidationError(f"{field} contains an integer outside the supported range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(f"{field} contains a non-finite number")
        return value
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        if len(value) > MAX_JSON_ITEMS:
            raise ValidationError(f"{field} exceeds the JSON item limit")
        return tuple(
            _freeze_json(
                item,
                f"{field}[{index}]",
                depth=depth + 1,
                reject_executable_keys=reject_executable_keys,
            )
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_ITEMS:
            raise ValidationError(f"{field} exceeds the JSON item limit")
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{field} must use string object keys")
            if reject_executable_keys and _is_executable_field_name(key):
                raise ValidationError(f"{field} contains executable-looking field {key!r}")
            result[key] = _freeze_json(
                item,
                f"{field}.{key}",
                depth=depth + 1,
                reject_executable_keys=reject_executable_keys,
            )
        return MappingProxyType(result)
    raise ValidationError(f"{field} must contain only JSON-compatible values")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _bounded_mapping(
    value: object,
    field: str,
    *,
    reject_executable_keys: bool = False,
) -> Mapping[str, object]:
    frozen = _freeze_json(value, field, reject_executable_keys=reject_executable_keys)
    if not isinstance(frozen, Mapping):
        raise ValidationError(f"{field} must be a JSON object")
    if len(canonical_json_bytes(_thaw_json(frozen))) > MAX_JSON_BYTES:
        raise ValidationError(f"{field} exceeds the bounded JSON byte limit")
    return frozen


def _schema_integer(value: object, field: str) -> int:
    return _nonnegative_int(value, field)


def _validate_enum(value: object, field: str, expected_type: str) -> None:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray) or not value:
        raise ValidationError(f"{field} must be a non-empty array")
    digests: set[str] = set()
    for index, item in enumerate(value):
        if expected_type == "string" and not isinstance(item, str):
            raise ValidationError(f"{field}[{index}] must be a string")
        if expected_type == "integer" and (isinstance(item, bool) or not isinstance(item, int)):
            raise ValidationError(f"{field}[{index}] must be an integer")
        if expected_type == "boolean" and not isinstance(item, bool):
            raise ValidationError(f"{field}[{index}] must be a boolean")
        frozen = _freeze_json(item, f"{field}[{index}]")
        digest = sha256_digest(_thaw_json(frozen))
        if digest in digests:
            raise ValidationError(f"{field} must not contain duplicate values")
        digests.add(digest)


def _validate_schema_node(value: object, field: str, *, depth: int) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValidationError(f"{field} exceeds the schema nesting limit")
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be an object")
    kind = value.get("type")
    if kind not in {"object", "array", "string", "integer", "boolean", "null"}:
        raise ValidationError(f"{field}.type uses an unsupported JSON type")
    common = {"type", "description"}
    allowed_by_type = {
        "object": {
            "properties",
            "required",
            "additionalProperties",
            "minProperties",
            "maxProperties",
        },
        "array": {"items", "minItems", "maxItems"},
        "string": {"enum", "pattern", "minLength", "maxLength"},
        "integer": {"enum", "minimum", "maximum"},
        "boolean": {"enum"},
        "null": set(),
    }
    unknown = sorted(set(value) - common - allowed_by_type[str(kind)])
    if unknown:
        raise ValidationError(f"{field} contains unsupported schema keywords: {unknown}")
    if "description" in value:
        _bounded_text(value.get("description"), f"{field}.description", max_bytes=2048)

    if kind == "object":
        properties = value.get("properties")
        if not isinstance(properties, Mapping):
            raise ValidationError(f"{field}.properties must be an object")
        if len(properties) > MAX_JSON_ITEMS:
            raise ValidationError(f"{field}.properties exceeds the field limit")
        for key, schema_node in properties.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(f"{field}.properties must use non-empty string keys")
            if _is_executable_field_name(key):
                raise ValidationError(
                    f"{field}.properties contains executable-looking field {key!r}"
                )
            _validate_schema_node(schema_node, f"{field}.properties.{key}", depth=depth + 1)
        required = _string_tuple(
            value.get("required", ()),
            f"{field}.required",
            sort=True,
        )
        missing = sorted(set(required) - set(properties))
        if missing:
            raise ValidationError(f"{field}.required references unknown fields: {missing}")
        if value.get("additionalProperties") is not False:
            raise ValidationError(f"{field}.additionalProperties must be false")
        minimum = _schema_integer(value.get("minProperties", 0), f"{field}.minProperties")
        maximum = _schema_integer(
            value.get("maxProperties", len(properties)),
            f"{field}.maxProperties",
        )
        if minimum > maximum or maximum > len(properties):
            raise ValidationError(f"{field} has invalid property bounds")
    elif kind == "array":
        if "items" not in value:
            raise ValidationError(f"{field}.items is required")
        _validate_schema_node(value.get("items"), f"{field}.items", depth=depth + 1)
        minimum = _schema_integer(value.get("minItems", 0), f"{field}.minItems")
        maximum = _schema_integer(value.get("maxItems", MAX_JSON_ITEMS), f"{field}.maxItems")
        if minimum > maximum or maximum > MAX_JSON_ITEMS:
            raise ValidationError(f"{field} has invalid item bounds")
    elif kind == "string":
        minimum = _schema_integer(value.get("minLength", 0), f"{field}.minLength")
        maximum = _schema_integer(value.get("maxLength", MAX_TEXT_BYTES), f"{field}.maxLength")
        if minimum > maximum or maximum > MAX_TEXT_BYTES:
            raise ValidationError(f"{field} has invalid string bounds")
        if "enum" in value:
            _validate_enum(value.get("enum"), f"{field}.enum", "string")
        if "pattern" in value:
            pattern = _bounded_text(
                value.get("pattern"),
                f"{field}.pattern",
                max_bytes=MAX_PATTERN_LENGTH,
            )
            try:
                re.compile(pattern)
            except re.error:
                raise ValidationError(
                    f"{field}.pattern is not a valid regular expression"
                ) from None
    elif kind == "integer":
        minimum = value.get("minimum", -MAX_INTEGER)
        maximum = value.get("maximum", MAX_INTEGER)
        if (
            isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or isinstance(maximum, bool)
            or not isinstance(maximum, int)
            or abs(minimum) > MAX_INTEGER
            or abs(maximum) > MAX_INTEGER
            or minimum > maximum
        ):
            raise ValidationError(f"{field} has invalid integer bounds")
        if "enum" in value:
            _validate_enum(value.get("enum"), f"{field}.enum", "integer")
    elif kind == "boolean" and "enum" in value:
        _validate_enum(value.get("enum"), f"{field}.enum", "boolean")


def validate_parameter_schema(value: object) -> Mapping[str, object]:
    """Validate and freeze the dependency-light parameter-schema subset."""

    _validate_schema_node(value, "parameter_schema", depth=0)
    if not isinstance(value, Mapping) or value.get("type") != "object":
        raise ValidationError("parameter_schema root type must be object")
    frozen = _bounded_mapping(value, "parameter_schema", reject_executable_keys=False)
    return frozen


def _require_strict_output_schema(value: Mapping[str, object], field: str) -> None:
    """Enforce the Structured Outputs all-properties-required subset."""

    kind = value.get("type")
    if kind == "object":
        properties = value.get("properties")
        required = value.get("required")
        if not isinstance(properties, Mapping) or not isinstance(required, Sequence):
            raise AssertionError("validated object schema has invalid structure")
        if set(required) != set(properties):
            raise ValidationError(
                f"{field} must require every property for strict structured output"
            )
        for key, nested in properties.items():
            if not isinstance(nested, Mapping):
                raise AssertionError("validated property schema must be an object")
            _require_strict_output_schema(nested, f"{field}.properties.{key}")
    elif kind == "array":
        items = value.get("items")
        if not isinstance(items, Mapping):
            raise AssertionError("validated array schema must contain an items object")
        _require_strict_output_schema(items, f"{field}.items")


def _validated_schema_int(
    schema: Mapping[str, object],
    field: str,
    default: int,
) -> int:
    value = schema.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"validated schema field {field!r} must be an integer")
    return value


def _enum_allows(schema: Mapping[str, object], value: object) -> bool:
    enum = schema.get("enum")
    if enum is None:
        return True
    if not isinstance(enum, Sequence) or isinstance(enum, str | bytes | bytearray):
        raise AssertionError("validated enum must be an array")
    return value in enum


def _validate_schema_value(value: object, schema: Mapping[str, object], field: str) -> object:
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, Mapping):
            raise ValidationError(f"{field} must be an object")
        properties = schema["properties"]
        if not isinstance(properties, Mapping):
            raise AssertionError("validated object schema must contain properties")
        unknown = sorted(set(value) - set(properties))
        if unknown:
            raise ValidationError(f"{field} contains unknown fields: {unknown}")
        required = schema.get("required", ())
        if not isinstance(required, Sequence):
            raise AssertionError("validated object schema must use an array for required")
        missing = sorted(set(required) - set(value))
        if missing:
            raise ValidationError(f"{field} is missing required fields: {missing}")
        minimum = _validated_schema_int(schema, "minProperties", 0)
        maximum = _validated_schema_int(schema, "maxProperties", len(properties))
        if not minimum <= len(value) <= maximum:
            raise ValidationError(f"{field} violates its property-count bounds")
        result: dict[str, object] = {}
        for key, item in value.items():
            nested = properties[key]
            if not isinstance(nested, Mapping):
                raise AssertionError("validated property schema must be an object")
            result[str(key)] = _validate_schema_value(item, nested, f"{field}.{key}")
        return result
    if kind == "array":
        if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
            raise ValidationError(f"{field} must be an array")
        minimum = _validated_schema_int(schema, "minItems", 0)
        maximum = _validated_schema_int(schema, "maxItems", MAX_JSON_ITEMS)
        if not minimum <= len(value) <= maximum:
            raise ValidationError(f"{field} violates its item-count bounds")
        nested = schema["items"]
        if not isinstance(nested, Mapping):
            raise AssertionError("validated array schema must contain an object items schema")
        return [
            _validate_schema_value(item, nested, f"{field}[{index}]")
            for index, item in enumerate(value)
        ]
    if kind == "string":
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be a string")
        _bounded_text(value or " ", field, max_bytes=MAX_TEXT_BYTES)
        minimum = _validated_schema_int(schema, "minLength", 0)
        maximum = _validated_schema_int(schema, "maxLength", MAX_TEXT_BYTES)
        if not minimum <= len(value) <= maximum:
            raise ValidationError(f"{field} violates its string-length bounds")
        if not _enum_allows(schema, value):
            raise ValidationError(f"{field} is not an allowed enum value")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise ValidationError(f"{field} does not match the required pattern")
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"{field} must be an integer")
        minimum = _validated_schema_int(schema, "minimum", -MAX_INTEGER)
        maximum = _validated_schema_int(schema, "maximum", MAX_INTEGER)
        if not minimum <= value <= maximum:
            raise ValidationError(f"{field} violates its integer bounds")
        if not _enum_allows(schema, value):
            raise ValidationError(f"{field} is not an allowed enum value")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"{field} must be a boolean")
        if not _enum_allows(schema, value):
            raise ValidationError(f"{field} is not an allowed enum value")
        return value
    if value is not None:
        raise ValidationError(f"{field} must be null")
    return None


def validate_planner_parameters(
    schema: Mapping[str, object],
    parameters: object,
) -> dict[str, object]:
    """Return a detached validated parameter object or fail without repair."""

    validate_parameter_schema(schema)
    validated = _validate_schema_value(parameters, schema, "parameters")
    if not isinstance(validated, dict):
        raise AssertionError("object parameter schema must produce an object")
    frozen = _bounded_mapping(validated, "parameters", reject_executable_keys=True)
    thawed = _thaw_json(frozen)
    if not isinstance(thawed, dict):
        raise AssertionError("validated parameters must thaw to an object")
    return thawed


@dataclass(frozen=True)
class PlannerCatalogEntryView:
    """Data-only model view of one repository-approved proof capability."""

    id: str
    version: str
    description: str
    parameter_schema: Mapping[str, object]
    assertion_operators: Sequence[str]
    capability_limits: Mapping[str, object]
    capability_digest: str
    schema: str = schemas.PLANNER_CATALOG_ENTRY_VIEW

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PLANNER_CATALOG_ENTRY_VIEW)
        _bounded_text(self.id, "id", max_bytes=256)
        _bounded_text(self.version, "version", max_bytes=128)
        _bounded_text(self.description, "description", max_bytes=4096)
        validated_schema = validate_parameter_schema(self.parameter_schema)
        _require_strict_output_schema(validated_schema, "parameter_schema")
        object.__setattr__(
            self,
            "parameter_schema",
            validated_schema,
        )
        object.__setattr__(
            self,
            "assertion_operators",
            _string_tuple(self.assertion_operators, "assertion_operators", sort=True),
        )
        object.__setattr__(
            self,
            "capability_limits",
            _bounded_mapping(
                self.capability_limits,
                "capability_limits",
                reject_executable_keys=True,
            ),
        )
        require_digest(self.capability_digest, "capability_digest")

    def parameter_schema_dict(self) -> dict[str, object]:
        value = _thaw_json(self.parameter_schema)
        if not isinstance(value, dict):
            raise AssertionError("parameter schema must thaw to an object")
        return value

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "parameter_schema": self.parameter_schema_dict(),
            "assertion_operators": list(self.assertion_operators),
            "capability_limits": _thaw_json(self.capability_limits),
            "capability_digest": self.capability_digest,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> PlannerCatalogEntryView:
        value = _closed_payload(
            payload,
            "PlannerCatalogEntryView",
            {
                "schema",
                "id",
                "version",
                "description",
                "parameter_schema",
                "assertion_operators",
                "capability_limits",
                "capability_digest",
            },
        )
        parameter_schema = value.get("parameter_schema")
        capability_limits = value.get("capability_limits")
        if not isinstance(parameter_schema, Mapping) or not isinstance(capability_limits, Mapping):
            raise ValidationError("planner catalog mappings must be objects")
        result = cls(
            schema=require_non_empty_string(value.get("schema"), "schema"),
            id=require_non_empty_string(value.get("id"), "id"),
            version=require_non_empty_string(value.get("version"), "version"),
            description=require_non_empty_string(value.get("description"), "description"),
            parameter_schema=parameter_schema,
            assertion_operators=_string_tuple(
                value.get("assertion_operators"), "assertion_operators"
            ),
            capability_limits=capability_limits,
            capability_digest=require_digest(value.get("capability_digest"), "capability_digest"),
        )
        if result.to_dict() != dict(payload):
            raise ValidationError("PlannerCatalogEntryView fields do not round-trip exactly")
        return result


def planner_catalog_digest(entries: Sequence[PlannerCatalogEntryView]) -> str:
    if not isinstance(entries, Sequence) or isinstance(entries, str | bytes | bytearray):
        raise ValidationError("catalog entries must be a sequence")
    values = list(entries)
    if not values or any(not isinstance(entry, PlannerCatalogEntryView) for entry in values):
        raise ValidationError("catalog entries must contain PlannerCatalogEntryView records")
    keys = [(entry.id, entry.version) for entry in values]
    if len(set(keys)) != len(keys):
        raise ValidationError("catalog entries must not contain duplicate id/version pairs")
    ids = [entry.id for entry in values]
    if len(set(ids)) != len(ids):
        raise ValidationError("catalog entries must expose only one active version per id")
    ordered = sorted(values, key=lambda entry: (entry.id, entry.version))
    return sha256_digest(
        {
            "schema": PLANNER_CATALOG_SCHEMA,
            "entries": [entry.to_dict() for entry in ordered],
        }
    )


def _requirement_reference_set(
    requirements: Sequence[str],
    acceptance_criteria: Sequence[str],
    rejection_criteria: Sequence[str],
) -> set[str]:
    references = set(requirements) | set(acceptance_criteria) | set(rejection_criteria)
    references.update(f"requirement:{index}" for index in range(len(requirements)))
    references.update(f"acceptance:{index}" for index in range(len(acceptance_criteria)))
    references.update(f"rejection:{index}" for index in range(len(rejection_criteria)))
    return references


@dataclass(frozen=True)
class PlanningFileSummary:
    """Bounded repository-owner-selected file context; never an executable path."""

    identifier: str
    summary: str
    content_digest: str
    schema: str = schemas.PLANNING_FILE_SUMMARY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PLANNING_FILE_SUMMARY)
        _bounded_text(self.identifier, "identifier", max_bytes=1024)
        _bounded_text(self.summary, "summary", max_bytes=4096)
        require_digest(self.content_digest, "content_digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "identifier": self.identifier,
            "summary": self.summary,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> PlanningFileSummary:
        value = _closed_payload(
            payload,
            "PlanningFileSummary",
            {"schema", "identifier", "summary", "content_digest"},
        )
        result = cls(
            schema=require_non_empty_string(value.get("schema"), "schema"),
            identifier=require_non_empty_string(value.get("identifier"), "identifier"),
            summary=require_non_empty_string(value.get("summary"), "summary"),
            content_digest=require_digest(value.get("content_digest"), "content_digest"),
        )
        if result.to_dict() != dict(payload):
            raise ValidationError("PlanningFileSummary fields do not round-trip exactly")
        return result


@dataclass(frozen=True)
class ProofPlanningRequest:
    """Exact bounded and redacted advisory request sent to a planner backend."""

    task_contract_id: str
    task_contract_digest: str
    task_title: str
    task_description: str
    requirements: Sequence[str]
    acceptance_criteria: Sequence[str]
    rejection_criteria: Sequence[str]
    attempt_id: str
    attempt_digest: str
    base_revision: str
    candidate_revision: str
    diff_digest: str
    redacted_diff_digest: str
    redacted_diff_text: str
    max_diff_bytes: int
    diff_truncated: bool
    file_summaries: Sequence[PlanningFileSummary]
    proof_catalog_digest: str
    catalog_entries: Sequence[PlannerCatalogEntryView]
    mandatory_claims: Sequence[ProofClaim]
    mandatory_template_ids: Sequence[str]
    prompt_template_version: str
    prompt_template_digest: str
    response_schema_version: str
    response_schema_digest: str
    redaction_summary: Mapping[str, object]
    schema: str = schemas.PROOF_PLANNING_REQUEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_PLANNING_REQUEST)
        for field in (
            "task_contract_id",
            "task_title",
            "task_description",
            "attempt_id",
            "base_revision",
            "candidate_revision",
            "redacted_diff_text",
            "prompt_template_version",
            "response_schema_version",
        ):
            _bounded_text(getattr(self, field), field)
        for field in (
            "task_contract_digest",
            "attempt_digest",
            "diff_digest",
            "redacted_diff_digest",
            "proof_catalog_digest",
            "prompt_template_digest",
            "response_schema_digest",
        ):
            require_digest(getattr(self, field), field)
        if sha256_digest(self.redacted_diff_text) != self.redacted_diff_digest:
            raise ValidationError("redacted_diff_digest must bind the redacted diff text")
        max_diff_bytes = _nonnegative_int(self.max_diff_bytes, "max_diff_bytes")
        if max_diff_bytes < 1:
            raise ValidationError("max_diff_bytes must be positive")
        if len(self.redacted_diff_text.encode("utf-8")) > max_diff_bytes:
            raise ValidationError("redacted_diff_text exceeds max_diff_bytes")
        if not isinstance(self.diff_truncated, bool):
            raise ValidationError("diff_truncated must be a boolean")
        object.__setattr__(
            self,
            "requirements",
            _string_tuple(self.requirements, "requirements", allow_empty=False, unique=False),
        )
        object.__setattr__(
            self,
            "acceptance_criteria",
            _string_tuple(self.acceptance_criteria, "acceptance_criteria", unique=False),
        )
        object.__setattr__(
            self,
            "rejection_criteria",
            _string_tuple(self.rejection_criteria, "rejection_criteria", unique=False),
        )
        summaries = list(self.file_summaries)
        if any(not isinstance(item, PlanningFileSummary) for item in summaries):
            raise ValidationError("file_summaries must contain PlanningFileSummary records")
        if len({item.identifier for item in summaries}) != len(summaries):
            raise ValidationError("file_summaries must use unique identifiers")
        object.__setattr__(
            self, "file_summaries", tuple(sorted(summaries, key=lambda item: item.identifier))
        )
        entries = list(self.catalog_entries)
        computed_catalog_digest = planner_catalog_digest(entries)
        if computed_catalog_digest != self.proof_catalog_digest:
            raise ValidationError("proof_catalog_digest must bind the exact exposed catalog")
        object.__setattr__(
            self,
            "catalog_entries",
            tuple(sorted(entries, key=lambda entry: (entry.id, entry.version))),
        )
        claims = list(self.mandatory_claims)
        if any(not isinstance(claim, ProofClaim) for claim in claims):
            raise ValidationError("mandatory_claims must contain ProofClaim records")
        if len({claim.id for claim in claims}) != len(claims):
            raise ValidationError("mandatory_claims must use unique IDs")
        object.__setattr__(
            self, "mandatory_claims", tuple(sorted(claims, key=lambda claim: claim.id))
        )
        mandatory_templates = _string_tuple(
            self.mandatory_template_ids,
            "mandatory_template_ids",
            sort=True,
        )
        unknown_templates = sorted(
            set(mandatory_templates) - {entry.id for entry in self.catalog_entries}
        )
        if unknown_templates:
            raise ValidationError(
                f"mandatory_template_ids reference unknown catalog entries: {unknown_templates}"
            )
        object.__setattr__(self, "mandatory_template_ids", mandatory_templates)
        allowed_refs = _requirement_reference_set(
            self.requirements,
            self.acceptance_criteria,
            self.rejection_criteria,
        )
        for claim in self.mandatory_claims:
            unknown_refs = sorted(set(claim.requirement_refs) - allowed_refs)
            if unknown_refs:
                raise ValidationError(
                    f"mandatory claim {claim.id!r} references unknown requirements: {unknown_refs}"
                )
        object.__setattr__(
            self,
            "redaction_summary",
            _bounded_mapping(self.redaction_summary, "redaction_summary"),
        )
        if len(canonical_json_bytes(self.to_dict())) > MAX_REQUEST_BYTES:
            raise ValidationError("planning request exceeds the protocol byte limit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "task_title": self.task_title,
            "task_description": self.task_description,
            "requirements": list(self.requirements),
            "acceptance_criteria": list(self.acceptance_criteria),
            "rejection_criteria": list(self.rejection_criteria),
            "attempt_id": self.attempt_id,
            "attempt_digest": self.attempt_digest,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "diff_digest": self.diff_digest,
            "redacted_diff_digest": self.redacted_diff_digest,
            "redacted_diff_text": self.redacted_diff_text,
            "max_diff_bytes": self.max_diff_bytes,
            "diff_truncated": self.diff_truncated,
            "file_summaries": [summary.to_dict() for summary in self.file_summaries],
            "proof_catalog_digest": self.proof_catalog_digest,
            "catalog_entries": [entry.to_dict() for entry in self.catalog_entries],
            "mandatory_claims": [claim.to_dict() for claim in self.mandatory_claims],
            "mandatory_template_ids": list(self.mandatory_template_ids),
            "prompt_template_version": self.prompt_template_version,
            "prompt_template_digest": self.prompt_template_digest,
            "response_schema_version": self.response_schema_version,
            "response_schema_digest": self.response_schema_digest,
            "redaction_summary": _thaw_json(self.redaction_summary),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofPlanningRequest:
        value = _closed_payload(
            payload,
            "ProofPlanningRequest",
            {
                "schema",
                "task_contract_id",
                "task_contract_digest",
                "task_title",
                "task_description",
                "requirements",
                "acceptance_criteria",
                "rejection_criteria",
                "attempt_id",
                "attempt_digest",
                "base_revision",
                "candidate_revision",
                "diff_digest",
                "redacted_diff_digest",
                "redacted_diff_text",
                "max_diff_bytes",
                "diff_truncated",
                "file_summaries",
                "proof_catalog_digest",
                "catalog_entries",
                "mandatory_claims",
                "mandatory_template_ids",
                "prompt_template_version",
                "prompt_template_digest",
                "response_schema_version",
                "response_schema_digest",
                "redaction_summary",
            },
        )
        max_diff_bytes = value.get("max_diff_bytes")
        diff_truncated = value.get("diff_truncated")
        if isinstance(max_diff_bytes, bool) or not isinstance(max_diff_bytes, int):
            raise ValidationError("max_diff_bytes must be an integer")
        if not isinstance(diff_truncated, bool):
            raise ValidationError("diff_truncated must be a boolean")
        raw_file_summaries = value.get("file_summaries")
        raw_entries = value.get("catalog_entries")
        raw_claims = value.get("mandatory_claims")
        redaction_summary = value.get("redaction_summary")
        if (
            not isinstance(raw_file_summaries, Sequence)
            or isinstance(raw_file_summaries, str | bytes | bytearray)
            or not isinstance(raw_entries, Sequence)
            or isinstance(raw_entries, str | bytes | bytearray)
            or not isinstance(raw_claims, Sequence)
            or isinstance(raw_claims, str | bytes | bytearray)
            or not isinstance(redaction_summary, Mapping)
        ):
            raise ValidationError("planning request nested records use invalid shapes")
        result = cls(
            schema=require_non_empty_string(value.get("schema"), "schema"),
            task_contract_id=require_non_empty_string(
                value.get("task_contract_id"), "task_contract_id"
            ),
            task_contract_digest=require_digest(
                value.get("task_contract_digest"), "task_contract_digest"
            ),
            task_title=require_non_empty_string(value.get("task_title"), "task_title"),
            task_description=require_non_empty_string(
                value.get("task_description"), "task_description"
            ),
            requirements=_string_tuple(
                value.get("requirements"),
                "requirements",
                allow_empty=False,
                unique=False,
            ),
            acceptance_criteria=_string_tuple(
                value.get("acceptance_criteria"),
                "acceptance_criteria",
                unique=False,
            ),
            rejection_criteria=_string_tuple(
                value.get("rejection_criteria"),
                "rejection_criteria",
                unique=False,
            ),
            attempt_id=require_non_empty_string(value.get("attempt_id"), "attempt_id"),
            attempt_digest=require_digest(value.get("attempt_digest"), "attempt_digest"),
            base_revision=require_non_empty_string(value.get("base_revision"), "base_revision"),
            candidate_revision=require_non_empty_string(
                value.get("candidate_revision"), "candidate_revision"
            ),
            diff_digest=require_digest(value.get("diff_digest"), "diff_digest"),
            redacted_diff_digest=require_digest(
                value.get("redacted_diff_digest"), "redacted_diff_digest"
            ),
            redacted_diff_text=require_non_empty_string(
                value.get("redacted_diff_text"), "redacted_diff_text"
            ),
            max_diff_bytes=max_diff_bytes,
            diff_truncated=diff_truncated,
            file_summaries=[
                PlanningFileSummary.from_dict(
                    _closed_payload(
                        item,
                        f"file_summaries[{index}]",
                        {"schema", "identifier", "summary", "content_digest"},
                    )
                )
                for index, item in enumerate(raw_file_summaries)
            ],
            proof_catalog_digest=require_digest(
                value.get("proof_catalog_digest"), "proof_catalog_digest"
            ),
            catalog_entries=[
                PlannerCatalogEntryView.from_dict(
                    _closed_payload(
                        item,
                        f"catalog_entries[{index}]",
                        {
                            "schema",
                            "id",
                            "version",
                            "description",
                            "parameter_schema",
                            "assertion_operators",
                            "capability_limits",
                            "capability_digest",
                        },
                    )
                )
                for index, item in enumerate(raw_entries)
            ],
            mandatory_claims=[
                ProofClaim.from_dict(
                    _closed_payload(
                        item,
                        f"mandatory_claims[{index}]",
                        {
                            "schema",
                            "id",
                            "statement",
                            "severity",
                            "requirement_refs",
                            "evidence_required",
                            "risk_rationale",
                        },
                    )
                )
                for index, item in enumerate(raw_claims)
            ],
            mandatory_template_ids=_string_tuple(
                value.get("mandatory_template_ids"),
                "mandatory_template_ids",
            ),
            prompt_template_version=require_non_empty_string(
                value.get("prompt_template_version"), "prompt_template_version"
            ),
            prompt_template_digest=require_digest(
                value.get("prompt_template_digest"), "prompt_template_digest"
            ),
            response_schema_version=require_non_empty_string(
                value.get("response_schema_version"), "response_schema_version"
            ),
            response_schema_digest=require_digest(
                value.get("response_schema_digest"), "response_schema_digest"
            ),
            redaction_summary=redaction_summary,
        )
        if result.to_dict() != dict(payload):
            raise ValidationError("ProofPlanningRequest fields do not round-trip exactly")
        return result


@dataclass(frozen=True)
class ProviderPlanningResponse:
    """Normalized provider data before authoritative local validation."""

    provider_adapter_id: str
    requested_model_id: str
    mode: str
    structured_response: Mapping[str, object]
    returned_model_id: str | None = None
    response_id: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    refusal: str | None = None
    error_code: str | None = None
    schema: str = schemas.PROVIDER_PLANNING_RESPONSE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROVIDER_PLANNING_RESPONSE)
        _bounded_text(self.provider_adapter_id, "provider_adapter_id", max_bytes=256)
        _bounded_text(self.requested_model_id, "requested_model_id", max_bytes=256)
        if self.mode not in {"live", "replay"}:
            raise ValidationError("mode must be 'live' or 'replay'")
        for field in ("returned_model_id", "response_id", "refusal", "error_code"):
            object.__setattr__(self, field, _optional_string(getattr(self, field), field))
        if self.error_code is not None and self.error_code not in PLANNING_ERROR_CODES:
            raise ValidationError("error_code is not a stable proof-planning category")
        for field in ("latency_ms", "input_tokens", "output_tokens"):
            _optional_nonnegative_int(getattr(self, field), field)
        object.__setattr__(
            self,
            "structured_response",
            _bounded_mapping(self.structured_response, "structured_response"),
        )

    def structured_response_dict(self) -> dict[str, object]:
        value = _thaw_json(self.structured_response)
        if not isinstance(value, dict):
            raise AssertionError("structured response must thaw to an object")
        return value

    def structured_response_digest(self) -> str:
        return sha256_digest(self.structured_response_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "provider_adapter_id": self.provider_adapter_id,
            "requested_model_id": self.requested_model_id,
            "returned_model_id": self.returned_model_id,
            "response_id": self.response_id,
            "mode": self.mode,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "refusal": self.refusal,
            "error_code": self.error_code,
            "structured_response": self.structured_response_dict(),
        }


class ProofPlannerBackend(Protocol):
    def plan(self, request: ProofPlanningRequest) -> ProviderPlanningResponse: ...


def _record_payload(
    value: object,
    name: str,
    fields: set[str],
    *,
    model_run: ModelRunEvidence,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProofPlanningError(
            "invalid_structured_output",
            f"{name} must be an object",
            model_run=model_run,
        )
    unknown = sorted(set(value) - fields)
    missing = sorted(fields - set(value))
    if unknown or missing:
        raise ProofPlanningError(
            "invalid_structured_output",
            f"{name} does not match the closed response schema",
            model_run=model_run,
        )
    return value


def _record_sequence(value: object, field: str, model_run: ModelRunEvidence) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ProofPlanningError(
            "invalid_structured_output",
            f"{field} must be an array",
            model_run=model_run,
        )
    if len(value) > MAX_JSON_ITEMS:
        raise ProofPlanningError(
            "invalid_structured_output",
            f"{field} exceeds the item limit",
            model_run=model_run,
        )
    return value


def _model_run(
    request: ProofPlanningRequest,
    response: ProviderPlanningResponse,
) -> ModelRunEvidence:
    return ModelRunEvidence(
        provider_adapter_id=response.provider_adapter_id,
        requested_model_id=response.requested_model_id,
        returned_model_id=response.returned_model_id,
        response_id=response.response_id,
        prompt_template_version=request.prompt_template_version,
        request_digest=request.digest(),
        structured_response_digest=response.structured_response_digest(),
        response_schema_version=request.response_schema_version,
        mode=response.mode,
        latency_ms=response.latency_ms,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        refusal=response.refusal,
        error_code=response.error_code,
    )


def materialize_proof_plan(
    request: ProofPlanningRequest,
    response: ProviderPlanningResponse,
) -> ProofPlanningResult:
    """Validate advisory provider data and bind it to immutable local authority context."""

    if not isinstance(request, ProofPlanningRequest):
        raise ProofPlanningError("policy_error", "request must be ProofPlanningRequest")
    if not isinstance(response, ProviderPlanningResponse):
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider response has the wrong record type",
        )
    model_run = _model_run(request, response)
    if response.refusal is not None:
        raise ProofPlanningError(
            "refusal",
            "the provider refused the proof-planning request",
            model_run=model_run,
        )
    if response.error_code is not None:
        raise ProofPlanningError(
            response.error_code,
            "the provider returned a terminal proof-planning error",
            model_run=model_run,
        )
    payload = _record_payload(
        response.structured_response,
        "structured response",
        {
            "schema",
            "claims",
            "selections",
            "uncovered_claim_ids",
            "human_review_recommended",
            "uncertainty_notes",
        },
        model_run=model_run,
    )
    if payload.get("schema") != request.response_schema_version:
        raise ProofPlanningError(
            "invalid_structured_output",
            "structured response uses the wrong schema version",
            model_run=model_run,
        )

    allowed_refs = _requirement_reference_set(
        request.requirements,
        request.acceptance_criteria,
        request.rejection_criteria,
    )
    claims: list[ProofClaim] = []
    try:
        for index, raw in enumerate(_record_sequence(payload.get("claims"), "claims", model_run)):
            claim_payload = _record_payload(
                raw,
                f"claims[{index}]",
                {
                    "id",
                    "statement",
                    "severity",
                    "requirement_refs",
                    "evidence_required",
                    "risk_rationale",
                },
                model_run=model_run,
            )
            refs = _string_tuple(
                claim_payload.get("requirement_refs"),
                f"claims[{index}].requirement_refs",
                allow_empty=False,
                sort=True,
            )
            unknown_refs = sorted(set(refs) - allowed_refs)
            if unknown_refs:
                raise ProofPlanningError(
                    "unknown_requirement",
                    "a proof claim references a requirement outside the planning request",
                    model_run=model_run,
                )
            evidence_required = claim_payload.get("evidence_required")
            if evidence_required is not True:
                raise ValidationError("planner claims must require executable evidence")
            claims.append(
                ProofClaim(
                    id=require_non_empty_string(claim_payload.get("id"), "id"),
                    statement=require_non_empty_string(claim_payload.get("statement"), "statement"),
                    severity=require_non_empty_string(claim_payload.get("severity"), "severity"),
                    requirement_refs=refs,
                    evidence_required=evidence_required,
                    risk_rationale=_optional_string(
                        claim_payload.get("risk_rationale"), "risk_rationale"
                    ),
                )
            )
        if len({claim.id for claim in claims}) != len(claims):
            raise ValidationError("claims contain duplicate IDs")
    except ProofPlanningError:
        raise
    except ValidationError:
        raise ProofPlanningError(
            "invalid_structured_output",
            "a proof claim failed local validation",
            model_run=model_run,
        ) from None

    claim_by_id = {claim.id: claim for claim in claims}
    inserted_mandatory: set[str] = set()
    for mandatory in request.mandatory_claims:
        existing = claim_by_id.get(mandatory.id)
        if existing is not None and existing.to_dict() != mandatory.to_dict():
            raise ProofPlanningError(
                "mandatory_claim_conflict",
                "the provider contradicted a mandatory policy claim",
                model_run=model_run,
            )
        if existing is None:
            claims.append(mandatory)
            claim_by_id[mandatory.id] = mandatory
            inserted_mandatory.add(mandatory.id)

    entries = {(entry.id, entry.version): entry for entry in request.catalog_entries}
    selections: list[ProofTemplateSelection] = []
    try:
        raw_selections = _record_sequence(payload.get("selections"), "selections", model_run)
        for index, raw in enumerate(raw_selections):
            selection_payload = _record_payload(
                raw,
                f"selections[{index}]",
                {
                    "claim_id",
                    "template_id",
                    "template_version",
                    "parameters",
                    "expected_behavior",
                    "rationale",
                },
                model_run=model_run,
            )
            template_id = require_non_empty_string(
                selection_payload.get("template_id"), "template_id"
            )
            template_version = require_non_empty_string(
                selection_payload.get("template_version"), "template_version"
            )
            entry = entries.get((template_id, template_version))
            if entry is None:
                raise ProofPlanningError(
                    "unknown_template",
                    "the provider selected an unknown or stale proof template",
                    model_run=model_run,
                )
            try:
                parameters = validate_planner_parameters(
                    entry.parameter_schema,
                    selection_payload.get("parameters"),
                )
            except ValidationError:
                raise ProofPlanningError(
                    "invalid_parameters",
                    "proof-template parameters failed the approved schema",
                    model_run=model_run,
                ) from None
            selections.append(
                ProofTemplateSelection(
                    claim_id=require_non_empty_string(
                        selection_payload.get("claim_id"), "claim_id"
                    ),
                    template_id=template_id,
                    template_version=template_version,
                    parameters=parameters,
                    expected_behavior=require_non_empty_string(
                        selection_payload.get("expected_behavior"),
                        "expected_behavior",
                    ),
                    rationale=require_non_empty_string(
                        selection_payload.get("rationale"), "rationale"
                    ),
                )
            )
    except ProofPlanningError:
        raise
    except ValidationError:
        raise ProofPlanningError(
            "invalid_structured_output",
            "a proof-template selection failed local validation",
            model_run=model_run,
        ) from None

    selected_template_ids = {selection.template_id for selection in selections}
    if set(request.mandatory_template_ids) - selected_template_ids:
        raise ProofPlanningError(
            "missing_mandatory_template",
            "the provider omitted a mandatory proof template",
            model_run=model_run,
        )
    selected_claim_ids = {selection.claim_id for selection in selections}
    covered_refs = {
        requirement_ref for claim in claims for requirement_ref in claim.requirement_refs
    }
    request_coverage_incomplete = any(
        value not in covered_refs and f"{prefix}:{index}" not in covered_refs
        for prefix, values in (
            ("requirement", request.requirements),
            ("acceptance", request.acceptance_criteria),
            ("rejection", request.rejection_criteria),
        )
        for index, value in enumerate(values)
    )
    try:
        uncovered = set(
            _string_tuple(
                payload.get("uncovered_claim_ids"),
                "uncovered_claim_ids",
                sort=True,
            )
        )
        uncovered.update(
            claim.id for claim in request.mandatory_claims if claim.id not in selected_claim_ids
        )
        human_review = payload.get("human_review_recommended")
        if not isinstance(human_review, bool):
            raise ValidationError("human_review_recommended must be a boolean")
        human_review = (
            human_review
            or request_coverage_incomplete
            or bool(inserted_mandatory)
            or bool(set(claim.id for claim in request.mandatory_claims) - selected_claim_ids)
        )
        uncertainty_notes = _string_tuple(
            payload.get("uncertainty_notes"),
            "uncertainty_notes",
            sort=True,
        )
        plan = ProofPlan(
            task_contract_id=request.task_contract_id,
            task_contract_digest=request.task_contract_digest,
            attempt_id=request.attempt_id,
            attempt_digest=request.attempt_digest,
            base_revision=request.base_revision,
            candidate_revision=request.candidate_revision,
            diff_digest=request.diff_digest,
            proof_catalog_digest=request.proof_catalog_digest,
            prompt_template_version=request.prompt_template_version,
            claims=claims,
            selections=selections,
            mandatory_claim_ids=[claim.id for claim in request.mandatory_claims],
            mandatory_template_ids=request.mandatory_template_ids,
            uncovered_claim_ids=sorted(uncovered),
            human_review_recommended=human_review,
            model_run=model_run,
        )
    except ValidationError:
        raise ProofPlanningError(
            "invalid_structured_output",
            "the provider output could not form a valid proof plan",
            model_run=model_run,
        ) from None
    return ProofPlanningResult(
        plan=plan,
        model_run=model_run,
        uncertainty_notes=uncertainty_notes,
        structured_response_digest=response.structured_response_digest(),
    )


def semantic_proof_plan_digest(plan: ProofPlan) -> str:
    """Digest advisory plan meaning while excluding live/replay transport metadata."""

    if not isinstance(plan, ProofPlan):
        raise ValidationError("plan must be ProofPlan")
    payload = plan.to_dict()
    payload.pop("model_run")
    return sha256_digest(payload)


@dataclass(frozen=True)
class ProofPlanningResult:
    """Validated plan plus non-authoritative provider context and uncertainty."""

    plan: ProofPlan
    model_run: ModelRunEvidence
    uncertainty_notes: Sequence[str]
    structured_response_digest: str
    schema: str = schemas.PROOF_PLANNING_RESULT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_PLANNING_RESULT)
        if not isinstance(self.plan, ProofPlan):
            raise ValidationError("plan must be ProofPlan")
        if not isinstance(self.model_run, ModelRunEvidence):
            raise ValidationError("model_run must be ModelRunEvidence")
        if self.plan.model_run.digest() != self.model_run.digest():
            raise ValidationError("model_run must match plan.model_run")
        require_digest(self.structured_response_digest, "structured_response_digest")
        if self.structured_response_digest != self.model_run.structured_response_digest:
            raise ValidationError("structured_response_digest must match model_run")
        object.__setattr__(
            self,
            "uncertainty_notes",
            _string_tuple(self.uncertainty_notes, "uncertainty_notes", sort=True),
        )

    def semantic_digest(self) -> str:
        return sha256_digest(
            {
                "plan": semantic_proof_plan_digest(self.plan),
                "uncertainty_notes": list(self.uncertainty_notes),
                "structured_response_digest": self.structured_response_digest,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "plan": self.plan.to_dict(),
            "model_run": self.model_run.to_dict(),
            "uncertainty_notes": list(self.uncertainty_notes),
            "structured_response_digest": self.structured_response_digest,
            "semantic_digest": self.semantic_digest(),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofPlanningResult:
        value = _closed_payload(
            payload,
            "ProofPlanningResult",
            {
                "schema",
                "plan",
                "model_run",
                "uncertainty_notes",
                "structured_response_digest",
                "semantic_digest",
            },
        )
        raw_plan = value.get("plan")
        raw_model_run = value.get("model_run")
        if not isinstance(raw_plan, Mapping) or not isinstance(raw_model_run, Mapping):
            raise ValidationError("planning result records must be objects")
        result = cls(
            schema=require_non_empty_string(value.get("schema"), "schema"),
            plan=ProofPlan.from_dict(raw_plan),
            model_run=ModelRunEvidence.from_dict(raw_model_run),
            uncertainty_notes=_string_tuple(
                value.get("uncertainty_notes"),
                "uncertainty_notes",
                sort=True,
            ),
            structured_response_digest=require_digest(
                value.get("structured_response_digest"),
                "structured_response_digest",
            ),
        )
        if require_digest(
            value.get("semantic_digest"), "semantic_digest"
        ) != result.semantic_digest() or result.to_dict() != dict(payload):
            raise ValidationError("ProofPlanningResult fields do not round-trip exactly")
        return result
