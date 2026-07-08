"""In-memory fake GitHub client for adapter tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now


@dataclass(frozen=True)
class GitHubPublication:
    """A recorded GitHub-like side effect."""

    repository: str
    target_kind: str
    surface: str
    body: str
    payload: dict[str, object]
    target_number: int | None = None
    id: str = field(default_factory=lambda: new_id("github-publication"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.github_publication.v1"

    def stable_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "repository": self.repository,
            "target_kind": self.target_kind,
            "target_number": self.target_number,
            "surface": self.surface,
            "body": self.body,
            "payload": self.payload,
        }

    def digest(self) -> str:
        return sha256_digest(self.stable_payload())

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "repository": self.repository,
            "target_kind": self.target_kind,
            "target_number": self.target_number,
            "surface": self.surface,
            "body": self.body,
            "payload": self.payload,
        }
        data["publication_digest"] = self.digest()
        return data


@dataclass
class FakeGitHubClient:
    """A fake client that records intended GitHub side effects in memory."""

    publications: list[GitHubPublication] = field(default_factory=list)

    def create_issue_comment(
        self,
        *,
        repository: str,
        issue_number: int,
        body: str,
        payload: dict[str, object],
    ) -> GitHubPublication:
        publication = GitHubPublication(
            repository=repository,
            target_kind="issue",
            target_number=issue_number,
            surface="comment",
            body=body,
            payload=payload,
        )
        self.publications.append(publication)
        return publication

    def create_pull_request_comment(
        self,
        *,
        repository: str,
        pull_request_number: int,
        body: str,
        payload: dict[str, object],
    ) -> GitHubPublication:
        publication = GitHubPublication(
            repository=repository,
            target_kind="pull_request",
            target_number=pull_request_number,
            surface="comment",
            body=body,
            payload=payload,
        )
        self.publications.append(publication)
        return publication

    def create_check_record(
        self,
        *,
        repository: str,
        body: str,
        payload: dict[str, object],
    ) -> GitHubPublication:
        publication = GitHubPublication(
            repository=repository,
            target_kind="repository",
            target_number=None,
            surface="check_record",
            body=body,
            payload=payload,
        )
        self.publications.append(publication)
        return publication
