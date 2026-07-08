"""Faber pilot fixture for a selected Hermes Agent external task."""

from __future__ import annotations

from faber.attempt_manifests import generate_attempt_manifest
from faber.budgets import FundingSource, RefundPolicy, WorkBudget
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.money import Money
from faber.traces import AttemptManifest
from faber.verifiers import VerifierSpec

CREATED_AT = "2026-07-08T00:00:00Z"
REPOSITORY = "NousResearch/hermes-agent"
ISSUE_NUMBER = 48628
ISSUE_URL = "https://github.com/NousResearch/hermes-agent/issues/48628"
TASK_CONTRACT_ID = "task-contract_hermes_nixos_lazy_deps_48628"
VERIFIER_IDS = [
    "verifier.hermes.lazy-deps.managed-install",
    "verifier.hermes.lazy-deps.docs",
    "verifier.hermes.faber-artifacts",
]


def lazy_deps_pilot_contract() -> TaskContract:
    """Return the selected external pilot task contract."""

    return TaskContract(
        id=TASK_CONTRACT_ID,
        created_at=CREATED_AT,
        title="Hermes managed-install lazy dependency startup guard",
        description=(
            "For NousResearch/hermes-agent issue #48628, prevent managed/read-only "
            "installs from repeatedly attempting doomed ensurepip or pip lazy "
            "dependency installs at startup while preserving clear remediation for "
            "unavailable optional backends."
        ),
        requirements=[
            "Re-check the upstream issue state before implementation.",
            "Add a managed/read-only install guard before lazy dependency install attempts.",
            "Do not run ensurepip or pip when the install cannot persist dependencies.",
            "Surface clear remediation for missing optional backend dependencies.",
            "Add objective tests for the managed/read-only path.",
            "Update user or developer docs if behavior or remediation changes.",
            "Attach .faber/attempt.json with at least Level 1 evidence.",
            "Prefer .faber/trace.jsonl with Level 2 evidence.",
        ],
        verifier_ids=VERIFIER_IDS,
        task_source="github.issue",
        repository=REPOSITORY,
        environment={
            "issue_number": ISSUE_NUMBER,
            "issue_url": ISSUE_URL,
            "required_platforms": ["nixos"],
            "minimum_reproducibility_level": "nix_flake",
            "evidence_level_required": 1,
            "evidence_level_preferred": 2,
            "acceptance_criteria": [
                "Managed/read-only installs avoid repeated doomed bootstrap attempts.",
                "Optional backend remediation remains clear to users.",
                "Local verifier specs pass on the candidate revision.",
                "Faber attempt manifest validates against this contract digest.",
            ],
            "rejection_criteria": [
                "Requires production credentials or private user data.",
                "Cannot be reproduced with local commands.",
                "Changes broad packaging behavior outside the issue scope.",
                "Missing required Faber evidence artifacts.",
            ],
            "upstream_contribution_path": [
                "Confirm issue #48628 is still useful upstream.",
                "Open a focused branch and PR referencing the issue.",
                "Include verifier commands and Faber artifacts as supplemental evidence.",
                "Accept maintainer feedback and avoid claiming endorsement.",
            ],
            "rollback_policy": [
                "If verifier specs cannot be made objective, pause the pilot.",
                "If upstream has already fixed the issue, select the next ranked candidate.",
                "If the guard regresses non-managed installs, reject the attempt.",
            ],
            "payment_provider_integrations": "out_of_scope",
        },
    )


def lazy_deps_pilot_verifier_specs() -> list[VerifierSpec]:
    """Return local verifier specs for the selected pilot."""

    return [
        VerifierSpec(
            id="verifier-spec_hermes_lazy_deps_managed_install",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.lazy-deps.managed-install",
            name="Managed install lazy dependency guard",
            version="1",
            description="Proves managed/read-only installs do not launch doomed bootstrap.",
            command_template=[
                "python",
                "-m",
                "pytest",
                "tests/test_lazy_deps_managed_install.py",
            ],
            allowed_timeout_seconds=120,
        ),
        VerifierSpec(
            id="verifier-spec_hermes_lazy_deps_docs",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.lazy-deps.docs",
            name="Managed install remediation docs",
            version="1",
            description="Proves user-facing remediation is documented.",
            command_template=["python", "-m", "pytest", "tests/test_lazy_deps_docs.py"],
            allowed_timeout_seconds=60,
        ),
        VerifierSpec(
            id="verifier-spec_hermes_faber_artifacts",
            created_at=CREATED_AT,
            verifier_id="verifier.hermes.faber-artifacts",
            name="Faber pilot artifacts",
            version="1",
            description="Validates .faber/attempt.json and optional trace evidence.",
            command_template=[
                "python",
                "-m",
                "faber.cli",
                "validate-attempt-manifest",
                ".faber/attempt.json",
            ],
            allowed_timeout_seconds=30,
        ),
    ]


