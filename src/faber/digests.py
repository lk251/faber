"""Digest helpers for canonical protocol data."""

from __future__ import annotations

import hashlib
from typing import Any

from faber.canonical_json import canonical_json_bytes


def sha256_digest(value: Any) -> str:
    """Return a digest string formatted as sha256:<hex>."""

    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = canonical_json_bytes(value)
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
