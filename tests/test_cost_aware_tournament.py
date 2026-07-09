from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.tournaments import (
    TournamentPolicy,
    run_candidate_tournament,
    tournament_dataset_records,
)

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_tournament",
        created_at=CREATED_AT,
        title="Candidate tournament",
        description="Choose under a verifier budget.",
        requirements=["Pass authoritative verifier"],
        verifier_ids=["verifier.tournament"],
    )


def _attempt(index: int) -> Attempt:
    return Attempt(
        id=f"attempt_{index}",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        worker_id=f"worker_{index}",
        base_revision="base",
        candidate_revision=f"candidate-{index}",
        summary=f"Candidate {index}",
        patch_digest=sha256_digest(f"patch:{index}"),
    )


def _receipt(attempt: Attempt, *, accepted: bool) -> VerificationReceipt:
    return VerificationReceipt(
        id=f"verification-receipt_{attempt.id}",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        task_contract_digest=_contract().digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id="verifier.tournament",
        verifier_digest=sha256_digest("hard verifier"),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics={"tests": 1},
        failure_reasons=[] if accepted else ["failed"],
        result_digest=sha256_digest({"attempt": attempt.id, "accepted": accepted}),
    )


def _policy(*, cap: int = 1_000) -> TournamentPolicy:
    return TournamentPolicy(
        full_round_robin_max_candidates=4,
        verifier_budget=Money("EUR", cap),
        comparison_cost=Money("EUR", 10),
        comparison_latency_ms=25,
    )


def test_small_pool_uses_full_round_robin() -> None:
    result = run_candidate_tournament(
        contract=_contract(),
        attempts=[_attempt(index) for index in range(3)],
        policy=_policy(),
        result_id="tournament-result_small",
        created_at=CREATED_AT,
    )

    assert result.schedule == "full_round_robin"
    assert result.comparison_count == 3
    assert result.verifier_cost == Money("EUR", 30)


def test_large_pool_uses_reduced_pivot_comparison() -> None:
    result = run_candidate_tournament(
        contract=_contract(),
        attempts=[_attempt(index) for index in range(6)],
        policy=_policy(),
        result_id="tournament-result_large",
        created_at=CREATED_AT,
    )

    assert result.schedule == "pivot"
    assert result.comparison_count == 5
    assert result.comparison_count < 15


def test_budget_cap_stops_comparisons() -> None:
    result = run_candidate_tournament(
        contract=_contract(),
        attempts=[_attempt(index) for index in range(5)],
        policy=_policy(cap=20),
        result_id="tournament-result_capped",
        created_at=CREATED_AT,
    )

    assert result.comparison_count == 2
    assert result.budget_exhausted is True
    assert result.verifier_cost.minor_units == 20


def test_hard_accepted_candidate_wins() -> None:
    attempts = [_attempt(index) for index in range(3)]
    advisory = run_candidate_tournament(
        contract=_contract(),
        attempts=attempts,
        policy=_policy(),
        result_id="tournament-result_advisory",
        created_at=CREATED_AT,
    )
    hard_winner = next(
        attempt for attempt in attempts if attempt.id != advisory.selected_attempt_id
    )

    authoritative = run_candidate_tournament(
        contract=_contract(),
        attempts=attempts,
        policy=_policy(),
        receipts=[_receipt(hard_winner, accepted=True)],
        result_id="tournament-result_authoritative",
        created_at=CREATED_AT,
    )

    assert authoritative.selected_attempt_id == hard_winner.id
    assert authoritative.selection_reason == "hard_authoritative_accept"


def test_rejected_alternatives_export_into_dataset_records() -> None:
    attempts = [_attempt(index) for index in range(3)]
    result = run_candidate_tournament(
        contract=_contract(),
        attempts=attempts,
        policy=_policy(),
        result_id="tournament-result_dataset",
        created_at=CREATED_AT,
    )
    records = [{"attempt_id": attempt.id} for attempt in attempts]

    annotated = tournament_dataset_records(records, result)

    assert sum(record["tournament_outcome"] == "rejected" for record in annotated) == 2
    assert {item["attempt_id"] for item in result.rejected_alternatives} == {
        attempt.id for attempt in attempts if attempt.id != result.selected_attempt_id
    }


def test_tournament_result_digest_is_stable() -> None:
    attempts = [_attempt(index) for index in range(5)]
    left = run_candidate_tournament(
        contract=_contract(),
        attempts=attempts,
        policy=_policy(),
        result_id="tournament-result_stable",
        created_at=CREATED_AT,
    )
    right = run_candidate_tournament(
        contract=_contract(),
        attempts=attempts,
        policy=_policy(),
        result_id="tournament-result_stable",
        created_at=CREATED_AT,
    )

    assert left.to_dict() == right.to_dict()
    assert left.digest() == right.digest()
