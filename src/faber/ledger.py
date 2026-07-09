"""Provider-agnostic local market ledger."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.validation import require_mapping, require_non_empty_string


@dataclass(frozen=True)
class LedgerAccount:
    account_id: str
    currency: str
    account_type: str
    allow_negative: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.LEDGER_ACCOUNT

    def __post_init__(self) -> None:
        require_non_empty_string(self.account_id, "account_id")
        require_non_empty_string(self.currency, "currency")
        require_non_empty_string(self.account_type, "account_type")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "account_id": self.account_id,
            "created_at": self.created_at,
            "currency": self.currency,
            "account_type": self.account_type,
            "allow_negative": self.allow_negative,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class LedgerEntry:
    source_account_id: str
    destination_account_id: str
    amount: Money
    reason: str
    idempotency_key: str
    related_receipt_id: str | None = None
    id: str = field(default_factory=lambda: new_id("ledger-entry"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.LEDGER_ENTRY

    def __post_init__(self) -> None:
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.source_account_id, "source_account_id")
        require_non_empty_string(self.destination_account_id, "destination_account_id")
        require_non_empty_string(self.reason, "reason")
        require_non_empty_string(self.idempotency_key, "idempotency_key")
        if self.related_receipt_id is not None:
            require_non_empty_string(self.related_receipt_id, "related_receipt_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "source_account_id": self.source_account_id,
            "destination_account_id": self.destination_account_id,
            "amount": self.amount.to_dict(),
            "reason": self.reason,
            "idempotency_key": self.idempotency_key,
            "related_receipt_id": self.related_receipt_id,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class MarketLedger:
    """Append-only in-memory market ledger for local accounting."""

    def __init__(self) -> None:
        self._accounts: dict[str, LedgerAccount] = {}
        self._entries: list[LedgerEntry] = []
        self._idempotency: dict[str, LedgerEntry] = {}

    def add_account(self, account: LedgerAccount) -> LedgerAccount:
        existing = self._accounts.get(account.account_id)
        if existing is not None and existing.digest() != account.digest():
            raise ValidationError(f"account {account.account_id!r} already exists differently")
        self._accounts[account.account_id] = account
        return account

    def account(self, account_id: str) -> LedgerAccount:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise ValidationError(f"unknown account_id {account_id!r}") from exc

    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)

    def balance(self, account_id: str) -> Money:
        account = self.account(account_id)
        balance = 0
        for entry in self._entries:
            if entry.amount.currency != account.currency:
                continue
            if entry.destination_account_id == account_id:
                balance += entry.amount.minor_units
            if entry.source_account_id == account_id:
                balance -= entry.amount.minor_units
        if balance < 0:
            raise ValidationError(f"account {account_id!r} has a negative balance")
        return Money(account.currency, balance)

    def record_entry(
        self,
        *,
        source_account_id: str,
        destination_account_id: str,
        amount: Money,
        reason: str,
        idempotency_key: str,
        related_receipt_id: str | None = None,
    ) -> LedgerEntry:
        if idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]
        source = self.account(source_account_id)
        destination = self.account(destination_account_id)
        if source.currency != amount.currency or destination.currency != amount.currency:
            raise ValidationError(
                "ledger entry currency must match source and destination accounts"
            )
        if (
            not source.allow_negative
            and self._balance_minor_units(source.account_id) < amount.minor_units
        ):
            raise SettlementError(f"account {source.account_id!r} has insufficient funds")
        entry = LedgerEntry(
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key,
            related_receipt_id=related_receipt_id,
        )
        self._entries.append(entry)
        self._idempotency[idempotency_key] = entry
        return entry

    def reserve(
        self,
        *,
        buyer_account_id: str,
        escrow_account_id: str,
        amount: Money,
        idempotency_key: str,
    ) -> LedgerEntry:
        return self.record_entry(
            source_account_id=buyer_account_id,
            destination_account_id=escrow_account_id,
            amount=amount,
            reason="reservation",
            idempotency_key=idempotency_key,
        )

    def payout(
        self,
        *,
        escrow_account_id: str,
        worker_account_id: str,
        receipt: VerificationReceipt,
        amount: Money,
        idempotency_key: str,
    ) -> LedgerEntry:
        if not receipt.accepted:
            raise SettlementError("payout requires an accepted verification receipt")
        return self.record_entry(
            source_account_id=escrow_account_id,
            destination_account_id=worker_account_id,
            amount=amount,
            reason="worker_payout",
            idempotency_key=idempotency_key,
            related_receipt_id=receipt.id,
        )

    def split_settlement(
        self,
        *,
        escrow_account_id: str,
        receipt: VerificationReceipt,
        worker_account_id: str,
        worker_amount: Money,
        platform_account_id: str,
        platform_fee: Money,
        idempotency_key: str,
        verifier_account_id: str | None = None,
        verifier_fee: Money | None = None,
        operating_account_id: str | None = None,
        operating_amount: Money | None = None,
    ) -> list[LedgerEntry]:
        if not receipt.accepted:
            raise SettlementError("split settlement requires an accepted verification receipt")
        amounts = [worker_amount, platform_fee]
        if verifier_fee is not None:
            amounts.append(verifier_fee)
        if operating_amount is not None:
            amounts.append(operating_amount)
        currencies = {amount.currency for amount in amounts}
        if len(currencies) != 1:
            raise ValidationError("split settlement amounts must use one currency")
        total_minor_units = sum(amount.minor_units for amount in amounts)
        escrow = self.account(escrow_account_id)
        if (
            not escrow.allow_negative
            and self._balance_minor_units(escrow_account_id) < total_minor_units
        ):
            raise SettlementError("escrow account has insufficient funds for split settlement")
        entries = [
            self.payout(
                escrow_account_id=escrow_account_id,
                worker_account_id=worker_account_id,
                receipt=receipt,
                amount=worker_amount,
                idempotency_key=f"{idempotency_key}:worker",
            ),
            self.record_entry(
                source_account_id=escrow_account_id,
                destination_account_id=platform_account_id,
                amount=platform_fee,
                reason="platform_fee",
                idempotency_key=f"{idempotency_key}:platform",
                related_receipt_id=receipt.id,
            ),
        ]
        if verifier_account_id and verifier_fee:
            entries.append(
                self.record_entry(
                    source_account_id=escrow_account_id,
                    destination_account_id=verifier_account_id,
                    amount=verifier_fee,
                    reason="verifier_fee",
                    idempotency_key=f"{idempotency_key}:verifier",
                    related_receipt_id=receipt.id,
                )
            )
        if operating_account_id and operating_amount:
            entries.append(
                self.record_entry(
                    source_account_id=escrow_account_id,
                    destination_account_id=operating_account_id,
                    amount=operating_amount,
                    reason="retained_operating_spend",
                    idempotency_key=f"{idempotency_key}:operating",
                    related_receipt_id=receipt.id,
                )
            )
        return entries

    def refund(
        self,
        *,
        escrow_account_id: str,
        buyer_account_id: str,
        amount: Money,
        idempotency_key: str,
        reason: str = "refund",
    ) -> LedgerEntry:
        return self.record_entry(
            source_account_id=escrow_account_id,
            destination_account_id=buyer_account_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key,
        )

    def reconciliation_summary(self) -> dict[str, object]:
        balances = {
            account_id: self._balance_minor_units(account_id)
            for account_id in sorted(self._accounts)
        }
        return {
            "entry_count": len(self._entries),
            "balances_minor_units": balances,
            "total_debits_minor_units": sum(entry.amount.minor_units for entry in self._entries),
            "total_credits_minor_units": sum(entry.amount.minor_units for entry in self._entries),
            "idempotency_key_count": len(self._idempotency),
        }

    def _balance_minor_units(self, account_id: str) -> int:
        balance = 0
        for entry in self._entries:
            if entry.destination_account_id == account_id:
                balance += entry.amount.minor_units
            if entry.source_account_id == account_id:
                balance -= entry.amount.minor_units
        return balance
