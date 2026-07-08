# 0008 — Trajectory dataset export and evaluation

## Goal

Make trajectories useful as a dataset, not just individual records. Add JSONL export, dataset manifests, quality checks, and simple evaluation helpers for future routing/orchestration training.

## Scope

Add dataset tooling for:

- trajectory JSONL export
- dataset manifest creation
- split assignment
- quality summaries
- redaction hooks
- cost/value metrics
- failure taxonomy summaries

## Requirements

1. Add a dataset export module, for example `src/faber/datasets.py`.
2. Support exporting trajectories to JSONL with one canonical record per line.
3. Add dataset manifest generation with:
   - dataset id
   - created_at
   - source store path or input paths
   - record count
   - schema versions
   - total accepted/rejected counts
   - total cost/reward/margin when available
   - digest of exported JSONL
4. Add deterministic split assignment helpers:
   - train
   - validation
   - test
   Use stable hashing so records remain in the same split across runs.
5. Add quality checks:
   - missing receipt
   - missing router decision
   - missing cost metadata
   - missing outcome
   - digest mismatch where detectable
6. Add redaction hooks that can remove or replace sensitive fields before export. Keep this simple and explicit.
7. Add CLI commands if clean:
   - `faber export-trajectories --store .faber/faber.sqlite3 --out data/trajectories.jsonl`
   - `faber dataset-summary data/trajectories.jsonl`
8. Update `docs/TRAJECTORY_SCHEMA.md` with dataset/export details.
9. Do not train models in this issue.
10. Do not add pandas unless clearly justified. Prefer standard library JSONL.

## Craftsmanship bar

A future researcher should trust that exported datasets are stable, inspectable, and auditable.

## Tests

Add tests for:

- JSONL export stability
- manifest digest changes when records change
- deterministic split assignment
- accepted/rejected summary counts
- cost/value summary
- redaction hook behavior
- dataset summary CLI if implemented

## Acceptance criteria

- Trajectory JSONL export exists and is tested.
- Dataset manifests are stable and useful.
- Quality checks identify incomplete records.
- Redaction hooks exist.
- Docs explain how trajectories support supervised learning, preference learning, RL, and router training.
- Existing tests still pass.
