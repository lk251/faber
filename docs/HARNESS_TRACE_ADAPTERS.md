# Harness trace adapters

The provider-free streaming and post-hoc SDK contract is documented in
`docs/TRACE_INGESTION.md`. Existing harness-specific adapters should normalize
to the same `TraceEvent` JSONL schema and conformance expectations.

Harness-native trace adapters convert external solver or runner logs into Faber
`TraceEvent` JSONL without making the external harness a core dependency.

The first adapter is a Hermes-like fake fixture adapter. It is deliberately based
on a test fixture, not on verified upstream internals. Before a community adapter
claims support for a real harness trace format, it should inspect current
upstream code or docs and record the observed artifact shape.

## Adapter contract

An adapter should:

- accept a native payload or file;
- return a `HarnessTraceExport`;
- map events into normalized `TraceEvent` records;
- preserve the native payload by stable digest, not by default raw storage;
- include event provenance such as adapter name, source run id, source event kind,
  source sequence, and raw trace digest;
- support explicit `RedactionPolicy` application before JSONL export;
- emit a Level 3 `TraceManifest` for harness-native trace evidence.

The normalized event stream should preserve input order. Event names can be
adapter-specific, but common categories should be represented when available:
context, action, tool, verification, failure, intervention, and outcome.

## Redaction

Adapters must assume native traces may contain private prompts, credentials,
local paths, customer data, or solver IP. Redaction is field-path based. Raw
trace storage should remain opt-in and should be represented by digest when raw
storage is not allowed.

Recommended defaults:

- redact private prompts and credentials;
- redact raw verifier output when it can include local secrets;
- keep public summaries, event type, ordering, timing, and verifier pass/fail
  evidence;
- retain `raw_trace_digest` so a party with access to the private raw trace can
  audit the normalized export later.

## Adding a community adapter

1. Add code under `src/faber/adapters/<harness>/`.
2. Add fake fixtures first under `tests/fixtures/<harness>/`.
3. Map only fields verified from current upstream artifacts.
4. Add tests for event mapping, ordering, redaction, provenance, stable digests,
   and `trajectory_evidence_bundle` enrichment.
5. Document unsupported native fields and privacy assumptions.
6. Keep optional harness dependencies outside Faber core.

The Hermes-like fixture adapter follows this pattern at
`src/faber/adapters/hermes/traces.py`.
