# 0059 — Cost-aware candidate tournament

## Goal

Implement a local, deterministic candidate tournament for selecting among multiple attempts under a verifier budget.

## Scope

Add:

- `CandidatePool`
- `CandidateComparison`
- `TournamentPolicy`
- `TournamentResult`
- budget-aware pairwise comparison scheduler
- stable tournament audit log

## Requirements

- Use fake deterministic pairwise scoring.
- Support full round robin for small pools and pivot-style reduced comparison for larger pools.
- Track comparison count, estimated verifier cost, latency, selected attempt, rejected alternatives, and uncertainty.
- Hard authoritative verifier outcomes dominate advisory tournament scores when available.
- Tournament output must be exportable into trajectory/dataset records.

## Tests

- small pool full comparison
- larger pool reduced comparison
- budget cap stops comparison
- hard accepted candidate wins
- rejected alternatives are recorded
- tournament result digest is stable

## Acceptance criteria

Faber can spend verifier budget intelligently when many agents submit candidate solutions.