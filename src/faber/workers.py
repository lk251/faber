"""Worker profile records."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

if TYPE_CHECKING:
    from faber.trajectories import Trajectory


@dataclass(frozen=True)
class WorkerProfile:
    """Portable worker capability and reputation record."""

    display_name: str
    capabilities: list[str]
    owner_ref: str | None = None
    supported_task_sources: list[str] = field(default_factory=list)
    supported_languages: list[str] = field(default_factory=list)
    cost_model: Money | None = None
    availability_status: str = "available"
    reputation: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("worker"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.WORKER_PROFILE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.WORKER_PROFILE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.display_name, "display_name")
        require_string_list(self.capabilities, "capabilities")
        if self.owner_ref is not None:
            require_non_empty_string(self.owner_ref, "owner_ref")
        require_string_list(self.supported_task_sources, "supported_task_sources")
        require_string_list(self.supported_languages, "supported_languages")
        require_non_empty_string(self.availability_status, "availability_status")
        require_mapping(self.reputation, "reputation")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "capabilities": self.capabilities,
            "owner_ref": self.owner_ref,
            "supported_task_sources": self.supported_task_sources,
            "supported_languages": self.supported_languages,
            "cost_model": self.cost_model.to_dict() if self.cost_model else None,
            "availability_status": self.availability_status,
            "reputation": self.reputation,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class WorkerRegistry:
    """In-memory registry of available workers."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerProfile] = {}

    def register(self, worker: WorkerProfile) -> WorkerProfile:
        existing = self._workers.get(worker.id)
        if existing is not None and existing.digest() != worker.digest():
            raise ValidationError(f"worker {worker.id!r} is already registered differently")
        self._workers[worker.id] = worker
        return worker

    def resolve(self, worker_id: str) -> WorkerProfile:
        require_non_empty_string(worker_id, "worker_id")
        try:
            return self._workers[worker_id]
        except KeyError as exc:
            raise ValidationError(f"worker {worker_id!r} is not registered") from exc

    def list_workers(self) -> list[WorkerProfile]:
        return [self._workers[key] for key in sorted(self._workers)]


def update_reputation_from_trajectory(
    worker: WorkerProfile,
    trajectory: Trajectory,
) -> WorkerProfile:
    """Return a worker profile with reputation updated from a verified trajectory."""

    reputation = dict(worker.reputation)
    accepted = _int_value(reputation.get("accepted_attempts", 0))
    rejected = _int_value(reputation.get("rejected_attempts", 0))
    verifier_failures = _int_value(reputation.get("verifier_failures", 0))
    if trajectory.receipt.accepted:
        accepted += 1
    else:
        rejected += 1
        verifier_failures += 1
    reputation["accepted_attempts"] = accepted
    reputation["rejected_attempts"] = rejected
    reputation["verifier_failures"] = verifier_failures
    reputation["last_outcome"] = trajectory.outcome()
    reputation["total_latency_seconds"] = _int_value(
        reputation.get("total_latency_seconds", 0)
    ) + _int_value(trajectory.latency_metadata.get("work_seconds", 0))
    cost_units = _int_value(trajectory.cost_metadata.get("compute_minor_units", 0)) + _int_value(
        trajectory.cost_metadata.get("review_minor_units", 0)
    )
    reputation["total_cost_minor_units"] = (
        _int_value(reputation.get("total_cost_minor_units", 0)) + cost_units
    )
    if trajectory.review_metadata.get("review_friction") not in (None, "none", "low"):
        reputation["review_friction_count"] = (
            _int_value(reputation.get("review_friction_count", 0)) + 1
        )
    return replace(worker, reputation=reputation)


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0
