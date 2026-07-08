# 0014 — Hardening pass after the queue

## Goal

After completing the previous issues, do a final hardening pass focused on correctness, coherence, documentation quality, and removal of accidental complexity.

This is the cleanup issue. It should not introduce major new product surfaces.

## Scope

Review the whole repository for:

- broken docs
- inconsistent names
- duplicated helpers
- weak tests
- unclear error messages
- untested CLI paths
- drift between README, docs, and implementation
- type-checking gaps
- lint suppressions
- excessive dependencies
- overly clever abstractions

## Requirements

1. Run the full test/check suite.
2. Fix any failing tests introduced by previous issues.
3. Ensure README, AGENTS.md, and docs agree on terminology:
   - Faber
   - Faber for GitHub
   - Faber Market
   - Faber Protocol
   - Faber Runner
   - Faber Verifiers
   - Faber Orchestration
4. Ensure there is no return of discarded metaphors or old hackathon names except in historical/reference docs.
5. Ensure the first-class objects remain the root objects:
   - `TaskContract`
   - `Attempt`
   - `VerifierRun`
   - `VerificationReceipt`
   - `Trajectory`
   - `Settlement`
   - `WorkerProfile`
   - `RouterDecision`
   - `MarketEvent`
6. Ensure no vendor is hardcoded into the core.
7. Improve docstrings and error messages where they would help future contributors.
8. Add a `docs/ROADMAP.md` with the next 10 likely issues after this queue, but do not implement them.
9. Add `docs/OPEN_QUESTIONS.md` for strategic questions that require human judgment.
10. Keep the repo small and readable.

## Craftsmanship bar

The final state should feel like a well-made instrument: minimal, precise, inspectable, and ready for the next serious product increment.

## Tests

Run:

```bash
nix develop --command just check
```

If Nix is unavailable, run:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

Document exactly what ran.

## Acceptance criteria

- Full checks pass, or any environmental limitation is documented precisely.
- Documentation and implementation terminology are aligned.
- No accidental vendor lock-in or old hackathon architecture has entered the core.
- `docs/ROADMAP.md` and `docs/OPEN_QUESTIONS.md` exist.
- The repo is ready for a human review pass.
