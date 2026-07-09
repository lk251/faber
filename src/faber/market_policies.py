"""Claim, competition, retry, shadow-attempt, and selection market policies."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.selection import (
    AdvisoryRankingRecord,
    CandidateSelectionRecord,
    select_best_attempt,
)
from faber.validation import require_non_empty_string, require_schema

CLAIM_MODES = {"exclusive", "open"}
COMPETITION_MODES = {"single_claim", "open_competition", "best_of_n"}


@dataclass(frozen=True)
class AttemptPolicy:
    max_active_attempts: int
    allow_pr_only: bool = True
    schema: str = schemas.ATTEMPT_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ATTEMPT_POLICY)
        _require_positive_int(self.max_active_attempts, "max_active_attempts")
        if not isinstance(self.allow_pr_only, bool):
            raise ValidationError("allow_pr_only must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_active_attempts": self.max_active_attempts,
            "allow_pr_only": self.allow_pr_only,
        }


@dataclass(frozen=True)
class ClaimPolicy:
    mode: str
    claim_ttl_seconds: int | None = None
    release_on_failure: bool = True
    schema: str = schemas.CLAIM_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.CLAIM_POLICY)
        if self.mode not in CLAIM_MODES:
            raise ValidationError(f"claim mode must be one of {sorted(CLAIM_MODES)}")
        if self.claim_ttl_seconds is not None:
            _require_positive_int(self.claim_ttl_seconds, "claim_ttl_seconds")
        if not isinstance(self.release_on_failure, bool):
            raise ValidationError("release_on_failure must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "mode": self.mode,
            "claim_ttl_seconds": self.claim_ttl_seconds,
            "release_on_failure": self.release_on_failure,
        }


@dataclass(frozen=True)
class CompetitionPolicy:
    mode: str
    max_candidates: int
    pay_winner_only: bool
    rejected_attempt_stipend: Money | None = None
    schema: str = schemas.COMPETITION_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.COMPETITION_POLICY)
        if self.mode not in COMPETITION_MODES:
            raise ValidationError(
                f"competition mode must be one of {sorted(COMPETITION_MODES)}"
            )
        _require_positive_int(self.max_candidates, "max_candidates")
        if not isinstance(self.pay_winner_only, bool):
            raise ValidationError("pay_winner_only must be a boolean")
        if self.rejected_attempt_stipend is not None and not isinstance(
            self.rejected_attempt_stipend, Money
        ):
            raise ValidationError("rejected_attempt_stipend must be Money or null")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "mode": self.mode,
            "max_candidates": self.max_candidates,
            "pay_winner_only": self.pay_winner_only,
            "rejected_attempt_stipend": (
                self.rejected_attempt_stipend.to_dict()
                if self.rejected_attempt_stipend
                else None
            ),
        }


@dataclass(frozen=True)
class RetryPolicy:
    max_retries_per_worker: int
    retry_after_rejection: bool = True
    schema: str = schemas.RETRY_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.RETRY_POLICY)
        _require_non_negative_int(self.max_retries_per_worker, "max_retries_per_worker")
        if not isinstance(self.retry_after_rejection, bool):
            raise ValidationError("retry_after_rejection must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_retries_per_worker": self.max_retries_per_worker,
            "retry_after_rejection": self.retry_after_rejection,
        }


@dataclass(frozen=True)
class ShadowAttemptPolicy:
    enabled: bool
    settlement_allowed: bool
    require_training_consent: bool = True
    schema: str = schemas.SHADOW_ATTEMPT_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.SHADOW_ATTEMPT_POLICY)
        for field_name, value in [
            ("enabled", self.enabled),
            ("settlement_allowed", self.settlement_allowed),
            ("require_training_consent", self.require_training_consent),
        ]:
            if not isinstance(value, bool):
                raise ValidationError(f"{field_name} must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "enabled": self.enabled,
            "settlement_allowed": self.settlement_allowed,
            "require_training_consent": self.require_training_consent,
        }


@dataclass(frozen=True)
class SelectionPolicy:
    verifier_budget_cap: Money
    authoritative_acceptance_required: bool = True
    advisory_ranking_allowed: bool = True
    name: str = "hard-authoritative-then-advisory"
    schema: str = schemas.SELECTION_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.SELECTION_POLICY)
        if not isinstance(self.verifier_budget_cap, Money):
            raise ValidationError("verifier_budget_cap must be Money")
        if not isinstance(self.authoritative_acceptance_required, bool):
            raise ValidationError("authoritative_acceptance_required must be a boolean")
        if not isinstance(self.advisory_ranking_allowed, bool):
            raise ValidationError("advisory_ranking_allowed must be a boolean")
        require_non_empty_string(self.name, "name")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "verifier_budget_cap": self.verifier_budget_cap.to_dict(),
            "authoritative_acceptance_required": self.authoritative_acceptance_required,
            "advisory_ranking_allowed": self.advisory_ranking_allowed,
            "name": self.name,
        }


@dataclass(frozen=True)
class AttemptClaim:
    task_contract_id: str
    worker_id: str
    idempotency_key: str
    status: str = "active"
    id: str = field(default_factory=lambda: new_id("attempt-claim"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ATTEMPT_CLAIM

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "worker_id": self.worker_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class CandidateEntry:
    attempt: Attempt
    verifier_cost: Money
    training_consent: bool
    shadow: bool
    status: str = "submitted"

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt": self.attempt.to_dict(),
            "verifier_cost": self.verifier_cost.to_dict(),
            "training_consent": self.training_consent,
            "shadow": self.shadow,
            "status": self.status,
        }


class CandidatePool:
    """Stateful local policy evaluator for claims and competing attempts."""

    def __init__(
        self,
        *,
        contract: TaskContract,
        attempt_policy: AttemptPolicy,
        claim_policy: ClaimPolicy,
        competition_policy: CompetitionPolicy,
        retry_policy: RetryPolicy,
        shadow_attempt_policy: ShadowAttemptPolicy,
        selection_policy: SelectionPolicy,
        pool_id: str | None = None,
        created_at: str | None = None,
    ) -> None:
        self.contract = contract
        self.attempt_policy = attempt_policy
        self.claim_policy = claim_policy
        self.competition_policy = competition_policy
        self.retry_policy = retry_policy
        self.shadow_attempt_policy = shadow_attempt_policy
        self.selection_policy = selection_policy
        self.id = pool_id or new_id("candidate-pool")
        self.created_at = created_at or utc_now()
        self.schema = schemas.CANDIDATE_POOL
        self._claims_by_key: dict[str, AttemptClaim] = {}
        self._entries_by_attempt: dict[str, CandidateEntry] = {}
        self._selection: CandidateSelectionRecord | None = None

    def claim(self, worker_id: str, *, idempotency_key: str) -> AttemptClaim:
        require_non_empty_string(worker_id, "worker_id")
        require_non_empty_string(idempotency_key, "idempotency_key")
        existing = self._claims_by_key.get(idempotency_key)
        if existing is not None:
            if existing.worker_id != worker_id:
                raise ValidationError("claim idempotency key reused by another worker")
            return existing
        active_claims = [
            claim for claim in self._claims_by_key.values() if claim.status == "active"
        ]
        if self.claim_policy.mode == "exclusive" and active_claims:
            raise ValidationError("exclusive claim is already active")
        claim = AttemptClaim(
            id=f"attempt-claim_{sha256_digest(idempotency_key)[-16:]}",
            created_at=self.created_at,
            task_contract_id=self.contract.id,
            worker_id=worker_id,
            idempotency_key=idempotency_key,
        )
        self._claims_by_key[idempotency_key] = claim
        return claim

    def release_claim(self, claim_id: str) -> AttemptClaim:
        for key, claim in self._claims_by_key.items():
            if claim.id == claim_id:
                released = replace(claim, status="released")
                self._claims_by_key[key] = released
                return released
        raise ValidationError("claim not found")

    def submit(
        self,
        attempt: Attempt,
        *,
        verifier_cost: Money,
        training_consent: bool,
        shadow: bool = False,
    ) -> CandidateEntry:
        if attempt.task_contract_id != self.contract.id:
            raise ValidationError("attempt task_contract_id must match candidate pool contract")
        if attempt.id in self._entries_by_attempt:
            return self._entries_by_attempt[attempt.id]
        if len(self._entries_by_attempt) >= self.competition_policy.max_candidates:
            raise ValidationError("competition candidate limit reached")
        active_count = sum(
            entry.status in {"submitted", "selected"}
            for entry in self._entries_by_attempt.values()
        )
        if active_count >= self.attempt_policy.max_active_attempts:
            raise ValidationError("active attempt limit reached")
        if self.competition_policy.mode == "single_claim":
            active_workers = {
                claim.worker_id
                for claim in self._claims_by_key.values()
                if claim.status == "active"
            }
            if attempt.worker_id not in active_workers:
                raise ValidationError("single-claim attempt requires the active claimant")
        prior_worker_attempts = sum(
            entry.attempt.worker_id == attempt.worker_id
            for entry in self._entries_by_attempt.values()
        )
        if prior_worker_attempts > self.retry_policy.max_retries_per_worker:
            raise ValidationError("worker retry limit reached")
        if not isinstance(training_consent, bool):
            raise ValidationError("training_consent must be a boolean")
        if shadow:
            if not self.shadow_attempt_policy.enabled:
                raise ValidationError("shadow attempts are disabled")
            if self.shadow_attempt_policy.require_training_consent and not training_consent:
                raise ValidationError("shadow attempt requires training consent")
        if verifier_cost.currency != self.selection_policy.verifier_budget_cap.currency:
            raise ValidationError("verifier cost currency must match selection budget")
        spent = sum(
            entry.verifier_cost.minor_units
            for entry in self._entries_by_attempt.values()
        )
        if (
            spent + verifier_cost.minor_units
            > self.selection_policy.verifier_budget_cap.minor_units
        ):
            raise ValidationError("verifier budget cap exceeded")
        entry = CandidateEntry(
            attempt=attempt,
            verifier_cost=verifier_cost,
            training_consent=training_consent,
            shadow=shadow,
        )
        self._entries_by_attempt[attempt.id] = entry
        return entry

    def select(
        self,
        *,
        advisory_rankings: list[AdvisoryRankingRecord] | None = None,
        receipts: list[VerificationReceipt] | None = None,
    ) -> CandidateSelectionRecord:
        rankings = advisory_rankings or []
        if rankings and not self.selection_policy.advisory_ranking_allowed:
            raise ValidationError("selection policy does not allow advisory ranking")
        entries = self.entries()
        if not entries:
            raise ValidationError("candidate pool is empty")
        budget_used = Money(
            self.selection_policy.verifier_budget_cap.currency,
            sum(entry.verifier_cost.minor_units for entry in entries),
        )
        selection = select_best_attempt(
            contract=self.contract,
            attempts=[entry.attempt for entry in entries],
            advisory_rankings=rankings,
            receipts=receipts or [],
            budget_used=budget_used,
            selection_id=f"candidate-selection_{self.id}",
            created_at=self.created_at,
        )
        self._selection = selection
        for attempt_id, entry in list(self._entries_by_attempt.items()):
            status = "selected" if attempt_id == selection.selected_attempt_id else "rejected"
            self._entries_by_attempt[attempt_id] = replace(entry, status=status)
        return selection

    def entries(self) -> list[CandidateEntry]:
        return list(self._entries_by_attempt.values())

    def training_records(self) -> list[dict[str, object]]:
        return [
            {
                "candidate_pool_id": self.id,
                "task_contract_id": self.contract.id,
                "attempt_id": entry.attempt.id,
                "worker_id": entry.attempt.worker_id,
                "status": entry.status,
                "shadow": entry.shadow,
                "verifier_cost": entry.verifier_cost.to_dict(),
                "selection_id": self._selection.id if self._selection else None,
            }
            for entry in self.entries()
            if entry.training_consent
        ]

    def require_settlement_eligible(
        self,
        attempt_id: str,
        receipt: VerificationReceipt,
    ) -> None:
        entry = self._entries_by_attempt.get(attempt_id)
        if entry is None:
            raise SettlementError("attempt is not in candidate pool")
        if self._selection is None or self._selection.selected_attempt_id != attempt_id:
            raise SettlementError("only the selected attempt is settlement eligible")
        if entry.shadow and not self.shadow_attempt_policy.settlement_allowed:
            raise SettlementError("shadow attempt policy forbids settlement")
        if not receipt.accepted or receipt.attempt_id != attempt_id:
            raise SettlementError("settlement requires an accepted receipt for the attempt")
        if (
            self.selection_policy.authoritative_acceptance_required
            and self._selection.authoritative_receipt_id != receipt.id
        ):
            raise SettlementError("selection lacks matching authoritative acceptance")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.contract.id,
            "attempt_policy": self.attempt_policy.to_dict(),
            "claim_policy": self.claim_policy.to_dict(),
            "competition_policy": self.competition_policy.to_dict(),
            "retry_policy": self.retry_policy.to_dict(),
            "shadow_attempt_policy": self.shadow_attempt_policy.to_dict(),
            "selection_policy": self.selection_policy.to_dict(),
            "claims": [claim.to_dict() for claim in self._claims_by_key.values()],
            "entries": [entry.to_dict() for entry in self.entries()],
            "selection": self._selection.to_dict() if self._selection else None,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def _require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")
