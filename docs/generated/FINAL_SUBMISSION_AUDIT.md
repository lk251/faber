# Faber Proof final submission audit

- Overall status: **HUMAN_INCOMPLETE**
- Machine status: **PASS**
- Human status: **INCOMPLETE**
- Branch: `build-week/faber-proof`
- Audited target: `HEAD`
- Audited commit: `f2518bd96ebc90f3d6fc7ba6097f1ffb1d6595da`
- Eligibility baseline: `64f775cfe2f622837bd9aaa40f6369aa22af1d80`

Machine completion and human submission completion are separate. An external workflow-authorization blocker or unavailable Nix command is reported explicitly; neither is represented as a successful remote run.

## Build Week delta

- Eligible commits: **45**
- Changed files: **166**
- Additions/deletions: **+35949 / -528**
- Warnings: **0**

## Machine checks

| Check | Category | Status | Detail |
|---|---|---|---|
| `clean_working_tree` | `git` | **PASS** | Working tree is clean before report output. |
| `expected_branch` | `git` | **PASS** | Current branch is build-week/faber-proof. |
| `baseline_tag` | `git` | **PASS** | build-week-2026-baseline resolves to the recorded pre-period commit. |
| `audit_target` | `git` | **PASS** | Audit target HEAD resolves to an eligible descendant. |
| `submission_artifacts` | `static` | **PASS** | 12 required machine artifacts are present. |
| `judge_readme` | `static` | **PASS** | README has the required opening, comparison, no-key path, honesty, and 15 sections. |
| `submission_document_content` | `static` | **PASS** | Judge quickstart and Devpost draft contain all required machine sections. |
| `placeholder_policy` | `static` | **PASS** | No generic machine placeholder exists; only approved explicit human-gate markers remain. |
| `submission_svg_assets` | `static` | **PASS** | Original SVG sources parse and contain no external or active content. |
| `submission_privacy` | `static` | **PASS** | 17 submission files passed with zero covered findings. |
| `remote_ci_definition` | `external` | **EXTERNAL_BLOCKED** | Exact Linux/Windows workflow remains preserved as a draft; GitHub rejected workflow-path updates from the registered non-FIDO deploy credential. |
| `build_week_delta` | `git` | **PASS** | 45 eligible commits and 166 changed files have a warning-free baseline delta. |
| `human_gate_state` | `static` | **PASS** | Human gates are explicit, structurally valid, and internally consistent. |
| `pytest` | `command` | **PASS** | Command exited 0. |
| `ruff_format` | `command` | **PASS** | Command exited 0. |
| `ruff_lint` | `command` | **PASS** | Command exited 0. |
| `mypy` | `command` | **PASS** | Command exited 0. |
| `adversarial_evals` | `command` | **PASS** | Command exited 0. |
| `report_regeneration` | `command` | **PASS** | Command exited 0. |
| `clean_install` | `command` | **PASS** | Command exited 0. |
| `performance_smoke` | `command` | **PASS** | Command exited 0. |
| `replay_demo` | `command` | **PASS** | Ordinary PASS/PASS and Faber Proof BLOCK/PASS reproduced with fake-development provenance. |
| `canonical_environment` | `command` | **NOT_AVAILABLE** | Nix and/or just is unavailable; equivalent Python release gates are required. |

## Human gates

| Gate | Status | Evidence present |
|---|---|:---:|
| `feedback_session` | **COMPLETE** | yes |
| `deadline_status` | **INCOMPLETE** | yes |
| `live_provenance` | **INCOMPLETE** | yes |
| `independent_audits` | **INCOMPLETE** | yes |
| `judge_repository_access` | **INCOMPLETE** | yes |
| `public_video` | **INCOMPLETE** | yes |
| `devpost` | **INCOMPLETE** | yes |
| `final_tag` | **INCOMPLETE** | yes |

## Interpretation

- `machine_status=pass` means every available machine gate executed successfully.
- `human_status=incomplete` is expected until live provenance, audits, access, video, permitted Devpost state, and final tag are human-attested.
- Run with `--require submission` to receive exit code 2 while those human gates remain incomplete.
- Do not create the final tag from this machine-only report.
