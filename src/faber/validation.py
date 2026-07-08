"""Small validation helpers for Faber Protocol objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from faber.errors import ProtocolVersionError, ValidationError


def require_non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value


def require_schema(value: object, expected: str, field: str = "schema") -> str:
    schema = require_non_empty_string(value, field)
    if schema != expected:
        raise ProtocolVersionError(f"{field} must be {expected!r}, got {schema!r}")
    return schema


def require_digest(value: object, field: str) -> str:
    digest = require_non_empty_string(value, field)
    prefix = "sha256:"
    if not digest.startswith(prefix):
        raise ValidationError(f"{field} must start with 'sha256:'")
    hex_part = digest.removeprefix(prefix)
    if len(hex_part) != 64:
        raise ValidationError(f"{field} must contain a 64-character SHA-256 hex digest")
    try:
        int(hex_part, 16)
    except ValueError as exc:
        raise ValidationError(f"{field} must contain a lowercase hexadecimal digest") from exc
    if hex_part.lower() != hex_part:
        raise ValidationError(f"{field} must contain a lowercase hexadecimal digest")
    return digest


def require_optional_digest(value: object, field: str) -> str | None:
    if value is None:
        return None
    return require_digest(value, field)


def require_string_list(value: object, field: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list of strings")
    if not allow_empty and not value:
        raise ValidationError(f"{field} must contain at least one string")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{field}[{index}] must be a non-empty string")
    return value


def require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise ValidationError(f"{field} keys must be strings")
    return value


def require_sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError(f"{field} must be a sequence")
    return value
