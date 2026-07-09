from pathlib import Path

import pytest

from faber.adapters.fake_trace_ingestion import (
    CodexLikeAdapter,
    GenericShellAdapter,
    HermesLikeAdapter,
    fake_adapter_fixtures,
)
from faber.errors import ValidationError
from faber.trace_ingestion import (
    TraceEventBuilder,
    TraceWriter,
    ingest_native_trace,
    validate_adapter_conformance,
)
from faber.traces import RedactionPolicy, read_trace_jsonl

CREATED_AT = "2026-01-01T00:00:00Z"


def test_trace_writer_emits_valid_streaming_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    builder = TraceEventBuilder(
        attempt_id="attempt_sdk",
        trust_level="runner_attested",
        clock=lambda: CREATED_AT,
    )
    writer = TraceWriter(
        path,
        attempt_id="attempt_sdk",
        adapter_name="fixture",
        result_id="trace-ingestion-result_sdk",
        created_at=CREATED_AT,
    )
    writer.append(builder.build("context.read", {"path": "README.md"}))
    writer.append(builder.build("tool.call", {"tool": "pytest"}))
    writer.flush()
    result = writer.result()

    loaded = read_trace_jsonl(path)
    assert [event.sequence for event in loaded] == [0, 1]
    assert result.events_written == 2
    assert result.trace_jsonl_digest.startswith("sha256:")
    assert result.digest() == result.digest()


@pytest.mark.parametrize(
    "adapter",
    [CodexLikeAdapter(), HermesLikeAdapter(), GenericShellAdapter()],
)
def test_fake_native_adapters_convert_post_hoc(tmp_path: Path, adapter) -> None:
    fixture = fake_adapter_fixtures()[adapter.adapter_name]
    result = ingest_native_trace(
        adapter,
        fixture,
        tmp_path / f"{adapter.adapter_name}.jsonl",
        result_id=f"trace-ingestion-result_{adapter.adapter_name}",
        created_at=CREATED_AT,
    )

    assert result.events_written >= 2
    assert "tool.call" in result.event_types
    assert result.provenance["adapter"] == adapter.adapter_name


def test_malformed_native_event_is_rejected_with_field_name(tmp_path: Path) -> None:
    payload = {
        "attempt_id": "attempt_bad",
        "events": [{"type": "tool", "timestamp": CREATED_AT, "data": "not-a-mapping"}],
    }

    with pytest.raises(ValidationError, match=r"events\[0\]\.data must be a mapping"):
        ingest_native_trace(CodexLikeAdapter(), payload, tmp_path / "bad.jsonl")


def test_redaction_hook_runs_during_ingestion(tmp_path: Path) -> None:
    fixture = fake_adapter_fixtures()["codex-like-v1"]
    policy = RedactionPolicy(
        id="redaction-policy_sdk",
        created_at=CREATED_AT,
        name="SDK fixture policy",
        field_paths=["credentials.token"],
    )
    path = tmp_path / "redacted.jsonl"

    result = ingest_native_trace(
        CodexLikeAdapter(),
        fixture,
        path,
        redaction_policy=policy,
        result_id="trace-ingestion-result_redacted",
        created_at=CREATED_AT,
    )

    assert result.redacted is True
    assert read_trace_jsonl(path)[1].payload["credentials"]["token"] == "[redacted]"


def test_all_fake_adapters_pass_same_conformance_fixture(tmp_path: Path) -> None:
    adapters = [CodexLikeAdapter(), HermesLikeAdapter(), GenericShellAdapter()]

    reports = [
        validate_adapter_conformance(
            adapter,
            fake_adapter_fixtures()[adapter.adapter_name],
            tmp_path / adapter.adapter_name,
        )
        for adapter in adapters
    ]

    assert [report["conformant"] for report in reports] == [True, True, True]
    assert all(report["ordered"] is True for report in reports)
    assert all(report["stable_digest"] is True for report in reports)
