"""Current external pilot package for Hermes Agent scheduler delivery issue #61631."""

from __future__ import annotations

from faber.budgets import FundingSource, RefundPolicy, WorkBudget
from faber.contracts import TaskContract
from faber.money import Money
from faber.sources import ExternalTaskReference
from faber.trajectory_quality import TrajectoryRequirement
from faber.verifiers import VerifierSpec

CREATED_AT = "2026-07-09T20:20:00Z"
REPOSITORY = "NousResearch/hermes-agent"
ISSUE_NUMBER = 61631
ISSUE_URL = f"https://github.com/{REPOSITORY}/issues/{ISSUE_NUMBER}"
TASK_CONTRACT_ID = "task-contract_hermes_scheduler_delivery_61631"
VERIFIER_IDS = [
    "verifier.hermes.scheduler-budget-delivery",
    "verifier.hermes.scheduler-regression",
    "verifier.hermes.faber-trajectory",
]


def scheduler_delivery_trajectory_requirement() -> TrajectoryRequirement:
    """Return the evidence policy for the external pilot."""

    return TrajectoryRequirement(
        id="trajectory-requirement_hermes_scheduler_delivery_61631",
        created_at=CREATED_AT,
        minimum_quality_tier="trace",
        require_training_eligible=False,
        require_rl_grade=False,
        full_payout_minimum_tier="trace",
        bonus_minimum_tier="episode",
        notes=(
            "A trace is required for the pilot evidence package. Training-use consent "
            "is separate from work acceptance. An authoritative verification receipt "
            "is always required for settlement."
        ),
    )


def scheduler_delivery_pilot_contract() -> TaskContract:
    """Return the proposed task contract, pending human and upstream approval."""

    source_reference = ExternalTaskReference(
        id="external-task-reference_hermes_issue_61631",
        source="github.issue",
        external_id=f"{REPOSITORY}#{ISSUE_NUMBER}",
        locator=ISSUE_URL,
        metadata={
            "surveyed_at": CREATED_AT,
            "state_at_selection": "open",
            "upstream_repository_role": "read_only_reference",
        },
    )
    return TaskContract(
        id=TASK_CONTRACT_ID,
        created_at=CREATED_AT,
        title="Preserve composed scheduler reports at turn-budget exhaustion",
        description=(
            "For Hermes Agent issue #61631, make scheduler completion handling agree "
            "with conversation-loop exit reasons so a complete composed report is "
            "delivered when the turn budget expires, while incomplete runs remain "
            "explicit failures."
        ),
        requirements=[
            "Re-check issue #61631 and ask before starting an upstream contribution.",
            "Set an explicit exit reason when the conversation loop expires its turn budget.",
            "Deliver a non-empty composed final response for the approved budget-exhausted path.",
            "Do not convert incomplete, empty, cancelled, or unrelated failed runs into success.",
            "Add deterministic tests for explicit exhaustion and loop-condition fall-through.",
            "Add a regression test proving incomplete runs still raise or report failure.",
            "Run the focused scheduler tests and the upstream Python test suite locally.",
            "Attach a redacted Faber trace meeting the declared trajectory requirement.",
            "Keep provider credentials, private prompts, network services, and real "
            "schedules out of tests.",
        ],
        verifier_ids=VERIFIER_IDS,
        task_source="github.issue",
        repository=REPOSITORY,
        source_reference=source_reference.to_dict(),
        trajectory_requirement=scheduler_delivery_trajectory_requirement().to_dict(),
        environment={
            "issue_number": ISSUE_NUMBER,
            "issue_url": ISSUE_URL,
            "reported_version": "0.17.0",
            "reported_platform": "macos",
            "language": "python",
            "production_credentials_required": False,
            "private_data_required": False,
            "external_services_required_for_verification": False,
            "external_writes_required_for_verification": False,
            "upstream_submission_requires_human_approval": True,
            "upstream_endorsement": False,
            "acceptance_criteria": [
                "Budget exhaustion has an explicit conversation-loop exit reason.",
                "A complete composed response is preserved and delivered on that path.",
                "Empty or incomplete output does not receive graceful-delivery treatment.",
                "Focused and upstream regression verifiers pass.",
                "The Faber trajectory evidence package validates.",
            ],
            "rejection_criteria": [
                "The change broadly suppresses scheduler failures.",
                "Tests require live providers, credentials, private data, or real schedules.",
                "The patch changes unrelated scheduling or conversation-loop behavior.",
                "Required trace evidence or an authoritative verification receipt is missing.",
            ],
            "upstream_contribution_path": [
                "Confirm the issue remains open and ask the reporter or maintainer before work.",
                "Prepare a focused fork branch with the smallest behavioral patch and tests.",
                "Open a conventional upstream PR that references issue #61631 and "
                "lists test commands.",
                "Keep Faber artifacts supplemental; do not require upstream to adopt Faber files.",
                "Respond to maintainer feedback and never imply endorsement or guaranteed funding.",
            ],
            "payment_provider_integrations": "out_of_scope",
        },
    )


