from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.reviews import (
    HumanReviewReceipt,
    MaintainerApproval,
    ReviewCriterion,
    ReviewFrictionSignal,
    attach_review_metadata,
    human_review_verification_receipt,
)
from faber.settlement import Settlement
from faber.templates import VerificationPolicy

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_human_review",
        created_at=CREATED_AT,
        title="Review task",
        description="Review product fit and maintainability.",
        requirements=["Pass maintainer review"],
        verifier_ids=["verifier.tests"],
    )


def _attempt() -> Attempt:
    return Attempt(
        id="attempt_human_review",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        worker_id="worker.reviewed",
        base_revision="base",
        candidate_revision="candidate",
        summary="Implemented reviewed change.",
        patch_digest=sha256_digest("patch"),
    )


def _review(*, private: bool = False) -> HumanReviewReceipt:
    return HumanReviewReceipt.from_comments(
        id="human-review-receipt_fixture",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        attempt_id=_attempt().id,
        reviewer_ref="maintainer:fixture",
        reviewer_relationship="repository_maintainer",
        outcome="approved",
        authority="authoritative",
        criteria=[
            ReviewCriterion(
                name="maintainability",
                outcome="passed",
                weight_milli=1000,
            )
        ],
        comments="Private detailed review text that must not enter core records.",
        comments_ref="private-review:fixture" if private else "review:fixture",
        friction=ReviewFrictionSignal(
            rounds=2,
            requested_changes=1,
            reviewer_minutes=20,
        ),
        private=private,
    )


def _hard_rejection() -> VerificationReceipt:
    return VerificationReceipt(
        id="verification-receipt_hard_reject",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        task_contract_digest=_contract().digest(),
        attempt_id=_attempt().id,
        worker_id=_attempt().worker_id,
        verifier_id="verifier.tests",
        verifier_digest=sha256_digest("tests"),
        base_revision="base",
        candidate_revision="candidate",
        accepted=False,
        metrics={"failures": 1},
        failure_reasons=["tests failed"],
        result_digest=sha256_digest("rejected"),
    )


def test_human_review_can_authorize_settlement_when_policy_permits() -> None:
    policy = VerificationPolicy(
        hard_verifier_ids=["verifier.tests"],
        human_review="authoritative",
    )
    receipt = human_review_verification_receipt(
        _review(),
        contract=_contract(),
        attempt=_attempt(),
        policy=policy,
    )
    settlement = Settlement.from_receipt(receipt, Money("EUR", 1_000))

    assert receipt.accepted is True
    assert receipt.verifier_id == "human-review:repository_maintainer"
    assert settlement.receipt_accepted is True


def test_human_review_cannot_override_hard_failure_when_policy_forbids() -> None:
    policy = VerificationPolicy(
        hard_verifier_ids=["verifier.tests"],
        human_review="authoritative",
        human_can_override_hard_failure=False,
    )

    with pytest.raises(ValidationError, match="cannot override rejected hard verifier"):
        human_review_verification_receipt(
            _review(),
            contract=_contract(),
            attempt=_attempt(),
            policy=policy,
            hard_receipt=_hard_rejection(),
        )


def test_review_friction_affects_trajectory_metadata() -> None:
    record = attach_review_metadata({"id": "trajectory_review"}, _review())

    assert record["review_metadata"]["outcome"] == "approved"
    assert record["review_metadata"]["friction"]["rounds"] == 2
    assert record["review_metadata"]["friction"]["requested_changes"] == 1


def test_comments_digest_and_maintainer_approval_are_stable() -> None:
    left = _review()
    right = _review()
    approval = MaintainerApproval.from_review(
        left,
        approval_id="maintainer-approval_fixture",
        created_at=CREATED_AT,
    )

    assert left.comments_digest == right.comments_digest
    assert left.digest() == right.digest()
    assert approval.review_receipt_digest == left.digest()


def test_private_review_text_is_not_leaked_into_public_export(tmp_path: Path) -> None:
    record = attach_review_metadata(
        {
            "schema": "faber.trajectory.v1",
            "id": "trajectory_private_review",
            "created_at": CREATED_AT,
        },
        _review(private=True),
        public=True,
    )
    out_path = tmp_path / "reviews.jsonl"

    export_trajectories_jsonl([record], out_path)
    exported = read_trajectory_jsonl(out_path)[0]

    assert "Private detailed review text" not in out_path.read_text(encoding="utf-8")
    assert exported["review_metadata"]["comments_ref"] is None
    assert exported["review_metadata"]["comments_digest"].startswith("sha256:")
