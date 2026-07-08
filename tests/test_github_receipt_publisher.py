from faber.adapters.github.client import FakeGitHubClient
from faber.adapters.github.publisher import publish_verification_receipt
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.receipts import VerificationReceipt
from faber.verifiers import VerifierRun


def _receipt() -> VerificationReceipt:
    contract = TaskContract(
        id="task-contract_publish",
        created_at="2026-01-01T00:00:00Z",
        title="Publish receipt",
        description="Publish verifier receipt.",
        requirements=["publish"],
        verifier_ids=["verifier.faber"],
        repository="lk251/faber",
    )
    attempt = Attempt(
        id="attempt_publish",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker",
        base_revision="base",
        candidate_revision="candidate",
        summary="Done",
        patch_digest=sha256_digest("patch"),
    )
    verifier_run = VerifierRun(
        id="verifier-run_publish",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.faber",
        name="Faber verifier",
        version="1",
        command=["pytest"],
        passed=True,
        metrics={"tests": 1},
    )
    return VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)


def test_verification_receipt_publishes_to_fake_github_client() -> None:
    receipt = _receipt()
    client = FakeGitHubClient()

    publication = publish_verification_receipt(
        client,
        receipt,
        repository="lk251/faber",
        target_kind="pull_request",
        target_number=7,
    )

    assert client.publications == [publication]
    assert publication.target_kind == "pull_request"
    assert publication.target_number == 7
    assert publication.payload["authority"] == "faber.verification_receipt"
    assert publication.payload["result"] == "accepted"
    assert publication.payload["receipt_id"] == receipt.id
    assert publication.payload["receipt_digest"] == receipt.digest()
    assert publication.payload["task_contract_id"] == receipt.task_contract_id
    assert publication.payload["task_contract_digest"] == receipt.task_contract_digest
    assert publication.payload["attempt_id"] == receipt.attempt_id
    assert publication.payload["candidate_revision"] == "candidate"
    assert publication.payload["verifier_id"] == "verifier.faber"
    assert publication.payload["result_digest"] == receipt.result_digest
    assert "Receipt digest:" in publication.body


def test_publication_digest_is_stable_for_same_receipt_target() -> None:
    receipt = _receipt()

    first = publish_verification_receipt(
        FakeGitHubClient(),
        receipt,
        repository="lk251/faber",
        target_kind="issue",
        target_number=2,
    )
    second = publish_verification_receipt(
        FakeGitHubClient(),
        receipt,
        repository="lk251/faber",
        target_kind="issue",
        target_number=2,
    )

    assert first.digest() == second.digest()
