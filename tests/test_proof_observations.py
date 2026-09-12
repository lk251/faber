from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from faber.cli import main
from faber.digests import sha256_digest
from faber.proof_observations import (
    ProofObservationError,
    ProofObservationRun,
    record_proof_feedback,
)
from faber.proof_planning import ProofPlanningError, ProofPlanningRequest, ProofPlanningResult
from faber.proof_product import ProofProductError, ProofRunOutcome, run_proof_product
from faber.proof_workflow import ProofWorkflowError, ProofWorkflowResult
from faber.proofs import ModelRunEvidence, ProofDecision
from test_proof_product import _fixture

Fixture = tuple[Path, str, str, Path, Path, Path]


def _run(fixture: Fixture, *, observations: Path | None = None) -> ProofRunOutcome:
    repository, base, candidate, task, catalog, replay = fixture
    return run_proof_product(
        repository=repository,
        task_path=task,
        catalog_path=catalog,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay,
        observations_directory=observations,
    )


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _events(directory: Path) -> list[dict[str, object]]:
    return [_json(path) for path in sorted(directory.glob("*-event.json"))]


def test_proposal_is_saved_before_planner_failure_without_exception_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"
    clock = "2030-01-02T03:04:05Z"
    monkeypatch.setattr("faber.proof_observations.utc_now", lambda: clock)

    def fail_planner(*, request: ProofPlanningRequest, **_: object) -> None:
        runs = list(observations.iterdir())
        assert len(runs) == 1
        assert _json(runs[0] / "planning-request.json") == request.to_dict()
        assert _events(runs[0])[0]["observed_at"] == clock
        model_run = ModelRunEvidence(
            provider_adapter_id="test-adapter",
            requested_model_id="gpt-5.6",
            prompt_template_version=request.prompt_template_version,
            request_digest=request.digest(),
            structured_response_digest=sha256_digest("refused"),
            response_schema_version=request.response_schema_version,
            mode="replay",
            latency_ms=123,
            input_tokens=42,
            output_tokens=7,
            refusal="SECRET-REFUSAL-TEXT",
        )
        raise ProofPlanningError(
            "refusal", "SECRET-PROVIDER-TEXT-DO-NOT-ARCHIVE", model_run=model_run
        )

    monkeypatch.setattr("faber.proof_product.plan_proof_request", fail_planner)
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=observations)
    assert error.value.category == "refusal"
    run = next(observations.iterdir())
    events = _events(run)
    assert [event["event_type"] for event in events] == [
        "policy.proposal_observed",
        "policy.proposal_failed",
    ]
    assert events[1]["payload"]["error_code"] == "refusal"
    assert events[0]["payload"]["requested_model_id"] == "gpt-5.6"
    assert events[0]["payload"]["mode"] == "replay"
    assert events[0]["payload"]["dry_run"] is False
    assert events[1]["payload"]["input_tokens"] == 42
    assert events[1]["payload"]["output_tokens"] == 7
    assert events[1]["payload"]["latency_ms"] == 123
    assert events[0]["payload"]["considered_alternatives"] is None
    assert all("SECRET-" not in p.read_text() for p in run.iterdir())
    record_proof_feedback(run, reviewer_ref="test", outcome="inconclusive", reason_codes=["other"])
    assert _events(run)[-1]["payload"]["feedback_target"] == "planning_request"
    assert not (fixture[0] / ".faber" / "proof").exists()


