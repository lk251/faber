from faber.trajectories import build_demo_trajectory


def test_trajectory_export_includes_training_context() -> None:
    trajectory = build_demo_trajectory()
    exported = trajectory.to_dict()
    learning = exported["learning_context"]

    assert exported["contract"]["schema"] == "faber.task_contract.v1"
    assert exported["attempt"]["worker_id"] == "worker_demo"
    assert exported["receipt"]["accepted"] is True
    assert exported["router_decision"]["policy_name"] == "baseline-rule-router-v1"
    assert exported["cost_metadata"]["compute_minor_units"] > 0
    assert exported["latency_metadata"]["work_seconds"] > 0
    assert exported["review_metadata"]["human_reviewed"] is False
    assert "supervised_learning" in learning
    assert "reinforcement_learning" in learning
    assert "router_training" in learning
