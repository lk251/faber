"""Verification receipt records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.validation import (
    ValidationError,
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_sequence,
    require_string_list,
)
from faber.verifiers import VerifierRun


@dataclass(frozen=True)
class VerificationReceipt:
    """Authoritative binding between a task, attempt, worker, verifier, and result."""

    task_contract_id: str
    task_contract_digest: str
    attempt_id: str
    worker_id: str
    verifier_id: str
    verifier_digest: str
    base_revision: str
    candidate_revision: str
    accepted: bool
    metrics: dict[str, object]
    failure_reasons: list[str]
    result_digest: str
    id: str = field(default_factory=lambda: new_id("verification-receipt"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.VERIFICATION_RECEIPT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.VERIFICATION_RECEIPT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_digest(self.task_contract_digest, "task_contract_digest")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_non_empty_string(self.worker_id, "worker_id")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_digest(self.verifier_digest, "verifier_digest")
        require_non_empty_string(self.base_revision, "base_revision")
        require_non_empty_string(self.candidate_revision, "candidate_revision")
        require_mapping(self.metrics, "metrics")
        require_sequence(self.failure_reasons, "failure_reasons")
        require_digest(self.result_digest, "result_digest")

    @classmethod
    def from_verifier_run(
        cls,
        contract: TaskContract,
        attempt: Attempt,
        verifier_run: VerifierRun,
    ) -> VerificationReceipt:
        if attempt.task_contract_id != contract.id:
            raise ValidationError(
                "attempt.task_contract_id must match the task contract used for receipt creation"
            )
        return cls(
            task_contract_id=contract.id,
            task_contract_digest=contract.digest(),
            attempt_id=attempt.id,
            worker_id=attempt.worker_id,
            verifier_id=verifier_run.verifier_id,
            verifier_digest=verifier_run.verifier_digest(),
            base_revision=attempt.base_revision,
            candidate_revision=attempt.candidate_revision,
            accepted=verifier_run.passed,
            metrics=verifier_run.metrics,
            failure_reasons=verifier_run.failure_reasons,
            result_digest=verifier_run.result_digest(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "attempt_id": self.attempt_id,
            "worker_id": self.worker_id,
            "verifier_id": self.verifier_id,
            "verifier_digest": self.verifier_digest,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "accepted": self.accepted,
            "metrics": self.metrics,
            "failure_reasons": self.failure_reasons,
            "result_digest": self.result_digest,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> VerificationReceipt:
        fields = {
            "schema",
            "id",
            "created_at",
            "task_contract_id",
            "task_contract_digest",
            "attempt_id",
            "worker_id",
            "verifier_id",
            "verifier_digest",
            "base_revision",
            "candidate_revision",
            "accepted",
            "metrics",
            "failure_reasons",
            "result_digest",
        }
        if set(payload) != fields:
            raise ValidationError("VerificationReceipt must use the exact supported field set")
        accepted = payload.get("accepted")
        if not isinstance(accepted, bool):
            raise ValidationError("accepted must be a boolean")
        receipt = cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            id=require_non_empty_string(payload.get("id"), "id"),
            created_at=require_non_empty_string(payload.get("created_at"), "created_at"),
            task_contract_id=require_non_empty_string(
                payload.get("task_contract_id"), "task_contract_id"
            ),
            task_contract_digest=require_digest(
                payload.get("task_contract_digest"), "task_contract_digest"
            ),
            attempt_id=require_non_empty_string(payload.get("attempt_id"), "attempt_id"),
            worker_id=require_non_empty_string(payload.get("worker_id"), "worker_id"),
            verifier_id=require_non_empty_string(payload.get("verifier_id"), "verifier_id"),
            verifier_digest=require_digest(payload.get("verifier_digest"), "verifier_digest"),
            base_revision=require_non_empty_string(payload.get("base_revision"), "base_revision"),
            candidate_revision=require_non_empty_string(
                payload.get("candidate_revision"), "candidate_revision"
            ),
            accepted=accepted,
            metrics=dict(require_mapping(payload.get("metrics"), "metrics")),
            failure_reasons=list(
                require_string_list(payload.get("failure_reasons"), "failure_reasons")
            ),
            result_digest=require_digest(payload.get("result_digest"), "result_digest"),
        )
        if receipt.to_dict() != dict(payload):
            raise ValidationError("VerificationReceipt fields do not round-trip exactly")
        return receipt
