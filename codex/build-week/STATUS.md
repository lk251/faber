# Faber Proof Build Week status

This file is the machine-resume state for the Build Week implementation queue. Update it
after every focused work-item or accepted-finding commit.

Independent reset sessions use `codex/build-week/AUDIT_QUEUE.md` and write durable audit
reports under `codex/build-week/audits/`.

## Current state

- Phase: offline P0 machine lane; 0082 implementation and all available local release
  checks are complete, remote CI activation is externally blocked, and 0083-M is
  current
- Canonical implementation branch: `build-week/faber-proof`
- Branch starting commit: `c915523383dc58114bf748f7d7a64c1c398faaba`
- Eligibility baseline: `64f775cfe2f622837bd9aaa40f6369aa22af1d80`, tagged by
  annotated `build-week-2026-baseline`
- Eligible commit count: 28 at branch start; 40 before the offline control-plane
  commit, which makes the total 41
- Current P0 item: `0083-M`; 0081 live-reviewed provenance and 0082 remote CI remain
  open external gates but do not block machine-completable submission work
- Current demo state: the original no-key command produces ordinary `PASS`/`PASS` and
  Faber Proof `BLOCK`/`PASS`; replay provenance is explicitly `fake-development`
- Primary implementation session: this director thread (0076 onward)
- Primary `/feedback` session ID: `019f6d53-0a3d-71d3-abd7-749dc4a3784c`
- Final submission tag: **not yet created**
- Deferred human-only gate: guarded bad/repaired live capture and review. It blocks
  live-dependent claims, final tagging, and submission completion, not 0082 or 0083
  machine work
- Open or unverified audit P0 findings: none
- Next eligible independent audit: A2 now for the current security implementation; a
  provenance addendum remains required after live-reviewed bundles exist

## P0 queue

- [x] `0076` — Build Week control plane, eligibility baseline, and repository handoff
- [x] `0077` — Proof protocol records and deterministic decision policy
- [x] `0078` — GPT-5.6 proof-planner adapter with live and replay modes
- [x] `0079` — Bounded proof-template catalog and safe proof executors
- [x] `A1-P0-001` — Require complete catalog/plan/selection authority binding for
  every selected proof outcome; independently verified
- [x] `0080` — End-to-end `faber proof` CLI and evidence report
- [ ] `0081` — Repository-scoped Codex skill and original winning demonstration
  - [x] Machine implementation and deterministic no-key demo
  - [ ] Guarded live capture and `live-reviewed` replay provenance
- [ ] `0082` — Adversarial evals, packaging, clean-install path, and CI
  - [x] Threat model, 49-case eval campaign, privacy audit, packaging, clean install,
    judge paths, live-capture transaction, formatting, and full local checks
  - [x] Least-privilege Linux/Windows workflow prepared and validated at
    `codex/build-week/drafts/ci.yml`
  - [ ] Promote the workflow with a non-FIDO credential authorized for workflow
    updates, observe both remote jobs, and repair any failure
- [ ] `0083` — Submission materials, video package, final audit, and freeze
  - machine-completable work is current after the locally green 0082 implementation
  - live capture, repository sharing, video upload, Devpost entry, and final tag remain
    human/final gates

## P1 queue

- [ ] `0084` — Optional Faber Proof Arena candidate comparison

Do not begin P1 until every P0 gate is green and the final submission package can be
produced from a clean clone.

## Independent audit lane

The complete audit state and finding ledger live in
`codex/build-week/AUDIT_QUEUE.md`.

- [x] `A1` — Architecture and authority `green` against `6d11e7a`; `A1-P0-001`
  independently verified
- [ ] `A2` — Adversarial security, eligible against the current machine-complete
  implementation; final live provenance needs a later addendum
- [ ] `A3` — Clean-room installation, eligible after 0082
- [ ] `A4` — Judge comprehension, eligible after 0082 and generated reports
- [ ] `A5` — Final compliance, eligible after 0083 machine work

Fresh reset instruction:

```text
Use $build-week-auditor and run the next eligible independent audit.
```

Open audit P0 findings take priority over new feature work. Final tagging is blocked
until all required audits are green and no P0 finding remains open.

## Global acceptance gates

### Competition eligibility

- [x] Baseline commit before the submission period identified
- [x] Annotated `build-week-2026-baseline` tag created
- [x] Pre-existing versus Build Week work documented
- [x] Eligible commit history preserved
- [x] Primary Codex session covers the majority of core Build Week functionality
- [x] `/feedback` session ID recorded - `019f6d53-0a3d-71d3-abd7-749dc4a3784c`

### Core product

- [ ] Direct `gpt-5.6` structured-output adapter works in a guarded live smoke test
- [x] Replay mode needs no key, account, or network
- [x] Live and replay responses use the same parser and validator
- [x] Model output can never define executable commands or source
- [x] Unknown templates and malformed parameters fail closed
- [x] Mandatory proof obligations cannot be removed by the model
- [x] Deterministic `PASS`, `BLOCK`, and `HUMAN_REVIEW` policy exists
- [x] Proof plans, evidence, receipts, and decisions have stable digests

