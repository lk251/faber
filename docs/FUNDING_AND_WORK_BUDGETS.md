# Funding and work budgets

Faber should let people attach a work budget to useful tasks. A repository owner, user, sponsor, company, or community member should be able to fund a particular issue, feature, bug, task class, verifier, or project maintenance goal.

The product idea:

> People who care about a problem vote with dollars; Faber turns that support into a verified work budget for humans and agents.

## Core concepts

- `FundingSource`: where support came from.
- `WorkBudget`: funds allocated to a project, issue, task family, verifier, or maintenance goal.
- `BudgetAllocation`: a rule mapping budget to task contracts or verifier spend.
- `Pledge`: conditional support for a specific issue or outcome.
- `Reservation`: budget set aside for an accepted claim or attempt.
- `Settlement`: payout after authoritative verification.
- `RefundPolicy`: what happens when work is rejected, expired, or cancelled.

Payment providers remain adapters. The Faber core should model budgets, reservations, obligations, and settlement events without hardcoding any provider.

## GitHub issue funding

The GitHub product loop should eventually support:

- fund this issue
- fund this label or milestone
- fund repository maintenance
- fund verifier compute
- fund a best-of-N attempt tournament
- add a bonus for richer traces
- add matching funds from a project sponsor

A GitHub issue can become a task contract with a budget, verifier policy, trace requirement, and settlement rule.

## Existing funding surfaces to support later

Faber should be able to ingest or reconcile support from existing repo funding mechanisms where permitted:

- GitHub Sponsors
- repository `FUNDING.yml`
- Open Collective
- issue-funding tools
- memberships or grants
- enterprise maintenance budgets
- future payment providers through adapters

## Democratization angle

Funding should not only buy expensive frontier attempts. It should help discover high intelligence-per-euro paths:

- cheap worker plus strong verifier
- many cheap attempts plus candidate ranking
- specialist agent for a narrow task class
- human review when uncertainty is high
- premium model only when expected value justifies it

## Safety and trust

Funded work should start as provider-agnostic protocol and local ledger behavior. Real provider integrations need explicit adapters, clear terms, and review.

## Customer delight

A maintainer should be able to see how much budget exists, what task it funds, which verifier policy protects acceptance, which worker got paid, what evidence justified payout, and what happened to unused funds.