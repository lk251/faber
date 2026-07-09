# 0047 — Training data rights, consent, and licensing

## Goal

Define how Faber records whether a trajectory may be used for training, evaluation, research, public datasets, private hosted learning, or only audit.

## Scope

Add protocol/docs for:

- `TrainingUsePolicy`
- `TrajectoryConsent`
- `DataLicense`
- `VisibilityLevel`
- `RetentionPolicy`
- `DeletionRequest`
- `DatasetExportPolicy`

## Requirements

- Do not assume every trajectory can be used for training.
- Distinguish audit retention from model-training permission.
- Distinguish public/open trajectories from private/customer trajectories.
- Support repository-level and task-level defaults.
- Support solver/operator consent and repo-owner/customer consent separately.
- Dataset export must filter by training permission.
- Add provenance for who granted which permission and when.
- No legal claims; frame docs as product/protocol requirements needing later legal review.

## Tests

- training-ineligible trajectory is excluded from training export
- audit-only record remains queryable for verification history
- task-level policy overrides default when stricter
- public dataset export excludes private records
- deletion/retention policy is represented without deleting audit-critical receipts by accident

## Acceptance criteria

Faber can separate customer value, auditability, and model-training rights before collecting valuable RL-grade data.