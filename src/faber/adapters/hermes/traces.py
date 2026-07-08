"""Adapter for fake Hermes-like trace fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from faber.adapters.traces import HarnessTraceExport, raw_trace_payload_digest
from faber.errors import ValidationError
from faber.traces import RedactionPolicy, TraceEvent, require_trust_level
from faber.validation import require_mapping, require_non_empty_string, require_sequence

HERMES_TRACE_ADAPTER_NAME = "faber.adapters.hermes.fake_trace.v1"

EVENT_TYPE_MAP = {
    "session.started": "context.loaded",
    "context.read": "context.read",
    "agent.action": "action.selected",
    "tool.call": "tool.call",
    "verification.result": "verification.result",
    "failure.observed": "failure.observed",
    "intervention.applied": "intervention.applied",
    "outcome.reported": "outcome.reported",
}


def load_hermes_trace_fixture(path: str | Path) -> dict[str, object]:
    """Load a fake Hermes-like trace fixture from JSON."""

    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValidationError("Hermes-like trace fixture must be a JSON object")
    return parsed


def adapt_hermes_trace_file(
    path: str | Path,
    *,
    attempt_id: str | None = None,
    redaction_policy: RedactionPolicy | None = None,
    trust_level: str = "self_attested",
) -> HarnessTraceExport:
    """Load and adapt a fake Hermes-like trace fixture."""

    return adapt_hermes_trace_payload(
        load_hermes_trace_fixture(path),
        attempt_id=attempt_id,
        redaction_policy=redaction_policy,
        trust_level=trust_level,
    )


def adapt_hermes_trace_payload(
    payload: Mapping[str, object],
    *,
    attempt_id: str | None = None,
    redaction_policy: RedactionPolicy | None = None,
    trust_level: str = "self_attested",
) -> HarnessTraceExport:
    """Map a fake Hermes-like payload into normalized Faber TraceEvent records."""

    require_trust_level(trust_level)
    native_payload = dict(require_mapping(payload, "payload"))
    source_attempt_id = attempt_id or _required_payload_string(native_payload, "attempt_id")
    raw_trace_digest = raw_trace_payload_digest(native_payload)
    run_id = _required_payload_string(native_payload, "run_id")
    session_id = _optional_payload_string(native_payload, "session_id")
    source_schema = _optional_payload_string(native_payload, "schema")
    events = _events_from_payload(
        native_payload,
        attempt_id=source_attempt_id,
        raw_trace_digest=raw_trace_digest,
        run_id=run_id,
        session_id=session_id,
        source_schema=source_schema,
        trust_level=trust_level,
    )
    return HarnessTraceExport(
        adapter_name=HERMES_TRACE_ADAPTER_NAME,
        attempt_id=source_attempt_id,
        events=events,
        raw_trace_digest=raw_trace_digest,
        redaction_policy=redaction_policy,
        trust_level=trust_level,
        provenance={
            "adapter": HERMES_TRACE_ADAPTER_NAME,
            "source_schema": source_schema,
            "source_run_id": run_id,
            "source_session_id": session_id,
            "source": "fake_fixture",
            "raw_trace_digest": raw_trace_digest,
        },
    )


def _events_from_payload(
    native_payload: Mapping[str, object],
    *,
    attempt_id: str,
    raw_trace_digest: str,
    run_id: str,
    session_id: str | None,
    source_schema: str | None,
    trust_level: str,
) -> list[TraceEvent]:
    native_events = require_sequence(native_payload.get("events"), "events")
    events: list[TraceEvent] = []
    for index, native_event in enumerate(native_events):
        event = _native_event_to_trace_event(
            native_event,
            index=index,
            attempt_id=attempt_id,
            raw_trace_digest=raw_trace_digest,
            run_id=run_id,
            session_id=session_id,
            source_schema=source_schema,
            trust_level=trust_level,
        )
        events.append(event)
    return events


def _native_event_to_trace_event(
    native_event: object,
    *,
    index: int,
    attempt_id: str,
    raw_trace_digest: str,
    run_id: str,
    session_id: str | None,
    source_schema: str | None,
    trust_level: str,
) -> TraceEvent:
    native = dict(require_mapping(native_event, f"events[{index}]"))
    kind = _required_payload_string(native, "kind")
    observed_at = _required_payload_string(native, "observed_at")
    payload = _event_payload(native, index)
    source_sequence = native.get("sequence", index)
    return TraceEvent(
        id=_trace_event_id(attempt_id, index),
        created_at=observed_at,
        attempt_id=attempt_id,
        sequence=index,
        event_type=EVENT_TYPE_MAP.get(kind, f"harness.{kind}"),
        observed_at=observed_at,
        payload=payload,
        trust_level=trust_level,
        provenance={
            "adapter": HERMES_TRACE_ADAPTER_NAME,
            "source_schema": source_schema,
            "source_run_id": run_id,
            "source_session_id": session_id,
            "source_event_kind": kind,
            "source_event_sequence": source_sequence,
            "source_event_index": index,
            "raw_trace_digest": raw_trace_digest,
        },
    )


def _event_payload(native_event: Mapping[str, object], index: int) -> dict[str, object]:
    payload = native_event.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValidationError(f"events[{index}].payload must be a mapping")
    normalized = dict(payload)
    for field in ["summary", "status"]:
        value = native_event.get(field)
        if value is not None and field not in normalized:
            normalized[field] = value
    return normalized


def _trace_event_id(attempt_id: str, index: int) -> str:
    safe_attempt_id = "".join(
        char if char.isalnum() or char in "-_" else "_" for char in attempt_id
    )
    return f"trace-event_{safe_attempt_id}_{index:04d}"


def _required_payload_string(payload: Mapping[str, object], field: str) -> str:
    return require_non_empty_string(payload.get(field), field)


def _optional_payload_string(payload: Mapping[str, object], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    return require_non_empty_string(value, field)
