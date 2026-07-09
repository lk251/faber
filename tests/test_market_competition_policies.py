import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.market_policies import (
    AttemptPolicy,
    CandidatePool,
    ClaimPolicy,
    CompetitionPolicy,
    RetryPolicy,
    SelectionPolicy,
    ShadowAttemptPolicy,
)
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.selection import AdvisoryRankingRecord

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_competition",
        created_at=CREATED_AT,
        title="Competition task",
        description="Select a verified candidate.",
        requirements=["Pass verifier"],
        verifier_ids=["verifier.competition"],
    )


def _attempt(suffix: str) -> Attempt:
    return Attempt(
        id=f"attempt_{suffix}",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        worker_id=f"worker_{suffix}",
        base_revision="base",
        candidate_revision=f"candidate-{suffix}",
        summary=f"Candidate {suffix}",
        patch_digest=sha256_digest(f"patch:{suffix}"),
    )


def _receipt(attempt: Attempt, *, accepted: bool = True) -> VerificationReceipt:
    return VerificationReceipt(
        id=f"verification-receipt_{attempt.id}",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        task_contract_digest=_contract().digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id="verifier.competition",
        verifier_digest=sha256_digest("verifier"),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics={"tests": 1},
        failure_reasons=[] if accepted else ["failed"],
        result_digest=sha256_digest({"accepted": accepted, "attempt": attempt.id}),
    )


def _pool(*, claim_mode: str, competition_mode: str, cap: int = 1_000) -> CandidatePool:
    return CandidatePool(
        contract=_contract(),
        attempt_policy=AttemptPolicy(max_active_attempts=4),
        claim_policy=ClaimPolicy(mode=claim_mode),
        competition_policy=CompetitionPolicy(
            mode=competition_mode,
            max_candidates=4,
            pay_winner_only=True,
        ),
        retry_policy=RetryPolicy(max_retries_per_worker=1),
        shadow_attempt_policy=ShadowAttemptPolicy(enabled=True, settlement_allowed=False),
        selection_policy=SelectionPolicy(
            verifier_budget_cap=Money("EUR", cap),
            authoritative_acceptance_required=True,
        ),
        pool_id=f"candidate-pool_{claim_mode}_{competition_mode}",
        created_at=CREATED_AT,
    )


def test_exclusive_claim_rejects_second_active_claimant() -> None:
    pool = _pool(claim_mode="exclusive", competition_mode="single_claim")
    pool.claim("worker_a", idempotency_key="claim-a")

    with pytest.raises(ValidationError, match="exclusive claim is already active"):
        pool.claim("worker_b", idempotency_key="claim-b")


def test_open_competition_allows_multiple_attempts() -> None:
    pool = _pool(claim_mode="open", competition_mode="open_competition")
    pool.claim("worker_a", idempotency_key="claim-a")
    pool.claim("worker_b", idempotency_key="claim-b")

    pool.submit(_attempt("a"), verifier_cost=Money("EUR", 100), training_consent=True)
    pool.submit(_attempt("b"), verifier_cost=Money("EUR", 100), training_consent=True)

    assert [entry.attempt.id for entry in pool.entries()] == ["attempt_a", "attempt_b"]


def test_best_of_n_records_rejected_alternatives() -> None:
    pool = _pool(claim_mode="open", competition_mode="best_of_n")
    attempts = [_attempt("a"), _attempt("b"), _attempt("c")]
    for attempt in attempts:
        pool.submit(attempt, verifier_cost=Money("EUR", 100), training_consent=True)
    rankings = [
        AdvisoryRankingRecord(
            id=f"ranking_{attempt.id}",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            score_milli=score,
            uncertainty_milli=10,
            scorer_id="fake-ranker",
        )
        for attempt, score in zip(attempts, [800, 900, 700], strict=True)
    ]

    selection = pool.select(
        advisory_rankings=rankings,
        receipts=[_receipt(attempts[1], accepted=True)],
    )

    assert selection.selected_attempt_id == "attempt_b"
    assert {item["attempt_id"] for item in selection.rejected_alternatives} == {
        "attempt_a",
        "attempt_c",
    }
    assert {record["attempt_id"] for record in pool.training_records()} == {
        "attempt_a",
        "attempt_b",
        "attempt_c",
    }


def test_budget_cap_limits_verifier_spend() -> None:
    pool = _pool(claim_mode="open", competition_mode="open_competition", cap=150)
    pool.submit(_attempt("a"), verifier_cost=Money("EUR", 100), training_consent=True)

    with pytest.raises(ValidationError, match="verifier budget cap"):
        pool.submit(_attempt("b"), verifier_cost=Money("EUR", 100), training_consent=True)


def test_shadow_attempt_is_training_only_and_cannot_settle() -> None:
    pool = _pool(claim_mode="open", competition_mode="open_competition")
    shadow = _attempt("shadow")
    pool.submit(
        shadow,
        verifier_cost=Money("EUR", 100),
        training_consent=True,
        shadow=True,
    )
    pool.select(receipts=[_receipt(shadow, accepted=True)])

    assert pool.training_records()[0]["shadow"] is True
    with pytest.raises(SettlementError, match="shadow attempt policy"):
        pool.require_settlement_eligible(shadow.id, _receipt(shadow, accepted=True))
