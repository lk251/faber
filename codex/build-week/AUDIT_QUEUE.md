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
  - Result: `green` against `6d11e7a76a8b3f235a026c877d4bf6710bda4925`;
    the original P0 finding is verified fixed

- [x] `A2` — Adversarial security audit (initial audit run; not green)
  - Eligible after: work item 0081 machine implementation complete
  - Scope note: audit current security and replay behavior now; after guarded live
    capture, verify final bundle provenance and sanitization in an addendum before tag
  - Prompt: `codex/audits/A2-adversarial-security.md`
  - Report: `codex/build-week/audits/A2-adversarial-security-report.md`
  - Result: `not-green` against
    `795ff0ad8f1d4706c8d92f88059059aa81f89bbb`; all 4 P0 findings are fixed at candidate
    `b254458d705d801631be8207a0ddce75fbf68c21` but remain independently unverified,
    while 4 P1 and 4 P2 findings remain open; the initial audit executed 38 additional
    cases, of which 30 were genuinely new and 8 were deeper corroborations

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
- Immediate audit action: A2 independent re-verification of exact candidate
  `b254458d705d801631be8207a0ddce75fbf68c21`; A3/A4 remain queued and must not begin
  first
- Final live provenance remains unavailable and requires a later addendum; this is
  separate from `A2-P0-003`, which concerns the validation gate
- Open or unverified P0 findings: 4, all fixed by the director and none independently
  verified
- Open P1 findings: 4
- Open P2 findings: 4
- Last audit report: A2 initial audit at
  `codex/build-week/audits/A2-adversarial-security-report.md`; exact report commit from
  `git log`
- Last implementation commit audited:
  `795ff0ad8f1d4706c8d92f88059059aa81f89bbb`
- Exact remediation candidate awaiting audit:
  `b254458d705d801631be8207a0ddce75fbf68c21`

## Finding ledger

| ID | Audit | Severity | Status | Summary | Owner | Fix commit | Verification |
|---|---|---|---|---|---|---|---|
| `A1-P0-001` | `A1` | P0 | verified | Unbound or advisory-metadata-only receipted runs can be relabeled as unrelated selected proof evidence and produce `PASS` | `$build-week-director` | `6d11e7a76a8b3f235a026c877d4bf6710bda4925` | 2-case regression passed; independent 16-case complete-binding tamper matrix failed closed |
| `A2-P0-001` | `A2` | P0 | fixed | Coherent bundle graph rewrite preserves failed evidence but changes self-declared decision, summary, reports, and digests to validated `PASS` | `$build-week-director` | `35231e7f9d891bc7838dce59c9ef68d50135c5a5` | Director regression reconstructs complete authority and rejects the coherent false-PASS rewrite; independent verification pending |
| `A2-P0-002` | `A2` | P0 | fixed | Visible PASS Markdown/HTML validates over unchanged BLOCK authority when hidden BLOCK markers remain | `$build-week-director` | `f161881822c7b829016103cfffc73d5b738474e8` | Seven independent visible report mutations reject despite retained hidden markers and refreshed byte digests; independent verification pending |
| `A2-P0-003` | `A2` | P0 | fixed | Fake-development replay copies can be relabeled `live-reviewed` by changing provenance status only | `$build-week-director` | `d41ca460264e1b962f74644bfa3d50a6ae5ef265` | Relabel-only and seven capture/review transaction mutations reject with inert fixtures and no provider call; independent verification pending |
| `A2-P0-004` | `A2` | P0 | fixed | Identical cached raw passing verifier authority can authorize different workflow invocations and candidates | `$build-week-director` | `b254458d705d801631be8207a0ddce75fbf68c21` | Ten cached-result cases now reject on single-use nonce binding, and context commitments change for every required mutation; independent verification pending |
| `A2-P1-001` | `A2` | P1 | open | Dry-run with no verdict exits 0 despite the documented 0=PASS contract | `$build-week-director` | - | Dry-run terminal/JSON had no verdict and process exit 0 |
| `A2-P1-002` | `A2` | P1 | open | Parent demo summary can contradict a valid child bundle with no demo-level validator | `$build-week-director` | - | `bad.verdict=pass` persisted while the unchanged child validated BLOCK |
| `A2-P1-003` | `A2` | P1 | open | Normal proof publication can persist an absolute machine path because privacy audit is not integrated | `$build-week-director` | - | Path survived diagnostics/HTML; standalone privacy correctly reported `machine_specific_path` |
| `A2-P1-004` | `A2` | P1 | open | Windows trailing-space, trailing-dot, and case aliases receive authority for one NTFS file | `$build-week-director` | - | Three non-exact catalog spellings resolved to `Evidence.txt`, passed, and received receipts |
| `A2-P2-001` | `A2` | P2 | open | Eval `actual_verdict` is inferred from `expected_verdict`, limiting the unjustified-PASS metric | `$build-week-director` | - | Source trace and focused eval evidence |
| `A2-P2-002` | `A2` | P2 | open | NFKC-confusable claim IDs reach execution before later checks fail closed | `$build-week-director` | - | ASCII/full-width pair both materialized and executed; publication was prevented late |
| `A2-P2-003` | `A2` | P2 | open | `max_output_bytes` is applied separately to stdout and stderr | `$build-week-director` | - | 3000+3000 bytes passed under singular 4096-byte setting |
| `A2-P2-004` | `A2` | P2 | open | Missing capture-manifest errors expose the full temporary machine path | `$build-week-director` | - | Partial capture review failed closed but included the absolute temp path |

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

## Pending A2 re-verification candidate

- Candidate: `b254458d705d801631be8207a0ddce75fbf68c21`
- Fix commits: `A2-P0-001` at
  `35231e7f9d891bc7838dce59c9ef68d50135c5a5`; `A2-P0-002` at
  `f161881822c7b829016103cfffc73d5b738474e8`; `A2-P0-003` at
  `d41ca460264e1b962f74644bfa3d50a6ae5ef265`; `A2-P0-004` at
  `b254458d705d801631be8207a0ddce75fbf68c21`
- Director validation: 725 passed and 1 guarded live-provider skip; Ruff lint passed;
  Ruff format checked 193 files; mypy checked 93 source files; 49/49 deterministic
  eval cases passed with zero reported unjustified PASS results; 4 development reports
  were byte-stable
- No-key and package validation: direct and clean-installed demos both reproduced
  ordinary `PASS`/`PASS` and Faber Proof `BLOCK`/`PASS`; the direct privacy audit
  scanned 53 files and 241762 bytes with zero findings; wheel and sdist built and the
  clean-install audit passed
- Limitations: Nix and `just` were unavailable on HB2; the guarded live-provider test
  remained skipped and no provider call was made
- Required next action: a fresh `$build-week-auditor` must independently reconstruct
  and verify each finding against this exact candidate. Do not infer verification from
  the director's regressions, do not change A2 from `not-green` before that audit, and
  do not begin A3/A4 first.

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
