from dataclasses import replace

import pytest

from faber.contracts import TaskContract
from faber.money import Money
from faber.routing import route_task
from faber.trajectories import build_demo_trajectory
from faber.workers import (
    EnvironmentManifest,
    HarnessManifest,
    ModelManifest,
    WorkerProfile,
    WorkerRegistry,
    update_reputation_from_trajectory,
    worker_supported_platforms,
)


def test_worker_registry_registers_lists_and_resolves_workers() -> None:
    registry = WorkerRegistry()
    worker = WorkerProfile(
        id="worker_registry",
        created_at="2026-01-01T00:00:00Z",
        display_name="Registry Worker",
        capabilities=["python"],
    )

    registry.register(worker)

    assert registry.resolve(worker.id) == worker
    assert registry.list_workers() == [worker]


def test_worker_profile_digest_is_stable() -> None:
    left = WorkerProfile(
        id="worker_stable",
        created_at="2026-01-01T00:00:00Z",
        display_name="Stable Worker",
        capabilities=["python"],
        cost_model=Money("EUR", 1200),
    )
    right = WorkerProfile(
        id="worker_stable",
        created_at="2026-01-01T00:00:00Z",
        display_name="Stable Worker",
        capabilities=["python"],
        cost_model=Money("EUR", 1200),
    )

    assert left.digest() == right.digest()


def test_model_manifest_disclosure_modes() -> None:
    exact = ModelManifest(
        id="model-exact",
        created_at="2026-01-01T00:00:00Z",
        display_name="Exact model",
        disclosure_level="exact",
        model_ref="qwen3-coder-480b",
        model_family="qwen",
        provider_class="open-weight",
    )
    coarse = ModelManifest(
        id="model-coarse",
        created_at="2026-01-01T00:00:00Z",
        display_name="Coarse model",
        disclosure_level="coarse",
        model_family="frontier-code-model",
        provider_class="closed-provider",
    )
    private = ModelManifest(
        id="model-private",
        created_at="2026-01-01T00:00:00Z",
        display_name="Private model",
        disclosure_level="private",
        model_family="undisclosed",
        provider_class="undisclosed",
    )

    assert exact.to_dict()["model_ref"] == "qwen3-coder-480b"
    assert coarse.to_dict()["disclosure_level"] == "coarse"
    assert private.to_dict()["model_ref"] is None
    with pytest.raises(ValueError, match="exact model disclosure requires model_ref"):
        ModelManifest(
            display_name="Broken exact model",
            disclosure_level="exact",
            model_family="unknown",
            provider_class="unknown",
        )


def test_worker_metadata_manifest_digest_is_stable() -> None:
    left = WorkerProfile(
        id="worker_metadata_stable",
        created_at="2026-01-01T00:00:00Z",
        display_name="Metadata Stable",
        capabilities=["python"],
        supported_platforms=["nixos", "windows"],
        cost_model=Money("EUR", 2000),
        model_manifest=ModelManifest(
            id="model-stable",
            created_at="2026-01-01T00:00:00Z",
            display_name="Stable coarse model",
            disclosure_level="coarse",
            model_family="frontier-code-model",
            provider_class="closed-provider",
        ),
        harness_manifest=HarnessManifest(
            id="harness-stable",
            created_at="2026-01-01T00:00:00Z",
            display_name="Stable harness",
            harness_family="codex-cli",
            disclosure_level="coarse",
            supported_platforms=["nixos", "windows"],
        ),
        environment_manifest=EnvironmentManifest(
            id="environment-stable",
            created_at="2026-01-01T00:00:00Z",
            platform="nixos",
            architecture="x86_64",
            reproducibility_level="flake-lock",
        ),
    )
    right = replace(left)

    assert left.digest() == right.digest()
    assert left.model_manifest is not None
    assert left.model_manifest.digest() == right.model_manifest.digest()


def test_reputation_updates_from_accepted_and_rejected_trajectories() -> None:
    worker = WorkerProfile(
        id="worker_demo",
        created_at="2026-01-01T00:00:00Z",
        display_name="Demo Worker",
        capabilities=["python"],
    )
    accepted = build_demo_trajectory()
    rejected = replace(
        accepted,
        receipt=replace(accepted.receipt, accepted=False),
        settlement=None,
    )

    updated = update_reputation_from_trajectory(worker, accepted)
    updated = update_reputation_from_trajectory(updated, rejected)

    assert updated.reputation["accepted_attempts"] == 1
    assert updated.reputation["rejected_attempts"] == 1
    assert updated.reputation["verifier_failures"] == 1


def test_router_selects_best_value_worker_for_task_shape() -> None:
    registry = WorkerRegistry()
    cheap_docs = WorkerProfile(
        id="worker_docs",
        created_at="2026-01-01T00:00:00Z",
        display_name="Cheap docs worker",
        capabilities=["documentation"],
        supported_task_sources=["github.issue"],
        cost_model=Money("EUR", 500),
        reputation={"accepted_attempts": 2, "rejected_attempts": 0},
    )
    specialist = WorkerProfile(
        id="worker_python",
        created_at="2026-01-01T00:00:00Z",
        display_name="Python specialist",
        capabilities=["python", "sqlite"],
        supported_task_sources=["github.issue"],
        cost_model=Money("EUR", 2500),
        reputation={"accepted_attempts": 20, "rejected_attempts": 1},
    )
    registry.register(cheap_docs)
    registry.register(specialist)
    python_task = TaskContract(
        id="task-contract_python",
        created_at="2026-01-01T00:00:00Z",
        title="Fix Python SQLite store",
        description="Improve Python persistence.",
        requirements=["python", "sqlite"],
        verifier_ids=["verifier"],
        task_source="github.issue",
    )

    decision = route_task(python_task, registry)

    assert decision.selected_worker_id == "worker_python"
    assert decision.rejected_alternatives[0]["worker_id"] == "worker_docs"
    assert decision.policy_name == "baseline-value-router"
    assert decision.decision_factors["capability_matches"] == ["python", "sqlite"]


