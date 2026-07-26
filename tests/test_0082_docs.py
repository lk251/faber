from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_0082_security_and_eval_docs_name_controls_results_and_limits() -> None:
    threat = _read("docs/FABER_PROOF_THREAT_MODEL.md")
    evals = _read("docs/BUILD_WEEK_EVALS.md")

    for term in (
        "candidate diff",
        "model output",
        "replay",
        "symlink",
        "receipt",
        "partial",
        "production-grade sandboxing",
        "comprehensive secret detection",
    ):
        assert term in threat

    assert "49/49" in evals
    assert "unjustified_pass_count: 0" in evals
    assert "HUMAN_REVIEW" in evals
    assert "scripts/run_build_week_evals.py --check" in evals
    assert "not exhaustive fuzzing" in evals


def test_judge_and_live_commands_are_documented_without_claiming_live_provenance() -> None:
    development = _read("docs/DEVELOPMENT.md")
    live_runbook = _read("docs/LIVE_GPT56_CAPTURE_RUNBOOK.md")
    example = _read("examples/build-week-proof/README.md")

    assert 'python -m pip install ".[live-openai]"' in development
    assert "faber demo proof --mode replay" in development
    assert "requires no API key" in development
    assert "capture_live_reviewed_demo.py --reviewer" in live_runbook
    assert "fake-development" in live_runbook
    assert "No provider call is made by the tests" in live_runbook
    assert "capture_live_reviewed_demo.py --reviewer" in example
