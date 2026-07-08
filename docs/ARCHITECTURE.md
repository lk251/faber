# Architecture

Faber is verifier-first and trajectory-first. The core protocol models work as
task contracts, attempts, verifier runs, verification receipts, trajectories,
settlements, worker profiles, router decisions, and market events.

The root abstractions are independent from any one task source, payment provider,
model provider, or hosted product. GitHub, payments, and model calls enter through
adapters.

## Trust Boundary

Candidate-owned CI can provide useful signal, but it is not authoritative by
itself. Platform-owned or repository-owner-approved verifier policy produces
authoritative receipts.

The core stores the boundary explicitly:

- `TaskContract` describes desired work and accepted verifier policy.
- `Attempt` records worker output against a base and candidate revision.
- `VerifierRun` records verifier execution evidence.
- `VerificationReceipt` binds contract digest, attempt, worker, verifier, base
  revision, candidate revision, and result digest.
- `Trajectory` packages the full learning/audit record.
- `Settlement` follows accepted verification.

## Adapter Boundaries

The GitHub adapter should translate issues, pull requests, commits, checks, and
comments into protocol objects. It should not define the core lifecycle.

Payment adapters should settle accepted receipts. They should not decide whether
work is accepted.

Model provider adapters should provide worker or router capabilities. They should
not be hardcoded into protocol objects.
