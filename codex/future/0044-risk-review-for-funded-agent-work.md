# 0044 — Risk review for funded agent work

## Goal

Add a lightweight risk review checklist for funded Faber tasks before real external pilots.

## Scope

Create docs and protocol flags that help classify task risk.

## Requirements

Risk review should cover:

- private data exposure
- credentials or account access
- external write actions
- legal or regulated domains
- security-sensitive repositories
- payment/provider assumptions
- maintainer consent and upstream norms
- trace privacy and redaction
- false accept risk
- reputational risk

Add task risk levels:

- local-only low risk
- open-source repo low/medium risk
- external-service risk
- private-data risk
- regulated-domain risk
- security-sensitive risk

## Tests

- low-risk local task passes
- task requiring credentials is flagged
- task with private data is flagged
- high-risk task cannot be marked ready without explicit review metadata

## Acceptance criteria

Faber can distinguish safe early bounties from tasks that require human review before funding or agent execution.