def scheduler_delivery_pilot_verifier_specs() -> list[VerifierSpec]:
    """Return the proposed local verifier policy for the selected issue."""

    return [
        VerifierSpec(
            id="verifier-spec_hermes_scheduler_budget_delivery",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.scheduler-budget-delivery",
            name="Scheduler budget delivery behavior",
            version="1",
            description=(
                "Checks explicit and fall-through budget exhaustion, composed report "
                "delivery, and incomplete-run rejection without external services."
            ),
            command_template=[
                "python",
                "-m",
                "pytest",
                "tests/test_scheduler_budget_exhaustion.py",
            ],
            allowed_timeout_seconds=120,
        ),
        VerifierSpec(
            id="verifier-spec_hermes_scheduler_regression",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.scheduler-regression",
            name="Hermes Python regression suite",
            version="1",
            description="Runs the upstream Python tests after the focused behavior verifier.",
            command_template=["python", "-m", "pytest", "-q"],
            allowed_timeout_seconds=900,
        ),
        VerifierSpec(
            id="verifier-spec_hermes_faber_trajectory",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.faber-trajectory",
            name="Faber trajectory evidence",
            version="1",
            description=(
                "Validates the supplemental trajectory in the Faber Runner environment; "
                "this does not require upstream to install Faber."
            ),
            command_template=[
                "python",
                "-m",
                "faber.cli",
                "validate-trajectory",
                ".faber/trajectory.json",
            ],
            working_directory_policy="faber-runner",
            allowed_timeout_seconds=30,
        ),
    ]


def scheduler_delivery_pilot_budget() -> tuple[FundingSource, WorkBudget]:
    """Return a provider-free, non-committing budget placeholder for review."""

    source = FundingSource(
        id="funding-source_hermes_scheduler_pilot_placeholder",
        created_at=CREATED_AT,
        source_type="placeholder",
        display_name="Hermes scheduler pilot placeholder",
        currency="EUR",
        provider_ref=None,
        metadata={
            "funds_committed": False,
            "custody_created": False,
            "payment_provider_integrations": "out_of_scope",
        },
    )
    requirement = scheduler_delivery_trajectory_requirement()
    budget = WorkBudget(
        id="work-budget_hermes_scheduler_delivery_61631",
        created_at=CREATED_AT,
        funding_source_id=source.id,
        amount=Money("EUR", 50000),
        target_kind="github.issue",
        target_ref=f"{REPOSITORY}#{ISSUE_NUMBER}",
        verifier_policy={
            "authoritative_verifier_ids": VERIFIER_IDS[:2],
            "advisory_verifier_ids": VERIFIER_IDS[2:],
            "settlement_requires_accepted_receipt": True,
            "advisory_scores_are_authority": False,
        },
        purpose_allocations={
            "solver_payout": Money("EUR", 42000),
            "verifier_spend": Money("EUR", 4000),
            "review_budget": Money("EUR", 3000),
            "trace_quality_bonus": Money("EUR", 1000),
        },
        refund_policy=RefundPolicy(
            id="refund-policy_hermes_scheduler_pilot",
            created_at=CREATED_AT,
            on_rejected="refund_to_source",
            on_expired="manual_review",
            on_cancelled="manual_review",
            notes="Placeholder policy only; no funds or payment provider are connected.",
        ),
        metadata={
            "placeholder": True,
            "issue_url": ISSUE_URL,
            "funds_committed": False,
            "training_consent_affects_work_acceptance": False,
            "trace_quality_bonus_policy": {
                "minimum_quality_tier": requirement.bonus_minimum_tier,
                "requires_authoritative_verification": True,
                "requires_training_consent": False,
            },
            "payment_provider_integrations": "out_of_scope",
        },
    )
    return source, budget
