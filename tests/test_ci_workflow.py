from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_ci_is_least_privilege_cross_platform_and_covers_0082_gates() -> None:
    active = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
    draft = REPOSITORY_ROOT / "codex" / "build-week" / "drafts" / "ci.yml"
    workflow = (active if active.is_file() else draft).read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "fetch-depth: 0" in workflow
    assert "persist-credentials: false" in workflow
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert 'python-version: "3.11"' in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v6" in workflow
    for required in (
        "ruff format --check",
        "ruff check",
        "mypy src",
        "python -m pytest",
        "python -m build --wheel --sdist",
        "clean_install_audit.py",
        "faber audit-proof-artifacts",
        "run_build_week_evals.py --check",
        "check_development_report_regeneration.py --check",
        "measure_proof_demo.py",
        "check_demo_script.py",
        "final_submission_audit.py --run-machine-checks --require machine",
        "find_spec('openai') is None",
        "find_spec('openai') is not None",
    ):
        assert required in workflow
    assert "OPENAI_API_KEY" not in workflow
    assert "write" not in workflow
