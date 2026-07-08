# 0004 — Protocol validation and errors

## Goal

Add explicit validation and shared error classes for Faber Protocol objects so incorrect records fail early with useful messages.

## Scope

Core objects:

- `TaskContract`
- `Attempt`
- `VerifierRun`
- `VerificationReceipt`
- `Trajectory`
- `Settlement`
- `WorkerProfile`
- `RouterDecision`
- `MarketEvent`

## Requirements

1. Add `src/faber/errors.py` with a small hierarchy:
   - `FaberError`
   - `ValidationError`
   - `DigestMismatchError`
   - `ScopeError`
   - `SettlementError`
   - `VerifierError`
   - `ProtocolVersionError`
2. Add simple validation helpers. Avoid framework magic.
3. Validate essential invariants:
   - required IDs are non-empty strings
   - schema names are stable and non-empty
   - digest fields use the expected `sha256:` prefix where appropriate
   - list and dict defaults are safe
   - money fields use integer minor units
4. Keep metadata extensible. Do not over-validate arbitrary metadata dictionaries.
5. Add schema constants or helper functions to reduce copy/paste schema drift.
6. Update GitHub adapter code to use shared errors where it improves clarity.
7. Update `docs/PROTOCOL.md` with the validation philosophy.

## Tests

Add tests for:

- invalid digest strings
- empty IDs
- settlement failure type
- GitHub repository scope failure type if present
- metadata extension fields remaining allowed

## Acceptance criteria

- Shared error classes exist.
- Core object validation is explicit and tested.
- Error messages name the field and expected shape.
- Existing tests still pass.
- No heavy validation dependency is introduced.
