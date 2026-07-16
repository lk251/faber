# Work item 0081 — Codex skill and original winning demonstration

## Objective

Create the competition's decisive end-to-end experience:

1. a repository-scoped `$faber-proof` Codex skill;
2. an original demonstration where ordinary tests stay green but Faber Proof blocks a
   subtle AI patch with a concrete counterexample;
3. an evidence-driven Codex repair followed by a Faber Proof pass;
4. a one-command, no-key replay path that generates both judge-facing reports.

This is the point where Faber Proof must become memorable rather than merely correct.

## Required context

Read the shared Build Week context and inspect all implementation from 0077 through
0080. Also verify the current official Codex skills format and repository discovery
rules before finalizing `.agents/skills/faber-proof/SKILL.md`.

## Part A — Repository-scoped Codex skill

Create:

```text
.agents/skills/faber-proof/
  SKILL.md
  references/
  scripts/
```

Only add optional metadata files when supported by current Codex documentation and when
they improve discovery without adding fragile assets.

### Frontmatter

Use valid required frontmatter with:

```text
name: faber-proof
```

Write a precise description that causes Codex to select the skill when asked to prove,
verify, audit, or repair an AI-generated patch with Faber Proof. Do not make it trigger
for every ordinary test request.

### Skill behavior

The skill must instruct Codex to:

1. Read the Faber Proof task contract and proof catalog.
2. Inspect repository state, base revision, candidate revision, and working tree.
3. Preserve unrelated user changes.
4. Invoke `faber proof` with an explicit live or replay mode.
5. Treat GPT-5.6 analysis as advisory and Faber evidence as authoritative.
6. Read `run-summary.json` and `proof-decision.json`, not infer verdict from prose.
7. When the verdict is `BLOCK`, identify the failed claim and concrete counterexample.
8. When the user has requested repair, make the smallest code change that satisfies the
   failed claim without weakening the task, catalog, proof policy, ordinary tests, or
   unrelated behavior.
9. Never edit the proof catalog, replay bundle, task contract, or expected evidence
   merely to turn a failure green unless the user explicitly asks to redesign policy.
10. Run ordinary tests and Faber Proof again after the repair.
11. Stop at `HUMAN_REVIEW` rather than claiming success.
12. Report exact commands, revisions, verdict, evidence path, and remaining limitations.

The skill must explicitly forbid:

- treating model rationale as proof;
- bypassing a required obligation;
- changing a test expectation to match the defect;
- replacing authoritative evidence with a model score;
- using a replay bundle that does not bind to the current task and diff;
- claiming production sandbox isolation;
- modifying unrelated files silently.

### Live versus replay repair behavior

In live mode, Codex may rerun the planner after changing the diff.

In replay mode, a replay bundle is valid only for its recorded request digest. The
original demonstration therefore provides separate reviewed replay bundles for the bad
and repaired revisions. Outside that fixture, the skill must not reuse a stale replay
after a patch changes; it should request live mode or stop with a precise human action.

### Invocation examples

Document concise examples such as:

```text
$faber-proof prove the current patch against .faber/task-contract.json
```

```text
$faber-proof run the Build Week replay demo and explain why the first patch is blocked
```

```text
$faber-proof use live GPT-5.6 to prove this patch, repair only demonstrated failures,
and rerun the proof
```

### Skill verification

Add a repository script or documented check that confirms:

- required frontmatter is present;
- referenced files and commands exist;
- the skill does not contain stale paths;
- its replay example runs without an API key.

Do not attempt to automate Codex's proprietary UI. Record one manual discovery check in
the status file when Codex loads the repository.

## Part B — Original demonstration project

Create an original, small Python project under a path similar to:

```text
examples/build-week-proof/
  README.md
  source/
  ordinary-tests/
  task-contract.json
  proof-catalog.json
  revisions/
  replays/
  expected/
  scripts/
```

The demonstration must be fully owned by this repository and must not depend on the
Hermes project, another third-party repository, external services, trademarks, or
accounts.

### Scenario

Use a compact scheduler or bounded conversation loop that composes a final report over
several turns.

The task contract requires all of these behaviors:

1. When a complete final report is produced on the last permitted turn, preserve and
   return it even though the budget is now exhausted.
2. Empty, incomplete, cancelled, or unrelated failed runs remain explicit failures.
3. Ordinary early-completion behavior remains unchanged.
4. The patch must not broadly suppress scheduler failures.

### Original base

Create a clear baseline implementation and ordinary test suite. The test suite should
cover:

- completion before the budget boundary;
- incomplete run failure;
- cancellation or another normal rejection path;
- deterministic report composition.

It intentionally does not contain the exact last-permitted-turn proof case.

### Bad AI patch

Create a realistic, minimal candidate patch that appears to satisfy the task and keeps
all ordinary tests green, but loses the complete report when completion occurs on the
exact final permitted turn.

The defect should be understandable in a short diff and should not depend on timing,
randomness, concurrency, or platform quirks.

Target counterexample shape:

```text
turn_budget: 2
responses: ["draft", "FINAL: summary"]
expected: "summary"
observed: null or an explicit failure
```

Exact names may differ. Keep the input small enough to display above the fold in the
report.

### Repaired patch

Create the smallest correct repair. It must:

- return the complete final report at the exact boundary;
- preserve incomplete and cancelled failures;
- keep ordinary tests green;
- avoid broad exception or failure suppression;
- satisfy the same proof obligations.

### Proof catalog

Provide a catalog with several plausible entries so GPT-5.6 must reason rather than
select the only available option. Include:

- ordinary regression test verifier;
- a parameterized approved `python-call` entry capable of exercising the exact budget
  boundary;
