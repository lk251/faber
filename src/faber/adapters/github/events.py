"""GitHub evidence reference and event records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    strings: list[str] = []
    for item in value:
        if isinstance(item, str):
            strings.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            strings.append(item["name"])
    return strings


def _nested_string(payload: dict[str, object], *keys: str) -> str | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if isinstance(current, str):
        return current
    return None


@dataclass(frozen=True)
class GitHubRepositoryRef:
    full_name: str
    owner: str
    name: str
    default_branch: str | None = None

    @classmethod
    def from_full_name(
        cls,
        full_name: str,
        *,
        default_branch: str | None = None,
    ) -> GitHubRepositoryRef:
        parts = full_name.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError("repository full_name must be owner/name")
        return cls(
            full_name=full_name,
            owner=parts[0],
            name=parts[1],
            default_branch=default_branch,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> GitHubRepositoryRef:
        full_name = _nested_string(payload, "full_name")
        if not full_name:
            raise ValidationError("repository.full_name is required")
        return cls.from_full_name(
            full_name,
            default_branch=_nested_string(payload, "default_branch"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "full_name": self.full_name,
            "owner": self.owner,
            "name": self.name,
            "default_branch": self.default_branch,
        }


@dataclass(frozen=True)
class GitHubIssueRef:
    repository_full_name: str
    issue_number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    author_login: str | None = None
    html_url: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> GitHubIssueRef:
        repository = payload.get("repository")
        issue = payload.get("issue")
        if not isinstance(repository, dict) or not isinstance(issue, dict):
            raise ValidationError("payload.repository and payload.issue are required")
        repository_full_name = _nested_string(repository, "full_name")
        number = issue.get("number")
        title = issue.get("title")
        if not repository_full_name or not isinstance(number, int) or not isinstance(title, str):
            raise ValidationError("issue payload is missing repository, number, or title")
        body = issue.get("body")
        user = issue.get("user")
        author_login = user.get("login") if isinstance(user, dict) else None
        return cls(
            repository_full_name=repository_full_name,
            issue_number=number,
            title=title,
            body=body if isinstance(body, str) else "",
            labels=_string_list(issue.get("labels")),
            author_login=author_login if isinstance(author_login, str) else None,
            html_url=issue.get("html_url") if isinstance(issue.get("html_url"), str) else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_full_name": self.repository_full_name,
            "issue_number": self.issue_number,
            "title": self.title,
            "body": self.body,
            "labels": self.labels,
            "author_login": self.author_login,
            "html_url": self.html_url,
        }


@dataclass(frozen=True)
class GitHubPullRequestRef:
    repository_full_name: str
    pull_request_number: int
    title: str
    body: str
    author_login: str | None
    base_revision: str
    head_revision: str
    html_url: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> GitHubPullRequestRef:
        repository = payload.get("repository")
        pull_request = payload.get("pull_request")
        if not isinstance(repository, dict) or not isinstance(pull_request, dict):
            raise ValidationError("payload.repository and payload.pull_request are required")
        repository_full_name = _nested_string(repository, "full_name")
        number = pull_request.get("number")
        title = pull_request.get("title")
        base_revision = _nested_string(pull_request, "base", "sha")
        head_revision = _nested_string(pull_request, "head", "sha")
        if (
            not repository_full_name
            or not isinstance(number, int)
            or not isinstance(title, str)
            or not base_revision
            or not head_revision
        ):
            raise ValidationError("pull request payload is missing required fields")
        body = pull_request.get("body")
        user = pull_request.get("user")
        author_login = user.get("login") if isinstance(user, dict) else None
        return cls(
            repository_full_name=repository_full_name,
            pull_request_number=number,
            title=title,
            body=body if isinstance(body, str) else "",
            author_login=author_login if isinstance(author_login, str) else None,
            base_revision=base_revision,
            head_revision=head_revision,
            html_url=(
                pull_request.get("html_url")
                if isinstance(pull_request.get("html_url"), str)
                else None
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_full_name": self.repository_full_name,
            "pull_request_number": self.pull_request_number,
            "title": self.title,
            "body": self.body,
            "author_login": self.author_login,
            "base_revision": self.base_revision,
            "head_revision": self.head_revision,
            "html_url": self.html_url,
        }


@dataclass(frozen=True)
class GitHubEvent:
    event_name: str
    action: str | None
    delivery_id: str | None
    repository_full_name: str | None
    raw_payload_digest: str
    id: str = field(default_factory=lambda: new_id("github-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.github_event.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "event_name": self.event_name,
            "action": self.action,
            "delivery_id": self.delivery_id,
            "repository_full_name": self.repository_full_name,
            "raw_payload_digest": self.raw_payload_digest,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def normalize_github_event(
    event_name: str,
    payload: dict[str, object],
    *,
    delivery_id: str | None = None,
) -> GitHubEvent:
    if not event_name:
        raise ValidationError("event_name must be a non-empty string")
    repository = payload.get("repository")
    repository_full_name = None
    if isinstance(repository, dict):
        repository_full_name = _nested_string(repository, "full_name")
    action = payload.get("action")
    return GitHubEvent(
        event_name=event_name,
        action=action if isinstance(action, str) else None,
        delivery_id=delivery_id,
        repository_full_name=repository_full_name,
        raw_payload_digest=sha256_digest(payload),
    )
