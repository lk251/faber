# ADR-0002: Probabilistic Verification Scaling

Status: Proposed

## Context

Faber already has verifier receipts, trajectories, GitHub adapter boundaries, a
local verifier runner, a local event store, and a provider-agnostic market ledger.
The next missing layer is a way to rank multiple candidate attempts, record
fine-grained verification evidence, estimate progress, and produce dense training
signals without making a model provider part of the core.

The paper "LLM-as-a-Verifier: A General-Purpose Verification Framework"
(arXiv:2607.05391v1) frames verification as its own scaling axis. It uses
probabilistic scores from scoring-token distributions, repeated evaluation,
criteria decomposition, and budget-aware candidate ranking.

## Decision

Faber will add a provider-agnostic probabilistic verification layer inspired by
LLM-as-a-Verifier.

Future implementation issues should introduce protocol objects and local fake
backends for:

- fine-grained verifier scores;
- criteria decomposition;
- repeated evaluation;
- pairwise preferences;
- budget-aware candidate ranking;
- progress scoring;
- dense reward export;
- calibration and evaluation of verifier quality.

LLM-based or probabilistic verifiers are advisory by default. They can influence
ranking, routing, monitoring, and training export, but they cannot release
settlement unless a task contract or task class explicitly approves that verifier
as authoritative.

## Consequences

- Faber can learn not just which worker succeeded, but which verifier or ranking
  strategy produced the best value per euro.
- Faber can compare cheap-many-attempts-plus-verifier strategies against
  expensive-single-attempt strategies.
- The architecture can support logprob-accessible models later without requiring
  them now.
- Closed-model reasoning plus open/logprob-scoring workarounds can be supported
  later through provider adapters.
- Deterministic hard tests, repository-owner-approved verifiers, and human review
  remain valid authority paths.
- The first implementation must stay local, fake, deterministic, and
  provider-agnostic.
