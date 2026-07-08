from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.receipts import VerificationReceipt
from faber.verifiers import VerifierRun


def test_receipt_binds_exact_contract_digest_and_candidate_revision() -> None:
    contract = TaskContract(
        id="task-contract_test",
        created_at="2026-01-01T00:00:00Z",
        title="Test task",
        description="Do the thing.",
        requirements=["pass tests"],
        verifier_ids=["verifier.tests"],
    )
    changed_contract = TaskContract(
        id="task-contract_test",
        created_at="2026-01-01T00:00:00Z",
        title="Test task",
        description="Do the changed thing.",
        requirements=["pass tests"],
        verifier_ids=["verifier.tests"],
    )
    attempt = Attempt(
        id="attempt_test",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker_test",
        base_revision="base",
        candidate_revision="candidate",
        summary="Implemented the thing.",
        patch_digest=sha256_digest("patch"),
    )
    verifier_run = VerifierRun(
        id="verifier-run_test",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.tests",
        name="Tests",
        version="1",
        command=["pytest"],
        passed=True,
        metrics={"tests": 1},
    )

    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)

    assert receipt.task_contract_digest == contract.digest()
    assert receipt.task_contract_digest != changed_contract.digest()
    assert receipt.candidate_revision == "candidate"
    assert receipt.base_revision == "base"
    assert receipt.result_digest == verifier_run.result_digest()
