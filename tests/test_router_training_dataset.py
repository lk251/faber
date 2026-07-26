from pathlib import Path

from faber.datasets import read_trajectory_jsonl
from faber.digests import sha256_digest
from faber.router_datasets import export_router_training_jsonl, router_training_record
from faber.trajectories import build_demo_trajectory

CREATED_AT = "2026-01-01T00:00:00Z"


def _record(
    *,
    record_id: str,
    outcome: str,
    consent: bool,
    strong: bool,
) -> dict[str, object]:
    record = build_demo_trajectory().to_dict()
    record["id"] = record_id
    record["outcome"] = outcome
    record["receipt"]["accepted"] = outcome == "accepted"
    record["training_consent"] = {
        "id": f"trajectory-consent_{record_id}",
        "training_use_allowed": consent,
        "allowed_uses": ["router", "supervised", "rl"] if consent else [],
    }
    if strong:
        record["attempt_manifest"] = {
            "id": f"attempt-manifest_{record_id}",
            "evidence_level": {"level": 2},
            "model_metadata": {"family": "fixture", "disclosure": "coarse"},
            "harness_metadata": {"family": "faber-runner", "version": "1"},
            "environment_metadata": {
                "platform": "windows",
                "repository_snapshot_digest": sha256_digest("snapshot"),
            },
            "training_consent": record["training_consent"],
        }
        record["trace_manifest"] = {
            "evidence_level": {"level": 2},
            "trace_event_count": 3,
            "trace_jsonl_digest": sha256_digest("trace"),
            "included_event_types": [
                "context.read",
                "tool.call",
                "verification.result",
            ],
            "provenance": {"runner": "fixture"},
        }
    return record


def test_router_dataset_record_includes_required_features_and_labels() -> None:
    record = router_training_record(
        _record(record_id="trajectory_router", outcome="accepted", consent=True, strong=True)
    )

    assert record["features"]["task"]["task_source"] == "demo"
    assert record["features"]["worker"]["worker_id"] == "worker_demo"
    assert record["features"]["solver"]["harness_family"] == "faber-runner"
    assert record["features"]["verifier_policy"]["verifier_ids"] == ["verifier.local.unit-tests"]
    assert record["labels"]["selected_worker_id"] == "worker_demo"
    assert record["labels"]["selected_verifier_id"] == "verifier.local.unit-tests"


def test_router_dataset_training_consent_filter_works(tmp_path: Path) -> None:
    allowed = _record(
        record_id="trajectory_allowed",
        outcome="accepted",
        consent=True,
        strong=True,
    )
    denied = _record(
        record_id="trajectory_denied",
        outcome="accepted",
        consent=False,
        strong=True,
    )
    path = tmp_path / "router.jsonl"

    manifest = export_router_training_jsonl([allowed, denied], path)

    assert manifest.record_count == 1
    assert read_trajectory_jsonl(path)[0]["trajectory_id"] == "trajectory_allowed"


def test_weak_and_strong_label_distinction_is_preserved() -> None:
    weak = router_training_record(
        _record(record_id="trajectory_weak", outcome="accepted", consent=True, strong=False)
    )
    strong = router_training_record(
        _record(record_id="trajectory_strong", outcome="accepted", consent=True, strong=True)
    )

    assert weak["label_strength"] == "weak"
    assert weak["trajectory_quality_tier"] == "pr_only"
    assert strong["label_strength"] == "strong"
    assert strong["trajectory_quality_tier"] == "trace"


def test_value_per_euro_label_uses_integer_money() -> None:
    record = router_training_record(
        _record(record_id="trajectory_value", outcome="accepted", consent=True, strong=True)
    )

    assert isinstance(record["labels"]["value_per_euro_milli"], int)
    assert record["labels"]["cost_minor_units"] == 3_000
    assert record["labels"]["reward_minor_units"] == 5_000


def test_negative_examples_are_included_when_policy_allows(tmp_path: Path) -> None:
    records = [
        _record(
            record_id="trajectory_rejected",
            outcome="rejected",
            consent=True,
            strong=True,
        ),
        _record(
            record_id="trajectory_timeout",
            outcome="timeout",
            consent=True,
            strong=True,
        ),
        _record(
            record_id="trajectory_declined",
            outcome="declined",
            consent=True,
            strong=False,
        ),
    ]
    path = tmp_path / "negative.jsonl"

    manifest = export_router_training_jsonl(records, path, include_negative=True)
    exported = read_trajectory_jsonl(path)

    assert manifest.negative_count == 3
    assert {record["labels"]["outcome"] for record in exported} == {
        "rejected",
        "timeout",
        "declined",
    }
