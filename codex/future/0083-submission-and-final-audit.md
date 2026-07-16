# Work item 0083 — Submission package, video, final audit, and freeze

## Objective

Turn the completed Faber Proof product into a compliant, persuasive, and independently
verifiable OpenAI Build Week submission. Freeze engineering scope, optimize the first
three minutes of judge attention, and eliminate submission-day failure modes.

Judges may decide from the Devpost text and video without installing the project. These
artifacts must therefore communicate the whole value proposition and the decisive proof
moment on their own.

## Required context

Read the shared Build Week context, final implementation, evals, threat model, status,
current official hackathon page, rules, resources, current official Codex documentation,
and current official GPT-5.6 documentation.

Re-verify all dates, repository-access instructions, video requirements, required fields,
and judging criteria against the official pages before finalizing. Record the
verification date in the submission checklist.

## Freeze rule

At the start of this work item:

- Stop adding product features.
- Do not begin the optional arena.
- Fix only P0 correctness, installation, privacy, demo, documentation, or compliance
  failures.
- Use the current proven bad-patch/fixed-patch vertical slice.
- Preserve eligible commit history.

Any proposed product change must be rejected unless it closes a failing global gate in
`codex/build-week/STATUS.md`.

## Part A — Judge-facing README

Rewrite the top-level README so the first screen presents the competition entry, while
preserving access to the broader Faber documentation below it.

Required opening:

```text
Faber Proof
Codex can write the patch. Faber makes the patch prove itself.
```

The first section must answer, without jargon:

- What problem is solved?
- What surprising thing happens in the demo?
- What does GPT-5.6 do?
- What does Faber, rather than the model, decide?
- How can a judge reproduce it without a key?

Include a compact comparison:

```text
                         BAD PATCH   REPAIRED PATCH
Ordinary tests              PASS          PASS
Faber Proof verdict        BLOCK          PASS
```

Required README sections:

1. **Thirty-second explanation**
2. **Watch the demo** with a placeholder that must be replaced by the public video URL
3. **Run the no-key proof demo** in five commands or fewer per supported platform
4. **What the blocked report proves** with a committed sample-report reference
5. **How it works** with one simple trust-boundary diagram
6. **Why this is not another AI code reviewer**
7. **GPT-5.6 usage**
8. **Codex usage and the repository-scoped skill**
9. **What existed before Build Week and what was added during Build Week**
10. **Technical decisions made by the human entrant**
11. **Security, privacy, authority, and runtime limitations**
12. **Supported platforms and installation paths**
13. **Tests, evals, and clean-install evidence**
14. **Business and adoption path**
15. **Repository map and deeper Faber documentation**

### Required honesty

State clearly:

- Faber's earlier protocol, trajectory, verifier, and local-runner foundation predates
  Build Week.
- Faber Proof, including its proof protocol, GPT-5.6 planner, bounded proof catalog,
  CLI, reports, skill, original demo, replay mode, and evals, is the competition
  extension.
- GPT-5.6 plans falsifiable obligations but does not make the authoritative verdict.
- Replay is a no-key reproduction of a context-bound reviewed model response, not a new
  live model call.
- The local runner is development infrastructure, not a production sandbox.
- The product does not guarantee universal program correctness.

Do not overclaim security, model independence, production readiness, customer adoption,
or benchmark results.

## Part B — Judge quickstart

Create `docs/JUDGE_QUICKSTART.md` containing:

- exact supported Python and platform combinations;
- clean clone and wheel/editable install variants;
- the shortest no-key replay command;
- expected terminal comparison;
- exact blocked and passing report locations;
- optional live install and run commands;
- troubleshooting for the three most likely setup failures;
- expected runtime range from measured evidence;
- how to validate bundle digests;
- how to uninstall or remove generated local data.

Every command must be copied from a clean-install audit that passed on the final
candidate commit.

## Part C — Devpost submission draft

Create `docs/DEVPOST_SUBMISSION.md` with copy-ready English text for every expected
field. Use final measured facts and avoid placeholders except human-only URLs or IDs.

Include:

### Project name

```text
Faber Proof
```

### Tagline

```text
Codex can write the patch. Faber makes the patch prove itself.
```

### One-sentence description

Describe proof-carrying patches, the independent GPT-5.6 proof planner, approved
executable evidence, and deterministic verdict in one sentence.

### Problem

Explain the concrete maintainer problem: ordinary tests and confident model prose can
miss the exact edge case an AI patch was supposed to solve.

### What it does

Describe the full workflow in plain language, leading with the blocked-green-tests demo.

### Why it is novel

Contrast bounded falsifiable proof obligations and authoritative evidence with generic
AI review, prose scoring, or unrestricted test generation.

### How it was built

Cover:

