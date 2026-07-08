# 0007 — Worker registry, reputation, and router baseline

## Goal

Introduce the first practical mechanism for matching tasks to workers: a simple worker registry, reputation signals, and a baseline router that records decisions for future learning.

This is not a marketplace matching algorithm yet. It is the minimum useful substrate for measuring intelligence per euro.

## Scope

Extend or add:

- worker profiles
- worker capability declarations
- worker cost models
- reputation summaries
- router decision inputs
- baseline deterministic routing policy
- router evaluation tests

## Requirements

1. Extend `WorkerProfile` if needed to include:
   - worker id
   - display name
   - owner/operator reference if useful
   - capabilities
   - supported task sources
   - supported languages/frameworks as metadata
   - cost model in integer minor units
   - historical reputation summary
   - availability/status field if useful
2. Add a `WorkerRegistry` with register/list/resolve operations.
3. Add reputation update helpers that can consume outcomes from trajectories:
   - accepted attempts
   - rejected attempts
   - verifier failures
   - review friction
   - latency
   - cost
4. Add a deterministic baseline router that selects a worker using transparent scoring.
5. Router decisions must record:
   - selected worker
   - rejected alternatives
   - estimated cost
   - expected value
   - policy name/version
   - decision factors
6. The router should prefer good expected value, not merely low cost.
7. Add a simple evaluation fixture that demonstrates a cheap worker winning on one task and a more expensive/specialist worker winning on another.
8. Do not call real model providers.
9. Do not build marketplace settlement or bidding in this issue.

## Craftsmanship bar

The router should be inspectable. A customer or developer should be able to understand why a worker was selected.

## Tests

Add tests for:

- worker registry behavior
- worker profile digest stability
- reputation update from accepted and rejected trajectories
- router selects the best value worker in simple cases
- router records rejected alternatives and decision factors
- router does not choose solely by cheapest cost

## Acceptance criteria

- Worker registry exists and is tested.
- Reputation can be updated from trajectory outcomes.
- Baseline router emits useful `RouterDecision` records.
- Router behavior supports future supervised/RL training data.
- Existing tests still pass.
