from dataclasses import replace

from faber.contracts import TaskContract
from faber.money import Money
from faber.routing import route_task
from faber.trajectories import build_demo_trajectory
from faber.workers import WorkerProfile, WorkerRegistry, update_reputation_from_trajectory


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
