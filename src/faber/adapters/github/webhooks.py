"""Webhook parsing skeleton without network or framework dependencies."""

from __future__ import annotations

import hmac
from hashlib import sha256

from faber.adapters.github.events import GitHubEvent, normalize_github_event


def verify_github_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """Verify a GitHub sha256 HMAC signature header."""

    if not isinstance(secret, str):
        raise TypeError("secret must be a string")
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    if not isinstance(signature_header, str):
        raise TypeError("signature_header must be a string")
    if not signature_header.startswith("sha256="):
        return False
    supplied_digest = signature_header.removeprefix("sha256=")
    if len(supplied_digest) != 64:
        return False
    try:
        int(supplied_digest, 16)
    except ValueError:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_event(
    event_name: str,
    payload: dict[str, object],
    *,
    delivery_id: str | None = None,
) -> GitHubEvent:
    return normalize_github_event(event_name, payload, delivery_id=delivery_id)
