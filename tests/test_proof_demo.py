from __future__ import annotations

import json
import os
import runpy
import shutil
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
    _install_reviewed_demo_files,
    _structured_response,
    generate_development_fixture_payloads,
    materialize_demo_repository,
    review_demo_replays,
    review_live_demo_capture,
    run_guarded_live_demo_capture,
    run_proof_demo,
)
from faber.proof_privacy import audit_proof_artifacts
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


def _guarded_capture_repository(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    fixture = repository / "examples" / "build-week-proof"
    shutil.copytree(FIXTURE_ROOT, fixture)
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Faber test")
    _git(repository, "config", "user.email", "faber-test@example.invalid")
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "fixture")
    _git(repository, "branch", "-M", "build-week/faber-proof")
    return repository, fixture


def _fake_live_capture(configuration, calls: list[str]):
    def capture(request, *, model: str, created_at: str):
        calls.append(request.candidate_revision)
        return faber.adapters.create_planning_replay_record(
            request,
            _structured_response(configuration),
            created_at=created_at,
            requested_model=model,
            returned_model="gpt-5.6-test-fixture",
            response_id=f"resp_test_{request.digest()[7:23]}",
            input_tokens=200,
            output_tokens=100,
            latency_ms=25,
        )

    return capture


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


def test_repeated_replay_has_stable_plan_evidence_and_decision_digests(
    demo_outcome: ProofDemoOutcome,
    tmp_path: Path,
    no_key: None,
) -> None:
    repeated = run_proof_demo(
        repository_root=REPOSITORY_ROOT,
        mode="replay",
        output_directory=tmp_path / "repeated",
    )
    for candidate in ("bad", "repaired"):
        first = json.loads(
            (demo_outcome.output_directory / candidate / "run-summary.json").read_text(
                encoding="utf-8"
            )
        )
        second = json.loads(
            (repeated.output_directory / candidate / "run-summary.json").read_text(encoding="utf-8")
        )
        first_digests = first["record_digests"]
        second_digests = second["record_digests"]
        for record in ("proof_plan", "proof_evidence", "proof_decision"):
            assert first_digests[record] == second_digests[record]


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
    assert audit_proof_artifacts([demo_outcome.output_directory]).passed
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
                "captured_at": "2026-07-17T00:30:00+00:00",
                "capture_mode": "live-provider",
                "capture_adapter": "faber.adapters.openai.live",
                "warning": "unreviewed test capture",
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


