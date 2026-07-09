# Trace Ingestion SDK

The trace ingestion SDK is a small standard-library boundary for solver
harnesses. It does not depend on Codex, Hermes Agent, OpenHands, SWE-agent, or a
model provider.

`TraceEventBuilder` assigns ordered sequences, stable event ids, timestamps,
trust levels, and provenance. A harness may use it while work is running.
`TraceWriter` appends canonical JSONL incrementally, supports explicit flush,
applies a `RedactionPolicy` or custom redaction hook, and returns a digestible
`TraceIngestionResult`.

For post-hoc conversion, a `HarnessAdapter` converts a native mapping into
normalized `TraceEvent` records. Faber includes deterministic Codex-like,
Hermes-like, and generic-shell fake adapters solely as conformance examples.
They do not import or call the real harnesses.

Adapter requirements:

- emit one attempt id and contiguous event sequences;
- retain source timestamps and provenance;
- map native payloads to stable Faber event types;
- reject malformed fields with their native field path;
- apply redaction before sharing normalized JSONL;
- produce identical JSONL digests for identical input.

`validate_adapter_conformance` exercises ordering, non-empty output, and stable
digests against local fake fixtures. External communities can implement the
same protocol without depending on Faber internals beyond the small ingestion
surface and public trace schema.
