"""Market event records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from faber import schemas
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.validation import require_mapping, require_non_empty_string, require_schema


class DigestibleRecord(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def schema(self) -> str: ...

    def digest(self) -> str: ...


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


def lifecycle_event(
    event_type: str,
    subject: DigestibleRecord,
    *,
    actor_id: str | None = None,
    payload: dict[str, object] | None = None,
) -> MarketEvent:
    event_payload: dict[str, object] = {
        "record_schema": subject.schema,
        "record_digest": subject.digest(),
    }
    if payload:
        event_payload.update(payload)
    return MarketEvent(
        event_type=event_type,
        subject_id=subject.id,
        actor_id=actor_id,
        payload=event_payload,
    )


def contract_created(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("contract.created", subject)


def attempt_submitted(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("attempt.submitted", subject)


def verifier_run_recorded(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("verifier_run.recorded", subject)


def receipt_issued(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("receipt.issued", subject)


def trajectory_exported(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("trajectory.exported", subject)


def settlement_created(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("settlement.created", subject)


def settlement_paid(subject: DigestibleRecord) -> MarketEvent:
    return lifecycle_event("settlement.paid", subject)


def settlement_failed(subject: DigestibleRecord, reason: str) -> MarketEvent:
    return lifecycle_event("settlement.failed", subject, payload={"reason": reason})
