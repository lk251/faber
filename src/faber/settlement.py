"""Settlement records and invariants."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt

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
    schema: str = "faber.settlement.v1"

    def __post_init__(self) -> None:
        if self.status not in SETTLEMENT_STATUSES:
            raise ValueError(f"invalid settlement status: {self.status}")
        if self.status == "paid" and not self.receipt_accepted:
            raise ValueError("paid settlement requires an accepted receipt")

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
            raise ValueError("settlement receipt does not match")
        if not receipt.accepted:
            raise ValueError("cannot mark rejected work as paid")
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
