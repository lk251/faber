# 0030 — Trace protocol and evidence ladder

## Goal

Implement Faber's trace vocabulary and evidence ladder so PR-only attempts, manifest-backed attempts, runner traces, harness traces, and replayable episode packages can coexist.

## Scope

Add protocol objects for:

- `EvidenceLevel`
- `TraceEvent`
- `TraceManifest`
- `AttemptManifest`
- `RedactionPolicy`
- `Attestation`
- `EpisodePackage`

## Requirements

- Define Level 0 through Level 4 evidence.
- Keep PR-only submissions valid.
- Add JSONL trace import/export.
- Add stable serialization and digests.
- Add provenance/trust level on solver-supplied metadata.
- Add redaction policy support.
- Do not require private prompts, finetune weights, or chain-of-thought.
- Do not add real model providers.

## Tests

- each evidence level validates
- PR-only attempt still works
- richer trace produces richer trajectory evidence
- redaction removes configured fields
- manifest and trace digests are stable

## Acceptance criteria

Trace strategy is represented in code and docs, with tests proving that Faber can accept low-friction submissions while rewarding richer data later.