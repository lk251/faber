# Reference Extraction: agent-bounty-market

This note records the parts of `lk251/agent-bounty-market` that should influence Faber.
The old repository is a reference only. Do not copy its hackathon demo architecture, vendor
integrations, or domain-specific verifier code into Faber core.

## Concepts To Preserve

- The trusted orchestrator owns state transitions, idempotency, verifier receipts, and payout
  decisions.
- Candidate code can supply an implementation under test, but it cannot supply the authoritative
  acceptance policy.
- Verifier receipts must bind the exact task contract, attempt, base revision, candidate revision,
  verifier identity, verifier digest, result digest, and policy/backend metadata available at run
  time.
- Timeouts and malformed verifier output must be recorded as failed verifier runs, not as
  payout-eligible receipts.
- Candidate-owned checks, statuses, logs, or process output are observations only. They can inform
  review, but they cannot replace a Faber verifier receipt.
- Ledger operations use integer minor units, idempotency keys, append-only entries, and
  non-negative internal account checks.
- Settlement follows verification. Payout and split settlement require an accepted receipt, and
  replaying the same idempotency key must not double-pay.
- Crash recovery should prefer replaying completed deterministic records and retrying incomplete
  work instead of treating half-written state as accepted.

## Concepts To Avoid

- Do not make Faber core depend on a single payment provider, model provider, UI toolkit, cloud
  runtime, or container runtime.
- Do not port Motoko-specific verifier assumptions, TUI replay details, vendor demo bundles, or
  presentation scripts into Faber core.
- Do not treat a GitHub adapter event as an authoritative market state transition without a Faber
  protocol record behind it.
- Do not require a real network call, payment account, model provider credential, or production
  runner to exercise the local protocol path.

## Tests Added In Faber

`tests/test_reference_invariants.py` captures the current Faber equivalents:

- receipts bind a candidate revision and cannot silently authorize a different attempt revision;
- candidate-reported success is metadata only until an approved verifier produces a receipt;
- timed-out verifier runs are rejected and cannot drive payout;
- replaying a stored trajectory digest inserts one record;
- payout idempotency prevents double payment;
- runner policy records shell-free execution and rejects unapproved environment variables;
- runner policy digests are bound into verifier run metadata.
