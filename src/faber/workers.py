"""Worker profile records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)


@dataclass(frozen=True)
class WorkerProfile:
    """Portable worker capability and reputation record."""

    display_name: str
    capabilities: list[str]
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
        require_mapping(self.reputation, "reputation")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "capabilities": self.capabilities,
            "reputation": self.reputation,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
