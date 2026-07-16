# Codex session handoff

This is Faber's machine-transfer and session-resume index. It records operational state
and points to the authoritative design documents; it does not replace them. Read this
file after `AGENTS.md` on every fresh clone. Update it before a machine switch or when
the recommended next action or validation baseline changes.

## Active override: OpenAI Build Week 2026

Faber Proof is the active implementation priority through the competition submission
freeze.

The single entrypoint is:

```text
codex/BUILD_WEEK_START_HERE.md
```

The machine-resume state is:

```text
codex/build-week/STATUS.md
```

When available, invoke:

```text
$build-week-director
```

A user instruction such as "continue Build Week," "continue Faber Proof," or "get to
work" in this project context means: execute the first incomplete P0 work item whose
dependencies are complete, commit it, update the status file, and continue until a
human-only gate.

The ordinary Hermes external-pilot roadmap is paused until the competition freeze ends
or Javier explicitly changes the decision. Do not contact upstream maintainers, publish
an external branch or pull request, use production credentials, move money, or collect
private data as part of the Build Week queue.

## Repository snapshot

- Repository: `lk251/faber`
- Canonical long-lived branch: `master` (`main` was intentionally removed)
- Active Build Week implementation branch: `build-week/faber-proof`
- Branch starting commit: `c915523383dc58114bf748f7d7a64c1c398faaba`
- Eligibility baseline: `64f775cfe2f622837bd9aaa40f6369aa22af1d80`
  (`Implement work item 0075 roadmap synthesis`), the verified last commit strictly
  before `2026-07-13T09:00:00-07:00`
- Eligibility tag: annotated `build-week-2026-baseline`, verified locally at the
  baseline commit
- Eligible history at the branch starting point: 28 commits with no pre-cutoff author
  or committer dates; the focused 0076 completion commit is the 29th
- Active work item after the control-plane commit: `0077-proof-protocol-and-policy.md`
- Snapshot date: 2026-07-16
- Primary-session designation: this director thread is the primary Build Week
  implementation session; its `/feedback` ID has not yet been recorded
- Current local working-tree state: expected clean after the focused 0076 commit;
  inspect it rather than relying on this file

Confirm the checked-out state before changing anything:

```bash
git status -sb
git branch --show-current
git log -1 --oneline --decorate
git fetch --prune
```

Do not discard or stage unrelated local work. If the active machine has unpublished
commits, understand and preserve them before switching branches.

## Build Week product decision

The submission is **Faber Proof**:

> Codex can write the patch. Faber makes the patch prove itself.

The competition extension creates proof-carrying patches for agentic software
development:

1. An independent GPT-5.6 Sol call reads a task contract, bounded redacted diff, and
   approved proof catalog.
2. It expresses falsifiable claims and selects only catalog-approved, data-only proof
   templates.
3. Faber validates the plan, executes approved proof capabilities, and binds evidence
   into verifier runs and receipts.
4. A deterministic policy returns `PASS`, `BLOCK`, or `HUMAN_REVIEW`.
5. Codex uses a concrete failed claim and counterexample to repair the patch and rerun
   the proof.

GPT-5.6 is advisory. Model output cannot define operational behavior, replace
repository-approved verifier policy, or override failed or missing evidence.

The mandatory original demo shows:

```text
Bad patch:      ordinary tests PASS, Faber Proof BLOCK
Repaired patch: ordinary tests PASS, Faber Proof PASS
```

The blocked report must show the exact failed claim and concrete budget-boundary
counterexample above the fold.

## Build Week read order

For Build Week sessions, read in this order:

1. [`AGENTS.md`](../AGENTS.md)
2. [`BUILD_WEEK_START_HERE.md`](../codex/BUILD_WEEK_START_HERE.md)
3. [`BUILD_WEEK_2026.md`](BUILD_WEEK_2026.md)
4. [`FABER_PROOF_PRODUCT.md`](FABER_PROOF_PRODUCT.md)
5. [`STATUS.md`](../codex/build-week/STATUS.md)
6. The next incomplete prompt in `codex/future/`
7. Relevant architecture, protocol, privacy, runner, and test documents named by that
   prompt

The Build Week queue is:

```text
0076  competition boundary and handoff
0077  proof protocol and deterministic decision policy
0078  direct GPT-5.6 planner with live and replay modes
0079  bounded proof catalog and safe executors
0080  end-to-end CLI and self-contained evidence report
0081  repository-scoped Codex skill and original winning demo
0082  adversarial evals, packaging, clean install, and CI
0083  submission package, video, final audit, and freeze
0084  optional proof arena, blocked until every P0 gate is green
```

