from pathlib import Path

from faber.data_rights import (
    ConsentGrant,
    DatasetExportPolicy,
    TrainingUsePolicy,
)
from faber.datasets import export_trajectories_jsonl
from faber.digests import sha256_digest
from faber.redaction import (
    PrivateTraceEnvelope,
    TraceVisibility,
    detect_sensitive_fields,
    redact_trace_events,
)
from faber.traces import RedactionPolicy, TraceEvent, TrajectoryConsent
from faber.trajectories import build_demo_trajectory

CREATED_AT = "2026-01-01T00:00:00Z"


def _event() -> TraceEvent:
    return TraceEvent(
        id="trace-event_private",
        created_at=CREATED_AT,
        attempt_id="attempt_private",
        sequence=0,
        event_type="tool.call",
        observed_at=CREATED_AT,
        payload={
            "authorization": "Bearer fixture-secret-value",
            "context": {"private_prompt": "do not export", "public": "ok"},
        },
        trust_level="runner_attested",
    )


def _policy() -> RedactionPolicy:
    return RedactionPolicy(
        id="redaction-policy_private",
        created_at=CREATED_AT,
        name="Private trace policy",
        field_paths=["context.private_prompt"],
        excluded_event_types=["context.private_reasoning"],
        detect_secrets=True,
    )


def _public_record() -> dict[str, object]:
    record = build_demo_trajectory().to_dict()
    uses = ["public_dataset"]
    consent = TrajectoryConsent(
        id="trajectory-consent_public",
        created_at=CREATED_AT,
        training_use_allowed=True,
        allowed_uses=uses,
        license_ref="fixture-license",
        grants=[
            ConsentGrant(
                party="solver_operator",
                actor_ref="worker_demo",
                allowed_uses=uses,
                granted_at=CREATED_AT,
                provenance="self_attested",
            ),
            ConsentGrant(
                party="repo_owner_customer",
                actor_ref="owner_demo",
                allowed_uses=uses,
                granted_at=CREATED_AT,
                provenance="repo_owner_verified",
            ),
        ],
    )
    record["attempt_manifest"] = {"training_consent": consent.to_dict()}
    record["contract"]["repository_training_policy"] = TrainingUsePolicy(
        id="training-use-policy_public",
        created_at=CREATED_AT,
        allowed_uses=uses,
        visibility="public",
        public_export_allowed=True,
    ).to_dict()
    return record


def test_sensitive_fields_and_secret_values_are_redacted() -> None:
    events, report = redact_trace_events(
        [_event()],
        _policy(),
        report_id="redaction-report_private",
        created_at=CREATED_AT,
    )

    assert events[0].payload["authorization"] == "[redacted]"
    assert events[0].payload["context"]["private_prompt"] == "[redacted]"
    assert events[0].payload["context"]["public"] == "ok"
    assert sorted(report.redacted_field_paths) == [
        "events[0].payload.authorization",
        "events[0].payload.context.private_prompt",
    ]


def test_redaction_report_is_stable_and_digestible() -> None:
    _, left = redact_trace_events(
        [_event()],
        _policy(),
        report_id="redaction-report_stable",
        created_at=CREATED_AT,
    )
    _, right = redact_trace_events(
        [_event()],
        _policy(),
        report_id="redaction-report_stable",
        created_at=CREATED_AT,
    )

    assert left.digest() == right.digest()
    assert left.original_digest == sha256_digest([_event().to_dict()])
    assert left.redacted_digest != left.original_digest


def test_private_trace_is_excluded_from_public_dataset_export(tmp_path: Path) -> None:
    record = _public_record()
    record["private_trace_envelope"] = PrivateTraceEnvelope(
        trace_digest=sha256_digest("private trace"),
        visibility=TraceVisibility.PRIVATE,
        redaction_required_for_export=True,
        redaction_report_digest=None,
    ).to_dict()

    manifest = export_trajectories_jsonl(
        [record],
        tmp_path / "public.jsonl",
        export_policy=DatasetExportPolicy(purpose="public_dataset", public=True),
    )

    assert manifest.record_count == 0


def test_redacted_private_trace_can_be_exported_inside_authorized_boundary(
    tmp_path: Path,
) -> None:
    record = _public_record()
    report_digest = sha256_digest("redaction report")
    record["private_trace_envelope"] = PrivateTraceEnvelope(
        trace_digest=sha256_digest("private trace"),
        visibility=TraceVisibility.RESTRICTED,
        redaction_required_for_export=True,
        redaction_report_digest=report_digest,
    ).to_dict()
    record["contract"]["repository_training_policy"]["visibility"] = "restricted"
    record["contract"]["repository_training_policy"]["public_export_allowed"] = False

    manifest = export_trajectories_jsonl(
        [record],
        tmp_path / "restricted.jsonl",
        export_policy=DatasetExportPolicy(
            purpose="public_dataset",
            include_restricted=True,
        ),
    )

    assert manifest.record_count == 1


def test_obvious_secret_like_strings_are_flagged_without_storing_value() -> None:
    findings = detect_sensitive_fields(
        {"token": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"}
    )

    assert findings[0]["field_path"] == "token"
    assert findings[0]["pattern"] in {"github_token", "sensitive_key"}
    assert findings[0]["value_digest"].startswith("sha256:")
    assert "ghp_" not in str(findings)
