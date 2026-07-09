from faber.digests import sha256_digest
from faber.scorecards import WorkerScorecardBuilder
from faber.trajectories import build_demo_trajectory


def _record(
    *,
    record_id: str,
    outcome: str,
    quality_tier: str,
    private: bool = False,
) -> dict[str, object]:
    record = build_demo_trajectory().to_dict()
    record["id"] = record_id
    record["outcome"] = outcome
    record["receipt"]["accepted"] = outcome == "accepted"
    record["contract"]["environment"]["task_type"] = "python-bugfix"
    record["contract"]["environment"]["customer_name"] = "Private Customer"
    record["private"] = private
    record["trajectory_quality"] = {
        "quality_tier": {"name": quality_tier},
        "is_rl_grade": quality_tier in {"trace", "episode"},
    }
    record["attempt_manifest"] = {
        "trust_level": "runner_attested",
        "environment_metadata": {"platform": "windows"},
    }
    if quality_tier in {"trace", "episode"}:
        record["trace_manifest"] = {
            "evidence_level": {"level": 2},
            "trace_event_count": 3,
            "trace_jsonl_digest": sha256_digest("trace"),
            "included_event_types": [
                "context.read",
                "tool.call",
                "verification.result",
            ],
        }
    return record


def test_scorecard_updates_from_accepted_trajectory() -> None:
    scorecard = WorkerScorecardBuilder("worker_demo").update(
        _record(record_id="trajectory_accepted", outcome="accepted", quality_tier="trace")
    ).build()
    family = scorecard.task_families["python-bugfix"]

    assert family.accepted_attempts == 1
    assert family.success_rate_milli == 1000
    assert family.total_cost_minor_units == 3_000
    assert family.total_reward_minor_units == 5_000


def test_scorecard_updates_from_rejected_trajectory() -> None:
    builder = WorkerScorecardBuilder("worker_demo")
    builder.update(
        _record(record_id="trajectory_accepted", outcome="accepted", quality_tier="trace")
    )
    builder.update(
        _record(record_id="trajectory_rejected", outcome="rejected", quality_tier="trace")
    )
    family = builder.build().task_families["python-bugfix"]

    assert family.accepted_attempts == 1
    assert family.rejected_attempts == 1
    assert family.success_rate_milli == 500


def test_trace_quality_affects_scorecard_separately_from_success() -> None:
    low = WorkerScorecardBuilder("worker_demo").update(
        _record(record_id="trajectory_pr", outcome="accepted", quality_tier="pr_only")
    ).build()
    high = WorkerScorecardBuilder("worker_demo").update(
        _record(record_id="trajectory_trace", outcome="accepted", quality_tier="trace")
    ).build()

    assert low.success_rate_milli == high.success_rate_milli == 1000
    assert low.average_trace_quality_milli < high.average_trace_quality_milli


def test_small_sample_size_and_uncertainty_are_represented() -> None:
    one = WorkerScorecardBuilder("worker_demo").update(
        _record(record_id="trajectory_one", outcome="accepted", quality_tier="trace")
    ).build()
    builder = WorkerScorecardBuilder("worker_demo")
    for index in range(4):
        builder.update(
            _record(
                record_id=f"trajectory_{index}",
                outcome="accepted",
                quality_tier="trace",
            )
        )
    four = builder.build()

    assert one.sample_size == 1
    assert one.uncertainty_milli == 1000
    assert four.sample_size == 4
    assert four.uncertainty_milli < one.uncertainty_milli


def test_private_fields_are_not_exported_publicly() -> None:
    record = _record(
        record_id="trajectory_private",
        outcome="accepted",
        quality_tier="trace",
        private=True,
    )
    record["worker_profile"]["operator_id"] = "private-operator"
    scorecard = WorkerScorecardBuilder("worker_demo").update(record).build()
    public = scorecard.to_dict(public=True)

    assert "private-operator" not in str(public)
    assert "Private Customer" not in str(public)
    assert public["self_attested_metadata"] == {}
    assert public["private_trajectory_count"] == 1
