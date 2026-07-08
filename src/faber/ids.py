"""Identifier and clock helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_id(prefix: str) -> str:
    """Create a readable opaque identifier with a stable prefix."""

    normalized = prefix.strip().lower().replace("_", "-")
    if not normalized:
        raise ValueError("id prefix is required")
    return f"{normalized}_{uuid.uuid4().hex}"


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with second precision."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
