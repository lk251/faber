"""Provider-agnostic work budget records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

BUDGET_PURPOSES = {"solver_payout", "verifier_spend", "trace_quality_bonus", "review_budget"}
REFUND_POLICY_STATES = {"refund_to_source", "return_to_budget", "manual_review", "expire_unclaimed"}


@dataclass(frozen=True)
class FundingSource:
    """Provider-neutral source of funds, without payment-provider behavior."""

    source_type: str
    display_name: str
    currency: str
    provider_ref: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("funding-source"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.FUNDING_SOURCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.FUNDING_SOURCE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.source_type, "source_type")
        require_non_empty_string(self.display_name, "display_name")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError("currency must be a three-letter code")
        if self.provider_ref is not None:
            require_non_empty_string(self.provider_ref, "provider_ref")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "source_type": self.source_type,
            "display_name": self.display_name,
            "currency": self.currency.upper(),
            "provider_ref": self.provider_ref,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class FundingEvent:
    """Provider-tagged funding signal reconciled by an adapter."""

    provider: str
    external_event_id: str
    source_type: str
    target_kind: str
    target_ref: str
    amount: Money
    occurred_at: str
    payload: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("funding-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.FUNDING_EVENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.FUNDING_EVENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.provider, "provider")
        require_non_empty_string(self.external_event_id, "external_event_id")
        require_non_empty_string(self.source_type, "source_type")
        require_non_empty_string(self.target_kind, "target_kind")
        require_non_empty_string(self.target_ref, "target_ref")
        _require_money(self.amount, "amount")
        require_non_empty_string(self.occurred_at, "occurred_at")
        require_mapping(self.payload, "payload")

    @property
    def idempotency_key(self) -> str:
        return f"{self.provider}:{self.external_event_id}"

    def stable_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "provider": self.provider,
            "external_event_id": self.external_event_id,
            "idempotency_key": self.idempotency_key,
            "source_type": self.source_type,
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "amount": self.amount.to_dict(),
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            **self.stable_payload(),
        }

    def digest(self) -> str:
        return sha256_digest(self.stable_payload())


@dataclass(frozen=True)
class RefundPolicy:
    """Explicit unused/rejected/expired fund policy states."""

    on_rejected: str = "refund_to_source"
    on_expired: str = "refund_to_source"
    on_cancelled: str = "manual_review"
    notes: str = ""
    id: str = field(default_factory=lambda: new_id("refund-policy"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.REFUND_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.REFUND_POLICY)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        for field_name, value in [
            ("on_rejected", self.on_rejected),
            ("on_expired", self.on_expired),
            ("on_cancelled", self.on_cancelled),
        ]:
            _require_refund_policy_state(value, field_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "on_rejected": self.on_rejected,
            "on_expired": self.on_expired,
            "on_cancelled": self.on_cancelled,
            "notes": self.notes,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class WorkBudget:
    """Funds attached to a target such as a GitHub issue, label, verifier, or task class."""

    funding_source_id: str
    amount: Money
    target_kind: str
    target_ref: str
    verifier_policy: dict[str, object]
    purpose_allocations: dict[str, Money]
    refund_policy: RefundPolicy
    status: str = "active"
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("work-budget"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.WORK_BUDGET

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.WORK_BUDGET)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.funding_source_id, "funding_source_id")
        _require_money(self.amount, "amount")
        require_non_empty_string(self.target_kind, "target_kind")
        require_non_empty_string(self.target_ref, "target_ref")
        require_mapping(self.verifier_policy, "verifier_policy")
        _require_purpose_money_mapping(
            self.purpose_allocations,
            "purpose_allocations",
            currency=self.amount.currency,
        )
        allocated_minor_units = sum(
            value.minor_units for value in self.purpose_allocations.values()
        )
        if allocated_minor_units > self.amount.minor_units:
            raise ValidationError("purpose allocations cannot exceed work budget amount")
        if not isinstance(self.refund_policy, RefundPolicy):
            raise ValidationError("refund_policy must be a RefundPolicy")
        require_non_empty_string(self.status, "status")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "funding_source_id": self.funding_source_id,
            "amount": self.amount.to_dict(),
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "verifier_policy": self.verifier_policy,
            "purpose_allocations": {
                purpose: amount.to_dict()
                for purpose, amount in sorted(self.purpose_allocations.items())
            },
            "refund_policy": self.refund_policy.to_dict(),
            "status": self.status,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class BudgetAllocation:
    """Budget assigned to a concrete task contract and purpose."""

    work_budget_id: str
    task_contract_id: str
    task_contract_digest: str
    amount: Money
    purpose: str
    verifier_policy: dict[str, object]
    trace_quality_bonus_policy: dict[str, object] = field(default_factory=dict)
    status: str = "allocated"
    id: str = field(default_factory=lambda: new_id("budget-allocation"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.BUDGET_ALLOCATION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.BUDGET_ALLOCATION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.work_budget_id, "work_budget_id")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.task_contract_digest, "task_contract_digest")
        _require_money(self.amount, "amount")
        _require_budget_purpose(self.purpose, "purpose")
        require_mapping(self.verifier_policy, "verifier_policy")
        require_mapping(self.trace_quality_bonus_policy, "trace_quality_bonus_policy")
        require_non_empty_string(self.status, "status")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "work_budget_id": self.work_budget_id,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "amount": self.amount.to_dict(),
            "purpose": self.purpose,
            "verifier_policy": self.verifier_policy,
            "trace_quality_bonus_policy": self.trace_quality_bonus_policy,
            "status": self.status,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class Pledge:
    """Conditional support for a target or outcome."""

    funding_source_id: str
    amount: Money
    target_kind: str
    target_ref: str
    conditions: list[str]
    status: str = "pledged"
    id: str = field(default_factory=lambda: new_id("pledge"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.PLEDGE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PLEDGE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.funding_source_id, "funding_source_id")
        _require_money(self.amount, "amount")
        require_non_empty_string(self.target_kind, "target_kind")
        require_non_empty_string(self.target_ref, "target_ref")
        require_string_list(self.conditions, "conditions")
        require_non_empty_string(self.status, "status")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "funding_source_id": self.funding_source_id,
            "amount": self.amount.to_dict(),
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "conditions": self.conditions,
            "status": self.status,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class Reservation:
    """Budget reserved for a candidate attempt, not yet authorized for payout."""

    work_budget_id: str
    budget_allocation_id: str
    task_contract_id: str
    attempt_id: str
    amount: Money
    purpose: str
    idempotency_key: str
    status: str = "reserved"
    expires_at: str | None = None
    id: str = field(default_factory=lambda: new_id("budget-reservation"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.BUDGET_RESERVATION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.BUDGET_RESERVATION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.work_budget_id, "work_budget_id")
        require_non_empty_string(self.budget_allocation_id, "budget_allocation_id")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.attempt_id, "attempt_id")
        _require_money(self.amount, "amount")
        _require_budget_purpose(self.purpose, "purpose")
        require_non_empty_string(self.idempotency_key, "idempotency_key")
        require_non_empty_string(self.status, "status")
        if self.expires_at is not None:
            require_non_empty_string(self.expires_at, "expires_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "work_budget_id": self.work_budget_id,
            "budget_allocation_id": self.budget_allocation_id,
            "task_contract_id": self.task_contract_id,
            "attempt_id": self.attempt_id,
            "amount": self.amount.to_dict(),
            "purpose": self.purpose,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "expires_at": self.expires_at,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class BudgetEvent:
    """Append-only budget-domain event for audit and training export."""

    event_type: str
    work_budget_id: str
    amount: Money
    payload: dict[str, object]
    reservation_id: str | None = None
    receipt_id: str | None = None
    id: str = field(default_factory=lambda: new_id("budget-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.BUDGET_EVENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.BUDGET_EVENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.event_type, "event_type")
        require_non_empty_string(self.work_budget_id, "work_budget_id")
        _require_money(self.amount, "amount")
        require_mapping(self.payload, "payload")
        if self.reservation_id is not None:
            require_non_empty_string(self.reservation_id, "reservation_id")
        if self.receipt_id is not None:
            require_non_empty_string(self.receipt_id, "receipt_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "event_type": self.event_type,
            "work_budget_id": self.work_budget_id,
            "reservation_id": self.reservation_id,
            "receipt_id": self.receipt_id,
            "amount": self.amount.to_dict(),
            "payload": self.payload,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class BudgetReservationBook:
    """In-memory idempotent reservation book for deterministic tests and adapters."""

    def __init__(self) -> None:
        self._reservations_by_key: dict[str, Reservation] = {}
        self._reserved_minor_units_by_allocation: dict[str, int] = {}

    def reserve(
        self,
        allocation: BudgetAllocation,
        *,
        attempt_id: str,
        idempotency_key: str,
        amount: Money | None = None,
        expires_at: str | None = None,
    ) -> Reservation:
        if idempotency_key in self._reservations_by_key:
            return self._reservations_by_key[idempotency_key]
        reservation_amount = amount or allocation.amount
        _require_same_currency(reservation_amount, allocation.amount, "reservation amount")
        already_reserved = self._reserved_minor_units_by_allocation.get(allocation.id, 0)
        if already_reserved + reservation_amount.minor_units > allocation.amount.minor_units:
            raise SettlementError("budget allocation has insufficient unreserved funds")
        reservation = Reservation(
            work_budget_id=allocation.work_budget_id,
            budget_allocation_id=allocation.id,
            task_contract_id=allocation.task_contract_id,
            attempt_id=attempt_id,
            amount=reservation_amount,
            purpose=allocation.purpose,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
        )
        self._reservations_by_key[idempotency_key] = reservation
        self._reserved_minor_units_by_allocation[allocation.id] = (
            already_reserved + reservation_amount.minor_units
        )
        return reservation

    def reservations(self) -> list[Reservation]:
        return [self._reservations_by_key[key] for key in sorted(self._reservations_by_key)]


class FundingEventLedger:
    """Idempotent in-memory reconciler for adapter-emitted funding events."""

    def __init__(self) -> None:
        self._events_by_key: dict[str, FundingEvent] = {}

    def record(self, event: FundingEvent) -> FundingEvent:
        existing = self._events_by_key.get(event.idempotency_key)
        if existing is not None:
            if existing.digest() != event.digest():
                raise ValidationError("funding event idempotency key reused with different payload")
            return existing
        self._events_by_key[event.idempotency_key] = event
        return event

    def events(self) -> list[FundingEvent]:
        return [self._events_by_key[key] for key in sorted(self._events_by_key)]


def issue_work_budget(
    *,
    repository: str,
    issue_number: int,
    funding_source: FundingSource,
    amount: Money,
    verifier_policy: dict[str, object],
    purpose_allocations: dict[str, Money] | None = None,
    refund_policy: RefundPolicy | None = None,
) -> WorkBudget:
    require_non_empty_string(repository, "repository")
    if issue_number <= 0:
        raise ValidationError("issue_number must be positive")
    _require_same_currency(amount, Money(funding_source.currency, 0), "work budget amount")
    return WorkBudget(
        funding_source_id=funding_source.id,
        amount=amount,
        target_kind="github.issue",
        target_ref=f"{repository}#{issue_number}",
        verifier_policy=verifier_policy,
        purpose_allocations=purpose_allocations or {"solver_payout": amount},
        refund_policy=refund_policy or RefundPolicy(),
        metadata={"repository": repository, "issue_number": issue_number},
    )


def work_budget_from_funding_event(
    event: FundingEvent,
    *,
    verifier_policy: dict[str, object],
    target_kind: str | None = None,
    target_ref: str | None = None,
    purpose_allocations: dict[str, Money] | None = None,
    refund_policy: RefundPolicy | None = None,
) -> tuple[FundingSource, WorkBudget]:
    budget_target_kind = target_kind or event.target_kind
    budget_target_ref = target_ref or event.target_ref
    source = FundingSource(
        id=_stable_id("funding-source", event.idempotency_key),
        source_type=event.source_type,
        display_name=f"{event.provider} funding event",
        currency=event.amount.currency,
        provider_ref=event.idempotency_key,
        metadata={
            "provider": event.provider,
            "external_event_id": event.external_event_id,
            "funding_event_digest": event.digest(),
        },
    )
    budget = WorkBudget(
        id=_stable_id(
            "work-budget",
            f"{event.idempotency_key}:{budget_target_kind}:{budget_target_ref}",
        ),
        funding_source_id=source.id,
        amount=event.amount,
        target_kind=budget_target_kind,
        target_ref=budget_target_ref,
        verifier_policy=verifier_policy,
        purpose_allocations=purpose_allocations or {"solver_payout": event.amount},
        refund_policy=refund_policy or RefundPolicy(),
        metadata={
            "provider": event.provider,
            "external_event_id": event.external_event_id,
            "source_target_kind": event.target_kind,
            "source_target_ref": event.target_ref,
        },
    )
    return source, budget


def issue_budget_from_repository_funding_event(
    event: FundingEvent,
    *,
    issue_number: int,
    verifier_policy: dict[str, object],
    purpose_allocations: dict[str, Money] | None = None,
    refund_policy: RefundPolicy | None = None,
) -> tuple[FundingSource, WorkBudget]:
    if event.target_kind != "github.repository":
        raise ValidationError("repository funding allocation requires github.repository event")
    if issue_number <= 0:
        raise ValidationError("issue_number must be positive")
    return work_budget_from_funding_event(
        event,
        verifier_policy=verifier_policy,
        target_kind="github.issue",
        target_ref=f"{event.target_ref}#{issue_number}",
        purpose_allocations=purpose_allocations,
        refund_policy=refund_policy,
    )


def allocate_budget_to_task(
    budget: WorkBudget,
    contract: TaskContract,
    *,
    amount: Money,
    purpose: str,
    trace_quality_bonus_policy: dict[str, object] | None = None,
) -> BudgetAllocation:
    _require_same_currency(amount, budget.amount, "budget allocation amount")
    if amount.minor_units > budget.amount.minor_units:
        raise ValidationError("budget allocation cannot exceed work budget amount")
    return BudgetAllocation(
        work_budget_id=budget.id,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        amount=amount,
        purpose=purpose,
        verifier_policy=budget.verifier_policy,
        trace_quality_bonus_policy=trace_quality_bonus_policy or {},
    )


def authorize_budget_spend(
    reservation: Reservation,
    receipt: VerificationReceipt,
    *,
    amount: Money | None = None,
    trace_bonus_policy_approved: bool = False,
) -> BudgetEvent:
    if not receipt.accepted:
        raise SettlementError("budget spend requires an accepted authoritative receipt")
    if receipt.task_contract_id != reservation.task_contract_id:
        raise SettlementError("budget spend receipt task does not match reservation")
    if receipt.attempt_id != reservation.attempt_id:
        raise SettlementError("budget spend receipt attempt does not match reservation")
    spend_amount = amount or reservation.amount
    _require_same_currency(spend_amount, reservation.amount, "budget spend amount")
    if spend_amount.minor_units > reservation.amount.minor_units:
        raise SettlementError("budget spend cannot exceed reservation amount")
    if reservation.purpose == "trace_quality_bonus" and not trace_bonus_policy_approved:
        raise SettlementError("trace-quality bonus requires explicit policy approval")
    return BudgetEvent(
        event_type="budget.spend_authorized",
        work_budget_id=reservation.work_budget_id,
        reservation_id=reservation.id,
        receipt_id=receipt.id,
        amount=spend_amount,
        payload={
            "purpose": reservation.purpose,
            "authority": "verification_receipt",
            "receipt_digest": receipt.digest(),
        },
    )


def expire_reservation(reservation: Reservation, refund_policy: RefundPolicy) -> BudgetEvent:
    return BudgetEvent(
        event_type="budget.reservation_expired",
        work_budget_id=reservation.work_budget_id,
        reservation_id=reservation.id,
        amount=reservation.amount,
        payload={
            "reservation_status": "expired",
            "refund_policy_state": refund_policy.on_expired,
        },
    )


def rejected_reservation_refund_event(
    reservation: Reservation,
    refund_policy: RefundPolicy,
) -> BudgetEvent:
    return BudgetEvent(
        event_type="budget.reservation_rejected",
        work_budget_id=reservation.work_budget_id,
        reservation_id=reservation.id,
        amount=reservation.amount,
        payload={
            "reservation_status": "rejected",
            "refund_policy_state": refund_policy.on_rejected,
        },
    )


def _require_budget_purpose(value: str, field: str) -> str:
    require_non_empty_string(value, field)
    if value not in BUDGET_PURPOSES:
        raise ValidationError(f"{field} must be one of {sorted(BUDGET_PURPOSES)}")
    return value


def _require_refund_policy_state(value: str, field: str) -> str:
    require_non_empty_string(value, field)
    if value not in REFUND_POLICY_STATES:
        raise ValidationError(f"{field} must be one of {sorted(REFUND_POLICY_STATES)}")
    return value


def _require_money(value: Money, field: str) -> Money:
    if not isinstance(value, Money):
        raise ValidationError(f"{field} must be Money")
    return value


def _require_purpose_money_mapping(
    value: dict[str, Money],
    field: str,
    *,
    currency: str,
) -> None:
    require_mapping(value, field)
    for purpose, amount in value.items():
        _require_budget_purpose(purpose, f"{field} key")
        _require_money(amount, f"{field}.{purpose}")
        if amount.currency != currency:
            raise ValidationError(f"{field}.{purpose} currency must match budget currency")


def _require_same_currency(left: Money, right: Money, field: str) -> None:
    _require_money(left, field)
    _require_money(right, field)
    if left.currency != right.currency:
        raise ValidationError(f"{field} currency mismatch")


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256_digest(value).removeprefix("sha256:")[:16]
    return f"{prefix}_{digest}"
