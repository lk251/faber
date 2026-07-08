# Market Ledger

Faber is not a payment processor. Payments remain adapters outside the core.

The local market ledger models provider-agnostic accounting facts:

- reservations from buyer accounts into escrow
- worker payouts after accepted verification receipts
- verifier fees
- platform fee or margin
- retained operating spend buckets
- refunds for rejected or expired work

Every ledger entry has a source account, destination account, integer minor-unit
amount, currency, reason, related receipt when applicable, and idempotency key.

Ledger entries are append-only. Repeating an operation with the same idempotency
key returns the existing entry instead of double-paying or double-reserving.

Normal accounts cannot go negative. External or clearing accounts may explicitly
allow negative balances for local reconciliation fixtures.
