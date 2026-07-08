"""Webhook parsing skeleton without network or framework dependencies."""

from __future__ import annotations


def parse_event(event_name: str, payload: dict[str, object]) -> dict[str, object]:
    if not event_name:
        raise ValueError("GitHub event name is required")
    return {
        "source": "github",
        "event_name": event_name,
        "payload": payload,
    }
