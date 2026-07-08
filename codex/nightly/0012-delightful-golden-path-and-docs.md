# 0012 — Delightful golden path and documentation

## Goal

Create a polished local golden path that lets a new user understand Faber in minutes: create a task, submit an attempt, run an approved verifier, issue a receipt, settle locally, and export a trajectory.

This issue is about customer delight through clarity and reliability, not surface-level demo theater.

## Scope

Add or improve:

- README quickstart
- docs quickstart
- CLI golden path
- local example fixtures
- narrative examples
- troubleshooting
- architecture diagram in text/mermaid if appropriate

## Requirements

1. Add `docs/QUICKSTART.md`.
2. Add `docs/GOLDEN_PATH.md` with a complete local walkthrough.
3. Provide a small example under `examples/` that can be used by tests.
4. Add CLI commands if missing to support a clear local flow:
   - create a demo contract
   - register a demo worker
   - register a demo verifier
   - submit a demo attempt
   - run verifier
   - issue receipt
   - settle locally
   - export trajectory
5. Keep the commands composable and transparent. Avoid one opaque magic command unless it is clearly labeled as a demo wrapper.
6. Add `just demo` if it can run quickly and deterministically.
7. Make output human-friendly and precise. Include IDs and file paths.
8. Add tests for the golden path.
9. Update README to point to quickstart and golden path.
10. Do not add web UI or hosted services.

## Craftsmanship bar

The first five minutes should feel calm and impressive. A developer should believe the system is small, real, and trustworthy.

## Tests

Add tests for:

- golden path CLI flow
- generated files exist
- exported trajectory validates
- docs command snippets are accurate where practical
- `just demo` if added

## Acceptance criteria

- Quickstart and golden path docs exist.
- A local end-to-end flow works without external services.
- `just demo` or equivalent is deterministic if implemented.
- README points users to the right first command.
- Existing tests still pass.