### Winning demonstration

- [x] Original demo contains no third-party dependency, trademark, or account
- [x] Bad patch ordinary tests pass
- [x] Bad patch Faber Proof returns `BLOCK`
- [x] Bad report shows a failed claim and concrete counterexample above the fold
- [x] Fixed patch ordinary tests pass
- [x] Fixed patch Faber Proof returns `PASS`
- [x] Both reports are generated by one replay demo command
- [ ] Guarded live run reproduces the same material verdict

### Product design

- [x] `.agents/skills/faber-proof/SKILL.md` is detected by Codex
- [ ] One skill invocation can run proof, repair from evidence, and rerun
- [x] Self-contained HTML report opens from disk
- [ ] Report is understandable within five seconds
- [x] Clean judge path is no more than five documented commands
- [x] Supported platforms are explicit and tested or honestly qualified

### Reliability

- [x] Full pytest suite passes after work item 0082 local work - 699 passed and 1
  guarded live test skipped
- [x] Ruff format and lint pass
- [x] mypy passes
- [x] Nix check passes when Nix is available, or unavailability is documented
- [x] Wheel and sdist build; the wheel installs and runs outside the checkout on HB2
- [ ] Linux and Windows CI pass
- [x] Current deterministic adversarial campaign has 49/49 passing cases and zero
  unjustified `PASS` results
- [x] Replay digest tampering is detected
- [x] Secret-like data is redacted from requests and reports

### Independent audits

- [x] A1 architecture and authority is green
- [ ] A2 adversarial security is green
- [ ] A3 clean-room installation is green
- [ ] A4 judge comprehension is green
- [ ] A5 final compliance is green against the final tag
- [x] No audit P0 finding remains open
- [ ] Every accepted P1 affecting the three-minute experience is resolved or explicitly
  rejected with rationale

### Submission

- [ ] README contains Build Week boundary and Codex/GPT-5.6 collaboration details
- [ ] Devpost description drafted
- [ ] Technical and business decisions drafted
- [ ] Demo script is under 2:50 before recording
- [ ] Public narrated YouTube video is under three minutes
- [ ] Private repository shared with both judging addresses
- [ ] Judge access verified from a clean context
- [ ] Final tag created and tested from a clean clone
- [ ] Devpost submission completed before the deadline

## Work-item evidence ledger

| Item | Status | Commit | Tests and demos | Primary/secondary session | Notes |
|---|---|---|---|---|---|
| 0076 | Complete | `ab9edd6` | 8 focused tests; 317 full tests; Ruff; mypy 75 files; clean local delta | Primary | Baseline `64f775c`; annotated tag verified |
| 0077 | Complete | `5b714fe` | 138 focused tests; 455 full tests; Ruff; mypy 76 files | Primary | Six digest-stable records; fail-closed authority policy |
| 0078 | Complete | `2a2eaa2` | 86 focused tests; 541 full tests; Ruff; mypy 82 files; SDK 2.45.0 mock | Primary | Strict GPT-5.6 live adapter; externally pinned replay; adversarial review green; 0079 next |
| 0079 | Complete | `9314ddb` | 254 focused tests; 650 full tests, 1 guarded live skip; Ruff; focused format; mypy 86 files | Primary | Five bounded families; source/workspace/receipt authority binding; local isolation limits documented; A1 found `A1-P0-001` |
| A1-P0-001 | Verified | `6d11e7a` | 2 audit regressions; 16-case binding matrix; 342 focused tests, 1 skip; 652 full tests, 1 skip; isolated import; Ruff; format; mypy | Primary fix; secondary verification | Selected outcomes require a complete executor-tagged proof binding; A1 is green |
| 0080 | Complete | `c759ac4` | 11 focused product tests; 343 adjacent proof/planner/executor tests, 1 guarded live skip; 663 full tests, 1 skip; Ruff; format; mypy 90 files; editable console install and `faber doctor` | Primary | Local Git context, owner configuration, externally pinned replay, atomic portable bundle, Markdown/HTML report, exit codes, and console entrypoint |
| 0081 | Machine complete; live gate deferred | `d74b967` | 12 focused demo/skill tests; 675 full tests, 1 guarded live skip; Ruff; 14-file format; mypy 91 files; deterministic fixture regeneration; two skill validators; installed no-key console demo | Primary | Original stdlib demo and `$faber-proof`; fake-development replay is honest; human live capture/review remains required; primary session `019f6d53-0a3d-71d3-abd7-749dc4a3784c` recorded |
| 0082 | Local machine work complete; remote CI gate open | completion commit containing this update | 699 passed, 1 skip; Ruff format/lint; mypy 93 files; 49/49 evals; clean wheel/sdist/install; installed `BLOCK`/`PASS`; 0 privacy findings; 4 byte-stable reports | Primary machine lane; A2 may run independently | GitHub rejected `.github/workflows/ci.yml` because the OAuth app that registered the HB2 deploy key lacks `workflow` scope; exact workflow preserved as a draft |
| 0083 | Machine work current | - | - | Primary machine lane; A5 later | Human/final gates remain separate |
| 0084 | Blocked by P0 | - | - | Optional | - |

