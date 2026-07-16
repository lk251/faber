# Work item 0077 — Proof protocol records and deterministic decision policy

## Objective

Add the smallest provider-neutral protocol needed to represent proof-carrying patches:
claims, model planning evidence, bounded template selections, executable evidence, and
a deterministic aggregate verdict.

This work item must preserve existing Faber receipt authority. GPT-5.6 output is
advisory and must never become verification merely because it is well formed.

## Required context

Read the shared Build Week context and inspect the existing style in:

- `src/faber/schemas.py`
- `src/faber/contracts.py`
- `src/faber/attempts.py`
- `src/faber/verifiers.py`
- `src/faber/receipts.py`
- `src/faber/digests.py`
- `src/faber/validation.py`
- relevant golden and schema-compatibility tests

## Design target

Prefer one cohesive module such as `src/faber/proofs.py` plus focused tests. Split only
when the existing repository conventions make the separation clearly better.

Add schema constants for records equivalent to:

```text
faber.proof_claim.v1
faber.model_run_evidence.v1
faber.proof_template_selection.v1
faber.proof_plan.v1
faber.proof_evidence.v1
faber.proof_decision.v1
```

Names may change slightly for consistency, but semantics must not.

## Required records

### `ProofClaim`

Represent one falsifiable behavioral claim derived from the task contract.

Required semantics:

- stable ID;
- concise statement;
- severity from a closed set such as `low`, `medium`, `high`, `critical`;
- requirement references or acceptance-criterion references;
- whether executable evidence is required;
- optional risk rationale;
- no model confidence as authority.

### `ModelRunEvidence`

Represent auditable metadata for a live or replay model run.

Required semantics:

- provider adapter ID;
- requested model ID;
- returned model ID when available;
- response ID when available;
- prompt-template version;
- request digest;
- structured-response digest;
- schema version;
- mode: `live` or `replay`;
- latency and token usage when available;
- refusal or error state;
- no private chain-of-thought or hidden prompt content.

### `ProofTemplateSelection`

Bind one claim to a catalog-approved proof template.

Required semantics:

- claim ID;
- template ID and version;
- JSON-compatible parameters;
- expected behavior or assertion summary;
- rationale;
- explicit `authority="advisory"`;
- no command, source-code, dynamic-import, or arbitrary-path field.

Reject suspicious executable field names recursively, including at minimum:

```text
command
command_template
shell
script
source
python
code
executable
working_directory
cwd
path
```

A later executor may use catalog-owned paths or commands, but model selections cannot
carry them.

### `ProofPlan`

Bind the model's advisory plan to immutable task and patch context.

Required semantics:

- task contract ID and digest;
- attempt ID and digest;
- base and candidate revisions;
- diff digest;
- proof-catalog digest;
- prompt-template version;
- claims;
- selections;
- mandatory claim IDs or mandatory template IDs supplied by policy;
- uncovered claim IDs;
- explicit human-review recommendation;
- `ModelRunEvidence`;
- `authority="advisory"`;
- deterministic canonical ordering or validation that makes ordering unambiguous.

Validation must reject:

- duplicate claim IDs;
- selections referencing unknown claims;
- uncovered IDs referencing unknown claims;
- duplicate selections for the same claim/template pair unless explicitly supported;
- missing mandatory claims;
- non-JSON-compatible parameters;
- executable-looking fields;
- mismatched prompt versions or malformed digests;
- a plan that marks a high or critical evidence-required claim as covered without a
  selection.

### `ProofEvidence`

Represent one claim's execution outcome without replacing existing verifier records.

Required semantics:

- proof-plan digest;
- claim ID;
- selection digest;
- status from a closed set such as `passed`, `failed`, `missing`, `error`;
- approved verifier or proof-executor identifier and version;
- `VerifierRun` digest when a verifier ran;
- `VerificationReceipt` digest when authoritative evidence was issued;
- expected and observed summaries as bounded JSON-compatible values;
- counterexample summary when available;
- failure reason codes;
- no raw unbounded logs.

### `ProofDecision`

Represent the aggregate result.

Required semantics:

- proof-plan digest;
- task and attempt binding;
- evidence digests;
- verdict: `pass`, `block`, or `human_review`;
- deterministic reason codes;
- passed, failed, missing, and uncovered claim IDs;
- authoritative receipt digests;
- policy name and version;
- stable digest.

## Deterministic decision function

Implement a pure function that accepts a validated plan, validated evidence, and an
explicit policy and returns `ProofDecision`.

Minimum policy:

### `BLOCK`

- Any evidence-required claim has authoritative status `failed`.
- Any mandatory verifier or proof obligation demonstrates a contract violation.

### `HUMAN_REVIEW`

- Model run has refusal or terminal error.
- Required evidence is missing or errored.
- A high or critical evidence-required claim is uncovered.
- Evidence references do not bind to the plan.
- Required authoritative receipt digest is absent.
- Evidence is contradictory or duplicated incompatibly.
- The plan explicitly requires human review for a material gap.

### `PASS`

Only when:

- every evidence-required claim has exactly one accepted authoritative outcome or a
  policy-approved deterministic aggregation;
- all such outcomes passed;
- no mandatory claim is missing;
- no high or critical risk is uncovered;
- no terminal model or evidence error remains;
- every receipt and evidence digest validates.

Precedence must be deterministic. Demonstrated failure should produce `BLOCK` even when
other evidence is missing; otherwise incomplete evidence should produce
`HUMAN_REVIEW`. Document and test the precedence.

## Compatibility and serialization

- Follow existing explicit dataclass and validation style.
- Use stable canonical serialization and digest helpers.
- Keep money, provider, GitHub, and runtime details out of these records.
- Do not modify the existing `VerificationReceipt` schema.
- Register new schemas in the compatibility registry and add golden snapshots when
  required by existing repository policy.
- Keep list ordering stable and documented.

## Tests

Add focused unit and property-style cases covering at minimum:

- round-trip serialization;
- stable digest under repeated construction;
- valid minimal pass, block, and human-review decisions;
- demonstrated failure plus missing evidence precedence;
- unknown and duplicate claim references;
- mandatory claim removal;
- unknown severity or status;
- nested executable field rejection;
- malformed digest binding;
- high-risk uncovered claim;
- model refusal;
- evidence from another plan or attempt;
- duplicate/contradictory evidence;
- no receipt for evidence requiring authority;
- deterministic reason-code ordering;
- backward compatibility of existing schemas and fixtures.

Use fixed IDs and timestamps in digest tests.

## Constraints

- No OpenAI SDK or provider code in this item.
- No subprocess execution in this item.
- No CLI surface in this item.
- No settlement behavior.
- No arbitrary confidence threshold that can turn advisory model output into authority.
- Avoid a generic abstraction framework; implement only the records required by the
  Faber Proof vertical slice.

## Acceptance criteria

- New protocol records validate, serialize, and digest deterministically.
- The pure policy function cannot produce an unjustified `PASS` in the tested failure
  modes.
- Existing `VerificationReceipt` and verifier authority behavior remain unchanged.
- Existing full tests, lint, and mypy pass.
- New schema compatibility and golden tests pass.
- `codex/build-week/STATUS.md` records the commit and marks 0078 as next.

## Commit

Use one focused commit similar to:

```text
Implement work item 0077 proof protocol and policy
```