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

The detailed HB2 0082 implementation checkpoint is:

```text
codex/build-week/0082_HB2_HANDOFF.md
```

The dated HB2-to-HB3 transfer packet is:

```text
codex/build-week/HB2_TO_HB3_HANDOFF_2026-07-26.md
```

When available, invoke:

```text
$build-week-director
```

A user instruction such as "continue Build Week," "continue Faber Proof," or "get to
work" in this project context means: execute the first eligible P0 machine slice,
commit it, update the status file, and continue. Defer unrelated human-only gates;
stop only when one blocks the selected work, a P0 failure prevents progress, or the
working tree is unsafe.

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
  or committer dates; the 0083 source snapshot has 45 baseline-to-target commits and
  166 changed files
- Last completed machine slice: 0083 submission package and final machine audit at
  source commit `f2518bd96ebc90f3d6fc7ba6097f1ffb1d6595da`
- Active implementation state: all machine-completable 0083 artifacts and checks are
  complete; the final audit is `machine_pass` and `human_incomplete`. The exact
  Linux/Windows workflow remains at `codex/build-week/drafts/ci.yml` pending a GitHub
  credential authorized to modify workflow files
- Last independent audit: A1 architecture/authority against `6d11e7a`, verdict
  `green`; `A1-P0-001` is independently verified
- Snapshot date: 2026-07-26
- Primary-session designation: this director thread is the primary Build Week
  implementation session; `/feedback` session ID
  `019f6d53-0a3d-71d3-abd7-749dc4a3784c` is recorded
- Current transfer target: the pushed `build-week/faber-proof` branch containing
  source commit `f2518bd` plus this handoff/evidence commit; the remote has only
  `master` and `build-week/faber-proof`, with no `main`

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
2. Select the first incomplete eligible P0 machine slice in
   `codex/build-week/STATUS.md`. Skip only deferred human slices that do not block the
   selected work.
3. Implement only that item.
4. Add tests before or alongside verification, proof, routing, evidence, and decision
   changes.
5. Run the item-specific acceptance commands and the full available checks.
6. Update the status file with exact results and the demo scorecard.
7. Update this handoff when the recommended next action or validation baseline changes.
8. Make one focused commit.
9. Continue through eligible machine work while the tree is clean. Audit eligibility
   and unrelated deferred human gates do not pause the implementation lane.

The primary implementation session ID is already recorded. Use fresh secondary sessions
for architecture, security, installation, judge, and final submission audits rather
than parallel redesigns of the core protocol.

## Human-only gates

Codex must complete deterministic local work without waiting. These actions remain
human-only, but they block only work that actually depends on them:

- confirming a timely Devpost submission exists or obtaining organizer authorization
  for a post-deadline modification;
- supplying an OpenAI API key for a guarded live run;
- requesting or redeeming competition credits;
- sharing the private repository with the official judging addresses;
- recording spoken narration and uploading a public YouTube video;
- completing and submitting the Devpost form;
- approving any external publication, third-party contribution, payment, production
  credential use, or private-data collection.

Do not mark one of these gates complete without the real value or explicit human
attestation. `/feedback` is already complete with session ID
`019f6d53-0a3d-71d3-abd7-749dc4a3784c`. The official submission deadline has passed,
so do not modify Devpost until the first gate above is established.

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

The work item 0083 source snapshot `f2518bd` was validated on HB2 with Python 3.11.15,
pytest 9.0.2, Ruff 0.15.10, mypy 2.1.0, and build 1.5.0:

- `python -m pytest -q`: 710 passed, 1 guarded live skip in 105.99 seconds
- focused submission/docs/audit/delta tests: 26 passed in 12.07 seconds
- Ruff lint passed; Ruff format passed across 193 files
- mypy passed across 93 source files
- adversarial campaign passed 49/49 cases with zero unjustified passes
- deterministic report regeneration produced 4 byte-stable reports
- full clean-install audit passed outside the checkout, including the optional
  `live-openai` extra without a provider call; wheel 336891 bytes, sdist 398045 bytes,
  51 demo files, 232261 bytes, and zero privacy findings
- direct replay produced ordinary `PASS`/`PASS` and Faber Proof `BLOCK`/`PASS`, with
  `fake-development` provenance stated throughout
- latest performance measurement completed in 12.207419 seconds with 232258 output
  bytes and zero privacy findings
- narration check passed at 391 words, mechanically estimated at 156.4-167.6 seconds;
  a human timed rehearsal remains required
- final aggregate audit passed every runnable machine check in one sequence and
  reported `MACHINE PASS; HUMAN INCOMPLETE`; its machine-snapshot JSON digest is
  `sha256:df9a108bc1b5f39e5cc3c2178beb7b3d9d30bc73217c3c58522dda6362bdf050`
- Build Week delta is warning-free at 45 commits and 166 changed files against
  baseline `64f775c`
- Nix and `just` were unavailable on HB2

The durable machine evidence is:

```text
docs/generated/FINAL_SUBMISSION_AUDIT.json
docs/generated/FINAL_SUBMISSION_AUDIT.md
docs/generated/BUILD_WEEK_DELTA.json
docs/generated/BUILD_WEEK_DELTA.md
docs/generated/DEMO_NARRATION_ANALYSIS.json
```

Two aggregate attempts before the passing report encountered non-reproducible Windows
infrastructure failures: one eval child exited once and then passed identically; one
temporary `venv` `ensurepip` bootstrap failed once and the complete standalone
clean-install audit then passed. Neither failed report is committed. The final
aggregate report passed from a clean source commit. HB2's ignored
`.faber/dev-venv` environment and disposable run outputs do not transfer through Git.

## Current code map

