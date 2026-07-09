# 0069 — Data retention, deletion, and audit policy

## Goal

Define how Faber balances user deletion requests, privacy, audit receipts, settlement records, and training dataset integrity.

## Scope

Add docs/protocol concepts for:

- retention classes
- audit-critical records
- private trace deletion
- dataset withdrawal
- tombstone records
- digest-preserving deletion reports

## Requirements

- Distinguish deleting private trace content from preserving minimal audit receipts.
- Dataset export should be able to exclude withdrawn trajectories.
- Local mode should remain simple.
- Hosted mode implications should be documented as future work.
- Avoid legal claims; mark legal review needed.

## Tests

- withdrawn trajectory excluded from export
- audit receipt reference remains without private trace payload
- deletion report has stable digest
- training dataset manifest records excluded count

## Acceptance criteria

Faber has a principled path for privacy and auditability before collecting valuable traces.