## Demo scorecard

Record exact values after each runnable milestone.

| Metric | Bad patch | Repaired patch |
|---|---:|---:|
| Ordinary test result | `PASS` | `PASS` |
| Faber Proof verdict | `BLOCK` | `PASS` |
| Required obligations | 3 | 3 |
| Passed obligations | 2 | 3 |
| Failed obligations | 1 | 0 |
| Missing obligations | 0 | 0 |
| Concrete counterexamples | 1 | 0 |
| Replay plan digest | `sha256:08caa61675de72c35f59624c5ed575b08d2c5d8af72f16b3e6b29999cd1b02a1` | `sha256:25784e467a27a52bc4fae73f5edd1d7fdca35658952f12825dc472c2f2db2b0b` |
| Decision digest | `sha256:c85766c5065fa521ca820f431da857072bc765177248ce50af9fe2805b1cbed5` | `sha256:4b3e9b17c89093e8d806b30e02c71324fac2d58301316dda76f6b74bc44082b8` |
| End-to-end runtime | 6.258291 seconds total for both candidates | 6.258291 seconds total for both candidates |
| Candidate bundle size | 120324 bytes | 108685 bytes |

## Validation baseline

HB2 work item 0082 local completion baseline:

- Python 3.11.15; pytest 9.0.2; Ruff 0.15.10; mypy 2.1.0; build 1.5.0
- adversarial campaign passed 49/49 cases twice with zero unjustified passes; suite
  digest
  `sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`
- `python -m pytest -q`: 699 passed, 1 guarded live skip in 117.88 seconds
- `python -m ruff check .`: passed
- `python -m ruff format --check .`: 189 files already formatted
- planner-focused suite: 88 passed, 1 guarded live skip
- product-focused suite: 14 passed; packaging suite: 4 passed
- deterministic report regeneration: 4 byte-stable reports
- clean wheel/sdist build and full clean-install audit, including optional live extra,
  passed outside the checkout; wheel 333474 bytes and sdist 388290 bytes
- installed demo: ordinary `PASS`/`PASS`, Faber Proof `BLOCK`/`PASS`, 51 files,
  232257 bytes, and zero privacy findings
- performance evidence: 6.258291 seconds, 232259 output bytes, zero privacy findings
- `python -m mypy src`: passed across 93 source files; focused Ruff checks passed
- guarded live fake success, rollback, and preflight tests passed; no provider call was
  made
- adversarial eval and deterministic report-regeneration `--check` commands passed
- development fixtures regenerate byte-identically with `fake-development` provenance
- direct privacy audit passed across 58 generated and committed files, 274922 bytes
- Nix and `just` were unavailable on HB2

See `codex/build-week/0082_HB2_HANDOFF.md` for commands, generated artifacts, known
residual risks, and the ordered completion checklist.

## Session handoff template

After each session, replace this section with current facts:

- Last completed item or finding: work item 0082 local machine work; remote CI remains
  an external credential gate
- Last implementation commit audited: `d74b967`, the focused 0081 machine-work commit;
  0082 is locally complete but has not yet received an independent audit
- Working tree state: expected clean after the focused 0082 completion commit is pushed
- Exact tests passed: full pytest 699 passed with 1 live skip; 49/49 adversarial cases;
  clean build/install/demo/privacy; four byte-stable reports; Ruff format and lint;
  mypy across 93 files; fake guarded-live transaction and rollback
- Exact tests unavailable or failed: Nix/`just` unavailable on HB2; GitHub rejected
  workflow-path updates
  from the dedicated deploy key because its registering OAuth app lacks `workflow`
  scope, so the exact YAML is preserved under `codex/build-week/drafts/`
- Bad-patch verdict: ordinary tests `PASS`; replay Faber Proof `BLOCK` with one exact
  last-turn counterexample
- Repaired-patch verdict: ordinary tests `PASS`; replay Faber Proof `PASS` with complete
  required coverage
- Open audit P0/P1 findings: none
- Next P0 action: execute all machine-completable 0083 submission work while preserving
  the exact 0082 workflow draft and external activation blocker
- Next eligible independent audit: A2 now; audit eligibility does not pause machine work
- Deferred human-only action: guarded live bad/repaired capture and review; do not ask
  for the key during the offline machine lane
- Should this session be submitted with `/feedback`: completed; primary session ID
  `019f6d53-0a3d-71d3-abd7-749dc4a3784c` is recorded
- Known risks: local executors do not provide OS, network, container, or descendant
  process isolation; production needs an immutable checkout and enforceable sandbox.
  Live GPT-5.6 capture requires a human-supplied API key; committed replays remain
  `fake-development`, so the final provenance addendum and final sample reports are not
  yet eligible
