import json
from pathlib import Path

from faber.artifact_validation import (
    validate_attempt_file,
    validate_trace_file,
    validate_trajectory_file,
)
from faber.cli import main
from faber.datasets import read_trajectory_jsonl


def test_full_funded_trajectory_cli_golden_path(
    tmp_path: Path,
    capsys,
) -> None:
    out_dir = tmp_path / "funded-demo"

    assert main(["demo-funded-trajectory", "--out-dir", str(out_dir), "--json"]) == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "complete"
    assert summary["contract"]["id"] == "task-contract_fake_github_65"
    assert summary["budget_settlement"]["id"].startswith("budget-settlement_")
    assert summary["trajectory"]["rl_grade"] is True
    assert summary["dataset"]["record_count"] == 1
    assert all(Path(path).exists() for path in summary["paths"].values())


def test_generated_funded_demo_artifacts_validate(tmp_path: Path, capsys) -> None:
    out_dir = tmp_path / "funded-demo"
    assert main(["demo-funded-trajectory", "--out-dir", str(out_dir), "--json"]) == 0
    capsys.readouterr()

    attempt = validate_attempt_file(out_dir / "pr" / ".faber" / "attempt.json")
    trace = validate_trace_file(out_dir / "pr" / ".faber" / "trace.jsonl")
    trajectory = validate_trajectory_file(out_dir / "trajectory.json")
    dataset = read_trajectory_jsonl(out_dir / "training.jsonl")

    assert attempt.status == "valid"
    assert trace.status == "valid"
    assert trajectory.status == "valid"
    assert trajectory.details["rl_grade_eligible"] is True
    assert len(dataset) == 1
    assert dataset[0]["trajectory_quality"]["is_rl_grade"] is True


def test_funded_demo_human_output_names_ids_digests_and_paths(
    tmp_path: Path,
    capsys,
) -> None:
    out_dir = tmp_path / "funded-demo"

    assert main(["demo-funded-trajectory", "--out-dir", str(out_dir)]) == 0

    output = capsys.readouterr().out
    assert "Faber funded RL-grade demo: complete" in output
    assert "Contract: task-contract_fake_github_65 (sha256:" in output
    assert "Receipt: verification-receipt_fake_github_165 (sha256:" in output
    assert "Dataset: 1 permitted record" in output
    assert str(out_dir / "trajectory.json") in output
    assert "No network, payment provider, or model provider was used." in output


def test_funded_demo_documented_command_matches_cli_and_justfile() -> None:
    quickstart = Path("docs/QUICKSTART.md").read_text(encoding="utf-8")
    justfile = Path("justfile").read_text(encoding="utf-8")
    command = (
        "python -m faber.cli demo-funded-trajectory "
        "--out-dir .faber/funded-demo"
    )

    assert command in quickstart
    assert "demo-funded-trajectory:" in justfile
    assert command in justfile
