"""Helpers for adapting GitHub task evidence into contracts."""

from __future__ import annotations

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
