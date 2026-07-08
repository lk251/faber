"""Settlement records and invariants."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import SettlementError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.validation import require_non_empty_string, require_schema

SETTLEMENT_STATUSES = {"pending", "paid", "rejected"}


@dataclass(frozen=True)
class Settlement:
    """Settlement follows verification and cannot pay rejected work."""

    receipt_id: str
    worker_id: str
    amount: Money
    status: str = "pending"
    receipt_accepted: bool = False
    transaction_ref: str | None = None
    paid_at: str | None = None
    id: str = field(default_factory=lambda: new_id("settlement"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.SETTLEMENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.SETTLEMENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.receipt_id, "receipt_id")
        require_non_empty_string(self.worker_id, "worker_id")
        if self.status not in SETTLEMENT_STATUSES:
            raise SettlementError(f"status must be one of {sorted(SETTLEMENT_STATUSES)}")
        if self.status == "paid" and not self.receipt_accepted:
            raise SettlementError("paid settlement requires an accepted receipt")

    @classmethod
    def from_receipt(cls, receipt: VerificationReceipt, amount: Money) -> Settlement:
        return cls(
            receipt_id=receipt.id,
            worker_id=receipt.worker_id,
            amount=amount,
            receipt_accepted=receipt.accepted,
            status="pending",
        )

    def mark_paid(
        self,
        receipt: VerificationReceipt,
        *,
        transaction_ref: str | None = None,
        paid_at: str | None = None,
    ) -> Settlement:
        if receipt.id != self.receipt_id:
            raise SettlementError("receipt_id does not match settlement receipt_id")
        if not receipt.accepted:
            raise SettlementError("cannot mark rejected work as paid")
        if self.status == "paid":
            return self
        return replace(
            self,
            status="paid",
            receipt_accepted=True,
            transaction_ref=transaction_ref,
            paid_at=paid_at or utc_now(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "receipt_id": self.receipt_id,
            "worker_id": self.worker_id,
            "amount": self.amount.to_dict(),
            "status": self.status,
            "receipt_accepted": self.receipt_accepted,
            "transaction_ref": self.transaction_ref,
            "paid_at": self.paid_at,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
