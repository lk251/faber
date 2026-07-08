# 0006 — Verifier registry and local runner

## Goal

Make verifiers first-class objects. Add a registry and a deterministic local runner path that can execute approved verifier commands and emit `VerifierRun` records.

This issue should improve the path from task contract to authoritative receipt without depending on GitHub, payments, or model providers.

## Scope

Add a local verifier subsystem around:

- verifier definitions
- verifier registry
- approved command specs
- local execution policy
- result capture
- digest binding
- receipt creation

## Requirements

1. Add a `VerifierSpec` dataclass or equivalent with:
   - verifier id
   - name
   - version
   - description
   - command template
   - working directory policy
   - allowed timeout seconds
   - expected output convention
   - digest
2. Add a `VerifierRegistry` that can register, list, and resolve verifier specs by id.
3. Add a local runner that can run an approved verifier spec using the Python standard library.
4. Capture:
   - exit code
   - stdout/stderr digests
   - elapsed time
   - pass/fail result
   - structured metrics when available
5. Convert successful local runner output into `VerifierRun` and then `VerificationReceipt` using existing core paths.
6. Keep candidate-owned commands separate from platform/repo-owner-approved verifier specs.
7. Add simple timeout behavior.
8. Add docs explaining that this is a development runner, not a complete production sandbox.
9. Do not execute arbitrary unregistered commands from task metadata.
10. Do not add Docker or container requirements.

## Craftsmanship bar

The runner should make the trust boundary obvious in code and docs. It should be small, safe by default, and easy to replace later with stronger isolation.

## Tests

Add tests for:

- registering and resolving verifier specs
- verifier spec digest stability
- local verifier success
- local verifier failure
- timeout behavior if practical
- stdout/stderr digest capture
- unregistered command rejection
- receipt creation from an approved verifier run

## Acceptance criteria

- Verifiers are first-class registered objects.
- The local runner emits trustworthy `VerifierRun` records.
- Receipts can be generated from approved verifier runs.
- Trust boundary is documented.
- Existing tests still pass.
