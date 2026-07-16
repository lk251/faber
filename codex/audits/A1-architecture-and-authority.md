# Audit A1 — Architecture and authority

## Eligibility

Run only after work item 0079 is complete. Audit the current clean
`build-week/faber-proof` head.

## Objective

Determine whether Faber Proof preserves Faber's provider-neutral architecture and
creates a real authority boundary between GPT-5.6 planning and executable verification.
Find any path by which advisory data can become an authoritative verdict without the
required approved evidence.

## Required reconstruction

Before judging, trace and diagram the actual code path for:

```text
task + attempt + diff + catalog
        -> planning request
        -> model/replay response
        -> ProofPlan validation
        -> catalog resolution
        -> executor or VerifierSpec
        -> VerifierRun
        -> VerificationReceipt
        -> ProofEvidence
        -> ProofDecision
```

Reference exact modules, classes, and functions. Note where digests and IDs are checked.

## Questions to answer

### Provider boundary

- Can core proof records import the OpenAI SDK or provider-specific response types?
- Does base Faber import and run when the OpenAI SDK is absent?
- Is `gpt-5.6` configuration isolated to the OpenAI adapter and product defaults?
- Can another fake or replay backend implement the neutral planner interface?

### Advisory versus authority

- Is every model-originated plan explicitly advisory?
- Can a model score, confidence, rationale, or recommendation directly create `PASS`?
- Does every authoritative claim outcome bind to a registered verifier or approved
  proof executor and, where policy requires it, a `VerificationReceipt`?
- Can model output change authority classification?
- Can candidate-owned CI or report text substitute for authoritative evidence?

### Proof catalog boundary

- Does the catalog own operational identity, version, location, timeout, and policy?
- Can any untrusted value alter which capability runs?
- Does every selection bind to the exact catalog digest and entry version?
- Can the plan add an entry, omit a mandatory entry, or use an entry from another
  catalog?

### Record and digest integrity

- Do task, attempt, revisions, diff, request, catalog, plan, evidence, receipt, and
  decision bind consistently?
- Are IDs, timestamps, and ordering deterministic where claimed?
- Are duplicate, contradictory, stale, or cross-attempt records rejected?
- Are schema compatibility and existing receipt semantics preserved?

### Decision policy

- Is `PASS` possible only with complete required accepted evidence?
- Does demonstrated failure take the documented precedence over missing evidence?
- Do incomplete, invalid, refused, timed-out, or contradictory states produce
  `HUMAN_REVIEW` rather than accidental success?
- Are reason codes stable and inspectable?
- Can report generation or CLI exit handling disagree with the decision artifact?

### Scope and maintainability

- Did the implementation add a generic framework larger than the vertical slice needs?
- Did it accidentally couple proof behavior to settlement, marketplace, GitHub, Hermes,
  or trajectory training?
- Are explicit dataclasses and deterministic functions used consistently?
- Are new dependencies justified and optional where appropriate?
- Are runtime-isolation limitations stated honestly?

## Required tests and commands

Run the relevant full checks plus focused proof tests. Add temporary or narrowly scoped
reproductions for:

- a valid pass, block, and human-review path;
- a model plan with a high-severity uncovered claim;
- evidence with no required receipt;
- evidence from another plan or attempt;
- a selection from another catalog version;
- contradictory evidence;
- provider SDK absent;
- report or CLI attempt to present a different verdict.

Do not trust a unit test solely because it constructs objects through the same helper
being audited. Where practical, construct malformed serialized input at the public
boundary.

## Deliverable

Write:

```text
codex/build-week/audits/A1-architecture-and-authority-report.md
```

Include:

- exact commit;
- reconstructed authority flow;
- P0/P1/P2 findings;
- reproduction commands;
- minimal fixes;
- regression tests needed;
- verified controls with no finding;
- untested areas;
- verdict.

Update `codex/build-week/AUDIT_QUEUE.md` and its finding ledger. Normally leave source
fixes to `$build-week-director`.

## Green criteria

Return `green` only when:

- core remains provider-neutral;
- model output is structurally unable to define operational behavior or verdict
  authority;
- all required evidence bindings are enforced;
- fail-closed decision semantics are deterministic;
- existing receipt authority and schema compatibility remain intact;
- no P0 or unresolved P1 architecture finding remains.