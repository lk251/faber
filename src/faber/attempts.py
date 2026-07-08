"""Attempt records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now


@dataclass(frozen=True)
class Attempt:
    """Worker output against a task contract and base revision."""

    task_contract_id: str
    worker_id: str
    base_revision: str
    candidate_revision: str
    summary: str
    patch_digest: str
    tool_summaries: list[dict[str, object]] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("attempt"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.attempt.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "worker_id": self.worker_id,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "summary": self.summary,
            "patch_digest": self.patch_digest,
            "tool_summaries": self.tool_summaries,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
