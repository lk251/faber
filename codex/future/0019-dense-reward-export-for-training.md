# 0019 - Dense Reward Export For Training

## Goal

Add dense reward export fields for future supervised learning, preference
learning, and reinforcement learning.

## Scope

Support export fields for:

- reward-shaping metadata;
- pairwise preference examples;
- group-relative preference examples;
- per-step or per-prefix progress scores;
- cost/value-aware reward summaries.

## Requirements

- Do not add real model APIs.
- Do not train models.
- Do not add machine-learning frameworks.
- Standard-library JSONL export is enough.
- Cost-adjusted reward summaries must use integer money.
- Update `docs/TRAJECTORY_SCHEMA.md`.

## Tests

Add tests for:

- dense reward fields appearing in trajectory or dataset export;
- stable pairwise preference examples;
- stable group-relative examples;
- cost-adjusted reward summaries using integer money.

## Acceptance Criteria

- Dense reward export is a data format addition only.
- Existing trajectory export remains backward compatible.
- No runtime model dependency is added.
