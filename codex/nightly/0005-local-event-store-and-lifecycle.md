# 0005 — Local event store and lifecycle

## Goal

Turn the local SQLite store from a skeleton into a useful append-oriented development store for Faber protocol records and lifecycle events.

This is still local/self-hosted infrastructure, not a hosted service.

## Scope

Implement a small persistence layer for:

- task contracts
- attempts
- verifier runs
- verification receipts
- trajectories
- settlements
- worker profiles
- router decisions
- market events

## Requirements

1. Keep SQLite as the local development store.
2. Prefer append-only event recording for audit history.
3. Add tables only as needed. Keep schema simple and readable.
4. Store canonical JSON payloads and stable digests.
5. Enforce idempotent inserts by record id and/or digest.
6. Provide repository-style functions for saving and loading records.
7. Add `MarketEvent` helpers for important lifecycle transitions:
   - contract created
   - attempt submitted
   - verifier run recorded
   - receipt issued
   - trajectory exported
   - settlement created
   - settlement paid or failed
8. Add CLI commands if they fit cleanly:
   - `faber store-summary`
   - `faber list-contracts`
   - `faber show-trajectory <id>`
9. Do not add migrations framework yet unless absolutely necessary. A simple schema version table is enough.
10. Do not add a web server or background worker.

## Craftsmanship bar

The store should be boring, inspectable, and easy to debug with the `sqlite3` CLI. It should preserve auditability and avoid hidden mutation.

## Tests

Add tests for:

- creating a fresh store
- saving and loading each major record type
- idempotent save behavior
- duplicate digest behavior where appropriate
- event ordering
- store summary output
- trajectory export from persisted records

## Acceptance criteria

- Local store can persist the core Faber objects.
- Canonical payloads and digests are stored.
- Lifecycle events are append-only and tested.
- Existing CLI commands still work.
- Existing tests still pass.