Prompts contain complete objectives, constraints, tests, acceptance criteria, and commit
instructions. Javier should not need to paste their contents into Codex.

## Autonomous session protocol

1. Work on `build-week/faber-proof` after work item 0076 establishes it safely.
2. Select the first incomplete P0 item in `codex/build-week/STATUS.md` whose dependencies
   are complete.
3. Implement only that item.
4. Add tests before or alongside verification, proof, routing, evidence, and decision
   changes.
5. Run the item-specific acceptance commands and the full available checks.
6. Update the status file with exact results and the demo scorecard.
7. Update this handoff when the recommended next action or validation baseline changes.
8. Make one focused commit.
9. Continue to the next P0 item while the working tree is clean and no human-only gate
   is required.

Keep work items 0077 through 0081 in one primary Codex thread where practical. Before
that thread ends, Javier must run `/feedback` and record the returned session ID. Use
fresh secondary sessions for architecture, security, installation, judge, and final
submission audits rather than parallel redesigns of the core protocol.

## Human-only gates

Codex may complete all deterministic local work without waiting. It must stop with an
exact instruction only for:

- supplying an OpenAI API key for a guarded live run;
- requesting or redeeming competition credits;
- running `/feedback` and copying the returned session ID;
- sharing the private repository with the official judging addresses;
- recording spoken narration and uploading a public YouTube video;
- completing and submitting the Devpost form;
- approving any external publication, third-party contribution, payment, production
  credential use, or private-data collection.

Do not mark one of these gates complete without the real value or explicit human
attestation.

## Start on another machine

Use a repository-specific, non-FIDO Ed25519 SSH key for every Faber fetch, pull, and
push. Do not commit or casually copy a private key. Create a key on the new machine, add
its public key to the Faber repository as a write-enabled deploy key, and constrain Git
to that identity. A Windows PowerShell setup looks like:

