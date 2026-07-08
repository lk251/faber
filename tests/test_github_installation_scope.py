from faber.adapters.github.installation import GitHubInstallation


def test_github_installation_allows_only_selected_repositories() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read", "pull_requests": "read"},
        created_at="2026-01-01T00:00:00Z",
    )

    assert installation.allows_repository("lk251/faber")
    assert installation.allows_repository("LK251/FABER")
    assert not installation.allows_repository("lk251/agent-bounty-market")
    assert installation.to_dict()["permissions"]["issues"] == "read"
