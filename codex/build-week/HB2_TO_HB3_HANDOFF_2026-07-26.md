# HB2 to HB3 Faber handoff - 2026-07-26

This is the dated transfer packet for continuing Faber on HB3. It captures the
repository, Git, validation, Build Week, credential, and queued-work state that existed
on HB2 immediately before maintenance. It contains no private key, API key, or
machine-local artifact.

Read in this order on HB3:

1. `AGENTS.md`
2. `docs/CODEX_SESSION_HANDOFF.md`
3. this file
4. `codex/build-week/STATUS.md`
5. `codex/build-week/OFFLINE_CONTINUATION.md`
6. `codex/future/0083-submission-and-final-audit.md`

When the repository skill is available, the intended resume instruction is:

```text
Use $build-week-director and continue Issue #7 from work item 0083-M. Preserve the
recorded workflow authorization blocker and complete every independent machine gate.
```

## Transfer snapshot

The following was verified on HB2 after `git fetch --prune --tags origin`:

- Repository: `lk251/faber`
- Remote: `git@github.com:lk251/faber.git`
- Active branch: `build-week/faber-proof`
- Source checkpoint: `c61ac4607b5f9b1c3f4fb6088ee37209365ccebf`
  (`Complete work item 0082 evals packaging and release checks`)
- Branch state at the source checkpoint: clean and even with
  `origin/build-week/faber-proof` (`0 0`)
- Remote branch heads:
  - `build-week/faber-proof` at `c61ac4607b5f9b1c3f4fb6088ee37209365ccebf`
  - `master` at `c915523383dc58114bf748f7d7a64c1c398faaba`
- `master` is the canonical long-lived branch. Remote `main` is absent and was
  intentionally deleted.
- Eligibility baseline tag: annotated `build-week-2026-baseline`
- Baseline target:
  `64f775cfe2f622837bd9aaa40f6369aa22af1d80`
  (`Implement work item 0075 roadmap synthesis`, 2026-07-09T21:45:20Z)
- Measured baseline-to-checkpoint delta: 43 commits, 152 changed files, 32,721
  additions, and 450 deletions. Generate current values with:

  ```powershell
  python scripts/build_week_delta.py --json
  ```

The commit containing this handoff file will be newer than the source checkpoint.
Treat `c61ac46` as the completed product checkpoint and inspect the fetched branch head
for the transfer-document commit.

## Active objective

