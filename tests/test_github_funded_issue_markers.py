import pytest

from faber.adapters.github.events import GitHubIssueRef
from faber.adapters.github.funded_issues import FakeGitHubFundedIssueAdapter
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.markers import (
    parse_funded_issue_marker,
    render_funded_issue_marker,
)
from faber.budgets import FundingSource, RefundPolicy, WorkBudget
from faber.contracts import TaskContract
from faber.money import Money

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_funded_marker",
        created_at=CREATED_AT,
        title="Funded issue",
        description="Implement verified work.",
        requirements=["Pass verification"],
        verifier_ids=["verifier.local"],
        task_source="github.issue",
        repository="lk251/faber",
    )


def _source() -> FundingSource:
    return FundingSource(
        id="funding-source_funded_marker",
        created_at=CREATED_AT,
        source_type="fake",
        display_name="Fake local funding",
        currency="EUR",
        provider_ref="opaque:fixture",
    )


def _budget() -> WorkBudget:
    return WorkBudget(
        id="work-budget_funded_marker",
        created_at=CREATED_AT,
        funding_source_id=_source().id,
        amount=Money("EUR", 5_000),
        target_kind="github.issue",
        target_ref="lk251/faber#6",
        verifier_policy={"required_verifier_ids": ["verifier.local"]},
        purpose_allocations={
            "solver_payout": Money("EUR", 4_000),
            "verifier_spend": Money("EUR", 500),
            "trace_quality_bonus": Money("EUR", 500),
        },
        refund_policy=RefundPolicy(
            id="refund-policy_funded_marker",
            created_at=CREATED_AT,
        ),
    )


def test_render_and_parse_funded_issue_marker() -> None:
    text = render_funded_issue_marker(
        _contract(),
        _budget(),
        funding_source_ref="opaque:fixture",
        budget_allocation_policy={"scope": "issue"},
        trace_quality_bonus_policy={"minimum_quality_tier": "trace"},
    )

    marker = parse_funded_issue_marker(f"Intro\n{text}\nOutro")

    assert marker.contract_id == _contract().id
    assert marker.budget_id == _budget().id
    assert marker.target_kind == "github.issue"
    assert marker.verifier_spend_budget == Money("EUR", 500).to_dict()
    assert marker.trace_quality_bonus_policy["minimum_quality_tier"] == "trace"


def test_funded_issue_marker_detects_digest_mismatch() -> None:
    text = render_funded_issue_marker(
        _contract(),
        _budget(),
        funding_source_ref="opaque:fixture",
    )
    tampered = text.replace("Implement verified work.", "Tampered work.")

    with pytest.raises(ValueError, match="contract digest mismatch"):
        parse_funded_issue_marker(tampered)


def test_fake_github_issue_becomes_contract_and_work_budget() -> None:
    issue = GitHubIssueRef(
        repository_full_name="lk251/faber",
        issue_number=6,
        title="Funded adapter issue",
        body="Build the adapter boundary.",
        author_login="maintainer",
    )
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read"},
    )

    result = FakeGitHubFundedIssueAdapter().adapt(
        issue,
        installation=installation,
        verifier_ids=["verifier.local"],
        funding_source=_source(),
        amount=Money("EUR", 5_000),
        purpose_allocations={
            "solver_payout": Money("EUR", 4_000),
            "verifier_spend": Money("EUR", 500),
            "trace_quality_bonus": Money("EUR", 500),
        },
        trace_quality_bonus_policy={"minimum_quality_tier": "trace"},
    )

    assert result.contract.task_source == "github.issue"
    assert result.budget.target_ref == "lk251/faber#6"
    assert parse_funded_issue_marker(result.marker_text).budget_digest == result.budget.digest()


def test_duplicate_identical_marker_is_idempotent() -> None:
    marker = render_funded_issue_marker(
        _contract(),
        _budget(),
        funding_source_ref="opaque:fixture",
    )

    parsed = parse_funded_issue_marker(f"{marker}\n{marker}")

    assert parsed.budget_id == _budget().id


def test_budget_marker_never_authorizes_settlement() -> None:
    marker = parse_funded_issue_marker(
        render_funded_issue_marker(
            _contract(),
            _budget(),
            funding_source_ref="opaque:fixture",
        )
    )

    assert marker.settlement_authority is False
