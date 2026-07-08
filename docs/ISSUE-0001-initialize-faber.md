# Issue 0001: Implement the initial Faber core

## Goal

Implement the initial Faber repository skeleton and core protocol/domain primitives described in:

```text
codex/prompts/0001-implement-faber-core.md
```

## Constraints

- Keep the project verifier-first and trajectory-first.
- GitHub is an adapter, not the root abstraction.
- Payments are adapters, not the root abstraction.
- Model providers are adapters, not the root abstraction.
- Do not hardcode Stripe, NVIDIA, Hermes, Motoko, OpenAI, Anthropic, Google, or any specific vendor into the core.
- Do not copy hackathon demo or presentation architecture from `lk251/agent-bounty-market`.
- Use `lk251/agent-bounty-market` only as read-only reference for ideas, invariants, and tests.
- Use NixOS as the first-class development environment.
- Do not require Docker for the first implementation.

## Acceptance criteria

- Repository has the structure specified in `codex/prompts/0001-implement-faber-core.md`.
- `nix develop` provides the expected development environment.
- `just check` runs formatting, linting, type checking, and tests.
- Stable canonical JSON and SHA-256 digest helpers exist and are tested.
- Money is represented only in integer minor units and rejects floats/negative amounts.
- Dataclass-based core objects exist for task contracts, attempts, verifier runs, receipts, trajectories, settlements, worker profiles, router decisions, and market events.
- Verification receipts bind task contract digest, attempt, worker, verifier, base revision, candidate revision, and result digest.
- Settlement cannot mark rejected work as paid.
- Trajectory export includes enough information for future supervised learning, reinforcement learning, and router/orchestrator training.
- Minimal CLI commands exist:
  - `python -m faber.cli doctor`
  - `python -m faber.cli init-local-store --path .faber/faber.sqlite3`
  - `python -m faber.cli emit-demo-trajectory --out .faber/demo_trajectory.json`

## Out of scope

- No web UI.
- No real GitHub API calls.
- No payment provider.
- No model provider integration.
- No marketplace matching algorithm.
- No background worker.
- No Docker/Kubernetes/cloud-specific assumptions.
