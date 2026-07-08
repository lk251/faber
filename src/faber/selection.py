"""Best-of-N candidate selection records."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass, field

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_sequence,
    require_string_list,
)

MAX_SCORE_MILLI = 1000


@dataclass(frozen=True)
class AdvisoryRankingRecord:
    """Deterministic advisory score for one candidate attempt."""

    attempt_id: str
    score_milli: int
    uncertainty_milli: int
    scorer_id: str
    rationale: str = ""
    id: str = field(default_factory=lambda: new_id("advisory-ranking"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ADVISORY_RANKING

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ADVISORY_RANKING)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_score_milli(self.score_milli, "score_milli")
        require_score_milli(self.uncertainty_milli, "uncertainty_milli")
        require_non_empty_string(self.scorer_id, "scorer_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "attempt_id": self.attempt_id,
            "score_milli": self.score_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "scorer_id": self.scorer_id,
            "rationale": self.rationale,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class CandidateSelectionRecord:
    """Auditable best-of-N selection result."""

    task_contract_id: str
    candidate_attempt_ids: list[str]
    selected_attempt_id: str
    rejected_alternatives: list[dict[str, object]]
    advisory_rankings: list[AdvisoryRankingRecord]
    budget_used: Money
    selection_reason: str
    uncertainty_milli: int
    authoritative_receipt_id: str | None = None
    policy_name: str = "hard-authoritative-then-advisory"
    policy_version: str = "1"
    id: str = field(default_factory=lambda: new_id("candidate-selection"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.CANDIDATE_SELECTION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.CANDIDATE_SELECTION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_string_list(self.candidate_attempt_ids, "candidate_attempt_ids", allow_empty=False)
        require_non_empty_string(self.selected_attempt_id, "selected_attempt_id")
        if self.selected_attempt_id not in self.candidate_attempt_ids:
            raise ValidationError("selected_attempt_id must be one of candidate_attempt_ids")
        require_sequence(self.rejected_alternatives, "rejected_alternatives")
        for index, rejected in enumerate(self.rejected_alternatives):
            require_mapping(rejected, f"rejected_alternatives[{index}]")
        for index, ranking in enumerate(self.advisory_rankings):
            if not isinstance(ranking, AdvisoryRankingRecord):
                raise ValidationError(
                    f"advisory_rankings[{index}] must be an AdvisoryRankingRecord"
                )
        require_non_empty_string(self.selection_reason, "selection_reason")
        require_score_milli(self.uncertainty_milli, "uncertainty_milli")
        if self.authoritative_receipt_id is not None:
            require_non_empty_string(self.authoritative_receipt_id, "authoritative_receipt_id")
        require_non_empty_string(self.policy_name, "policy_name")
        require_non_empty_string(self.policy_version, "policy_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "candidate_attempt_ids": self.candidate_attempt_ids,
            "selected_attempt_id": self.selected_attempt_id,
            "rejected_alternatives": self.rejected_alternatives,
            "advisory_rankings": [ranking.to_dict() for ranking in self.advisory_rankings],
            "budget_used": self.budget_used.to_dict(),
            "selection_reason": self.selection_reason,
            "uncertainty_milli": self.uncertainty_milli,
            "authoritative_receipt_id": self.authoritative_receipt_id,
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def select_best_attempt(
    *,
    contract: TaskContract,
    attempts: list[Attempt],
    advisory_rankings: list[AdvisoryRankingRecord] | None = None,
    receipts: list[VerificationReceipt] | None = None,
    budget_used: Money | None = None,
    selection_id: str | None = None,
    created_at: str | None = None,
) -> CandidateSelectionRecord:
    """Select a candidate using hard receipts first, then advisory ranking."""

    if not attempts:
        raise ValidationError("attempts must contain at least one candidate")
    rankings = advisory_rankings or []
    receipt_records = receipts or []
    _validate_selection_inputs(contract, attempts, rankings, receipt_records)
    attempt_order = {attempt.id: index for index, attempt in enumerate(attempts)}
    rankings_by_attempt = {ranking.attempt_id: ranking for ranking in rankings}
    receipts_by_attempt = {receipt.attempt_id: receipt for receipt in receipt_records}
    accepted_receipts = [
        receipt
        for receipt in receipt_records
        if receipt.accepted and receipt.attempt_id in attempt_order
    ]

    if accepted_receipts:
        selected_receipt = _best_receipt(accepted_receipts, rankings_by_attempt, attempt_order)
        selected_attempt_id = selected_receipt.attempt_id
        selection_reason = "hard_authoritative_accept"
        authoritative_receipt_id = selected_receipt.id
        uncertainty_milli = 0
    else:
        selected_attempt_id = _best_advisory_attempt(attempts, rankings_by_attempt)
        selected_ranking = rankings_by_attempt.get(selected_attempt_id)
        selection_reason = "advisory_ranking" if selected_ranking is not None else "first_candidate"
        authoritative_receipt_id = None
        uncertainty_milli = (
            selected_ranking.uncertainty_milli if selected_ranking else MAX_SCORE_MILLI
        )

    return CandidateSelectionRecord(
        id=selection_id if selection_id is not None else new_id("candidate-selection"),
        created_at=created_at if created_at is not None else utc_now(),
        task_contract_id=contract.id,
        candidate_attempt_ids=[attempt.id for attempt in attempts],
        selected_attempt_id=selected_attempt_id,
        rejected_alternatives=_rejected_alternatives(
            attempts=attempts,
            selected_attempt_id=selected_attempt_id,
            rankings_by_attempt=rankings_by_attempt,
            receipts_by_attempt=receipts_by_attempt,
            hard_winner=authoritative_receipt_id is not None,
        ),
        advisory_rankings=rankings,
        budget_used=budget_used or Money("EUR", 0),
        selection_reason=selection_reason,
        uncertainty_milli=uncertainty_milli,
        authoritative_receipt_id=authoritative_receipt_id,
    )


def selection_dataset_records(
    records: Sequence[dict[str, object]],
    selection: CandidateSelectionRecord,
) -> list[dict[str, object]]:
    """Annotate trajectory-like records with selection outcome metadata."""

    annotated: list[dict[str, object]] = []
    selection_payload = selection.to_dict()
    for record in records:
        next_record = copy.deepcopy(record)
        attempt_id = _record_attempt_id(next_record)
        if attempt_id in selection.candidate_attempt_ids:
            next_record["candidate_selection"] = selection_payload
            next_record["selection_outcome"] = (
                "selected" if attempt_id == selection.selected_attempt_id else "rejected"
            )
        annotated.append(next_record)
    return annotated


def require_score_milli(value: int, field: str) -> int:
    """Validate an integer score in thousandths."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    if value < 0 or value > MAX_SCORE_MILLI:
        raise ValidationError(f"{field} must be between 0 and {MAX_SCORE_MILLI}")
    return value


