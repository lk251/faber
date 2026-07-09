# 0065 — Fake GitHub funded task end-to-end

## Goal

Create a complete fake GitHub flow that demonstrates funded issue -> task contract -> attempt -> trace -> verifier receipt -> settlement ledger -> dataset export.

## Scope

Use only fake/local adapters.

## Requirements

- Fake issue includes task marker and budget marker.
- Fake PR includes `.faber/attempt.json` and trace artifact references.
- Verifier run produces authoritative receipt.
- Work budget ledger reserves and settles locally.
- Trajectory validates as RL-grade when data is complete.
- Dataset export includes the final trajectory when consent permits.
- Output text should be clear and delightful for a maintainer.

## Tests

- full fake product loop succeeds
- missing trace downgrades trajectory quality
- missing training consent excludes dataset export
- rejected verifier prevents settlement
- duplicate webhook-like events are idempotent

## Acceptance criteria

Faber has one high-signal local product loop that proves the architecture is coherent before real integrations.