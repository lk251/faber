---
name: build-week-auditor
description: Run the next eligible independent Faber Proof Build Week audit from the repository queue. Use in a fresh Codex reset when asked to audit, red-team, review architecture, test clean installation, judge the demo, or check final submission compliance. Do not use to implement the normal feature queue.
---

# Build Week independent auditor

Use a fresh context to discover faults in the current implementation, not to redesign
the product.

## Route

1. Inspect the branch, commit, and working tree. Audit only a clean, current
   `build-week/faber-proof` head or a clearly isolated worktree.
2. Read `codex/build-week/AUDIT_QUEUE.md`, `codex/build-week/STATUS.md`, and the complete
   prompt for the first eligible incomplete audit, unless the user names another
   eligible audit.
3. Load product or competition references only as needed to evaluate the selected
   prompt. Read the handoff only on an actual session or machine resume.

## Audit

- Reconstruct behavior from code, tests, and executable evidence. Treat prior claims
  and documentation as hypotheses.
- Run the prompt's baseline and failure cases. Prefer reproducible counterexamples over
  speculation, inspect adjacent negative paths, and distinguish facts, inferences, and
  untested concerns.
- Use the queue's severity and report requirements. Record exact commits, commands,
  inputs, expected and observed results, source locations, and incomplete coverage.
- Write the audit report and update the queue and finding ledger. Commit only those
  records and, when useful, a minimal reproducing test.

Do not fix production source in the audit context. Do not alter task contracts,
catalogs, replay bundles, expected reports, or assertions to make behavior green. Route
findings to `$build-week-director`; preserve independent verification after fixes.

Report the audit ID and commit, verdict, finding counts and P0 reproductions, report and
ledger paths, the director's next action, and the next eligible audit. Do not claim
independence if the audited tree contains changes created in this session.
