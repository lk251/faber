"""Shared contracts for harness-native trace adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.traces import (
    RedactionPolicy,
    TraceEvent,
    TraceManifest,
    require_evidence_level,
    require_trust_level,
    trace_manifest_from_events,
    write_trace_jsonl,
)
from faber.validation import require_digest, require_mapping, require_non_empty_string


class HarnessTraceAdapter(Protocol):
    """Minimal interface for native harness trace adapters."""

    adapter_name: str

    def adapt(
        self,
        payload: Mapping[str, object],
        *,
        attempt_id: str | None = None,
        redaction_policy: RedactionPolicy | None = None,
    ) -> HarnessTraceExport:
        """Convert a native harness payload into normalized Faber trace evidence."""


@dataclass(frozen=True)
class HarnessTraceExport:
    """Normalized output from a harness-native trace adapter."""

    adapter_name: str
    attempt_id: str
    events: list[TraceEvent]
    raw_trace_digest: str
    provenance: dict[str, object]
    redaction_policy: RedactionPolicy | None = None
    trust_level: str = "self_attested"
    evidence_level_value: int = 3

    def __post_init__(self) -> None:
        require_non_empty_string(self.adapter_name, "adapter_name")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_digest(self.raw_trace_digest, "raw_trace_digest")
        require_mapping(self.provenance, "provenance")
        require_trust_level(self.trust_level)
        require_evidence_level(self.evidence_level_value)
        if self.evidence_level_value < 3:
            raise ValidationError("harness trace export requires evidence level 3 or higher")
        if not isinstance(self.events, list):
            raise ValidationError("events must be a list of TraceEvent records")
        for index, event in enumerate(self.events):
            if not isinstance(event, TraceEvent):
                raise ValidationError(f"events[{index}] must be a TraceEvent")
            if event.attempt_id != self.attempt_id:
                raise ValidationError("trace event attempt_id must match export attempt_id")

    def redacted_events(self) -> list[TraceEvent]:
        """Return events after applying the configured redaction policy."""

        if self.redaction_policy is None:
            return list(self.events)
        return [event.redacted(self.redaction_policy) for event in self.events]

    def write_jsonl(self, out_path: str | Path) -> str:
        """Write normalized trace JSONL and return its digest."""

        return write_trace_jsonl(
            self.events,
            out_path,
            redaction_policy=self.redaction_policy,
        )

    def trace_manifest(
        self,
        *,
        trace_jsonl_digest: str,
        manifest_id: str | None = None,
        created_at: str | None = None,
        privacy_notes: str = "",
    ) -> TraceManifest:
        """Build a Faber trace manifest for this adapter export."""

        provenance = dict(self.provenance)
        provenance.setdefault("adapter", self.adapter_name)
        return trace_manifest_from_events(
            attempt_id=self.attempt_id,
            events=self.redacted_events(),
            evidence_level_value=self.evidence_level_value,
            trace_jsonl_digest=trace_jsonl_digest,
            trust_level=self.trust_level,
            redaction_policy=self.redaction_policy,
            raw_trace_digest=self.raw_trace_digest,
            provenance=provenance,
            privacy_notes=privacy_notes,
            manifest_id=manifest_id,
            created_at=created_at,
        )


def raw_trace_payload_digest(payload: Mapping[str, object]) -> str:
    """Return the stable digest Faber stores for a native harness payload."""

    return sha256_digest(dict(payload))
