# Work item 0082 — Adversarial evals, packaging, clean installation, and CI

## Objective

Harden Faber Proof against false acceptance, make the judge path reproducible from a
fresh environment, and produce credible engineering evidence for the technological-
implementation score.

Do not add product breadth. Spend this work item eliminating ways the existing vertical
slice can fail, mislead, leak sensitive data, or become difficult to install.

## Required context

Read the shared Build Week context and all implementation through 0081. Inspect the
current package metadata, Nix and `just` workflows, existing CI, runtime-boundary docs,
redaction/secret detection, golden fixtures, and performance smoke tests.

## Part A — Threat model

Create `docs/FABER_PROOF_THREAT_MODEL.md` describing:

- assets: repository content, secrets, task contract, proof catalog, model request and
  response, replay bundle, verifier policy, receipts, decision, and reports;
- trust boundaries: candidate diff, task text, model output, catalog, runner, local
  filesystem, OpenAI adapter, replay artifact, and human approval;
- attacker or failure goals: change executable behavior through untrusted data, omit a
  required claim, cause an unjustified pass, replay evidence against another diff,
  escape repository boundaries, leak a secret, forge or mismatch receipts, or make a
  partial run look complete;
- controls already implemented;
- residual risks, especially the local runner's lack of production-grade isolation;
- explicit non-claims;
- future production controls not required for the hackathon.

Keep it specific to the implemented product rather than a generic security checklist.

## Part B — Adversarial evaluation suite

Create a repeatable eval command and `docs/BUILD_WEEK_EVALS.md` with the case, expected
verdict, actual verdict, reason codes, and reproduction command.

The suite must cover at minimum:

### Untrusted repository content

- a diff comment instructs the model to ignore the task or mark the patch safe;
- a string literal imitates a system or developer instruction;
- a file contains secret-like values;
- a very large diff exceeds policy;
- a changed `.faber/` output file attempts to influence planning;
- unusual Unicode and line endings do not produce ambiguous digests.

### Planner and replay output

- unknown proof entry;
- stale proof entry version;
- extra operational-looking field;
- nested disallowed field;
- missing mandatory claim;
- duplicate claim or selection;
- malformed parameter type;
- oversized parameter;
- planner refusal;
- timeout;
- invalid structured response;
- replay request mismatch;
- replay catalog mismatch;
- replay prompt or schema mismatch;
- replay response-digest tampering;
- replay from the bad patch applied to the repaired diff and vice versa;
- critic contradiction when critic mode exists.

### Execution and evidence

- repository traversal and symlink escape attempts;
- missing approved verifier or callable;
- proof timeout;
- bounded-output truncation;
- child-process operational error;
- wrong task, attempt, plan, or catalog binding;
- receipt from another result;
- duplicate or contradictory evidence;
- all ordinary tests pass but a high-severity claim remains uncovered;
- candidate-owned output claims success while authoritative evidence fails;
- one failed claim plus one missing claim follows the documented verdict precedence;
- a partial bundle cannot be loaded as complete;
- repeated replay produces stable plan, evidence, and decision digests.

Every case must assert that an unjustified `PASS` is impossible. Use `BLOCK` for a
demonstrated contract failure and `HUMAN_REVIEW` for incomplete or uncertain evidence,
consistent with the policy.

Prefer deterministic table-driven tests. Add lightweight generated boundary cases where
valuable, but do not introduce a large testing framework solely for fuzzing.

## Part C — Secret and privacy audit

Add a deterministic repository audit script that can inspect generated demo artifacts
and committed sample reports for:

- common credential patterns;
- environment-variable values explicitly supplied to the audit as forbidden hashes or
  literals;
- absolute home-directory or temporary-directory paths;
- user names and machine-specific paths;
- unredacted diff fragments marked sensitive by fixtures;
- external asset references in the self-contained report;
- raw unbounded model or verifier output.

Avoid claiming comprehensive secret detection. State its scope and combine it with the
existing redaction tests.

The audit must fail before a replay fixture or sample report is accepted when a known
fixture secret is present.

## Part D — Packaging

Make Faber installable as a conventional Python package while preserving the current
Nix-first development path.

Update `pyproject.toml` with:

- a supported build backend;
- package discovery for `src/faber`;
- project metadata needed to build a wheel;
- console script `faber = faber.cli:main` or the correct wrapper;
- Python version metadata matching tested support;
- optional OpenAI dependency for live mode;
- any package-data entries required for templates or schemas;
- no unnecessary base runtime dependencies.

