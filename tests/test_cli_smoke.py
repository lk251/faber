from pathlib import Path

from faber.cli import main


def test_cli_doctor_returns_success_and_environment_facts(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert "Faber doctor" in output
    assert "Python:" in output
    assert "Package import: ok" in output
    assert "SQLite: ok" in output
    assert f"Working directory: {tmp_path}" in output
    assert "Local state directory .faber/: missing" in output
    assert "faber doctor: ok" in output


def test_cli_init_local_store_creates_sqlite_file(tmp_path: Path) -> None:
    store_path = tmp_path / ".faber" / "faber.sqlite3"

    assert main(["init-local-store", "--path", str(store_path)]) == 0

    assert store_path.exists()


def test_cli_emit_demo_trajectory_writes_json(tmp_path: Path) -> None:
    out_path = tmp_path / ".faber" / "demo_trajectory.json"

    assert main(["emit-demo-trajectory", "--out", str(out_path)]) == 0

    payload = out_path.read_text(encoding="utf-8")
    assert '"schema":"faber.trajectory.v1"' in payload
    assert '"id":"trajectory_demo"' in payload


def test_documented_check_commands_match_development_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    development = Path("docs/DEVELOPMENT.md").read_text(encoding="utf-8")
    justfile = Path("justfile").read_text(encoding="utf-8")

    for command in [
        "nix develop --command just check",
        "python -m pytest",
        "python -m ruff check .",
        "python -m mypy src",
        "python -m faber.cli doctor",
    ]:
        assert command in readme or command in development
    for recipe in ["fmt:", "lint:", "typecheck:", "test:", "doctor:", "check:"]:
        assert recipe in justfile
