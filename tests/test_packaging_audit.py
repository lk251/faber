from __future__ import annotations

import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_package_metadata_keeps_openai_optional_and_installs_the_demo_fixture() -> None:
    configuration = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = configuration["project"]

    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == []
    assert project["scripts"]["faber"] == "faber.cli:main"
    assert project["optional-dependencies"]["live-openai"] == ["openai>=2.45.0,<3"]
    data_files = configuration["tool"]["setuptools"]["data-files"]
    assert "share/faber/examples/build-week-proof" in data_files
    assert (
        "examples/build-week-proof/replays/*.json"
        in data_files["share/faber/examples/build-week-proof/replays"]
    )


def test_clean_install_audit_controls_checkout_imports_and_required_smoke_steps() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "clean_install_audit.py").read_text(encoding="utf-8")

    for required in (
        '"PYTHONPATH"',
        '"PYTHONNOUSERSITE"',
        '"--wheel"',
        '"--sdist"',
        '"--no-deps"',
        '"openai_available"',
        '"doctor"',
        '"demo"',
        '"audit-proof-artifacts"',
        '"bad/report.html"',
        '"repaired/report.html"',
    ):
        assert required in script


def test_development_report_regeneration_is_explicitly_not_live_provenance() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "check_development_report_regeneration.py").read_text(
        encoding="utf-8"
    )

    assert '"sample_reports_committed": False' in script
    assert "fake-development" in script
    assert "live-reviewed" in script
    assert "first_bytes != second_bytes" in script
    assert "audit_proof_artifacts" in script


def test_performance_smoke_covers_required_stages_with_generous_thresholds() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "measure_proof_demo.py").read_text(encoding="utf-8")

    for required in (
        "replay_planning_seconds",
        "proof_execution_seconds",
        "report_generation_seconds",
        "total_demo_seconds",
        "bundle_bytes",
        "maximum_total_demo_seconds",
        "memory_measurement",
    ):
        assert required in script
    assert '"maximum_total_demo_seconds": 90.0' in script