```powershell
$key = "$env:USERPROFILE/.ssh/faber_github_deploy_ed25519"
ssh-keygen -t ed25519 -f $key -C "faber repository key"
$env:GIT_SSH_COMMAND = "`"C:/Windows/System32/OpenSSH/ssh.exe`" -i `"$key`" -o IdentitiesOnly=yes -o AddKeysToAgent=no"
git clone git@github.com:lk251/faber.git
Set-Location faber
git config core.sshCommand "`"C:/Windows/System32/OpenSSH/ssh.exe`" -i `"$key`" -o IdentitiesOnly=yes -o AddKeysToAgent=no"
```

Keep the private key machine-local. On another operating system, use the same identity
constraints with that system's OpenSSH executable.

Establish the development baseline:

```powershell
python --version
python -m pip install pytest ruff mypy
$env:PYTHONPATH = "src"
python -m pytest
python -m ruff check .
python -m mypy src
```

Python 3.11 or newer is currently required. Before packaging work item 0082, Faber's
base runtime has no package dependencies. The canonical repository check remains:

```bash
nix develop --command just check
```

Run the closest local equivalents and state exactly what was unavailable when Nix is
not installed.

Local `.faber/` artifacts are disposable and are not transferred by Git. Existing
pre-competition demos can still be recreated, but they are not the Build Week product:

```powershell
$env:PYTHONPATH = "src"
python -m faber.cli demo-funded-trajectory --out-dir .faber/funded-demo
```

## Pre-competition foundation

The repository already contains a tested local foundation for verifier-first work and
RL-grade trajectory collection:

- Work items 0030-0045 implement trace acquisition, attempt manifests, solver and
  environment metadata, work budgets, funding adapter stubs, and Hermes planning.
- Issue 0046 makes trajectory quality explicit and supports RL-grade validation, task
  requirements, evidence levels, process and replay evidence, reward signals, training
  eligibility, consent, and filtered dataset export.
- Work items 0047-0075 add data rights, trace privacy, validation and ingestion, generic
  source adapters, budget and competition policy, human and probabilistic verification,
  tournaments, learning datasets, scorecards, the Hermes pilot package, optional
  reproducibility verifiers, cross-platform fixtures, a complete fake funded loop, risk
  gates, retention, runtime and product boundaries, schema compatibility, golden
  fixtures, performance smoke coverage, customer-facing CLI output, and roadmap
  synthesis.
- `lk251/agent-bounty-market` and `lk251/llm-as-a-verifier` remain read-only research
  references. Their vendor or demo architecture is not part of Faber's core.

This foundation predates Build Week and must not be presented as new competition work.
The Build Week delta and README must distinguish it from the Faber Proof extension.

## Last recorded validation baseline

The completed work item 0076 baseline on HB3 uses Python 3.12.2, pytest 9.0.2,
Ruff 0.15.10, and mypy 2.1.0:

- focused Build Week delta tests: 8 passed in 4.02 seconds
- `python -m pytest`: 317 passed in 11.11 seconds
- `python -m ruff check .`: passed
- `python -m mypy src`: passed across 75 source files
- `nix develop --command just check`: unavailable because Nix and `just` are not
  installed on HB3

The local delta smoke resolved the baseline and branch target, reported all 28 eligible
pre-0076 commits and 25 changed files, and emitted only the expected dirty-tree warning
before the focused commit. The Python tools are installed in the Windows user site;
Codex had to run outside its workspace sandbox to read them, while an ordinary HB3
shell can use them normally.

## Current code map

- `src/faber/schemas.py`, `contracts.py`, `trajectories.py`, and
  `trajectory_quality.py`: protocol records and trajectory quality decisions.
- `src/faber/traces.py`, `trace_ingestion.py`, `redaction.py`, and `data_rights.py`:
  process evidence, ingestion, privacy, consent, retention, and training-use controls.
- `src/faber/verifiers.py`, `reviews.py`, `calibration.py`, and `probabilistic.py`: hard
  authority, human review, calibration, and advisory scoring.
- `src/faber/budgets.py`, `budget_ledger.py`, `market_policies.py`, and
  `tournaments.py`: provider-neutral budgets, reservations, settlement policy, and
  candidate selection.
- `src/faber/adapters/`: GitHub, Hermes, local, and trace boundaries. Provider-specific
  Build Week integration belongs here rather than in core.
- `src/faber/adapters/github/funded_product_loop.py` and `src/faber/funded_demo.py`: the
  pre-existing local fake funded flow.
- `src/faber/cli.py`: inspectable local workflows and validation commands.
- `tests/fixtures/golden/`: canonical cross-platform and trajectory snapshots.

## Recommended next action

Continue with work item 0077 through the director skill:

```text
Use $build-week-director and continue until the next human-only gate.
```

Fallback when the skill has not yet been discovered:

```text
Read codex/BUILD_WEEK_START_HERE.md and execute the next incomplete Build Week work item.
```

Work item 0076 established the branch, annotated eligibility tag, deterministic local
delta report, competition boundary, and HB3 validation baseline. Work item 0077 is the
next P0 item and must add the proof protocol records and deterministic fail-closed
decision policy without introducing provider-specific behavior into the core.

## Invariants to preserve

- Verification is authoritative before settlement; payment state cannot rewrite a
  receipt.
- GitHub, payment providers, model providers, and hosted services remain adapters.
- Candidate-owned CI is evidence, not verifier authority.
- GPT-5.6 planning is advisory; only approved proof capabilities and verifier policy can
  create authoritative evidence.
- Model output, repository content, task text, diffs, and replay bundles cannot define
  operational behavior.
- Missing, invalid, contradictory, or unbound evidence cannot produce `PASS`.
- PR-only work may be useful customer work but is low-evidence and not RL-grade by
  default.
- Training permission is separate from work acceptance and payout.
- Money uses integer minor units; state transitions and serialization remain explicit,
  deterministic, digest-stable, and idempotent.
- No private prompts, hidden reasoning, provider credentials, model weights, or
  proprietary harness internals are required for evidence.
- Do not make Nix mandatory for every task or introduce Windows-only core behavior.
- Preserve a no-key, no-network replay path.
- Do not claim production sandboxing from the local runner.

## Post-submission roadmap

After the final audited submission tag and competition freeze, restore the normal
strategic sequence from `docs/ROADMAP.md`: the human-approved, unpaid external pilot,
followed by durable GitHub delivery, stronger runner isolation, verifier approval and
revocation, and dataset review controls.

The selected Hermes issue must be checked again for freshness and maintainer permission
before any external work. A prepared package is not permission to execute or publish.

## Before the next machine switch

1. Re-run the available checks and record exact results when they materially change.
2. Update the active work item, commit, demo scorecard, human gates, recommended next
   action, and known blockers in `codex/build-week/STATUS.md`.
3. Update this handoff when the validation baseline or recommended next action changes.
4. Ensure `git status -sb` is understood and no local `.faber/` artifact is needed as
   source material.
5. Commit clearly and push the intended branch with the repository-specific SSH
   identity.
6. Verify the remote commit from a fresh fetch before leaving the machine.
7. Remind Javier to run `/feedback` before the primary implementation thread ends.
