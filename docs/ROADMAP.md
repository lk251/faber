# Roadmap

These are likely next issues after the 0003-0014 queue. They are intentionally
not implemented in this pass.

1. Add durable verifier-run recovery so completed verifier runs replay by
   idempotency key and incomplete runs retry cleanly.
2. Persist the market ledger to the local store with append-only entries,
   account snapshots, and reconciliation checks.
3. Define an explicit task lifecycle state machine from contract creation through
   attempt, verification, settlement, and trajectory export.
4. Add verifier spec manifests with stable digests, compatibility checks, and
   repository-owner approval metadata.
5. Introduce a runner backend interface so local process execution can be swapped
   for stronger isolation without changing protocol records.
6. Add a durable Faber for GitHub publication journal with replay and dry-run CLI
   commands.
7. Add worker profile import/export so Faber Market can move worker capability
   and reputation data between local stores.
8. Build router evaluation datasets that compare selected workers, rejected
   alternatives, cost, latency, and verified outcomes.
9. Add trajectory privacy policies for redaction, retention, and training splits.
10. Define payment adapter contracts around accepted receipts while keeping
    integer-money settlement and local fake settlement first.

## Probabilistic Verification Scaling

This research queue is tracked in `codex/future/0015` through `0022` and is based
on `docs/research/llm-as-a-verifier-2607-05391.md`. The reference project is
`lk251/llm-as-a-verifier`; use it for ideas and tests, not as a core dependency.

1. Add provider-agnostic probabilistic verifier protocol objects and deterministic
   fake scoring backends.
2. Implement a budget-aware Probabilistic Pivot Tournament for multi-attempt
   candidate ranking.
3. Add a local multi-attempt selection loop that combines authoritative hard
   verifier results, advisory probabilistic scores, and cost metadata.
4. Add trajectory progress scoring primitives for long-running agent monitoring.
5. Add dense reward export fields for supervised learning, preference learning,
   and reinforcement learning experiments.
6. Add verifier-quality and intelligence-per-euro metrics so Faber can compare
   verifier strategies, not only workers.
7. Harden authority boundaries so advisory LLM/probabilistic scores cannot settle
   payment unless explicitly approved.
8. Keep all initial work provider-agnostic, fake-backend-first, and independent
   from real model APIs.

## Trace Acquisition, Solver Metadata, And Harness Bounties

This track is defined in `docs/TRACE_STRATEGY.md`,
`docs/SOLVER_METADATA.md`, `docs/ADR-0003-traces-and-solver-metadata.md`, and
`codex/future/0023` through `0029`.

1. Define Faber's trace protocol and evidence ladder from PR-only fallback to
   replayable episode packages.
2. Support optional `.faber/attempt.json` manifests in pull requests.
3. Extend worker metadata to describe model, harness, environment, platform, cost,
   and trust level.
4. Add trace-quality incentives so richer, attested traces improve eligibility,
   reputation, and possibly economics.
5. Design a NixOS-first agent harness bounty pilot after investigating candidate
   harnesses. Hermes is only a candidate until evidence supports that choice.
6. Add harness-native trace adapter stubs that map fake native events into Faber
   trace events without depending on real harness packages.
7. Document data requirements for supervised learning, attempt quality
   prediction, harness/orchestration learning, verifier calibration, progress
   scoring, reinforcement learning, and value-per-euro evaluation.
8. Preserve privacy: do not require private chain-of-thought, proprietary prompts,
   finetune weights, or provider secrets.
