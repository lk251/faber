# ADR 0001: Fresh Start

## Status

Accepted.

## Decision

Faber starts as a fresh repository instead of refactoring the previous hackathon
repository.

## Context

The long-term scarce asset is verified trajectories for orchestration learning,
not bounty settlement. The hackathon repository can provide ideas, invariants, and
tests, but its architecture is not the right root for a verifier-first,
trajectory-first system.

## Consequences

We will port useful ideas, invariants, and tests from the hackathon repo later, but
not its architecture.

GitHub is an adapter. The core is task contracts, attempts, verifier receipts,
trajectories, routing decisions, and settlement.
