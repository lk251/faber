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

check: format-check lint typecheck test smoke
