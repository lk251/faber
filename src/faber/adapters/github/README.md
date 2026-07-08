# Faber for GitHub Adapter

This adapter translates GitHub evidence into Faber Protocol objects. GitHub is the
first integration, not the root abstraction.

The initial skeleton intentionally avoids real API calls. Future work should add a
fake client and contract tests before connecting live GitHub App behavior.

## Funding source boundary

GitHub funding support is represented as adapter-emitted `FundingEvent` records.
The adapter may describe future inputs such as Sponsors, `FUNDING.yml`, Open
Collective, issue-funding tools, grants, or enterprise budgets, but it does not
claim custody, compliance coverage, or payment execution. Core budget objects
turn those events into provider-tagged work budgets with idempotent reconciliation.
