from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_demo_script.py"


def _load_script() -> object:
    spec = importlib.util.spec_from_file_location("check_demo_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_committed_demo_narration_meets_the_mechanical_budget() -> None:
    script = _load_script()
    text = (ROOT / "docs" / "DEMO_SCRIPT.md").read_text(encoding="utf-8")

    analysis = script.analyze_narration(text)

    assert analysis.status == "pass"
    assert 388 <= analysis.word_count <= 396
    assert analysis.estimated_seconds_at_150_wpm >= 155
    assert analysis.estimated_seconds_at_140_wpm <= 170
    narration = script.extract_narration(text)
    for required in (
        "Codex",
        "GPT-5.6",
        "BLOCK",
        "PASS",
        "ordinary tests",
        "counterexample",
        "trust boundary",
        "replay",
    ):
        assert required.casefold() in narration.casefold()


def test_word_budget_rejects_short_and_long_narration() -> None:
    script = _load_script()

    short = f"{script.START_MARKER}\none two three\n{script.END_MARKER}"
    long = (
        f"{script.START_MARKER}\n"
        + " ".join(f"word{index}" for index in range(500))
        + f"\n{script.END_MARKER}"
    )

    assert script.analyze_narration(short).status == "fail"
    assert script.analyze_narration(long).status == "fail"


def test_marker_errors_fail_before_word_counting() -> None:
    script = _load_script()

    with pytest.raises(script.NarrationError, match="exactly one"):
        script.extract_narration("No markers")
    with pytest.raises(script.NarrationError, match="must follow"):
        script.extract_narration(f"{script.END_MARKER}\ntext\n{script.START_MARKER}")
