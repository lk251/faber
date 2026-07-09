# 0052 — GitHub budget markers and funded issue protocol

## Goal

Represent funded GitHub issues in a machine-readable, provider-agnostic way before integrating any real payment provider.

## Scope

Add marker/protocol concepts for:

- funded issue marker
- work budget marker
- funding source reference
- budget allocation policy
- verifier spend budget
- trace-quality bonus policy

## Requirements

- No real payment provider integration.
- Marker should be robust when embedded in issue bodies or comments.
- Marker should bind to task contract id/digest and budget id/digest.
- Support budgets for issue, label, milestone, repository, and verifier compute.
- Add fake GitHub adapter tests for rendering and parsing markers.
- Budget marker cannot authorize payout by itself; settlement still requires authoritative verification.

## Tests

- render/parse funded issue marker
- digest mismatch is detected
- fake GitHub issue becomes task contract plus work budget
- duplicate marker is idempotent
- budget marker alone cannot settle work

## Acceptance criteria

Faber can model the user-facing idea “fund this issue” without creating payment-provider lock-in or custody assumptions.