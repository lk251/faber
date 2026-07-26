"""Small standard-library SDK for streaming and adapting solver traces."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TextIO

from faber import schemas
from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.redaction import redact_trace_events
from faber.traces import RedactionPolicy, TraceEvent, require_trust_level
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

Clock = Callable[[], str]
RedactionHook = Callable[[TraceEvent], TraceEvent | None]


class HarnessAdapter(Protocol):
    """Provider-free contract for converting one native trace payload."""

    adapter_name: str

    def convert(
        self,
        payload: Mapping[str, object],
        builder: TraceEventBuilder,
    ) -> list[TraceEvent]:
        """Convert post-hoc native events into ordered Faber events."""


@dataclass
class TraceEventBuilder:
    """Build ordered trace events with shared provenance and a supplied clock."""

    attempt_id: str
    trust_level: str = "self_attested"
    provenance: dict[str, object] = field(default_factory=dict)
    clock: Clock = utc_now
    _sequence: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_trust_level(self.trust_level)
        require_mapping(self.provenance, "provenance")

    def build(
        self,
        event_type: str,
        payload: Mapping[str, object],
        *,
        observed_at: str | None = None,
        provenance: Mapping[str, object] | None = None,
        event_id: str | None = None,
    ) -> TraceEvent:
        require_non_empty_string(event_type, "event_type")
        event_payload = dict(require_mapping(payload, "payload"))
        timestamp = observed_at or self.clock()
        require_non_empty_string(timestamp, "observed_at")
        merged_provenance = dict(self.provenance)
        if provenance is not None:
            merged_provenance.update(dict(require_mapping(provenance, "provenance")))
        merged_provenance.setdefault(
            "timestamp_source",
            "adapter" if observed_at is not None else "builder_clock",
        )
        sequence = self._sequence
        self._sequence += 1
        return TraceEvent(
            id=event_id or _event_id(self.attempt_id, sequence),
            created_at=timestamp,
            attempt_id=self.attempt_id,
            sequence=sequence,
            event_type=event_type,
            payload=event_payload,
            observed_at=timestamp,
            trust_level=self.trust_level,
            provenance=merged_provenance,
        )


@dataclass(frozen=True)
class TraceIngestionResult:
    attempt_id: str
    adapter_name: str
    output_path: str
    events_written: int
    event_types: list[str]
    trace_jsonl_digest: str
    provenance: dict[str, object]
    redacted: bool
    id: str = field(default_factory=lambda: new_id("trace-ingestion-result"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRACE_INGESTION_RESULT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRACE_INGESTION_RESULT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_non_empty_string(self.adapter_name, "adapter_name")
        require_non_empty_string(self.output_path, "output_path")
        if not isinstance(self.events_written, int) or isinstance(self.events_written, bool):
            raise ValidationError("events_written must be an integer")
        if self.events_written < 0:
            raise ValidationError("events_written must be non-negative")
        require_string_list(self.event_types, "event_types")
        require_digest(self.trace_jsonl_digest, "trace_jsonl_digest")
        require_mapping(self.provenance, "provenance")
        if not isinstance(self.redacted, bool):
            raise ValidationError("redacted must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "attempt_id": self.attempt_id,
            "adapter_name": self.adapter_name,
            "output_path": self.output_path,
            "events_written": self.events_written,
            "event_types": self.event_types,
            "trace_jsonl_digest": self.trace_jsonl_digest,
            "provenance": self.provenance,
            "redacted": self.redacted,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class TraceWriter:
    """Buffered JSONL writer for streaming normalized trace events."""

    def __init__(
        self,
        path: str | Path,
        *,
        attempt_id: str,
        adapter_name: str = "streaming",
        redaction_policy: RedactionPolicy | None = None,
        redaction_hook: RedactionHook | None = None,
        provenance: Mapping[str, object] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.attempt_id = require_non_empty_string(attempt_id, "attempt_id")
        self.adapter_name = require_non_empty_string(adapter_name, "adapter_name")
        self.redaction_policy = redaction_policy
        self.redaction_hook = redaction_hook
        self.provenance = dict(provenance or {})
        self.result_id = result_id or new_id("trace-ingestion-result")
        self.created_at = created_at or utc_now()
        self._handle: TextIO = self.path.open("w", encoding="utf-8", newline="\n")
        self._source_events_seen = 0
        self._events_written = 0
        self._event_types: set[str] = set()
        self._closed = False

    def append(self, event: TraceEvent) -> bool:
        if self._closed:
            raise ValidationError("trace writer is closed")
        if not isinstance(event, TraceEvent):
            raise ValidationError("event must be a TraceEvent")
        if event.attempt_id != self.attempt_id:
            raise ValidationError("event.attempt_id must match writer attempt_id")
        if event.sequence != self._source_events_seen:
            raise ValidationError(
                f"event.sequence must be {self._source_events_seen}, got {event.sequence}"
            )
        self._source_events_seen += 1
        candidate: TraceEvent | None = event
        if self.redaction_policy is not None:
            redacted, _ = redact_trace_events([event], self.redaction_policy)
            candidate = redacted[0] if redacted else None
        if candidate is not None and self.redaction_hook is not None:
            candidate = self.redaction_hook(candidate)
        if candidate is None:
            return False
        if candidate.sequence != self._events_written:
            provenance = dict(candidate.provenance)
            provenance["source_sequence"] = candidate.sequence
            candidate = TraceEvent(
                id=candidate.id,
                created_at=candidate.created_at,
                attempt_id=candidate.attempt_id,
                sequence=self._events_written,
                event_type=candidate.event_type,
                payload=candidate.payload,
                observed_at=candidate.observed_at,
                trust_level=candidate.trust_level,
                provenance=provenance,
                redaction_policy_id=candidate.redaction_policy_id,
            )
        self._handle.write(canonical_json(candidate.to_dict()) + "\n")
        self._events_written += 1
        self._event_types.add(candidate.event_type)
        return True

    def flush(self) -> None:
        if not self._closed:
            self._handle.flush()

    def close(self) -> None:
        if not self._closed:
            self._handle.flush()
            self._handle.close()
            self._closed = True

    def result(self) -> TraceIngestionResult:
        self.close()
        provenance = dict(self.provenance)
        provenance.setdefault("adapter", self.adapter_name)
        return TraceIngestionResult(
            id=self.result_id,
            created_at=self.created_at,
            attempt_id=self.attempt_id,
            adapter_name=self.adapter_name,
            output_path=str(self.path),
            events_written=self._events_written,
            event_types=sorted(self._event_types),
            trace_jsonl_digest=sha256_digest(self.path.read_bytes()),
            provenance=provenance,
            redacted=self.redaction_policy is not None or self.redaction_hook is not None,
        )

    def __enter__(self) -> TraceWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def ingest_native_trace(
    adapter: HarnessAdapter,
    payload: Mapping[str, object],
    out_path: str | Path,
    *,
    attempt_id: str | None = None,
    trust_level: str = "self_attested",
    redaction_policy: RedactionPolicy | None = None,
    redaction_hook: RedactionHook | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
) -> TraceIngestionResult:
    """Convert a complete native payload and write normalized JSONL."""

    normalized_payload = dict(require_mapping(payload, "payload"))
    source_attempt_id = attempt_id or _required_string(
        normalized_payload, "attempt_id", "attempt_id"
    )
    raw_digest = sha256_digest(normalized_payload)
    builder = TraceEventBuilder(
        attempt_id=source_attempt_id,
        trust_level=trust_level,
        provenance={"adapter": adapter.adapter_name, "raw_trace_digest": raw_digest},
    )
    events = adapter.convert(normalized_payload, builder)
    writer = TraceWriter(
        out_path,
        attempt_id=source_attempt_id,
        adapter_name=adapter.adapter_name,
        redaction_policy=redaction_policy,
        redaction_hook=redaction_hook,
        provenance={
            "adapter": adapter.adapter_name,
            "raw_trace_digest": raw_digest,
            "mode": "post_hoc_conversion",
        },
        result_id=result_id,
        created_at=created_at,
    )
    try:
        for event in events:
            writer.append(event)
        return writer.result()
    except Exception:
        writer.close()
        raise


def validate_adapter_conformance(
    adapter: HarnessAdapter,
    payload: Mapping[str, object],
    out_dir: str | Path,
) -> dict[str, object]:
    """Run the deterministic contract shared by all fake harness adapters."""

    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    left = ingest_native_trace(
        adapter,
        payload,
        directory / "left.jsonl",
        result_id="trace-ingestion-result_conformance",
        created_at="1970-01-01T00:00:00Z",
    )
    right = ingest_native_trace(
        adapter,
        payload,
        directory / "right.jsonl",
        result_id="trace-ingestion-result_conformance",
        created_at="1970-01-01T00:00:00Z",
    )
    events = _read_sequences(directory / "left.jsonl")
    ordered = events == list(range(len(events)))
    return {
        "adapter": adapter.adapter_name,
        "conformant": left.events_written > 0 and ordered,
        "ordered": ordered,
        "stable_digest": left.trace_jsonl_digest == right.trace_jsonl_digest,
        "events_written": left.events_written,
    }


def _required_string(
    payload: Mapping[str, object],
    field_name: str,
    display_name: str,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{display_name} must be a non-empty string")
    return value


def _event_id(attempt_id: str, sequence: int) -> str:
    safe_attempt_id = "".join(
        character if character.isalnum() or character in "-_" else "_" for character in attempt_id
    )
    return f"trace-event_{safe_attempt_id}_{sequence:06d}"


def _read_sequences(path: Path) -> list[int]:
    import json

    return [
        int(record["sequence"])
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
        for record in [json.loads(line)]
    ]
