# AGENTS.md

This repository is Faber.

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

## Session startup

After reading this file, read `docs/CODEX_SESSION_HANDOFF.md`. It is the canonical
machine-transfer and session-resume index: it identifies the current milestone,
recommended next action, validation baseline, and external-action boundaries.
Update it before a machine switch or when those facts materially change.

## Mission

Build a useful, profitable, verifier-first agent labor market that produces high-quality verified trajectories for training cost-effective orchestrated models.

Democratization here does not mean "always cheapest." It means discovering, measuring, and making accessible high-intelligence-per-euro solutions, including open/self-hosted options, paid hosted verifiers, premium proprietary models, and future learned orchestrations.

## Architectural commitments

- Keep the core verifier-first and trajectory-first.
- GitHub is an adapter, not the core.
- Payments are adapters, not the core.
- Model providers are adapters, not the core.
- Verifiers are first-class objects, not incidental test scripts.
- Trajectories are first-class objects, not logs.
- Settlement follows verification; verification does not follow settlement.
- Market data should be exportable for later supervised learning, reinforcement learning, preference learning, and router/orchestrator training.
- The open protocol should be useful even if the hosted Faber service does not exist.

## Terminology

- Faber for GitHub is the GitHub adapter and future GitHub App.
- Faber Market is the buyer/seller marketplace.
- Faber Protocol is the open schema layer.
- Faber Runner is the self-hosted execution/verifier component.
- Faber Verifiers is the verifier layer or verifier marketplace.
- Faber Orchestration is the training and routing system built from verified trajectories.

## Do not import old hackathon assumptions

The old repository `lk251/agent-bounty-market` may be used as read-only reference for ideas, invariants, and tests.

Do not refactor that repo in place.
Do not copy its architecture into Faber.
Do not introduce hackathon demo code.
Do not hardcode Stripe, NVIDIA, Hermes, Motoko, OpenAI, Anthropic, Google, or any specific vendor into the core.

## Core objects

The root objects are not bounties or payments. They are:

1. `TaskContract`
2. `Attempt`
3. `VerifierRun`
4. `VerificationReceipt`
5. `Trajectory`
6. `Settlement`
7. `WorkerProfile`
8. `RouterDecision`
9. `MarketEvent`

## Trust boundary

Keep candidate code and platform/verifier policy separated by a trust boundary.

Candidate-owned CI is useful signal, not authority. Platform-owned or repo-owner-approved verifiers produce authoritative receipts.

## Implementation rules

- Use integer minor units for money. No floats for money.
- Keep state transitions explicit, inspectable, and idempotent.
- Prefer stable canonical serialization for audit/training data.
- Make digests stable and test them.
- Prefer explicit dataclasses over framework magic.
- Prefer boring deterministic functions.
- Do not hide important behavior behind global state.
- Keep dependency count low.
- Keep NixOS as the first-class development environment.
- Avoid Windows assumptions.
- Do not require Docker for the initial implementation.

## Testing rules

Add tests before extending settlement, verifier, routing, or trajectory behavior.

Before claiming completion, run:

```bash
nix develop --command just check
```

If Nix is unavailable in the execution environment, run the closest local equivalents and state exactly what could not be run.

## First task

Read and implement:

```text
codex/prompts/0001-implement-faber-core.md
```

Treat `lk251/agent-bounty-market` as read-only reference only.
