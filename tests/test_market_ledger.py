import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError
from faber.ledger import LedgerAccount, MarketLedger
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.verifiers import VerifierRun


def _receipt(*, accepted: bool = True) -> VerificationReceipt:
    contract = TaskContract(
        id="task-contract_ledger",
        created_at="2026-01-01T00:00:00Z",
        title="Ledger task",
        description="Test ledger settlement.",
        requirements=["settle"],
        verifier_ids=["verifier.ledger"],
    )
    attempt = Attempt(
        id="attempt_ledger",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker",
        base_revision="base",
        candidate_revision="candidate",
        summary="Done",
        patch_digest=sha256_digest("patch"),
    )
    run = VerifierRun(
        verifier_id="verifier.ledger",
        name="Ledger verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=accepted,
        metrics={},
        failure_reasons=[] if accepted else ["failed"],
    )
    return VerificationReceipt.from_verifier_run(contract, attempt, run)


def _ledger() -> MarketLedger:
    ledger = MarketLedger()
    for account in [
        LedgerAccount("external", "EUR", "external", allow_negative=True),
        LedgerAccount("buyer", "EUR", "buyer"),
        LedgerAccount("escrow", "EUR", "escrow"),
        LedgerAccount("worker", "EUR", "worker"),
        LedgerAccount("platform", "EUR", "platform"),
        LedgerAccount("verifier", "EUR", "verifier"),
        LedgerAccount("operating", "EUR", "operating"),
    ]:
        ledger.add_account(account)
    ledger.record_entry(
        source_account_id="external",
        destination_account_id="buyer",
        amount=Money("EUR", 10_000),
        reason="local_funding",
        idempotency_key="fund-buyer",
    )
    return ledger


def test_ledger_uses_exact_integer_accounting() -> None:
    ledger = _ledger()

    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 2_500),
        idempotency_key="reserve-1",
    )

    assert ledger.balance("buyer").minor_units == 7_500
    assert ledger.balance("escrow").minor_units == 2_500


def test_idempotent_reservation_does_not_double_reserve() -> None:
    ledger = _ledger()
    kwargs = {
        "buyer_account_id": "buyer",
        "escrow_account_id": "escrow",
        "amount": Money("EUR", 2_500),
        "idempotency_key": "reserve-1",
    }

    first = ledger.reserve(**kwargs)
    second = ledger.reserve(**kwargs)

    assert first == second
    assert ledger.balance("escrow").minor_units == 2_500


def test_no_payout_without_accepted_receipt() -> None:
    ledger = _ledger()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 1_000),
        idempotency_key="reserve-1",
    )

    with pytest.raises(SettlementError, match="accepted verification receipt"):
        ledger.payout(
            escrow_account_id="escrow",
            worker_account_id="worker",
            receipt=_receipt(accepted=False),
            amount=Money("EUR", 1_000),
            idempotency_key="payout-1",
        )


def test_duplicate_payout_does_not_double_pay() -> None:
    ledger = _ledger()
    receipt = _receipt()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 1_000),
        idempotency_key="reserve-1",
    )

    first = ledger.payout(
        escrow_account_id="escrow",
        worker_account_id="worker",
        receipt=receipt,
        amount=Money("EUR", 1_000),
        idempotency_key="payout-1",
    )
    second = ledger.payout(
        escrow_account_id="escrow",
        worker_account_id="worker",
        receipt=receipt,
        amount=Money("EUR", 1_000),
        idempotency_key="payout-1",
    )

    assert first == second
    assert ledger.balance("worker").minor_units == 1_000


def test_split_settlement_sums_exactly() -> None:
    ledger = _ledger()
    receipt = _receipt()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 2_500),
        idempotency_key="reserve-1",
    )

    entries = ledger.split_settlement(
        escrow_account_id="escrow",
        receipt=receipt,
        worker_account_id="worker",
        worker_amount=Money("EUR", 1_800),
        platform_account_id="platform",
        platform_fee=Money("EUR", 400),
        verifier_account_id="verifier",
        verifier_fee=Money("EUR", 200),
        operating_account_id="operating",
        operating_amount=Money("EUR", 100),
        idempotency_key="settle-1",
    )

    assert sum(entry.amount.minor_units for entry in entries) == 2_500
    assert ledger.balance("escrow").minor_units == 0
    assert ledger.balance("worker").minor_units == 1_800


def test_refund_path_for_rejected_work() -> None:
    ledger = _ledger()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 2_500),
        idempotency_key="reserve-1",
    )

    refund = ledger.refund(
        escrow_account_id="escrow",
        buyer_account_id="buyer",
        amount=Money("EUR", 2_500),
        idempotency_key="refund-1",
        reason="rejected_work_refund",
    )

    assert refund.reason == "rejected_work_refund"
    assert ledger.balance("escrow").minor_units == 0
    assert ledger.balance("buyer").minor_units == 10_000


def test_reconciliation_summary() -> None:
    ledger = _ledger()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 1_000),
        idempotency_key="reserve-1",
    )

    summary = ledger.reconciliation_summary()

    assert summary["entry_count"] == 2
    assert summary["balances_minor_units"]["buyer"] == 9_000
    assert summary["total_debits_minor_units"] == summary["total_credits_minor_units"]
