from faber.adapters.hermes.scheduler_delivery_pilot import (
    ISSUE_NUMBER,
    ISSUE_URL,
    REPOSITORY,
    scheduler_delivery_pilot_budget,
    scheduler_delivery_pilot_contract,
    scheduler_delivery_pilot_verifier_specs,
    scheduler_delivery_trajectory_requirement,
)
from faber.budgets import allocate_budget_to_task
from faber.trajectory_quality import TrajectoryRequirement
from faber.verifiers import VerifierRegistry


def test_scheduler_delivery_task_contract_validates() -> None:
    contract = scheduler_delivery_pilot_contract()

    assert contract.repository == REPOSITORY
    assert contract.environment["issue_number"] == ISSUE_NUMBER
    assert contract.source_reference["locator"] == ISSUE_URL
    assert contract.environment["upstream_endorsement"] is False
    assert contract.environment["production_credentials_required"] is False
    assert contract.digest().startswith("sha256:")


def test_scheduler_delivery_verifier_specs_validate() -> None:
    contract = scheduler_delivery_pilot_contract()
    specs = scheduler_delivery_pilot_verifier_specs()
    registry = VerifierRegistry()

    for spec in specs:
        registry.register(spec)

    assert [spec.verifier_id for spec in specs] == contract.verifier_ids
    assert specs[0].command() == [
        "python",
        "-m",
        "pytest",
        "tests/test_scheduler_budget_exhaustion.py",
    ]
    assert all(registry.resolve(spec.verifier_id) == spec for spec in specs)


def test_scheduler_delivery_evidence_requirement_validates() -> None:
    contract = scheduler_delivery_pilot_contract()
    requirement = scheduler_delivery_trajectory_requirement()
    parsed = TrajectoryRequirement.from_dict(contract.trajectory_requirement)

    assert parsed == requirement
    assert requirement.minimum_quality_tier == "trace"
    assert requirement.full_payout_minimum_tier == "trace"
    assert requirement.bonus_minimum_tier == "episode"
    assert requirement.require_training_eligible is False


def test_scheduler_delivery_work_budget_placeholder_validates() -> None:
    contract = scheduler_delivery_pilot_contract()
    source, budget = scheduler_delivery_pilot_budget()
    solver_allocation = allocate_budget_to_task(
        budget,
        contract,
        amount=budget.purpose_allocations["solver_payout"],
        purpose="solver_payout",
    )
    trace_bonus = allocate_budget_to_task(
        budget,
        contract,
        amount=budget.purpose_allocations["trace_quality_bonus"],
        purpose="trace_quality_bonus",
        trace_quality_bonus_policy=budget.metadata["trace_quality_bonus_policy"],
    )

    assert source.provider_ref is None
    assert source.metadata["funds_committed"] is False
    assert budget.metadata["placeholder"] is True
    assert budget.target_ref == f"{REPOSITORY}#{ISSUE_NUMBER}"
    assert sum(value.minor_units for value in budget.purpose_allocations.values()) == (
        budget.amount.minor_units
    )
    assert solver_allocation.task_contract_digest == contract.digest()
    assert trace_bonus.trace_quality_bonus_policy["minimum_quality_tier"] == "episode"
