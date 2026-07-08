# 0015 - Probabilistic Verifier Protocol

## Goal

Implement provider-agnostic protocol objects for probabilistic verification.

## Scope

Add explicit protocol records for:

- `VerifierScoreSpec`
- `CriterionSpec`
- `ScoringScale`
- `ScoringTokenDistribution`
- `CriterionScore`
- `VerifierScore`
- `PairwisePreference`
- `VerificationBudget`
- `VerifierUncertainty`

## Requirements

- Do not add real model APIs.
- Use a fake deterministic scoring backend only.
- Preserve stable serialization and stable digests.
- Scores must record:
  - verifier id;
  - scoring policy name and version;
  - criteria;
  - repetitions;
  - granularity;
  - per-criterion scores;
  - aggregate score;
  - uncertainty or confidence where possible;
  - cost metadata in integer minor units if monetary;
  - latency metadata.
- Docs must clearly distinguish hard authoritative verification from advisory
  probabilistic verification.

## Tests

Add tests for:

- digest stability;
- schema shape;
- repeated evaluation aggregation;
- criteria decomposition;
- fake backend determinism;
- advisory scores not becoming `VerificationReceipt` authority by default.

## Acceptance Criteria

- New objects are boring dataclasses with `to_dict()` and `digest()` methods.
- No provider names appear in core probabilistic verification objects.
- Existing checks pass.
