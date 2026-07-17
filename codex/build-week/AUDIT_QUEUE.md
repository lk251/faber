# Faber Proof independent audit queue

This file is the machine-resume state for fresh GPT-5.6 audit sessions. The auditor must
select the first eligible incomplete audit, run it against the current clean
`build-week/faber-proof` branch, and record exact evidence.

## Instruction

```text
Use $build-week-auditor and run the next eligible independent audit.
```

## Queue

- [x] `A1` — Architecture and authority audit
  - Eligible after: work item 0079 complete
  - Prompt: `codex/audits/A1-architecture-and-authority.md`
  - Report: `codex/build-week/audits/A1-architecture-and-authority-report.md`
  - Result: `not-green` against `9314ddb51962aa194989e97a619a8dbedc19f04a`;
    one P0 finding requires a director fix and fresh A1 verification

- [ ] `A2` — Adversarial security audit
  - Eligible after: work item 0081 complete
  - Prompt: `codex/audits/A2-adversarial-security.md`
  - Report: `codex/build-week/audits/A2-adversarial-security-report.md`

- [ ] `A3` — Clean-room installation audit
  - Eligible after: work item 0082 complete
  - Prompt: `codex/audits/A3-clean-room-installation.md`
  - Report: `codex/build-week/audits/A3-clean-room-installation-report.md`

- [ ] `A4` — Judge comprehension audit
  - Eligible after: work item 0082 complete and blocked/passing reports generated
  - Prompt: `codex/audits/A4-judge-comprehension.md`
  - Report: `codex/build-week/audits/A4-judge-comprehension-report.md`

- [ ] `A5` — Final compliance and submission audit
  - Eligible after: work item 0083 machine work complete
  - Prompt: `codex/audits/A5-final-compliance.md`
  - Report: `codex/build-week/audits/A5-final-compliance-report.md`

## Current state

- Implementation branch to audit: `build-week/faber-proof`
- Eligible audit: fresh `A1` fix verification after the director resolves `A1-P0-001`;
  no new audit is currently eligible
- Open P0 findings: 1 (`A1-P0-001`)
- Open P1 findings: none recorded
- Last audit commit: this focused A1 audit commit; exact SHA is available from `git log`
- Last implementation commit audited: `9314ddb51962aa194989e97a619a8dbedc19f04a`

## Finding ledger

| ID | Audit | Severity | Status | Summary | Owner | Fix commit | Verification |
|---|---|---|---|---|---|---|---|
| `A1-P0-001` | `A1` | P0 | open | Unbound or advisory-metadata-only receipted runs can be relabeled as unrelated selected proof evidence and produce `PASS` | `$build-week-director` | — | `python -m pytest -q tests/test_proofs.py::test_unbound_receipted_run_cannot_be_relabelled_as_another_selected_proof` |

Use finding IDs such as `A1-P0-001`. Status is one of:

```text
open
accepted
fixed
verified
rejected-with-rationale
```

A P0 finding cannot be marked resolved without a fix or an evidence-backed rationale
that the reported failure is impossible under the actual implementation.

## Audit report requirements

Every report must contain:

- audited branch and exact commit;
- clean/dirty working-tree state;
- prompt version or prompt file digest when practical;
- commands and tools used;
- concise system model or architecture reconstructed from code;
- findings ordered P0, P1, P2;
- exact file and symbol references;
- reproduction steps or failing tests;
- expected versus observed behavior;
- recommended minimal fix;
- tests needed to prevent regression;
- explicit areas inspected with no finding;
- uncertainty and incomplete coverage;
- final audit verdict: `green`, `green-with-P1`, or `not-green`.

## Write policy

The independent auditor should normally write only the audit report and queue update.
It may add a narrowly scoped failing test when that is the clearest reproducible finding
and the working tree is clean. It must not perform a broad source fix, redesign the
product, edit evidence fixtures to hide a failure, or change submission claims without
routing the finding back to `$build-week-director`.

After the director fixes findings, a fresh auditor session or the original auditor after
a reset must verify the exact fix commit and update the ledger.

## No-audit conditions

Do not run or trust an audit when:

- the implementation branch has uncommitted overlapping changes;
- the audit is based on a stale commit after material source changes;
- its eligibility work item is incomplete;
- the auditor cannot run the relevant tests and does not clearly state that limitation;
- the session is using a different product definition than
  `docs/FABER_PROOF_PRODUCT.md`.
