# Roadmap

These are likely next issues after the 0003-0014 queue. They are intentionally
not implemented in this pass.

1. Add durable verifier-run recovery so completed verifier runs replay by
   idempotency key and incomplete runs retry cleanly.
2. Persist the market ledger to the local store with append-only entries,
   account snapshots, and reconciliation checks.
3. Define an explicit task lifecycle state machine from contract creation through
   attempt, verification, settlement, and trajectory export.
4. Add verifier spec manifests with stable digests, compatibility checks, and
   repository-owner approval metadata.
5. Introduce a runner backend interface so local process execution can be swapped
   for stronger isolation without changing protocol records.
6. Add a durable Faber for GitHub publication journal with replay and dry-run CLI
   commands.
7. Add worker profile import/export so Faber Market can move worker capability
   and reputation data between local stores.
8. Build router evaluation datasets that compare selected workers, rejected
   alternatives, cost, latency, and verified outcomes.
9. Add trajectory privacy policies for redaction, retention, and training splits.
10. Define payment adapter contracts around accepted receipts while keeping
    integer-money settlement and local fake settlement first.
