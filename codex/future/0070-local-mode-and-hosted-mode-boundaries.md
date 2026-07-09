# 0070 — Local mode and hosted mode boundaries

## Goal

Make Faber's local/self-hosted mode clearly separate from future hosted market infrastructure.

## Scope

Document and, where useful, encode boundaries between:

- local protocol validation
- local runner/verifier execution
- local event store
- fake GitHub adapter
- hosted market coordination
- hosted work-budget management
- hosted verifier services
- hosted dataset/model training

## Requirements

- Local mode should not require accounts, external APIs, or telemetry.
- Hosted mode should be described as future work.
- Core objects must remain usable in both modes.
- Docs should explain which commands are local-only.
- No hosted service implementation in this issue.

## Tests

- local commands run without external credentials
- imports do not require network/provider packages
- docs mention local/no-telemetry expectation

## Acceptance criteria

Faber remains trustworthy to developers who want inspectable local and self-hosted workflows.