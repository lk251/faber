# 0060 — Router training dataset features and labels

## Goal

Create an explicit dataset view for training routers that choose workers, verifiers, budgets, and escalation policies.

## Scope

Add dataset export helpers for:

- task features
- worker features
- harness/model/environment features
- verifier policy features
- selected worker/verifier/budget labels
- outcome labels
- cost/latency/review labels
- value-per-euro labels

## Requirements

- Do not train models.
- Export JSONL records only.
- Include provenance and disclosure levels.
- Include negative examples: rejected attempts, declined tasks, timeouts, verifier failures.
- Filter by training consent.
- Support weak labels for PR-only records and stronger labels for RL-grade trajectories.

## Tests

- router dataset export includes required features
- training consent filter works
- weak/strong label distinction is preserved
- value-per-euro label uses integer money
- negative examples are included when policy allows

## Acceptance criteria

Faber can export clean supervised training data for future worker/router/orchestration selection.