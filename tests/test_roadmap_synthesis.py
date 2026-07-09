from pathlib import Path


def _read(name: str) -> str:
    return Path("docs", name).read_text(encoding="utf-8")


def test_roadmap_selects_one_low_risk_external_pilot() -> None:
    roadmap = _read("ROADMAP.md")

    assert "Next milestone: no-money external pilot" in roadmap
    assert "issue #61631" in roadmap
    assert "issue #48628" not in roadmap
    assert "Keep the first pilot unpaid" in roadmap


def test_roadmap_lists_next_five_and_required_blockers() -> None:
    roadmap = _read("ROADMAP.md")

    for heading in [
        "Next five implementation items",
        "Blockers before real money or external autonomous work",
        "Blockers before training on collected trajectories",
        "Blockers before a real GitHub App installation",
    ]:
        assert heading in roadmap
    for number in range(1, 6):
        assert f"{number}. **" in roadmap


def test_milestones_mark_foundation_complete_and_external_pilot_next() -> None:
    milestones = _read("MILESTONES.md")

    assert "Milestone 1: RL-grade local foundation - complete" in milestones
    assert "Milestone 2: human-approved external dry run - next" in milestones
    assert "Milestone 4: limited funded pilot - blocked" in milestones
    assert "Milestone 5: first learning experiment - blocked" in milestones


def test_open_questions_are_narrowed_to_unresolved_decisions() -> None:
    questions = _read("OPEN_QUESTIONS.md")

    assert "Which learned output should come first" in questions
    assert "What evidence level should paid work require by default?" not in questions
    assert "should #48628 stay first" not in questions


def test_glossary_covers_protocol_market_and_learning_terms() -> None:
    glossary = _read("GLOSSARY.md")

    for term in [
        "TaskContract",
        "Raw trace",
        "Trajectory",
        "RL-grade trajectory",
        "VerificationReceipt",
        "Work budget",
        "Training eligibility",
        "Faber Protocol",
        "Faber Market",
        "Local mode",
        "Hosted mode",
    ]:
        assert f"**{term}**" in glossary
