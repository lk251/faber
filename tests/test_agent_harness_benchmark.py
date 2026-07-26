from pathlib import Path

from faber.benchmarks import (
    BENCHMARK_ID,
    agent_harness_benchmark,
    agent_harness_dataset_records,
    benchmark_flake_exists,
    validate_agent_harness_benchmark,
)
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.traces import AttemptManifest, TraceEvent


def test_benchmark_fixtures_validate() -> None:
    fixtures = agent_harness_benchmark()

    assert len(fixtures) == 3
    assert validate_agent_harness_benchmark(fixtures) == []
    assert benchmark_flake_exists()
    assert {
        fixture.contract.environment["dev_environment"]["flake_path"] for fixture in fixtures
    } == {"flake.nix"}
    assert all(fixture.contract.environment["external_services"] == [] for fixture in fixtures)


def test_verifier_commands_are_represented() -> None:
    fixtures = agent_harness_benchmark()

    for fixture in fixtures:
        assert fixture.verifier_spec.verifier_id in fixture.contract.verifier_ids
        assert fixture.verifier_spec.command_template[:3] == ["python", "-m", "pytest"]
        assert fixture.verifier_spec.allowed_timeout_seconds > 0
        assert fixture.verifier_spec.command() == fixture.verifier_spec.command_template


def test_expected_manifests_and_traces_validate() -> None:
    fixtures = agent_harness_benchmark()

    for fixture in fixtures:
        manifest = AttemptManifest.from_dict(fixture.attempt_manifest.to_dict())
        events = [TraceEvent.from_dict(event.to_dict()) for event in fixture.expected_trace_events]
        event_types = {event.event_type for event in events}

        assert manifest.task_contract_id == fixture.contract.id
        assert manifest.task_contract_digest == fixture.contract.digest()
        assert event_types == {
            "context.loaded",
            "tool.call",
            "verification.result",
            "outcome.reported",
        }
        assert fixture.expected_trace_manifest.trace_event_count == len(events)
        assert fixture.expected_trace_manifest.evidence_level == 3


def test_dataset_export_includes_benchmark_trajectories(tmp_path: Path) -> None:
    records = agent_harness_dataset_records()
    out_path = tmp_path / "benchmark-trajectories.jsonl"

    manifest = export_trajectories_jsonl(
        records,
        out_path,
        dataset_id="dataset_agent_harness_benchmark",
    )
    loaded = read_trajectory_jsonl(out_path)

    assert manifest.record_count == 3
    assert manifest.quality_issues == []
    assert {record["benchmark"]["id"] for record in loaded} == {BENCHMARK_ID}
    assert {record["outcome"] for record in loaded} == {"accepted"}
    assert all(record["receipt"]["accepted"] is True for record in loaded)
