"""Local JSON/filesystem task source and submission adapters."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.sources import ArtifactReference, ExternalTaskReference
from faber.validation import require_mapping, require_non_empty_string, require_string_list


class LocalJsonTaskSource:
    adapter_name = "local.json"

    def load(self, reference: ExternalTaskReference) -> TaskContract:
        path = Path(reference.locator)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValidationError(f"task JSON could not be loaded: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValidationError("task JSON root must be a mapping")
        return _contract_from_payload(payload, reference, task_source=self.adapter_name)


class LocalFilesystemTaskSource:
    adapter_name = "local.filesystem"

    def load(self, reference: ExternalTaskReference) -> TaskContract:
        task_path = Path(reference.locator) / "task.json"
        json_reference = replace(reference, locator=str(task_path))
        contract = LocalJsonTaskSource().load(json_reference)
        return replace(contract, task_source=self.adapter_name)


class LocalFilesystemSubmissionAdapter:
    adapter_name = "local.filesystem"

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
        require_non_empty_string(worker_id, "worker_id")
        require_non_empty_string(base_revision, "base_revision")
        require_non_empty_string(summary, "summary")
        artifact_list = list(artifacts)
        if not artifact_list:
            raise ValidationError("artifacts must contain at least one ArtifactReference")
        if any(not isinstance(artifact, ArtifactReference) for artifact in artifact_list):
            raise ValidationError("artifacts must contain ArtifactReference records")
        artifact_payloads = [artifact.to_dict() for artifact in artifact_list]
        content_payloads = [artifact.stable_content() for artifact in artifact_list]
        attempt_metadata: dict[str, object] = {
            "submission_adapter": self.adapter_name,
            "artifacts": artifact_payloads,
        }
        if metadata is not None:
            attempt_metadata.update(dict(require_mapping(metadata, "metadata")))
        candidate_digest = sha256_digest(content_payloads)
        return Attempt(
            id=attempt_id or new_id("attempt"),
            created_at=created_at or utc_now(),
            task_contract_id=contract.id,
            worker_id=worker_id,
            base_revision=base_revision,
            candidate_revision=candidate_digest,
            summary=summary,
            patch_digest=sha256_digest(artifact_payloads),
            metadata=attempt_metadata,
        )


def artifact_reference_from_path(
    path: str | Path,
    *,
    kind: str,
    media_type: str | None = None,
    artifact_id: str | None = None,
) -> ArtifactReference:
    artifact_path = Path(path)
    try:
        content = artifact_path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"artifact could not be read: {artifact_path}: {exc}") from exc
    return ArtifactReference(
        id=artifact_id or f"artifact-reference_{sha256_digest(str(artifact_path))[-16:]}",
        kind=kind,
        locator=str(artifact_path),
        digest=sha256_digest(content),
        media_type=media_type,
        metadata={"size_bytes": len(content)},
    )


def _contract_from_payload(
    payload: dict[str, object],
    reference: ExternalTaskReference,
    *,
    task_source: str,
) -> TaskContract:
    reward_payload = payload.get("reward")
    reward: Money | None = None
    if reward_payload is not None:
        if not isinstance(reward_payload, Mapping):
            raise ValidationError("reward must be a mapping or null")
        currency = require_non_empty_string(reward_payload.get("currency"), "reward.currency")
        minor_units = reward_payload.get("minor_units")
        if not isinstance(minor_units, int) or isinstance(minor_units, bool):
            raise ValidationError("reward.minor_units must be an integer")
        reward = Money(currency, minor_units)
    payload_digest = sha256_digest(payload)
    contract_id = payload.get("id")
    if contract_id is None:
        contract_id = f"task-contract_local_{payload_digest[-16:]}"
    created_at = payload.get("created_at", "1970-01-01T00:00:00Z")
    repository = payload.get("repository")
    if repository is not None and not isinstance(repository, str):
        raise ValidationError("repository must be a string or null")
    return TaskContract(
        id=require_non_empty_string(contract_id, "id"),
        created_at=require_non_empty_string(created_at, "created_at"),
        title=require_non_empty_string(payload.get("title"), "title"),
        description=require_non_empty_string(payload.get("description"), "description"),
        requirements=require_string_list(
            payload.get("requirements"), "requirements", allow_empty=False
        ),
        verifier_ids=require_string_list(
            payload.get("verifier_ids"), "verifier_ids", allow_empty=False
        ),
        task_source=task_source,
        repository=repository,
        environment=dict(require_mapping(payload.get("environment", {}), "environment")),
        trajectory_requirement=dict(
            require_mapping(
                payload.get("trajectory_requirement", {}),
                "trajectory_requirement",
            )
        ),
        source_reference=reference.to_dict(),
        reward=reward,
    )
