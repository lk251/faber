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

`WorkBudgetLedger` provides exact local accounting. Every registration,
reservation, release, and settlement requires an idempotency key and appends a
budget event. When a local store path is supplied those events are persisted as
canonical protocol records. Duplicate operations return the original result;
reuse of a key with different content is rejected.

Settlement splits worker payout, verifier cost, platform margin, and optional
trace-quality bonus in integer minor units. Splits must sum exactly to the
reservation. A bonus requires both an allocation policy and trajectory-quality
evidence. Rejected or expired attempts release reservations according to the
explicit refund policy. Reconciliation reports explain opening, active reserved,
settled, released, available, and per-split balances.

Funding-source adapters should emit provider-tagged `FundingEvent` records.
Those records can be reconciled idempotently into `FundingSource` and
`WorkBudget` objects. Adapter records are audit evidence, not custody,
compliance, or payment-processing claims.

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

The fake GitHub adapter can render a `faber:funded-issue` marker that binds the
task contract id/digest, work budget id/digest, opaque funding-source reference,
allocation policy, verifier-spend allocation, and trace-quality bonus policy.
Identical duplicate markers are idempotent; conflicting or digest-mismatched
markers are rejected. A marker is public protocol evidence only. It never grants
settlement authority, which still comes from the accepted authoritative receipt.

## Evidence and payout eligibility

Work budgets may declare trajectory quality requirements. A task can accept
PR-only work for settlement, require manifest or trace evidence for full payout,
or reserve bonuses for RL-grade or replayable episode packages.

Richer evidence affects payout eligibility and reputation, not the authority of
settlement. Settlement still requires authoritative verification through the task
contract's verifier policy, and no payment-provider integration is part of the
core protocol.

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

Before funding or agent execution, external work should pass the lightweight
risk review in `docs/RISK_REVIEW.md`, especially when credentials, private data,
external writes, regulated domains, security-sensitive repositories, or payment
provider assumptions are involved.

## Customer delight

A maintainer should be able to see how much budget exists, what task it funds, which verifier policy protects acceptance, which worker got paid, what evidence justified payout, and what happened to unused funds.
