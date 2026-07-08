from pathlib import Path

from faber.adapters.hermes import adapt_hermes_trace_file
from faber.digests import sha256_digest
from faber.traces import (
    AttemptManifest,
    RedactionPolicy,
    read_trace_jsonl,
    trajectory_evidence_bundle,
)

CREATED_AT = "2026-01-01T00:00:00Z"
FIXTURE = Path("tests/fixtures/hermes/fake_trace.json")


def _redaction_policy() -> RedactionPolicy:
    return RedactionPolicy(
        id="redaction-policy_hermes_trace",
        created_at=CREATED_AT,
        name="Hermes-like fixture redaction",
        field_paths=[
            "context.private_prompt",
            "credentials.api_key",
            "result.raw_output",
        ],
        allow_raw_trace=False,
    )


def _attempt_manifest() -> AttemptManifest:
    return AttemptManifest(
        id="attempt-manifest_hermes_fake",
        created_at=CREATED_AT,
        task_contract_id="task-contract_hermes_nixos_lazy_deps_48628",
        task_contract_digest=sha256_digest("hermes task contract"),
        attempt_id="attempt_hermes_fake_48628",
        base_revision="base",
        candidate_revision="candidate",
        worker_id="worker_hermes_fake",
        evidence_level=3,
        redaction_policy=_redaction_policy(),
        model_metadata={"disclosure": "coarse", "family": "fake-local-model"},
        harness_metadata={"adapter": "faber.adapters.hermes.fake_trace.v1"},
        runner_metadata={"runner": "fake-offline-runner"},
        environment_metadata={"platform": "Linux", "reproducibility": "declared"},
        trust_level="self_attested",
    )


def test_fake_hermes_trace_maps_to_faber_events() -> None:
    export = adapt_hermes_trace_file(FIXTURE)

    assert export.attempt_id == "attempt_hermes_fake_48628"
    assert export.raw_trace_digest.startswith("sha256:")
    assert [event.sequence for event in export.events] == list(range(8))
    assert [event.event_type for event in export.events] == [
        "context.loaded",
        "context.read",
        "action.selected",
        "tool.call",
        "verification.result",
        "failure.observed",
        "intervention.applied",
        "outcome.reported",
    ]
    assert [event.provenance["source_event_sequence"] for event in export.events] == [
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
    ]


def test_redaction_is_applied_when_writing_adapter_trace_jsonl(tmp_path: Path) -> None:
    export = adapt_hermes_trace_file(FIXTURE, redaction_policy=_redaction_policy())

    trace_digest = export.write_jsonl(tmp_path / "trace.jsonl")
    loaded = read_trace_jsonl(tmp_path / "trace.jsonl")

    assert trace_digest.startswith("sha256:")
    assert loaded[0].payload["context"]["private_prompt"] == "[redacted]"
    assert loaded[3].payload["credentials"]["api_key"] == "[redacted]"
    assert loaded[4].payload["result"]["raw_output"] == "[redacted]"
    assert {event.redaction_policy_id for event in loaded} == {"redaction-policy_hermes_trace"}


def test_trace_manifest_digest_is_stable(tmp_path: Path) -> None:
    left = adapt_hermes_trace_file(FIXTURE, redaction_policy=_redaction_policy())
    right = adapt_hermes_trace_file(FIXTURE, redaction_policy=_redaction_policy())

    left_digest = left.write_jsonl(tmp_path / "left.jsonl")
    right_digest = right.write_jsonl(tmp_path / "right.jsonl")
    left_manifest = left.trace_manifest(
        trace_jsonl_digest=left_digest,
        manifest_id="trace-manifest_hermes_fake",
        created_at=CREATED_AT,
    )
    right_manifest = right.trace_manifest(
        trace_jsonl_digest=right_digest,
        manifest_id="trace-manifest_hermes_fake",
        created_at=CREATED_AT,
    )

    assert left.raw_trace_digest == right.raw_trace_digest
    assert left_digest == right_digest
    assert left_manifest.digest() == right_manifest.digest()
    assert left_manifest.included_event_types == [
        "action.selected",
        "context.loaded",
        "context.read",
        "failure.observed",
        "intervention.applied",
        "outcome.reported",
        "tool.call",
        "verification.result",
    ]


def test_adapter_output_can_enrich_trajectory_evidence(tmp_path: Path) -> None:
    export = adapt_hermes_trace_file(FIXTURE, redaction_policy=_redaction_policy())
    trace_digest = export.write_jsonl(tmp_path / "trace.jsonl")
    trace_manifest = export.trace_manifest(
        trace_jsonl_digest=trace_digest,
        manifest_id="trace-manifest_hermes_fake",
        created_at=CREATED_AT,
    )

    bundle = trajectory_evidence_bundle(
        evidence_level_value=3,
        attempt_manifest=_attempt_manifest(),
        trace_manifest=trace_manifest,
    )

    assert bundle["richness_score"] == 3
    assert bundle["trace_manifest"] is not None
    assert trace_manifest.raw_trace_digest == export.raw_trace_digest