- Codex primary implementation thread;
- repository-scoped skills;
- direct GPT-5.6 Responses API integration and structured output;
- provider-neutral proof records;
- bounded proof catalog;
- Faber Runner and verification receipts;
- live and replay modes;
- self-contained report;
- adversarial evals and cross-platform packaging.

### GPT-5.6 use

State exactly what the model receives, what structured data it produces, what it cannot
control, and how model-run evidence is recorded.

### Codex use

State how Codex implemented most of the Build Week extension, how the director skill
resumed work items, how `$faber-proof` drives the product, and how Codex used the
counterexample to repair the demo patch. Include the real `/feedback` session ID only
after Javier supplies it.

### Human technical and product decisions

List the important entrant decisions, including:

- proof-carrying patches rather than a broad marketplace demo;
- provider adapter rather than vendor-specific core;
- model advisory role and deterministic verifier authority;
- bounded templates rather than unrestricted generated tests;
- original local demo rather than a third-party dependency;
- no-key replay for judge accessibility;
- fail-closed policy;
- explicit pre-existing/new-work boundary.

### Challenges and tradeoffs

Use real implementation evidence: replay binding, safe expressiveness, preserving
provider neutrality, deterministic reports, and keeping the experience small enough for
three minutes.

### Accomplishments

Use only measured results from the status file and eval suite.

### Potential impact and business path

Present a credible path:

1. local Codex skill and CLI;
2. CI/check integration for engineering teams;
3. repository-approved proof catalogs;
4. organization policy, audit export, and team reporting;
5. later Faber routing and market integration.

The initial buyer is an engineering team paying to reduce review risk and increase the
amount of agent-generated code it can safely accept. Do not claim existing revenue or
customers unless documented.

### What is next

Keep it concise: CI/GitHub integration, stronger isolated runners, broader approved
proof libraries, and evidence-aware multi-candidate routing.

### Built with

List only technologies actually present in the final repository.

### Category

```text
Developer Tools
```

### Links and IDs

Provide explicit placeholders with validation status for:

- public YouTube URL;
- repository URL;
- final tag or commit;
- `/feedback` session ID;
- optional static sample report URL when one is legitimately hosted.

## Part D — Three-minute video package

Create:

```text
docs/DEMO_SCRIPT.md
docs/DEMO_SHOT_LIST.md
docs/DEMO_RECORDING_CHECKLIST.md
```

Target final runtime: **2:35 to 2:50**, leaving a safety margin below three minutes.

### Required narrative

The video must show, not merely tell:

1. A plausible Codex patch and a green ordinary test suite.
2. `$faber-proof` or the equivalent exact product invocation.
3. GPT-5.6 decomposing the task into falsifiable claims and selecting approved proofs.
4. Faber executing evidence independently of model prose.
5. A visible red `BLOCK` report with the exact failed claim and counterexample.
6. Codex making the narrow repair from that evidence.
7. Ordinary tests remaining green.
8. The same proof turning green with `PASS`.
9. A ten-second trust-boundary explanation.
10. A concise impact statement.

### Recommended timing

Use a script close to:

```text
0:00–0:12  Hook: green tests, but the AI patch is still wrong.
0:12–0:28  Task and tiny candidate diff.
0:28–0:45  Invoke Faber Proof through Codex.
0:45–1:02  GPT-5.6 creates claims and chooses bounded proof entries.
1:02–1:25  BLOCK report and concrete budget-boundary counterexample.
1:25–1:40  Trust boundary: model plans; approved evidence decides.
1:40–2:02  Codex makes the narrow repair.
2:02–2:22  Rerun: ordinary tests PASS, Faber Proof PASS.
2:22–2:40  No-key replay, auditability, and developer-tool impact.
2:40–2:47  Closing tagline.
```

Adapt to measured tool latency. Remove dead time in editing while representing live and
replay states honestly. Never label a replay as a live call.

### Spoken audio

Write complete narration, not just bullet points. It must explicitly say how Codex and
GPT-5.6 were used. Use plain English and avoid reading digests aloud.

### Screen preparation

The shot list must define:

- terminal font size and dimensions;
- exact repository state and revision before each take;
- commands pre-positioned but not falsified;
- report zoom and sections to show;
- how to show `LIVE` versus `REPLAY` labels;
- how to avoid API keys, file-system user names, notifications, private tabs, and
  unrelated repository content;
- fallback recorded output if a live provider call is slow, clearly labeled as replay;
- final crop and subtitle-safe regions.

### Recording checklist

Include:

- microphone and spoken-audio check;
- 1080p or better capture;
- no copyrighted music or third-party media;
- no secrets or private notifications;
- public YouTube visibility;
- final duration check;
- incognito playback check;
- captions or transcript when practical;
- exact final commit shown or recorded in the description.

## Part E — Submission images

Create `docs/SUBMISSION_IMAGES.md` with an exact capture plan for at least:

1. The blocked report above the fold.
2. The passing report above the fold.
3. A two-panel comparison or architecture/trust-boundary view.

