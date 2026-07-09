"""Deterministic fake harness adapters for trace-ingestion conformance tests."""

from __future__ import annotations

from collections.abc import Mapping

from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.trace_ingestion import TraceEventBuilder
from faber.traces import TraceEvent


class CodexLikeAdapter:
    adapter_name = "codex-like-v1"
    _event_types = {
        "context": "context.read",
        "tool": "tool.call",
        "verification": "verification.result",
        "outcome": "outcome.reported",
    }

    def convert(
        self,
        payload: Mapping[str, object],
        builder: TraceEventBuilder,
    ) -> list[TraceEvent]:
        events = _event_list(payload, "events")
        converted: list[TraceEvent] = []
        for index, raw_event in enumerate(events):
            native = _event_mapping(raw_event, index)
            event_type = _required_string(native, "type", f"events[{index}].type")
            timestamp = _required_string(
                native, "timestamp", f"events[{index}].timestamp"
            )
            data = _required_mapping(native, "data", f"events[{index}].data")
            converted.append(
                builder.build(
                    self._event_types.get(event_type, f"harness.{event_type}"),
                    data,
                    observed_at=timestamp,
                    provenance={"native_event_index": index, "native_type": event_type},
                )
            )
        return converted


class HermesLikeAdapter:
    adapter_name = "hermes-like-v1"
    _event_types = {
        "context.read": "context.read",
        "tool.call": "tool.call",
        "verification.result": "verification.result",
        "outcome.reported": "outcome.reported",
    }

    def convert(
        self,
        payload: Mapping[str, object],
        builder: TraceEventBuilder,
    ) -> list[TraceEvent]:
        events = _event_list(payload, "events")
        converted: list[TraceEvent] = []
        for index, raw_event in enumerate(events):
            native = _event_mapping(raw_event, index)
            kind = _required_string(native, "kind", f"events[{index}].kind")
            observed_at = _required_string(
                native, "observed_at", f"events[{index}].observed_at"
            )
            event_payload = _required_mapping(
                native, "payload", f"events[{index}].payload"
            )
            converted.append(
                builder.build(
                    self._event_types.get(kind, f"harness.{kind}"),
                    event_payload,
                    observed_at=observed_at,
                    provenance={"native_event_index": index, "native_kind": kind},
                )
            )
        return converted


class GenericShellAdapter:
    adapter_name = "generic-shell-v1"

    def convert(
        self,
        payload: Mapping[str, object],
        builder: TraceEventBuilder,
    ) -> list[TraceEvent]:
        commands = _event_list(payload, "commands")
        converted: list[TraceEvent] = []
        for index, raw_command in enumerate(commands):
            command = _event_mapping(raw_command, index, collection="commands")
            observed_at = _required_string(
                command, "observed_at", f"commands[{index}].observed_at"
            )
            command_text = _required_string(
                command, "command", f"commands[{index}].command"
            )
            exit_code = command.get("exit_code")
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                raise ValidationError(f"commands[{index}].exit_code must be an integer")
            converted.append(
                builder.build(
                    "tool.call",
                    {"tool": "shell", "command_digest": sha256_digest(command_text)},
                    observed_at=observed_at,
                    provenance={"native_command_index": index},
                )
            )
            converted.append(
                builder.build(
                    "verification.result",
                    {
                        "exit_code": exit_code,
                        "passed": exit_code == 0,
                        "output_digest": command.get("output_digest"),
                    },
                    observed_at=observed_at,
                    provenance={"native_command_index": index},
                )
            )
        return converted


def fake_adapter_fixtures() -> dict[str, dict[str, object]]:
    timestamp = "2026-01-01T00:00:00Z"
    return {
        "codex-like-v1": {
            "attempt_id": "attempt_codex_fixture",
            "events": [
                {"type": "context", "timestamp": timestamp, "data": {"path": "README.md"}},
                {
                    "type": "tool",
                    "timestamp": timestamp,
                    "data": {
                        "tool": "pytest",
                        "credentials": {"token": "fixture-secret"},
                    },
                },
                {
                    "type": "verification",
                    "timestamp": timestamp,
                    "data": {"passed": True},
                },
            ],
        },
        "hermes-like-v1": {
            "attempt_id": "attempt_hermes_fixture",
            "events": [
                {
                    "kind": "context.read",
                    "observed_at": timestamp,
                    "payload": {"path": "AGENTS.md"},
                },
                {
                    "kind": "tool.call",
                    "observed_at": timestamp,
                    "payload": {"tool": "pytest"},
                },
                {
                    "kind": "verification.result",
                    "observed_at": timestamp,
                    "payload": {"passed": True},
                },
            ],
        },
        "generic-shell-v1": {
            "attempt_id": "attempt_shell_fixture",
            "commands": [
                {
                    "command": "python -m pytest",
                    "observed_at": timestamp,
                    "exit_code": 0,
                    "output_digest": sha256_digest("tests passed"),
                },
                {
                    "command": "python -m ruff check .",
                    "observed_at": timestamp,
                    "exit_code": 0,
                    "output_digest": sha256_digest("lint passed"),
                },
            ],
        },
    }


def _event_list(payload: Mapping[str, object], field_name: str) -> list[object]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")
    return value


def _event_mapping(
    value: object,
    index: int,
    *,
    collection: str = "events",
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{collection}[{index}] must be a mapping")
    return dict(value)


def _required_mapping(
    payload: Mapping[str, object],
    field_name: str,
    display_name: str,
) -> dict[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValidationError(f"{display_name} must be a mapping")
    return dict(value)


def _required_string(
    payload: Mapping[str, object],
    field_name: str,
    display_name: str,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{display_name} must be a non-empty string")
    return value
