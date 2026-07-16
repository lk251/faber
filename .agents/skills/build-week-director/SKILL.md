---
name: build-week-director
description: Continue the Faber Proof OpenAI Build Week implementation from the next incomplete repo prompt. Use when asked to continue Build Week, get to work, maximize the hackathon submission, resume the queue, or prepare the submission. Do not use for ordinary Faber roadmap work after the competition is closed.
---

# Build Week director

Drive the Faber Proof Build Week queue without requiring the user to paste prompts or
restate decisions.

## Start

1. Read `codex/BUILD_WEEK_START_HERE.md`.
2. Read the files listed there in order.
3. Inspect `git status -sb`, the current branch, and the latest commit.
4. If not already on `build-week/faber-proof`, create or switch to that branch without
   discarding unrelated work. If the working tree is mixed, preserve it and report the
   conflict rather than staging it blindly.
5. Read `codex/build-week/STATUS.md` and select the first incomplete P0 work item whose
   dependencies are complete.

## Execution loop

For each selected work item:

1. Read the complete prompt from `codex/future/`.
2. Inspect the existing implementation and tests before designing changes.
3. Implement the smallest coherent solution that satisfies every acceptance criterion
   and advances the winning vertical slice.
4. Keep OpenAI-specific code in an adapter. Keep GPT-5.6 advisory and data-only. Never
   execute a command, Python source, shell fragment, or path supplied by model output.
5. Add tests first or alongside behavior changes. Include failure-path tests.
6. Run the prompt-specific checks and the full available checks.
7. Exercise the Build Week demo whenever the vertical slice is runnable.
8. Update `codex/build-week/STATUS.md` with:
   - status;
   - commit SHA;
   - exact validation results;
   - demo state;
   - known limitations;
   - next work item.
9. Update `docs/CODEX_SESSION_HANDOFF.md` when the recommended next action or validation
   baseline changes.
10. Create one focused commit using the work-item number and a terse description.
11. Continue automatically to the next P0 item while the repository remains clean and
    no human-only gate is required.

## Primary-session requirement

The hackathon requires the `/feedback` session ID for the thread where the majority of
core functionality was built. Keep the main implementation thread focused on the core
vertical slice, ideally work items 0077 through 0081. Use fresh secondary threads for
architecture review, security review, installation review, and submission review only.

Before the primary thread ends, remind the user to run `/feedback` and record the ID in
`codex/build-week/STATUS.md`. Do not invent or infer a session ID.

## Decision policy

Use the decisions already recorded in `docs/FABER_PROOF_PRODUCT.md` and
`docs/BUILD_WEEK_2026.md`. Do not reopen settled product choices merely because another
architecture is possible.

A redesign is justified only when the current path cannot meet a P0 acceptance gate or
when it clearly raises the expected judging score without threatening the deadline.
Record such a change in the product document and status file before implementing it.

## Fail-closed requirements

A Faber Proof run must never return `PASS` when any of these conditions holds:

- a required proof obligation is missing;
- a required verifier is unavailable or failed;
- GPT-5.6 output is invalid, refused, timed out, or references an unknown template;
- a high-severity claim has no executable evidence;
- a replay response does not match its recorded request or schema digest;
- evidence is contradictory;
- the decision policy cannot be evaluated deterministically.

Use `HUMAN_REVIEW` for incomplete or uncertain evidence and `BLOCK` for demonstrated
failure.

## Scope control

Do not implement the following before every P0 submission gate is green:

- real payments or custody;
- marketplace or worker-economy features;
- model training;
- a production GitHub App;
- external autonomous publication;
- third-party upstream contributions;
- arbitrary model-generated executable tests;
- a general web account system;
- the optional multi-candidate arena.

## Human-only gates

Stop only for the human-only actions enumerated in
`codex/BUILD_WEEK_START_HERE.md`. When stopping, leave a clean commit, a precise next
instruction in the status file, and the exact command or website action the user must
perform.

## Completion report

At the end of each session, report:

- completed work items and commit SHAs;
- exact tests and demo commands with results;
- current bad-patch and fixed-patch verdicts;
- remaining P0 items;
- the next human-only gate, if any;
- whether the current session should be submitted with `/feedback`.