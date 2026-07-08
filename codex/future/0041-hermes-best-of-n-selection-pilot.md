# 0041 — Hermes best-of-N selection pilot

## Goal

Design a Faber pilot where multiple candidate attempts are produced for a small Hermes-related task and Faber selects the best candidate using hard verifier results and advisory ranking evidence.

## Scope

- multi-attempt fixture
- candidate selection record
- hard verifier dominance rule
- advisory ranking records
- trajectory export for accepted and rejected attempts

## Requirements

- Do not use real model APIs.
- Use deterministic fake attempts and fake advisory scores.
- Hard authoritative verifier wins over advisory score when available.
- Rejected attempts remain valuable training data.
- Selection record includes budget used, selected attempt, rejected alternatives, scores, and uncertainty.

## Tests

- hard accepted attempt wins
- advisory ranking chooses among unverified candidates
- rejected attempts export into dataset
- selection record digest is stable

## Acceptance criteria

Faber can demonstrate how multiple attempts on a real-style task become learning data, not just one accepted PR.