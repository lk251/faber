from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.cli import main
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.events import (
    attempt_submitted,
    contract_created,
    receipt_issued,
    settlement_created,
    trajectory_exported,
    verifier_run_recorded,
)
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.settlement import Settlement
from faber.store import (
    export_trajectory,
    init_local_store,
    list_lifecycle_events,
    load_record,
    save_attempt,
    save_lifecycle_event,
    save_record,
    save_router_decision,
    save_settlement,
    save_task_contract,
    save_trajectory,
    save_verification_receipt,
    save_verifier_run,
    save_worker_profile,
    store_summary,
)
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRun
from faber.workers import WorkerProfile


def _records() -> tuple[
    TaskContract,
    Attempt,
    VerifierRun,
    VerificationReceipt,
    Settlement,
    WorkerProfile,
    RouterDecision,
    Trajectory,
]:
    created_at = "2026-01-01T00:00:00Z"
    contract = TaskContract(
        id="task-contract_store",
        created_at=created_at,
        title="Store task",
        description="Persist records.",
        requirements=["save records"],
        verifier_ids=["verifier.store"],
        repository="lk251/faber",
        reward=Money("EUR", 1000),
    )
    attempt = Attempt(
        id="attempt_store",
        created_at=created_at,
        task_contract_id=contract.id,
        worker_id="worker_store",
        base_revision="base",
        candidate_revision="candidate",
        summary="Persisted implementation.",
        patch_digest=sha256_digest("patch"),
    )
    verifier_run = VerifierRun(
        id="verifier-run_store",
        created_at=created_at,
        verifier_id="verifier.store",
        name="Store verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=True,
        metrics={"tests": 1},
        logs_digest=sha256_digest("logs"),
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
    settlement = Settlement.from_receipt(receipt, Money("EUR", 1000)).mark_paid(
        receipt,
        transaction_ref="store-test",
        paid_at=created_at,
    )
    worker = WorkerProfile(
        id="worker_store",
        created_at=created_at,
        display_name="Store Worker",
        capabilities=["python"],
    )
    router_decision = RouterDecision(
        id="router-decision_store",
        created_at=created_at,
        task_contract_id=contract.id,
        selected_worker_id=worker.id,
        rejected_alternatives=[],
        estimated_cost=Money("EUR", 500),
        expected_value=Money("EUR", 1500),
        policy_name="store-test-router",
    )
    trajectory = Trajectory(
        id="trajectory_store",
        created_at=created_at,
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        settlement=settlement,
        router_decision=router_decision,
        worker_profile=worker,
        cost_metadata={"currency": "EUR", "compute_minor_units": 100},
        latency_metadata={"work_seconds": 10},
        review_metadata={"human_reviewed": False},
    )
    return contract, attempt, verifier_run, receipt, settlement, worker, router_decision, trajectory


def test_init_local_store_creates_schema(tmp_path: Path) -> None:
    store_path = init_local_store(tmp_path / ".faber" / "faber.sqlite3")

    assert store_path.exists()
    assert store_summary(store_path)["schema_version"] == 1


def test_save_and_load_each_major_record_type(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    contract, attempt, verifier_run, receipt, settlement, worker, router_decision, trajectory = (
        _records()
    )

    save_task_contract(store_path, contract)
    save_attempt(store_path, attempt)
    save_verifier_run(store_path, verifier_run)
    save_verification_receipt(store_path, receipt)
    save_settlement(store_path, settlement)
    save_worker_profile(store_path, worker)
    save_router_decision(store_path, router_decision)
    save_trajectory(store_path, trajectory)

    assert load_record(store_path, "task_contract", contract.id)["title"] == "Store task"
    assert load_record(store_path, "attempt", attempt.id)["candidate_revision"] == "candidate"
    assert load_record(store_path, "verifier_run", verifier_run.id)["passed"] is True
    assert load_record(store_path, "verification_receipt", receipt.id)["accepted"] is True
    assert load_record(store_path, "settlement", settlement.id)["status"] == "paid"
    assert load_record(store_path, "worker_profile", worker.id)["display_name"] == "Store Worker"
    assert (
        load_record(store_path, "router_decision", router_decision.id)["selected_worker_id"]
        == worker.id
    )
    assert load_record(store_path, "trajectory", trajectory.id)["outcome"] == "accepted"


def test_idempotent_save_and_conflicting_record_detection(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    contract = _records()[0]

    first = save_task_contract(store_path, contract)
    second = save_task_contract(store_path, contract)

    assert first.inserted is True
    assert second.inserted is False
    assert store_summary(store_path)["record_counts"]["task_contract"] == 1

    changed = TaskContract(
        id=contract.id,
        title="Changed",
        description=contract.description,
        requirements=contract.requirements,
        verifier_ids=contract.verifier_ids,
    )
    with pytest.raises(ValidationError, match="different digest"):
        save_record(store_path, "task_contract", changed)


def test_lifecycle_events_are_append_only_and_ordered(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    contract, attempt, verifier_run, receipt, settlement, _, _, trajectory = _records()

    for event in [
        contract_created(contract),
        attempt_submitted(attempt),
        verifier_run_recorded(verifier_run),
        receipt_issued(receipt),
        settlement_created(settlement),
        trajectory_exported(trajectory),
    ]:
        save_lifecycle_event(store_path, event)

    events = list_lifecycle_events(store_path)

    assert [event["sequence"] for event in events] == [1, 2, 3, 4, 5, 6]
    assert [event["event_type"] for event in events] == [
        "contract.created",
        "attempt.submitted",
        "verifier_run.recorded",
        "receipt.issued",
        "settlement.created",
        "trajectory.exported",
    ]
    assert events[0]["payload"]["payload"]["record_digest"] == contract.digest()


def test_store_summary_and_cli_outputs(tmp_path: Path, capsys) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    contract, *_ = _records()
    save_task_contract(store_path, contract)

    assert main(["store-summary", "--path", str(store_path)]) == 0
    summary_output = capsys.readouterr().out
    assert '"task_contract":1' in summary_output

    assert main(["list-contracts", "--path", str(store_path)]) == 0
    list_output = capsys.readouterr().out
    assert "Store task" in list_output


def test_export_trajectory_from_persisted_record(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    trajectory = _records()[-1]
    save_trajectory(store_path, trajectory)

    out_path = export_trajectory(store_path, trajectory.id, tmp_path / "trajectory.json")

    assert out_path.exists()
    assert '"id":"trajectory_store"' in out_path.read_text(encoding="utf-8")


def test_show_trajectory_cli(tmp_path: Path, capsys) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    trajectory = _records()[-1]
    save_trajectory(store_path, trajectory)

    assert main(["show-trajectory", trajectory.id, "--path", str(store_path)]) == 0

    assert "trajectory_store" in capsys.readouterr().out
