# Local store performance smoke

`run_local_performance_smoke()` guards the local SQLite and JSONL path against
obvious regressions. Its default corpus contains:

- 300 task contracts;
- 500 attempts;
- 1,000 lifecycle events;
- 250 stored and exported RL-grade trajectories.

The smoke uses generated fake records, one SQLite file, and one JSONL file. It
does not contact an external database or hosted service.

`save_records_batch()` and `save_lifecycle_events_batch()` preserve the existing
digest and idempotency checks while using one transaction per batch. Replaying the
contract and event batches must not increase row counts.

The normal test gate allows 30 seconds for the complete smoke and 15 seconds each
for store writes and dataset export. These are regression ceilings, not throughput
claims or production service objectives. Update them only after measuring a real
cross-platform regression; do not tune the architecture around this synthetic
fixture prematurely.
