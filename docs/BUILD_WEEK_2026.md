# OpenAI Build Week 2026 — competition control

This document controls competition-specific decisions for Faber Proof. The official
rules and hackathon website remain the source of truth:

- https://openai.devpost.com/
- https://openai.devpost.com/rules
- https://openai.devpost.com/resources

Verify them again before final submission.

## Dates in Madrid time

- Submission work became eligible on **Monday, July 13, 2026 at 18:00 CEST**
  (9:00 AM Pacific Time).
- Submission closes **Wednesday, July 22, 2026 at 02:00 CEST**
  (Tuesday, July 21 at 5:00 PM Pacific Time).
- Judging runs from July 22 through August 5, 2026 Pacific Time.
- The project and judge access must remain available and free through the end of the
  judging period.

## Track

Submit only to **Developer Tools**.

Faber Proof is a testing, agentic-workflow, and software-supply-chain trust tool for
maintainers reviewing AI-generated patches. This is the most accurate category and the
clearest story.

## Eligibility boundary

Faber existed before the submission period. The rules allow a pre-existing project only
when it is meaningfully extended during the submission period and the entrant clearly
distinguishes prior work from new work.

The Build Week implementation must therefore:

1. Identify the latest commit before `2026-07-13T09:00:00-07:00`.
2. Create an annotated tag named `build-week-2026-baseline` at that commit.
3. Preserve dated, focused commits after the baseline.
4. Maintain an evidence table in `codex/build-week/STATUS.md` linking work items,
   commits, tests, and Codex sessions.
5. State plainly in the README which capabilities were pre-existing and which were
   added for Build Week.
6. Avoid claiming pre-existing protocol, marketplace, trajectory, runner, or verifier
   functionality as new competition work.

Do not rewrite or squash eligible history before submission.

### Recorded boundary

- Submission-period cutoff: `2026-07-13T09:00:00-07:00` (strictly before).
- Verified last pre-period commit: `64f775cfe2f622837bd9aaa40f6369aa22af1d80`
  (`Implement work item 0075 roadmap synthesis`, authored and committed
  `2026-07-09T21:45:20Z`).
- Annotated boundary tag: `build-week-2026-baseline`, verified locally at that commit.
- Build Week implementation branch starting commit:
  `c915523383dc58114bf748f7d7a64c1c398faaba`.
- Eligible commits before the focused 0076 completion commit: 28. The completion
  commit makes the baseline-to-branch range 29 commits.

The immediately older commits are work items 0074 and 0073, dated July 9. The first
commit after the baseline is `6d8c84b46daffc234b56238b28da903358f749c6`
(`Add machine transfer handoff`), authored and committed `2026-07-16T05:04:08Z`.
The local delta report is generated without network access by
`python scripts/build_week_delta.py`.

## Required submission artifacts

The final submission must include:

- A working project built with Codex and GPT-5.6.
- The Developer Tools category.
- An English project description.
- A public YouTube demonstration video shorter than three minutes.
- Spoken audio explaining what was built and how Codex and GPT-5.6 were used.
- A repository URL. A private repository must be shared with:
  - `testing@devpost.com`
  - `build-week-event@openai.com`
- A README with setup, sample data, test guidance, Codex collaboration, key human
  decisions, and GPT-5.6 usage.
- A `/feedback` Codex session ID from the thread where the majority of the core
  functionality was built.
- Installation instructions, supported platforms, and a judge-testable path that does
  not require rebuilding from scratch.
- Free, unrestricted judge access through the judging period.

Judges are not required to run the project and may judge only from the description,
images, and video. The video and evidence report must therefore carry the complete
story even when nothing is installed.

## Judging strategy

Stage one is pass/fail on viability, theme fit, and reasonable application of the
required technology. Stage two uses four equally weighted criteria. Technological
implementation is the first tie-break criterion.

### 1. Technological implementation

Target evidence:

- A direct `gpt-5.6` Responses API integration using structured outputs.
- A repository-scoped Codex skill that drives the product workflow.
- A primary Codex implementation thread covering most of the new core functionality.
- A bounded proof-template system in which model output is data, never executable
  source or shell commands.
- Deterministic canonical serialization and digest-bound proof evidence.
- Fail-closed verdict policy with meaningful adversarial tests.
- Live and replay modes sharing the same validation path.
- A clean install, full test suite, type checking, linting, and cross-platform evidence.