def test_router_does_not_choose_solely_by_cheapest_cost() -> None:
    registry = WorkerRegistry()
    registry.register(
        WorkerProfile(
            id="worker_cheap",
            created_at="2026-01-01T00:00:00Z",
            display_name="Cheap worker",
            capabilities=["misc"],
            cost_model=Money("EUR", 100),
            reputation={"accepted_attempts": 0, "rejected_attempts": 5},
        )
    )
    registry.register(
        WorkerProfile(
            id="worker_value",
            created_at="2026-01-01T00:00:00Z",
            display_name="Value worker",
            capabilities=["python"],
            cost_model=Money("EUR", 1500),
            reputation={"accepted_attempts": 10, "rejected_attempts": 0},
        )
    )
    task = TaskContract(
        id="task-contract_value",
        created_at="2026-01-01T00:00:00Z",
        title="Python task",
        description="Needs Python expertise.",
        requirements=["python"],
        verifier_ids=["verifier"],
    )

    decision = route_task(task, registry)

    assert decision.selected_worker_id == "worker_value"
    assert decision.estimated_cost.minor_units == 1500


def test_router_uses_platform_requirements() -> None:
    registry = WorkerRegistry()
    registry.register(
        WorkerProfile(
            id="worker_linux",
            created_at="2026-01-01T00:00:00Z",
            display_name="Linux worker",
            capabilities=["python"],
            supported_platforms=["linux"],
            cost_model=Money("EUR", 1000),
        )
    )
    registry.register(
        WorkerProfile(
            id="worker_windows",
            created_at="2026-01-01T00:00:00Z",
            display_name="Windows worker",
            capabilities=["python"],
            supported_platforms=["windows"],
            cost_model=Money("EUR", 2000),
        )
    )
    task = TaskContract(
        id="task-contract_windows",
        created_at="2026-01-01T00:00:00Z",
        title="Fix Windows path handling",
        description="Needs local Windows reproduction.",
        requirements=["python"],
        verifier_ids=["verifier"],
        environment={"required_platforms": ["windows"]},
    )

    decision = route_task(task, registry)

    assert decision.selected_worker_id == "worker_windows"
    assert decision.decision_factors["required_platforms"] == ["windows"]
    assert decision.decision_factors["platform_matches"] == ["windows"]


def test_nixos_specific_task_matches_nixos_worker() -> None:
    registry = WorkerRegistry()
    registry.register(
        WorkerProfile(
            id="worker_generic_linux",
            created_at="2026-01-01T00:00:00Z",
            display_name="Generic Linux worker",
            capabilities=["nix", "python"],
            supported_platforms=["linux"],
            cost_model=Money("EUR", 500),
        )
    )
    registry.register(
        WorkerProfile(
            id="worker_nixos",
            created_at="2026-01-01T00:00:00Z",
            display_name="NixOS worker",
            capabilities=["nix", "python"],
            cost_model=Money("EUR", 2000),
            harness_manifest=HarnessManifest(
                id="harness-nixos",
                created_at="2026-01-01T00:00:00Z",
                display_name="Nix harness",
                harness_family="agent-harness",
                disclosure_level="coarse",
                supported_platforms=["nixos"],
                trust_level="runner_attested",
            ),
        )
    )
    task = TaskContract(
        id="task-contract_nixos",
        created_at="2026-01-01T00:00:00Z",
        title="NixOS packaging fix",
        description="Requires NixOS reproduction evidence.",
        requirements=["nix", "nixos"],
        verifier_ids=["verifier"],
    )

    decision = route_task(task, registry)

    assert decision.selected_worker_id == "worker_nixos"
    assert worker_supported_platforms(registry.resolve("worker_nixos")) == ["nixos"]
    assert decision.decision_factors["required_platforms"] == ["nixos"]


def test_runner_attested_metadata_beats_self_attested_metadata_when_otherwise_equal() -> None:
    registry = WorkerRegistry()
    registry.register(
        WorkerProfile(
            id="worker_self_attested",
            created_at="2026-01-01T00:00:00Z",
            display_name="Self attested",
            capabilities=["python"],
            cost_model=Money("EUR", 1000),
            environment_manifest=EnvironmentManifest(
                id="environment-self",
                created_at="2026-01-01T00:00:00Z",
                platform="linux",
                architecture="x86_64",
                reproducibility_level="self-reported",
                trust_level="self_attested",
            ),
        )
    )
    registry.register(
        WorkerProfile(
            id="worker_runner_attested",
            created_at="2026-01-01T00:00:00Z",
            display_name="Runner attested",
            capabilities=["python"],
            cost_model=Money("EUR", 1000),
            environment_manifest=EnvironmentManifest(
                id="environment-runner",
                created_at="2026-01-01T00:00:00Z",
                platform="linux",
                architecture="x86_64",
                reproducibility_level="runner-observed",
                trust_level="runner_attested",
            ),
        )
    )
    task = TaskContract(
        id="task-contract_trust",
        created_at="2026-01-01T00:00:00Z",
        title="Python task",
        description="Needs Python changes.",
        requirements=["python"],
        verifier_ids=["verifier"],
        environment={"platform": "linux"},
    )

    decision = route_task(task, registry)

    assert decision.selected_worker_id == "worker_runner_attested"
    assert decision.decision_factors["metadata_trust_score"] == 25