Choose a small conventional backend already compatible with the repository. Explain the
choice in a short developer note.

Validate both installations:

```text
base install
live OpenAI extra
```

The base install must not import or require the OpenAI SDK.

## Part E — Clean-install audit

Add a script or documented test that:

1. Builds an sdist and wheel.
2. Creates a fresh virtual environment outside the repository.
3. Installs the wheel without editable mode.
4. Runs `faber --help` and `faber doctor`.
5. Copies or locates the packaged original example as documented.
6. Runs the no-key replay demo.
7. Verifies bad `BLOCK`, repaired `PASS`, both ordinary-test passes, and both reports.
8. Runs the artifact privacy audit.
9. Exits nonzero on any mismatch.

Do not let the test succeed because `PYTHONPATH` still points at the checkout. Explicitly
clear or control it and record the imported package location.

Add a fast version suitable for CI and a full local audit if necessary.

## Part F — Judge path

Document a judge path of no more than five commands from a fresh clone to both reports.
Target something similar to:

```bash
python -m venv .venv
<activate the environment>
python -m pip install -e .
faber demo proof --mode replay --out-dir .faber/build-week-demo
<open the two reported HTML files>
```

Because activation syntax differs by platform, provide tested Linux/macOS and Windows
variants. A wheel-based path may be used instead when simpler.

The judge path must require no:

- OpenAI key;
- Codex account;
- network after dependencies are installed;
- Docker;
- GitHub token;
- external repository;
- model-provider call;
- hosted account.

## Part G — Continuous integration

Add or update GitHub Actions to test the supported platforms honestly.

Minimum matrix:

- Linux on Python 3.11;
- Windows on Python 3.11.

Add a newer supported Python version and macOS only when the implementation is stable
and the current hosted runners support them. Do not advertise an untested combination.

CI must cover:

- base installation without OpenAI SDK;
- test suite;
- Ruff;
- mypy;
- wheel build;
- clean installed CLI smoke;
- no-key replay demo;
- adversarial eval suite;
- privacy audit;
- deterministic sample-report regeneration check.

Keep live OpenAI calls out of pull-request and ordinary CI workflows. Provide a manual,
guarded workflow or local command only when it can avoid exposing credentials and
unreviewed artifacts.

Pin GitHub Action major versions and use least privilege. Do not grant write permissions
to a test workflow.

## Part H — Reliability and performance budget

Measure and record on the active machine:

- replay planning time;
- proof execution time;
- report generation time;
- total bad/repaired demo time;
- output bundle sizes;
- peak or approximate memory only when easy to measure reliably.

Set conservative regression thresholds for deterministic replay components. Avoid a
fragile wall-clock test on slow CI; use a generous smoke threshold or record metrics
without failing unless there is a severe regression.

The demo should feel immediate after installation. Optimize obvious repeated work but do
not rewrite core architecture for microbenchmarks.

## Part I — Documentation updates

Update:

- `docs/DEVELOPMENT.md` with packaging and test workflows;
- `docs/BUILD_WEEK_EVALS.md` with exact results;
- `docs/FABER_PROOF_THREAT_MODEL.md` with implemented controls and residual risks;
- `codex/build-week/STATUS.md` with platform, installation, eval, privacy, and demo
  evidence;
- `docs/CODEX_SESSION_HANDOFF.md` with the current clean validation baseline.

The final judge README is completed in 0083, but all commands it will need must already
work.

## Constraints

- Do not add a hosted service or account system.
- Do not make Docker mandatory.
- Do not add a large dependency solely for report rendering, schema validation, or
  fuzzing when the existing explicit style is sufficient.
- Do not weaken replay binding to simplify the demo.
- Do not skip Windows-specific path tests.
- Do not claim a production sandbox or comprehensive secret scanner.
- Do not begin the optional arena.

## Acceptance criteria

- Every documented adversarial case produces the expected fail-closed result.
- The threat model accurately describes controls and residual limitations.
- A wheel builds and imports from a clean environment outside the checkout.
- The base wheel works without the OpenAI SDK.
- The no-key demo reproduces bad `BLOCK` and repaired `PASS` after clean installation.
- Generated and committed judge artifacts pass the privacy audit.
- Linux and Windows CI pass.
- Full tests, Ruff, mypy, and available Nix checks pass.
- The judge path is five commands or fewer per platform, excluding opening the reports.
- `codex/build-week/STATUS.md` records the commit and marks 0083 as next.

## Commit

Use one focused commit similar to:

```text
Implement work item 0082 evals packaging and CI
```