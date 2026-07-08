# 0040 — Faber attempt manifest generator for Hermes PRs

## Goal

Make it easy for a Hermes contributor or agent harness to attach a valid `.faber/attempt.json` to a PR.

## Scope

Add a small manifest-generation path that can be used with Hermes-style task attempts without depending on Hermes.

## Requirements

- Generate `.faber/attempt.json` from CLI inputs or local metadata.
- Include task contract id/digest, base revision, candidate revision, worker id, harness/model disclosure, runner version, environment digest, cost/latency, evidence level, and redaction policy.
- Validate generated manifest.
- Provide examples for Hermes Agent candidate tasks.
- No real GitHub API calls.
- No Hermes dependency.

## Tests

- generated manifest validates
- invalid required fields fail clearly
- digest is stable
- example Hermes manifest fixture validates

## Acceptance criteria

A solver can add structured Faber metadata to a Hermes-related PR with minimal friction.