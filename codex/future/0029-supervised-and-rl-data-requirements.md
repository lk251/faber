# 0029 - Supervised And RL Data Requirements

## Goal

Document and test data requirements for supervised learning and reinforcement
learning.

Create `docs/DATA_REQUIREMENTS.md`.

## Scope

Explain required fields for:

- supervised worker/router selection;
- attempt quality prediction;
- harness/orchestration imitation;
- verifier calibration;
- progress scoring;
- reinforcement learning;
- value-per-euro evaluation.

## Requirements

- Do not train models.
- Do not add machine-learning frameworks.
- Do not require private chain-of-thought.
- Do not require solvers to reveal proprietary prompts or finetune weights.
- Support disclosure levels, redaction, and provenance.
- Cost metadata must use integer minor units.

## Fixtures Or Tests

Add tests or fixtures demonstrating:

- PR-only trajectory supports weak supervised labels;
- manifest trajectory supports router training;
- runner trace supports harness/orchestration learning;
- progress-scored trace supports dense reward export;
- cost metadata supports intelligence-per-euro metrics.

## Acceptance Criteria

- `docs/DATA_REQUIREMENTS.md` distinguishes weak PR-only data from richer trace
  data.
- Data requirements are explicit enough to guide future schema work.
- No runtime ML dependency is added.
