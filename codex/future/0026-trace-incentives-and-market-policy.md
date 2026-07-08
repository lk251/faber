# 0026 - Trace Incentives And Market Policy

## Goal

Add protocol and docs for trace-quality incentives.

## Scope

Support:

- `TraceQualityScore`
- minimum evidence level per task contract;
- optional richer-trace bonus fields;
- reputation impact;
- eligibility for premium tasks;
- trace privacy and redaction policy.

## Requirements

- Do not implement real payments.
- Use integer minor units for any bonus or money fields.
- Do not require full traces globally.
- Do not require private chain-of-thought.
- Richer trace incentives must respect redaction policy and solver IP.

## Tests

Add tests showing:

- a task can require a minimum evidence level;
- a PR-only attempt is rejected for a task requiring runner trace;
- richer traces can receive higher trace quality scores;
- redacted traces are accepted when policy allows them;
- money or bonus fields use integer minor units.

## Docs

Explain why Faber rewards richer traces but does not require them globally.

## Acceptance Criteria

- Trace quality influences eligibility, reputation, or optional economics without
  bypassing verifier authority.
- PR-only work remains valid for tasks that allow it.
