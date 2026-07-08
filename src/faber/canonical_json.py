"""Stable JSON serialization for audit and training data."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Convert common Python objects into deterministic JSON-compatible values."""

    if hasattr(value, "to_dict"):
        return to_jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible data with stable key ordering and compact separators."""

    return json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return UTF-8 bytes for canonical JSON."""

    return canonical_json(value).encode("utf-8")
