import pytest

from faber.adapters.github.contracts import issue_to_task_contract
from faber.adapters.github.events import GitHubIssueRef
from faber.adapters.github.installation import GitHubInstallation


def test_github_issue_ref_becomes_task_contract_without_label_authority() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read"},
    )
    issue = GitHubIssueRef(
        repository_full_name="lk251/faber",
        issue_number=2,
        title="Implement adapter",
        body="Build the fake client boundary.",
        labels=["verified", "urgent"],
        author_login="javier",
        html_url="https://github.com/lk251/faber/issues/2",
    )

    contract = issue_to_task_contract(
        issue,
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )

    assert contract.task_source == "github.issue"
    assert contract.repository == "lk251/faber"
    assert contract.verifier_ids == ["verifier.faber.local"]
    assert "verified" not in contract.verifier_ids
    assert contract.environment["issue_number"] == 2
    assert contract.environment["html_url"] == "https://github.com/lk251/faber/issues/2"
    assert contract.environment["author_login"] == "javier"
    assert contract.environment["labels"] == ["verified", "urgent"]
    assert contract.environment["labels_are_authority"] is False


def test_github_issue_contract_rejects_out_of_scope_repository() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read"},
    )
    issue = GitHubIssueRef(
        repository_full_name="lk251/agent-bounty-market",
        issue_number=2,
        title="Wrong repo",
        body="Nope.",
    )

    with pytest.raises(ValueError, match="outside the GitHub installation scope"):
        issue_to_task_contract(issue, installation=installation, verifier_ids=["verifier"])
