# 0061 — Worker reputation and value-per-euro scorecards

## Goal

Turn worker performance history into inspectable reputation and value-per-euro scorecards.

## Scope

Add scorecard objects for:

- worker success rate by task family
- accepted/rejected/abandoned attempts
- verifier failures
- review friction
- latency
- cost
- trace quality
- platform support
- value per euro

## Requirements

- Use trajectories and settlement/cost metadata as input.
- Distinguish self-attested metadata from observed outcomes.
- Do not expose private customer data in public scorecards.
- Support task-family-specific reputation.
- Include uncertainty or sample size.
- Router can use scorecard summaries later.

## Tests

- scorecard updates from accepted trajectory
- scorecard updates from rejected trajectory
- trace quality affects scorecard separately from success
- small sample size is represented
- private fields are not exported publicly

## Acceptance criteria

Faber can help buyers choose workers and help routers learn from reliable outcome history.