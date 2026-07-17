"""Strict catalog-derived Structured Outputs schema for proof planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from faber.adapters.openai.prompt import RESPONSE_SCHEMA_VERSION
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_planning import PlannerCatalogEntryView

MAX_OPENAI_SCHEMA_OBJECT_DEPTH = 10
MAX_OPENAI_SCHEMA_PROPERTIES = 5_000
MAX_OPENAI_SCHEMA_ENUM_VALUES = 1_000
MAX_OPENAI_SCHEMA_STRING_BYTES = 120_000
MAX_LARGE_ENUM_STRING_BYTES = 15_000
_UNSUPPORTED_OBJECT_KEYWORDS = {"minProperties", "maxProperties"}


def _validate_supported_schema_keywords(value: Mapping[str, object], field: str) -> None:
    unsupported = sorted(set(value) & _UNSUPPORTED_OBJECT_KEYWORDS)
    if unsupported:
        raise ValidationError(
            f"{field} uses Structured Outputs keywords not supported by this adapter: {unsupported}"
        )
    if value.get("type") == "object":
        properties = value.get("properties")
        if not isinstance(properties, Mapping):
            raise AssertionError("validated object schema must contain properties")
        for key, nested in properties.items():
            if not isinstance(nested, Mapping):
                raise AssertionError("validated property schema must be an object")
            _validate_supported_schema_keywords(nested, f"{field}.properties.{key}")
    elif value.get("type") == "array":
        items = value.get("items")
        if not isinstance(items, Mapping):
            raise AssertionError("validated array schema must contain items")
        _validate_supported_schema_keywords(items, f"{field}.items")


def _validate_openai_schema_limits(schema: Mapping[str, object]) -> None:
    property_count = 0
    enum_count = 0
    string_bytes = 0
    maximum_depth = 0

    def visit(value: object, object_depth: int) -> None:
        nonlocal property_count, enum_count, string_bytes, maximum_depth
        if isinstance(value, Mapping):
            current_depth = object_depth + (1 if value.get("type") == "object" else 0)
            maximum_depth = max(maximum_depth, current_depth)
            properties = value.get("properties")
            if isinstance(properties, Mapping):
                property_count += len(properties)
            enum = value.get("enum")
            if isinstance(enum, list):
                enum_count += len(enum)
                if len(enum) > 250:
                    enum_string_bytes = sum(
                        len(item.encode("utf-8")) for item in enum if isinstance(item, str)
                    )
                    if enum_string_bytes > MAX_LARGE_ENUM_STRING_BYTES:
                        raise ValidationError(
                            "structured response schema exceeds OpenAI's large-enum string limit"
                        )
            for key, item in value.items():
                string_bytes += len(str(key).encode("utf-8"))
                visit(item, current_depth)
        elif isinstance(value, list):
            for item in value:
                visit(item, object_depth)
        elif isinstance(value, str):
            string_bytes += len(value.encode("utf-8"))

    visit(schema, 0)
    if maximum_depth > MAX_OPENAI_SCHEMA_OBJECT_DEPTH:
        raise ValidationError("structured response schema exceeds OpenAI's object-depth limit")
    if property_count > MAX_OPENAI_SCHEMA_PROPERTIES:
        raise ValidationError("structured response schema exceeds OpenAI's property limit")
    if enum_count > MAX_OPENAI_SCHEMA_ENUM_VALUES:
        raise ValidationError("structured response schema exceeds OpenAI's enum-value limit")
    if string_bytes > MAX_OPENAI_SCHEMA_STRING_BYTES:
        raise ValidationError("structured response schema exceeds OpenAI's schema-string limit")


def structured_response_schema(
    catalog_entries: Sequence[PlannerCatalogEntryView],
) -> dict[str, object]:
    """Build a strict schema whose selection branches expose only approved templates."""

    entries = sorted(catalog_entries, key=lambda entry: (entry.id, entry.version))
    if not entries:
        raise ValidationError("catalog_entries must contain at least one planning view")

    selection_branches: list[dict[str, object]] = []
    for entry in entries:
        parameter_schema = entry.parameter_schema_dict()
        _validate_supported_schema_keywords(parameter_schema, "parameter_schema")
        selection_branches.append(
            {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "template_id": {"type": "string", "enum": [entry.id]},
                    "template_version": {
                        "type": "string",
                        "enum": [entry.version],
                    },
                    "parameters": parameter_schema,
                    "expected_behavior": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "claim_id",
                    "template_id",
                    "template_version",
                    "parameters",
                    "expected_behavior",
                    "rationale",
                ],
                "additionalProperties": False,
            }
        )

    schema = {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "enum": [RESPONSE_SCHEMA_VERSION]},
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "statement": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "requirement_refs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "evidence_required": {
                            "type": "boolean",
                            "enum": [True],
                        },
                        "risk_rationale": {"type": ["string", "null"]},
                    },
                    "required": [
                        "id",
                        "statement",
                        "severity",
                        "requirement_refs",
                        "evidence_required",
                        "risk_rationale",
                    ],
                    "additionalProperties": False,
                },
            },
            "selections": {
                "type": "array",
                "items": {"anyOf": selection_branches},
            },
            "uncovered_claim_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "human_review_recommended": {"type": "boolean"},
            "uncertainty_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "schema",
            "claims",
            "selections",
            "uncovered_claim_ids",
            "human_review_recommended",
            "uncertainty_notes",
        ],
        "additionalProperties": False,
    }
    _validate_openai_schema_limits(schema)
    return schema


def structured_response_schema_digest(
    catalog_entries: Sequence[PlannerCatalogEntryView],
) -> str:
    """Bind replay and request records to the exact generated response schema."""

    return sha256_digest(structured_response_schema(catalog_entries))
