# Faber

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

This repository is intentionally seeded with project guidance only. The first implementation pass should be done by Codex Cloud using `AGENTS.md` and `codex/prompts/0001-implement-faber-core.md`.

## First implementation task

Implement the initial Faber repository skeleton, Nix-first development environment, protocol/domain primitives, stable digests, integer-money invariants, trajectory export, and tests described in:

```text
codex/prompts/0001-implement-faber-core.md
```

## Reference repository

The previous hackathon prototype is:

```text
lk251/agent-bounty-market
```

Use it only as read-only reference for ideas, invariants, tests, and lessons. Do not refactor it in place. Do not copy hackathon demo, Stripe, NVIDIA, Hermes, Motoko-specific, or presentation-bundle assumptions into Faber's core.

## Intended first integration

Faber for GitHub is the first integration. GitHub is an adapter, not the root abstraction.

The root abstractions are:

- `TaskContract`
- `Attempt`
- `VerifierRun`
- `VerificationReceipt`
- `Trajectory`
- `Settlement`
- `WorkerProfile`
- `RouterDecision`
- `MarketEvent`

The scarce asset is the verified trajectory stream: tasks, attempts, verifier outcomes, cost, latency, review signal, settlement, and eventual routing/orchestration decisions.
