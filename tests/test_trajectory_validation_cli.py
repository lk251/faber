import json
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.cli import main
from faber.digests import sha256_digest
from faber.trajectories import build_demo_trajectory

CREATED_AT = "2026-01-01T00:00:00Z"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")


def _rl_grade_record() -> dict[str, object]:
    record = build_demo_trajectory().to_dict()
    record["attempt_manifest"] = {
        "schema": "faber.attempt_manifest.v1",
        "id": "attempt-manifest_cli",
        "created_at": CREATED_AT,
        "task_contract_id": "task-contract_demo",
        "task_contract_digest": record["receipt"]["task_contract_digest"],
        "attempt_id": "attempt_demo",
        "base_revision": "base-demo-revision",
        "candidate_revision": "candidate-demo-revision",
        "worker_id": "worker_demo",
        "evidence_level": {"level": 2},
        "model_metadata": {"disclosure": "coarse", "family": "fixture"},
        "harness_metadata": {"family": "faber-runner", "version": "1"},
        "runner_metadata": {"runner": "faber-runner"},
        "environment_metadata": {
            "platform": "windows",
            "reproducibility_level": "lockfile",
            "repository_snapshot_digest": sha256_digest("snapshot"),
        },
        "budget_metadata": {"currency": "EUR", "budget_minor_units": 5000},
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 1200},
        "latency_metadata": {"work_seconds": 600},
        "training_consent": {
            "id": "trajectory-consent_cli",
            "training_use_allowed": True,
            "allowed_uses": ["rl", "supervised", "router"],
        },
    }
    record["trace_manifest"] = {
        "id": "trace-manifest_cli",
        "attempt_id": "attempt_demo",
        "evidence_level": {"level": 2},
        "trace_event_count": 3,
        "trace_jsonl_digest": sha256_digest("trace"),
        "included_event_types": [
            "context.read",
            "tool.call",
            "verification.result",
        ],
        "redaction_policy": {"id": "redaction-policy_cli"},
        "provenance": {"runner": "faber"},
    }
    return record


def test_valid_rl_grade_trajectory_returns_success(
    tmp_path: Path,
    capsys,
) -> None:
    path = tmp_path / "trajectory.json"
    _write_json(path, _rl_grade_record())

    assert main(["validate-trajectory", str(path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "valid"
    assert output["summary"] == "Trajectory is valid and RL-grade."
    assert output["details"]["rl_grade_eligible"] is True
    assert output["details"]["training_consent"] is True


def test_pr_only_trajectory_returns_valid_warning(tmp_path: Path, capsys) -> None:
    path = tmp_path / "pr-only.json"
    _write_json(path, build_demo_trajectory().to_dict())

    assert main(["trajectory-quality", str(path)]) == 2

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "warning"
    assert output["details"]["quality_tier"] == "pr_only"
    assert output["details"]["audit_eligible"] is True
    assert output["details"]["rl_grade_eligible"] is False


def test_malformed_manifest_returns_clear_field_error(tmp_path: Path, capsys) -> None:
    path = tmp_path / "attempt.json"
    _write_json(path, {})

    assert main(["validate-attempt", str(path)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "invalid"
    assert output["errors"][0]["field"] == "redaction_policy"
    assert "expected" in output["errors"][0]


def test_missing_consent_blocks_training_eligibility(tmp_path: Path, capsys) -> None:
    path = tmp_path / "missing-consent.json"
    record = _rl_grade_record()
    record["attempt_manifest"]["training_consent"] = None
    _write_json(path, record)

    assert main(["validate-trajectory", str(path)]) == 2

    output = json.loads(capsys.readouterr().out)
    assert output["details"]["training_consent"] is False
    assert output["details"]["training_export_eligible"] is False
    assert "training_consent" in output["details"]["missing_fields"]


def test_valid_trace_command_and_output_are_stable(tmp_path: Path, capsys) -> None:
    path = tmp_path / "trace.jsonl"
    event = {
        "schema": "faber.trace_event.v1",
        "id": "trace-event_cli",
        "created_at": CREATED_AT,
        "attempt_id": "attempt_cli",
        "sequence": 0,
        "event_type": "tool.call",
        "observed_at": CREATED_AT,
        "payload": {"tool": "pytest"},
        "trust_level": "runner_attested",
        "provenance": {"runner": "fixture"},
        "redaction_policy_id": None,
    }
    path.write_text(canonical_json(event) + "\n", encoding="utf-8")

    assert main(["validate-trace", str(path)]) == 0
    first = capsys.readouterr().out
    assert main(["validate-trace", str(path)]) == 0
    second = capsys.readouterr().out

    assert first == second
    assert json.loads(first)["details"]["event_count"] == 1
