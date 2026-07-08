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

## Trace, Metadata, Funding, And External Pilots

This track is defined in `docs/TRACE_STRATEGY.md`,
`docs/SOLVER_METADATA.md`, `docs/REPRODUCIBILITY_AND_PLATFORMS.md`,
`docs/FUNDING_AND_WORK_BUDGETS.md`, `docs/RISK_REVIEW.md`,
`docs/ADR-0003-traces-metadata-reproducibility-and-funding.md`, and the
0030-0045 queue.

1. Keep the trace protocol and evidence ladder central: PR-only fallback,
   `.faber/attempt.json`, Faber Runner traces, harness-native adapters, and
   replayable episode packages should coexist under explicit task policy.
2. Use solver metadata and provenance for routing and learning, with exact,
   coarse, and private disclosure modes plus explicit trust levels.
3. Treat cross-platform reproducibility honestly. NixOS can be preferred for
   high-replayability tasks, while Windows, macOS, other Linux, containers, and
   remote runners remain valid when recorded with environment evidence.
4. Model funded GitHub issues through provider-agnostic work budgets,
   allocations, reservations, refund policies, and receipt-gated settlement.
5. Keep funding source adapters deterministic first. Existing repository funding
   surfaces should reconcile into `FundingEvent`, `FundingSource`, and
   `WorkBudget` records without turning core into a payment processor.
6. Continue harness-native trace adapters from fake fixtures before adopting real
   harness internals. The Hermes-like adapter remains an adapter, not a core
   dependency.
7. Use the offline agent harness benchmark to test local verifiers, attempt
   manifests, trace examples, and dataset export without model providers or
   external services.
8. Use best-of-N selection records to preserve rejected attempts as training
   data while accepted authoritative receipts dominate advisory ranking.
9. Use skill/plugin safety manifests to declare platform support, permissions,
   dependencies, and verifier checks before relying on third-party extensions.
10. Treat Hermes Agent as the current external pilot candidate set, with #48628
    the default first task unless upstream status changes before launch.
11. Run risk review before funded external work. Credentials, private data,
    external writes, regulated domains, security-sensitive repositories, and
    payment-provider assumptions require explicit review metadata.
12. Preserve privacy: do not require private chain-of-thought, proprietary
    prompts, finetune weights, provider secrets, or raw traces when redacted
    structured evidence is sufficient.
