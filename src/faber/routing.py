"""Router decision records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money


@dataclass(frozen=True)
class RouterDecision:
    """A record of how Faber selected a worker or orchestration policy."""

    task_contract_id: str
    selected_worker_id: str
    rejected_alternatives: list[dict[str, object]]
    estimated_cost: Money
    expected_value: Money
    policy_name: str
    decision_factors: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("router-decision"))
    created_at: str = field(default_factory=utc_now)
    schema: str = "faber.router_decision.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "selected_worker_id": self.selected_worker_id,
            "rejected_alternatives": self.rejected_alternatives,
            "estimated_cost": self.estimated_cost.to_dict(),
            "expected_value": self.expected_value.to_dict(),
            "policy_name": self.policy_name,
            "decision_factors": self.decision_factors,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())
