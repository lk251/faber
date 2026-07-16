# Work item 0080 — End-to-end `faber proof` CLI and evidence report

## Objective

Create the coherent product surface judges and Codex will use: one command from task
contract and candidate revision to a deterministic verdict and an immediately legible
evidence report.

This work item must turn the protocol, planner, catalog, and executors into a polished
vertical slice. Avoid exposing the underlying subsystem complexity to the user.

## Required context

Read the shared Build Week context and inspect:

- proof records and decision policy from 0077;
- live/replay planner from 0078;
- proof catalog, executors, and workflow from 0079;
- current CLI conventions and error formatting in `src/faber/cli.py`;
- attempt manifests, redaction, artifact validation, canonical output, and local store
  behavior;
- packaging configuration in `pyproject.toml`;
- existing customer-facing output and golden fixtures.

## Target command

Add a top-level CLI experience equivalent to:

```bash
faber proof \
  --repo . \
  --task .faber/task-contract.json \
  --catalog .faber/proof-catalog.json \
  --base HEAD~1 \
  --candidate HEAD \
  --mode replay \
  --replay .faber/replays/gpt56-proof-plan.json \
  --out-dir .faber/proof
```

Support at minimum:

```text
--repo
--task
--catalog
--base
--candidate
--mode live|replay
--replay
--model gpt-5.6
--critic-count 0|1
--max-diff-bytes
--out-dir
--json
--dry-run
--open-report
```

A nested parser or a hyphenated compatibility command is acceptable, but the documented
entrypoint must be `faber proof` through a console script.

Target exit codes:

```text
0  PASS
1  BLOCK
2  HUMAN_REVIEW or operational failure
```

Machine-readable output must also include the explicit verdict and reason codes so
callers do not need to infer meaning from the process status alone.

## Repository context collection

Implement a deterministic Git context collector that:

- validates the repository root;
- resolves base and candidate revisions to full commit IDs;
- rejects an invalid or ambiguous revision;
- obtains a bounded unified diff without network access;
- normalizes paths and line endings for digest purposes;
- records changed file names and bounded statistics;
- excludes `.git/`, `.faber/` output, known generated artifacts, and policy-defined
  paths from context;
- applies secret detection and redaction before model request construction;
- enforces `--max-diff-bytes` before a provider call;
- emits a stable diff digest and context manifest;
- handles an empty diff explicitly;
- behaves consistently on Linux, macOS, and Windows.

Do not use GitHub APIs or require a remote. Use local Git.

When the diff is too large, fail closed with a useful next step or use a deterministic
policy-approved summary mode. Do not silently truncate in a way that changes the task's
meaning without recording it.

## Input loading and binding

Load and validate:

- task contract;
- attempt or generated attempt binding;
- proof catalog;
- planner mode and replay bundle;
- execution policy;
- revisions and diff digest.

If an attempt is generated for this workflow, bind it explicitly to the task, worker
identity used for the demo, base/candidate revisions, environment evidence, and diff
artifact. Do not create a fake accepted receipt before proof execution.

Every generated artifact must refer to the exact same task, attempt, revisions, catalog,
and diff.

## Workflow behavior

### Normal run

1. Collect and redact repository context.
2. Build the proof-planning request.
3. Obtain and validate the live or replay plan.
4. Resolve and execute approved proof obligations.
5. Create verifier runs, receipts, proof evidence, and aggregate decision.
6. Validate the complete artifact graph.
7. Write machine-readable artifacts.
8. Generate Markdown and self-contained HTML reports.
9. Print a concise human result or canonical JSON.
10. Return the defined exit status.

### `--dry-run`

- Collect context and obtain or replay the plan.
- Validate catalog selections and parameter schemas.
- Do not execute proof obligations.
- Produce a plan report clearly labeled `DRY RUN — NO VERDICT`.
- Return success only when planning and validation succeeded; never label it `PASS`.

### Operational failures

Map configuration, Git, input, planning, replay, execution, and report errors to stable
categories. Human output should use the repository's existing pattern:

```text
Failed: ...
Why it matters: ...
Next step: ...
```

Do not emit a green or successful-looking report after an incomplete workflow.

## Artifact bundle

Write a deterministic directory structure similar to:

```text
<out-dir>/
  context.json
  redaction-report.json
  planning-request.json
  model-run-evidence.json
  proof-plan.json
  proof-catalog.json
  proof-evidence/
  verifier-runs/
  verification-receipts/
  proof-decision.json
  run-summary.json
  report.md
  report.html
```

Avoid writing the raw unredacted diff by default. The context artifact should contain
the bounded redacted content or a policy-approved summary plus its digest.

`run-summary.json` should be the stable machine entrypoint and contain:

- status and verdict;
- task and attempt identifiers;
- base and candidate revisions;
- all important digests;
- model and mode;
- obligation counts;
- failed and missing claim IDs;
- paths to bundle artifacts;
- total latency and known model usage/cost metadata;
- validation status;
- disclosure that local execution is not a production sandbox.

Use relative paths inside the bundle when practical so it remains portable.

## Report design

