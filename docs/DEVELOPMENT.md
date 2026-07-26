# Development

Faber supports Python 3.11 or newer. The declared Build Week CI platforms are Linux
and Windows on Python 3.11.

## Canonical check

From a fresh clone in the repository development environment:

```bash
nix develop --command just check
```

`just check` runs formatting, lint, mypy, pytest, the CLI doctor, and local-store smoke
commands. When Nix or `just` is unavailable, run the equivalent Python commands and
record that limitation.

## Python environment

Create and install an isolated development environment:

Linux/macOS:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ".[dev]"
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[dev]"
```

An installed environment does not need `PYTHONPATH`. For direct source-tree fallback
commands without installation, set `PYTHONPATH=src` on POSIX or
`$env:PYTHONPATH = "src"` in PowerShell.

## Common commands

```bash
just fmt
just lint
just typecheck
just test
just doctor
just demo-proof
just proof-evals
just proof-report-regeneration
just proof-performance
just proof-clean-install
```

The direct check equivalents are:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
python -m faber.cli doctor
```

## Packaging

Faber uses the standard setuptools build backend with `src/faber` package discovery.
This keeps the build conventional, dependency-light, and compatible with the
repository's existing explicit package structure. Build Week replay fixtures are
installed as package data so the no-key demo works outside the checkout.

The base package intentionally has no runtime dependency and neither imports nor
requires the OpenAI SDK:

```bash
python -m pip install .
```

Install the optional SDK only for the guarded live planner:

```bash
python -m pip install ".[live-openai]"
```

Build both conventional artifacts:

```bash
python -m build --wheel --sdist --outdir dist
```

## Clean-install audit

The full audit builds a wheel and sdist, creates fresh environments outside the
checkout, clears checkout `PYTHONPATH`, installs the wheel non-editably, checks the
actual import location, proves the base install lacks the OpenAI package, runs
`faber --help` and `faber doctor`, executes the installed no-key demo, validates
ordinary `PASS`/`PASS` and Faber Proof `BLOCK`/`PASS`, and privacy-audits every
generated artifact. It also installs the optional extra in a separate environment
without making a provider call.

```bash
python scripts/clean_install_audit.py --json-out .faber/clean-install-audit.json
```

Ordinary CI can skip the network-dependent optional-extra installation probe:

```bash
python scripts/clean_install_audit.py --skip-live-extra
```

## Faber Proof release checks

Run and compare the deterministic adversarial campaign:

```bash
python scripts/run_build_week_evals.py --check
```

Check byte-stable development report regeneration:

```bash
python scripts/check_development_report_regeneration.py --check
```

Measure the no-key bad/repaired workflow, output sizes, and privacy state:

```bash
python scripts/measure_proof_demo.py
```

Audit any local or committed proof artifacts directly:

```bash
faber audit-proof-artifacts .faber/build-week-demo examples/build-week-proof/expected
```

The audit is a bounded check for known secret forms, supplied forbidden values,
machine-specific paths, external report assets, sensitive fixture fragments, and raw
unbounded output. It is not comprehensive secret discovery.

## Judge path

The no-key judge flow is no more than five commands per platform, excluding opening
the two generated HTML files.

Linux/macOS:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
faber doctor
faber demo proof --mode replay --out-dir .faber/build-week-demo
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\faber.exe doctor
.\.venv\Scripts\faber.exe demo proof --mode replay --out-dir .faber\build-week-demo
```

Expected reports:

```text
.faber/build-week-demo/bad/report.html
.faber/build-week-demo/repaired/report.html
```

The flow requires no API key, Codex account, Docker, GitHub token, external repository,
hosted account, or provider call. After the package is installed, replay itself makes
no network request.

## Guarded live development

Live capture is a separate human gate. Read `docs/LIVE_GPT56_CAPTURE_RUNBOOK.md` and
use its one-command transaction. Ordinary development and CI must not call a provider
or relabel the current `fake-development` fixtures.

## Submission checks

Check that the marked narration remains inside the recording budget:

```bash
python scripts/check_demo_script.py
```

Run every machine-completable final check and write the durable report:

```bash
python scripts/final_submission_audit.py --run-machine-checks --require machine \
  --json-out docs/generated/FINAL_SUBMISSION_AUDIT.json \
  --markdown-out docs/generated/FINAL_SUBMISSION_AUDIT.md
```

`--require machine` succeeds only when the deterministic machine lane passes. The
report still records unresolved human actions without treating them as machine
failures. Use `--require submission` only after the human-gate state is backed by real
evidence and bound to the audited commit.

Write the exact competition delta in both formats from one repository snapshot:

```bash
python scripts/build_week_delta.py --target HEAD \
  --json-out docs/generated/BUILD_WEEK_DELTA.json \
  --markdown-out docs/generated/BUILD_WEEK_DELTA.md
```

## Troubleshooting

- If `faber` is not found, invoke the executable from the active environment or use
  `python -m faber.cli`.
- If an import resolves inside the checkout during a clean-install audit, remove
  `PYTHONPATH`, leave the repository directory, and reinstall the wheel non-editably.
- If Git is unavailable, install it and ensure `git --version` succeeds; the original
  demo materializes deterministic candidate commits.
- If SQLite checks fail, confirm the Python build includes the standard-library
  `sqlite3` module.
- If `.faber/` contains stale output, remove that generated directory and rerun the
  command. `.faber/` is ignored local state.