def test_relabelled_development_provenance_cannot_satisfy_live_gate(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "relabelled-fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    provenance_path = fixture / "replays" / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["status"] = "live-reviewed"
    provenance_path.write_text(
        canonical_json(provenance) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ProofDemoError, match="review transaction"):
        review_demo_replays(fixture, require_live_reviewed=True)


def test_reviewed_fixture_privacy_failure_preserves_existing_files(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    existing = fixture / "replays" / "provenance.json"
    existing.parent.mkdir()
    existing.write_text('{"status":"existing"}\n', encoding="utf-8")
    secret = "sk-proj-AAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(ProofDemoError, match="privacy audit"):
        _install_reviewed_demo_files(
            fixture,
            {
                "replays/provenance.json": {"status": "replacement"},
                "expected/report.html": f"<p>{secret}</p>",
            },
            forbidden_literals=(secret,),
        )

    assert existing.read_text(encoding="utf-8") == '{"status":"existing"}\n'
    assert not (fixture / "expected" / "report.html").exists()


def test_guarded_live_capture_uses_fake_backend_and_completes_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, fixture = _guarded_capture_repository(tmp_path)
    configuration = load_proof_configuration(fixture / "proof-catalog.json")
    calls: list[str] = []
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-CCCCCCCCCCCCCCCCCCCCCCCC")

    result = run_guarded_live_demo_capture(
        fixture,
        reviewer="Faber test reviewer",
        reviewed_at="2026-07-26T00:00:00+00:00",
        review_manifest_path=repository / ".faber" / "review.json",
        capture_record=_fake_live_capture(configuration, calls),
    )

    assert result["status"] == "installed-inert-reviewed"
    assert len(calls) == 2
    assert len(set(calls)) == 2
    assert result["offline_demo"]["bad"]["verdict"] == "block"  # type: ignore[index]
    assert result["offline_demo"]["repaired"]["verdict"] == "pass"  # type: ignore[index]
    assert result["privacy_audit"]["status"] == "pass"  # type: ignore[index]
    provenance = json.loads((fixture / "replays" / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "inert-reviewed"
    assert provenance["review_transaction"]["capture_mode"] == "inert-injected"
    assert review_demo_replays(fixture)["provenance"] == "inert-reviewed"
    with pytest.raises(ProofDemoError, match="live-reviewed"):
        review_demo_replays(fixture, require_live_reviewed=True)
    assert (fixture / "expected" / "blocked-report.html").is_file()
    assert (fixture / "expected" / "passing-report.html").is_file()
    assert (fixture / "expected" / "capture-manifest.json").is_file()
    assert (fixture / "expected" / "review-transaction.json").is_file()
    assert (repository / ".faber" / "review.json").is_file()

    for mutation in (
        "missing-reviewer",
        "missing-reviewed-at",
        "missing-capture-digest",
        "missing-privacy-result",
        "swapped-review-transaction",
        "development-returned-model",
        "capture-mode-relabel",
    ):
        variant = tmp_path / f"fixture-{mutation}"
        shutil.copytree(fixture, variant)
        variant_provenance_path = variant / "replays" / "provenance.json"
        variant_provenance = json.loads(variant_provenance_path.read_text(encoding="utf-8"))
        if mutation == "missing-reviewer":
            del variant_provenance["reviewer"]
        elif mutation == "missing-reviewed-at":
            del variant_provenance["reviewed_at"]
        elif mutation == "missing-capture-digest":
            del variant_provenance["review_transaction"]["capture_manifest_digest"]
        elif mutation == "missing-privacy-result":
            (variant / "expected" / "privacy-audit.json").unlink()
        elif mutation == "swapped-review-transaction":
            transaction_path = variant / "expected" / "review-transaction.json"
            transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
            transaction["reviewer"] = "different reviewer"
            transaction_path.write_text(
                canonical_json(transaction) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        elif mutation == "development-returned-model":
            variant_provenance["bundles"]["bad"]["returned_model"] = "development-fixture-not-live"
        else:
            variant_provenance["review_transaction"]["capture_mode"] = "live-provider"
        variant_provenance_path.write_text(
            canonical_json(variant_provenance) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        with pytest.raises(ProofDemoError):
            review_demo_replays(variant)


def test_guarded_live_capture_rolls_back_after_post_install_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, fixture = _guarded_capture_repository(tmp_path)
    configuration = load_proof_configuration(fixture / "proof-catalog.json")
    before = {
        path.relative_to(fixture).as_posix(): path.read_bytes()
        for path in fixture.rglob("*")
        if path.is_file()
    }
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-DDDDDDDDDDDDDDDDDDDDDDDD")

    def fail_demo(**_: object) -> ProofDemoOutcome:
        raise ProofDemoError("injected post-install failure")

    with pytest.raises(ProofDemoError, match="injected post-install failure"):
        run_guarded_live_demo_capture(
            fixture,
            reviewer="Faber test reviewer",
            reviewed_at="2026-07-26T00:00:00+00:00",
            capture_record=_fake_live_capture(configuration, []),
            demo_runner=fail_demo,
        )

    after = {
        path.relative_to(fixture).as_posix(): path.read_bytes()
        for path in fixture.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_guarded_live_capture_preflight_never_calls_provider_without_key_or_clean_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, fixture = _guarded_capture_repository(tmp_path)
    configuration = load_proof_configuration(fixture / "proof-catalog.json")
    calls: list[str] = []
    capture = _fake_live_capture(configuration, calls)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProofDemoError, match="OPENAI_API_KEY"):
        run_guarded_live_demo_capture(
            fixture,
            reviewer="Faber test reviewer",
            capture_record=capture,
        )
    assert calls == []

    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-EEEEEEEEEEEEEEEEEEEEEEEE")
    (repository / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ProofDemoError, match="clean Git worktree"):
        run_guarded_live_demo_capture(
            fixture,
            reviewer="Faber test reviewer",
            capture_record=capture,
        )
    assert calls == []
