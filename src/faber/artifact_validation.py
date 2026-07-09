"""Structured validation reports for attempt, trace, and trajectory artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from faber.attempt_manifests import load_attempt_manifest
from faber.digests import sha256_digest
from faber.errors import FaberError
from faber.traces import read_trace_jsonl
from faber.trajectory_quality import validate_trajectory_quality

VALID_EXIT = 0
INVALID_EXIT = 1
WARNING_EXIT = 2


@dataclass(frozen=True)
class ArtifactValidationResult:
    artifact_type: str
    path: str
    status: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)
    warnings: list[dict[str, object]] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        if self.status == "valid":
            return VALID_EXIT
        if self.status == "warning":
            return WARNING_EXIT
        return INVALID_EXIT

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type,
            "path": self.path,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def validate_attempt_file(path: str | Path) -> ArtifactValidationResult:
    artifact_path = Path(path)
    try:
        manifest = load_attempt_manifest(artifact_path)
    except (FaberError, json.JSONDecodeError, OSError) as exc:
        return _invalid_result("attempt_manifest", artifact_path, exc)
    return ArtifactValidationResult(
        artifact_type="attempt_manifest",
        path=str(artifact_path),
        status="valid",
        summary="Attempt manifest is valid.",
        details={
            "attempt_id": manifest.attempt_id,
            "evidence_level": manifest.evidence_level,
            "training_consent": (
                manifest.training_consent.training_use_allowed
                if manifest.training_consent is not None
                else False
            ),
            "redaction_policy_id": manifest.redaction_policy.id,
            "digest": manifest.digest(),
        },
    )


def validate_trace_file(path: str | Path) -> ArtifactValidationResult:
    artifact_path = Path(path)
    try:
        events = read_trace_jsonl(artifact_path)
    except (FaberError, json.JSONDecodeError, OSError) as exc:
        return _invalid_result("trace", artifact_path, exc)
    if not events:
        return ArtifactValidationResult(
            artifact_type="trace",
            path=str(artifact_path),
            status="invalid",
            summary="Trace is invalid: at least one event is required.",
            errors=[
                {
                    "field": "events",
                    "message": "events must contain at least one trace event",
                    "expected": "one or more ordered trace event objects",
                }
            ],
        )
    attempt_ids = {event.attempt_id for event in events}
    sequences = [event.sequence for event in events]
    errors: list[dict[str, object]] = []
    if len(attempt_ids) != 1:
        errors.append(
            {
                "field": "attempt_id",
                "message": "trace events refer to multiple attempts",
                "expected": "one attempt_id for the complete trace",
            }
        )
    if sequences != list(range(len(events))):
        errors.append(
            {
                "field": "sequence",
                "message": "trace sequence is not contiguous and ordered",
                "expected": f"integer sequence 0 through {len(events) - 1}",
            }
        )
    if errors:
        return ArtifactValidationResult(
            artifact_type="trace",
            path=str(artifact_path),
            status="invalid",
            summary="Trace is invalid; fix the reported event fields.",
            details={"event_count": len(events)},
            errors=errors,
        )
    redacted_count = sum(event.redaction_policy_id is not None for event in events)
    return ArtifactValidationResult(
        artifact_type="trace",
        path=str(artifact_path),
        status="valid",
        summary="Trace is valid and ordered.",
        details={
            "attempt_id": events[0].attempt_id,
            "event_count": len(events),
            "event_types": sorted({event.event_type for event in events}),
            "redacted_event_count": redacted_count,
            "digest": sha256_digest(artifact_path.read_bytes()),
        },
    )


def validate_trajectory_file(
    path: str | Path,
    *,
    quality_only: bool = False,
) -> ArtifactValidationResult:
    artifact_path = Path(path)
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return _invalid_result("trajectory", artifact_path, exc)
    if not isinstance(payload, dict):
        return ArtifactValidationResult(
            artifact_type="trajectory",
            path=str(artifact_path),
            status="invalid",
            summary="Trajectory is invalid: the root value must be an object.",
            errors=[
                {
                    "field": "$",
                    "message": "trajectory root must be a JSON object",
                    "expected": "object",
                }
            ],
        )
    report = validate_trajectory_quality(
        payload,
        report_id=f"trajectory-validation-report_{payload.get('id', 'unknown')}",
        created_at=str(payload.get("created_at", "1970-01-01T00:00:00Z")),
    )
    missing_fields = sorted(
        {
            str(issue.get("field"))
            for issue in report.issues
            if issue.get("severity") == "blocker"
        }
    )
    redaction_status = "not_applicable"
    if report.quality_tier in {"trace", "episode"}:
        redaction_status = (
            "redacted"
            if report.process_evidence.trace_completeness.redacted
            else "unredacted"
        )
    details: dict[str, object] = {
        "trajectory_id": report.trajectory_id,
        "quality_tier": report.quality_tier,
        "evidence_level": report.evidence_level,
        "audit_eligible": report.usable_for_audit,
        "supervised_learning_eligible": report.usable_for_supervised_training,
        "rl_grade_eligible": report.is_rl_grade,
        "training_consent": report.training_eligibility.eligible,
        "training_export_eligible": (
            report.training_eligibility.eligible
            and (
                report.usable_for_supervised_training
                or report.usable_for_rl_training
            )
        ),
        "redaction_status": redaction_status,
        "missing_fields": missing_fields,
        "requirement_satisfied": report.meets_requirement,
        "report": report.to_dict(),
    }
    structurally_invalid = not report.usable_for_audit or not report.meets_requirement
    if structurally_invalid:
        return ArtifactValidationResult(
            artifact_type="trajectory",
            path=str(artifact_path),
            status="invalid",
            summary="Trajectory is invalid for its task requirement.",
            details=details,
            errors=report.issues,
        )
    if not report.is_rl_grade:
        summary = (
            "Trajectory is valid but not RL-grade."
            if not quality_only
            else "Trajectory quality is valid with non-RL-grade evidence."
        )
        return ArtifactValidationResult(
            artifact_type="trajectory",
            path=str(artifact_path),
            status="warning",
            summary=summary,
            details=details,
            warnings=report.issues,
        )
    warnings = [
        issue for issue in report.issues if issue.get("severity") == "warning"
    ]
    return ArtifactValidationResult(
        artifact_type="trajectory",
        path=str(artifact_path),
        status="warning" if warnings else "valid",
        summary=(
            "Trajectory is valid and RL-grade with warnings."
            if warnings
            else "Trajectory is valid and RL-grade."
        ),
        details=details,
        warnings=warnings,
    )


def _invalid_result(
    artifact_type: str,
    path: Path,
    exc: Exception,
) -> ArtifactValidationResult:
    message = str(exc)
    field_name = "$"
    expected = "valid JSON matching the Faber schema"
    if " must " in message:
        field_name, expectation = message.split(" must ", maxsplit=1)
        expected = f"must {expectation}"
    elif isinstance(exc, json.JSONDecodeError):
        field_name = f"line {exc.lineno}, column {exc.colno}"
        expected = "valid JSON syntax"
    return ArtifactValidationResult(
        artifact_type=artifact_type,
        path=str(path),
        status="invalid",
        summary=f"{artifact_type.replace('_', ' ').title()} is invalid.",
        errors=[
            {
                "field": field_name,
                "message": message,
                "expected": expected,
            }
        ],
    )
