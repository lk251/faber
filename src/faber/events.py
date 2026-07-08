"""Market event records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.validation import require_mapping, require_non_empty_string, require_schema


@dataclass(frozen=True)
class MarketEvent:
    """Generic market event for audit and future training exports."""

    event_type: str
    subject_id: str
    actor_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("market-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.MARKET_EVENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.MARKET_EVENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.event_type, "event_type")
        require_non_empty_string(self.subject_id, "subject_id")
        if self.actor_id is not None:
            require_non_empty_string(self.actor_id, "actor_id")
        require_mapping(self.payload, "payload")

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
