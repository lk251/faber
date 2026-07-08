import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.settlement import Settlement
from faber.verifiers import VerifierRun


def test_settlement_cannot_mark_rejected_work_as_paid() -> None:
    contract = TaskContract(
        id="task-contract_rejected",
        created_at="2026-01-01T00:00:00Z",
        title="Rejected task",
        description="This attempt fails.",
        requirements=["pass tests"],
        verifier_ids=["verifier.tests"],
    )
    attempt = Attempt(
        id="attempt_rejected",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker_rejected",
        base_revision="base",
        candidate_revision="candidate",
        summary="Broken implementation.",
        patch_digest=sha256_digest("broken patch"),
    )
    verifier_run = VerifierRun(
        id="verifier-run_rejected",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.tests",
        name="Tests",
        version="1",
        command=["pytest"],
        passed=False,
        metrics={"tests": 1, "failures": 1},
        failure_reasons=["unit tests failed"],
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
    settlement = Settlement.from_receipt(receipt, Money("EUR", 1000))

    with pytest.raises(ValueError, match="cannot mark rejected work as paid"):
        settlement.mark_paid(receipt)


def test_paid_settlement_requires_accepted_receipt_flag() -> None:
    with pytest.raises(ValueError, match="paid settlement requires an accepted receipt"):
        Settlement(
            receipt_id="receipt",
            worker_id="worker",
            amount=Money("EUR", 1000),
            status="paid",
            receipt_accepted=False,
        )
