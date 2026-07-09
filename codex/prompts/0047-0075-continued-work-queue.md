# Codex Prompt: Implement Faber continued work queue 0047-0075

You are working in `lk251/faber`.

This queue follows work item `0046: RL-grade trajectory by default`.

## Read first

1. `AGENTS.md`
2. `docs/TRACE_STRATEGY.md`
3. `docs/TRAJECTORY_SCHEMA.md`
4. `docs/SOLVER_METADATA.md`
5. `docs/REPRODUCIBILITY_AND_PLATFORMS.md`
6. `docs/FUNDING_AND_WORK_BUDGETS.md`
7. `codex/future/README-0047-0075.md`
8. Each work item file from `0047` through `0075`

## Repositories

Main repo:

- `lk251/faber`

Read-only references:

- `lk251/agent-bounty-market`
- `lk251/llm-as-a-verifier`
- `NousResearch/hermes-agent`

Use reference repos only for ideas, invariants, issue selection, and test inspiration. Do not refactor them. Do not copy their architecture into Faber. Do not make them dependencies of Faber core.

## Mission

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

After work item 0046, the next goal is to make RL-grade trajectory collection commercially, technically, and socially viable: rights/consent, privacy/redaction, validation, trace ingestion, budgeted work, multi-attempt competitions, human review, verifier calibration, route-training datasets, worker reputation, safe external pilots, and excellent local UX.

## Work order

Implement in numeric order:

1. `codex/future/0047-training-data-rights-consent-and-licensing.md`
2. `codex/future/0048-redaction-secrets-and-private-trace-policy.md`
3. `codex/future/0049-trajectory-validation-cli-and-quality-reports.md`
4. `codex/future/0050-trace-ingestion-sdk-and-adapter-contract.md`
5. `codex/future/0051-non-github-task-source-and-submission-adapters.md`
6. `codex/future/0052-github-budget-markers-and-funded-issue-protocol.md`
7. `codex/future/0053-work-budget-ledger-and-idempotent-reservations.md`
8. `codex/future/0054-competition-claim-and-multi-attempt-market-policy.md`
9. `codex/future/0055-task-contract-templates-and-verification-policy-dsl.md`
10. `codex/future/0056-human-review-receipts-and-maintainer-approval.md`
11. `codex/future/0057-verifier-calibration-and-oracle-comparison.md`
12. `codex/future/0058-probabilistic-verifier-adapter-boundary.md`
13. `codex/future/0059-cost-aware-candidate-tournament.md`
14. `codex/future/0060-router-training-dataset-features-and-labels.md`
15. `codex/future/0061-worker-reputation-and-value-per-euro-scorecards.md`
16. `codex/future/0062-hermes-pilot-issue-selection-and-task-contract.md`
17. `codex/future/0063-nixos-reproducibility-verifier-pack.md`
18. `codex/future/0064-cross-platform-agent-harness-fixtures.md`
19. `codex/future/0065-fake-github-funded-task-end-to-end.md`
20. `codex/future/0066-cli-golden-path-for-funded-rl-grade-task.md`
21. `codex/future/0067-risk-gating-for-funded-agent-tasks.md`
22. `codex/future/0068-open-protocol-vs-hosted-product-boundaries.md`
23. `codex/future/0069-data-retention-deletion-and-audit-policy.md`
24. `codex/future/0070-local-mode-and-hosted-mode-boundaries.md`
25. `codex/future/0071-schema-versioning-and-compatibility.md`
26. `codex/future/0072-golden-fixture-corpus-and-snapshot-tests.md`
27. `codex/future/0073-local-store-scale-and-performance-smoke.md`
28. `codex/future/0074-customer-delight-copy-and-error-messages.md`
29. `codex/future/0075-roadmap-synthesis-after-rl-grade-queue.md`

## Implementation principles

- Keep the core verifier-first and trajectory-first.
- Optimize for RL-grade trajectories where task policy requires them.
- Keep PR-only work possible when explicitly allowed, but mark it low evidence.
- GitHub is an adapter, not the core.
- Payments and funding sources are adapters, not the core.
- Model providers are adapters, not the core.
- Hermes Agent and llm-as-a-verifier are read-only references, not dependencies.
- Use integer minor units for money. No floats for money.
- Preserve stable canonical serialization and stable digests.
- Use deterministic fake adapters/backends before real integrations.
- Do not require private prompts, chain-of-thought, finetune weights, or proprietary harness internals.
- Support disclosure levels, redaction, training consent, and dataset filtering.
- Settlement follows authoritative verification.
- Advisory probabilistic verification cannot release payment unless explicit task policy allows it.
- Keep NixOS first-class but not mandatory for every task.
- Keep local mode useful without external accounts or telemetry.

## Non-goals

- Do not train models.
- Do not add ML frameworks.
- Do not add real model provider integrations.
- Do not add real payment provider integrations.
- Do not add web UI.
- Do not add background workers.
- Do not add cloud-specific assumptions.
- Do not make Hermes Agent a Faber dependency.
- Do not make GitHub the root abstraction.

## Check cadence

After each work item, run:

```bash
nix develop --command just check
```

If Nix is unavailable, run:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

If a check fails because of implementation, fix it before moving on. If a check cannot run because of the environment, record the exact reason and run the closest available checks.

## Commit cadence

Prefer one clean commit per work item with a clear message, for example:

```text
Implement work item 0047 training data rights
Implement work item 0048 trace redaction policy
```

## Final summary

When finished, report:

- work items completed
- important files changed
- commands/checks run
- any checks that could not be run and why
- any work item partially completed and why
- recommended first real external Faber pilot task
- next five recommended work items after 0075
