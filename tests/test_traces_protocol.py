from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.traces import (
    AttemptManifest,
    RedactionPolicy,
    TraceEvent,
    evidence_level,
    read_trace_jsonl,
    trace_manifest_from_events,
    trajectory_evidence_bundle,
    write_trace_jsonl,
)

CREATED_AT = "2026-01-01T00:00:00Z"


def _redaction_policy() -> RedactionPolicy:
    return RedactionPolicy(
        id="redaction-policy_trace",
        created_at=CREATED_AT,
        name="Default trace redaction",
        field_paths=["secret", "context.private_prompt"],
        allow_raw_trace=False,
    )


def _attempt_manifest(*, evidence_level_value: int = 1) -> AttemptManifest:
    return AttemptManifest(
        id="attempt-manifest_trace",
        created_at=CREATED_AT,
        task_contract_id="task-contract_trace",
        task_contract_digest=sha256_digest("contract"),
        attempt_id="attempt_trace",
        base_revision="base",
        candidate_revision="candidate",
        worker_id="worker_trace",
        evidence_level=evidence_level_value,
        redaction_policy=_redaction_policy(),
        model_metadata={"disclosure": "coarse", "family": "local-open-weight"},
        harness_metadata={"family": "fake-harness", "version": "1"},
        runner_metadata={"runner": "faber-runner", "version": "1"},
        environment_metadata={"platform": "NixOS", "reproducibility": "flake"},
        tool_registry_digest=sha256_digest("tools"),
        nix_flake_lock_digest=sha256_digest("flake.lock"),
        budget_metadata={"currency": "EUR", "budget_minor_units": 1000},
        cost_metadata={"currency": "EUR", "compute_minor_units": 100},
        latency_metadata={"work_seconds": 30},
        trust_level="runner_attested",
    )


def _events() -> list[TraceEvent]:
    return [
        TraceEvent(
            id="trace-event_1",
            created_at=CREATED_AT,
            attempt_id="attempt_trace",
            sequence=0,
            event_type="tool.call",
            observed_at=CREATED_AT,
            payload={
                "tool": "pytest",
                "secret": "do-not-store",
                "context": {"private_prompt": "hidden", "public": "ok"},
            },
            trust_level="runner_attested",
            provenance={"runner": "faber"},
        ),
        TraceEvent(
            id="trace-event_2",
            created_at=CREATED_AT,
            attempt_id="attempt_trace",
            sequence=1,
            event_type="verifier.result",
            observed_at=CREATED_AT,
            payload={"passed": True},
            trust_level="runner_attested",
            provenance={"runner": "faber"},
        ),
    ]


def test_each_evidence_level_validates() -> None:
    levels = [evidence_level(level) for level in range(5)]

    assert [level.level for level in levels] == [0, 1, 2, 3, 4]
    assert levels[0].name == "pr_only"
    assert levels[4].name == "replayable_episode_package"
    with pytest.raises(ValidationError, match="between 0 and 4"):
        evidence_level(5)


def test_pr_only_attempt_still_works() -> None:
    attempt = Attempt(
        id="attempt_pr_only",
        created_at=CREATED_AT,
        task_contract_id="task-contract_trace",
        worker_id="worker_trace",
        base_revision="base",
        candidate_revision="candidate",
        summary="PR-only attempt.",
        patch_digest=sha256_digest("patch"),
    )
    bundle = trajectory_evidence_bundle(evidence_level_value=0)

    assert attempt.metadata == {}
    assert bundle["richness_score"] == 0
    assert bundle["attempt_manifest"] is None


def test_redaction_removes_configured_fields() -> None:
    policy = _redaction_policy()
    event = _events()[0].redacted(policy)

    assert event.payload["secret"] == "[redacted]"
    assert event.payload["context"]["private_prompt"] == "[redacted]"
    assert event.payload["context"]["public"] == "ok"
    assert event.redaction_policy_id == policy.id


def test_trace_jsonl_round_trip_and_manifest_digest(tmp_path: Path) -> None:
    events = _events()
    out_path = tmp_path / "trace.jsonl"

    digest = write_trace_jsonl(events, out_path, redaction_policy=_redaction_policy())
    loaded = read_trace_jsonl(out_path)
    manifest = trace_manifest_from_events(
        attempt_id="attempt_trace",
        events=loaded,
        evidence_level_value=2,
        trace_jsonl_digest=digest,
        trust_level="runner_attested",
        redaction_policy=_redaction_policy(),
    )

    assert digest.startswith("sha256:")
    assert [event.event_type for event in loaded] == ["tool.call", "verifier.result"]
    assert manifest.trace_event_count == 2
    assert manifest.included_event_types == ["tool.call", "verifier.result"]


def test_manifest_and_trace_digests_are_stable(tmp_path: Path) -> None:
    left = _attempt_manifest()
    right = _attempt_manifest()
    events = _events()
    out_path = tmp_path / "trace.jsonl"

    trace_digest = write_trace_jsonl(events, out_path)
    first_manifest = trace_manifest_from_events(
        attempt_id="attempt_trace",
        events=events,
        evidence_level_value=2,
        trace_jsonl_digest=trace_digest,
        trust_level="runner_attested",
        manifest_id="trace-manifest_trace",
        created_at=CREATED_AT,
    )
    second_manifest = trace_manifest_from_events(
        attempt_id="attempt_trace",
        events=events,
        evidence_level_value=2,
        trace_jsonl_digest=trace_digest,
        trust_level="runner_attested",
        manifest_id="trace-manifest_trace",
        created_at=CREATED_AT,
    )

    assert left.digest() == right.digest()
    assert first_manifest.digest() == second_manifest.digest()
    assert first_manifest.to_dict()["trace_jsonl_digest"] == second_manifest.to_dict()[
        "trace_jsonl_digest"
    ]


def test_richer_trace_produces_richer_trajectory_evidence(tmp_path: Path) -> None:
    events = _events()
    trace_digest = write_trace_jsonl(events, tmp_path / "trace.jsonl")
    manifest = _attempt_manifest(evidence_level_value=2)
    trace_manifest = trace_manifest_from_events(
        attempt_id=manifest.attempt_id,
        events=events,
        evidence_level_value=2,
        trace_jsonl_digest=trace_digest,
        trust_level="runner_attested",
    )

    pr_only = trajectory_evidence_bundle(evidence_level_value=0)
    runner_trace = trajectory_evidence_bundle(
        evidence_level_value=2,
        attempt_manifest=manifest,
        trace_manifest=trace_manifest,
    )

    assert pr_only["richness_score"] == 0
    assert runner_trace["richness_score"] == 2
    assert runner_trace["attempt_manifest"] is not None
    assert runner_trace["trace_manifest"] is not None