### 2. Design

Target evidence:

- One command or one Codex skill invocation from patch to verdict.
- A no-key, no-network replay demonstration.
- A polished self-contained HTML report whose first screen communicates verdict,
  failed claim, counterexample, model role, and verifier evidence.
- Clear recovery actions: repair the patch, rerun the proof, and compare reports.
- A coherent experience rather than a collection of protocol primitives.

### 3. Potential impact

Target argument:

- Real audience: maintainers and engineering teams adopting Codex and other coding
  agents.
- Real problem: ordinary green tests and confident model prose do not establish that an
  AI-generated patch satisfies the issue contract or covers the risky edge cases.
- Specific solution: convert the task and diff into explicit proof obligations, execute
  approved evidence, and block or escalate patches that cannot support their claims.
- Credible adoption path: local CLI and Codex skill first, CI/GitHub integration later.

### 4. Quality of the idea

The novelty claim is:

> Faber Proof creates proof-carrying patches for agentic software development. It does
> not ask a model whether its own patch is good; it requires an independent model to
> express falsifiable claims in a bounded proof language and then makes deterministic
> verifiers test those claims.

Avoid positioning the project as:

- another AI code review bot;
- another test generator;
- another CI wrapper;
- a broad marketplace demo;
- a vague agent safety framework.

## Winning demo narrative

The demo must have a visible reversal within the first minute:

1. Codex has produced a plausible patch.
2. The ordinary tests are green.
3. Faber Proof independently identifies the contract's risky boundary case.
4. A data-only proof probe produces a concrete counterexample.
5. The patch is blocked despite green ordinary tests.
6. Codex repairs the patch using the evidence.
7. The same proof reruns and passes.

The strongest visual moment is not a long architecture explanation. It is the report
changing from a red `BLOCK` with one exact failed claim to a green `PASS` with every
claim backed by evidence.

## Build-versus-buy decisions

### Direct GPT-5.6 adapter

Use the official OpenAI Python SDK as an optional dependency and the Responses API.
Default to the `gpt-5.6` alias, which routes to GPT-5.6 Sol. Use structured outputs and
record the model identifier returned by the API. Verify current SDK syntax against the
official OpenAI developer documentation when implementing.

### Replay mode

Replay is a first-class product mode, not a mock hidden from judges. A replay bundle
must bind the sanitized request digest, model response, schema version, prompt-template
version, and expected plan digest. The same validation code must handle live and replay
responses.

### No arbitrary model code

GPT-5.6 may produce:

- behavioral claims;
- severity and rationale;
- approved proof-template identifiers;
- JSON-compatible template parameters;
- expected results;
- coverage and uncertainty notes.

GPT-5.6 may not produce executable commands, Python source, shell fragments, dynamic
imports, or filesystem paths outside the allowed contract. Unknown fields and template
identifiers fail closed.

### Original demo only

The submitted demo uses an original small Python project created for Faber Proof. Do
not depend on the Hermes issue or another third-party repository, trademark, service,
account, or copyrighted asset.

## Scope exclusions until submission freeze

Do not spend P0 time on:

- real payments, funding, or custody;
- the Faber marketplace;
- training models from trajectories;
- production GitHub App permissions or webhooks;
- production sandbox claims;
- external upstream contributions;
- hosted user accounts;
- broad framework rewrites;
- arbitrary generated test execution;
- multiple unrelated demonstrations.

## Human-only compliance actions

The following cannot be completed solely by Codex and must be explicitly handed to
Javier with exact instructions:

- Request or redeem Codex credits before the resource deadline, if still available.
- Provide an API key for the guarded live smoke test.
- Run `/feedback` in the primary implementation thread and record the returned ID.
- Share the private repository with the judging addresses and verify access.
- Record and narrate the video.
- Upload the video publicly to YouTube.
- Complete and submit the Devpost form.

## Final freeze policy

After the final submission tag:

1. Run the complete clean-install and replay audit from the tagged commit.
2. Confirm the video, repository access, and all submission links in an incognito or
   otherwise clean context.
3. Do not change the submitted project after the deadline except where the official
   rules explicitly permit a limited correction.
4. Keep the repository and any demo artifact available through the judging period.
