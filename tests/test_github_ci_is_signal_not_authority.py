from faber.adapters.github.contracts import issue_to_task_contract, pull_request_to_attempt
from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.webhooks import parse_event
from faber.digests import sha256_digest
from faber.receipts import VerificationReceipt
from faber.verifiers import VerifierRun


def test_candidate_ci_is_signal_not_authoritative_receipt() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"checks": "read", "pull_requests": "read"},
    )
    check_payload = {
        "action": "completed",
        "repository": {"full_name": "lk251/faber"},
        "check_run": {"name": "candidate-ci", "conclusion": "success"},
    }
    event = parse_event("check_run", check_payload, delivery_id="delivery-ci")

    contract = issue_to_task_contract(
        GitHubIssueRef(
            repository_full_name="lk251/faber",
            issue_number=2,
            title="Implement adapter",
            body="Build fake client boundary.",
        ),
        installation=installation,
        verifier_ids=["verifier.faber"],
    )
    attempt = pull_request_to_attempt(
        GitHubPullRequestRef(
            repository_full_name="lk251/faber",
            pull_request_number=7,
            title="Adapter PR",
            body="Done.",
            author_login="worker",
            base_revision="base",
            head_revision="candidate",
        ),
        contract=contract,
        installation=installation,
        worker_id="worker",
        patch_digest=sha256_digest("patch"),
        check_summaries=[check_payload["check_run"]],
    )

    assert event.event_name == "check_run"
    assert attempt.metadata["candidate_ci"]["authority"] == "signal_only"
    assert isinstance(event, VerificationReceipt) is False

    verifier_run = VerifierRun(
        verifier_id="verifier.faber",
        name="Faber verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=True,
        metrics={"tests": 18},
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)

    assert receipt.accepted is True
    assert receipt.verifier_id == "verifier.faber"
    assert receipt.result_digest == verifier_run.result_digest()
