import pytest

from faber.adapters.github.markers import (
    parse_funded_issue_marker,
    render_funded_issue_marker,
)
from faber.adapters.github.templates import github_bug_template
from faber.budgets import FundingSource
from faber.errors import ValidationError
from faber.money import Money
from faber.templates import (
    BudgetPreset,
    TaskContractTemplate,
    bugfix_template,
    documentation_template,
    nixos_harness_template,
    rl_grade_template,
)

CREATED_AT = "2026-01-01T00:00:00Z"


def test_github_bug_template_renders_valid_task_contract() -> None:
    contract = github_bug_template().render(
        title="Fix funded issue marker parsing",
        description="Reject a digest mismatch.",
        repository="lk251/faber",
        created_at=CREATED_AT,
        contract_id="task-contract_template_github_bug",
    )

    assert contract.task_source == "github.issue"
    assert contract.verifier_ids == ["verifier.tests", "verifier.lint"]
    assert contract.environment["task_type"] == "bugfix"
    assert contract.digest().startswith("sha256:")


def test_nixos_harness_template_requires_platform_evidence() -> None:
    contract = nixos_harness_template().render(
        title="Package harness",
        description="Add a reproducible harness package.",
        created_at=CREATED_AT,
        contract_id="task-contract_template_nixos",
    )

    assert contract.environment["required_platforms"] == ["nixos"]
    assert contract.environment["require_lock_digest"] is True
    assert contract.trajectory_requirement["minimum_quality_tier"] == "trace"


def test_rl_grade_template_requires_trace_or_episode_tier() -> None:
    template = rl_grade_template()
    contract = template.render(
        title="Collect trace",
        description="Produce an RL-grade local episode.",
        created_at=CREATED_AT,
        contract_id="task-contract_template_rl",
    )

    assert contract.trajectory_requirement["minimum_quality_tier"] == "trace"
    assert contract.trajectory_requirement["require_rl_grade"] is True
    assert template.evidence_preset.allowed_quality_tiers == ["trace", "episode"]


def test_budget_preset_binds_to_work_budget_marker() -> None:
    contract = bugfix_template().render(
        title="Funded bugfix",
        description="Fix and verify the bug.",
        repository="lk251/faber",
        created_at=CREATED_AT,
        contract_id="task-contract_template_budget",
    )
    source = FundingSource(
        id="funding-source_template",
        created_at=CREATED_AT,
        source_type="fixture",
        display_name="Template fixture",
        currency="EUR",
        provider_ref="opaque:template",
    )
    preset = BudgetPreset(
        name="small-bugfix",
        amount=Money("EUR", 5_000),
        purpose_allocations={
            "solver_payout": Money("EUR", 4_000),
            "verifier_spend": Money("EUR", 500),
            "trace_quality_bonus": Money("EUR", 500),
        },
        trace_quality_bonus_policy={"minimum_quality_tier": "trace"},
    )
    budget = preset.create_budget(
        funding_source=source,
        target_kind="github.issue",
        target_ref="lk251/faber#55",
        verification_policy=bugfix_template().verification_policy,
        budget_id="work-budget_template",
        created_at=CREATED_AT,
    )
    marker = parse_funded_issue_marker(
        render_funded_issue_marker(
            contract,
            budget,
            funding_source_ref="opaque:template",
            budget_allocation_policy=preset.marker_binding(contract, budget),
            trace_quality_bonus_policy=preset.trace_quality_bonus_policy,
        )
    )

    assert marker.budget_allocation_policy["preset"] == "small-bugfix"
    assert marker.budget_allocation_policy["task_contract_digest"] == contract.digest()


def test_templates_are_data_only_and_invalid_shape_fails_clearly() -> None:
    assert documentation_template().to_dict()["template_kind"] == "documentation"

    with pytest.raises(ValidationError, match="unsupported template fields"):
        TaskContractTemplate.from_dict(
            {
                "name": "unsafe",
                "template_kind": "bugfix",
                "requirements": ["run arbitrary code"],
                "verification_policy": {},
                "evidence_preset": {},
                "render_code": "__import__('os').system('echo no')",
            }
        )
