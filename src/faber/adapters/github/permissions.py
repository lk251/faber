"""Minimal intended GitHub App permission model."""

from __future__ import annotations

READ_PERMISSIONS: dict[str, str] = {
    "issues": "read",
    "pull_requests": "read",
    "contents": "read",
    "metadata": "read",
    "checks": "read",
}

WRITE_PERMISSIONS: dict[str, str] = {
    "checks": "write",
    "statuses": "write",
    "issues": "write",
}


def minimal_permissions() -> dict[str, dict[str, str]]:
    return {
        "read": READ_PERMISSIONS,
        "write_when_needed": WRITE_PERMISSIONS,
    }
