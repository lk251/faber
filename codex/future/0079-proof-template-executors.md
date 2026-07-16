# Work item 0079 — Bounded proof catalog and safe executors

## Objective

Turn a validated advisory `ProofPlan` into authoritative, replayable evidence. The
catalog owns every executable capability. GPT-5.6 may select an approved capability and
provide schema-validated JSON values, but it may not create or alter that capability.

## Required context

Read the shared Build Week context and inspect the proof records, planner catalog
representation, `VerifierSpec`, `VerifierRegistry`, Faber Runner, verification receipts,
artifact validators, canonical digests, path validation, redaction, and runtime-boundary
documentation.

## Architecture

Add explicit provider-neutral modules similar to:

```text
src/faber/proof_catalog.py
src/faber/proof_executors.py
src/faber/proof_workflow.py
src/faber/proof_runtime_helper.py
```

Suggested records:

```text
ProofCatalog
ProofCatalogEntry
ProofParameterSchema
ProofExecutorRegistry
ProofExecutionPolicy
ProofExecutionResult
ProofWorkflowResult
```

The catalog must serialize canonically and have a stable digest. Each entry has an
immutable identifier and version.

## Authority boundary

A catalog entry owns all operational details, including the registered verifier,
approved test node, approved callable, approved artifact location, assertion family,
working-directory policy, timeout, output limit, and environment policy.

A model selection may contain only:

- catalog entry ID and version;
- claim ID;
- JSON-compatible values for fields explicitly declared by the entry;
- expected-behavior summary and rationale.

Untrusted values must never determine an executable identity, module name, callable
name, test location, filesystem location, environment-variable name, or working
directory. They must remain inert data after validation.

## Initial proof families

Implement only the families required for the winning vertical slice.

### `existing-command`

Run an existing `VerifierSpec` through Faber Runner.

- The catalog references the registered verifier ID and expected version or digest.
- Resolve only through `VerifierRegistry`.
- The plan cannot override invocation, directory, timeout, environment, shell policy,
  or authority.
- Bind the resulting `VerifierRun` and `VerificationReceipt` to `ProofEvidence`.

### `pytest-node`

Run one or more exact pytest node IDs owned by the catalog.

- The model selects the catalog entry, not the node text.
- Use a fixed Python module invocation with shell execution disabled.
- Capture bounded output digests, exit status, duration, and parsed metrics.
- Issue authoritative evidence through the receipt boundary.

### `python-call`

Call a catalog-approved module and callable with validated JSON inputs and a bounded
assertion.

- The catalog owns module, callable, import root, directory, timeout, argument schema,
  assertion set, and result serializer.
- Execute through a fixed Faber-owned helper in a child process.
- Pass validated values through a temporary JSON document or standard input.
- Import only the catalog-owned target.
- Use a minimal environment and bounded output.
- Support the small closed assertion set needed by the demo:

  ```text
  equals
  not_equals
  is_none
  is_not_none
  raises
  contains
  truthy
  falsey
  ```

- Serialize expected and observed values with explicit type, size, and nesting limits.
- On failure, record a bounded counterexample summary.

This remains development infrastructure, not a claim of production-grade sandboxing.

### `file-invariant`

Check a catalog-approved repository file or generated artifact.

- The catalog owns the normalized repository-relative location.
- Reject absolute locations, parent traversal, symlink escape, alternate-drive escape,
  and any location outside the allowed root.
- Support a small closed operation set:

  ```text
  exists
  absent
  digest_equals
  contains_literal
  excludes_literal
  valid_json
  json_pointer_equals
  ```

- Persist bounded observations and digests rather than full unbounded content.

### `artifact-validator`

Invoke an existing Faber artifact validator for a catalog-approved artifact kind and
location. Reuse current validation behavior and bind its result to stable proof reason
codes.

## Parameter validation

Implement a small dependency-light schema supporting only the necessary JSON types:

- bounded strings with optional enum or pattern;
- bounded integers;
- booleans;
- explicit null;
- bounded homogeneous lists;
- bounded mappings with a closed field set;
- exact required and optional keys;
- no unknown keys by default.

Validate every value before creating a temporary file or child process. Return stable
validation reason codes.

## Execution policy

Add an explicit policy binding:

- allowed repository root;
- allowed catalog digest;
- verifier registry identity or digest;
- maximum obligations;
- per-obligation and total time limits;
- maximum input and output sizes;
- environment allowlist;
- shell execution disabled;
- path and symlink policy;
- local-runner isolation disclosure;
- whether authoritative receipts are mandatory.

Reject an over-limit plan before execution.

## Workflow

Implement a provider-neutral function accepting the validated task, attempt, proof
plan, exact catalog, verifier registry, runner, and execution policy.

It must:

1. Verify that task, attempt, diff, and catalog digests bind to the plan.
2. Verify all mandatory obligations.
3. Resolve every selection to an exact catalog entry and version.
4. Validate all parameters before executing anything.
5. Execute in stable documented order.
6. Create one `ProofEvidence` record for each required outcome.
7. Create or bind authoritative receipts where policy requires them.
8. Represent missing, failed, timed-out, and operational-error states explicitly.
9. Invoke the pure decision policy from 0077.
10. Return a `ProofWorkflowResult` with plan, evidence, runs, receipts, decision,
    timings, and bounded diagnostics.

A failure must not erase already collected evidence. Continue only where safe and
within policy, and record whether execution was short-circuited.

## Counterexample format

Use a stable bounded representation containing:

```text
input_summary
expected_summary
observed_summary
exception_type
reason_code
```

Apply byte, nesting, and secret-redaction limits before persistence.

## Tests

Cover at minimum:

- stable catalog digest;
- duplicate or stale entries;
- catalog mismatch;
- malformed parameter schemas;
- attempts to add operational fields to a selection;
- attempts to choose an unapproved callable, test, or location;
- absolute, traversal, symlink-escape, and alternate-drive cases;
- unknown or oversized parameters;
- minimal environment behavior;
- invalid values create no child process;
- shell execution remains disabled;
- passing and failing existing verifiers;
- passing and failing approved pytest nodes;
- passing, failing, and raising approved Python calls;
- every supported assertion;
- bounded counterexample generation;
- file and artifact checks;
- timeout and output truncation;
- missing capability;
- receipt creation and binding;
- evidence bound to the wrong task, attempt, plan, or catalog;
- deterministic execution order and reason-code order;
- demonstrated failure plus later missing evidence follows the 0077 precedence;
- an operational error can never yield `PASS`.

Use original temporary fixtures. Tests require no network, Docker, or OpenAI key.

## Constraints

- No CLI or HTML report in this item.
- Model-provided text remains data and is never treated as operational configuration.
- Preserve the local runner's honest isolation limitations.
- Do not add Docker as a requirement.
- Do not invoke payments, settlement, marketplace, or external publication.
- Keep the language small and auditable.

## Acceptance criteria

- A valid plan resolves entirely through approved catalog entries.
- Untrusted values cannot alter executable identity or repository boundaries.
- Passing outcomes create authoritative receipt bindings where required.
- A failing approved Python call creates a bounded concrete counterexample.
- Missing capabilities, timeouts, and execution errors fail closed.
- The aggregate decision is deterministic.
- Full tests, lint, mypy, and available Nix checks pass.
- `codex/build-week/STATUS.md` records the commit and marks 0080 as next.

## Commit

Use one focused commit similar to:

```text
Implement work item 0079 bounded proof executors
```