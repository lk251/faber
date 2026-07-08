# 0010 — Market ledger and settlement economics

## Goal

Add a local, provider-agnostic market ledger that can model obligations, reservations, payouts, refunds, platform margin, and retained operating spend without integrating any payment provider.

Payments remain an adapter. This issue builds the internal accounting vocabulary needed for profitable, auditable market behavior.

## Scope

Add or extend local domain objects for:

- accounts
- ledger entries
- reservations
- settlement obligations
- payouts
- refunds
- platform fees/margin
- operating spend categories
- reconciliation summaries

## Requirements

1. Use integer minor units only.
2. Do not use floats for money.
3. Keep ledger entries append-only.
4. Add idempotency keys for ledger operations.
5. Prevent negative balances except for explicitly external/clearing accounts if such accounts are modeled.
6. Settlement should require an accepted `VerificationReceipt`.
7. Add split settlement support:
   - worker payout
   - verifier fee if applicable
   - platform fee/margin
   - retained operating spend bucket if useful
8. Add refund/failure states for rejected or expired work.
9. Add reconciliation summary helpers.
10. Keep payment providers out of the core.
11. Update docs to make clear that Faber is not a payment processor.

## Craftsmanship bar

The accounting should be boring, exact, and explainable. Every movement of value should have a reason, source, destination, amount, currency, and idempotency key.

## Tests

Add tests for:

- exact integer accounting
- idempotent reservation
- no payout without accepted receipt
- duplicate payout does not double pay
- split settlement sums exactly
- refund path
- rejected work cannot be paid
- reconciliation summary

## Acceptance criteria

- Local market ledger exists and is tested.
- Settlement economics are explicit and provider-agnostic.
- No payment provider integration is added.
- Docs explain ledger versus payment provider boundary.
- Existing tests still pass.
