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
Read AGENTS.md and docs/CODEX_SESSION_HANDOFF.md, verify source commit f2518bd is in
the fetched build-week/faber-proof branch, verify CI repair commit b622d7b is present,
then use $build-week-auditor for A2. Do not invent human-gate evidence.
```

## Transfer snapshot

The final HB2 source and machine-evidence snapshot is:

- Repository: `lk251/faber`
- Remote: `git@github.com:lk251/faber.git`
- Active branch: `build-week/faber-proof`
- 0083 source checkpoint: `f2518bd96ebc90f3d6fc7ba6097f1ffb1d6595da`
  (`Implement work item 0083 submission package`)
- The transfer/evidence commit follows that source checkpoint and contains the
  generated reports plus the updated resume state.
- `master` is the canonical long-lived branch. Remote `main` is absent and was
  intentionally deleted.
- Eligibility baseline tag: annotated `build-week-2026-baseline`
- Baseline target:
  `64f775cfe2f622837bd9aaa40f6369aa22af1d80`
  (`Implement work item 0075 roadmap synthesis`, 2026-07-09T21:45:20Z)
- Warning-free baseline-to-source delta: 45 commits, 166 changed files, 35,949
  additions, 528 deletions, and zero binary files. The exact report is committed at:

  ```text
  docs/generated/BUILD_WEEK_DELTA.json
  docs/generated/BUILD_WEEK_DELTA.md
  ```

After cloning, run `git fetch --prune --tags`, check out
`build-week/faber-proof`, and verify `git merge-base --is-ancestor f2518bd HEAD`.
The push verification recorded at the end of this packet is authoritative for the
final remote head.

## Active objective

GitHub Issue
[#7](https://github.com/lk251/faber/issues/7), "0082-0083-M: Execute the autonomous
offline Faber Proof completion campaign," is machine-complete through 0083-M at
`f2518bd`. Do not redo it by default.

0083 now contains:

- the judge-facing README and five-command no-key path;
- `docs/JUDGE_QUICKSTART.md` and copy-ready `docs/DEVPOST_SUBMISSION.md`;
- a 391-word script, shot list, recording checklist, and deterministic narration
  checker;
- original 1600x900 comparison and trust-boundary SVG assets plus an image plan;
- explicit, validated human-gate state;
- a deterministic final audit with JSON and Markdown outputs;
- a warning-free exact Build Week delta;
- tests for narration bounds, final-audit failure modes, delta outputs, and CI content.

The final audit result is:

```text
MACHINE PASS; HUMAN INCOMPLETE; OVERALL HUMAN_INCOMPLETE
```

The 0082 workflow gate is resolved. The active workflow is
`.github/workflows/ci.yml`, synchronized with `codex/build-week/drafts/ci.yml`.
GitHub Actions run `30217997785` passed Ubuntu, Windows, and the optional OpenAI-extra
no-provider-call lane at `b622d7b`.

The next machine-actionable queue is independent A2, A3, A4, then the machine portion
of A5. Use fresh audit contexts; accepted P0 findings block the final tag. A5 must be
repeated or finalized after real human evidence and a candidate tag exist.

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
$sshExe = Join-Path $env:WINDIR "System32/OpenSSH/ssh.exe"
$ssh = '"' + $sshExe + '" -i "' + $key + '" -o IdentitiesOnly=yes -o AddKeysToAgent=no'
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

HB2 used the same constrained command shape with its machine-local
`$env:USERPROFILE/.ssh/faber_github_deploy_ed25519` key.

An additional HB2 workflow key was generated during diagnosis but was never registered.
It is not a usable repository credential and does not transfer.

## Workflow activation resolution

The active Linux and Windows workflow and its synchronized reference are:

```text
.github/workflows/ci.yml
codex/build-week/drafts/ci.yml
```

The first promotion attempt was rejected because the GitHub OAuth token lacked
`workflow` scope:

```text
refusing to allow an OAuth App to create or update workflow
.github/workflows/ci.yml without workflow scope
```

Javier granted workflow authorization. HB2 then promoted the workflow at `0ab9b7b`,
fixed cross-platform replay command identity at `6e7aebd`, and enabled full-history
checkout for the eligibility-baseline audit at `b622d7b`. Actions run `30217997785`
passed all three jobs. All pushes used the repository-specific non-FIDO key with
`IdentitiesOnly=yes` and `AddKeysToAgent=no`.

## Validation baseline

The completed HB2 0083 run at `f2518bd` used Python 3.11.15, pytest 9.0.2, Ruff
0.15.10, mypy 2.1.0, and build 1.5.0:

- `python -m pytest -q`: 710 passed, 1 guarded live skip in 105.99 seconds;
- focused submission/docs/audit/delta suite: 26 passed in 12.07 seconds;
- `python -m ruff format --check .`: 193 files already formatted;
- `python -m ruff check .`: passed;
- `python -m mypy src`: passed across 93 source files;
- adversarial campaign: 49/49 passed, zero unjustified passes;
- campaign digest:
  `sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`;
- full clean wheel/sdist and isolated install audit, including optional extra: passed;
- wheel: 336,891 bytes; sdist: 398,045 bytes;
- installed demo: ordinary `PASS`/`PASS`, Faber Proof `BLOCK`/`PASS`;
- installed demo package: 51 files, 232,261 bytes, zero privacy findings;
- measured demo: 12.207419 seconds, 232,258 output bytes;
- submission-artifact privacy audit: zero findings;
- deterministic report regeneration: four byte-identical reports;
- narration: 391 words, 156.4-167.6 seconds mechanically estimated;
- warning-free delta: 45 commits, 166 files, +35,949/-528;
- final aggregate audit: `MACHINE PASS; HUMAN INCOMPLETE`, JSON digest
  `sha256:df9a108bc1b5f39e5cc3c2178beb7b3d9d30bc73217c3c58522dda6362bdf050`;
- no real provider call was made.

Committed evidence:

```text
docs/generated/FINAL_SUBMISSION_AUDIT.json
docs/generated/FINAL_SUBMISSION_AUDIT.md
docs/generated/BUILD_WEEK_DELTA.json
docs/generated/BUILD_WEEK_DELTA.md
docs/generated/DEMO_NARRATION_ANALYSIS.json
```

Before the passing aggregate report, one eval child and one Windows temporary-venv
`ensurepip` bootstrap each failed once and then passed in standalone reproduction.
Those failed reports were discarded. The final aggregate sequence passed from the
clean source commit; this history is recorded so HB3 does not misdiagnose a repeat
Windows bootstrap transient as a deterministic Faber failure.

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
- A3 clean installation and A4 judge comprehension are eligible now.
- A5 can inspect the machine package now, but final-green status requires the later
  human-complete candidate and tag.
- Audit eligibility does not pause the primary machine lane. A recorded P0 finding does.

The primary `/feedback` session ID is already recorded:

```text
019f6d53-0a3d-71d3-abd7-749dc4a3784c
```

Do not request it again. Remaining human or live gates are:

1. establish post-deadline submission status or organizer authorization;
2. supply `OPENAI_API_KEY` locally and run the guarded live bad/repaired capture;
3. review, sanitize, and accept the staged bundles as `live-reviewed`;
4. grant and verify judge repository access;
5. record a human narration and upload a public sub-three-minute YouTube video;
6. complete or amend Devpost only if deadline status permits;
7. create the immutable final tag only after every machine, audit, and permitted human
   gate is complete.

The independent audit wave is machine-actionable on HB3 rather than a human
attestation. Run A2-A4 from fresh contexts now and add the live-provenance review to
the final audit evidence after capture.

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

Then verify `f2518bd` is an ancestor of `HEAD`, inspect the committed final-audit
report, and begin A2 in a fresh audit session. Preserve provider neutrality,
fail-closed authority, stable digests, no-key replay, honest `fake-development`
provenance, integer money, and the separation between machine completion and human
submission completion.

## Final HB2 push verification

HB2 pushed source commit `f2518bd` and evidence/handoff commit
`1ed77cbff09bf88921c868fe9e2bfd9d9b11ac9f` with the repository-specific
`faber_github_deploy_ed25519` identity, `IdentitiesOnly=yes`, and
`AddKeysToAgent=no`. A fresh authenticated fetch then showed:

```text
origin/build-week/faber-proof...HEAD = 0 0
HEAD = origin/build-week/faber-proof = 1ed77cbff09bf88921c868fe9e2bfd9d9b11ac9f
remote build-week/faber-proof = 1ed77cbff09bf88921c868fe9e2bfd9d9b11ac9f
remote master = c915523383dc58114bf748f7d7a64c1c398faaba
remote main = absent
```

The earlier `404` and missing `workflow` scope described above were resolved after
Javier refreshed GitHub authorization. The active workflow is present and Actions run
`30217997785` is green on Ubuntu, Windows, and the optional-extra lane.

The commit containing this section is a final documentation-only synchronization note
after `1ed77cb`. On HB3, trust the freshly fetched branch head and verify it is even with
origin rather than expecting this document to embed its own commit ID.
