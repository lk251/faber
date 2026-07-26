# Faber Proof adversarial evals

## Purpose

The Build Week eval campaign asks one release question:

> Can any covered untrusted-input, replay, execution, evidence, or artifact failure
> produce an unjustified `PASS`?

The suite is deterministic and table driven. Each case names one existing regression
assertion, its expected Faber verdict, stable reason codes, and the exact pytest node
that reproduces it. A linked test that fails, errors, or skips is recorded as
`NOT_EVALUATED`, which fails the campaign.

## Commands

Refresh the committed JSON and Markdown reports:

```bash
python scripts/run_build_week_evals.py
```

Verify a fresh successful run matches the committed reports byte for byte:

```bash
python scripts/run_build_week_evals.py --check
```

Run any individual case with the command in the generated report's `Reproduce` column.

## Current result

The current HB2 checkpoint result is:

```text
PASS: 49/49 cases
unjustified_pass_count: 0
suite digest: sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c
```

The complete case table, expected verdict, actual verdict, reason codes, and
reproduction command are committed in:

- `docs/generated/BUILD_WEEK_EVAL_RESULTS.md`
- `docs/generated/BUILD_WEEK_EVAL_RESULTS.json`

The digest covers the stable case manifest rather than wall-clock output.

## Verdict interpretation

- `BLOCK` means authoritative evidence demonstrated a task-contract failure. A known
  failed claim takes precedence over other missing evidence.
- `HUMAN_REVIEW` means evidence is unavailable, malformed, stale, operationally
  incomplete, contradictory, uncovered, or not bound strongly enough for authority.
- `PASS` is justified only by a positive control with complete passing authoritative
  evidence or by a deterministic normalization/privacy behavior whose expected result
  is explicitly safe.
- `NOT_EVALUATED` means the assertion did not complete successfully and fails the eval
  campaign.

Ordinary candidate tests are not authority. The campaign includes a case where
candidate-owned output claims success while authoritative proof fails.

## Coverage

### Untrusted repository content

- prompt-injection comments and instruction-like string literals remain labeled data;
- secret-like values are redacted and blocked from accepted artifacts;
- oversized diffs fail before a planner call;
- generated `.faber/` output is excluded; and
- Unicode and CRLF/LF normalization produce unambiguous bindings.

### Planner and replay

- unknown or stale catalog entries;
- extra and nested operational-looking fields;
- missing mandatory templates and duplicate claims/selections;
- malformed or oversized parameters;
- refusal, timeout, and invalid structured output;
- request, catalog, prompt, schema, model, and response-digest mismatch;
- cross-candidate replay reuse; and
- unsupported or contradictory critic configuration.

### Execution and evidence

- path traversal and symlink escape;
- missing or stale verifiers and capabilities;
- timeout, output truncation, and child-process operational error;
- wrong task, attempt, plan, selection, catalog, workflow, or policy binding;
- swapped receipts, duplicate evidence, and contradictory evidence;
- green ordinary tests with a high-risk uncovered claim;
- candidate success text versus authoritative failure;
- failure-versus-missing precedence;
- partial bundles; and
- repeated replay with stable plan, evidence, and decision digests.

### Privacy and positive controls

- a known-safe artifact set passes deterministically;
- secrets, machine paths, external assets, and raw-output markers fail without echoing
  their values;
- a complete authoritative proof passes;
- the original bad candidate blocks; and
- the repaired candidate passes.

## Limits

This is a curated deterministic adversarial campaign, not exhaustive fuzzing or a
formal proof. It demonstrates fail-closed behavior for the named threat classes and
keeps every case directly reproducible. The broader product limits are documented in
`docs/FABER_PROOF_THREAT_MODEL.md`.
