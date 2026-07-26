# Faber Proof threat model

## Scope

This model covers the Faber Proof local product path implemented for Build Week:

```text
task + candidate diff
        |
        v
bounded planner request -> advisory proof plan
        |
        v
owner-approved catalog -> bounded local executors
        |
        v
verifier runs + receipts -> deterministic PASS / BLOCK / HUMAN_REVIEW
        |
        v
portable evidence bundle + self-contained report
```

It covers live planning through the OpenAI adapter, context-bound replay planning, the
local proof runner, the original bad/repaired demonstration, generated bundles, and the
guarded live-fixture capture transaction. It does not model Faber's future hosted
marketplace, payment adapters, or a production execution service.

## Security objectives

Faber Proof should:

1. Treat task text, repository content, diffs, model output, and replay files as
   untrusted data.
2. Prevent those inputs from defining executable commands, imports, source paths, proof
   authority, or the final verdict.
3. Bind every accepted plan, proof run, receipt, decision, and replay to the exact task,
   candidate, diff, catalog, prompt, schema, and policy context that produced it.
4. Fail closed when required evidence is missing, contradictory, truncated, stale,
   operationally incomplete, or bound to another context.
5. Keep known credentials, sensitive fixture content, and machine-specific paths out of
   accepted replay and report artifacts.
6. Prevent a partial or failed run from appearing to be a complete proof bundle.

## Assets

| Asset | Required property |
|---|---|
| Repository and candidate diff | Exact content and digest binding; generated `.faber/` output cannot influence planning |
| Task contract | Exact task identity, requirements, revisions, and digest |
| Owner proof catalog | Immutable entry identity, version, parameter schema, capability, and source commitment |
| Planner request | Bounded, redacted, canonical, and bound to prompt/schema/model/catalog/candidate |
| Planner response | Strict structured data only; raw response is bounded and non-authoritative |
| Replay artifact | Exact request/response/model/provenance bindings and response digest |
| Execution policy | Owner-selected workspace, capabilities, limits, and verifier registry |
| Verifier run and receipt | Exact task/attempt/plan/selection/catalog/result binding |
| Decision | Deterministic policy result derived from complete authoritative evidence |
| Evidence bundle and reports | Atomic, portable, complete, digest-valid, privacy-audited, and self-contained |
| Provider credential | Never serialized, logged, printed, committed, or required for replay |
| Reviewed live fixture | Installed only after both candidates validate and the complete transaction passes |

## Trust boundaries

### Candidate repository to planner context

Changed code, comments, strings, task text, and filenames may contain prompt injection,
secret-like values, generated output, unusual Unicode, or excessive input. The context
collector bounds the diff, normalizes line endings before digesting, excludes generated
`.faber/` paths, labels repository material as untrusted, and redacts known secret
patterns before serialization.

### Planner response to proof plan

GPT-5.6 is advisory. Its structured response can state claims and select existing
catalog entries with closed parameters. Strict parsing rejects unknown or extra fields,
operational-looking nested data, duplicate claims or selections, malformed values,
missing mandatory templates, refusals, and oversized output. Model output cannot add a
command, callable, import, source file, timeout, path, or verdict.

### Replay file to planner adapter

Replay is not trusted because it is committed. The adapter recomputes and compares the
request, task, diff, catalog, prompt, schema, requested model, returned model, and
structured-response digest. A bad-candidate replay cannot be used for the repaired diff
or vice versa. Replay and live responses pass through the same strict parser and plan
validator.

### Owner catalog to executor

The catalog is repository-owner policy, not candidate or model output. Entries use
closed parameter schemas, fixed capabilities, immutable source commitments, bounded
limits, and explicit versions. All selected entries are preflighted before any child
process starts. Missing, stale, duplicate, or mismatched entries stop the workflow.

### Local filesystem and process boundary

Catalog paths must remain repository-relative and inside the resolved workspace.
Absolute paths, traversal, drive/UNC forms, backslash variants, and symlink escapes are
rejected. Executors use fixed implementation paths, argument construction, timeouts,
input limits, output caps, and explicit error states. Timeout, truncation, registry
mismatch, missing callables, and child-process errors cannot become authoritative
success.

### Execution evidence to authority decision

Every selected outcome must carry the complete executor-created authority binding.
Faber verifies task, attempt, revisions, diff, plan, selection, catalog, workflow,
policy, verifier, result, and receipt commitments. Candidate-owned success text is only
signal. Duplicated, contradictory, swapped, relabeled, or incompletely bound evidence
cannot produce `PASS`.