- an incomplete-run rejection proof;
- one or more plausible but irrelevant alternatives, such as serialization or a
  different scheduler state;
- mandatory task-policy obligations.

The catalog must own all operational targets. GPT-5.6 supplies only bounded input and
expected values.

### GPT-5.6 replay bundles

Provide separate sanitized, reviewed replay bundles for:

- the bad candidate diff;
- the repaired candidate diff.

Each bundle must bind to its exact task, catalog, prompt, schema, and request digest and
must pass the same validation path as live mode.

Do not fabricate a response and describe it as a real GPT-5.6 result. The implementation
may begin with deterministic fake fixtures while credentials are unavailable, but the
status file must remain blocked at the human-only `capture live replay` gate until a
real guarded GPT-5.6 run has produced the final reviewed bundles.

Add a sanitization and review script that:

- removes no field needed for digest validation;
- verifies no secret-like values are present;
- records requested and returned model IDs;
- validates the final bundle before it can replace a fake fixture;
- makes the provenance state explicit: `fake-development` or `live-reviewed`.

The final submitted demo bundles must be `live-reviewed`.

## Part C — One-command demonstration

Add a command equivalent to:

```bash
faber demo proof --mode replay --out-dir .faber/build-week-demo
```

It must:

1. Create isolated temporary Git repositories or worktrees from the original fixture.
2. Materialize the bad candidate revision.
3. Run the ordinary test suite and record `PASS`.
4. Run Faber Proof with the matching bad replay bundle.
5. Validate that the result is `BLOCK` and contains the expected failed claim and
   counterexample.
6. Materialize the repaired candidate revision.
7. Run the same ordinary test suite and record `PASS`.
8. Run Faber Proof with the matching repaired replay bundle.
9. Validate that the result is `PASS` with no failed or missing required claim.
10. Write both complete proof bundles and reports.
11. Print one concise comparison and paths to the reports.

Target console moment:

```text
Faber Proof Build Week demo

                         BAD PATCH   REPAIRED PATCH
Ordinary tests              PASS          PASS
Faber Proof verdict        BLOCK          PASS
Failed required claims         1             0
Concrete counterexamples       1             0

Blocked report:  .../bad/report.html
Passing report:  .../repaired/report.html
```

Use stable labels and avoid depending on terminal color.

Add `--json` for a canonical comparison object. Add a matching `just` recipe when
consistent with the repository.

## Part D — Evidence-driven repair demonstration

Provide a documented live demonstration path for the primary Codex session:

1. Start from the bad candidate.
2. Invoke `$faber-proof` in live mode with GPT-5.6.
3. Show ordinary tests passing.
4. Show Faber Proof blocking the boundary claim.
5. Let Codex inspect the counterexample and make the narrow repair.
6. Rerun ordinary tests.
7. Rerun Faber Proof live against the new diff.
8. Show `PASS`.

Record exact commands and screen states in the example README so the final video can be
recorded without improvisation.

Do not automate or fake Codex's textual repair in the submitted evidence. The project
may include bad and repaired fixture revisions for deterministic replay, while the
video shows the actual Codex repair workflow.

## Part E — Committed sample reports

Generate and commit sanitized sample blocked and passing HTML reports under the example
only after the artifact generator is stable.

Requirements:

- They must be generated from the reviewed replay bundles.
- Include a generation manifest with command, source commit, generator version, and
  digests.
- Ensure no absolute local paths, user names, API keys, or private machine data appear.
- Regeneration must produce byte-identical output or documented deterministic fields.
- The reports supplement the runnable demo; they do not replace it.

## Tests

Cover at minimum:

- skill frontmatter and reference validation;
- skill replay command runs without credentials;
- original fixture license/ownership notice;
- bad and repaired revisions are distinct and deterministic;
- ordinary tests pass for both;
- bad replay validates only against the bad diff;
- repaired replay validates only against the repaired diff;
- stale replay after a changed diff is rejected;
- bad proof verdict is `BLOCK`;
- bad failed claim and concrete counterexample match the task boundary;
- repaired proof verdict is `PASS`;
- incomplete/cancelled behavior remains rejected after repair;
- one-command demo writes both bundles and reports;
- JSON and human comparison agree;
- committed sample reports contain no absolute paths or secret-like values;
- regeneration is deterministic;
- no network call in replay mode.

## Constraints

- Keep one original demonstration. Do not add unrelated showcases.
- Do not modify proof policy merely to force the expected demo result.
- Do not use a fake fixture as final live-model provenance.
- Do not require Codex, an API key, or network for the judge replay command.
- Do not claim that replay proves a newly changed diff unless its digest matches.
- Do not begin the optional arena.

## Acceptance criteria

- Codex discovers and can explicitly invoke `$faber-proof` from the repository.
- The no-key one-command demo produces ordinary-test `PASS` for both candidates,
  Faber Proof `BLOCK` for the bad candidate, and Faber Proof `PASS` for the repair.
- The blocked report contains the exact failed claim and bounded counterexample above
  the fold.
- The repaired report contains complete required coverage.
- Replay bundles are context-bound and provenance-labeled.
- A documented live Codex repair path exists.
- Full tests, lint, mypy, and available Nix checks pass.
- `codex/build-week/STATUS.md` records the commit, exact demo scorecard, provenance
  state, and marks 0082 as next or identifies the live-replay human gate.

## Commit

Use one focused commit similar to:

```text
Implement work item 0081 Faber Proof skill and demo
```

Before the primary implementation thread ends, remind Javier to run `/feedback` and
record the returned session ID. Do not invent it.