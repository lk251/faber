"""Fake funded-issue product boundary for GitHub text surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from faber.adapters.github.contracts import issue_to_task_contract
from faber.adapters.github.events import GitHubIssueRef
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.markers import render_funded_issue_marker
from faber.budgets import FundingSource, WorkBudget, issue_work_budget
from faber.contracts import TaskContract
from faber.money import Money


@dataclass(frozen=True)
class FundedIssueAdaptation:
    contract: TaskContract
    budget: WorkBudget
    marker_text: str


class FakeGitHubFundedIssueAdapter:
    """Create local protocol records; this adapter holds or transfers no funds."""

    def adapt(
        self,
        issue: GitHubIssueRef,
        *,
        installation: GitHubInstallation,
        verifier_ids: list[str],
        funding_source: FundingSource,
        amount: Money,
        purpose_allocations: dict[str, Money] | None = None,
        budget_allocation_policy: dict[str, object] | None = None,
        trace_quality_bonus_policy: dict[str, object] | None = None,
    ) -> FundedIssueAdaptation:
        contract = issue_to_task_contract(
            issue,
            installation=installation,
            verifier_ids=verifier_ids,
        )
        budget = issue_work_budget(
            repository=issue.repository_full_name,
            issue_number=issue.issue_number,
            funding_source=funding_source,
            amount=amount,
            verifier_policy={"required_verifier_ids": verifier_ids},
            purpose_allocations=purpose_allocations,
        )
        marker_text = render_funded_issue_marker(
            contract,
            budget,
            funding_source_ref=funding_source.provider_ref or funding_source.id,
            budget_allocation_policy=budget_allocation_policy
            or {"scope": "github.issue", "target_ref": budget.target_ref},
            trace_quality_bonus_policy=trace_quality_bonus_policy,
        )
        return FundedIssueAdaptation(
            contract=contract,
            budget=budget,
            marker_text=marker_text,
        )
