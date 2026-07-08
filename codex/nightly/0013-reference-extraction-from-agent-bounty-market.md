# 0013 — Reference extraction from agent-bounty-market

## Goal

Inspect `lk251/agent-bounty-market` as a read-only reference and extract durable lessons into Faber documentation and tests without importing its hackathon architecture.

This issue is about mining hard-earned invariants, not copying code.

## Scope

Review the old repo for useful ideas around:

- integer money handling
- explicit lifecycle transitions
- idempotency
- ledger invariants
- verifier receipt binding
- GitHub contract markers
- candidate/repo-owner trust boundary
- malicious or stale candidate rejection tests
- timeout and malformed verifier output tests
- restart/replay behavior

## Requirements

1. Create `docs/REFERENCE-agent-bounty-market.md`.
2. Summarize what Faber should preserve conceptually.
3. Summarize what Faber should avoid carrying forward:
   - hackathon demo layers
   - vendor-specific paths
   - Stripe-first assumptions
   - Motoko-specific core assumptions
   - presentation/release bundle code
4. Add at least five tests or test TODOs in Faber inspired by old invariants, only where they fit the current architecture.
5. Add an ADR if a major design lesson deserves one.
6. Do not copy large code blocks.
7. Do not make `agent-bounty-market` a dependency.
8. Do not refactor `agent-bounty-market`.

## Craftsmanship bar

The resulting document should help future contributors understand why Faber started fresh and which prototype lessons matter.

## Tests

Where useful, add or strengthen tests for:

- idempotent ledger/store behavior
- stale candidate revision rejection
- receipt binding to exact contract and candidate revision
- no settlement without accepted receipt
- verifier timeout/failure handling
- trust boundary between candidate CI and authoritative receipts

## Acceptance criteria

- Reference extraction doc exists.
- Faber tests are strengthened by at least a few old-repo lessons.
- No old hackathon architecture is copied into Faber.
- Existing tests still pass.
