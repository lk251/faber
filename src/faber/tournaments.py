"""Deterministic cost-aware candidate tournaments."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from itertools import combinations

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.validation import require_schema


@dataclass(frozen=True)
class TournamentPolicy:
    full_round_robin_max_candidates: int
    verifier_budget: Money
    comparison_cost: Money
    comparison_latency_ms: int
    pivot_count: int = 1
    schema: str = schemas.TOURNAMENT_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TOURNAMENT_POLICY)
        _require_positive_int(
            self.full_round_robin_max_candidates,
            "full_round_robin_max_candidates",
        )
        _require_positive_int(self.pivot_count, "pivot_count")
        _require_non_negative_int(self.comparison_latency_ms, "comparison_latency_ms")
        if not isinstance(self.verifier_budget, Money):
            raise ValidationError("verifier_budget must be Money")
        if not isinstance(self.comparison_cost, Money):
            raise ValidationError("comparison_cost must be Money")
        if self.verifier_budget.currency != self.comparison_cost.currency:
            raise ValidationError("comparison cost currency must match verifier budget")
        if self.comparison_cost.minor_units <= 0:
            raise ValidationError("comparison_cost must be positive")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "full_round_robin_max_candidates": self.full_round_robin_max_candidates,
            "verifier_budget": self.verifier_budget.to_dict(),
            "comparison_cost": self.comparison_cost.to_dict(),
            "comparison_latency_ms": self.comparison_latency_ms,
            "pivot_count": self.pivot_count,
        }


@dataclass(frozen=True)
class CandidateComparison:
    left_attempt_id: str
    right_attempt_id: str
    preferred_attempt_id: str
    preference_probability_milli: int
    uncertainty_milli: int
    verifier_cost: Money
    latency_ms: int
    sequence: int
    id: str
    schema: str = schemas.CANDIDATE_COMPARISON

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "sequence": self.sequence,
            "left_attempt_id": self.left_attempt_id,
            "right_attempt_id": self.right_attempt_id,
            "preferred_attempt_id": self.preferred_attempt_id,
            "preference_probability_milli": self.preference_probability_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "verifier_cost": self.verifier_cost.to_dict(),
            "latency_ms": self.latency_ms,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class TournamentResult:
    task_contract_id: str
    candidate_attempt_ids: list[str]
    selected_attempt_id: str
    rejected_alternatives: list[dict[str, object]]
    comparisons: list[CandidateComparison]
    schedule: str
    verifier_cost: Money
    latency_ms: int
    uncertainty_milli: int
    selection_reason: str
    budget_exhausted: bool
    authoritative_receipt_id: str | None = None
    id: str = field(default_factory=lambda: new_id("tournament-result"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TOURNAMENT_RESULT

    @property
    def comparison_count(self) -> int:
        return len(self.comparisons)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "candidate_attempt_ids": self.candidate_attempt_ids,
            "selected_attempt_id": self.selected_attempt_id,
            "rejected_alternatives": self.rejected_alternatives,
            "comparisons": [comparison.to_dict() for comparison in self.comparisons],
            "comparison_count": self.comparison_count,
            "schedule": self.schedule,
            "verifier_cost": self.verifier_cost.to_dict(),
            "latency_ms": self.latency_ms,
            "uncertainty_milli": self.uncertainty_milli,
            "selection_reason": self.selection_reason,
            "budget_exhausted": self.budget_exhausted,
            "authoritative_receipt_id": self.authoritative_receipt_id,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def run_candidate_tournament(
    *,
    contract: TaskContract,
    attempts: list[Attempt],
    policy: TournamentPolicy,
    receipts: list[VerificationReceipt] | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
) -> TournamentResult:
    if not attempts:
        raise ValidationError("attempts must contain at least one candidate")
    attempt_ids = {attempt.id for attempt in attempts}
    if len(attempt_ids) != len(attempts):
        raise ValidationError("attempt ids must be unique")
    if any(attempt.task_contract_id != contract.id for attempt in attempts):
        raise ValidationError("attempt task_contract_id must match contract")
    receipt_records = receipts or []
    if any(
        receipt.task_contract_id != contract.id or receipt.attempt_id not in attempt_ids
        for receipt in receipt_records
    ):
        raise ValidationError("receipt must reference a tournament candidate")
    schedule = (
        "full_round_robin"
        if len(attempts) <= policy.full_round_robin_max_candidates
        else "pivot"
    )
    scheduled_pairs = _comparison_pairs(attempts, policy, schedule)
    comparisons: list[CandidateComparison] = []
    spent = 0
    for left, right in scheduled_pairs:
        if spent + policy.comparison_cost.minor_units > policy.verifier_budget.minor_units:
            break
        comparison = _compare(
            left,
            right,
            policy,
            sequence=len(comparisons),
            result_id=result_id or "tournament",
        )
        comparisons.append(comparison)
        spent += policy.comparison_cost.minor_units
    win_mass = {attempt.id: 0 for attempt in attempts}
    for comparison in comparisons:
        win_mass[comparison.preferred_attempt_id] += comparison.preference_probability_milli
    accepted_receipts = [receipt for receipt in receipt_records if receipt.accepted]
    if accepted_receipts:
        selected_receipt = sorted(
            accepted_receipts,
            key=lambda receipt: (-win_mass[receipt.attempt_id], receipt.attempt_id),
        )[0]
        selected_attempt_id = selected_receipt.attempt_id
        reason = "hard_authoritative_accept"
        receipt_id = selected_receipt.id
    else:
        selected_attempt_id = sorted(
            attempts,
            key=lambda attempt: (-win_mass[attempt.id], attempt.id),
        )[0].id
        reason = "advisory_tournament"
        receipt_id = None
    receipts_by_attempt = {receipt.attempt_id: receipt for receipt in receipt_records}
    rejected = []
    for attempt in attempts:
        if attempt.id == selected_attempt_id:
            continue
        receipt = receipts_by_attempt.get(attempt.id)
        if receipt is not None and not receipt.accepted:
            rejection_reason = "hard_rejected"
        elif receipt_id is not None:
            rejection_reason = "authoritative_acceptance_dominated"
        else:
            rejection_reason = "lower_tournament_win_mass"
        rejected.append(
            {
                "attempt_id": attempt.id,
                "reason": rejection_reason,
                "win_mass_milli": win_mass[attempt.id],
                "receipt_id": receipt.id if receipt else None,
                "receipt_accepted": receipt.accepted if receipt else None,
            }
        )
    uncertainty = (
        sum(comparison.uncertainty_milli for comparison in comparisons)
        // len(comparisons)
        if comparisons
        else 1000
    )
    return TournamentResult(
        id=result_id or new_id("tournament-result"),
        created_at=created_at or utc_now(),
        task_contract_id=contract.id,
        candidate_attempt_ids=[attempt.id for attempt in attempts],
        selected_attempt_id=selected_attempt_id,
        rejected_alternatives=rejected,
        comparisons=comparisons,
        schedule=schedule,
        verifier_cost=Money(policy.verifier_budget.currency, spent),
        latency_ms=sum(comparison.latency_ms for comparison in comparisons),
        uncertainty_milli=uncertainty,
        selection_reason=reason,
        budget_exhausted=len(comparisons) < len(scheduled_pairs),
        authoritative_receipt_id=receipt_id,
    )


def tournament_dataset_records(
    records: list[dict[str, object]],
    result: TournamentResult,
) -> list[dict[str, object]]:
    annotated: list[dict[str, object]] = []
    result_payload = result.to_dict()
    for record in records:
        next_record = copy.deepcopy(record)
        attempt_id = _record_attempt_id(next_record)
        if attempt_id in result.candidate_attempt_ids:
            next_record["candidate_tournament"] = result_payload
            next_record["tournament_outcome"] = (
                "selected" if attempt_id == result.selected_attempt_id else "rejected"
            )
        annotated.append(next_record)
    return annotated


def _comparison_pairs(
    attempts: list[Attempt],
    policy: TournamentPolicy,
    schedule: str,
) -> list[tuple[Attempt, Attempt]]:
    if schedule == "full_round_robin":
        return list(combinations(attempts, 2))
    pivots = attempts[: min(policy.pivot_count, len(attempts) - 1)]
    pairs: list[tuple[Attempt, Attempt]] = []
    seen: set[tuple[str, str]] = set()
    for pivot in pivots:
        for candidate in attempts:
            if candidate.id == pivot.id:
                continue
            key = (
                (pivot.id, candidate.id)
                if pivot.id < candidate.id
                else (candidate.id, pivot.id)
            )
            if key in seen:
                continue
            seen.add(key)
            pairs.append((pivot, candidate))
    return pairs


def _compare(
    left: Attempt,
    right: Attempt,
    policy: TournamentPolicy,
    *,
    sequence: int,
    result_id: str,
) -> CandidateComparison:
    left_value = int(left.patch_digest.removeprefix("sha256:")[:8], 16) % 1001
    right_value = int(right.patch_digest.removeprefix("sha256:")[:8], 16) % 1001
    preferred = left.id if left_value >= right_value else right.id
    probability = min(1000, 500 + abs(left_value - right_value) // 2)
    return CandidateComparison(
        id=f"candidate-comparison_{sha256_digest([result_id, left.id, right.id])[-16:]}",
        sequence=sequence,
        left_attempt_id=left.id,
        right_attempt_id=right.id,
        preferred_attempt_id=preferred,
        preference_probability_milli=probability,
        uncertainty_milli=1000 - probability,
        verifier_cost=policy.comparison_cost,
        latency_ms=policy.comparison_latency_ms,
    )


def _record_attempt_id(record: dict[str, object]) -> str | None:
    attempt = record.get("attempt")
    if isinstance(attempt, dict) and isinstance(attempt.get("id"), str):
        return str(attempt["id"])
    attempt_id = record.get("attempt_id")
    return attempt_id if isinstance(attempt_id, str) else None


def _require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")
