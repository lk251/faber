# 0017 - Multi-Attempt Selection Loop

## Goal

Add a local multi-attempt selection loop for Faber tasks.

## Scope

Given one `TaskContract` and multiple `Attempt` records, select the best candidate
using:

- hard verifier results when available;
- probabilistic verifier scores when hard verification is absent or expensive;
- router and cost metadata;
- explicit policy configuration.

## Requirements

- Do not add real model APIs.
- Do not settle payment automatically from advisory verifier scores.
- Produce an auditable selection record.
- Selection records must include:
  - task contract id and digest;
  - candidate attempt ids;
  - selected attempt id;
  - selection policy;
  - verifier score records;
  - budget used;
  - why rejected alternatives lost.

## Tests

Add tests showing:

- hard accepted verifier dominates advisory score when authoritative;
- advisory ranking can choose among unverified candidates;
- rejected attempts remain useful training data;
- selection records are exported into trajectories or datasets.

## Acceptance Criteria

- Selection is auditable, deterministic under fixture backends, and provider-free.
- The selection path cannot bypass settlement authority requirements.