- `src/faber/schemas.py`, `contracts.py`, `trajectories.py`, and
  `trajectory_quality.py`: protocol records and trajectory quality decisions.
- `src/faber/traces.py`, `trace_ingestion.py`, `redaction.py`, and `data_rights.py`:
  process evidence, ingestion, privacy, consent, retention, and training-use controls.
- `src/faber/verifiers.py`, `reviews.py`, `calibration.py`, and `probabilistic.py`: hard
  authority, human review, calibration, and advisory scoring.
- `src/faber/proofs.py`: provider-neutral proof records, bounded advisory plan
  validation, receipted proof-authority binding, and deterministic fail-closed policy.
- `src/faber/proof_planning.py` and `src/faber/adapters/openai/`: provider-neutral
  planning records plus the guarded GPT-5.6 live and externally pinned replay paths.
- `src/faber/proof_catalog.py`: immutable typed catalog entries, closed parameter
  schemas, owner-only operational views, and stable capability/source commitments.
- `src/faber/proof_executors.py` and `src/faber/proof_runtime_helper.py`: five bounded
  proof families, fixed child-process paths, pinned source loading, bounded capture,
  exact JSON assertions, redacted counterexamples, and honest isolation limits.
- `src/faber/proof_workflow.py`: preflight-all stable execution, workspace binding,
  evidence and receipt creation, raw-authority reuse prevention, and aggregate result.
- `src/faber/proof_context.py`, `proof_configuration.py`, `proof_product.py`, and
  `proof_reports.py`: bounded local Git collection, owner-approved configuration,
  end-to-end orchestration, portable artifact validation, and self-contained reports.
- `src/faber/proof_demo.py` and `examples/build-week-proof/`: deterministic original
  bad/repaired scheduler revisions, context-bound replay review, one-command comparison,
  live capture/install gate, and judge-facing documentation.
- `src/faber/proof_evals.py`, `src/faber/proof_privacy.py`, and `scripts/`: the active
  0082 adversarial campaign, release privacy audit, clean-install audit, deterministic
  report regeneration, performance evidence, 0083 narration check, Build Week delta,
  and final submission audit.
- `docs/JUDGE_QUICKSTART.md`, `docs/DEVPOST_SUBMISSION.md`, `docs/DEMO_*`,
  `docs/SUBMISSION_IMAGES.md`, and `docs/submission-assets/`: the complete 0083
  judge, recording, submission, and original-image package.
- `.agents/skills/faber-proof/`: repository-scoped proof, evidence-driven repair, and
  stale-replay safety workflow with deterministic validation.
- `src/faber/budgets.py`, `budget_ledger.py`, `market_policies.py`, and
  `tournaments.py`: provider-neutral budgets, reservations, settlement policy, and
  candidate selection.
- `src/faber/adapters/`: GitHub, Hermes, local, and trace boundaries. Provider-specific
  Build Week integration belongs here rather than in core.
- `src/faber/adapters/github/funded_product_loop.py` and `src/faber/funded_demo.py`: the
  pre-existing local fake funded flow.
- `src/faber/cli.py`: inspectable local workflows plus the `faber proof` product CLI.
- `tests/fixtures/golden/`: canonical cross-platform and trajectory snapshots.

## Recommended next action

On HB3, first read:

```text
AGENTS.md
docs/CODEX_SESSION_HANDOFF.md
codex/build-week/STATUS.md
codex/build-week/HB2_TO_HB3_HANDOFF_2026-07-26.md
docs/generated/FINAL_SUBMISSION_AUDIT.md
```

Do not redo 0083 merely because `.faber/` outputs are absent; those are intentionally
ignored. Confirm the branch contains source commit `f2518bd`, install a local
development environment, and run a focused smoke check. If source or submission
artifacts change, rerun the complete final audit before relying on its report.

The next machine-actionable work is independent review:

1. Run A2 adversarial security from a fresh audit session.
2. Run A3 clean-room installation from a separate fresh context.
3. Run A4 judge comprehension without relying on implementation-session memory.
4. Run the machine portion of A5, then repeat/finalize A5 after human evidence and the
   candidate tag exist.
5. Resolve every accepted P0 finding before final tagging.

Use `$build-week-auditor` and the queue in
`codex/build-week/AUDIT_QUEUE.md`. Existing A1 evidence is:

```text
codex/build-week/audits/A1-architecture-and-authority-report.md
```

Remote CI remains a precise external authorization gate. Promote
`codex/build-week/drafts/ci.yml` to `.github/workflows/ci.yml` only with a non-FIDO
credential authorized for workflow updates, then observe and repair both Linux and
Windows jobs. HB2's repository deploy key works for normal Git traffic, but GitHub
rejected workflow-path changes because the OAuth app that registered it lacks
`workflow` scope.

The ordered human/final sequence is:

1. Establish that a timely Devpost submission exists or obtain organizer authorization
   for a post-deadline modification.
2. Run the guarded live capture in `docs/LIVE_GPT56_CAPTURE_RUNBOOK.md`, review it, and
   obtain the required provenance audit addendum.
3. Share and independently verify repository access for both judging addresses.
4. Perform a timed narration rehearsal, record the under-three-minute video, upload it
   publicly, and verify it while signed out.
5. Update `codex/build-week/submission-human-gates.json` only with real evidence.
6. Run the full final audit, complete A5, create
   `build-week-2026-submission`, rerun the audit against the tag, and record the digest.
7. Update or submit Devpost only when step 1 permits it, and bind the record to the
   audited tag.

The no-key demo is complete and green, but committed replay fixtures remain honestly
`fake-development`. Do not claim `live-reviewed` provenance, green remote CI,
independent audit completion, submission eligibility, or final submission until each
has real evidence.

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
7. Preserve the recorded primary `/feedback` session ID in the Build Week status.
