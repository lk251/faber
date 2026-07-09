# 0056 — Human review receipts and maintainer approval

## Goal

Represent human maintainer review as first-class verification evidence without making every task depend only on subjective review.

## Scope

Add or extend:

- `HumanReviewReceipt`
- `ReviewCriterion`
- `MaintainerApproval`
- `ReviewFrictionSignal`
- `ReviewOutcome`

## Requirements

- Human review can be authoritative when task policy allows it.
- Human review can also be advisory or supplementary.
- Record reviewer identity reference, timestamp, criteria, outcome, comments digest, and relationship to task/attempt.
- Do not store long private review text in core records by default; store digest/reference.
- Dataset export should include review outcome and friction signals when allowed.

## Tests

- human review can authorize settlement when task policy permits
- human review cannot override hard verifier when policy forbids it
- review friction affects trajectory metadata
- comments digest is stable
- private review text is not leaked into public export

## Acceptance criteria

Faber can combine deterministic verification, probabilistic verification, and human judgment cleanly.