Specify recommended crop, resolution, visible labels, and captions. Use only original
project visuals. Generate committed source HTML or SVG assets where practical, but do
not add a fragile screenshot dependency merely for this work item. Javier may capture
the final PNG/JPEG images manually from the deterministic reports.

## Part F — Final audit tool

Create `scripts/final_submission_audit.py` or an equivalent deterministic command that
checks the local final candidate for:

- clean working tree;
- expected branch and baseline tag;
- eligible commit delta generation;
- all P0 status gates that can be machine-checked;
- final full test/lint/type results recorded and current;
- wheel and clean-install audit success;
- replay demo expected verdicts;
- sample-report regeneration and privacy audit;
- no placeholder in machine-completable README or docs fields;
- no accidental API key or known fixture secret;
- public-video, repository-sharing, `/feedback`, and Devpost human fields explicitly
  marked complete or incomplete;
- final tag consistency when a tag exists;
- final submitted commit matching the audited commit.

The script must not claim to verify a private repository invitation or public YouTube
visibility automatically unless it actually has a safe supported mechanism. Treat
human attestations as explicit checklist fields.

Produce a concise JSON and Markdown final-audit report.

## Part G — Human-only gates

When all machine work is complete, stop with exact instructions for Javier. Do not
invent values or claim completion.

### 1. Primary Codex session

In the thread where the majority of core functionality was built:

```text
Run /feedback
```

Record the returned session ID in:

- `codex/build-week/STATUS.md`;
- `docs/DEVPOST_SUBMISSION.md`;
- final audit inputs.

### 2. Live GPT-5.6 provenance

When final replay bundles are not yet `live-reviewed`, provide the exact guarded command
that uses `OPENAI_API_KEY`, sanitizes the response, validates all bindings, and replaces
only the reviewed fixture. Rerun the full replay demo afterward.

### 3. Private repository access

Share the final private repository with the judging addresses specified by the current
official rules. Verify the invitations or access from a separate clean context. Keep
access through the judging period.

### 4. Video

Record, edit, upload publicly to YouTube, and replace every video placeholder. Verify
playback without being signed in.

### 5. Devpost

Paste the reviewed copy, select Developer Tools, attach images, enter the repository,
video, final commit/tag, and session ID, preview the submission, and submit before the
deadline with margin.

## Part H — Final checks and tag

After all machine-completable gates pass and human values have been entered:

1. Run the full final audit from a clean clone or clean worktree at the exact candidate
   commit.
2. Run all tests, Ruff, mypy, available Nix checks, build, clean-install audit, replay
   demo, evals, privacy audit, and report regeneration.
3. Confirm the Build Week delta and pre-existing/new-work statement.
4. Confirm every README and Devpost command matches the audited commit.
5. Confirm all sample artifacts contain no machine-specific or sensitive data.
6. Create an annotated tag:

   ```text
   build-week-2026-submission
   ```

7. Rerun the final audit against the tag.
8. Record the tag SHA and audit-report digest in the status and submission document.
9. Do not move the tag silently.

If any source or generated artifact changes after tagging, create a reviewed new final
commit and intentionally replace the tag only before submission, recording why. Never
rewrite the state after the deadline unless current official rules explicitly permit a
limited correction.

## Part I — Post-submission handoff

Update `docs/CODEX_SESSION_HANDOFF.md` with:

- exact submitted commit and tag;
- submission date and status;
- judge access period;
- no-change or limited-change rule;
- where final audit and submission text live;
- restoration of the Hermes external-pilot roadmap after the competition freeze;
- any unresolved operational follow-up.

Do not perform the Hermes pilot during the freeze merely because the normal roadmap is
restored in documentation.

## Acceptance criteria

Machine-completable:

- README leads with a clear Faber Proof story and a verified five-command no-key path.
- Judge quickstart commands pass from the final candidate.
- Devpost copy is complete, factual, and aligned with all four judging criteria.
- Video script and narration fit within 2:50 in a timed rehearsal.
- Shot list exposes the green-tests-to-block-to-pass reversal clearly.
- Final audit tool detects incomplete human fields and all tested technical failures.
- All code, packaging, replay, eval, privacy, and report gates are green.
- Build Week delta and baseline are documented.
- Full checks pass.

Human-completable before final tag/submission:

- `/feedback` session ID entered.
- Final replay provenance is `live-reviewed`.
- Repository access granted and independently checked.
- Public narrated YouTube video is under three minutes and independently playable.
- Devpost fields and images are entered and previewed.
- Final audited tag matches the submitted repository state.

`codex/build-week/STATUS.md` must distinguish machine-complete from human-complete rather
than marking unresolved human gates as finished.

## Commit

Use one focused commit for the machine-created submission package, similar to:

```text
Implement work item 0083 Build Week submission package
```

Create the annotated final tag only after the later human values and final audit are
complete.