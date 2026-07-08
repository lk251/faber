"""Dependency-light GitHub adapter skeleton for Faber for GitHub."""

from faber.adapters.github.contracts import issue_to_task_contract, pull_request_to_attempt
from faber.adapters.github.events import (
    GitHubEvent,
    GitHubIssueRef,
    GitHubPullRequestRef,
    GitHubRepositoryRef,
)
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.markers import parse_contract_marker, render_contract_marker
from faber.adapters.github.publisher import publish_verification_receipt

__all__ = [
    "GitHubEvent",
    "GitHubInstallation",
    "GitHubIssueRef",
    "GitHubPullRequestRef",
    "GitHubRepositoryRef",
    "issue_to_task_contract",
    "parse_contract_marker",
    "publish_verification_receipt",
    "pull_request_to_attempt",
    "render_contract_marker",
]
