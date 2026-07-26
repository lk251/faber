# Faber Proof — offline continuation directive

This file is a user-authorized queue override for the period when `OPENAI_API_KEY` is
not available. Its purpose is to maximize useful Build Week work without weakening,
faking, or prematurely claiming live GPT-5.6 provenance.

## Completion notice

This directive has been executed through all machine-completable 0082 and 0083 work.
The 0083 source snapshot is `f2518bd96ebc90f3d6fc7ba6097f1ffb1d6595da`;
`docs/generated/FINAL_SUBMISSION_AUDIT.md` records `MACHINE PASS; HUMAN INCOMPLETE`.
Do not reimplement the workstreams below on a fresh machine. Resume from
`docs/CODEX_SESSION_HANDOFF.md` and `codex/build-week/STATUS.md`: run the independent
audit queue and preserve the remaining human/live gates. Remote Ubuntu/Windows CI is
active and green in Actions run `30217997785`.

## Invocation

The historical execution instruction was:

```text
Read codex/build-week/OFFLINE_CONTINUATION.md and execute it end-to-end. Do not stop at the missing OPENAI_API_KEY gate; continue all independent machine-completable P0 work.
```

## Non-negotiable interpretation

The missing API key is a **deferred human-only provenance gate**, not a dependency for
packaging, adversarial evaluation, CI, installation, report design, documentation, or
submission preparation.

Preserve all of these facts:

- Work item 0081 machine implementation is complete.
- The current replay fixtures remain honestly labeled `fake-development`.
- They must never be called live, reviewed, final, or submission-ready.
- Final submitted replay bundles must still be produced by guarded real `gpt-5.6` calls,
  sanitized, reviewed, context-bound, and labeled `live-reviewed`.
- Missing live provenance blocks final technical completion of 0081, any final submission
  claim based on live evidence, the final tag, and Devpost submission.
- Missing live provenance does **not** block work item 0082 or the machine-completable
  portions of 0083.
- Do not ask Javier again for an API key during this offline run.
- Do not request another `/feedback` submission. The recorded primary session ID is
  already authoritative for the submission.

## First action — repair the control plane

Before product work, make one small focused control-plane commit that updates the
repository so future director runs do not stop unnecessarily.

Update `codex/build-week/STATUS.md`, `docs/CODEX_SESSION_HANDOFF.md`,
`codex/BUILD_WEEK_START_HERE.md`, and `.agents/skills/build-week-director/SKILL.md` as
needed to express this state clearly:

```text
0081-M  machine implementation and deterministic demo: complete
0081-L  guarded live capture and live-reviewed provenance: deferred human gate
0082    eligible now and current machine work
0083-M  eligible after 0082; all machine-completable submission work may proceed
0083-H  live capture, repository sharing, video upload, Devpost entry, and final tag:
        human/final gates
```

Use equivalent wording rather than introducing new identifiers everywhere when that
would create needless churn. The essential behavior is:

1. Select 0082 despite 0081-L remaining open.
2. After 0082, continue directly through 0083 machine work.
3. Do not stop merely because an independent audit becomes eligible.
4. Open P0 audit findings still take priority and block final tagging.
5. Human gates block only work that actually depends on them.
6. Final status must distinguish `machine-complete` from `submission-complete`.

Do not mark 0081 fully complete and do not check live-provenance acceptance boxes.

## Workstream 1 — complete work item 0082 without live credentials

Read and implement `codex/future/0082-evals-packaging-and-ci.md` in full. No part of its
core acceptance criteria requires a live provider call.

Complete at least:

- the product-specific threat model;
- the deterministic adversarial evaluation suite;
- prompt-injection, stale-replay, malformed-plan, authority-binding, traversal, timeout,
  contradiction, partial-bundle, and false-pass cases;
- the secret/privacy artifact audit;
- conventional sdist and wheel packaging;
- base installation that does not import or require the OpenAI SDK;
- an optional OpenAI extra for later live mode;
- an isolated clean-install audit outside the checkout with controlled `PYTHONPATH`;
- the five-command-or-fewer judge path on supported platforms;
- least-privilege Linux and Windows CI;
- no-key replay-demo CI coverage;
- deterministic report regeneration checks;
- performance and bundle-size evidence;
- exact documentation and status updates.

Keep all live OpenAI calls out of ordinary CI. A manual guarded workflow may be prepared,
but it must not expose credentials or commit unreviewed output automatically.

Use one focused 0082 commit. Run the prompt-specific checks, full pytest, Ruff, mypy,
available Nix checks, wheel build, clean-install audit, no-key demo, evals, privacy audit,
and deterministic regeneration. Record exact results and limitations.

## Workstream 2 — make the eventual live capture one-command and low-risk

Without using a key, inspect the existing guarded live adapter and capture utilities.
Create or finish `docs/LIVE_GPT56_CAPTURE_RUNBOOK.md` and a deterministic wrapper command
or script so that later human involvement is limited to setting `OPENAI_API_KEY` and
running one documented command.

The prepared capture path must:

1. Fail before any call when `OPENAI_API_KEY` is absent, without printing its value.
2. Confirm the expected branch, clean tree, task, catalog, prompt, schema, and candidate
   bindings.
3. Capture bad and repaired planner responses separately through the existing strict
   parser and validator.
4. Never overwrite accepted fixtures incrementally; stage outputs in a temporary review
   area first.
