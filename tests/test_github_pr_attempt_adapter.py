import pytest

from faber.adapters.github.contracts import issue_to_task_contract, pull_request_to_attempt
from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.digests import sha256_digest


def _installation() -> GitHubInstallation:
    return GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"pull_requests": "read", "checks": "read"},
    )


def _contract(installation: GitHubInstallation):
    return issue_to_task_contract(
        GitHubIssueRef(
            repository_full_name="lk251/faber",
            issue_number=2,
            title="Implement adapter",
            body="Build the fake client boundary.",
        ),
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )


def test_github_pr_ref_becomes_attempt_with_ci_as_metadata_only() -> None:
    installation = _installation()
    contract = _contract(installation)
    pull_request = GitHubPullRequestRef(
        repository_full_name="lk251/faber",
        pull_request_number=7,
        title="Implement GitHub adapter",
        body="Adds fake client tests.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
        html_url="https://github.com/lk251/faber/pull/7",
    )

    attempt = pull_request_to_attempt(
        pull_request,
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("patch diff"),
        check_summaries=[{"name": "candidate-ci", "conclusion": "success"}],
    )

    assert attempt.task_contract_id == contract.id
    assert attempt.base_revision == "base-sha"
    assert attempt.candidate_revision == "head-sha"
    assert attempt.tool_summaries == []
    assert attempt.metadata["pull_request_number"] == 7
    assert attempt.metadata["candidate_ci"]["authority"] == "signal_only"
    assert attempt.metadata["candidate_ci"]["check_summaries"][0]["conclusion"] == "success"


def test_github_pr_attempt_rejects_contract_repository_mismatch() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber", "lk251/other"],
        permissions={"pull_requests": "read"},
    )
    contract = _contract(installation)
    pull_request = GitHubPullRequestRef(
        repository_full_name="lk251/other",
        pull_request_number=7,
        title="Wrong repo",
        body="Nope.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
    )

    with pytest.raises(ValueError, match="does not match task contract repository"):
        pull_request_to_attempt(
            pull_request,
            contract=contract,
            installation=installation,
            worker_id="worker",
            patch_digest=sha256_digest("patch"),
        )


def test_github_pr_attempt_rejects_out_of_scope_repository() -> None:
    installation = _installation()
    contract = _contract(installation)
    pull_request = GitHubPullRequestRef(
        repository_full_name="lk251/other",
        pull_request_number=7,
        title="Wrong repo",
        body="Nope.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
    )

    with pytest.raises(ValueError, match="outside the GitHub installation scope"):
        pull_request_to_attempt(
            pull_request,
            contract=contract,
            installation=installation,
            worker_id="worker",
            patch_digest=sha256_digest("patch"),
        )
