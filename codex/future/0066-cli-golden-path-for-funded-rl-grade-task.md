# 0066 — CLI golden path for a funded RL-grade task

## Goal

Add a local CLI walkthrough that creates a funded task, submits an RL-grade attempt, runs verification, settles locally, and exports the trajectory.

## Scope

Add composable CLI commands or improve existing ones:

- create task from template
- attach local work budget
- register worker
- generate attempt manifest
- write or ingest trace
- run verifier
- issue receipt
- settle locally
- validate trajectory
- export dataset

## Requirements

- Keep each command transparent.
- `just demo-funded-trajectory` may wrap the flow if deterministic.
- Use fake/local data only.
- Output IDs, digests, and file paths clearly.
- Do not add web UI, payment provider, or model provider.

## Tests

- full CLI golden path works in temp directory
- generated artifacts validate
- trajectory is RL-grade
- dataset export includes exactly the permitted record
- docs commands match implementation where practical

## Acceptance criteria

A developer can understand Faber's value in one local terminal session.