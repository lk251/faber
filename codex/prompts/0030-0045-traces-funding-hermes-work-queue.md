# Codex Prompt: Implement Faber trace, funding, and Hermes work queue 0030-0045

You are working in `lk251/faber`.

Read first:

1. `AGENTS.md`
2. `docs/TRACE_STRATEGY.md`
3. `docs/SOLVER_METADATA.md`
4. `docs/REPRODUCIBILITY_AND_PLATFORMS.md`
5. `docs/FUNDING_AND_WORK_BUDGETS.md`
6. `docs/research/HERMES_AGENT_ISSUE_SURVEY.md`
7. `docs/bounties/HERMES_AGENT_FIRST_TASKS.md`
8. `docs/ADR-0003-traces-metadata-reproducibility-and-funding.md`

Then implement the future issue files in numeric order when the current 0003-0014 queue is complete.

## Repositories

- Main repo: `lk251/faber`
- Read-only references:
  - `lk251/agent-bounty-market`
  - `lk251/llm-as-a-verifier`
  - `NousResearch/hermes-agent`

Use reference repos only for ideas, invariants, issue selection, and test inspiration. Do not refactor them. Do not make them dependencies of Faber core.

## Work order

1. `codex/future/0030-trace-protocol-and-evidence-ladder.md`
2. `codex/future/0031-attempt-manifest-in-pr.md`
3. `codex/future/0032-worker-harness-model-metadata-registry.md`
4. `codex/future/0033-cross-platform-reproducibility-evidence.md`
5. `codex/future/0034-work-budgets-and-funded-issues.md`
6. `codex/future/0035-github-funding-source-adapters.md`
7. `codex/future/0036-hermes-issue-survey-and-candidate-ranking.md`
8. `codex/future/0037-hermes-nixos-tier-one-packaging-pilot.md`
9. `codex/future/0038-hermes-trace-adapter.md`
10. `codex/future/0039-nixos-agent-harness-benchmark.md`
11. `codex/future/0040-faber-attempt-manifest-generator-for-hermes-prs.md`
12. `codex/future/0041-hermes-best-of-n-selection-pilot.md`
13. `codex/future/0042-hermes-skills-and-plugin-safety-manifests.md`
14. `codex/future/0043-real-external-faber-pilot-task-contract.md`
15. `codex/future/0044-risk-review-for-funded-agent-work.md`
16. `codex/future/0045-roadmap-update-traces-funding-hermes.md`

## Strategy

The core question is how Faber gets training-quality trajectories from a market where many solvers would otherwise submit only a PR.

Implement the evidence ladder:

- Level 0: PR-only fallback
- Level 1: PR + `.faber/attempt.json`
- Level 2: Faber Runner trace
- Level 3: harness-native trace adapter
- Level 4: replayable episode package

Faber should be NixOS-first for development and high-replayability tasks, but not NixOS-only. Windows, macOS, other Linux, containers, and remote runners are valid evidence sources when recorded honestly.

Faber should let people fund issues and work budgets, but payment providers remain adapters. Do not add real payment integrations.

Hermes Agent is a promising external pilot target. Inspect `NousResearch/hermes-agent` issues before selecting a candidate. Do not assume any specific Hermes problem is real until verified from upstream docs/issues. Do not make Hermes a Faber dependency.

## Implementation principles

- Keep the core verifier-first and trajectory-first.
- GitHub is an adapter, not the core.
- Payments are adapters, not the core.
- Model providers are adapters, not the core.
- Verifiers are first-class objects.
- Trajectories are first-class objects.
- Settlement follows authoritative verification.
- Use integer minor units for money. No floats for money.
- Preserve stable canonical serialization and stable digests.
- Use deterministic fake adapters/backends first.
- Do not require private prompts, finetune weights, chain-of-thought, or proprietary harness internals.
- Support redaction and disclosure levels.
- Keep NixOS first-class, but support cross-platform evidence.

## Non-goals

- No real GitHub API calls beyond existing fake adapter boundaries.
- No real payment provider integration.
- No real model provider integration.
- No web UI.
- No background worker.
- No cloud-specific assumptions.
- No dependency on Hermes Agent, llm-as-a-verifier, or agent-bounty-market.

## Checks

After each issue, run:

```bash
nix develop --command just check
```

If Nix is unavailable, run:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

Fix implementation failures before moving on. If a check cannot run because of the environment, record the exact reason and run the closest available checks.

## Final response

Summarize:

- issues completed
- important files changed
- commands/checks run
- any checks that could not be run and why
- any issue partially completed and why
- recommended first real external Faber pilot task
