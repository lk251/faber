# AGENTS.md

This repository is Faber.

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

## Session startup

After reading this file, read `docs/CODEX_SESSION_HANDOFF.md`. It is the canonical
machine-transfer and session-resume index: it identifies the current milestone,
recommended next action, validation baseline, and external-action boundaries.
Update it before a machine switch or when those facts materially change.

## Temporary OpenAI Build Week override

Through the Faber Proof Build Week submission freeze, a request to continue Build Week,
continue Faber Proof, maximize the hackathon submission, resume the queue, or simply
"get to work" in that context has one unambiguous entrypoint:

1. Read `codex/BUILD_WEEK_START_HERE.md`.
2. Read `docs/BUILD_WEEK_2026.md` and `docs/FABER_PROOF_PRODUCT.md`.
3. Read `codex/build-week/STATUS.md`.
4. Use the repository skill `$build-week-director` when it is available.
5. Execute the first incomplete P0 prompt in `codex/future/` whose dependencies are
   complete.
6. Continue through subsequent P0 items without asking Javier to paste prompts.

The Build Week implementation should use branch `build-week/faber-proof`; create or
switch to it safely on the first local implementation run. Do not discard or stage
unrelated local work.

The normal Hermes external-pilot roadmap is temporarily paused, not cancelled. Resume
it only after the competition freeze or an explicit human decision. Do not contact an
upstream maintainer, publish externally, use production credentials, move money, or
collect private data as part of the Build Week queue.

All architectural, trust-boundary, testing, privacy, and external-action rules below
remain binding. Competition pressure is not permission to bypass them.

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
Do not introduce unrelated old hackathon demo code.
Do not hardcode Stripe, NVIDIA, Hermes, Motoko, OpenAI, Anthropic, Google, or any specific vendor into the core.

Faber Proof may include a direct OpenAI adapter because the Build Week product requires
it. The adapter must remain optional and outside the provider-neutral core. GPT-5.6
output is advisory data and may never define executable policy or replace authoritative
verifier evidence.

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

Faber Proof may add explicit proof-plan, proof-evidence, and proof-decision records. They
must bind to, rather than weaken or silently replace, the existing task, attempt,
verifier-run, and receipt authority model.

## Trust boundary

Keep candidate code and platform/verifier policy separated by a trust boundary.

Candidate-owned CI is useful signal, not authority. Platform-owned or repo-owner-approved verifiers produce authoritative receipts.

For Faber Proof, task text, repository content, diffs, model output, and replay bundles
are untrusted inputs. Only repository-owner-approved catalog entries and registered
verifier specifications may determine operational behavior. Incomplete or contradictory
evidence must fail closed.

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
- Keep optional provider SDKs out of the base runtime when practical.
- Preserve a no-key, no-network replay path for Faber Proof.
- Do not store private chain-of-thought or require it for verification evidence.

## Testing rules

Add tests before extending settlement, verifier, routing, trajectory, proof, or decision behavior.

Before claiming completion, run:

```bash
nix develop --command just check
```

If Nix is unavailable in the execution environment, run the closest local equivalents and state exactly what could not be run.

For every Build Week work item, also run the prompt-specific acceptance command and
update `codex/build-week/STATUS.md` with exact results before committing.

## Current task routing

During the Build Week override, do not restart the historical first task. Continue from:

```text
codex/BUILD_WEEK_START_HERE.md
codex/build-week/STATUS.md
```

The historical bootstrap prompt remains reference material only:

```text
codex/prompts/0001-implement-faber-core.md
```

Treat `lk251/agent-bounty-market` as read-only reference only.