def test_repeated_runs_keep_history_and_capture_does_not_change_plan_or_verdict(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, candidate_text="bad\n")
    observations = fixture[0] / ".faber" / "observations"
    baseline = _run(fixture)
    first = _run(fixture, observations=observations)
    first_run = next(observations.iterdir())
    original = {p.name: p.read_bytes() for p in first_run.iterdir()}
    second = _run(fixture, observations=observations)
    assert baseline.verdict == first.verdict == second.verdict == "block"
    assert len(list(observations.iterdir())) == 2
    assert original == {p.name: p.read_bytes() for p in first_run.iterdir()}
    archived = ProofWorkflowResult.from_dict(_json(first_run / "workflow-result.json"))
    assert archived.evidence and archived.verifier_runs and archived.verification_receipts
    assert archived.timings
    verification = _events(first_run)[2]["payload"]
    assert verification["workflow_reference"]["record_digest"] == archived.digest()
    for record in ("planning_request", "planning_result", "proof_plan", "proof_policy"):
        assert baseline.summary["record_digests"][record] == first.summary["record_digests"][record]
    decision_before = (fixture[0] / ".faber" / "proof" / "proof-decision.json").read_bytes()
    record_proof_feedback(
        first_run,
        reviewer_ref="owner:test",
        outcome="accepted",
        reason_codes=["useful_missing_check"],
    )
    feedback = _events(first_run)[-1]
    assert feedback["event_type"] == "policy.owner_feedback_reported"
    assert feedback["payload"]["authority"] == "none"
    assert feedback["payload"]["training_permission_granted"] is False
    assert feedback["payload"]["proof_plan_digest"] == first.summary["record_digests"]["proof_plan"]
    assert feedback["payload"]["counterfactual_outcome"] is None
    assert decision_before == (fixture[0] / ".faber" / "proof" / "proof-decision.json").read_bytes()


@pytest.mark.parametrize(
    "path", [".", ".git/history", "source/history", ".faber", ".faber/proof", ".faber/proof/events"]
)
def test_unsafe_or_overlapping_destination_fails_before_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")

    def forbidden(**_: object) -> None:
        pytest.fail("planner must not run when initial capture fails")

    monkeypatch.setattr("faber.proof_product.plan_proof_request", forbidden)
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=fixture[0] / path)
    assert error.value.category == "observation_error"


def test_capture_byte_limit_fails_explicitly_before_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    monkeypatch.setattr("faber.proof_observations.MAX_OBSERVATION_BYTES", 128)
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=fixture[0] / ".faber" / "observations")
    assert error.value.category == "observation_error"
    assert "byte limit" in error.value.failure


def test_workflow_failure_is_retained_as_closed_phase_without_raw_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"

    def fail_workflow(**_: object) -> None:
        raise ProofWorkflowError("workflow_test_failure", "SECRET-WORKFLOW-DETAIL")

    monkeypatch.setattr("faber.proof_product.run_proof_workflow", fail_workflow)
    with pytest.raises(ProofProductError):
        _run(fixture, observations=observations)
    run = next(observations.iterdir())
    events = _events(run)
    assert events[-1]["event_type"] == "policy.run_failed"
    assert events[-1]["payload"]["phase"] == "execution"
    assert all("SECRET-WORKFLOW" not in p.read_text() for p in run.iterdir())


def test_terminal_capture_failure_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import faber.proof_observations as observations_module

    fixture = _fixture(tmp_path, candidate_text="good\n")
    original = observations_module._event

    def fail_terminal(
        directory: Path, attempt_id: str, event_type: str, payload: dict[str, object]
    ) -> None:
        if event_type != "policy.proposal_observed":
            raise ProofObservationError("simulated storage failure")
        original(directory, attempt_id, event_type, payload)

    monkeypatch.setattr(observations_module, "_event", fail_terminal)
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=fixture[0] / ".faber" / "observations")
    assert error.value.category == "observation_error"


def test_publication_failure_is_observed_without_exception_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"

    def fail_publish(*_: object) -> None:
        raise OSError("SECRET-PUBLISH-DETAIL")

    monkeypatch.setattr("faber.proof_product._publish_stage", fail_publish)
    with pytest.raises(ProofProductError):
        _run(fixture, observations=observations)
    run = next(observations.iterdir())
    assert _events(run)[-1]["payload"]["phase"] == "publication"
    assert all("SECRET-PUBLISH" not in p.read_text() for p in run.iterdir())


