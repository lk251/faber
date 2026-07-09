# Faber Protocol

Faber Protocol is the open schema layer for verified work and trajectory export.

Initial root objects:

- `TaskContract`
- `Attempt`
- `VerifierRun`
- `VerificationReceipt`
- `Trajectory`
- `Settlement`
- `WorkerProfile`
- `RouterDecision`
- `MarketEvent`

The protocol should support JSON and JSONL export for audit and training. A JSONL
trajectory stream should be useful for supervised learning, reinforcement learning,
preference learning, router training, and verifier-quality analysis.

The protocol must remain compatible with hosted and self-hosted runners, multiple
payment providers, multiple model providers, and non-GitHub task sources.

GitHub evidence can seed task contracts and attempts, but receipts should bind
approved verifier outputs rather than trusting candidate-owned CI as authority.

## Validation Philosophy

Faber Protocol objects validate essential invariants at construction time. Required
identifiers must be non-empty strings, schema names must match stable versioned
constants, digest fields must use `sha256:<hex>`, and money must remain in integer
minor units.

Metadata stays extensible. Adapter-specific context, review notes, cost details,
and future training annotations may use ordinary dictionaries as long as the core
audit fields remain stable and explicit.

Shared error types in `faber.errors` make failure boundaries inspectable:
validation failures use `ValidationError`, scope failures use `ScopeError`, digest
mismatches use `DigestMismatchError`, settlement invariant failures use
`SettlementError`, and verifier/runner failures use `VerifierError`.

## Product Boundary

Protocol portability, self-hosted components, hosted services, paid verification,
data visibility, and premium training outputs are separated in
[`PRODUCT_BOUNDARIES.md`](PRODUCT_BOUNDARIES.md).

Schema IDs, strict unknown-version handling, no-op current upgrades, deprecation
warnings, and dataset schema inventories are defined in
[`SCHEMA_VERSIONING.md`](SCHEMA_VERSIONING.md).
