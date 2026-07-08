"""Task contract primitives."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money


@dataclass(frozen=True)
class TaskContract:
    """A verifier-first description of work to be attempted."""

    title: str
    description: str
    requirements: list[str]
    verifier_ids: list[str]
    task_source: str = "generic"
    repository: str | None = None
    environment: dict[str, object] = field(default_factory=dict)
    reward: Money | None = None
    id: str = field(default_factory=lambda: new_id("task-contract"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.task_contract.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "title": self.title,
            "description": self.description,
            "requirements": self.requirements,
            "verifier_ids": self.verifier_ids,
            "task_source": self.task_source,
            "repository": self.repository,
            "environment": self.environment,
            "reward": self.reward.to_dict() if self.reward else None,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
