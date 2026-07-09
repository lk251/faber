import json
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.datasets import export_trajectories_jsonl
from faber.golden_fixtures import (
    GOLDEN_FIXTURE_NAMES,
    TRAJECTORY_FIXTURE_NAMES,
    build_golden_fixture_corpus,
    load_golden_fixture_corpus,
    validate_golden_fixture_corpus,
)

FIXTURE_ROOT = Path("tests/fixtures/golden")


def test_all_golden_fixtures_validate() -> None:
    fixtures = load_golden_fixture_corpus(FIXTURE_ROOT)

    assert [fixture.name for fixture in fixtures] == list(GOLDEN_FIXTURE_NAMES)
    assert validate_golden_fixture_corpus(fixtures) == []


def test_canonical_json_snapshots_match_builders(tmp_path: Path) -> None:
    expected = load_golden_fixture_corpus(FIXTURE_ROOT)
    rebuilt = build_golden_fixture_corpus(tmp_path / "builder-work")

    assert [fixture.canonical_json() for fixture in rebuilt] == [
        fixture.canonical_json() for fixture in expected
    ]
    for fixture in expected:
        snapshot_text = (FIXTURE_ROOT / fixture.filename).read_text(encoding="utf-8")
        assert snapshot_text == canonical_json(fixture.payload) + "\n"


def test_golden_payload_digests_match_manifest() -> None:
    fixtures = load_golden_fixture_corpus(FIXTURE_ROOT)
    digest_manifest = json.loads((FIXTURE_ROOT / "digests.json").read_text(encoding="utf-8"))

    for fixture in fixtures:
        expected = digest_manifest["fixtures"][fixture.name]
        assert expected["file"] == fixture.filename
        assert expected["payload_digest"] == fixture.digest()


def test_dataset_export_from_golden_corpus_is_stable(tmp_path: Path) -> None:
    fixtures = load_golden_fixture_corpus(FIXTURE_ROOT)
    trajectories = [
        fixture.payload
        for fixture in fixtures
        if fixture.name in TRAJECTORY_FIXTURE_NAMES
    ]
    expected = json.loads((FIXTURE_ROOT / "digests.json").read_text(encoding="utf-8"))

    manifest = export_trajectories_jsonl(
        trajectories,
        tmp_path / "golden-dataset.jsonl",
        dataset_id="dataset_golden_fixture_corpus",
    )

    assert manifest.record_count == expected["dataset"]["record_count"]
    assert manifest.jsonl_digest == expected["dataset"]["jsonl_digest"]


def test_fixture_docs_match_snapshot_names() -> None:
    text = Path("docs/GOLDEN_FIXTURE_CORPUS.md").read_text(encoding="utf-8")

    for name in GOLDEN_FIXTURE_NAMES:
        assert f"`{name}.json`" in text
