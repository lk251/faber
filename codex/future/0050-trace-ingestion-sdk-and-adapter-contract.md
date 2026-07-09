# 0050 — Trace ingestion SDK and adapter contract

## Goal

Make it easy for any solver harness to emit Faber-compatible traces without depending on Faber internals.

## Scope

Add a small trace ingestion interface:

- `TraceWriter`
- `TraceEventBuilder`
- `HarnessAdapter`
- `TraceIngestionResult`
- JSONL append/flush helpers
- adapter conformance tests

## Requirements

- Standard-library first.
- Stable event schemas and digests.
- Support streaming writes and post-hoc conversion.
- Support redaction hooks.
- Support provenance and clock/timestamp metadata.
- Include fake adapters for Codex-like, Hermes-like, and generic shell traces.
- No dependency on real Codex, Hermes, OpenHands, SWE-agent, or model APIs.

## Tests

- trace writer emits valid JSONL
- adapter converts fake native events
- malformed event is rejected with useful error
- redaction hook works during ingestion
- adapter conformance fixture validates all fake adapters

## Acceptance criteria

External solver communities have a clear seam for contributing RL-grade process evidence to Faber.