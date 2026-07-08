# 0038 — Hermes trace adapter

## Goal

Plan and stub a Hermes trace adapter that maps Hermes run/session/log artifacts into Faber TraceEvent JSONL.

## Scope

- generic harness trace adapter interface
- fake Hermes trace fixtures
- mapping to Faber `TraceEvent`
- redaction policy
- event provenance
- tests and docs

## Requirements

- Do not depend on real Hermes internals unless inspected and verified.
- Do not add Hermes as a dependency.
- Use fake fixtures first.
- Support action, tool, context, verification, failure, intervention, and outcome-like events where available.
- Preserve stable serialization and digests.
- Document how external harness communities can add adapters.

## Tests

- fake Hermes trace maps to Faber TraceEvents
- redaction removes sensitive fields
- event ordering is preserved
- adapter output can enrich a Faber trajectory

## Acceptance criteria

Faber has a safe adapter seam for Hermes-like traces without coupling core code to Hermes.