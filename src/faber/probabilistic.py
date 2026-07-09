"""Provider-neutral probabilistic verifier interfaces and deterministic fakes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.templates import VerificationPolicy
from faber.validation import (
    require_digest,
    require_non_empty_string,
)


@dataclass(frozen=True)
class CriterionSpec:
    name: str
    weight_milli: int
    description: str = ""

    def __post_init__(self) -> None:
        require_non_empty_string(self.name, "name")
        _require_milli(self.weight_milli, "weight_milli")
        if not isinstance(self.description, str):
            raise ValidationError("description must be a string")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "weight_milli": self.weight_milli,
            "description": self.description,
        }


@dataclass(frozen=True)
class ScoreRequest:
    task_contract_id: str
    attempt_id: str
    candidate_digest: str
    criteria: list[CriterionSpec]
    scoring_policy: str
    scoring_policy_version: str

    def __post_init__(self) -> None:
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_digest(self.candidate_digest, "candidate_digest")
        if not self.criteria or any(
            not isinstance(criterion, CriterionSpec) for criterion in self.criteria
        ):
            raise ValidationError("criteria must contain CriterionSpec records")
        if sum(criterion.weight_milli for criterion in self.criteria) != 1000:
            raise ValidationError("criteria weights must sum to 1000")
        require_non_empty_string(self.scoring_policy, "scoring_policy")
        require_non_empty_string(self.scoring_policy_version, "scoring_policy_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "task_contract_id": self.task_contract_id,
            "attempt_id": self.attempt_id,
            "candidate_digest": self.candidate_digest,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "scoring_policy": self.scoring_policy,
            "scoring_policy_version": self.scoring_policy_version,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class ScoreSample:
    criterion_scores_milli: dict[str, int]
    latency_ms: int


class ScoringBackend(Protocol):
    backend_id: str
    backend_version: str
    cost_per_evaluation: Money

    def score(self, request: ScoreRequest, repetition: int) -> ScoreSample:
        """Return one local/provider-adapter score sample."""

    def spec_digest(self) -> str:
        """Return a stable backend configuration digest."""


@dataclass
class DeterministicFakeScoringBackend:
    cost_per_evaluation: Money
    latency_ms: int = 10
    backend_id: str = "fake-deterministic-scorer"
    backend_version: str = "1"
    call_count: int = field(default=0, init=False)

    def score(self, request: ScoreRequest, repetition: int) -> ScoreSample:
        if repetition < 0:
            raise ValidationError("repetition must be non-negative")
        self.call_count += 1
        scores: dict[str, int] = {}
        for criterion in request.criteria:
            digest = sha256_digest(
                {
                    "backend": self.backend_id,
                    "version": self.backend_version,
                    "request": request.digest(),
                    "criterion": criterion.name,
                    "repetition": repetition,
                }
            ).removeprefix("sha256:")
            scores[criterion.name] = 400 + int(digest[:8], 16) % 601
        return ScoreSample(criterion_scores_milli=scores, latency_ms=self.latency_ms)

    def spec_digest(self) -> str:
        return sha256_digest(
            {
                "backend_id": self.backend_id,
                "backend_version": self.backend_version,
                "cost_per_evaluation": self.cost_per_evaluation.to_dict(),
                "latency_ms": self.latency_ms,
            }
        )


@dataclass(frozen=True)
class CriterionScore:
    criterion_name: str
    repetition_scores_milli: list[int]
    aggregate_score_milli: int

    def to_dict(self) -> dict[str, object]:
        return {
            "criterion_name": self.criterion_name,
            "repetition_scores_milli": self.repetition_scores_milli,
            "aggregate_score_milli": self.aggregate_score_milli,
        }


@dataclass(frozen=True)
class ProbabilisticScoreResult:
    request: ScoreRequest
    backend_id: str
    backend_version: str
    backend_spec_digest: str
    repetitions: int
    criterion_scores: list[CriterionScore]
    repetition_scores_milli: list[int]
    aggregate_score_milli: int
    uncertainty_milli: int
    cost: Money
    latency_ms: int
    authority: str = "advisory"
    id: str = field(default_factory=lambda: new_id("probabilistic-score"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.PROBABILISTIC_SCORE

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "request": self.request.to_dict(),
            "request_digest": self.request.digest(),
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "backend_spec_digest": self.backend_spec_digest,
            "repetitions": self.repetitions,
            "criterion_scores": [score.to_dict() for score in self.criterion_scores],
            "repetition_scores_milli": self.repetition_scores_milli,
            "aggregate_score_milli": self.aggregate_score_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "cost": self.cost.to_dict(),
            "latency_ms": self.latency_ms,
            "authority": self.authority,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class PairwisePreference:
    left_attempt_id: str
    right_attempt_id: str
    preferred_attempt_id: str
    preference_probability_milli: int
    uncertainty_milli: int
    authority: str = "ranking"
    id: str = field(default_factory=lambda: new_id("pairwise-preference"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.PAIRWISE_PREFERENCE

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "left_attempt_id": self.left_attempt_id,
            "right_attempt_id": self.right_attempt_id,
            "preferred_attempt_id": self.preferred_attempt_id,
            "preference_probability_milli": self.preference_probability_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "authority": self.authority,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class ProgressScore:
    attempt_id: str
    prefix_index: int
    prefix_digest: str
    score_milli: int
    uncertainty_milli: int
    authority: str = "progress"

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "prefix_index": self.prefix_index,
            "prefix_digest": self.prefix_digest,
            "score_milli": self.score_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "authority": self.authority,
        }


class ScoreBudget:
    def __init__(self, cap: Money) -> None:
        self.cap = cap
        self.spent_minor_units = 0

    @property
    def remaining_minor_units(self) -> int:
        return self.cap.minor_units - self.spent_minor_units

    def charge(self, amount: Money) -> None:
        if amount.currency != self.cap.currency:
            raise ValidationError("score budget currency mismatch")
        if amount.minor_units > self.remaining_minor_units:
            raise ValidationError("score budget cap exceeded")
        self.spent_minor_units += amount.minor_units


class ScoreCache:
    def __init__(self) -> None:
        self._results: dict[str, ProbabilisticScoreResult] = {}

    def get(self, key: str) -> ProbabilisticScoreResult | None:
        return self._results.get(key)

    def put(self, key: str, result: ProbabilisticScoreResult) -> None:
        self._results[key] = result

    def keys(self) -> list[str]:
        return sorted(self._results)


def score_with_repetitions(
    backend: ScoringBackend,
    request: ScoreRequest,
    *,
    repetitions: int,
    budget: ScoreBudget | None = None,
    cache: ScoreCache | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
) -> ProbabilisticScoreResult:
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions <= 0:
        raise ValidationError("repetitions must be a positive integer")
    cache_key = sha256_digest(
        {
            "request_digest": request.digest(),
            "backend_spec_digest": backend.spec_digest(),
            "repetitions": repetitions,
        }
    )
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    total_cost = Money(
        backend.cost_per_evaluation.currency,
        backend.cost_per_evaluation.minor_units * repetitions,
    )
    if budget is not None:
        budget.charge(total_cost)
    samples = [backend.score(request, repetition) for repetition in range(repetitions)]
    criterion_scores: list[CriterionScore] = []
    for criterion in request.criteria:
        values = [sample.criterion_scores_milli[criterion.name] for sample in samples]
        criterion_scores.append(
            CriterionScore(
                criterion_name=criterion.name,
                repetition_scores_milli=values,
                aggregate_score_milli=sum(values) // len(values),
            )
        )
    repetition_scores = [
        sum(
            sample.criterion_scores_milli[criterion.name] * criterion.weight_milli
            for criterion in request.criteria
        )
        // 1000
        for sample in samples
    ]
    result = ProbabilisticScoreResult(
        id=result_id or new_id("probabilistic-score"),
        created_at=created_at or utc_now(),
        request=request,
        backend_id=backend.backend_id,
        backend_version=backend.backend_version,
        backend_spec_digest=backend.spec_digest(),
        repetitions=repetitions,
        criterion_scores=criterion_scores,
        repetition_scores_milli=repetition_scores,
        aggregate_score_milli=sum(repetition_scores) // repetitions,
        uncertainty_milli=max(repetition_scores) - min(repetition_scores),
        cost=total_cost,
        latency_ms=sum(sample.latency_ms for sample in samples),
    )
    if cache is not None:
        cache.put(cache_key, result)
    return result


def pairwise_preference(
    left: ProbabilisticScoreResult,
    right: ProbabilisticScoreResult,
    *,
    preference_id: str | None = None,
    created_at: str | None = None,
) -> PairwisePreference:
    difference = left.aggregate_score_milli - right.aggregate_score_milli
    preferred = (
        left.request.attempt_id if difference >= 0 else right.request.attempt_id
    )
    probability = min(1000, 500 + abs(difference) // 2)
    return PairwisePreference(
        id=preference_id or new_id("pairwise-preference"),
        created_at=created_at or utc_now(),
        left_attempt_id=left.request.attempt_id,
        right_attempt_id=right.request.attempt_id,
        preferred_attempt_id=preferred,
        preference_probability_milli=probability,
        uncertainty_milli=max(left.uncertainty_milli, right.uncertainty_milli),
    )


def score_progress_prefixes(
    backend: ScoringBackend,
    request: ScoreRequest,
    prefix_digests: list[str],
) -> list[ProgressScore]:
    scores: list[ProgressScore] = []
    for index, prefix_digest in enumerate(prefix_digests):
        require_digest(prefix_digest, f"prefix_digests[{index}]")
        prefix_request = ScoreRequest(
            task_contract_id=request.task_contract_id,
            attempt_id=request.attempt_id,
            candidate_digest=prefix_digest,
            criteria=request.criteria,
            scoring_policy=request.scoring_policy,
            scoring_policy_version=request.scoring_policy_version,
        )
        result = score_with_repetitions(backend, prefix_request, repetitions=1)
        scores.append(
            ProgressScore(
                attempt_id=request.attempt_id,
                prefix_index=index,
                prefix_digest=prefix_digest,
                score_milli=result.aggregate_score_milli,
                uncertainty_milli=result.uncertainty_milli,
            )
        )
    return scores


def probabilistic_verification_receipt(
    result: ProbabilisticScoreResult,
    *,
    contract: TaskContract,
    attempt: Attempt,
    policy: VerificationPolicy,
    acceptance_threshold_milli: int = 500,
) -> VerificationReceipt:
    if result.backend_id not in policy.authoritative_probabilistic_verifier_ids:
        raise ValidationError("probabilistic verifier is not explicitly authoritative")
    if result.request.task_contract_id != contract.id or result.request.attempt_id != attempt.id:
        raise ValidationError("probabilistic score must bind the contract and attempt")
    _require_milli(acceptance_threshold_milli, "acceptance_threshold_milli")
    accepted = result.aggregate_score_milli >= acceptance_threshold_milli
    return VerificationReceipt(
        id=f"verification-receipt_{result.id}",
        created_at=result.created_at,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id=result.backend_id,
        verifier_digest=result.backend_spec_digest,
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics={
            "probabilistic_score_milli": result.aggregate_score_milli,
            "uncertainty_milli": result.uncertainty_milli,
            "repetitions": result.repetitions,
            "authority": "authoritative_by_task_policy",
        },
        failure_reasons=[] if accepted else ["score below task acceptance threshold"],
        result_digest=result.digest(),
    )


def _require_milli(value: int, field_name: str) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > 1000
    ):
        raise ValidationError(f"{field_name} must be an integer from 0 to 1000")
