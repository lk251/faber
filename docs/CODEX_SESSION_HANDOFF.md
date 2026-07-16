# Codex session handoff

This is Faber's machine-transfer and session-resume index. It records operational
state and points to the authoritative design documents; it does not replace them.
Read this file after `AGENTS.md` when starting on a fresh clone. Update it before a
machine switch or after a milestone changes the recommended next action.

## Repository snapshot

- Repository: `lk251/faber`
- Canonical branch: `master` (`main` was intentionally removed)
- Implementation baseline before this handoff: `64f775c` (`Implement work item
  0075 roadmap synthesis`)
- Snapshot date: 2026-07-16
- Local state before the handoff commit: clean and 52 commits ahead of
  `origin/master`; the handoff commit and those commits are intended to be pushed
  together so a fresh clone is complete.
- Runtime baseline used on HB2: Python 3.11.15, pytest 9.0.2, Ruff 0.15.10, and
  mypy 2.1.0.

The remote `master` branch is authoritative after synchronization. Confirm the
checked-out commit and working tree instead of relying on the snapshot above:

```bash
git status -sb
git log -1 --oneline --decorate
```

## Start on another machine

Use a repository-specific, non-FIDO Ed25519 SSH key for every Faber fetch, pull,
and push. Do not commit or casually copy a private key. Create a key on the new
machine, add its public key to the Faber repository as a write-enabled deploy key,
and constrain Git to that identity. A Windows PowerShell setup looks like:

```powershell
$key = "$env:USERPROFILE/.ssh/faber_github_deploy_ed25519"
ssh-keygen -t ed25519 -f $key -C "faber repository key"
$env:GIT_SSH_COMMAND = "`"C:/Windows/System32/OpenSSH/ssh.exe`" -i `"$key`" -o IdentitiesOnly=yes -o AddKeysToAgent=no"
git clone git@github.com:lk251/faber.git
Set-Location faber
git config core.sshCommand "`"C:/Windows/System32/OpenSSH/ssh.exe`" -i `"$key`" -o IdentitiesOnly=yes -o AddKeysToAgent=no"
```

Keep the private key machine-local. On another operating system, use the same
identity constraints with that system's OpenSSH executable.

Then establish the development baseline:

```powershell
python --version
python -m pip install pytest ruff mypy
$env:PYTHONPATH = "src"
python -m pytest
python -m ruff check .
python -m mypy src
```

Python 3.11 or newer is required. Faber has no runtime package dependencies. The
canonical repository check remains `nix develop --command just check` where Nix is
available, but Nix was unavailable on HB2 and is not a blocker for the current
Windows workflow.

Local `.faber/` artifacts are disposable and are not transferred by Git. Recreate
the complete local funded trajectory example with:

```powershell
$env:PYTHONPATH = "src"
python -m faber.cli demo-funded-trajectory --out-dir .faber/funded-demo
```

## What is complete

The repository contains a tested local foundation for verifier-first work and
RL-grade trajectory collection:

- Work items 0030-0045 implement trace acquisition, attempt manifests, solver and
  environment metadata, work budgets, funding adapter stubs, and Hermes planning.
- Issue 0046 makes trajectory quality explicit and supports RL-grade validation,
  task requirements, evidence levels, process and replay evidence, reward signals,
  training eligibility, consent, and filtered dataset export.
- Work items 0047-0075 add data rights, trace privacy, validation and ingestion,
  generic source adapters, budget and competition policy, human and probabilistic
  verification, tournaments, learning datasets, scorecards, the Hermes pilot
  package, optional reproducibility verifiers, cross-platform fixtures, a complete
  fake funded loop, risk gates, retention, runtime and product boundaries, schema
  compatibility, golden fixtures, performance smoke coverage, customer-facing CLI
  output, and roadmap synthesis.
- `lk251/agent-bounty-market` and `lk251/llm-as-a-verifier` are read-only research
  references. Their vendor or demo architecture is not part of Faber's core.

The last full HB2 fallback validation, run after work item 0075, was:

- `python -m pytest`: 309 passed
- `python -m ruff check .`: passed
- `python -m mypy src`: passed across 75 source files
- funded trajectory demo and trajectory validation: passed, RL-grade, one eligible
  dataset record
- `nix develop --command just check`: unavailable because Nix was not installed

Run the checks again on the new machine; this section is evidence, not a substitute
for validating the clone.

## Read in this order

1. [`AGENTS.md`](../AGENTS.md) for non-negotiable architecture and work rules.
2. [`ROADMAP.md`](ROADMAP.md) for the current decision and next five work items.
3. [`MILESTONES.md`](MILESTONES.md) for completed and blocked stages.
4. [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) for decisions that require human,
   maintainer, security, legal, or research judgment.
5. [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PROTOCOL.md`](PROTOCOL.md), and
   [`GLOSSARY.md`](GLOSSARY.md) for system structure and exact terminology.
