# 0054 — Competition, claim, and multi-attempt market policy

## Goal

Define how Faber handles single-claim work, open competitions, best-of-N attempts, retries, and shadow attempts.

## Scope

Add market policy objects:

- `AttemptPolicy`
- `ClaimPolicy`
- `CompetitionPolicy`
- `RetryPolicy`
- `ShadowAttemptPolicy`
- `CandidatePool`
- `SelectionPolicy`

## Requirements

- Some tasks should allow one active claimant.
- Some tasks should allow multiple competing attempts.
- Some tasks should pay only accepted winner; others may pay verifier/review stipends.
- Multi-attempt tasks should record all failed/rejected attempts as training data when consent permits.
- Budget policy must limit spend.
- Selection policy should separate advisory ranking from authoritative acceptance.

## Tests

- exclusive claim rejects second active claimant
- open competition allows multiple attempts
- best-of-N selection records rejected alternatives
- budget cap limits verifier spend
- shadow attempt is training-only and cannot settle without policy

## Acceptance criteria

Faber can support both ordinary bounties and richer multi-agent competitions that generate valuable trajectory data.