from pathlib import Path


def test_roadmap_covers_trace_funding_and_external_pilot_tracks() -> None:
    roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")

    for phrase in [
        "trace protocol and evidence ladder",
        "solver metadata and provenance",
        "cross-platform reproducibility",
        "funded GitHub issues",
        "funding source adapters",
        "Hermes Agent",
        "risk review before funded external work",
    ]:
        assert phrase in roadmap


def test_open_questions_cover_trace_funding_and_authority_decisions() -> None:
    questions = Path("docs/OPEN_QUESTIONS.md").read_text(encoding="utf-8")

    for phrase in [
        "What evidence level should paid work require",
        "What trace level can Faber use for training data",
        "How should Faber price richer traces",
        "How do we prevent fake solver metadata",
        "When should NixOS be required",
        "should #48628 stay first",
        "existing repository funding mechanisms fund task budgets",
        "license and consent terms",
        "When can advisory verification influence payment",
    ]:
        assert phrase in questions


def test_future_queue_indexes_trace_funding_external_pilot_queue() -> None:
    queue_index = Path("codex/future/README.md").read_text(encoding="utf-8")

    for issue in ["0030", "0038", "0041", "0044", "0045"]:
        assert issue in queue_index
