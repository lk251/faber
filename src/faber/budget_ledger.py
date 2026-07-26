"""Exact, idempotent local accounting for work-budget reservations and settlement."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from faber import schemas
from faber.budgets import BudgetAllocation, BudgetEvent, RefundPolicy, Reservation, WorkBudget
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.ids import utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.store import save_record
from faber.trajectory_quality import quality_rank
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
)

BudgetReservation = Reservation
Clock = Callable[[], str]
SETTLEMENT_SPLIT_KINDS = {
    "worker",
    "verifier",
    "platform_margin",
    "trace_quality_bonus",
}


@dataclass(frozen=True)
class BudgetAccount:
    work_budget_id: str
    currency: str
    opening_minor_units: int
    active_reserved_minor_units: int
    settled_minor_units: int
    released_minor_units: int
    available_minor_units: int
    schema: str = schemas.BUDGET_ACCOUNT

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "work_budget_id": self.work_budget_id,
            "currency": self.currency,
            "opening_minor_units": self.opening_minor_units,
            "active_reserved_minor_units": self.active_reserved_minor_units,
            "settled_minor_units": self.settled_minor_units,
            "released_minor_units": self.released_minor_units,
            "available_minor_units": self.available_minor_units,
        }


@dataclass(frozen=True)
class BudgetRelease:
    work_budget_id: str
    reservation_id: str
    amount: Money
    reason: str
    refund_policy_state: str
    idempotency_key: str
    receipt_id: str | None = None
    id: str = ""
    created_at: str = ""
    schema: str = schemas.BUDGET_RELEASE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.BUDGET_RELEASE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.work_budget_id, "work_budget_id")
        require_non_empty_string(self.reservation_id, "reservation_id")
        require_non_empty_string(self.reason, "reason")
        require_non_empty_string(self.refund_policy_state, "refund_policy_state")
        require_non_empty_string(self.idempotency_key, "idempotency_key")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "work_budget_id": self.work_budget_id,
            "reservation_id": self.reservation_id,
            "receipt_id": self.receipt_id,
            "amount": self.amount.to_dict(),
            "reason": self.reason,
            "refund_policy_state": self.refund_policy_state,
            "idempotency_key": self.idempotency_key,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class BudgetSettlement:
    work_budget_id: str
    reservation_id: str
    receipt_id: str
    receipt_digest: str
    splits: dict[str, Money]
    idempotency_key: str
    id: str
    created_at: str
    schema: str = schemas.BUDGET_SETTLEMENT

    @property
    def total_minor_units(self) -> int:
        return sum(amount.minor_units for amount in self.splits.values())

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.BUDGET_SETTLEMENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.work_budget_id, "work_budget_id")
        require_non_empty_string(self.reservation_id, "reservation_id")
        require_non_empty_string(self.receipt_id, "receipt_id")
        require_non_empty_string(self.receipt_digest, "receipt_digest")
        require_non_empty_string(self.idempotency_key, "idempotency_key")
        require_mapping(self.splits, "splits")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "work_budget_id": self.work_budget_id,
            "reservation_id": self.reservation_id,
            "receipt_id": self.receipt_id,
            "receipt_digest": self.receipt_digest,
            "splits": {name: amount.to_dict() for name, amount in sorted(self.splits.items())},
            "total_minor_units": self.total_minor_units,
            "idempotency_key": self.idempotency_key,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class BudgetReconciliationReport:
    work_budget_id: str
    currency: str
    opening_minor_units: int
    active_reserved_minor_units: int
    settled_minor_units: int
    released_minor_units: int
    available_minor_units: int
    split_totals_minor_units: dict[str, int]
    reservation_count: int
    settlement_count: int
    release_count: int
    issues: list[str]
    id: str
    created_at: str
    schema: str = schemas.BUDGET_RECONCILIATION_REPORT

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "work_budget_id": self.work_budget_id,
            "currency": self.currency,
            "opening_minor_units": self.opening_minor_units,
            "active_reserved_minor_units": self.active_reserved_minor_units,
            "settled_minor_units": self.settled_minor_units,
            "released_minor_units": self.released_minor_units,
            "available_minor_units": self.available_minor_units,
            "split_totals_minor_units": self.split_totals_minor_units,
            "reservation_count": self.reservation_count,
            "settlement_count": self.settlement_count,
            "release_count": self.release_count,
            "issues": self.issues,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class WorkBudgetLedger:
    """Append-only accounting state with idempotency on every mutation."""

    def __init__(
        self,
        *,
        store_path: str | Path | None = None,
        clock: Clock = utc_now,
    ) -> None:
        self.store_path = Path(store_path) if store_path is not None else None
        self.clock = clock
        self._budgets: dict[str, WorkBudget] = {}
        self._allocations: dict[str, BudgetAllocation] = {}
        self._reservations: dict[str, BudgetReservation] = {}
        self._reservation_states: dict[str, str] = {}
        self._settlements: dict[str, BudgetSettlement] = {}
        self._releases: dict[str, BudgetRelease] = {}
        self._operation_digests: dict[str, str] = {}
        self._operation_results: dict[str, object] = {}
        self._events: list[BudgetEvent] = []

    def register_budget(
        self,
        budget: WorkBudget,
        *,
        idempotency_key: str,
    ) -> BudgetAccount:
        payload = {"operation": "register", "budget_digest": budget.digest()}
        existing = self._existing(idempotency_key, payload)
        if existing is not None:
            if not isinstance(existing, BudgetAccount):
                raise SettlementError("idempotency operation type mismatch")
            return existing
        if budget.id in self._budgets:
            raise SettlementError("work budget is already registered")
        self._budgets[budget.id] = budget
        account = self.account(budget.id)
        self._record_operation(idempotency_key, payload, account)
        self._append_event(
            event_type="budget.registered",
            budget=budget,
            amount=budget.amount,
            payload={"idempotency_key": idempotency_key, "budget_digest": budget.digest()},
            idempotency_key=idempotency_key,
        )
        return account

    def reserve(
        self,
        allocation: BudgetAllocation,
        *,
        attempt_id: str,
        idempotency_key: str,
        amount: Money | None = None,
        expires_at: str | None = None,
    ) -> BudgetReservation:
        reservation_amount = amount or allocation.amount
        payload = {
            "operation": "reserve",
            "allocation_digest": allocation.digest(),
            "attempt_id": attempt_id,
            "amount": reservation_amount.to_dict(),
            "expires_at": expires_at,
        }
        existing = self._existing(idempotency_key, payload)
        if existing is not None:
            if not isinstance(existing, Reservation):
                raise SettlementError("idempotency operation type mismatch")
            return existing
        budget = self._require_budget(allocation.work_budget_id)
        _require_currency(reservation_amount, budget.amount.currency, "reservation amount")
        if reservation_amount.minor_units <= 0:
            raise SettlementError("reservation amount must be positive")
        if reservation_amount.minor_units > allocation.amount.minor_units:
            raise SettlementError("reservation exceeds budget allocation")
        allocated_consumed = sum(
            reservation.amount.minor_units
            for reservation in self._reservations.values()
            if reservation.budget_allocation_id == allocation.id
            and self._reservation_states[reservation.id] in {"reserved", "settled"}
        )
        if allocated_consumed + reservation_amount.minor_units > allocation.amount.minor_units:
            raise SettlementError("budget allocation has insufficient available funds")
        if reservation_amount.minor_units > self.account(budget.id).available_minor_units:
            raise SettlementError("work budget has insufficient available funds")
        created_at = self.clock()
        reservation = Reservation(
            id=_stable_id("budget-reservation", idempotency_key),
            created_at=created_at,
            work_budget_id=budget.id,
            budget_allocation_id=allocation.id,
            task_contract_id=allocation.task_contract_id,
            attempt_id=attempt_id,
            amount=reservation_amount,
            purpose=allocation.purpose,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
        )
        self._allocations[allocation.id] = allocation
        self._reservations[reservation.id] = reservation
        self._reservation_states[reservation.id] = "reserved"
        self._record_operation(idempotency_key, payload, reservation)
        self._append_event(
            event_type="budget.reserved",
            budget=budget,
            amount=reservation.amount,
            payload={
                "idempotency_key": idempotency_key,
                "allocation_id": allocation.id,
                "attempt_id": attempt_id,
            },
            idempotency_key=idempotency_key,
            reservation_id=reservation.id,
        )
        return reservation

    def settle(
        self,
        reservation: BudgetReservation,
        receipt: VerificationReceipt,
        *,
        splits: dict[str, Money],
        idempotency_key: str,
        trajectory_quality: Mapping[str, object] | None = None,
    ) -> BudgetSettlement:
        split_payload = {name: amount.to_dict() for name, amount in sorted(splits.items())}
        payload = {
            "operation": "settle",
            "reservation_id": reservation.id,
            "receipt_digest": receipt.digest(),
            "splits": split_payload,
            "trajectory_quality": dict(trajectory_quality or {}),
        }
        existing = self._existing(idempotency_key, payload)
        if existing is not None:
            if not isinstance(existing, BudgetSettlement):
                raise SettlementError("idempotency operation type mismatch")
            return existing
        budget, allocation = self._require_active_reservation(reservation)
        self._validate_authoritative_receipt(reservation, allocation, receipt)
        _validate_splits(splits, reservation.amount)
        bonus = splits.get("trace_quality_bonus")
        if bonus is not None and bonus.minor_units > 0:
            self._validate_trace_bonus(allocation, trajectory_quality)
        settlement = BudgetSettlement(
            id=_stable_id("budget-settlement", idempotency_key),
            created_at=self.clock(),
            work_budget_id=budget.id,
            reservation_id=reservation.id,
            receipt_id=receipt.id,
            receipt_digest=receipt.digest(),
            splits=dict(splits),
            idempotency_key=idempotency_key,
        )
        self._settlements[settlement.id] = settlement
        self._reservation_states[reservation.id] = "settled"
        self._record_operation(idempotency_key, payload, settlement)
        self._append_event(
            event_type="budget.settled",
            budget=budget,
            amount=reservation.amount,
            payload={
                "idempotency_key": idempotency_key,
                "receipt_digest": receipt.digest(),
                "splits": split_payload,
            },
            idempotency_key=idempotency_key,
            reservation_id=reservation.id,
            receipt_id=receipt.id,
        )
        return settlement

    def release_rejected(
        self,
        reservation: BudgetReservation,
        receipt: VerificationReceipt,
        *,
        refund_policy: RefundPolicy,
        idempotency_key: str,
    ) -> BudgetRelease:
        if receipt.accepted:
            raise SettlementError("rejected release requires a rejected receipt")
        if receipt.task_contract_id != reservation.task_contract_id:
            raise SettlementError("receipt task does not match reservation")
        if receipt.attempt_id != reservation.attempt_id:
            raise SettlementError("receipt attempt does not match reservation")
        return self.release(
            reservation,
            reason="rejected",
            refund_policy_state=refund_policy.on_rejected,
            idempotency_key=idempotency_key,
            receipt=receipt,
        )

    def release_expired(
        self,
        reservation: BudgetReservation,
        *,
        refund_policy: RefundPolicy,
        idempotency_key: str,
    ) -> BudgetRelease:
        if reservation.expires_at is None:
            raise SettlementError("expired release requires reservation.expires_at")
        return self.release(
            reservation,
            reason="expired",
            refund_policy_state=refund_policy.on_expired,
            idempotency_key=idempotency_key,
        )

    def release(
        self,
        reservation: BudgetReservation,
        *,
        reason: str,
        refund_policy_state: str,
        idempotency_key: str,
        receipt: VerificationReceipt | None = None,
    ) -> BudgetRelease:
        payload = {
            "operation": "release",
            "reservation_id": reservation.id,
            "reason": reason,
            "refund_policy_state": refund_policy_state,
            "receipt_digest": receipt.digest() if receipt else None,
        }
        existing = self._existing(idempotency_key, payload)
        if existing is not None:
            if not isinstance(existing, BudgetRelease):
                raise SettlementError("idempotency operation type mismatch")
            return existing
        budget, _allocation = self._require_active_reservation(reservation)
        release = BudgetRelease(
            id=_stable_id("budget-release", idempotency_key),
            created_at=self.clock(),
            work_budget_id=budget.id,
            reservation_id=reservation.id,
            receipt_id=receipt.id if receipt else None,
            amount=reservation.amount,
            reason=reason,
            refund_policy_state=refund_policy_state,
            idempotency_key=idempotency_key,
        )
        self._releases[release.id] = release
        self._reservation_states[reservation.id] = "released"
        self._record_operation(idempotency_key, payload, release)
        self._append_event(
            event_type=f"budget.released.{reason}",
            budget=budget,
            amount=reservation.amount,
            payload={
                "idempotency_key": idempotency_key,
                "refund_policy_state": refund_policy_state,
            },
            idempotency_key=idempotency_key,
            reservation_id=reservation.id,
            receipt_id=receipt.id if receipt else None,
        )
        return release

    def account(self, work_budget_id: str) -> BudgetAccount:
        budget = self._require_budget(work_budget_id)
        reservations = [
            reservation
            for reservation in self._reservations.values()
            if reservation.work_budget_id == work_budget_id
        ]
        active_reserved = sum(
            reservation.amount.minor_units
            for reservation in reservations
            if self._reservation_states[reservation.id] == "reserved"
        )
        settled = sum(
            settlement.total_minor_units
            for settlement in self._settlements.values()
            if settlement.work_budget_id == work_budget_id
        )
        released = sum(
            release.amount.minor_units
            for release in self._releases.values()
            if release.work_budget_id == work_budget_id
        )
        available = budget.amount.minor_units - active_reserved - settled
        return BudgetAccount(
            work_budget_id=work_budget_id,
            currency=budget.amount.currency,
            opening_minor_units=budget.amount.minor_units,
            active_reserved_minor_units=active_reserved,
            settled_minor_units=settled,
            released_minor_units=released,
            available_minor_units=available,
        )

    def reconcile(self, work_budget_id: str) -> BudgetReconciliationReport:
        account = self.account(work_budget_id)
        settlements = [
            settlement
            for settlement in self._settlements.values()
            if settlement.work_budget_id == work_budget_id
        ]
        split_totals: dict[str, int] = {}
        for settlement in settlements:
            for name, amount in settlement.splits.items():
                split_totals[name] = split_totals.get(name, 0) + amount.minor_units
        issues: list[str] = []
        if (
            account.available_minor_units
            + account.active_reserved_minor_units
            + account.settled_minor_units
            != account.opening_minor_units
        ):
            issues.append("opening balance does not reconcile")
        if sum(split_totals.values()) != account.settled_minor_units:
            issues.append("settlement splits do not reconcile")
        reservations = [
            reservation
            for reservation in self._reservations.values()
            if reservation.work_budget_id == work_budget_id
        ]
        releases = [
            release
            for release in self._releases.values()
            if release.work_budget_id == work_budget_id
        ]
        return BudgetReconciliationReport(
            id=_stable_id("budget-reconciliation-report", work_budget_id),
            created_at=self.clock(),
            work_budget_id=work_budget_id,
            currency=account.currency,
            opening_minor_units=account.opening_minor_units,
            active_reserved_minor_units=account.active_reserved_minor_units,
            settled_minor_units=account.settled_minor_units,
            released_minor_units=account.released_minor_units,
            available_minor_units=account.available_minor_units,
            split_totals_minor_units=dict(sorted(split_totals.items())),
            reservation_count=len(reservations),
            settlement_count=len(settlements),
            release_count=len(releases),
            issues=issues,
        )

    def events(self) -> list[BudgetEvent]:
        return list(self._events)

    def _require_budget(self, work_budget_id: str) -> WorkBudget:
        budget = self._budgets.get(work_budget_id)
        if budget is None:
            raise SettlementError(f"work budget is not registered: {work_budget_id}")
        return budget

    def _require_active_reservation(
        self,
        reservation: BudgetReservation,
    ) -> tuple[WorkBudget, BudgetAllocation]:
        stored = self._reservations.get(reservation.id)
        if stored is None or stored.digest() != reservation.digest():
            raise SettlementError("reservation is not registered in this ledger")
        if self._reservation_states[reservation.id] != "reserved":
            raise SettlementError("reservation is not active")
        allocation = self._allocations[reservation.budget_allocation_id]
        return self._require_budget(reservation.work_budget_id), allocation

    def _validate_authoritative_receipt(
        self,
        reservation: BudgetReservation,
        allocation: BudgetAllocation,
        receipt: VerificationReceipt,
    ) -> None:
        if not receipt.accepted:
            raise SettlementError("settlement requires an accepted authoritative receipt")
        if receipt.task_contract_id != reservation.task_contract_id:
            raise SettlementError("receipt task does not match reservation")
        if receipt.attempt_id != reservation.attempt_id:
            raise SettlementError("receipt attempt does not match reservation")
        required = allocation.verifier_policy.get("required_verifier_ids", [])
        if not isinstance(required, list) or receipt.verifier_id not in required:
            raise SettlementError("receipt verifier is not authoritative for this allocation")

    def _validate_trace_bonus(
        self,
        allocation: BudgetAllocation,
        trajectory_quality: Mapping[str, object] | None,
    ) -> None:
        policy = allocation.trace_quality_bonus_policy
        if not policy:
            raise SettlementError("trace-quality bonus requires an allocation policy")
        if trajectory_quality is None:
            raise SettlementError("trace-quality bonus requires trajectory quality evidence")
        minimum = policy.get("minimum_quality_tier", "trace")
        actual = trajectory_quality.get("quality_tier")
        if isinstance(actual, Mapping):
            actual = actual.get("name")
        if not isinstance(minimum, str) or not isinstance(actual, str):
            raise SettlementError("trace-quality bonus requires trajectory quality evidence")
        if quality_rank(actual) < quality_rank(minimum):
            raise SettlementError("trajectory quality is below trace-quality bonus policy")

    def _existing(self, idempotency_key: str, payload: object) -> object | None:
        require_non_empty_string(idempotency_key, "idempotency_key")
        payload_digest = sha256_digest(payload)
        existing_digest = self._operation_digests.get(idempotency_key)
        if existing_digest is None:
            return None
        if existing_digest != payload_digest:
            raise SettlementError("idempotency key reused with different operation payload")
        return self._operation_results[idempotency_key]

    def _record_operation(
        self,
        idempotency_key: str,
        payload: object,
        result: object,
    ) -> None:
        self._operation_digests[idempotency_key] = sha256_digest(payload)
        self._operation_results[idempotency_key] = result

    def _append_event(
        self,
        *,
        event_type: str,
        budget: WorkBudget,
        amount: Money,
        payload: dict[str, object],
        idempotency_key: str,
        reservation_id: str | None = None,
        receipt_id: str | None = None,
    ) -> None:
        event = BudgetEvent(
            id=_stable_id("budget-event", idempotency_key),
            created_at=self.clock(),
            event_type=event_type,
            work_budget_id=budget.id,
            reservation_id=reservation_id,
            receipt_id=receipt_id,
            amount=amount,
            payload=payload,
        )
        self._events.append(event)
        if self.store_path is not None:
            save_record(self.store_path, "budget_event", event)


def _validate_splits(splits: dict[str, Money], amount: Money) -> None:
    if not splits:
        raise SettlementError("settlement splits must not be empty")
    unknown = sorted(set(splits) - SETTLEMENT_SPLIT_KINDS)
    if unknown:
        raise SettlementError(f"unsupported settlement split kinds: {unknown}")
    total = 0
    for name, split in splits.items():
        if not isinstance(split, Money):
            raise SettlementError(f"settlement split {name} must be Money")
        _require_currency(split, amount.currency, f"settlement split {name}")
        total += split.minor_units
    if total != amount.minor_units:
        raise SettlementError("settlement splits must sum exactly to reservation amount")


def _require_currency(amount: Money, currency: str, field_name: str) -> None:
    if not isinstance(amount, Money):
        raise ValidationError(f"{field_name} must be Money")
    if amount.currency != currency:
        raise SettlementError(f"{field_name} currency mismatch")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_digest(value).removeprefix('sha256:')[:16]}"
