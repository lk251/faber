# 0003 — Quality gates and development experience

## Goal

Make Faber feel like a serious craft project from the first clone: predictable checks, readable errors, clean tooling, and documented local workflows.

This issue should not change the product model. It should make the repository safer and more pleasant to work in.

## Scope

Improve repository quality infrastructure around:

- `justfile`
- `pyproject.toml`
- `flake.nix`
- test organization
- type checking
- linting
- local developer documentation
- package import behavior
- CLI smoke tests

## Requirements

1. Ensure `nix develop --command just check` is the canonical check.
2. Ensure `just check` runs, in a sensible order:
   - formatting check or formatter
   - ruff linting
   - mypy over `src`
   - pytest
   - CLI smoke checks if cheap
3. Add `just fmt`, `just test`, `just lint`, `just typecheck`, and `just doctor` if missing.
4. Make `python -m faber.cli doctor` report useful environment facts:
   - Python version
   - package import status
   - sqlite availability
   - current working directory
   - whether `.faber/` exists
   - a final human-readable OK line
5. Add or improve tests for the CLI smoke path.
6. Ensure README development instructions are accurate for NixOS first, with non-Nix fallback clearly secondary.
7. Add `docs/DEVELOPMENT.md` with exact commands and troubleshooting notes.
8. Keep dependencies minimal and justified.
9. Do not introduce Docker, web servers, hosted services, payment providers, or model providers.

## Craftsmanship bar

- A new developer should be able to clone the repo and know exactly what command to run.
- Failure messages should make the next action obvious.
- Checks should be deterministic and fast.
- Do not hide failures behind permissive shell behavior.

## Tests

Add tests that cover:

- CLI doctor returns success
- demo trajectory emission still works
- local store initialization still works
- check commands documented in README/DEVELOPMENT match actual commands where practical

## Acceptance criteria

- `nix develop --command just check` succeeds, or closest available equivalents are run and documented.
- `docs/DEVELOPMENT.md` exists and is useful.
- `README.md` has accurate NixOS-first setup instructions.
- CLI smoke tests exist.
- Existing Issue #1 and Issue #2 tests still pass.
