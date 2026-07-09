import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.money import Money
from faber.probabilistic import (
    CriterionSpec,
    DeterministicFakeScoringBackend,
    ScoreBudget,
    ScoreCache,
    ScoreRequest,
    pairwise_preference,
    probabilistic_verification_receipt,
    score_with_repetitions,
)
from faber.templates import VerificationPolicy

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_probabilistic",
        created_at=CREATED_AT,
        title="Probabilistic scoring task",
        description="Score a candidate before hard verification.",
        requirements=["Pass hard verification"],
        verifier_ids=["verifier.hard"],
    )


def _attempt(suffix: str = "a") -> Attempt:
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


def _request(suffix: str = "a") -> ScoreRequest:
    return ScoreRequest(
        task_contract_id=_contract().id,
        attempt_id=_attempt(suffix).id,
        candidate_digest=_attempt(suffix).patch_digest,
        criteria=[
            CriterionSpec(name="correctness", weight_milli=700),
            CriterionSpec(name="maintainability", weight_milli=300),
        ],
        scoring_policy="fixture-policy",
        scoring_policy_version="1",
    )


def test_fake_scorer_emits_stable_scores() -> None:
    backend = DeterministicFakeScoringBackend(cost_per_evaluation=Money("EUR", 5))

    left = score_with_repetitions(
        backend,
        _request(),
        repetitions=3,
        result_id="probabilistic-score_stable",
        created_at=CREATED_AT,
    )
    right = score_with_repetitions(
        backend,
        _request(),
        repetitions=3,
        result_id="probabilistic-score_stable",
        created_at=CREATED_AT,
    )

    assert left.to_dict() == right.to_dict()
    assert left.digest() == right.digest()


def test_repeated_evaluation_aggregates_deterministically() -> None:
    backend = DeterministicFakeScoringBackend(cost_per_evaluation=Money("EUR", 7))
    budget = ScoreBudget(Money("EUR", 21))

    result = score_with_repetitions(
        backend,
        _request(),
        repetitions=3,
        budget=budget,
        result_id="probabilistic-score_repeated",
        created_at=CREATED_AT,
    )

    assert len(result.repetition_scores_milli) == 3
    assert result.aggregate_score_milli == sum(result.repetition_scores_milli) // 3
    assert result.cost == Money("EUR", 21)
    assert budget.remaining_minor_units == 0


def test_criteria_decomposition_and_pairwise_preference_are_represented() -> None:
    backend = DeterministicFakeScoringBackend(cost_per_evaluation=Money("EUR", 5))
    left = score_with_repetitions(
        backend,
        _request("a"),
        repetitions=2,
        result_id="probabilistic-score_a",
        created_at=CREATED_AT,
    )
    right = score_with_repetitions(
        backend,
        _request("b"),
        repetitions=2,
        result_id="probabilistic-score_b",
        created_at=CREATED_AT,
    )
    preference = pairwise_preference(
        left,
        right,
        preference_id="pairwise-preference_fixture",
        created_at=CREATED_AT,
    )

    assert {score.criterion_name for score in left.criterion_scores} == {
        "correctness",
        "maintainability",
    }
    assert preference.preferred_attempt_id in {"attempt_a", "attempt_b"}
    assert preference.authority == "ranking"


def test_advisory_score_cannot_release_settlement_authority() -> None:
    result = score_with_repetitions(
        DeterministicFakeScoringBackend(cost_per_evaluation=Money("EUR", 5)),
        _request(),
        repetitions=1,
        result_id="probabilistic-score_advisory",
        created_at=CREATED_AT,
    )
    policy = VerificationPolicy(hard_verifier_ids=["verifier.hard"])

    with pytest.raises(ValidationError, match="not explicitly authoritative"):
        probabilistic_verification_receipt(
            result,
            contract=_contract(),
            attempt=_attempt(),
            policy=policy,
        )


def test_score_cache_is_keyed_by_stable_digests() -> None:
    backend = DeterministicFakeScoringBackend(cost_per_evaluation=Money("EUR", 5))
    cache = ScoreCache()

    left = score_with_repetitions(
        backend,
        _request(),
        repetitions=2,
        cache=cache,
        result_id="probabilistic-score_cache",
        created_at=CREATED_AT,
    )
    calls_after_first = backend.call_count
    right = score_with_repetitions(
        backend,
        _request(),
        repetitions=2,
        cache=cache,
        result_id="probabilistic-score_cache",
        created_at=CREATED_AT,
    )

    assert backend.call_count == calls_after_first
    assert left.digest() == right.digest()
    assert cache.keys()[0].startswith("sha256:")