def lazy_deps_pilot_budget() -> tuple[FundingSource, WorkBudget]:
    """Return a provider-free placeholder budget for the pilot."""

    source = FundingSource(
        id="funding-source_hermes_pilot_placeholder",
        created_at=CREATED_AT,
        source_type="placeholder",
        display_name="Hermes pilot placeholder budget",
        currency="EUR",
        provider_ref=None,
        metadata={"payment_provider_integrations": "out_of_scope"},
    )
    budget = WorkBudget(
        id="work-budget_hermes_pilot_48628",
        created_at=CREATED_AT,
        funding_source_id=source.id,
        amount=Money("EUR", 25000),
        target_kind="github.issue",
        target_ref=f"{REPOSITORY}#{ISSUE_NUMBER}",
        verifier_policy={
            "authoritative_verifier_ids": VERIFIER_IDS,
            "settlement_requires_accepted_receipt": True,
            "advisory_scores_are_authority": False,
        },
        purpose_allocations={
            "solver_payout": Money("EUR", 20000),
            "verifier_spend": Money("EUR", 3000),
            "review_budget": Money("EUR", 2000),
        },
        refund_policy=RefundPolicy(
            id="refund-policy_hermes_pilot",
            created_at=CREATED_AT,
            on_rejected="refund_to_source",
            on_expired="manual_review",
            on_cancelled="manual_review",
            notes="Placeholder only; no provider integration is in scope.",
        ),
        metadata={
            "placeholder": True,
            "issue_url": ISSUE_URL,
            "payment_provider_integrations": "out_of_scope",
        },
    )
    return source, budget


def lazy_deps_pilot_attempt_manifest() -> AttemptManifest:
    """Return an example attempt manifest matching the pilot contract digest."""

    contract = lazy_deps_pilot_contract()
    return generate_attempt_manifest(
        manifest_id="attempt-manifest_hermes_48628_example",
        redaction_policy_id="redaction-policy_hermes_48628_example",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id="attempt_hermes_48628_example",
        base_revision="upstream-base-revision",
        candidate_revision="candidate-pr-revision",
        worker_id="worker_external_solver_example",
        environment_digest=sha256_digest(
            {"repository": REPOSITORY, "issue_number": ISSUE_NUMBER, "environment": "declared"}
        ),
        evidence_level=1,
        model_disclosure="private",
        model_family="undisclosed",
        harness_family="generic-agent-harness",
        harness_version="example",
        runner_name="local",
        runner_version="example",
        platform="nixos",
        cost_minor_units=0,
        latency_seconds=300,
    )


def validate_lazy_deps_pilot_evidence(
    manifest: AttemptManifest,
    *,
    contract: TaskContract | None = None,
) -> list[str]:
    """Return evidence-policy errors for a pilot attempt manifest."""

    task_contract = contract or lazy_deps_pilot_contract()
    errors: list[str] = []
    if manifest.task_contract_id != task_contract.id:
        errors.append("attempt manifest task_contract_id does not match pilot contract")
    if manifest.task_contract_digest != task_contract.digest():
        errors.append("attempt manifest task_contract_digest does not match pilot contract")
    required_evidence = _evidence_requirement(task_contract, "evidence_level_required")
    if manifest.evidence_level < required_evidence:
        errors.append(
            f"attempt manifest evidence_level {manifest.evidence_level} is below "
            f"required level {required_evidence}"
        )
    if not manifest.redaction_policy.field_paths:
        errors.append("attempt manifest must declare redaction field paths")
    return errors


def _evidence_requirement(contract: TaskContract, field: str) -> int:
    value = contract.environment.get(field)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 1