The deterministic precedence is:

1. A demonstrated authoritative contract failure produces `BLOCK`.
2. Missing, uncertain, invalid, or operationally incomplete evidence produces
   `HUMAN_REVIEW`.
3. `PASS` requires complete passing evidence for every required obligation.

### Bundle to report consumer

Bundles are staged and validated before atomic replacement. The loader requires the
complete manifest and declared artifacts, recomputes digests, and rejects partial or
tampered output. Reports embed their styling and do not fetch external assets. Portable
recorded commands omit checkout and interpreter paths while retaining a digest of the
raw execution command.

### Live capture to committed replay fixture

The guarded wrapper checks the branch, clean tree, request bindings, catalog, prompt,
schema, model metadata, reviewer identity, privacy, ordinary tests, and material
`BLOCK`/`PASS` outcome. Bad and repaired responses are staged separately. Existing
fixtures are replaced only after the complete transaction succeeds; any error restores
or leaves them unchanged. A final offline replay verifies the installed fixtures.

## Attacker and failure goals

The deterministic adversarial campaign covers attempts to:

- instruct the model through diff comments or instruction-like string literals;
- leak a credential or sensitive fixture fragment;
- exceed request, parameter, process-output, or time limits;
- smuggle executable behavior in structured model fields;
- remove a mandatory claim or select an unknown/stale proof entry;
- poison replay context or reuse evidence across candidates;
- traverse outside the repository or follow a symlink escape;
- make missing verifiers, operational errors, or truncated output look successful;
- swap a receipt or evidence object from another task, plan, selection, or result;
- use candidate-owned claims to override authoritative failure;
- exploit duplicate, contradictory, missing, or uncovered evidence;
- load a partial bundle as complete; or
- introduce host-specific paths or external report assets into accepted artifacts.

The current generated campaign and reproduction commands are in
`docs/generated/BUILD_WEEK_EVAL_RESULTS.md`.

## Privacy audit

`faber audit-proof-artifacts` performs a deterministic bounded release audit for:

- common credential patterns;
- caller-supplied forbidden literals and SHA-256 hashes;
- supplied home, temporary-directory, and user-name values;
- absolute Windows and POSIX paths;
- fixture-marked sensitive fragments;
- external HTML assets; and
- raw or unbounded model/verifier output markers.

The audit reports finding classes, paths, and safe hashes without echoing a detected
secret. It runs before reviewed fixture installation and during clean-install/demo
validation.

This is not comprehensive secret discovery. It complements request redaction, bounded
capture, fixture-specific forbidden values, code review, and the rule that private
prompts and credentials are not proof evidence.

## Residual risks

- The local runner does not provide an operating-system, container, VM, network, or
  descendant-process sandbox. A repository-approved command still runs with the local
  user's permissions.
- Path checks and fixed launchers reduce accidental escape but do not defend against a
  malicious executable, interpreter, kernel, or dependency.
- Repository-owner catalog policy is trusted. A compromised owner catalog can approve
  a dangerous capability.
- Digests provide deterministic integrity and context binding, not identity,
  non-repudiation, or cryptographic signing.
- Local files can change between validation and process access on a hostile machine.
- The privacy scanner recognizes bounded patterns and supplied forbidden values; novel
  encodings or unknown secrets may evade it.
- A proof catalog establishes its declared obligations, not universal program
  correctness. Missing specifications remain a human/product risk.
- A reviewed model response can still propose weak claims. Mandatory owner obligations
  and deterministic evidence prevent unilateral acceptance, but proof quality depends
  on the task and approved catalog.
- The Build Week live-capture path still requires human review and a real provider
  credential. Current committed fixtures remain `fake-development`.

## Explicit non-claims

Faber Proof does not claim:

- production-grade sandboxing;
- comprehensive secret detection;
- that GPT-5.6 is an authority or verifier;
- that ordinary green tests prove the patch;
- that every bug can be expressed by the current proof catalog;
- universal correctness or freedom from vulnerabilities;
- that a replay is a new live model call; or
- that committed development fixtures have live-reviewed provenance.

## Future production controls

Production deployment should add immutable checkouts, isolated workers, network
deny-by-default policy, resource and descendant-process enforcement, signed owner
catalogs and receipts, stronger artifact attestations, dependency provenance,
revocation, independent privacy review, and audited multi-tenant credential handling.
These controls are intentionally outside the Build Week local vertical slice.
