# Faber Proof judge quickstart

This is the shortest reproducible path from a clean Faber checkout to the original
bad/repaired Faber Proof comparison. Replay requires no API key, account, model SDK,
network request, Docker image, hosted service, or rebuild of a third-party project.

## Supported combinations

| Platform | Python | Status |
|---|---|---|
| Windows | 3.11 | Locally validated on HB2 with Python 3.11.15 |
| Linux | 3.11 | Declared in the prepared Build Week workflow; remote run not yet observed |
| macOS | 3.11+ | Expected from the standard Python path, not claimed CI-verified |

The package metadata accepts Python 3.11 or newer. The Build Week workflow intentionally
targets Python 3.11 on Linux and Windows. Git must be available because the demo creates
an isolated deterministic candidate repository.

## Fastest no-key path

Clone the competition branch, then run the platform block.

```bash
git clone --branch build-week/faber-proof https://github.com/lk251/faber.git
cd faber
```

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

Expected terminal comparison:

```text
                         BAD PATCH   REPAIRED PATCH
Ordinary tests              PASS          PASS
Faber Proof verdict        BLOCK          PASS
Failed required claims         1             0
Concrete counterexamples      1             0

Replay provenance: FAKE-DEVELOPMENT
```

Open:

```text
.faber/build-week-demo/bad/report.html
.faber/build-week-demo/repaired/report.html
```

The reports are self-contained and load from disk without a server or external assets.
The first is a red `BLOCK` with the failed last-turn claim and concrete counterexample;
the second is a green `PASS` with complete required evidence.

## Wheel install variant

The release audit builds and installs the wheel outside the checkout with `PYTHONPATH`
removed. To reproduce that path manually:

```bash
python -m pip install build
python -m build --wheel --outdir dist
python -m venv .wheel-venv
.wheel-venv/bin/python -m pip install dist/faber-0.1.0-py3-none-any.whl
.wheel-venv/bin/faber demo proof --mode replay --out-dir .faber/wheel-demo
```

Windows uses the same artifacts:

```powershell
py -3.11 -m pip install build
py -3.11 -m build --wheel --outdir dist
py -3.11 -m venv .wheel-venv
.\.wheel-venv\Scripts\python.exe -m pip install .\dist\faber-0.1.0-py3-none-any.whl
.\.wheel-venv\Scripts\faber.exe demo proof --mode replay --out-dir .faber\wheel-demo
```

## Editable development variant

For source exploration:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
faber doctor
python -m pytest -q
faber demo proof --mode replay --out-dir .faber/build-week-demo
```

Activate the environment first when its executable directory is not already on `PATH`.

## Validate bundle integrity

The demo validates each bundle before publishing it. An explicit post-run check is:

```bash
python -c "from faber.proof_product import validate_proof_bundle; print(validate_proof_bundle('.faber/build-week-demo/bad')['status']); print(validate_proof_bundle('.faber/build-week-demo/repaired')['status'])"
```

Expected output:

```text
valid
valid
```

The validator requires the complete manifest and declared artifacts, recomputes every
artifact digest, and rejects a partial or modified bundle.

Run the bounded privacy audit separately:

```bash
faber audit-proof-artifacts .faber/build-week-demo
```

## Optional guarded live path

Live mode is not required to judge replay. It is a separate human-reviewed provenance
gate and must never be run with a credential in screen recordings or shared terminals.

Install the optional adapter:

```bash
python -m pip install ".[live-openai]"
```

After setting `OPENAI_API_KEY` locally, the prepared transaction is:

```bash
python examples/build-week-proof/scripts/capture_live_reviewed_demo.py --reviewer "Javier"
```

Read [the live capture runbook](LIVE_GPT56_CAPTURE_RUNBOOK.md) first. The wrapper
preflights the clean branch and exact bindings, stages bad and repaired responses,
sanitizes and audits them, requires the material `BLOCK`/`PASS` result, and replaces
fixtures atomically only after human review. Current committed fixtures remain
`fake-development`; no live provenance is claimed.

## Runtime expectations

The completed HB2 measurement for both candidates was 6.258291 seconds and 232,259
output bytes on Windows with Python 3.11.15. The conservative release smoke threshold
is 90 seconds for the full bad/repaired demo. Initial environment creation and package
installation are separate and depend on the machine and package cache.

## Troubleshooting

### `faber` is not found

Use the executable inside the environment:

```powershell
.\.venv\Scripts\faber.exe doctor
```

On POSIX, activate `.venv` or run `.venv/bin/faber`. An installed environment does not
need `PYTHONPATH`.

### Git is unavailable

Run:

```bash
git --version
```

Install Git or put it on `PATH`, then rerun the demo. Faber materializes candidate
commits locally; it does not contact GitHub during replay.

### Output already exists or looks stale

Choose a fresh `--out-dir` or remove only the generated local directory. `.faber/` is
ignored repository state:

```powershell
Remove-Item -Recurse -Force .faber\build-week-demo
```

Then rerun the exact replay command.

## Cleanup and uninstall

Generated demo data is confined to `.faber/`. Remove it and the environment:

Linux/macOS:

```bash
rm -rf .faber/build-week-demo .venv .wheel-venv
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force .faber\build-week-demo, .venv, .wheel-venv
```

If Faber was installed into another active environment:

```bash
python -m pip uninstall faber
```

## Final machine audit

Maintainers can execute every available release gate and write deterministic reports:

```bash
python scripts/final_submission_audit.py \
  --run-machine-checks \
  --require machine \
  --json-out docs/generated/FINAL_SUBMISSION_AUDIT.json \
  --markdown-out docs/generated/FINAL_SUBMISSION_AUDIT.md
```

`machine_status=pass` is distinct from `human_status=incomplete`. Use
`--require submission` only after the structured live, audit, access, video, deadline,
Devpost, and final-tag attestations are complete.
