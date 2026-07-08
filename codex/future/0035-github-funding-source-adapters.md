# 0035 — GitHub funding source adapters

## Goal

Plan provider-adapter boundaries so existing repository funding surfaces can fund Faber work budgets later.

## Scope

Add docs and stub interfaces for funding-source adapters.

Potential future sources:

- GitHub Sponsors
- repository `FUNDING.yml`
- Open Collective
- issue-funding tools
- membership or grant programs
- enterprise maintenance budgets
- future payment providers

## Requirements

- Do not integrate real providers yet.
- Add adapter interfaces only.
- Add local fake adapter fixtures.
- Reconcile external support into provider-tagged `FundingEvent`s.
- Map funding events into `WorkBudget` allocations.
- Preserve auditability and idempotency.
- Avoid compliance or custody claims.

## Tests

- fake funding source emits events
- duplicate events are idempotent
- funding event creates budget allocation
- repository-level funding can allocate to issue-level budgets by policy
- unknown provider is represented without core changes

## Acceptance criteria

Faber can later ingest existing repo funding mechanisms without changing the core budget model.