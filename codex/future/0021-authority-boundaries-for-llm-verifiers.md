# 0021 - Authority Boundaries For LLM Verifiers

## Goal

Harden authority boundaries for LLM and probabilistic verifiers.

## Scope

Make it impossible for advisory verifier scores to release settlement unless the
verifier is explicitly approved as authoritative for the task contract or task
class.

Add verifier authority levels:

- advisory;
- ranking;
- progress;
- authoritative;
- human-review;
- hard-test.

## Requirements

- Do not add real model APIs.
- Settlement must require an accepted authoritative receipt.
- Advisory probabilistic scores can influence selection and routing, but not
  payment by default.
- Ranking verifiers can select candidates but cannot settle.
- Authoritative verifiers can settle only when the task contract permits them.
- Human-review and hard-test receipts remain valid authority paths.
- Update docs.

## Tests

Add tests proving:

- advisory score cannot trigger payout;
- ranking verifier can select a candidate but not settle;
- authoritative verifier can settle only when task contract permits it;
- human and hard-test receipts remain valid authority paths.

## Acceptance Criteria

- Settlement code fails closed when authority is absent or ambiguous.
- Authority level is visible in protocol records and docs.
- Existing hard verifier receipt behavior remains valid.
