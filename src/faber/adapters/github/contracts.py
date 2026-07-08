"""Helpers for adapting GitHub task evidence into contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.errors import ScopeError, ValidationError
from faber.ids import new_id
from faber.traces import AttemptManifest

ATTEMPT_MANIFEST_PATH = ".faber/attempt.json"
ATTEMPT_MANIFEST_EVIDENCE_SCHEMA = "faber.github_attempt_manifest_evidence.v1"


@dataclass(frozen=True)
class PullRequestAttemptManifestEvidence:
    """Optional `.faber/attempt.json` evidence found in a PR file map."""

    status: str
    source_path: str = ATTEMPT_MANIFEST_PATH
    manifest: AttemptManifest | None = None
    manifest_digest: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema: str = ATTEMPT_MANIFEST_EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.status not in {"missing", "valid", "invalid"}:
            raise ValidationError("attempt manifest evidence status is invalid")

    def to_metadata(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": self.status,
            "source_path": self.source_path,
            "manifest_digest": self.manifest_digest,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "provenance": {
                "adapter": "github",
                "source": "pull_request_file_map",
                "path": self.source_path,
                "trust_level": self.manifest.trust_level if self.manifest else "self_attested",
            },
        }


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
        raise ScopeError("repository is outside the GitHub installation scope")
    if not verifier_ids:
        raise ValidationError("verifier_ids must contain at least one verifier id")
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
    file_map: Mapping[str, str] | None = None,
) -> Attempt:
    """Convert a GitHub pull request reference into an attempt for a contract."""

    if not installation.allows_repository(pull_request.repository_full_name):
        raise ScopeError("repository is outside the GitHub installation scope")
    if contract.repository != pull_request.repository_full_name:
        raise ScopeError("repository does not match task contract repository")
    if not patch_digest:
        raise ValidationError("patch_digest is required")
    if not worker_id:
        raise ValidationError("worker_id is required")
    manifest_evidence = parse_pull_request_attempt_manifest(
        file_map,
        contract=contract,
        pull_request=pull_request,
        worker_id=worker_id,
    )
    valid_manifest = manifest_evidence.manifest if manifest_evidence.status == "valid" else None
    return Attempt(
        id=valid_manifest.attempt_id if valid_manifest else new_id("attempt"),
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
            "faber_attempt_manifest": manifest_evidence.to_metadata(),
        },
    )


def parse_pull_request_attempt_manifest(
    file_map: Mapping[str, str] | None,
    *,
    contract: TaskContract,
    pull_request: GitHubPullRequestRef,
    worker_id: str,
) -> PullRequestAttemptManifestEvidence:
    """Parse optional `.faber/attempt.json` content from a fake PR file map."""

    content = _manifest_content(file_map)
    if content is None:
        return PullRequestAttemptManifestEvidence(status="missing")
    try:
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValidationError(".faber/attempt.json must contain a JSON object")
        manifest = AttemptManifest.from_dict(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        return PullRequestAttemptManifestEvidence(
            status="invalid",
            errors=[f"{ATTEMPT_MANIFEST_PATH}: {exc}"],
        )
    errors = _manifest_link_errors(
        manifest,
        contract=contract,
        pull_request=pull_request,
        worker_id=worker_id,
    )
    if errors:
        return PullRequestAttemptManifestEvidence(
            status="invalid",
            manifest=manifest,
            manifest_digest=manifest.digest(),
            errors=errors,
        )
    return PullRequestAttemptManifestEvidence(
        status="valid",
        manifest=manifest,
        manifest_digest=manifest.digest(),
    )


def _manifest_content(file_map: Mapping[str, str] | None) -> str | None:
    if file_map is None:
        return None
    for path, content in file_map.items():
        if path.replace("\\", "/") == ATTEMPT_MANIFEST_PATH:
            return content
    return None


def _manifest_link_errors(
    manifest: AttemptManifest,
    *,
    contract: TaskContract,
    pull_request: GitHubPullRequestRef,
    worker_id: str,
) -> list[str]:
    errors: list[str] = []
    expected_contract_digest = contract.digest()
    if manifest.task_contract_id != contract.id:
        errors.append("attempt manifest task_contract_id does not match task contract")
    if manifest.task_contract_digest != expected_contract_digest:
        errors.append("attempt manifest task_contract_digest does not match task contract")
    if manifest.base_revision != pull_request.base_revision:
        errors.append("attempt manifest base_revision does not match pull request")
    if manifest.candidate_revision != pull_request.head_revision:
        errors.append("attempt manifest candidate_revision does not match pull request")
    if manifest.worker_id != worker_id:
        errors.append("attempt manifest worker_id does not match adapter worker_id")
    return errors
