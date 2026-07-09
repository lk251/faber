# 0048 — Redaction, secrets, and private trace policy

## Goal

Make high-quality trajectory collection compatible with privacy, proprietary solvers, and real repositories by adding redaction policy and safety checks.

## Scope

Add or extend:

- `RedactionPolicy`
- `RedactionReport`
- `SensitiveFieldPattern`
- `TraceVisibility`
- `PrivateTraceEnvelope`
- dataset export redaction hooks

## Requirements

- Do not require private prompts, chain-of-thought, finetune weights, or proprietary harness internals.
- Redaction should preserve enough structure for learning when possible.
- Support field-level and event-level redaction.
- Record redaction digests so audit records remain stable.
- Add a simple local detector for obvious secrets in trace text and metadata.
- Dataset export should refuse unredacted private traces when policy forbids export.
- Documentation must explain the difference between hiding content and losing RL usefulness.

## Tests

- sensitive fields are redacted
- redaction report is stable and digestible
- private trace is excluded from public export
- redacted trace can still validate as RL-grade when required fields remain
- obvious token/secret-like strings are flagged in fixtures

## Acceptance criteria

Faber can collect richer traces without forcing solvers or customers to expose private information unnecessarily.