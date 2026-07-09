"""GitHub App installation scope modelling."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import require_mapping, require_non_empty_string, require_string_list


@dataclass(frozen=True)
class GitHubInstallation:
    """A selected-repository GitHub App installation."""

    installation_id: int
    account_login: str
    selected_repository_full_names: list[str]
    permissions: dict[str, object]
    id: str = field(default_factory=lambda: new_id("github-installation"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.GITHUB_INSTALLATION

    def __post_init__(self) -> None:
        if self.installation_id <= 0:
            raise ValidationError("installation_id must be positive")
        require_non_empty_string(self.account_login, "account_login")
        require_string_list(
            self.selected_repository_full_names,
            "selected_repository_full_names",
            allow_empty=False,
        )
        require_mapping(self.permissions, "permissions")

    def allows_repository(self, repository_full_name: str) -> bool:
        normalized = repository_full_name.casefold()
        return normalized in {
            repository.casefold() for repository in self.selected_repository_full_names
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "installation_id": self.installation_id,
            "account_login": self.account_login,
            "selected_repository_full_names": self.selected_repository_full_names,
            "permissions": self.permissions,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
