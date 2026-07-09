"""Generic task-source, submission, and artifact adapter contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_schema,
)

ARTIFACT_KINDS = {"patch", "commit", "file", "generated_output", "non_code"}


@dataclass(frozen=True)
class ArtifactReference:
    """Digest-bound reference to code or non-code submitted work."""

    kind: str
    locator: str
    digest: str
    media_type: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("artifact-reference"))
    schema: str = schemas.ARTIFACT_REFERENCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ARTIFACT_REFERENCE)
        require_non_empty_string(self.id, "id")
        if self.kind not in ARTIFACT_KINDS:
            raise ValidationError(f"kind must be one of {sorted(ARTIFACT_KINDS)}")
        require_non_empty_string(self.locator, "locator")
        require_digest(self.digest, "digest")
        if self.media_type is not None:
            require_non_empty_string(self.media_type, "media_type")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "kind": self.kind,
            "locator": self.locator,
            "digest": self.digest,
            "media_type": self.media_type,
            "metadata": self.metadata,
        }

    def stable_content(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "locator": self.locator,
            "digest": self.digest,
            "media_type": self.media_type,
            "metadata": self.metadata,
        }

    def digest_record(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class ExternalTaskReference:
    """Provider-neutral reference to a task outside the protocol record."""

    source: str
    external_id: str
    locator: str
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("external-task-reference"))
    schema: str = schemas.EXTERNAL_TASK_REFERENCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.EXTERNAL_TASK_REFERENCE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.source, "source")
        require_non_empty_string(self.external_id, "external_id")
        require_non_empty_string(self.locator, "locator")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "locator": self.locator,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class TaskSourceAdapter(Protocol):
    adapter_name: str

    def load(self, reference: ExternalTaskReference) -> TaskContract:
        """Load an external reference as an ordinary task contract."""


class SubmissionAdapter(Protocol):
    adapter_name: str

    def submit(
        self,
        contract: TaskContract,
        *,
        worker_id: str,
        base_revision: str,
        summary: str,
        artifacts: Sequence[ArtifactReference],
        attempt_id: str | None = None,
        created_at: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Attempt:
        """Submit referenced artifacts as an ordinary attempt."""
