from faber.money import Money
from faber.routing import RouterDecision


def test_router_decision_records_worker_alternatives_cost_value_and_policy() -> None:
    decision = RouterDecision(
        id="router-decision_test",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id="task-contract_test",
        selected_worker_id="worker_selected",
        rejected_alternatives=[{"worker_id": "worker_rejected", "reason": "lower expected value"}],
        estimated_cost=Money("EUR", 2000),
        expected_value=Money("EUR", 6000),
        policy_name="baseline-rule-router-v1",
    )

    exported = decision.to_dict()

    assert exported["selected_worker_id"] == "worker_selected"
    assert exported["rejected_alternatives"][0]["worker_id"] == "worker_rejected"
    assert exported["estimated_cost"] == {"currency": "EUR", "minor_units": 2000}
    assert exported["expected_value"] == {"currency": "EUR", "minor_units": 6000}
    assert exported["policy_name"] == "baseline-rule-router-v1"