def _validate_selection_inputs(
    contract: TaskContract,
    attempts: list[Attempt],
    rankings: list[AdvisoryRankingRecord],
    receipts: list[VerificationReceipt],
) -> None:
    attempt_ids = {attempt.id for attempt in attempts}
    if len(attempt_ids) != len(attempts):
        raise ValidationError("attempt ids must be unique")
    for attempt in attempts:
        if attempt.task_contract_id != contract.id:
            raise ValidationError("attempt task_contract_id must match contract")
    for ranking in rankings:
        if ranking.attempt_id not in attempt_ids:
            raise ValidationError("advisory ranking attempt_id must reference a candidate")
    for receipt in receipts:
        if receipt.task_contract_id != contract.id:
            raise ValidationError("receipt task_contract_id must match contract")
        if receipt.attempt_id not in attempt_ids:
            raise ValidationError("receipt attempt_id must reference a candidate")


def _best_receipt(
    accepted_receipts: list[VerificationReceipt],
    rankings_by_attempt: dict[str, AdvisoryRankingRecord],
    attempt_order: dict[str, int],
) -> VerificationReceipt:
    return sorted(
        accepted_receipts,
        key=lambda receipt: (
            -_score_for_attempt(receipt.attempt_id, rankings_by_attempt),
            _uncertainty_for_attempt(receipt.attempt_id, rankings_by_attempt),
            attempt_order[receipt.attempt_id],
            receipt.attempt_id,
        ),
    )[0]


def _best_advisory_attempt(
    attempts: list[Attempt],
    rankings_by_attempt: dict[str, AdvisoryRankingRecord],
) -> str:
    return sorted(
        attempts,
        key=lambda attempt: (
            -_score_for_attempt(attempt.id, rankings_by_attempt),
            _uncertainty_for_attempt(attempt.id, rankings_by_attempt),
            attempt.id,
        ),
    )[0].id


def _score_for_attempt(
    attempt_id: str,
    rankings_by_attempt: dict[str, AdvisoryRankingRecord],
) -> int:
    ranking = rankings_by_attempt.get(attempt_id)
    return ranking.score_milli if ranking is not None else 0


def _uncertainty_for_attempt(
    attempt_id: str,
    rankings_by_attempt: dict[str, AdvisoryRankingRecord],
) -> int:
    ranking = rankings_by_attempt.get(attempt_id)
    return ranking.uncertainty_milli if ranking is not None else MAX_SCORE_MILLI


def _rejected_alternatives(
    *,
    attempts: list[Attempt],
    selected_attempt_id: str,
    rankings_by_attempt: dict[str, AdvisoryRankingRecord],
    receipts_by_attempt: dict[str, VerificationReceipt],
    hard_winner: bool,
) -> list[dict[str, object]]:
    rejected: list[dict[str, object]] = []
    for attempt in attempts:
        if attempt.id == selected_attempt_id:
            continue
        ranking = rankings_by_attempt.get(attempt.id)
        receipt = receipts_by_attempt.get(attempt.id)
        if receipt is not None and receipt.accepted is False:
            reason = "hard_rejected"
        elif hard_winner:
            reason = "hard_acceptance_dominated_advisory"
        elif ranking is not None:
            reason = "lower_advisory_score"
        else:
            reason = "no_selection_evidence"
        rejected.append(
            {
                "attempt_id": attempt.id,
                "reason": reason,
                "advisory_score_milli": ranking.score_milli if ranking else None,
                "uncertainty_milli": ranking.uncertainty_milli if ranking else None,
                "receipt_id": receipt.id if receipt else None,
                "receipt_accepted": receipt.accepted if receipt else None,
            }
        )
    return rejected


def _record_attempt_id(record: dict[str, object]) -> str | None:
    attempt = record.get("attempt")
    if isinstance(attempt, dict):
        attempt_id = attempt.get("id")
        if isinstance(attempt_id, str):
            return attempt_id
    attempt_id = record.get("attempt_id")
    if isinstance(attempt_id, str):
        return attempt_id
    return None
