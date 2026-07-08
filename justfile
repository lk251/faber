set shell := ["sh", "-eu", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

export PYTHONPATH := "src"

format:
    ruff format .

format-check:
    ruff format --check .

lint:
    ruff check .

typecheck:
    mypy src

test:
    pytest

check: format-check lint typecheck test
