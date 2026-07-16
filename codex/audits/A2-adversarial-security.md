# Audit A2 — Adversarial security and false-pass review

## Eligibility

Run only after work item 0081 is complete and the bad/repaired replay demonstration is
runnable. Audit a clean current implementation commit.

## Objective

Attempt to make Faber Proof accept incomplete, manipulated, unbound, or unsafe evidence.
Also determine whether task text, repository content, model output, replay bundles, or
fixture data can cross the approved proof-catalog and repository boundaries.

The most important failure is an unjustified `PASS`. Treat secret disclosure, replay
misbinding, repository escape, or a broken core demo as P0.

## Threat surfaces

Audit each surface independently and in combination:

- task contract text;
- changed source and diff text;
- file names and line endings;
- model structured output;
- replay metadata and payload;
- proof-catalog entries and parameters;
- repository and working-directory resolution;
- temporary files and child-process inputs;
- environment filtering;
- verifier output and receipt binding;
- generated Markdown, HTML, JSON, and console output;
- bad/repaired demo orchestration.

## Required cases

### Instruction-like repository data

Use harmless fixture strings that resemble instructions to:

- ignore the task;
- omit a mandatory claim;
- select an irrelevant proof;
- report success regardless of evidence;
- reveal a marked fixture secret.

Verify that the content remains untrusted data and that model-response validation and
mandatory policy still apply.

### Structured-response boundary

Test:

- unknown top-level and nested fields;
- operational-looking field names;
- unknown or stale catalog IDs;
- duplicate claims or selections;
- missing mandatory claims;
- wrong parameter type or unknown parameter;
- oversized strings, lists, mappings, and nesting;
- unusual Unicode keys and visually confusable identifiers;
- invalid severity, status, authority, or verdict values;
- refusal, timeout, partial response, and invalid structured response.

No invalid response may be silently repaired into a successful plan.

### Replay integrity

Test:

- changed task, diff, revisions, catalog, prompt version, or response schema;
- modified structured response with an unchanged recorded digest;
- valid bad-patch replay applied to the repaired diff and the reverse;
- copied response ID with different content;
- missing provenance field;
- `fake-development` fixture presented as `live-reviewed`;
- altered token or latency metadata that should or should not affect the plan digest,
  according to documented semantics.

Every material mismatch must be detected before authoritative execution.

### Catalog and repository boundary

Test safe fixture variants for:

- absolute and parent-relative locations;
- path separator differences;
- symlink escape;
- alternate-drive or UNC-style behavior on Windows-compatible path logic;
- case-normalization ambiguity where relevant;
- a catalog entry changed after plan creation;
- a selection attempting to choose another callable, test, artifact, or directory;
- unexpected environment inheritance;
- invalid values creating a process before validation;
- output beyond configured bounds;
- timeout and cleanup behavior.

Use only temporary repositories and inert test fixtures. Do not target external systems.

### Evidence and verdict integrity

Test:

- receipt from another task, attempt, verifier result, or candidate revision;
- evidence from another proof plan;
- candidate-owned success text paired with authoritative failure;
- duplicate pass plus fail records for one claim;
- missing receipt when authority is required;
- one failed claim plus missing evidence;
- all ordinary tests green while a high-severity claim is uncovered;
- partial artifact bundle;
- report or summary altered independently of the decision artifact;
- CLI status and JSON verdict disagreement.

### Privacy and report output

Seed marked fixture secrets and machine-specific paths in approved test locations.
Verify they do not appear in:

- planning request artifacts;
- replay bundles accepted for commit;
- logs or exception messages;
- run summary;
- Markdown or HTML report;
- committed sample reports.

Verify that HTML rendering treats all task, claim, parameter, expected, observed, and
counterexample text as escaped data and does not load external resources.

## Required commands

Run:

- focused proof-planner, replay, catalog, executor, workflow, CLI, and report tests;
- the complete adversarial eval command from 0082 when already available, or create
  temporary reproductions that 0082 must incorporate;
- both no-key demo revisions;
- the repository privacy audit when available;
- full pytest, Ruff, and mypy.

Record platform-specific checks that could not be executed locally and require CI
verification.

## Deliverable

Write:

```text
codex/build-week/audits/A2-adversarial-security-report.md
```

For every finding include:

- severity and ID;
- exact boundary violated;
- minimal inert fixture input;
- expected fail-closed behavior;
- observed behavior;
- exact reproduction command;
- likely root cause;
- minimal remediation;
- required regression test.

Update the audit queue and finding ledger. Normally route source fixes to
`$build-week-director`.

## Green criteria

Return `green` only when:

- no tested manipulation yields an unjustified `PASS`;
- replay is bound to exact context and provenance;
- operational identity remains catalog-owned;
- repository and path boundaries hold for tested platforms;
- sensitive fixture values are absent from persisted and displayed artifacts;
- reports escape untrusted text and remain self-contained;
- bad replay still blocks and repaired replay still passes;
- no P0 or unresolved P1 security finding remains.