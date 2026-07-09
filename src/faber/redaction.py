"""Deterministic trace redaction and private-trace export policy."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from faber import schemas
from faber.data_rights import DatasetExportPolicy
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.traces import RedactionPolicy, TraceEvent
from faber.validation import (
    require_digest,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
    require_string_list,
)


class TraceVisibility:
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"


TRACE_VISIBILITIES = {
    TraceVisibility.PUBLIC,
    TraceVisibility.RESTRICTED,
    TraceVisibility.PRIVATE,
}


@dataclass(frozen=True)
class SensitiveFieldPattern:
    """A local detector pattern that never retains the matched secret value."""

    name: str
    value_pattern: str
    field_name_pattern: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.value_pattern, "value_pattern")
        try:
            re.compile(self.value_pattern)
            if self.field_name_pattern is not None:
                re.compile(self.field_name_pattern)
        except re.error as exc:
            raise ValidationError(f"invalid sensitive field pattern {self.name}: {exc}") from exc

    def matches(self, field_name: str, value: str) -> bool:
        field_matches = self.field_name_pattern is None or re.search(
            self.field_name_pattern,
            field_name,
            flags=re.IGNORECASE,
        )
        return bool(field_matches and re.search(self.value_pattern, value))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value_pattern": self.value_pattern,
            "field_name_pattern": self.field_name_pattern,
        }


def default_sensitive_patterns() -> list[SensitiveFieldPattern]:
    return [
        SensitiveFieldPattern(
            name="sensitive_key",
            field_name_pattern=r"(^|[_-])(api[_-]?key|authorization|password|secret|token)($|[_-])",
            value_pattern=r".+",
        ),
        SensitiveFieldPattern(
            name="github_token",
            value_pattern=r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
        ),
        SensitiveFieldPattern(
            name="aws_access_key",
            value_pattern=r"\bAKIA[0-9A-Z]{16}\b",
        ),
        SensitiveFieldPattern(
            name="bearer_token",
            value_pattern=r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}",
        ),
        SensitiveFieldPattern(
            name="private_key",
            value_pattern=r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        ),
    ]


@dataclass(frozen=True)
class RedactionReport:
    policy_id: str
    original_digest: str
    redacted_digest: str
    redacted_field_paths: list[str]
    excluded_event_types: list[str]
    findings: list[dict[str, object]]
    detector_version: str = "faber-local-secrets-v1"
    id: str = field(default_factory=lambda: new_id("redaction-report"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.REDACTION_REPORT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.REDACTION_REPORT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.policy_id, "policy_id")
        require_digest(self.original_digest, "original_digest")
        require_digest(self.redacted_digest, "redacted_digest")
        require_string_list(self.redacted_field_paths, "redacted_field_paths")
        require_string_list(self.excluded_event_types, "excluded_event_types")
        if any(not isinstance(finding, dict) for finding in self.findings):
            raise ValidationError("findings must contain mappings")
        require_non_empty_string(self.detector_version, "detector_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "policy_id": self.policy_id,
            "original_digest": self.original_digest,
            "redacted_digest": self.redacted_digest,
            "redacted_field_paths": self.redacted_field_paths,
            "excluded_event_types": self.excluded_event_types,
            "findings": self.findings,
            "detector_version": self.detector_version,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class PrivateTraceEnvelope:
    """Reference to private trace content without embedding that content."""

    trace_digest: str
    visibility: str
    redaction_required_for_export: bool
    redaction_report_digest: str | None = None
    content_ref: str | None = None
    raw_content_retained: bool = True
    id: str = field(default_factory=lambda: new_id("private-trace-envelope"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.PRIVATE_TRACE_ENVELOPE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PRIVATE_TRACE_ENVELOPE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_digest(self.trace_digest, "trace_digest")
        if self.visibility not in TRACE_VISIBILITIES:
            raise ValidationError(
                f"visibility must be one of {sorted(TRACE_VISIBILITIES)}"
            )
        if not isinstance(self.redaction_required_for_export, bool):
            raise ValidationError("redaction_required_for_export must be a boolean")
        require_optional_digest(self.redaction_report_digest, "redaction_report_digest")
        if self.content_ref is not None:
            require_non_empty_string(self.content_ref, "content_ref")
        if not isinstance(self.raw_content_retained, bool):
            raise ValidationError("raw_content_retained must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "trace_digest": self.trace_digest,
            "visibility": self.visibility,
            "redaction_required_for_export": self.redaction_required_for_export,
            "redaction_report_digest": self.redaction_report_digest,
            "content_ref": self.content_ref,
            "raw_content_retained": self.raw_content_retained,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def detect_sensitive_fields(
    payload: Mapping[str, object],
    *,
    patterns: list[SensitiveFieldPattern] | None = None,
) -> list[dict[str, object]]:
    """Find obvious local secret patterns without retaining matched values."""

    configured = patterns or default_sensitive_patterns()
    findings: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    def visit(value: object, path: list[str]) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                visit(nested, [*path, str(key)])
            return
        if isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, [*path, str(index)])
            return
        if not isinstance(value, str):
            return
        field_name = path[-1] if path else "value"
        field_path = ".".join(path)
        for pattern in configured:
            if pattern.matches(field_name, value):
                key = (field_path, pattern.name)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "field_path": field_path,
                        "pattern": pattern.name,
                        "value_digest": sha256_digest(value),
                    }
                )

    visit(payload, [])
    return sorted(findings, key=lambda item: (str(item["field_path"]), str(item["pattern"])))


def redact_trace_events(
    events: list[TraceEvent],
    policy: RedactionPolicy,
    *,
    patterns: list[SensitiveFieldPattern] | None = None,
    report_id: str | None = None,
    created_at: str | None = None,
) -> tuple[list[TraceEvent], RedactionReport]:
    """Apply field and event redaction while preserving ordered trace structure."""

    original_records = [event.to_dict() for event in events]
    redacted_events: list[TraceEvent] = []
    redacted_paths: set[str] = set()
    excluded: set[str] = set()
    all_findings: list[dict[str, object]] = []
    for index, event in enumerate(events):
        if event.event_type in policy.excluded_event_types:
            excluded.add(event.event_type)
            continue
        raw_payload = copy.deepcopy(event.payload)
        redacted_payload = policy.apply(raw_payload)
        for field_path in policy.field_paths:
            if _path_exists(raw_payload, field_path.split(".")):
                redacted_paths.add(f"events[{index}].payload.{field_path}")
        findings = detect_sensitive_fields(raw_payload, patterns=patterns)
        if policy.detect_secrets:
            for finding in findings:
                field_path = str(finding["field_path"])
                _replace_path(redacted_payload, field_path.split("."), policy.replacement)
                redacted_paths.add(f"events[{index}].payload.{field_path}")
        for finding in findings:
            all_findings.append(
                {"event_index": index, "event_type": event.event_type, **finding}
            )
        redacted_events.append(
            TraceEvent(
                id=event.id,
                created_at=event.created_at,
                attempt_id=event.attempt_id,
                sequence=event.sequence,
                event_type=event.event_type,
                payload=redacted_payload,
                observed_at=event.observed_at,
                trust_level=event.trust_level,
                provenance=event.provenance,
                redaction_policy_id=policy.id,
            )
        )
    redacted_records = [event.to_dict() for event in redacted_events]
    report = RedactionReport(
        id=report_id or new_id("redaction-report"),
        created_at=created_at or utc_now(),
        policy_id=policy.id,
        original_digest=sha256_digest(original_records),
        redacted_digest=sha256_digest(redacted_records),
        redacted_field_paths=sorted(redacted_paths),
        excluded_event_types=sorted(excluded),
        findings=all_findings,
    )
    return redacted_events, report


def record_trace_export_allowed(
    record: Mapping[str, object],
    export_policy: DatasetExportPolicy,
) -> bool:
    """Apply private-trace visibility and redaction requirements to export."""

    raw_envelope = record.get("private_trace_envelope")
    if not isinstance(raw_envelope, Mapping):
        return True
    visibility = raw_envelope.get("visibility")
    if visibility not in TRACE_VISIBILITIES:
        return False
    if export_policy.purpose == "audit":
        return True
    if export_policy.public and visibility != TraceVisibility.PUBLIC:
        return False
    if visibility == TraceVisibility.RESTRICTED and not export_policy.include_restricted:
        return False
    if visibility == TraceVisibility.PRIVATE and export_policy.public:
        return False
    redaction_required = raw_envelope.get("redaction_required_for_export") is True
    if redaction_required and not isinstance(raw_envelope.get("redaction_report_digest"), str):
        return False
    return True


def _path_exists(payload: Mapping[str, object], path: list[str]) -> bool:
    current: object = payload
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _replace_path(payload: dict[str, object], path: list[str], replacement: str) -> None:
    if not path:
        return
    current: object = payload
    for part in path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(part)
    if isinstance(current, dict) and path[-1] in current:
        current[path[-1]] = replacement