@pytest.mark.parametrize(
    "mutation", ["request_replaced", "proposal_missing", "result_replaced", "result_missing"]
)
def test_feedback_rejects_missing_or_changed_original_records(
    tmp_path: Path, mutation: str
) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"
    _run(fixture, observations=observations)
    run = next(observations.iterdir())
    if mutation == "proposal_missing":
        (run / "000000-event.json").unlink()
    elif mutation == "result_missing":
        (run / "planning-result.json").unlink()
    elif mutation == "request_replaced":
        request = ProofPlanningRequest.from_dict(_json(run / "planning-request.json"))
        from faber.canonical_json import canonical_json

        (run / "planning-request.json").write_text(
            canonical_json(replace(request, task_title="different known input").to_dict()) + "\n",
            encoding="utf-8",
        )
    else:
        result = ProofPlanningResult.from_dict(_json(run / "planning-result.json"))
        from faber.canonical_json import canonical_json

        (run / "planning-result.json").write_text(
            canonical_json(replace(result, uncertainty_notes=["changed"]).to_dict()) + "\n",
            encoding="utf-8",
        )
    with pytest.raises(ProofObservationError):
        record_proof_feedback(run, reviewer_ref="test", outcome="accepted", reason_codes=["other"])


def test_feedback_rejects_symlinked_request_and_observation_destination(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"
    _run(fixture, observations=observations)
    run = next(observations.iterdir())
    saved = tmp_path / "saved-request.json"
    shutil.copyfile(run / "planning-request.json", saved)
    link = tmp_path / "link-check"
    try:
        link.symlink_to(observations, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=link / "nested")
    assert error.value.category == "observation_error"
    (run / "planning-request.json").unlink()
    (run / "planning-request.json").symlink_to(saved)
    with pytest.raises(ProofObservationError):
        record_proof_feedback(run, reviewer_ref="test", outcome="accepted", reason_codes=["other"])


def test_record_helpers_reject_mixed_plans_and_never_overwrite_result(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, candidate_text="good\n")
    observations = fixture[0] / ".faber" / "observations"
    _run(fixture, observations=observations)
    directory = next(observations.iterdir())
    request = ProofPlanningRequest.from_dict(_json(directory / "planning-request.json"))
    result = ProofPlanningResult.from_dict(_json(directory / "planning-result.json"))
    run = ProofObservationRun(directory, request)
    before = (directory / "planning-result.json").read_bytes()
    with pytest.raises(ProofObservationError, match="exclusively"):
        run.record_result(result)
    assert before == (directory / "planning-result.json").read_bytes()
    decision = ProofDecision.from_dict(_json(directory / "proof-decision.json"))
    with pytest.raises(ProofObservationError, match="does not match"):
        run.record_decision(replace(decision, proof_plan_digest=sha256_digest("other plan")))


def test_cli_can_capture_no_key_dry_run(tmp_path: Path) -> None:
    repository, base, candidate, task, catalog, replay = _fixture(tmp_path, candidate_text="good\n")
    observations = repository / ".faber" / "observations"
    assert (
        main(
            [
                "proof",
                "--repo",
                str(repository),
                "--task",
                str(task),
                "--catalog",
                str(catalog),
                "--base",
                base,
                "--candidate",
                candidate,
                "--mode",
                "replay",
                "--replay",
                str(replay),
                "--observations-dir",
                str(observations),
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    events = _events(next(observations.iterdir()))
    assert [event["event_type"] for event in events] == [
        "policy.proposal_observed",
        "policy.proposal_result",
    ]
    assert events[0]["payload"]["dry_run"] is True


@pytest.mark.skipif(os.name != "nt", reason="Windows path aliases only")
def test_windows_extended_and_short_path_aliases_cannot_bypass_output_boundary(
    tmp_path: Path,
) -> None:
    import ctypes

    fixture = _fixture(tmp_path, candidate_text="good\n")
    _run(fixture)
    output = fixture[0] / ".faber" / "proof"
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=Path("\\\\?\\" + str(output)))
    assert error.value.category == "observation_error"
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(output), buffer, len(buffer))
    assert 0 < length < len(buffer)
    with pytest.raises(ProofProductError) as error:
        _run(fixture, observations=Path(buffer.value))
    assert error.value.category == "observation_error"
