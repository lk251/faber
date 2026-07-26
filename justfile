set shell := ["sh", "-eu", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

export PYTHONPATH := "src"

fmt:
    python -m ruff format .

format: fmt

format-check:
    python -m ruff format --check .

lint:
    python -m ruff check .

typecheck:
    python -m mypy src

test:
    python -m pytest

doctor:
    python -m faber.cli doctor

smoke:
    python -m faber.cli doctor
    python -m faber.cli init-local-store --path .faber/smoke.sqlite3
    python -m faber.cli emit-demo-trajectory --out .faber/smoke_trajectory.json

demo:
    python -m faber.cli run-golden-path --store .faber/golden.sqlite3 --out .faber/golden_trajectory.json

demo-funded-trajectory:
    python -m faber.cli demo-funded-trajectory --out-dir .faber/funded-demo

demo-proof:
    python -m faber.cli demo proof --mode replay --out-dir .faber/build-week-demo

proof-evals:
    python scripts/run_build_week_evals.py --check

proof-report-regeneration:
    python scripts/check_development_report_regeneration.py --check

proof-performance:
    python scripts/measure_proof_demo.py

proof-clean-install:
    python scripts/clean_install_audit.py

check: format-check lint typecheck test smoke