GitHub Issue
[#7](https://github.com/lk251/faber/issues/7), "0082-0083-M: Execute the autonomous
offline Faber Proof completion campaign," was open when this packet was written.

Work item 0082 is locally machine-complete at `c61ac46`:

- product-specific threat model;
- 49/49 deterministic adversarial cases with zero unjustified passes;
- privacy and secret audit;
- wheel and sdist packaging;
- isolated base and optional-extra installation;
- installed no-key bad/repaired demo;
- deterministic report regeneration;
- guarded, atomic live-capture preparation tested with fake clients;
- performance and bundle-size evidence;
- full local test, format, lint, and type checks.

The only remaining 0082 gate is remote workflow activation and observation. It does not
block independent 0083 machine work.

Work item 0083-M has not been implemented. It is the next product change. Complete:

- the judge-facing top-level README, beginning with `Faber Proof` and
  `Codex can write the patch. Faber makes the patch prove itself.`;
- `docs/JUDGE_QUICKSTART.md`;
- copy-ready `docs/DEVPOST_SUBMISSION.md`;
- `docs/DEMO_SCRIPT.md`, mechanically constrained to a 2:35-2:50 narration budget;
- `docs/DEMO_SHOT_LIST.md`;
- `docs/DEMO_RECORDING_CHECKLIST.md`;
- `docs/SUBMISSION_IMAGES.md` and deterministic original source assets;
- a deterministic narration checker;
- a deterministic final-submission audit tool with JSON and Markdown reports;
- the exact pre-existing versus Build Week delta;
- factual technical decisions, security limits, business path, and adoption path;
- an explicit human-gate state file or equivalent structured input;
- tests and full local validation.

The final audit must distinguish `machine_pass` from unresolved human gates. Do not
make a live provider call, relabel `fake-development` fixtures, share repository access,
upload a video, submit Devpost, contact maintainers, or create the final submission tag
as part of 0083-M.

## Deadline status

The official Build Week submission period ended on 2026-07-21 at 17:00 Pacific. This
handoff was prepared on 2026-07-26, after that deadline.

The HB3 session must not claim that a new or modified submission can still be entered.
Before any submission action, a human must establish one of these facts:

1. a timely Devpost submission already exists and the intended action is permitted; or
2. the organizers explicitly authorized a post-deadline modification.

The machine-completable documentation and audit work remains useful and should continue,
but deadline eligibility is an unresolved human gate.

## SSH identity on HB3

Use only a machine-local, repository-specific, non-FIDO Ed25519 key for every Faber
clone, fetch, pull, and push. Do not copy the HB2 private key into Git or another
repository. GitHub already had a deploy-key entry named
`HB3 Faber deploy key 2026-07-16`; verify that the HB3 public-key fingerprint matches it
rather than assuming the local file is correct.

For the expected HB3 key path:

```powershell
$key = "$env:USERPROFILE/.ssh/faber_github_deploy_ed25519"
$ssh = 'C:/Windows/System32/OpenSSH/ssh.exe -i "' + $key + '" -o IdentitiesOnly=yes -o AddKeysToAgent=no'
Test-Path $key
ssh-keygen -lf "$key.pub"
$env:GIT_SSH_COMMAND = $ssh
git clone --branch build-week/faber-proof git@github.com:lk251/faber.git
Set-Location faber
git config core.sshCommand $ssh
git config --local --get core.sshCommand
git fetch --prune --tags origin
git status -sb
git rev-list --left-right --count origin/build-week/faber-proof...HEAD
```

If the key is absent, create a new Ed25519 key on HB3 and add only its public key as a
write-enabled deploy key for `lk251/faber`. Keep the private key machine-local:

```powershell
ssh-keygen -t ed25519 -f $key -C "HB3 Faber repository key"
Get-Content "$key.pub"
```

Constrain Git with the same `core.sshCommand` after registration. Never fall back to a
FIDO-backed identity for this repository.

The HB2 repository used:

```text
C:/Windows/System32/OpenSSH/ssh.exe -i C:/Users/javie/.ssh/faber_github_deploy_ed25519 -o IdentitiesOnly=yes -o AddKeysToAgent=no
```

An additional HB2 workflow key was generated during diagnosis but was never registered.
It is not a usable repository credential and does not transfer.

## Workflow activation blocker

The intended Linux and Windows workflow is preserved verbatim at:

```text
codex/build-week/drafts/ci.yml
```

HB2 could authenticate and push ordinary files with its non-FIDO deploy key. GitHub
rejected a commit containing `.github/workflows/ci.yml` with:

```text
refusing to allow an OAuth App to create or update workflow
.github/workflows/ci.yml without workflow scope
```

The active `gh` token had `repo` but not `workflow` scope. Browser-based remediation was
not performed because the HB2 in-app browser was not signed in. On HB3, use a
human-authorized GitHub action that is allowed to register or use a non-FIDO SSH
credential for workflow updates. Then:

1. promote the exact draft to `.github/workflows/ci.yml`;
2. update documentation references that describe it as a draft;
3. commit and push with the repository-specific non-FIDO key;
4. observe both Linux and Windows jobs;
5. fix real platform failures and record exact results.

Do not weaken the workflow and do not use the FIDO identity as a shortcut.

## Validation baseline

The completed HB2 0082 run used Python 3.11.15, pytest 9.0.2, Ruff 0.15.10, mypy
2.1.0, and build 1.5.0:

- `python -m pytest -q`: 699 passed, 1 guarded live skip in 117.88 seconds;
- `python -m ruff format --check .`: 189 files already formatted;
- `python -m ruff check .`: passed;
- `python -m mypy src`: passed across 93 source files;
- adversarial campaign: 49/49 passed twice, zero unjustified passes;
- campaign digest:
  `sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`;
- clean wheel/sdist and isolated install audit: passed;
- wheel: 333,474 bytes; sdist: 388,290 bytes;
- installed demo: ordinary `PASS`/`PASS`, Faber Proof `BLOCK`/`PASS`;
- installed demo package: 51 files, 232,257 bytes, zero privacy findings;
- measured demo: 6.258291 seconds, 232,259 output bytes;
- direct committed/generated artifact audit: 58 files, 274,922 bytes, zero findings;
- deterministic report regeneration: four byte-identical reports;
- fake guarded-live success, rollback, and no-callback preflight tests: passed;
- no real provider call was made.

The committed replay fixtures remain `fake-development`. The exact commands and
residual risks are in `codex/build-week/0082_HB2_HANDOFF.md`. The ignored
`.faber/dev-venv` and generated `.faber/` output do not transfer through Git. Recreate a
local environment on HB3. Nix and `just` were unavailable on HB2; Windows work should
continue with the recorded local equivalents unless the environment changes.

## Demo facts

Bad candidate:

- ordinary tests: `PASS`;
- Faber Proof: `BLOCK`;
- required obligations: 3;
- passed/failed/missing: 2/1/0;
- one concrete budget-boundary counterexample;
- plan digest:
  `sha256:08caa61675de72c35f59624c5ed575b08d2c5d8af72f16b3e6b29999cd1b02a1`;
- decision digest:
  `sha256:c85766c5065fa521ca820f431da857072bc765177248ce50af9fe2805b1cbed5`.

Repaired candidate:

- ordinary tests: `PASS`;
- Faber Proof: `PASS`;
- required obligations: 3;
- passed/failed/missing: 3/0/0;
- plan digest:
  `sha256:25784e467a27a52bc4fae73f5edd1d7fdca35658952f12825dc472c2f2db2b0b`;
- decision digest:
  `sha256:4b3e9b17c89093e8d806b30e02c71324fac2d58301316dda76f6b74bc44082b8`.

## Audit and human gates

- A1 architecture and authority is green. `A1-P0-001` is independently verified.
- No open P0/P1 audit finding was recorded at transfer.
- A2 adversarial security is eligible now.
- A3 clean installation and A4 judge comprehension are eligible after 0082.
- A5 final compliance becomes eligible after 0083-M.
- Audit eligibility does not pause the primary machine lane. A recorded P0 finding does.

The primary `/feedback` session ID is already recorded:

```text
019f6d53-0a3d-71d3-abd7-749dc4a3784c
```

Do not request it again. Remaining human or live gates are:

1. establish post-deadline submission status or organizer authorization;
2. supply `OPENAI_API_KEY` locally and run the guarded live bad/repaired capture;
3. review, sanitize, and accept the staged bundles as `live-reviewed`;
4. run the independent audit wave and any live-provenance addendum;
5. grant and verify judge repository access;
6. record a human narration and upload a public sub-three-minute YouTube video;
7. complete or amend Devpost only if deadline status permits;
8. create the immutable final tag only after every machine, audit, and permitted human
   gate is complete.

The prepared one-command live gate is:

```powershell
python examples/build-week-proof/scripts/capture_live_reviewed_demo.py --reviewer "Javier"
```

Follow `docs/LIVE_GPT56_CAPTURE_RUNBOOK.md`; do not run it without the human-supplied
key and review.

## Earlier queued work

Do not reconstruct or reimplement these goals from old chat history:

- Initial Faber core Issue #1, the GitHub adapter Issue #2, and queue Issue #3 are
  closed on GitHub.
- `main` was replaced by `master` and removed from the remote.
- The `llm-as-a-verifier` research addition is in
  `docs/research/llm-as-a-verifier-2607-05391.md`,
  `docs/ADR-0002-probabilistic-verification-scaling.md`, and the future queue. Relevant
  commits include `45969a9` and `423b789`.
- The trace acquisition, solver metadata, evidence ladder, and harness-pilot research
  track is in `docs/TRACE_STRATEGY.md`, `docs/SOLVER_METADATA.md`,
  `docs/ADR-0003-traces-and-solver-metadata.md`, and work items 0023-0029. Relevant
  roadmap commit: `4fb1045`.
- RL-grade trajectory-by-default Issue #5 is implemented in code at `bd1cd89`, with
  `src/faber/trajectory_quality.py` and
  `tests/test_rl_grade_trajectory_quality.py`.
- The repository contains implementation history through work item 0075. GitHub Issues
  #4, #5, and #6 were still open as bookkeeping at transfer even though their
  corresponding implementation exists. Reconcile acceptance and issue state before
  doing duplicate work or closing them.
- `lk251/agent-bounty-market` and `lk251/llm-as-a-verifier` are read-only references,
  not dependencies or core architecture.

The ordinary post-Build-Week roadmap remains paused while the Faber Proof freeze and
submission status are unresolved. Do not begin the Hermes external pilot, contact an
upstream maintainer, publish a contribution, use production credentials, move money, or
collect private data without explicit human approval and a fresh target check.

## First HB3 verification

Before editing:

```powershell
git status -sb
git branch --show-current
git log -3 --oneline --decorate
git remote -v
git config --local --get core.sshCommand
git fetch --prune --tags origin
git rev-list --left-right --count origin/build-week/faber-proof...HEAD
git rev-list -n 1 build-week-2026-baseline
```

Expected values are a clean `build-week/faber-proof`, no local/remote divergence, a
repository-specific non-FIDO SSH command, and baseline target `64f775c`.

Then continue 0083-M. Preserve provider neutrality, fail-closed authority, stable
digests, no-key replay, honest `fake-development` provenance, integer money, and the
separation between machine completion and human submission completion.
