# Codex Prompt: Implement the Faber Work Queue 0003–0014

You are working in `lk251/faber`.

Read first:

1. `AGENTS.md`
2. `codex/nightly/README-2026-07-08.md`
3. Each issue file under `codex/nightly/` from `0003` through `0014`

Then implement the queue in numeric order.

## Repositories

- Main repo: `lk251/faber`
- Read-only reference repo: `lk251/agent-bounty-market`

Use `lk251/agent-bounty-market` only for ideas, invariants, and tests. Do not refactor it. Do not copy its hackathon/demo architecture into Faber.

## Mission reminder

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

The goal of this work queue is to make the repository substantially more useful: better local checks, stronger protocol validation, local lifecycle persistence, first-class verifiers, worker/router baselines, trajectory dataset export, GitHub product-loop polish, provider-agnostic market accounting, runner safety, and a delightful local golden path.

## Work order

Implement these in order:

1. `codex/nightly/0003-quality-gates-and-dev-experience.md`
2. `codex/nightly/0004-protocol-validation-and-errors.md`
3. `codex/nightly/0005-local-event-store-and-lifecycle.md`
4. `codex/nightly/0006-verifier-registry-and-local-runner.md`
5. `codex/nightly/0007-worker-registry-reputation-and-router.md`
6. `codex/nightly/0008-trajectory-dataset-export-and-evaluation.md`
7. `codex/nightly/0009-github-product-loop-polish.md`
8. `codex/nightly/0010-market-ledger-and-settlement-economics.md`
9. `codex/nightly/0011-trust-boundary-and-runner-safety.md`
10. `codex/nightly/0012-delightful-golden-path-and-docs.md`
11. `codex/nightly/0013-reference-extraction-from-agent-bounty-market.md`
12. `codex/nightly/0014-autonomous-hardening-pass.md`

## Implementation principles

- Keep the core verifier-first and trajectory-first.
- GitHub is an adapter, not the core.
- Payments are adapters, not the core.
- Model providers are adapters, not the core.
- Verifiers are first-class objects.
- Trajectories are first-class objects.
- Settlement follows verification.
- Use integer minor units for money. No floats for money.
- Preserve stable canonical serialization and stable digests.
- Prefer explicit dataclasses and boring deterministic functions.
- Keep NixOS first-class.
- Do not require Docker.
- Do not add real GitHub API calls, real payment providers, real model providers, web UI, background workers, Kubernetes, or cloud-specific assumptions.

## Check cadence

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

If a check fails because of an implementation issue, fix it before moving on. If a check cannot run because of the execution environment, record the exact reason and run the closest available checks.

## Commit cadence

Prefer one clean commit per issue with a clear message, for example:

```text
Implement issue 0003 quality gates
Implement issue 0004 protocol validation
```

## Final response

When finished, summarize:

- issues completed
- important files changed
- commands/checks run
- any checks that could not be run and why
- any issue partially completed and why
- next three recommended issues for human review
