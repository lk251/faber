from dataclasses import replace

from faber.adapters.hermes.pilot import (
    ISSUE_NUMBER,
    REPOSITORY,
    lazy_deps_pilot_attempt_manifest,
    lazy_deps_pilot_budget,
    lazy_deps_pilot_contract,
    lazy_deps_pilot_verifier_specs,
    validate_lazy_deps_pilot_evidence,
)
from faber.budgets import allocate_budget_to_task
from faber.traces import AttemptManifest
from faber.verifiers import VerifierRegistry


def test_pilot_task_contract_validates() -> None:
    contract = lazy_deps_pilot_contract()

    assert contract.id == "task-contract_hermes_nixos_lazy_deps_48628"
    assert contract.repository == REPOSITORY
    assert contract.environment["issue_number"] == ISSUE_NUMBER
    assert contract.environment["evidence_level_required"] == 1
    assert contract.environment["evidence_level_preferred"] == 2
    assert contract.environment["payment_provider_integrations"] == "out_of_scope"
    assert contract.digest().startswith("sha256:")


def test_pilot_verifier_specs_validate() -> None:
    contract = lazy_deps_pilot_contract()
    specs = lazy_deps_pilot_verifier_specs()
    registry = VerifierRegistry()

    for spec in specs:
        registry.register(spec)

    assert [spec.verifier_id for spec in specs] == contract.verifier_ids
    assert all(spec.command_template[:3] == ["python", "-m", "pytest"] for spec in specs[:2])
    assert registry.resolve("verifier.hermes.faber-artifacts").command() == [
        "python",
        "-m",
        "faber.cli",
        "validate-attempt-manifest",
        ".faber/attempt.json",
    ]


def test_pilot_work_budget_placeholder_validates() -> None:
    contract = lazy_deps_pilot_contract()
    source, budget = lazy_deps_pilot_budget()
    allocation = allocate_budget_to_task(
        budget,
        contract,
        amount=budget.purpose_allocations["solver_payout"],
        purpose="solver_payout",
    )

    assert source.provider_ref is None
    assert source.metadata["payment_provider_integrations"] == "out_of_scope"
    assert budget.target_ref == f"{REPOSITORY}#{ISSUE_NUMBER}"
    assert budget.amount.minor_units == 25000
    assert sum(amount.minor_units for amount in budget.purpose_allocations.values()) == 25000
    assert allocation.task_contract_digest == contract.digest()


def test_required_evidence_level_is_enforced() -> None:
    contract = lazy_deps_pilot_contract()
    manifest = lazy_deps_pilot_attempt_manifest()
    strict_contract = replace(
        contract,
        environment={**contract.environment, "evidence_level_required": 2},
    )
    strict_manifest = replace(manifest, task_contract_digest=strict_contract.digest())

    assert validate_lazy_deps_pilot_evidence(manifest, contract=contract) == []
    assert validate_lazy_deps_pilot_evidence(strict_manifest, contract=strict_contract) == [
        "attempt manifest evidence_level 1 is below required level 2"
    ]


def test_example_attempt_manifest_validates() -> None:
    manifest = lazy_deps_pilot_attempt_manifest()
    parsed = AttemptManifest.from_dict(manifest.to_dict())

    assert parsed.task_contract_id == lazy_deps_pilot_contract().id
    assert parsed.task_contract_digest == lazy_deps_pilot_contract().digest()
    assert parsed.evidence_level == 1
    assert validate_lazy_deps_pilot_evidence(parsed) == []