Generate both Markdown and one self-contained HTML document. The HTML must require no
external JavaScript, stylesheet, font, image, or network request.

### Above the fold

The first viewport must communicate within five seconds:

- a large `PASS`, `BLOCK`, or `HUMAN REVIEW` state;
- task title;
- candidate revision;
- one-sentence verdict reason;
- the failed claim and concrete counterexample when blocked;
- GPT-5.6 model identity and `LIVE` or `REPLAY` label;
- required, passed, failed, missing, and uncovered counts;
- exact reproduction command.

A blocked report should make the counterexample the visual focal point. A passing
report should make complete evidence coverage immediately visible.

### Model analysis section

Show:

- concise claim decomposition;
- severity;
- requirement linkage;
- selected proof entries and rationale;
- critic findings when present;
- uncovered risks and human-review recommendation;
- a clear `ADVISORY` label.

Do not display private chain-of-thought or imply that rationale is proof.

### Authoritative evidence section

Show:

- proof claim and approved catalog entry;
- validated parameters as bounded data;
- executor or verifier identity and version;
- expected and observed summaries;
- counterexample;
- status, duration, and bounded metrics;
- verifier-run, evidence, and receipt digests;
- stable reason codes;
- a clear `AUTHORITATIVE EVIDENCE` label where applicable.

### Audit section

Show:

- task, attempt, revisions, diff, catalog, request, response, plan, evidence, receipt,
  and decision digests;
- prompt and schema versions;
- replay validation status;
- redaction summary;
- token, latency, and cost information when available;
- runtime-boundary disclosure;
- no-key replay instructions.

### Accessibility and legibility

- Use semantic headings and tables or definition lists where suitable.
- Ensure verdict and status are not communicated by color alone.
- Use system fonts.
- Keep contrast and print readability strong.
- Avoid animation, auto-playing media, or hidden critical evidence.
- Keep generated markup deterministic enough for snapshot tests.

Use only standard-library rendering or a very small justified dependency. Prefer no new
runtime dependency.

## Console output

Default human output should be concise and demo-friendly, for example:

```text
Faber Proof: BLOCK
Task: Preserve the final report at budget exhaustion
Candidate: <short-sha>
Ordinary test verifier: PASS
Failed claim: A complete composed result is returned when the final budget unit is used
Counterexample: budget=3, observed=None, expected="summary"
Report: .faber/proof/report.html
```

JSON mode should print one canonical object and no decorative text.

## `--open-report`

Opening a local report is convenience only:

- generate the report first;
- use a standard-library browser opener;
- do not treat failure to open a browser as proof failure;
- disable or ignore this option safely in noninteractive environments;
- never start a server merely to view the report.

## Tests

Cover at minimum:

### Git context

- valid base/candidate resolution;
- invalid revision;
- empty diff;
- path normalization and spaces;
- line-ending stability;
- oversized diff;
- excluded output paths;
- secret redaction;
- deterministic context digest;
- no network or remote requirement.

### CLI

- replay `PASS`, `BLOCK`, and `HUMAN_REVIEW` exit statuses;
- live mode without optional SDK;
- live mode without API key;
- replay option requirements;
- dry run never reports `PASS`;
- JSON output is parseable and isolated;
- human error messages contain failure, significance, and next step;
- output directory creation and safe overwrite behavior;
- partial failure does not leave a misleading complete summary;
- repeated replay is idempotent.

### Reports

- snapshot or golden checks for pass, block, review, and dry-run reports;
- failed claim and counterexample above the fold;
- model/evidence authority separation;
- all important digests present;
- no external asset references;
- no raw secret-like value;
- bounded large observations;
- deterministic markup for fixed input;
- HTML parses and opens as a local file;
- Markdown and HTML agree with the decision artifact.

### Artifact graph

- all records bind to the same task, attempt, revisions, diff, catalog, and plan;
- missing or tampered artifact fails validation;
- receipt/evidence mismatch;
- portable relative paths;
- run summary accurately reflects counts and verdict.

## Packaging entrypoint

Add or prepare a proper build-system configuration and console script so a later clean
installation can invoke:

```text
faber
```

Do not break `python -m faber.cli`. Full wheel and CI hardening is completed in 0082.

## Constraints

- No original demo project or Codex repair skill yet; those are 0081.
- No external hosted service.
- No raw unredacted diff persistence by default.
- No report content may override the decision artifact.
- No settlement or marketplace behavior.
- Do not expand scope to a dashboard or web application.

## Acceptance criteria

- A replay fixture can run end to end from local Git revisions to a valid proof bundle.
- Exit codes and JSON verdicts agree.
- The HTML report is self-contained and makes a block counterexample visible in the
  first viewport.
- All artifact bindings and digests validate.
- Operational or incomplete workflows cannot produce a misleading `PASS` report.
- The console script and module invocation both work in the development environment.
- Full tests, lint, mypy, and available Nix checks pass.
- `codex/build-week/STATUS.md` records the commit and marks 0081 as next.

## Commit

Use one focused commit similar to:

```text
Implement work item 0080 Faber Proof CLI and report
```