6. [`TRACE_STRATEGY.md`](TRACE_STRATEGY.md),
   [`TRAJECTORY_SCHEMA.md`](TRAJECTORY_SCHEMA.md), and
   [`TRAJECTORY_VALIDATION.md`](TRAJECTORY_VALIDATION.md) before changing evidence
   or learning behavior.
7. [`DATA_RIGHTS.md`](DATA_RIGHTS.md), [`TRACE_PRIVACY.md`](TRACE_PRIVACY.md), and
   [`RISK_REVIEW.md`](RISK_REVIEW.md) before collecting external data or running
   external work.

The implementation queue and acceptance criteria remain in `codex/future/`. Git
history has one focused commit for each completed work item, which is the most
precise way to inspect why a particular module or test was added.

## Current code map

- `src/faber/schemas.py`, `contracts.py`, `trajectories.py`, and
  `trajectory_quality.py`: protocol records and trajectory quality decisions.
- `src/faber/traces.py`, `trace_ingestion.py`, `redaction.py`, and
  `data_rights.py`: process evidence, ingestion, privacy, consent, retention, and
  training-use controls.
- `src/faber/verifiers.py`, `reviews.py`, `calibration.py`, and `probabilistic.py`:
  hard authority, human review, calibration, and advisory scoring.
- `src/faber/budgets.py`, `budget_ledger.py`, `market_policies.py`, and
  `tournaments.py`: provider-neutral budgets, reservations, settlement policy, and
  candidate selection.
- `src/faber/adapters/`: GitHub, Hermes, local, and trace boundaries. Adapters do
  not define core protocol semantics.
- `src/faber/adapters/github/funded_product_loop.py` and `src/faber/funded_demo.py`:
  the local fake funded flow used for end-to-end acceptance.
- `src/faber/cli.py`: inspectable local workflows and validation commands.
- `tests/fixtures/golden/`: canonical cross-platform and trajectory snapshots.

## Recommended next action

Milestone 2 is a human-approved, unpaid external dry run based on
`NousResearch/hermes-agent` issue #61631. The selection was last checked on
2026-07-09, so first verify that the issue is still open, unclaimed, and suitable.
The package and rationale are in
[`HERMES_AGENT_PILOT_SELECTION_2026-07-09.md`](research/HERMES_AGENT_PILOT_SELECTION_2026-07-09.md)
and `src/faber/adapters/hermes/scheduler_delivery_pilot.py`.

Do not begin solver execution, contact maintainers, publish an upstream branch or
PR, reserve real funds, use production credentials, or collect private data merely
because the package exists. The next operator must obtain Javier's approval for the
external action and maintainer/reporter approval for the contribution. The first
pilot remains unpaid, local, fixture-driven, and manually published.

The next implementation item, if work continues locally before the external run,
is the external pilot runbook and evidence bundle listed first in
[`ROADMAP.md`](ROADMAP.md). It should instantiate the existing contract, record
human risk approval, ingest a redacted harness trace, run approved verifiers, and
package review artifacts without performing an external write.

## Invariants to preserve

- Verification is authoritative before settlement; payment state cannot rewrite a
  receipt.
- GitHub, payment providers, model providers, and hosted services remain adapters.
- Candidate-owned CI is evidence, not verifier authority.
- PR-only work may be valid customer work but is low-evidence and not RL-grade by
  default.
- Training permission is separate from work acceptance and payout.
- Money uses integer minor units; state transitions and serialization stay explicit,
  deterministic, digest-stable, and idempotent.
- No private prompts, hidden reasoning, provider credentials, model weights, or
  proprietary harness internals are required for RL-grade evidence.
- Do not make Nix mandatory for every task or introduce Windows-only core behavior.

## Before the next machine switch

1. Re-run the available checks and record exact results here if they materially
   changed.
2. Update the snapshot, current milestone, recommended next action, and known
   blockers; remove stale operational detail instead of accumulating a diary.
3. Ensure `git status -sb` is understood and no local `.faber/` artifact is needed
   as source material.
4. Commit clearly and push the intended branch with the repository-specific SSH
   identity.
5. Verify the remote commit from a fresh fetch before shutting down.
