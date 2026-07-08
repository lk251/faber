from pathlib import Path

from faber.cli import main
from faber.store import load_record, store_summary


def test_golden_path_cli_flow_generates_files(tmp_path: Path, capsys) -> None:
    store_path = tmp_path / ".faber" / "golden.sqlite3"
    out_path = tmp_path / ".faber" / "golden_trajectory.json"

    assert main(["run-golden-path", "--store", str(store_path), "--out", str(out_path)]) == 0

    output = capsys.readouterr().out
    assert "trajectory_golden" in output
    assert store_path.exists()
    assert out_path.exists()
    assert '"schema":"faber.trajectory.v1"' in out_path.read_text(encoding="utf-8")
    assert load_record(store_path, "trajectory", "trajectory_golden")["id"] == "trajectory_golden"


def test_composable_golden_path_commands(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "golden.sqlite3"
    out_path = tmp_path / ".faber" / "golden_trajectory.json"

    for command in [
        "init-local-store",
        "create-demo-contract",
        "register-demo-worker",
        "register-demo-verifier",
        "submit-demo-attempt",
        "run-demo-verifier",
        "issue-demo-receipt",
        "settle-demo",
    ]:
        if command == "init-local-store":
            assert main([command, "--path", str(store_path)]) == 0
        else:
            assert main([command, "--store", str(store_path)]) == 0
    assert main(["export-demo-trajectory", "--store", str(store_path), "--out", str(out_path)]) == 0

    summary = store_summary(store_path)
    assert summary["record_counts"]["task_contract"] == 1
    assert summary["record_counts"]["worker_profile"] == 1
    assert summary["record_counts"]["trajectory"] == 1
    assert out_path.exists()


def test_golden_path_docs_and_just_demo_are_accurate() -> None:
    quickstart = Path("docs/QUICKSTART.md").read_text(encoding="utf-8")
    golden = Path("docs/GOLDEN_PATH.md").read_text(encoding="utf-8")
    justfile = Path("justfile").read_text(encoding="utf-8")

    command = (
        "python -m faber.cli run-golden-path --store .faber/golden.sqlite3 "
        "--out .faber/golden_trajectory.json"
    )
    assert command in quickstart
    assert command in golden
    assert "demo:" in justfile
    assert "run-golden-path" in justfile
