# 0034 — Work budgets and funded GitHub issues

## Goal

Add provider-agnostic work-budget objects so people can attach budget to issues, labels, milestones, repositories, verifiers, and task classes.

## Scope

Add protocol/domain objects such as:

- `FundingSource`
- `WorkBudget`
- `BudgetAllocation`
- `Pledge`
- `Reservation`
- `RefundPolicy`
- `BudgetEvent`

## Requirements

- No real payment provider integration.
- Use integer minor units only.
- A GitHub issue can have a work budget and verifier policy.
- Budget can fund solver payout, verifier spend, trace-quality bonus, or review budget.
- Budget reservations must be idempotent.
- Budget cannot be spent without authoritative verification.
- Unused/rejected/expired funds must have explicit policy states.

## Tests

- create issue work budget
- allocate budget to a task contract
- reserve budget for an attempt
- no payout without accepted authoritative receipt
- trace-quality bonus represented but not paid without policy
- refund/expiry path

## Acceptance criteria

Faber can model funded work without hardcoding any provider or turning the core into a payment processor.