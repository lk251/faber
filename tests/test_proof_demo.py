from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

import faber.adapters
import faber.cli
from faber.canonical_json import canonical_json
from faber.proof_configuration import load_proof_configuration
from faber.proof_demo import (
    DEMO_CAPTURE_SCHEMA,
    DEMO_EXPECTED_FAILED_CLAIM,
    ProofDemoError,
    ProofDemoOutcome,
    generate_development_fixture_payloads,
    materialize_demo_repository,
    review_demo_replays,
    review_live_demo_capture,
    run_proof_demo,
)
from faber.proof_product import ProofProductError, run_proof_product

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "examples" / "build-week-proof"
SKILL_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "faber-proof"


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


@pytest.fixture(scope="module")
def no_key() -> Iterator[None]:
    previous = os.environ.pop("OPENAI_API_KEY", None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ["OPENAI_API_KEY"] = previous


@pytest.fixture(scope="module")
def demo_outcome(tmp_path_factory: pytest.TempPathFactory, no_key: None) -> ProofDemoOutcome:
    return run_proof_demo(
        repository_root=REPOSITORY_ROOT,
        mode="replay",
        output_directory=tmp_path_factory.mktemp("proof-demo") / "result",
    )


def test_skill_frontmatter_references_and_commands_validate() -> None:
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "validate_skill.py")],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "skill validation passed" in result.stdout
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: faber-proof\ndescription:")
    assert "do not trigger for ordinary test-only requests" in skill


def test_skill_replay_example_runs_without_credentials(
    tmp_path: Path,
    no_key: None,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "validate_skill.py"),
            "--run-replay",
            "--out-dir",
            str(tmp_path / "skill-demo"),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "skill validation passed" in result.stdout


def test_fixture_is_owned_stdlib_only_and_catalog_has_real_choice() -> None:
    ownership = (FIXTURE_ROOT / "OWNERSHIP.md").read_text(encoding="utf-8")
    assert "owned by this repository" in ownership
    assert "Python standard library" in ownership
    for path in [
        FIXTURE_ROOT / "source" / "scheduler.py",
        FIXTURE_ROOT / "ordinary-tests" / "test_scheduler.py",
        FIXTURE_ROOT / "proof_harness.py",
    ]:
        source = path.read_text(encoding="utf-8")
        assert "requests" not in source
        assert "pytest" not in source
    configuration = load_proof_configuration(FIXTURE_ROOT / "proof-catalog.json")
    assert len(configuration.catalog.entries) == 5
    assert len(configuration.proof_policy.mandatory_template_ids) == 3
    assert "proof.serialization-preview" not in configuration.proof_policy.mandatory_template_ids


def test_development_fixtures_regenerate_byte_identically() -> None:
    provenance = json.loads(
        (FIXTURE_ROOT / "replays" / "provenance.json").read_text(encoding="utf-8")
    )
    if provenance["status"] == "live-reviewed":
        pytest.skip("live-reviewed fixtures are protected from fake regeneration")
    generated = generate_development_fixture_payloads(FIXTURE_ROOT)
    files = {
        "task_contract": FIXTURE_ROOT / "task-contract.json",
        "proof_catalog": FIXTURE_ROOT / "proof-catalog.json",
        "bad_replay": FIXTURE_ROOT / "replays" / "bad.json",
        "repaired_replay": FIXTURE_ROOT / "replays" / "repaired.json",
        "provenance": FIXTURE_ROOT / "replays" / "provenance.json",
    }
    for key, path in files.items():
        assert path.read_text(encoding="utf-8") == canonical_json(generated[key]) + "\n"


def test_bad_and_repaired_revisions_are_distinct_and_deterministic(tmp_path: Path) -> None:
    first = materialize_demo_repository(FIXTURE_ROOT, tmp_path / "first")
    second = materialize_demo_repository(FIXTURE_ROOT, tmp_path / "second")

    assert first.base_revision == second.base_revision
    assert first.bad_revision == second.bad_revision
    assert first.repaired_revision == second.repaired_revision
    assert len({first.base_revision, first.bad_revision, first.repaired_revision}) == 3
    bad_diff = _git(first.root, "diff", first.base_revision, first.bad_revision, "--")
    repaired_diff = _git(first.root, "diff", first.base_revision, first.repaired_revision, "--")
    assert "turn_number == turn_budget" in bad_diff
    assert bad_diff != repaired_diff


def test_one_command_demo_produces_memorable_authoritative_contrast(
    demo_outcome: ProofDemoOutcome,
) -> None:
    bad = demo_outcome.summary["bad"]
    repaired = demo_outcome.summary["repaired"]
    assert isinstance(bad, Mapping)
    assert isinstance(repaired, Mapping)
    assert bad["ordinary_tests"] == "pass"
    assert repaired["ordinary_tests"] == "pass"
    assert bad["verdict"] == "block"
    assert repaired["verdict"] == "pass"
    assert bad["failed_claim_ids"] == [DEMO_EXPECTED_FAILED_CLAIM]
    assert bad["failed_required_claims"] == 1
    assert repaired["failed_required_claims"] == 0
    assert repaired["missing_required_claims"] == 0
    counterexample = canonical_json(bad["counterexample"])
    assert "turn_budget=2" in counterexample
    assert "FINAL: summary" in counterexample
    assert "budget_exhausted" in counterexample

    blocked_html = (demo_outcome.output_directory / "bad" / "report.html").read_text(
        encoding="utf-8"
    )
    above_fold = blocked_html[:12_000]
    assert "BLOCK" in above_fold
    assert "last permitted turn" in above_fold
    assert "turn_budget=2" in above_fold
    assert "FINAL: summary" in above_fold
    assert "budget_exhausted" in above_fold
    passing_html = (demo_outcome.output_directory / "repaired" / "report.html").read_text(
        encoding="utf-8"
    )
    assert "PASS" in passing_html[:8_000]


