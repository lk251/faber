"""Worker profile records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now


@dataclass(frozen=True)
class WorkerProfile:
    """Portable worker capability and reputation record."""

    display_name: str
    capabilities: list[str]
    reputation: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("worker"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.worker_profile.v1"

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
