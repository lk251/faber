from dataclasses import replace
from pathlib import Path

from faber.cli import main
from faber.datasets import (
    assign_split,
    dataset_summary,
    export_trajectories_jsonl,
    quality_issues,
    redact_fields,
    summarize_records,
)
from faber.store import save_trajectory
from faber.trajectories import build_demo_trajectory


def _records() -> list[dict[str, object]]:
    accepted = build_demo_trajectory()
    rejected = replace(
        accepted,
        id="trajectory_rejected",
        receipt=replace(accepted.receipt, accepted=False),
        settlement=None,
    )
    return [accepted.to_dict(), rejected.to_dict()]


def test_jsonl_export_is_stable(tmp_path: Path) -> None:
    records = _records()
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"

    manifest_a = export_trajectories_jsonl(records, out_a, dataset_id="dataset_test")
    manifest_b = export_trajectories_jsonl(records, out_b, dataset_id="dataset_test")

    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")
    assert manifest_a.jsonl_digest == manifest_b.jsonl_digest
    assert manifest_a.record_count == 2


def test_manifest_digest_changes_when_records_change(tmp_path: Path) -> None:
    records = _records()
    manifest_a = export_trajectories_jsonl(records, tmp_path / "a.jsonl")
    changed = [dict(records[0], outcome="rejected")]
    manifest_b = export_trajectories_jsonl(changed, tmp_path / "b.jsonl")

    assert manifest_a.jsonl_digest != manifest_b.jsonl_digest


def test_split_assignment_is_deterministic() -> None:
    assert assign_split("trajectory_demo") == assign_split("trajectory_demo")
    assert assign_split("trajectory_demo") in {"train", "validation", "test"}


def test_dataset_summary_counts_cost_and_value() -> None:
    summary = summarize_records(_records())

    assert summary["record_count"] == 2
    assert summary["accepted_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["total_cost_minor_units"] > 0
    assert summary["total_reward_minor_units"] > 0
    assert isinstance(summary["total_margin_minor_units"], int)


def test_redaction_hook_replaces_sensitive_fields() -> None:
    record = build_demo_trajectory().to_dict()

    redacted = redact_fields(record, ["contract.description", "review_metadata.notes"])

    assert redacted["contract"]["description"] == "[redacted]"
    assert redacted["review_metadata"]["notes"] == "[redacted]"
    assert record["contract"]["description"] != "[redacted]"


def test_quality_checks_identify_incomplete_records() -> None:
    issues = quality_issues({"id": "trajectory_incomplete"})

    assert {"field": "receipt", "issue": "missing"} in issues
    assert {"field": "router_decision", "issue": "missing"} in issues


def test_dataset_cli_exports_and_summarizes_store(tmp_path: Path, capsys) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"
    trajectory = build_demo_trajectory()
    save_trajectory(store_path, trajectory)
    out_path = tmp_path / "trajectories.jsonl"

    assert main(["export-trajectories", "--store", str(store_path), "--out", str(out_path)]) == 0
    export_output = capsys.readouterr().out
    assert '"record_count":1' in export_output

    assert main(["dataset-summary", str(out_path)]) == 0
    summary_output = capsys.readouterr().out
    assert '"accepted_count":1' in summary_output
    assert dataset_summary(out_path)["record_count"] == 1
