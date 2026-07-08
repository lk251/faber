"""Market event records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now


@dataclass(frozen=True)
class MarketEvent:
    """Generic market event for audit and future training exports."""

    event_type: str
    subject_id: str
    actor_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("market-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.market_event.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "event_type": self.event_type,
            "subject_id": self.subject_id,
            "actor_id": self.actor_id,
            "payload": self.payload,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
