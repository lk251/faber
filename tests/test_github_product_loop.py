import json
from pathlib import Path

from faber.adapters.github.client import FakeGitHubClient
from faber.adapters.github.contracts import issue_to_task_contract, pull_request_to_attempt
from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.markers import parse_contract_marker, render_contract_marker
from faber.adapters.github.publisher import (
    publish_verification_receipt,
    render_receipt_publication_body,
)
from faber.adapters.github.webhooks import parse_event
from faber.datasets import export_trajectories_jsonl
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.settlement import Settlement
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRun
from faber.workers import WorkerProfile

FIXTURES = Path("tests/fixtures/github")


def _json_fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_realistic_github_fixtures_parse() -> None:
    issue_payload = _json_fixture("issue_opened.json")
    pr_payload = _json_fixture("pull_request_opened.json")
    check_payload = _json_fixture("check_run_completed.json")

    issue = GitHubIssueRef.from_payload(issue_payload)
    pull_request = GitHubPullRequestRef.from_payload(pr_payload)
    check_event = parse_event("check_run", check_payload, delivery_id="delivery-1")

    assert issue.issue_number == 42
    assert issue.labels == ["faber", "dataset"]
    assert pull_request.base_revision == "base-sha-0001"
    assert pull_request.head_revision == "candidate-sha-0002"
    assert check_event.repository_full_name == "lk251/faber"


def test_contract_marker_round_trips_in_human_issue_body() -> None:
    installation = GitHubInstallation(
        installation_id=12345,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read"},
    )
    contract = issue_to_task_contract(
        GitHubIssueRef.from_payload(_json_fixture("issue_opened.json")),
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )
    issue_body = (FIXTURES / "issue_body.md").read_text(encoding="utf-8")

    parsed = parse_contract_marker(f"{issue_body}\n\n{render_contract_marker(contract)}")

    assert parsed.contract_id == contract.id
    assert parsed.contract_digest == contract.digest()


def test_publication_text_is_readable_for_accepted_and_rejected_receipts() -> None:
    accepted = _receipt(accepted=True)
    rejected = _receipt(accepted=False)

    accepted_body = render_receipt_publication_body(accepted)
    rejected_body = render_receipt_publication_body(rejected)

    assert "Faber verification result: accepted" in accepted_body
    assert "Candidate revision: candidate-sha-0002" in accepted_body
    assert "Receipt digest:" in accepted_body
    assert "Next action: maintainer may review" in accepted_body
    assert "Faber verification result: rejected" in rejected_body
    assert "Next action: inspect verifier failure reasons" in rejected_body


def test_full_fake_github_product_loop_exports_trajectory(tmp_path: Path) -> None:
    installation = GitHubInstallation(
        installation_id=12345,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read", "pull_requests": "read", "checks": "read"},
    )
    issue_payload = _json_fixture("issue_opened.json")
    pr_payload = _json_fixture("pull_request_opened.json")
    check_payload = _json_fixture("check_run_completed.json")
    issue_event = parse_event("issues", issue_payload, delivery_id="issue-delivery")
    check_event = parse_event("check_run", check_payload, delivery_id="check-delivery")
    contract = issue_to_task_contract(
        GitHubIssueRef.from_payload(issue_payload),
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )
    marker = render_contract_marker(contract)
    attempt = pull_request_to_attempt(
        GitHubPullRequestRef.from_payload(pr_payload),
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("diff-ref"),
        check_summaries=[check_payload["check_run"]],
    )
    verifier_run = VerifierRun(
        verifier_id="verifier.faber.local",
        name="Faber local verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=True,
        metrics={"tests": 59},
        logs_digest=sha256_digest("logs"),
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
    client = FakeGitHubClient()
    publication = publish_verification_receipt(
        client,
        receipt,
        repository="lk251/faber",
        target_kind="pull_request",
        target_number=77,
    )
    settlement = Settlement.from_receipt(receipt, Money("EUR", 1000)).mark_paid(
        receipt,
        transaction_ref="fake-product-loop",
        paid_at="2026-01-01T00:00:00Z",
    )
    trajectory = Trajectory(
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        settlement=settlement,
        router_decision=RouterDecision(
            task_contract_id=contract.id,
            selected_worker_id=attempt.worker_id,
            rejected_alternatives=[],
            estimated_cost=Money("EUR", 400),
            expected_value=Money("EUR", 1500),
            policy_name="fixture-router",
        ),
        worker_profile=WorkerProfile(
            id=attempt.worker_id,
            display_name="GitHub Worker",
            capabilities=["python"],
        ),
        cost_metadata={"compute_minor_units": 250, "review_minor_units": 150},
        latency_metadata={"work_seconds": 120},
        review_metadata={"human_reviewed": False, "source": "fake-github-product-loop"},
    )
    manifest = export_trajectories_jsonl([trajectory], tmp_path / "trajectories.jsonl")

    assert issue_event.event_name == "issues"
    assert check_event.event_name == "check_run"
    assert parse_contract_marker(marker).contract_id == contract.id
    assert attempt.metadata["candidate_ci"]["authority"] == "signal_only"
    assert publication.payload["authority"] == "faber.verification_receipt"
    assert client.publications == [publication]
    assert manifest.record_count == 1
    assert (tmp_path / "trajectories.jsonl").exists()


def test_rejected_verifier_publication_path() -> None:
    receipt = _receipt(accepted=False)
    client = FakeGitHubClient()

    publication = publish_verification_receipt(
        client,
        receipt,
        repository="lk251/faber",
        target_kind="check",
    )

    assert publication.payload["result"] == "rejected"
    assert "rejected" in publication.body
    assert "Next action: inspect verifier failure reasons" in publication.body


def _receipt(*, accepted: bool) -> VerificationReceipt:
    installation = GitHubInstallation(
        installation_id=12345,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read", "pull_requests": "read"},
    )
    contract = issue_to_task_contract(
        GitHubIssueRef.from_payload(_json_fixture("issue_opened.json")),
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )
    attempt = pull_request_to_attempt(
        GitHubPullRequestRef.from_payload(_json_fixture("pull_request_opened.json")),
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("diff-ref"),
    )
    verifier_run = VerifierRun(
        verifier_id="verifier.faber.local",
        name="Faber local verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=accepted,
        metrics={"tests": 1, "failures": 0 if accepted else 1},
        failure_reasons=[] if accepted else ["unit tests failed"],
        logs_digest=sha256_digest("logs"),
    )
    return VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
