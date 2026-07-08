"""Helpers for adapting GitHub task evidence into contracts."""

from __future__ import annotations

from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.attempts import Attempt
from faber.contracts import TaskContract


def issue_contract(
    *,
    repository: str,
    issue_number: int,
    title: str,
    body: str,
    verifier_ids: list[str],
) -> TaskContract:
    return TaskContract(
        title=title,
        description=body,
        requirements=[f"Resolve GitHub issue #{issue_number}."],
        verifier_ids=verifier_ids,
        task_source="github.issue",
        repository=repository,
        environment={"adapter": "github", "issue_number": issue_number},
    )


def issue_to_task_contract(
    issue: GitHubIssueRef,
    *,
    installation: GitHubInstallation,
    verifier_ids: list[str],
) -> TaskContract:
    """Convert a GitHub issue reference into a verifier-first task contract."""

    if not installation.allows_repository(issue.repository_full_name):
        raise ValueError("issue repository is outside the GitHub installation scope")
    if not verifier_ids:
        raise ValueError("verifier_ids are required")
    return TaskContract(
        title=issue.title,
        description=issue.body,
        requirements=[f"Resolve GitHub issue #{issue.issue_number}."],
        verifier_ids=verifier_ids,
        task_source="github.issue",
        repository=issue.repository_full_name,
        environment={
            "adapter": "github",
            "repository": issue.repository_full_name,
            "issue_number": issue.issue_number,
            "html_url": issue.html_url,
            "author_login": issue.author_login,
            "labels": issue.labels,
            "labels_are_authority": False,
        },
    )


def pull_request_to_attempt(
    pull_request: GitHubPullRequestRef,
    *,
    contract: TaskContract,
    installation: GitHubInstallation,
    worker_id: str,
    patch_digest: str,
    check_summaries: list[dict[str, object]] | None = None,
) -> Attempt:
    """Convert a GitHub pull request reference into an attempt for a contract."""

    if not installation.allows_repository(pull_request.repository_full_name):
        raise ValueError("pull request repository is outside the GitHub installation scope")
    if contract.repository != pull_request.repository_full_name:
        raise ValueError("pull request repository does not match task contract repository")
    if not patch_digest:
        raise ValueError("patch_digest is required")
    if not worker_id:
        raise ValueError("worker_id is required")
    return Attempt(
        task_contract_id=contract.id,
        worker_id=worker_id,
        base_revision=pull_request.base_revision,
        candidate_revision=pull_request.head_revision,
        summary=pull_request.title,
        patch_digest=patch_digest,
        tool_summaries=[],
        metadata={
            "adapter": "github",
            "repository": pull_request.repository_full_name,
            "pull_request_number": pull_request.pull_request_number,
            "html_url": pull_request.html_url,
            "author_login": pull_request.author_login,
            "body": pull_request.body,
            "candidate_ci": {
                "authority": "signal_only",
                "check_summaries": check_summaries or [],
            },
        },
    )
