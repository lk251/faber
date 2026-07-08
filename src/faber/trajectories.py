"""Trajectory records and demo export."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.settlement import Settlement
from faber.validation import (
    ValidationError,
    require_mapping,
    require_non_empty_string,
    require_schema,
)
from faber.verifiers import VerifierRun
from faber.workers import WorkerProfile


@dataclass(frozen=True)
class Trajectory:
    """Training and audit record for a task attempt."""

    contract: TaskContract
    attempt: Attempt
    receipt: VerificationReceipt
    router_decision: RouterDecision
    cost_metadata: dict[str, object]
    latency_metadata: dict[str, object]
    review_metadata: dict[str, object]
    reward_metadata: dict[str, object] = field(default_factory=dict)
    settlement: Settlement | None = None
    worker_profile: WorkerProfile | None = None
    id: str = field(default_factory=lambda: new_id("trajectory"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRAJECTORY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRAJECTORY)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        if self.attempt.task_contract_id != self.contract.id:
            raise ValidationError("trajectory attempt must belong to trajectory contract")
        if self.receipt.task_contract_id != self.contract.id:
            raise ValidationError("trajectory receipt must belong to trajectory contract")
        if self.receipt.attempt_id != self.attempt.id:
            raise ValidationError("trajectory receipt must bind the trajectory attempt")
        require_mapping(self.cost_metadata, "cost_metadata")
        require_mapping(self.latency_metadata, "latency_metadata")
        require_mapping(self.review_metadata, "review_metadata")
        require_mapping(self.reward_metadata, "reward_metadata")

    def outcome(self) -> str:
        if self.receipt.accepted:
            return "accepted"
        return "rejected"

    def learning_context(self) -> dict[str, object]:
        return {
            "supervised_learning": {
                "input_fields": [
                    "contract",
                    "attempt.summary",
                    "attempt.tool_summaries",
                    "router_decision",
                    "worker_profile",
                ],
                "target_fields": [
                    "receipt.accepted",
                    "receipt.result_digest",
                    "attempt.candidate_revision",
                ],
            },
            "reinforcement_learning": {
                "reward": self.reward_metadata
                or (self.settlement.amount.to_dict() if self.settlement else None),
                "outcome": self.outcome(),
                "cost_metadata": self.cost_metadata,
                "latency_metadata": self.latency_metadata,
                "review_metadata": self.review_metadata,
            },
            "router_training": {
                "selected_worker_id": self.router_decision.selected_worker_id,
                "rejected_alternatives": self.router_decision.rejected_alternatives,
                "estimated_cost": self.router_decision.estimated_cost.to_dict(),
                "expected_value": self.router_decision.expected_value.to_dict(),
                "policy_name": self.router_decision.policy_name,
                "verified_outcome": self.outcome(),
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "contract": self.contract.to_dict(),
            "attempt": self.attempt.to_dict(),
            "receipt": self.receipt.to_dict(),
            "settlement": self.settlement.to_dict() if self.settlement else None,
            "router_decision": self.router_decision.to_dict(),
            "worker_profile": self.worker_profile.to_dict() if self.worker_profile else None,
            "cost_metadata": self.cost_metadata,
            "latency_metadata": self.latency_metadata,
            "review_metadata": self.review_metadata,
            "reward_metadata": self.reward_metadata,
            "outcome": self.outcome(),
            "learning_context": self.learning_context(),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def build_demo_trajectory() -> Trajectory:
    """Build a deterministic generic trajectory for local CLI smoke tests."""

    created_at = "2026-01-01T00:00:00Z"
    contract = TaskContract(
        id="task-contract_demo",
        created_at=created_at,
        title="Implement deterministic canonical JSON",
        description="Add stable JSON serialization and digest helpers to a small library.",
        requirements=[
            "Serialize mappings with stable key ordering.",
            "Use compact JSON separators.",
            "Return SHA-256 digests with a sha256: prefix.",
        ],
        verifier_ids=["verifier.local.unit-tests"],
        task_source="demo",
        repository="example/repository",
        environment={"language": "python", "runner": "local"},
        reward=Money("EUR", 5000),
    )
    worker = WorkerProfile(
        id="worker_demo",
        created_at=created_at,
        display_name="Demo Worker",
        capabilities=["python", "tests", "protocol-design"],
        reputation={"accepted_attempts": 12, "rejected_attempts": 1},
    )
    router_decision = RouterDecision(
        id="router-decision_demo",
        created_at=created_at,
        task_contract_id=contract.id,
        selected_worker_id=worker.id,
        rejected_alternatives=[
            {
                "worker_id": "worker_alternative",
                "reason": "higher estimated latency",
                "estimated_cost": Money("EUR", 6500).to_dict(),
            }
        ],
        estimated_cost=Money("EUR", 3000),
        expected_value=Money("EUR", 9000),
        policy_name="baseline-rule-router-v1",
        decision_factors={"skill_match": "high", "latency_risk": "low"},
    )
    attempt = Attempt(
        id="attempt_demo",
        created_at=created_at,
        task_contract_id=contract.id,
        worker_id=worker.id,
        base_revision="base-demo-revision",
        candidate_revision="candidate-demo-revision",
        summary="Implemented stable canonical serialization and digest helpers.",
        patch_digest=sha256_digest("demo patch"),
        tool_summaries=[
            {"tool": "pytest", "outcome": "passed"},
            {"tool": "ruff", "outcome": "passed"},
        ],
    )
    verifier_run = VerifierRun(
        id="verifier-run_demo",
        created_at=created_at,
        verifier_id="verifier.local.unit-tests",
        name="Local unit test verifier",
        version="1",
        command=["pytest"],
        passed=True,
        metrics={"tests": 7, "failures": 0},
        logs_digest=sha256_digest("demo logs"),
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
    settlement = Settlement.from_receipt(receipt, Money("EUR", 5000)).mark_paid(
        receipt,
        transaction_ref="demo-local-settlement",
        paid_at=created_at,
    )
    return Trajectory(
        id="trajectory_demo",
        created_at=created_at,
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        settlement=settlement,
        router_decision=router_decision,
        worker_profile=worker,
        cost_metadata={
            "currency": "EUR",
            "compute_minor_units": 1200,
            "review_minor_units": 800,
            "platform_minor_units": 1000,
        },
        latency_metadata={
            "queue_seconds": 30,
            "work_seconds": 600,
            "verification_seconds": 20,
        },
        review_metadata={
            "human_reviewed": False,
            "review_friction": "none",
            "notes": "Demo trajectory for local protocol export.",
        },
        reward_metadata={"currency": "EUR", "reward_minor_units": 5000},
    )