def test_repair_preserves_incomplete_and_cancelled_failures() -> None:
    namespace = runpy.run_path(str(FIXTURE_ROOT / "revisions" / "repaired" / "scheduler.py"))
    run_conversation = namespace["run_conversation"]
    assert callable(run_conversation)
    assert run_conversation(["NOTE: draft"], 2) == {
        "status": "failed",
        "reason": "incomplete",
    }
    assert run_conversation(["CANCEL"], 2) == {
        "status": "failed",
        "reason": "cancelled",
    }
    assert run_conversation(["NOTE: premise", "FINAL: summary"], 2) == {
        "status": "complete",
        "report": "premise\nsummary",
    }


def test_bad_replay_is_rejected_after_repaired_diff(tmp_path: Path) -> None:
    repository = materialize_demo_repository(FIXTURE_ROOT, tmp_path / "repository")
    _git(repository.root, "checkout", "-q", "--detach", repository.repaired_revision)

    with pytest.raises(ProofProductError, match="replay_mismatch"):
        run_proof_product(
            repository=repository.root,
            task_path=FIXTURE_ROOT / "task-contract.json",
            catalog_path=FIXTURE_ROOT / "proof-catalog.json",
            base_revision=repository.base_revision,
            candidate_revision=repository.repaired_revision,
            mode="replay",
            replay_path=FIXTURE_ROOT / "replays" / "bad.json",
            output_directory=tmp_path / "stale-output",
        )
    assert not (tmp_path / "stale-output").exists()


def test_replay_mode_never_constructs_live_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_key: None,
) -> None:
    class ForbiddenLiveBackend:
        def __init__(self, **_: object) -> None:
            raise AssertionError("live backend was touched during replay")

    monkeypatch.setattr(faber.adapters, "OpenAIProofPlannerBackend", ForbiddenLiveBackend)
    result = run_proof_demo(
        repository_root=REPOSITORY_ROOT,
        mode="replay",
        output_directory=tmp_path / "no-network-demo",
    )
    assert result.summary["bad"]["verdict"] == "block"  # type: ignore[index]
    assert result.summary["repaired"]["verdict"] == "pass"  # type: ignore[index]


def test_json_and_human_cli_comparisons_agree(
    demo_outcome: ProofDemoOutcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(faber.cli, "run_proof_demo", lambda **_: demo_outcome)
    assert faber.cli.main(["demo", "proof", "--mode", "replay", "--json"]) == 0
    machine = json.loads(capsys.readouterr().out)
    assert canonical_json(machine) == canonical_json(demo_outcome.summary)

    assert faber.cli.main(["demo", "proof", "--mode", "replay"]) == 0
    human = capsys.readouterr().out
    assert "BAD PATCH" in human and "REPAIRED PATCH" in human
    assert "BLOCK" in human and "PASS" in human
    assert "FAKE-DEVELOPMENT" in human


def test_reports_are_portable_secret_safe_and_final_samples_wait_for_live_review(
    demo_outcome: ProofDemoOutcome,
) -> None:
    for name in ("bad", "repaired"):
        report = (demo_outcome.output_directory / name / "report.html").read_text(encoding="utf-8")
        lowered = report.casefold()
        assert "c:\\users\\" not in lowered
        assert "/users/" not in lowered
        assert "sk-proj-" not in lowered
        assert "api_key=" not in lowered
        assert "<script" not in lowered
        assert "https://" not in lowered
    provenance = json.loads(
        (FIXTURE_ROOT / "replays" / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance["status"] in {"fake-development", "live-reviewed"}
    if provenance["status"] == "fake-development":
        assert list((FIXTURE_ROOT / "expected").glob("*.html")) == []
    else:
        assert (FIXTURE_ROOT / "expected" / "blocked-report.html").is_file()
        assert (FIXTURE_ROOT / "expected" / "passing-report.html").is_file()
        assert (FIXTURE_ROOT / "expected" / "generation-manifest.json").is_file()
    with pytest.raises(ProofDemoError, match="live-reviewed"):
        review_demo_replays(FIXTURE_ROOT, require_live_reviewed=True)


def test_fake_development_bundles_cannot_be_installed_as_live_reviewed(
    tmp_path: Path,
) -> None:
    provenance = json.loads(
        (FIXTURE_ROOT / "replays" / "provenance.json").read_text(encoding="utf-8")
    )
    capture = tmp_path / "capture"
    capture.mkdir()
    bundles: dict[str, object] = {}
    for name in ("bad", "repaired"):
        (capture / f"{name}.json").write_bytes(
            (FIXTURE_ROOT / "replays" / f"{name}.json").read_bytes()
        )
        recorded = provenance["bundles"][name]
        bundles[name] = {
            "path": f"{name}.json",
            "bundle_digest": recorded["bundle_digest"],
            "request_digest": recorded["request_digest"],
        }
    (capture / "capture-manifest.json").write_text(
        canonical_json(
            {
                "schema": DEMO_CAPTURE_SCHEMA,
                "status": "live-captured-unreviewed",
                "bundles": bundles,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProofDemoError, match="real returned model metadata"):
        review_live_demo_capture(
            FIXTURE_ROOT,
            capture,
            reviewer="test reviewer",
            reviewed_at="2026-07-17T01:00:00+00:00",
        )
