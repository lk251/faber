# Work item 0082 HB2 machine handoff

This is the detailed checkpoint for moving active Faber Proof work from HB2 to HB3.
Read it after `AGENTS.md`, `docs/CODEX_SESSION_HANDOFF.md`, and
`codex/build-week/STATUS.md`.

## Checkpoint scope

- Branch: `build-week/faber-proof`
- Starting commit for this checkpoint:
  `e69552e1316a77361075a8d321f1c3fb7d7be54f`
- Remote: `git@github.com:lk251/faber.git`
- GitHub issue: `#7`
- Active work item: `codex/future/0082-adversarial-evals-packaging-ci.md`
- Follow-on item: `codex/future/0083-submission-video-final-audit.md`
- Platform used: HB2, Windows, Python 3.11.15
- State: this historical checkpoint has been completed locally. Threat/eval/live
  documentation, repository-wide formatting, full checks, packaging, clean installation,
  privacy, report regeneration, and performance evidence are green. The only 0082 gate
  still open is remote workflow activation and observation.
- 0083 machine work is current.

The commit containing this file is a machine-transfer checkpoint, not the 0082
completion commit. Use `git log -1 --oneline` after cloning to identify the exact
checkpoint commit.

## What is implemented

### Deterministic adversarial evaluation

- `src/faber/proof_evals.py` defines the deterministic case manifest and result model.
- `scripts/run_build_week_evals.py` runs the selected pytest cases, writes JSON,
  Markdown, and JUnit evidence, and rejects an unjustified `PASS`.
- `tests/test_proof_evals.py` covers manifest stability and result generation.
- Committed generated evidence is under:
  - `docs/generated/BUILD_WEEK_EVAL_RESULTS.json`
  - `docs/generated/BUILD_WEEK_EVAL_RESULTS.md`
- Latest HB2 result: 49/49 cases passed, zero unjustified passes.
- Suite digest:
  `sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`

The campaign covers prompt injection and operational-field smuggling, malformed and
oversized planner output, replay poisoning and cross-candidate reuse, catalog and
receipt binding failures, path and symlink attacks, verifier errors and truncation,
partial/tampered bundles, secret-like values, and fail-closed authority behavior.

### Privacy audit

- `src/faber/proof_privacy.py` implements the deterministic artifact privacy scanner.
- `faber audit-proof-artifacts` is registered in `src/faber/cli.py`.
- `tests/test_proof_privacy.py` covers secret-like values, absolute checkout paths,
  external report assets, redaction, and clean bundles.
- The reviewed replay-fixture installation path and clean-install audit both invoke
  the privacy scanner.
- Latest complete installed-demo audit found zero privacy findings across 51 demo
  files.

The scanner is a bounded release check, not a claim that arbitrary secrets can always
be detected. The remaining threat-model documentation is listed under "Work still
required."

### Packaging and clean installation

- `pyproject.toml` now uses a conventional setuptools build backend and `src/` layout.
- Base Faber has no runtime dependencies.
- The optional `live-openai` extra installs the OpenAI SDK only for guarded live use.
- Build Week replay fixtures and demo source are installed as package data.
- `scripts/clean_install_audit.py` builds a wheel and sdist, installs the wheel outside
  the checkout with no checkout `PYTHONPATH`, verifies the imported module location,
  proves the base environment has no OpenAI package, runs the no-key bad/repaired demo,
  audits its artifacts, and optionally verifies the live extra in a separate
  environment without making a provider call.
- `tests/test_packaging_audit.py` covers packaging metadata and the clean audit.

Latest complete HB2 clean-install result:

```text
status: pass
base import: site-packages/faber/__init__.py
checkout PYTHONPATH: absent
base OpenAI package: absent
live extra OpenAI package: present
ordinary tests: PASS / PASS
Faber Proof: BLOCK / PASS
demo files: 51
demo bytes: 232257
privacy findings: 0
wheel bytes: 333474
sdist bytes: 388290
```

### Determinism and authority hardening

- Planner diff text is normalized for line endings and must match the attempt patch
  digest.
- Replay verifier-run and receipt identities are deterministic.
- Host-specific artifact roots are excluded from authority digests.
- Timing values are excluded from authoritative process observations and report
  content.
- Portable recorded commands retain a raw command digest while avoiding checkout and
  runtime paths in exported bundles.
- Repeated bad/repaired replay runs produce the same plan, evidence, decision, and
  report bytes.
- Full generated demo bundles pass the privacy path scan.
- Report artifact tables exclude the timing-bearing workflow result so the rendered
  report remains byte stable.

### CI and reproducibility evidence

- `codex/build-week/drafts/ci.yml` preserves the prepared CI workflow verbatim. It
  defines least-privilege `contents: read` Linux and Windows jobs using
  `actions/checkout@v7` with persisted credentials disabled and
  `actions/setup-python@v6`.
- CI runs pytest, Ruff lint and format checks, mypy, wheel/sdist build, clean-install
  audit, adversarial evals, deterministic report regeneration, and proof-demo
  measurement.
- A separate optional-extra job installs `.[live-openai]` and makes no provider call.
- `tests/test_ci_workflow.py` checks the draft's permissions and required coverage.
- `scripts/check_development_report_regeneration.py` verifies four byte-stable
  fake-development reports.
- `scripts/measure_proof_demo.py` records runtime, bundle size, and privacy evidence.
- Latest HB2 measurement: 6.258291 seconds total, 232259 output bytes, zero privacy
  findings.
