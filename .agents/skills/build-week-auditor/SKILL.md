---
name: build-week-auditor
description: Run the next eligible independent Faber Proof Build Week audit from the repository queue. Use in a fresh Codex reset when asked to audit, red-team, review architecture, test clean installation, judge the demo, or check final submission compliance. Do not use to implement the normal feature queue.
---

# Build Week independent auditor

Use a fresh reasoning context to challenge the current Faber Proof implementation. The
purpose is independent fault discovery, not product ideation.

## Start

1. Read `AGENTS.md` and `docs/CODEX_SESSION_HANDOFF.md`.
2. Read `codex/BUILD_WEEK_START_HERE.md`, `docs/BUILD_WEEK_2026.md`, and
   `docs/FABER_PROOF_PRODUCT.md`.
3. Read `codex/build-week/RESET_STRATEGY.md` and
   `codex/build-week/AUDIT_QUEUE.md`.
4. Inspect the current branch, commit, working tree, and implementation status.
5. Require a clean, current `build-week/faber-proof` branch or a clearly isolated
   worktree at its current head. Do not audit a stale or ambiguous tree.
6. Select the first eligible incomplete audit in the queue unless the user names a
   specific eligible audit.
7. Read its complete prompt under `codex/audits/`.

## Independence rules

- Reconstruct behavior from code and tests rather than accepting README claims.
- Treat prior implementation-thread explanations as hypotheses, not evidence.
- Do not reopen the settled product definition unless implementation cannot meet a P0
  gate.
- Do not propose broad features, marketplaces, payments, training, or hosted systems.
- Prefer a reproducible failing case over a speculative concern.
- Prefer the smallest corrective action that preserves the winning vertical slice.
- Explicitly distinguish verified facts, inferences, and untested concerns.

## Severity

Classify every finding:

```text
P0  Can disqualify the submission, cause an unjustified PASS, break the core demo,
    expose sensitive data, or prevent clean judge use.
P1  Materially weakens a judging criterion or a common user path.
P2  Useful but must not delay P0 completion or human submission work.
```

Do not inflate severity merely to make the audit appear valuable.

## Audit procedure

1. Record exact branch, commit, and working-tree state.
2. Run the prompt's baseline commands.
3. Trace the relevant data and authority flow through source code.
4. Attempt the named failure cases using existing tests, temporary fixtures, or narrowly
   scoped additional tests.
5. Check whether a claimed control is enforced in code or only documented.
6. Record exact file, symbol, input, expected result, observed result, and reproduction
   command for every actionable finding.
7. Check adjacent negative paths so one example is not mistaken for a complete control.
8. Write the required report under `codex/build-week/audits/`.
9. Update the finding ledger and queue state.
10. Commit only the audit report, queue update, and any minimal reproducing test.

## Source-change policy

The auditor normally does not fix production code. This preserves independence and
prevents a fresh session from redesigning the implementation while auditing it.

A narrowly scoped source fix is allowed only when all are true:

- it addresses a clear P0 defect;
- the fix is mechanically obvious;
- it does not alter public protocol or product design;
- focused and full tests can be run immediately;
- the audit report still records the original failure and fix commit.

Otherwise route findings to `$build-week-director` through the queue and status file.

Never modify task contracts, proof catalogs, replay bundles, expected reports, or
assertions merely to make a failing implementation appear green.

## Evidence requirements

A report is not complete without:

- exact commit audited;
- exact commands and results;
- concrete findings or a clear account of what was tested;
- explicit untested areas;
- final verdict: `green`, `green-with-P1`, or `not-green`;
- next action for the director;
- whether a fresh verification audit is required after fixes.

## Completion

At the end, report to the user:

- audit ID and commit audited;
- verdict;
- P0/P1/P2 counts;
- exact P0 reproductions;
- report and ledger paths;
- whether the implementation director must resume;
- next eligible audit.

Do not claim that an audit is independent when it was run against uncommitted changes
created in the same session.