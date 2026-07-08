"""Task contract primitives."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)


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
    schema: str = schemas.TASK_CONTRACT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TASK_CONTRACT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.title, "title")
        require_non_empty_string(self.description, "description")
        require_string_list(self.requirements, "requirements", allow_empty=False)
        require_string_list(self.verifier_ids, "verifier_ids", allow_empty=False)
        require_non_empty_string(self.task_source, "task_source")
        if self.repository is not None:
            require_non_empty_string(self.repository, "repository")
        require_mapping(self.environment, "environment")

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
