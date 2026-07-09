# 0073 — Local store scale and performance smoke

## Goal

Ensure Faber's local store and dataset export remain usable with thousands of records before adding hosted infrastructure.

## Scope

Add performance smoke tests for:

- inserting many task contracts
- inserting many attempts and events
- exporting many trajectories to JSONL
- calculating summary metrics
- filtering training-eligible RL-grade records

## Requirements

- Keep tests lightweight enough for normal checks.
- Use generated fake records.
- Do not optimize prematurely; measure and guard obvious regressions.
- No external database.
- No hosted service.

## Tests

- store can insert a modest batch quickly
- export handles a modest trajectory corpus
- summary metrics remain correct
- duplicate idempotent inserts do not grow records unexpectedly

## Acceptance criteria

Faber's local-first architecture remains pleasant for realistic development datasets.