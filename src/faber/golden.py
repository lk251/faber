"""Local golden path helpers."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.events import (
    attempt_submitted,
    contract_created,
    receipt_issued,
    settlement_created,
    settlement_paid,
    trajectory_exported,
    verifier_run_recorded,
)
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.runner.local import (
    LocalVerifierRunner,
    RunnerPolicy,
    new_local_verifier_invocation_nonce,
)
from faber.settlement import Settlement
from faber.store import (
    export_trajectory,
    save_attempt,
    save_lifecycle_event,
    save_record,
    save_settlement,
    save_task_contract,
    save_trajectory,
    save_verification_receipt,
    save_verifier_run,
    save_worker_profile,
)
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec
from faber.workers import WorkerProfile

CREATED_AT = "2026-01-01T00:00:00Z"


def demo_contract() -> TaskContract:
    return TaskContract(
        id="task-contract_golden",
        created_at=CREATED_AT,
        title="Implement a deterministic local verifier receipt",
        description="Create a small local attempt and verify it with an approved runner.",
        requirements=["python", "local verifier", "receipt"],
        verifier_ids=["verifier.golden.local"],
        task_source="local.demo",
        repository="examples/golden_path",
        reward=Money("EUR", 2500),
    )


def demo_worker() -> WorkerProfile:
    return WorkerProfile(
        id="worker_golden",
        created_at=CREATED_AT,
        display_name="Golden Path Worker",
        capabilities=["python", "local verifier"],
        supported_task_sources=["local.demo"],
        cost_model=Money("EUR", 1000),
        reputation={"accepted_attempts": 3, "rejected_attempts": 0},
    )


def demo_verifier_spec() -> VerifierSpec:
    return VerifierSpec(
        id="verifier-spec_golden",
        created_at=CREATED_AT,
        verifier_id="verifier.golden.local",
        name="Golden local verifier",
        version="1",
        description="A deterministic local verifier for the golden path.",
        command_template=[
            sys.executable,
            "-c",
            'print(\'{"metrics":{"golden_path_checks":1}}\')',
        ],
        allowed_timeout_seconds=30,
    )


def demo_attempt() -> Attempt:
    contract = demo_contract()
    worker = demo_worker()
    return Attempt(
        id="attempt_golden",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id=worker.id,
        base_revision="golden-base",
        candidate_revision="golden-candidate",
        summary="Produced the deterministic golden path candidate.",
        patch_digest=sha256_digest("golden path patch"),
        metadata={"example_path": "examples/golden_path"},
    )


def create_demo_contract(store_path: str | Path) -> TaskContract:
    contract = demo_contract()
    save_task_contract(store_path, contract)
    save_lifecycle_event(store_path, contract_created(contract))
    return contract


def register_demo_worker(store_path: str | Path) -> WorkerProfile:
    worker = demo_worker()
    save_worker_profile(store_path, worker)
    return worker


def register_demo_verifier(store_path: str | Path) -> VerifierSpec:
    spec = demo_verifier_spec()
    save_record(store_path, "verifier_spec", spec)
    return spec


def submit_demo_attempt(store_path: str | Path) -> Attempt:
    create_demo_contract(store_path)
    register_demo_worker(store_path)
    attempt = demo_attempt()
    save_attempt(store_path, attempt)
    save_lifecycle_event(store_path, attempt_submitted(attempt))
    return attempt


def run_demo_verifier(
    store_path: str | Path, *, working_directory: str | Path | None = None
) -> VerifierRun:
    register_demo_verifier(store_path)
    registry = VerifierRegistry()
    spec = demo_verifier_spec()
    registry.register(spec)
    cwd = Path(working_directory or Path.cwd()).resolve()
    runner = LocalVerifierRunner(
        registry,
        policy=RunnerPolicy(allowed_working_directory_root=str(cwd), timeout_seconds=30),
    )
    verifier_run = runner.run(
        spec.verifier_id,
        working_directory=cwd,
        invocation_nonce=new_local_verifier_invocation_nonce(),
        invocation_context_digest=sha256_digest(
            {
                "schema": "faber.golden_verifier_invocation_context.v1",
                "verifier_registry_digest": registry.digest(),
                "verifier_id": spec.verifier_id,
                "working_directory": str(cwd),
                "runner_policy_digest": runner.runner_policy_digest,
            }
        ),
    ).verifier_run
    verifier_run = VerifierRun(
        id="verifier-run_golden",
        created_at=CREATED_AT,
        verifier_id=verifier_run.verifier_id,
        name=verifier_run.name,
        version=verifier_run.version,
        command=verifier_run.command,
        passed=verifier_run.passed,
        metrics={"golden_path_checks": 1},
        failure_reasons=verifier_run.failure_reasons,
        logs_digest=verifier_run.logs_digest,
        metadata={
            "runner": "local",
            "approved_verifier_spec_digest": spec.digest(),
            "stdout_digest": verifier_run.metadata.get("stdout_digest", ""),
            "stderr_digest": verifier_run.metadata.get("stderr_digest", ""),
            "runner_policy_digest": verifier_run.metadata.get("runner_policy_digest", ""),
        },
    )
    save_verifier_run(store_path, verifier_run)
    save_lifecycle_event(store_path, verifier_run_recorded(verifier_run))
    return verifier_run


def issue_demo_receipt(store_path: str | Path) -> VerificationReceipt:
    contract = create_demo_contract(store_path)
    attempt = submit_demo_attempt(store_path)
    verifier_run = run_demo_verifier(store_path)
    receipt = replace(
        VerificationReceipt.from_verifier_run(contract, attempt, verifier_run),
        id="verification-receipt_golden",
        created_at=CREATED_AT,
    )
    save_verification_receipt(store_path, receipt)
    save_lifecycle_event(store_path, receipt_issued(receipt))
    return receipt


def settle_demo(store_path: str | Path) -> Settlement:
    receipt = issue_demo_receipt(store_path)
    settlement = Settlement.from_receipt(receipt, Money("EUR", 2500)).mark_paid(
        receipt,
        transaction_ref="golden-local-settlement",
        paid_at=CREATED_AT,
    )
    settlement = replace(settlement, id="settlement_golden", created_at=CREATED_AT)
    save_settlement(store_path, settlement)
    save_lifecycle_event(store_path, settlement_created(settlement))
    save_lifecycle_event(store_path, settlement_paid(settlement))
    return settlement


def export_demo_trajectory(store_path: str | Path, out_path: str | Path) -> Trajectory:
    contract = create_demo_contract(store_path)
    worker = register_demo_worker(store_path)
    attempt = submit_demo_attempt(store_path)
    verifier_run = run_demo_verifier(store_path)
    receipt = replace(
        VerificationReceipt.from_verifier_run(contract, attempt, verifier_run),
        id="verification-receipt_golden",
        created_at=CREATED_AT,
    )
    settlement = Settlement.from_receipt(receipt, Money("EUR", 2500)).mark_paid(
        receipt,
        transaction_ref="golden-local-settlement",
        paid_at=CREATED_AT,
    )
    settlement = replace(settlement, id="settlement_golden", created_at=CREATED_AT)
    router_decision = RouterDecision(
        id="router-decision_golden",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        selected_worker_id=worker.id,
        rejected_alternatives=[],
        estimated_cost=Money("EUR", 1000),
        expected_value=Money("EUR", 4000),
        policy_name="golden-path-router",
    )
    trajectory = Trajectory(
        id="trajectory_golden",
        created_at=CREATED_AT,
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        settlement=settlement,
        router_decision=router_decision,
        worker_profile=worker,
        cost_metadata={"compute_minor_units": 400, "review_minor_units": 100},
        latency_metadata={"work_seconds": 30, "verification_seconds": 1},
        review_metadata={"human_reviewed": False, "review_friction": "none"},
    )
    save_verification_receipt(store_path, receipt)
    save_settlement(store_path, settlement)
    save_trajectory(store_path, trajectory)
    save_lifecycle_event(store_path, trajectory_exported(trajectory))
    export_trajectory(store_path, trajectory.id, out_path)
    return trajectory


def run_golden_path(store_path: str | Path, out_path: str | Path) -> dict[str, str]:
    contract = create_demo_contract(store_path)
    worker = register_demo_worker(store_path)
    verifier = register_demo_verifier(store_path)
    attempt = submit_demo_attempt(store_path)
    verifier_run = run_demo_verifier(store_path)
    receipt = replace(
        VerificationReceipt.from_verifier_run(contract, attempt, verifier_run),
        id="verification-receipt_golden",
        created_at=CREATED_AT,
    )
    save_verification_receipt(store_path, receipt)
    save_lifecycle_event(store_path, receipt_issued(receipt))
    settlement = Settlement.from_receipt(receipt, Money("EUR", 2500)).mark_paid(
        receipt,
        transaction_ref="golden-local-settlement",
        paid_at=CREATED_AT,
    )
    settlement = replace(settlement, id="settlement_golden", created_at=CREATED_AT)
    save_settlement(store_path, settlement)
    save_lifecycle_event(store_path, settlement_created(settlement))
    trajectory = export_demo_trajectory(store_path, out_path)
    return {
        "contract_id": contract.id,
        "worker_id": worker.id,
        "verifier_id": verifier.verifier_id,
        "attempt_id": attempt.id,
        "receipt_id": receipt.id,
        "settlement_id": settlement.id,
        "trajectory_id": trajectory.id,
        "trajectory_path": str(out_path),
        "trajectory_digest": trajectory.digest(),
        "next_step": (
            f"Run `python -m faber.cli validate-trajectory {out_path}` to inspect "
            "the exported evidence."
        ),
    }