5. Record requested and returned model IDs, response IDs, usage, latency, and binding
   digests when available.
6. Sanitize secret-like material and machine-specific paths.
7. Run the privacy audit and bundle validation before replacement.
8. Require both candidates to reproduce the material `BLOCK`/`PASS` result.
9. Replace fixtures atomically only after every check succeeds.
10. Regenerate sample reports and rerun the completely offline replay demo.
11. Produce a concise review manifest showing exactly what changed.
12. Roll back or leave existing fixtures untouched on any failure.

Add tests for the wrapper using injected/fake clients only. Do not make a live call and do
not relabel development fixtures.

This work may be part of 0082 when it fits coherently, or a separate focused preparation
commit. It does not close 0081-L.

## Workstream 3 — complete all machine-completable work in 0083

After 0082 is green, read `codex/future/0083-submission-and-final-audit.md` and complete
every portion that does not require a human secret, voice, upload, private invitation, or
Devpost submission.

Produce and validate:

- the judge-facing top-level README;
- `docs/JUDGE_QUICKSTART.md` using commands proven by the clean-install audit;
- copy-ready `docs/DEVPOST_SUBMISSION.md` with measured facts and explicit placeholders
  only for unresolved human/live values;
- complete `docs/DEMO_SCRIPT.md` narration targeting 2:35–2:50;
- `docs/DEMO_SHOT_LIST.md`;
- `docs/DEMO_RECORDING_CHECKLIST.md`;
- `docs/SUBMISSION_IMAGES.md` and any deterministic original SVG/HTML source assets;
- the deterministic final-submission audit tool and JSON/Markdown reports;
- the Build Week delta and pre-existing/new-work explanation;
- a concise business and adoption path grounded in the implemented product;
- explicit technical decisions made by the human entrant;
- a final human-gate checklist with exact commands and fields.

Use the current deterministic replay reports to develop layout, copy, timing, and audit
logic, but label their provenance accurately. Make replacing them after live capture a
single documented regeneration step.

Time the narration mechanically from word count and, where practical, add a deterministic
script that flags a script likely to exceed 2:50 at conservative speaking rates. Do not
claim that this substitutes for Javier's final spoken rehearsal.

The final-audit command should pass all machine-completable checks while returning a
clear nonzero or incomplete status for unresolved human gates. It must not treat missing
live provenance, video URL, judge access, or Devpost completion as a software defect.

Use one focused 0083 machine-work commit. Do not create the final submission tag.

## Audit scheduling

Independent audits remain valuable, but audit eligibility must not strand the primary
machine-work lane.

- A2 may audit the current security and replay implementation once the tree is clean,
  explicitly recording that final live-artifact provenance was not yet available.
- After live capture, A2 or a narrow provenance addendum must verify the final reviewed
  bundles and sanitization path before final tagging.
- A3 and A4 become eligible after 0082.
- A5 becomes eligible after 0083 machine work, but its final verdict must remain
  conditional until live provenance and all human submission fields are complete.

The director must not impersonate an independent auditor. Record eligible audits and
continue machine-completable implementation. Open P0 findings, when later recorded by an
independent session, take priority over further work.

## Prohibited shortcuts

Do not:

- fabricate, hand-author, or regenerate a fixture and call it a live GPT-5.6 response;
- weaken request, catalog, prompt, schema, diff, receipt, or authority binding;
- let model output define commands, code, imports, paths, or authority;
- skip an adversarial case because live credentials are absent;
- add broad product features, the arena, payments, a marketplace, a hosted account
  system, or a GitHub App;
- claim production sandboxing or universal program correctness;
- create the final submission tag;
- overwrite user changes or stage unrelated files;
- stop solely because `OPENAI_API_KEY` is missing.

## Commit, push, and continuation policy

- Begin by inspecting `git status -sb`, current branch, latest commit, and remotes.
- Work only on `build-week/faber-proof` and preserve unrelated changes.
- Pull or fast-forward the just-pushed remote branch when the tree is clean.
- Keep the control-plane update, 0082, and 0083 machine work in focused commits.
- After each clean validated commit, push `build-week/faber-proof` when authentication is
  available. A push failure should be reported, but it should not erase or mix local work.
- Update `codex/build-week/STATUS.md` and `docs/CODEX_SESSION_HANDOFF.md` after each
  milestone with exact SHAs, commands, results, limitations, and next action.
- Continue automatically until all 0082 and 0083 machine-completable acceptance criteria
  are complete, an actual P0 failure prevents safe progress, or the working tree cannot
  be made safe.

## Required final report for this offline run

Do not end with another request for `OPENAI_API_KEY`. Report:

- control-plane commit;
- 0082 commit and exact validation;
- live-capture preparation command and tests;
- 0083 machine-work commit and produced submission artifacts;
- current demo verdicts and runtime;
- CI/workflow state and any remote checks not yet observed;
- eligible independent audits;
- open P0/P1 findings;
- the exact remaining human/live gates, grouped separately;
- the single next instruction Javier should use.

The expected next human/live gates after this offline lane are still:

1. guarded live GPT-5.6 capture and review;
2. independent audit completion and any fixes;
3. repository access for judges;
4. human voice recording and public video upload;
5. Devpost preview and submission;
6. final audited immutable tag.

Do not weaken any of them. Complete everything else now.
