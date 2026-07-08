# Development

Faber is developed with NixOS as the first-class environment.

## Canonical Check

From a fresh clone, run:

```bash
nix develop --command just check
```

`just check` runs, in order:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
python -m faber.cli doctor
python -m faber.cli init-local-store --path .faber/smoke.sqlite3
python -m faber.cli emit-demo-trajectory --out .faber/smoke_trajectory.json
```

## Common Commands

```bash
just fmt
just lint
just typecheck
just test
just doctor
```

## Non-Nix Fallback

On machines without Nix, use Python directly:

```bash
export PYTHONPATH=src
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
python -m faber.cli doctor
```

On Windows PowerShell, set `PYTHONPATH` with:

```powershell
$env:PYTHONPATH = "src"
```

## Troubleshooting

- If `python -m faber.cli doctor` cannot import `faber`, confirm `PYTHONPATH`
  includes `src`.
- If SQLite checks fail, confirm the Python build includes the standard-library
  `sqlite3` module.
- If `.faber/` does not exist, run
  `python -m faber.cli init-local-store --path .faber/faber.sqlite3`.
- If Nix is unavailable, record that limitation and run the non-Nix fallback
  commands before claiming the repository is healthy.
