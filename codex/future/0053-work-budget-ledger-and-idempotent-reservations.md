# 0053 — Work budget ledger and idempotent reservations

## Goal

Strengthen Faber's local work-budget ledger so funded tasks can reserve, release, split, and settle budgets exactly once.

## Scope

Add or extend:

- `WorkBudgetLedger`
- `BudgetAccount`
- `BudgetReservation`
- `BudgetRelease`
- `BudgetSettlement`
- `BudgetReconciliationReport`

## Requirements

- Integer minor units only.
- Idempotency keys for all state-changing operations.
- No payout without accepted authoritative receipt.
- Support reservation release on rejection/expiry.
- Support split settlement for worker, verifier, platform margin, and trace-quality bonus.
- Keep provider references opaque.
- Store append-only ledger events when local store exists.

## Tests

- idempotent reserve
- duplicate settle does not double pay
- rejected attempt releases or refunds by policy
- split settlement sums exactly
- trace-quality bonus requires policy and evidence level
- reconciliation report explains balances

## Acceptance criteria

Faber has exact local economics for funded work while still keeping payment providers outside the core.