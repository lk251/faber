# 0011 — Trust boundary and runner safety

## Goal

Harden the local runner and verifier boundary so the code clearly separates candidate-owned inputs from platform/repo-owner-approved verifier policy.

This issue should be honest about local limitations while making unsafe behavior harder to introduce accidentally.

## Scope

Improve safety around:

- verifier specs
- runner execution policy
- path handling
- environment variables
- command approval
- timeout behavior
- result capture
- docs and tests

## Requirements

1. Add a `RunnerPolicy` or equivalent explicit policy object.
2. Policy should describe:
   - allowed working directory root
   - whether network isolation is provided; for local runner, state clearly that it is not complete isolation
   - allowed environment variables
   - timeout seconds
   - maximum stdout/stderr capture length if implemented
   - whether shell execution is allowed; prefer no shell by default
3. Refuse path traversal outside approved roots where practical.
4. Avoid `shell=True` for verifier commands unless explicitly justified and blocked by default.
5. Ensure verifier commands come from registered verifier specs, not task or PR metadata.
6. Add structured runner result records with digests, not giant raw logs in core records.
7. Add docs explaining local runner threat model and production replacement path.
8. Do not add Docker, Firecracker, Kubernetes, or cloud-specific sandboxing in this issue.

## Craftsmanship bar

Safety claims must be precise. Do not imply the local runner is a production sandbox. The code should make the safe path the easy path.

## Tests

Add tests for:

- command list execution without shell
- rejected unregistered command
- rejected path outside allowed root
- timeout result
- stdout/stderr digest capture
- local runner policy serialization/digest
- docs include explicit local-runner limitation

## Acceptance criteria

- Runner policy is explicit and tested.
- Verifier execution path respects registered specs.
- Local limitations are documented honestly.
- Existing tests still pass.