- Generated evidence is under:
  - `docs/generated/DEVELOPMENT_REPORT_REGENERATION.json`
  - `docs/generated/DEVELOPMENT_REPORT_REGENERATION.md`
  - `docs/generated/BUILD_WEEK_PERFORMANCE_HB2.json`
  - `docs/generated/BUILD_WEEK_PERFORMANCE_HB2.md`

### Guarded live capture

- `examples/build-week-proof/scripts/capture_live_reviewed_demo.py` is the prepared
  one-command live transaction.
- It requires an API key, expected branch, clean tree, authority bindings, real
  provider metadata, reviewer identity, privacy-clean artifacts, atomic fixture
  installation with rollback, and a successful no-key replay after installation.
- It writes `.faber/live-gpt56-review-manifest.json`.
- Fake injected success, rollback, and preflight tests pass.
- No live provider call was made on HB2. Do not call one without the explicit human
  gate.

## Validation already performed on HB2

Use the ignored environment at `.faber/dev-venv` only on HB2. Recreate an environment
on HB3 rather than depending on it.

```text
Python 3.11.15
pytest 9.0.2
Ruff 0.15.10
mypy 2.1.0
build 1.5.0
```

Recorded passing checks:

- full repository suite: 699 passed, 1 guarded live test skipped in 117.88 seconds
- `python -m ruff check .`: passed
- `python -m ruff format --check .`: 189 files already formatted
- planner-focused suite: 88 passed, 1 guarded live test skipped
- product-focused suite after timing fields: 14 passed
- packaging tests: 4 passed
- guarded live fake success: 1 passed
- guarded live rollback: 1 passed
- guarded live preflight without callback: 1 passed
- deterministic replay and full-demo privacy regressions: passed
- adversarial campaign, run twice: 49/49 passed, zero unjustified passes
- deterministic report regeneration: 4 byte-stable reports
- `python -m mypy src`: success across 93 source files
- focused Ruff checks: passed
- wheel and sdist build: passed
- full clean-install audit including optional live extra: passed

The final clean-install audit produced a 333474-byte wheel and 388290-byte sdist. Its
installed no-key demo produced ordinary `PASS`/`PASS`, Faber Proof `BLOCK`/`PASS`, 51
files, 232257 bytes, and zero privacy findings. Final performance evidence records
6.258291 seconds, 232259 bytes, and zero privacy findings.

Nix and `just` were unavailable on HB2. Run the repository's normal checks on HB3 when
available; otherwise run the documented local equivalents and record the limitation.

## Work still required for 0082

Promote `codex/build-week/drafts/ci.yml` to `.github/workflows/ci.yml` using a non-FIDO
credential that GitHub permits to modify workflow files. The HB2 repository deploy key
authenticates correctly, but GitHub rejected a push containing the workflow path because
the OAuth app that registered the key lacks `workflow` scope. Do not fall back to the
FIDO key.

After promotion, observe both Linux and Windows jobs to completion and repair any
platform failure. All machine work independent of that external authorization is
complete, so 0083-M proceeds while this exact blocker remains recorded.

## Intended threat-model content

The documentation still needed in 0082 should preserve these facts:

- Assets: task/diff integrity, owner catalog, planner response, execution evidence,
  receipts, decision, report bundle, credentials, and reviewed replay provenance.
- Trust boundaries: candidate repository to planner context; planner to plan; replay to
  adapter; owner catalog to executor; executor to authority; bundle to consumer; live
  capture to committed fixture.
- Controls: closed schemas, bounded inputs, immutable catalog commitments, preflight
  all selections, fixed executors, path containment, symlink rejection, timeouts and
  output caps, source and workspace digests, receipt binding, deterministic fail-closed
  policy, atomic bundles, self-contained reports, redaction/privacy audit, and guarded
  fixture replacement.
- Honest residual risks: local execution is not an OS/network/descendant-process
  sandbox; the privacy scanner is bounded; owner-approved catalog content is trusted;
  digests provide integrity rather than signing; an immutable checkout and enforceable
  production sandbox are future requirements.

## 0083 continuation

After 0082 and CI are green, execute all machine-completable parts of
`codex/future/0083-submission-video-final-audit.md` and
`codex/build-week/OFFLINE_CONTINUATION.md`:

- top-level judge quickstart
- complete Devpost draft with only genuine human/live placeholders
- mechanically checked 2:35-2:50 narration
- shot list, submission checklist, and image-source artifacts
- deterministic final audit JSON and Markdown
- Build Week delta, decisions, security, business, and adoption material
- exact human gate list

Do not make a live provider call, publish a video, submit Devpost, share the private
repository, or create the final submission tag without the required human action.

## Git and SSH on HB3

Use a machine-local, repository-specific non-FIDO key. The HB2 private key is not in
Git and must not be copied into this repository. Configure the HB3 clone to constrain
all Faber Git traffic to its own key:

```powershell
git config core.sshCommand "C:/Windows/System32/OpenSSH/ssh.exe -i C:/Users/javie/.ssh/faber_github_deploy_ed25519 -o IdentitiesOnly=yes -o AddKeysToAgent=no"
git config --local --get core.sshCommand
git fetch --prune origin
```

Before changing files on HB3:

```powershell
git status -sb
git branch --show-current
git log -1 --oneline --decorate
git rev-list --left-right --count HEAD...origin/build-week/faber-proof
```

The expected branch after cloning this checkpoint is `build-week/faber-proof`, clean
and even with its remote. Before 0082 can complete, promote the preserved CI draft
using an appropriately authorized non-FIDO credential.
