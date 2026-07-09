# 0067 — Risk gating for funded agent tasks

## Goal

Ensure Faber can identify tasks that are inappropriate for unsupervised agent execution or automatic funded work.

## Scope

Add task risk flags and review gates:

- `TaskRiskLevel`
- `ExternalActionRisk`
- `CredentialRisk`
- `PrivateDataRisk`
- `RegulatedDomainRisk`
- `SecuritySensitiveRisk`
- `HumanReviewGate`

## Requirements

- Local/open-source code tasks can remain low risk.
- Tasks requiring credentials, private data, external writes, regulated domains, or sensitive security changes should require explicit human review metadata.
- Risk gating should affect task readiness, not core serialization.
- Docs should connect this to Faber's first external pilot selection.

## Tests

- low-risk local task is ready
- credential-requiring task is blocked without review
- private-data task is blocked without review
- risk flags appear in task contract digest
- risk review can approve a task with explicit metadata

## Acceptance criteria

Faber can choose safe early tasks and avoid accidentally incentivizing risky autonomous work.