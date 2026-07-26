"""First-class human review evidence and policy-gated maintainer approval."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.receipts import VerificationReceipt
from faber.templates import VerificationPolicy
from faber.validation import (
    require_digest,
    require_non_empty_string,
    require_schema,
)

REVIEW_OUTCOMES = {"approved", "rejected", "changes_requested", "abstained"}
CRITERION_OUTCOMES = {"passed", "failed", "not_applicable", "uncertain"}
REVIEW_AUTHORITIES = {"advisory", "supplementary", "authoritative"}


class ReviewOutcome:
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ABSTAINED = "abstained"


@dataclass(frozen=True)
class ReviewCriterion:
    name: str
    outcome: str
    weight_milli: int
    evidence_digest: str | None = None
    schema: str = schemas.REVIEW_CRITERION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.REVIEW_CRITERION)
        require_non_empty_string(self.name, "name")
        if self.outcome not in CRITERION_OUTCOMES:
            raise ValidationError(f"criterion outcome must be one of {sorted(CRITERION_OUTCOMES)}")
        if (
            not isinstance(self.weight_milli, int)
            or isinstance(self.weight_milli, bool)
            or self.weight_milli < 0
            or self.weight_milli > 1000
        ):
            raise ValidationError("weight_milli must be an integer from 0 to 1000")
        if self.evidence_digest is not None:
            require_digest(self.evidence_digest, "evidence_digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "name": self.name,
            "outcome": self.outcome,
            "weight_milli": self.weight_milli,
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True)
class ReviewFrictionSignal:
    rounds: int
    requested_changes: int
    reviewer_minutes: int
    comment_count: int = 0
    schema: str = schemas.REVIEW_FRICTION_SIGNAL

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.REVIEW_FRICTION_SIGNAL)
        for field_name, value in [
            ("rounds", self.rounds),
            ("requested_changes", self.requested_changes),
            ("reviewer_minutes", self.reviewer_minutes),
            ("comment_count", self.comment_count),
        ]:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValidationError(f"{field_name} must be a non-negative integer")

    @property
    def level(self) -> str:
        if self.requested_changes == 0 and self.rounds <= 1:
            return "low"
        if self.requested_changes <= 2 and self.rounds <= 3:
            return "moderate"
        return "high"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "rounds": self.rounds,
            "requested_changes": self.requested_changes,
            "reviewer_minutes": self.reviewer_minutes,
            "comment_count": self.comment_count,
            "level": self.level,
        }


@dataclass(frozen=True)
class HumanReviewReceipt:
    task_contract_id: str
    attempt_id: str
    reviewer_ref: str
    reviewer_relationship: str
    outcome: str
    authority: str
    criteria: list[ReviewCriterion]
    comments_digest: str
    comments_ref: str | None
    friction: ReviewFrictionSignal
    private: bool = False
    id: str = field(default_factory=lambda: new_id("human-review-receipt"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.HUMAN_REVIEW_RECEIPT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.HUMAN_REVIEW_RECEIPT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_non_empty_string(self.reviewer_ref, "reviewer_ref")
        require_non_empty_string(self.reviewer_relationship, "reviewer_relationship")
        if self.outcome not in REVIEW_OUTCOMES:
            raise ValidationError(f"outcome must be one of {sorted(REVIEW_OUTCOMES)}")
        if self.authority not in REVIEW_AUTHORITIES:
            raise ValidationError(f"authority must be one of {sorted(REVIEW_AUTHORITIES)}")
        if any(not isinstance(criterion, ReviewCriterion) for criterion in self.criteria):
            raise ValidationError("criteria must contain ReviewCriterion records")
        require_digest(self.comments_digest, "comments_digest")
        if self.comments_ref is not None:
            require_non_empty_string(self.comments_ref, "comments_ref")
        if not isinstance(self.friction, ReviewFrictionSignal):
            raise ValidationError("friction must be a ReviewFrictionSignal")
        if not isinstance(self.private, bool):
            raise ValidationError("private must be a boolean")

    @classmethod
    def from_comments(
        cls,
        *,
        task_contract_id: str,
        attempt_id: str,
        reviewer_ref: str,
        reviewer_relationship: str,
        outcome: str,
        authority: str,
        criteria: list[ReviewCriterion],
        comments: str,
        comments_ref: str | None,
        friction: ReviewFrictionSignal,
        private: bool = False,
        id: str | None = None,
        created_at: str | None = None,
    ) -> HumanReviewReceipt:
        if not isinstance(comments, str):
            raise ValidationError("comments must be a string")
        return cls(
            id=id or new_id("human-review-receipt"),
            created_at=created_at or utc_now(),
            task_contract_id=task_contract_id,
            attempt_id=attempt_id,
            reviewer_ref=reviewer_ref,
            reviewer_relationship=reviewer_relationship,
            outcome=outcome,
            authority=authority,
            criteria=criteria,
            comments_digest=sha256_digest(comments),
            comments_ref=comments_ref,
            friction=friction,
            private=private,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "attempt_id": self.attempt_id,
            "reviewer_ref": self.reviewer_ref,
            "reviewer_relationship": self.reviewer_relationship,
            "outcome": self.outcome,
            "authority": self.authority,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "comments_digest": self.comments_digest,
            "comments_ref": self.comments_ref,
            "friction": self.friction.to_dict(),
            "private": self.private,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class MaintainerApproval:
    review_receipt_id: str
    review_receipt_digest: str
    reviewer_relationship: str
    id: str = field(default_factory=lambda: new_id("maintainer-approval"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.MAINTAINER_APPROVAL

    @classmethod
    def from_review(
        cls,
        review: HumanReviewReceipt,
        *,
        approval_id: str | None = None,
        created_at: str | None = None,
    ) -> MaintainerApproval:
        if review.outcome != ReviewOutcome.APPROVED:
            raise ValidationError("maintainer approval requires an approved review")
        return cls(
            id=approval_id or new_id("maintainer-approval"),
            created_at=created_at or utc_now(),
            review_receipt_id=review.id,
            review_receipt_digest=review.digest(),
            reviewer_relationship=review.reviewer_relationship,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "review_receipt_id": self.review_receipt_id,
            "review_receipt_digest": self.review_receipt_digest,
            "reviewer_relationship": self.reviewer_relationship,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def human_review_verification_receipt(
    review: HumanReviewReceipt,
    *,
    contract: TaskContract,
    attempt: Attempt,
    policy: VerificationPolicy,
    hard_receipt: VerificationReceipt | None = None,
) -> VerificationReceipt:
    """Convert authorized human review into a normal authoritative receipt."""

    if review.task_contract_id != contract.id or review.attempt_id != attempt.id:
        raise ValidationError("human review must bind the contract and attempt")
    if attempt.task_contract_id != contract.id:
        raise ValidationError("attempt must belong to contract")
    if policy.human_review != "authoritative" or review.authority != "authoritative":
        raise ValidationError("task policy does not authorize human review for acceptance")
    if review.outcome != ReviewOutcome.APPROVED:
        raise ValidationError("authoritative human acceptance requires approved outcome")
    if (
        hard_receipt is not None
        and not hard_receipt.accepted
        and not policy.human_can_override_hard_failure
    ):
        raise ValidationError("human review cannot override rejected hard verifier")
    verifier_id = f"human-review:{review.reviewer_relationship}"
    return VerificationReceipt(
        id=f"verification-receipt_{review.id}",
        created_at=review.created_at,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id=verifier_id,
        verifier_digest=sha256_digest(
            {
                "verifier_id": verifier_id,
                "policy": policy.to_dict(),
                "review_receipt_digest": review.digest(),
            }
        ),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=True,
        metrics={
            "review_outcome": review.outcome,
            "review_authority": review.authority,
            "review_friction": review.friction.to_dict(),
            "criterion_count": len(review.criteria),
        },
        failure_reasons=[],
        result_digest=review.digest(),
    )


def attach_review_metadata(
    trajectory: dict[str, object],
    review: HumanReviewReceipt,
    *,
    public: bool = False,
) -> dict[str, object]:
    """Attach export-safe review outcome and friction without review prose."""

    record = copy.deepcopy(trajectory)
    record["review_metadata"] = {
        "review_receipt_id": review.id,
        "review_receipt_digest": review.digest(),
        "outcome": review.outcome,
        "authority": review.authority,
        "reviewer_relationship": review.reviewer_relationship,
        "comments_digest": review.comments_digest,
        "comments_ref": None if public and review.private else review.comments_ref,
        "friction": review.friction.to_dict(),
        "private": review.private,
    }
    return record
