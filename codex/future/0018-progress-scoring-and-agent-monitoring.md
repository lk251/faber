# 0018 - Progress Scoring And Agent Monitoring

## Goal

Add trajectory progress scoring primitives.

## Scope

Support:

- scoring prefixes of a trajectory;
- representing progress curves;
- detecting stalls and regressions;
- computing a simple Value-Order Correlation-like metric for successful and
  failed trajectories;
- exporting progress signals for future monitoring and training.

## Requirements

- Do not add real model APIs.
- Use a fake deterministic progress scorer.
- Store progress scores as advisory verifier evidence.
- Update docs to explain how Faber could later surface progress during
  long-running Codex or agent jobs.

## Tests

Add tests for:

- monotonic successful trajectory fixture;
- flat or stalled failed trajectory fixture;
- regression detection;
- progress score export to JSONL.

## Acceptance Criteria

- Progress scoring is advisory and cannot settle payment.
- Progress records use stable serialization and digests.
- Exported progress data can be consumed by later training/evaluation tools.
