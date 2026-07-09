from pathlib import Path


def test_roadmap_covers_trace_funding_and_external_pilot_tracks() -> None:
    roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")

    for phrase in [
        "PR-only, manifest, trace, and replayable episode quality tiers",
        "process, environment, solver, verifier, reward, cost",
        "cross-platform fixtures",
        "Work budgets, exact local reservations",
        "NousResearch/hermes-agent",
        "Run the existing task risk review",
    ]:
        assert phrase in roadmap


def test_open_questions_cover_trace_funding_and_authority_decisions() -> None:
    questions = Path("docs/OPEN_QUESTIONS.md").read_text(encoding="utf-8")

    for phrase in [
        "Which harness can provide useful process evidence",
        "Should richer trace evidence affect base payout",
        "Which consent and license terms allow",
        "What calibration threshold and uncertainty policy",
        "Which learned output should come first",
    ]:
        assert phrase in questions
    assert "should #48628 stay first" not in questions
    assert "What evidence level should paid work require by default?" not in questions


def test_future_queue_indexes_trace_funding_external_pilot_queue() -> None:
    queue_index = Path("codex/future/README.md").read_text(encoding="utf-8")

    for issue in ["0030", "0038", "0041", "0044", "0045"]:
        assert issue in queue_index
