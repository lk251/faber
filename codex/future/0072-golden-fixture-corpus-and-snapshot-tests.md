# 0072 — Golden fixture corpus and snapshot tests

## Goal

Create a high-quality fixture corpus that protects Faber's protocol, examples, and training export behavior from accidental drift.

## Scope

Add golden fixtures for:

- PR-only low-evidence trajectory
- manifest-backed trajectory
- RL-grade trace-backed trajectory
- replayable episode package
- funded GitHub issue
- rejected attempt
- human-reviewed attempt
- advisory-verifier-ranked candidate pool
- NixOS environment evidence
- cross-platform environment evidence

## Requirements

- Fixtures should be small, readable, deterministic, and documented.
- Snapshot tests should verify canonical JSON and digest stability.
- Avoid brittle snapshots of irrelevant timestamps; use fixed timestamps in fixtures.
- Dataset export tests should use the fixture corpus.

## Tests

- all fixtures validate
- canonical JSON snapshots stable
- digest snapshots stable
- dataset export from fixtures stable
- docs examples match fixture names

## Acceptance criteria

Faber has a regression shield around its most important protocol behavior.