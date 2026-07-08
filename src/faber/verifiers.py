"""Verifier execution records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now


@dataclass(frozen=True)
class VerifierRun:
    """Evidence from an approved verifier run."""

    verifier_id: str
    name: str
    version: str
    command: list[str]
    passed: bool
    metrics: dict[str, object] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)
    logs_digest: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("verifier-run"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.verifier_run.v1"

    def verifier_spec(self) -> dict[str, object]:
        return {
            "verifier_id": self.verifier_id,
            "name": self.name,
            "version": self.version,
            "command": self.command,
        }

    def verifier_digest(self) -> str:
        return sha256_digest(self.verifier_spec())

    def result_digest(self) -> str:
        return sha256_digest(
            {
                "passed": self.passed,
                "metrics": self.metrics,
                "failure_reasons": self.failure_reasons,
                "logs_digest": self.logs_digest,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "verifier_id": self.verifier_id,
            "name": self.name,
            "version": self.version,
            "command": self.command,
            "passed": self.passed,
            "metrics": self.metrics,
            "failure_reasons": self.failure_reasons,
            "logs_digest": self.logs_digest,
            "metadata": self.metadata,
            "verifier_digest": self.verifier_digest(),
            "result_digest": self.result_digest(),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
