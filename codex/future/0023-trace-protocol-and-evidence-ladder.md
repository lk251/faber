# 0023 - Trace Protocol And Evidence Ladder

## Goal

Implement Faber's trace protocol and evidence ladder.

## Scope

Add protocol records for:

- `TraceEvent`
- `TraceManifest`
- `AttemptManifest`
- `EvidenceLevel`
- `RedactionPolicy`
- `Attestation`

Add:

- JSONL trace export and import;
- conversion from raw trace events into a normalized trajectory evidence bundle.

## Requirements

- Do not add real model APIs.
- Do not require full prompt, private reasoning, or chain-of-thought capture.
- Preserve stable serialization and stable digests.
- Support redaction.
- Store provenance and trust level on all solver-supplied metadata.
- PR-only submissions must still work.
- Richer traces should produce richer trajectory records.

## Tests

Add tests for:

- each evidence level;
- PR-only fallback;
- manifest-backed attempts;
- runner trace bundles;
- redaction behavior;
- stable trace and manifest digests;
- richer traces creating richer trajectory evidence.

## Acceptance Criteria

- Trace protocol records are provider-agnostic dataclasses.
- JSONL import/export is deterministic.
- Trace evidence is advisory unless bound to an approved verifier or explicit task
  policy.
