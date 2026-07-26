# A2 adversarial security audit report

## Verdict

`not-green`

Faber Proof was audited on branch `build-week/faber-proof` at exact commit
`795ff0ad8f1d4706c8d92f88059059aa81f89bbb`. The source candidate was clean and
immutable when this synthesis began. No production source, test, fixture, expected
output, product document, or generated report was changed, and no provider call was
made.

Open findings:

| Severity | Count |
|---|---:|
| P0 | 4 |
| P1 | 4 |
| P2 | 4 |
| Total | 12 |

The four P0 findings permit false or unjustified acceptance at authority, report, replay
provenance, or cross-invocation verifier-result boundaries. A2 must remain not-green
until `$build-week-director` fixes the findings and an independent auditor verifies the
exact fix commit. A3 and A4 remain queued but are not the immediate action while these
P0 findings are open.

## Audit identity and method

- Audit: `A2`, adversarial security and false-PASS review.
- Date: 2026-07-26 UTC.
- Audited branch: `build-week/faber-proof`.
- Audited commit: `795ff0ad8f1d4706c8d92f88059059aa81f89bbb`.
- Commit subject: `Refresh final audit after CI activation`.
- Initial worktree: clean; `HEAD` exactly matched the audited commit.
- Audit prompt: `codex/audits/A2-adversarial-security.md`.
- Audit prompt SHA-256:
  `0607c11252f0ecdf72173a8315a8a783db840eeaa3028f11b482e2331cc608a8`.
- Review basis: authorized local QA already executed by four independent fresh
  reviewers, reconciled here against the exact source tree and current product/threat
  model.
- Evidence-collection external actions: none. No provider call or product publication
  occurred. The report commit, push, and issue comment are the separately authorized
  durable publication transaction after this report is finalized.

The synthesis auditor used `git status`, `git rev-parse`, `git show`, `git ls-tree`,
`rg`, read-only PowerShell file inspection, `Get-FileHash`, and pytest collection to
confirm the recorded test group composition. Behavioral results below are the
independent reviewers' already-executed evidence, not a new provider-backed run.

### Environment

- Host: HB2, `platform.platform()` reported `Windows-10-10.0.26200-SP0`; execution/path
  cases used the local NTFS checkout.
- Python: CPython 3.11.15, 64-bit, MSC v.1944.
- pytest: 9.0.2.
- Ruff: 0.15.10.
- mypy: 2.1.0 compiled.
- Git: 2.54.0.windows.1.
- PowerShell: 7.6.4.
- Nix and `just`: unavailable.

Machine-local supporting evidence was present and its supplied hashes verified. Portable
names are used below so the report does not persist the host account path:

| Evidence | SHA-256 | Durability |
|---|---|---|
| `%TEMP%\faber_a2_conformance_795ff0ad_results.json` | `f09fc3787ff4f19593283b4d387b23b0c06637bcb007bbecad134e911c04dfb5` | Machine-local, non-durable |
| `%TEMP%\faber_a2_conformance_795ff0ad.py` | `216099448e5cfde61b2f19abbb94e1e5e73601996f26fcbd253b530d3a6551d2` | Machine-local, non-durable |
| `%TEMP%\faber-execution-boundary-795ff0a\harness.py` | `09d4a046eed8b44656b38b8fecc910b1071fe56126ce90362bedf169358e3ed2` | Machine-local, non-durable |

Those paths are not durable audit artifacts. The finding sections and case inventory
therefore specify the inert inputs, mutations, expected results, observed results,
source roots, and required regressions independently of the temporary files.

## Reconstructed PASS path and authority graph

1. **Context and planner request.** `run_proof_product` loads owner task/catalog
   configuration, collects the exact local Git context, snapshots the workspace, builds
   an attempt, and creates the bounded planning request
   (`src/faber/proof_product.py:937-966`, `build_planning_request` at
   `src/faber/adapters/openai/proof_planner.py:205`).
2. **Live/replay planner boundary.** `plan_proof_request` dispatches only `live` or
   owner-digest-approved `replay` mode (`src/faber/adapters/__init__.py:29-61`).
   Replay compares provider, model, prompt, schema, request, catalog, and structured
   response commitments before returning data
   (`ReplayProofPlannerBackend._validate_context`,
   `src/faber/adapters/openai/replay.py:404-451`). Live and replay both call
   `materialize_proof_plan` (`src/faber/proof_planning.py:981-1244`).
3. **Claims, catalog, and selections.** The materializer enforces a closed response
   shape, claim fields, owner mandatory claims, exact active catalog ID/version,
   parameter schemas, and mandatory templates
   (`src/faber/proof_planning.py:1007-1176`). `ProofPlan.__post_init__` binds claims,
   selections, mandatory IDs, and uncovered IDs
   (`src/faber/proofs.py:622-711`).
4. **Workflow preflight.** `_preflight_workflow` binds task, attempt, revisions, patch,
   workspace, catalog, registry, owner policy, limits, environment, and every selected
   capability before execution (`src/faber/proof_workflow.py:589-748`).
5. **Executor, run, and receipt.** `run_proof_workflow` executes canonical selections
   through `execute_catalog_entry` and checks the workspace around each obligation
   (`src/faber/proof_workflow.py:1036-1217`). `_evidence_from_execution` creates the
   current proof-authority binding and then the receipt
   (`src/faber/proof_workflow.py:928-1033`). File/content, Python helper, pytest, and
   existing-command execution remain catalog-owned in
   `src/faber/proof_executors.py`.
6. **Deterministic decision.** `decide_proof` resolves actual run/receipt authority,
   applies demonstrated failure before incompleteness, and permits PASS only with no
   remaining reason (`src/faber/proofs.py:1466-1691`).
7. **Bundle generation.** `_write_bundle` writes plan, workflow, decision, evidence,
   runs, receipts, summary, and reports from in-memory validated objects
   (`src/faber/proof_product.py:311-495`).
8. **Portable bundle validator.** `validate_proof_bundle` rereads canonical artifacts,
   checks byte and selected record digests, selected task/context links, decision
   references, run/receipt pairs, counts, and report substrings
   (`src/faber/proof_product.py:514-786`). It does not reconstruct
   `ProofWorkflowResult`, call `decide_proof`, or regenerate either report. This is the
   root boundary for A2-P0-001 and A2-P0-002.
9. **CLI, JSON, and terminal.** The CLI prints either canonical `ProofRunOutcome.summary`
   or `ProofRunOutcome.human_lines`, then returns `ProofRunOutcome.exit_code`
   (`src/faber/cli.py:313-342`; `src/faber/proof_product.py:63-102`).
10. **Markdown and HTML.** `render_markdown_report` and `render_html_report` derive the
    displayed verdict from the in-memory workflow decision and escape report values
    (`src/faber/proof_reports.py:158-297`, `src/faber/proof_reports.py:300-424`).
11. **Demo summary.** `run_proof_demo` runs both candidate bundles, projects each child
    summary through `_proof_summary`, checks the contrast once, writes
    `demo-summary.json`, and publishes the staged directory
    (`src/faber/proof_demo.py:868-940`, `src/faber/proof_demo.py:943-1013`). There is no
    corresponding demo-level reload validator.
12. **Live capture transaction.** The guarded path checks key/branch/clean-tree and
    committed authority, captures both candidates, validates real returned model
    metadata, installs reviewed files, replays offline, runs privacy, and restores the
    backup after post-install failure (`src/faber/proof_demo.py:1076-1215`,
    `src/faber/proof_demo.py:1299-1479`).
13. **Eval report.** `build_eval_report` displays expected and actual verdict labels and
    computes `unjustified_pass_count` (`src/faber/proof_evals.py:486-550`). Its current
    actual-verdict field is assertion-derived rather than independently observed, which
    is A2-P2-001.

The generation path is materially stronger than the portable validation path. The
audited defects exploit that asymmetry or a boundary outside a single workflow
invocation.

## Validation evidence

All results in this section are recorded against the audited SHA.

| Check | Recorded result |
|---|---|
| Full pytest | 712 passed, 1 skipped |
| Focused proof/planner/executor/decision/product/demo/privacy/CLI | 379 passed, 1 guarded live skip |
| Additional focused structured/replay set | 259 passed |
| Executor/eval set | 109 passed |
| Ruff lint | Passed |
| Ruff format | Passed for 193 files |
| mypy | Passed across 93 source files |
| CI | GitHub Actions run `30219026273` passed Ubuntu, Windows, and optional OpenAI-extra/no-provider-call |
| Installed-package smoke | Not separately rerun during A2; audited-SHA CI performed its clean wheel install and installed no-key replay |
| Nix/just | Unavailable on HB2 |

The ordinary local command forms were:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m pytest -q <reviewer-recorded focused node set>
python -m pytest -q tests/test_openai_proof_planner.py tests/test_proofs.py tests/test_proof_product.py tests/test_proof_demo.py
python -m pytest -q tests/test_proof_executors.py tests/test_proof_evals.py
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python scripts/run_build_week_evals.py --check
python -m faber.cli demo proof --mode replay --out-dir <temporary-output> --json
python -m faber.cli audit-proof-artifacts <generated-demo-output>
```

The focused 379-pass/1-skip reviewer result was preserved by category and total, but
its complete node-selector command was not retained as a durable artifact. The same
behavioral area is included in the exact full-suite command. This limitation is
recorded rather than reconstructing an unobserved command.

The complete existing eval campaign reported 49/49 passing, zero reported unjustified
PASS outcomes, and suite digest
`sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`.
A2-P2-001 limits that metric: `build_eval_report` assigns `actual_verdict` from the
manifest's `expected_verdict` when the linked pytest assertion passes, so
`unjustified_pass_count` is not independent runtime-verdict evidence.

No-key replay produced:

- ordinary tests: `PASS` / `PASS`;
- Faber Proof: `BLOCK` / `PASS`;
- provenance: `fake-development`.

Generated artifact privacy scanned 51 files totaling 231075 bytes and reported zero
findings. That aggregate is valid for the scanned generated set; it does not close
A2-P1-003 because normal proof publication does not invoke the scanner and the inert
diagnostic-path probe was outside that generated set.

## Independent new-case inventory

The reviewers executed 38 additional cases. Thirty were assessed as genuinely new
against the existing 49-case campaign; eight were deeper, field-specific corroborations
of already represented replay/template/authority categories. Only the 30 genuinely new
cases count toward issue #9's minimum. Matrix members are listed separately only where
each material binding was mutated and executed separately.

### Structured planning and replay: 15 executed, 7 genuinely new

1. Boolean-as-integer token count rejected.
2. Nested operational `verdict` field rejected.
3. NFKC-confusable claim IDs both materialized and reached workflow execution; later
   authority reuse checks prevented publication.
4. A 24-level structured object was rejected.
5. A 140 KB replay payload was rejected.
6. Supplemental: task identity binding mutation rejected.
7. Supplemental: attempt/revision binding mutation rejected.
8. Supplemental: diff binding mutation rejected.
9. Supplemental: catalog binding mutation rejected.
10. Supplemental: prompt binding mutation rejected.
11. Supplemental: response-schema binding mutation rejected.
12. Supplemental: selected catalog version mutation with recomputed local digests
    rejected.
13. Supplemental: cross-context passing-authority mutation matrix returned
    `human_review`.
14. Fake-development provenance relabeled only by `provenance.status` was accepted by
    the final replay-review gate.
15. Contradictory visible reports with refreshed byte digests were accepted.

### Execution and path boundaries: 9 genuinely new

16. Alternate-drive, drive-relative, UNC, device, ADS, reserved-name, repeated
    separator, dot-segment, backslash, and trailing-separator matrix rejected.
17. Windows trailing-space, trailing-dot, and case aliases resolved to one NTFS file
    and were accepted.
18. Installed-package shadow in the repository was isolated from the pytest launcher.
19. Trusted source mutation between preflight and child use failed closed.
20. Non-UTF-8 partial Python-helper output with exit 0 failed closed.
21. Real timeout with partial non-UTF-8 stdout/stderr failed closed.
22. 3000-byte stdout plus 3000-byte stderr passed under a singular 4096-byte setting.
23. A descendant survived parent timeout; this matches the documented local-runner
    non-claim and is not a finding.
24. One cached raw passing verifier result authorized two distinct workflow
    invocations and candidates.

### Records, reports, and capture transactions: 14 genuinely new

25. Combined failed, duplicate, substituted-receipt, and missing evidence respected
    BLOCK precedence.
26. Independent `run-summary.json.verdict` mutation was rejected.
27. Visible Markdown/HTML disagreement with an unchanged BLOCK decision was accepted.
28. Parent `demo-summary.json` mutation had no demo-level validator.
29. One HTML injection marker passed through task, claim, parameter, expected,
    observed, counterexample, and reproduction fields as escaped, self-contained data.
30. Secret marker was redacted and a long marker truncated, but an absolute Windows
    machine path persisted and the standalone privacy audit caught it.
31. Fake capture client failure before the first candidate preserved all fixtures.
32. Fake capture client failure between candidates left only `bad.json`; review
    rejected it, preserved fixtures, but echoed the temporary path.
33. Malformed capture replay rejected before install.
34. Two-way bad/repaired capture swap with refreshed capture digests rejected on exact
    request binding.
35. Injected post-stage product validation failure preserved the previous output and
    removed the stage.
36. Interrupted stage-to-target directory replacement restored the previous output.
37. Interrupted reviewed multi-file install rolled back all earlier replacements.
38. Privacy failure preserved the prior fixture and did not echo the seeded secret,
    long marker, or machine path in its generic error.

## Findings

### A2-P0-001 - Coherent self-declared graph rewrite yields false PASS

- **Invariant:** A bundle with authoritative evidence statuses
  `[failed, passed, passed]` must deterministically remain BLOCK. Self-declared decision,
  summary, report, and digest changes cannot override evidence.
- **Source:** `decide_proof` derives BLOCK from authoritative failure at
  `src/faber/proofs.py:1558-1673`. `_write_bundle` records workflow, decision, evidence,
  and digests at `src/faber/proof_product.py:376-421`. The loader checks selected
  decision/evidence references at `src/faber/proof_product.py:645-739`, but never
  rebuilds the workflow or calls `decide_proof`.
- **Inert reproduction:** Generate the no-key bad demo bundle. Copy it. Leave all three
  proof-evidence files, verifier runs, receipts, plan, policy, task, attempt, and
  `workflow-result.json` unchanged. In `proof-decision.json`, change verdict `block` to
  `pass`, move `claim.boundary-final-report` from failed to passed, clear failed IDs,
  and replace reason codes with `["proof_passed"]`. In `run-summary.json`, make the
  corresponding verdict/reason/count/focus changes. Replace visible BLOCK with PASS in
  Markdown/HTML. Recompute only the changed artifact byte digests and the summary's
  self-declared decision digest.
- **Reproduction command:** Run the ordinary no-key demo command shown above, apply the
  canonical JSON mutation recipe, then call
  `validate_proof_bundle(<copied-bundle>)` and construct/print
  `ProofRunOutcome(summary=<copied run-summary>, ...)`.
- **Expected:** Validation rejects the graph because recomputed deterministic policy is
  BLOCK and `workflow-result.json`, decision, evidence, summary, and reports are not one
  structural graph.
- **Observed:** `validate_proof_bundle` returned `status=valid`, `verdict=pass`; the
  outcome returned exit 0, terminal PASS, canonical JSON PASS, Markdown PASS, and HTML
  PASS while authoritative evidence remained `[failed, passed, passed]`.
- **Impact:** A party able to rewrite a portable bundle can manufacture a fully visible
  PASS without changing the failed verifier evidence. This breaks the core
  proof-carrying-patch authority claim.
- **Root cause:** The portable validator trusts a self-consistent subset of declared
  artifacts. It neither deserializes/validates the complete workflow result nor
  recomputes `decide_proof`, and it does not structurally compare every graph edge.
- **Minimal remediation:** Add a strict `ProofWorkflowResult` loader; reconstruct the
  plan, policy, evidence, runs, and receipts from artifacts; recompute the decision with
  `decide_proof`; require exact canonical equality with decision, workflow, summary,
  counts, focus fields, and record digests before accepting.
- **Required regression:** Starting from a real BLOCK bundle, mutate each decision
  field alone and then apply the complete coherent rewrite above. Every variant must
  reject. Include an unchanged failed-evidence assertion and verify validator, JSON,
  terminal, Markdown, HTML, and exit status cannot report PASS.

### A2-P0-002 - Hidden markers let visible PASS reports validate over BLOCK

- **Invariant:** Markdown and HTML must be deterministic semantic projections of the
  authoritative decision, not arbitrary bytes containing a required substring.
- **Source:** Reports are generated from workflow objects by
  `render_markdown_report`/`render_html_report`
  (`src/faber/proof_reports.py:158-297`, `src/faber/proof_reports.py:300-424`). Bundle
  validation only searches for the expected verdict label and candidate revision
  substrings (`src/faber/proof_product.py:757-780`).
- **Inert reproduction:** Copy an unchanged BLOCK bundle. Change the visible Markdown
  heading and HTML title/H1/class from BLOCK to PASS. Retain `BLOCK` and the candidate
  revision in hidden/non-visible report text. Refresh only `report.md` and
  `report.html` byte digests in `run-summary.json`.
- **Reproduction command:**
  `python %TEMP%\faber_a2_conformance_795ff0ad.py`
  (case `bundle.visible-report-disagreement`); the mutation recipe above is sufficient
  to recreate it without that temporary harness.
- **Expected:** Bundle validation rejects both reports as semantically unequal to a
  deterministic regeneration from the BLOCK records.
- **Observed:** The child decision, summary, terminal, and JSON remained BLOCK, while
  visible Markdown and HTML showed PASS; `validate_proof_bundle` still returned valid
  BLOCK.
- **Impact:** A judge or maintainer opening the primary visual artifact can be shown
  PASS while machine-readable authority says BLOCK.
- **Root cause:** Substring presence checks substitute for deterministic report
  regeneration and byte/semantic equality.
- **Minimal remediation:** Regenerate both reports from reconstructed validated records
  and require exact bytes, or omit reports from authority and always regenerate them at
  display time. Do not accept hidden marker presence as consistency.
- **Required regression:** Mutate visible heading, title, class, reason, counts, failed
  focus, and candidate separately while retaining expected strings in comments,
  metadata, CSS, or hidden nodes. Every altered report must reject.

### A2-P0-003 - Fake development replay can be relabeled live-reviewed

- **Invariant:** `live-reviewed` must be established by validated live-capture evidence,
  real returned-model metadata, reviewer identity/time, and installation transaction;
  it cannot be asserted by one mutable status string.
- **Source:** The development returned-model constant is
  `development-fixture-not-live` (`src/faber/proof_demo.py:57`). Development fixtures
  identify returned model
  `development-fixture-not-live` and status `fake-development`
  (`src/faber/proof_demo.py:695-745`). `review_demo_replays` checks only that
  `provenance.status` is an allowed string and, when requested, equals `live-reviewed`,
  then compares bundle metadata without constraining the returned model for that status
  (`src/faber/proof_demo.py:770-825`). The guarded live-review path separately rejects
  missing/development returned-model metadata (`src/faber/proof_demo.py:1353-1362`).
- **Inert reproduction:** Copy the committed fixture directory to a temporary
  directory. Change only `replays/provenance.json.status` from `fake-development` to
  `live-reviewed`; leave both replay bundles and each recorded
  `returned_model=development-fixture-not-live` unchanged. Call
  `review_demo_replays(copy, require_live_reviewed=True)`.
- **Expected:** Reject because no live-capture/reviewer transaction establishes the
  claimed provenance and the returned model is explicitly a development fixture.
- **Observed:** The gate returned valid with `provenance=live-reviewed`.
- **Impact:** The final provenance gate can certify committed fake planner records as
  live-reviewed without a provider result or human review.
- **Root cause:** Provenance status is self-asserted and not bound to a capture/review
  manifest or minimum live metadata invariants.
- **Minimal remediation:** Make the final gate validate a signed/digest-bound or at
  least structurally bound review manifest produced by `review_live_demo_capture`;
  require reviewer, reviewed time, capture digest, real returned model and response ID,
  both request bindings, privacy result, and offline contrast.
- **Required regression:** Relabel unchanged development fixtures, remove each review
  field, substitute development returned-model metadata, and swap review manifests.
  Every case must reject. A fake injected capture may test the transaction, but it must
  not satisfy the real final-provenance gate.

This finding concerns the validation gate. The separate human requirement to perform a
real guarded live capture remains deferred and must not be merged into or used to close
this defect.

### A2-P0-004 - Raw passing verifier authority is reusable across workflows

- **Invariant:** One raw verifier result must authorize only the exact invocation and
  candidate context that produced it; it must not be rebound to another task, attempt,
  revision, patch, or workspace.
- **Source:** Existing-command execution accepts a runner-returned
  `LocalVerifierResult`, captures its raw run ID/digest, and enriches its metadata
  (`src/faber/proof_executors.py:1107-1207`). `_evidence_from_execution` creates a new
  authority binding from the current context around that raw identity
  (`src/faber/proof_workflow.py:928-1000`). Reuse tracking is a local set created anew
  for each `run_proof_workflow` call (`src/faber/proof_workflow.py:1080`,
  `src/faber/proof_workflow.py:1150-1186`).
- **Inert reproduction:** Use a catalog-approved inert existing-command verifier and a
  runner that caches and returns the identical passing `LocalVerifierResult`. Invoke
  workflow A. Change task ID/digest, attempt ID/digest, candidate revision, patch
  digest, and workspace bytes/digest; build valid context B; invoke workflow B with the
  same runner-returned object.
- **Reproduction command:**
  `python %TEMP%\faber-execution-boundary-795ff0a\harness.py`
  (case `cross_candidate_raw_result_reuse`); the `CachedRunner` recipe above is the
  complete independent reproducer.
- **Expected:** Workflow B rejects the already-consumed raw authority or the runner
  proves a context-bound fresh execution.
- **Observed:** Both workflow A and B produced PASS and receipts from the identical raw
  run object despite different task, attempt, revision, patch, and workspace digests.
  The final enriched run digests differed because Faber rebound the cached raw result
  to each current context.
- **Impact:** A stale cached success can authorize a changed candidate across workflow
  invocations.
- **Root cause:** Consumption uniqueness is invocation-local, while the adapter result
  itself has no unforgeable current invocation/candidate binding; the workflow treats
  it as fresh and rebinds it.
- **Minimal remediation:** Require the runner result to carry a caller-generated,
  single-use execution nonce and exact pre-execution context/policy commitment verified
  on return. Make replay/caching explicit and fail closed unless globally scoped
  authority storage proves non-reuse. Do not create current authority from an unbound
  cached result.
- **Required regression:** Return one identical passing raw object across two calls
  while mutating each of task, attempt, base/candidate revision, patch, workspace,
  selection, and policy independently and in combination. The second call must not
  produce PASS or a receipt.

### A2-P1-001 - Dry-run/no-verdict exits 0

- **Invariant:** Exit 0 is reserved for PASS by the documented CLI contract.
- **Source:** Product contract: `docs/FABER_PROOF_PRODUCT.md:94-99`.
  `ProofRunOutcome.exit_code` explicitly returns 0 for `status=dry_run`
  (`src/faber/proof_product.py:74-77`), and CLI returns it
  (`src/faber/cli.py:342`).
- **Inert reproduction:** Run an otherwise valid replay proof with `--dry-run`; inspect
  canonical JSON (`verdict=null`, `status=dry_run`) and `$LASTEXITCODE`.
- **Expected:** Exit 2 for no verdict/HUMAN_REVIEW-like incomplete authority, or a
  separately documented non-success code.
- **Observed:** `DRY RUN - NO VERDICT`, `verdict=null`, exit 0.
- **Impact:** Automation that treats exit 0 as documented PASS can merge or publish an
  unexecuted plan.
- **Root cause:** Dry-run is special-cased as process success despite the public verdict
  exit contract.
- **Minimal remediation:** Return 2 for dry-run/no verdict and keep a separate summary
  status for successful planning validation.
- **Required regression:** Assert human, JSON, verdict, and exit-code agreement for
  PASS, BLOCK, HUMAN_REVIEW, operational failure, and dry-run.

### A2-P1-002 - Demo summary is not bound to child bundles

- **Invariant:** `demo-summary.json` must be a validated projection of both child proof
  bundles and ordinary-test records.
- **Source:** `_proof_summary` projects child fields at
  `src/faber/proof_demo.py:868-895`; contrast is checked only before writing at
  `src/faber/proof_demo.py:898-917`; `run_proof_demo` writes and publishes the parent at
  `src/faber/proof_demo.py:991-1013`. `_publish_demo` checks only the management marker
  on an existing target (`src/faber/proof_demo.py:920-940`).
- **Inert reproduction:** Generate the no-key demo, leave `bad/` unchanged and
  validating BLOCK, then change only `demo-summary.json.bad.verdict` to `pass`.
- **Reproduction command:**
  `python %TEMP%\faber_a2_conformance_795ff0ad.py`
  (case `demo.manifest-independent-mutation`).
- **Expected:** A demo-level validator rejects the parent/child mismatch.
- **Observed:** No demo validator was available; the parent said PASS, child validation
  said BLOCK, and the privacy audit still passed.
- **Impact:** Demo JSON/terminal consumers can receive a materially false comparison
  even when child bundles are intact.
- **Root cause:** Parent projection and child digests have no reload-time structural
  validation.
- **Minimal remediation:** Add `validate_proof_demo` that validates both child bundles,
  ordinary records, report paths, projected fields, and contrast, then require it before
  display or overwrite.
- **Required regression:** Mutate every projected parent field and swap child paths or
  digests; all mismatches must reject.

### A2-P1-003 - Machine path persists through normal report publication

- **Invariant:** Known absolute machine paths must not persist in published proof
  diagnostics or reports.
- **Source:** `_safe_diagnostic` redacts sensitive-field patterns and truncates long
  strings but returns an ordinary short path unchanged
  (`src/faber/proof_executors.py:882-899`). Report `_safe_text` similarly lacks an
  absolute-path rule (`src/faber/proof_reports.py:27-47`). Normal product publication
  validates then publishes without calling `audit_proof_artifacts`
  (`src/faber/proof_product.py:1015-1035`); the standalone scanner detects paths at
  `src/faber/proof_privacy.py:386-415`.
- **Inert reproduction:** Return a safe helper diagnostic containing
  `C:\Users\qa-marker\private\proof-output.txt`, a marked secret, and a 715-byte marker;
  render HTML and run the standalone privacy audit.
- **Reproduction command:**
  `python %TEMP%\faber_a2_conformance_795ff0ad.py`
  (case `diagnostic.secret-path-truncation`).
- **Expected:** Secret, long marker, and machine path are absent before publication;
  privacy remains a backstop.
- **Observed:** Secret was redacted and long marker truncated. The machine path remained
  in diagnostic JSON and HTML. Standalone privacy correctly failed with
  `machine_specific_path`.
- **Impact:** Normal proof runs can publish host identity/path information unless a
  caller separately remembers the release audit.
- **Root cause:** Path sanitization exists only in an optional downstream scanner.
- **Minimal remediation:** Redact covered absolute paths in diagnostic/report
  sanitizers and run bounded privacy validation on the staged bundle before
  `_publish_stage`.
- **Required regression:** Seed Windows/POSIX/home/temp paths through every diagnostic
  and report field; normal publication must fail or redact, while errors must not echo
  the original path.

### A2-P1-004 - Windows file aliases receive authority

- **Invariant:** A catalog path must identify the exact owner-approved lexical path,
  not an NTFS alias of another path.
- **Source:** Catalog lexical validation checks separators, roots, traversal, and POSIX
  normalization but not Windows trailing-dot/space or case aliasing
  (`src/faber/proof_catalog.py:129-144`). `resolve_catalog_path` resolves the candidate
  and returns the OS-canonical file (`src/faber/proof_executors.py:485-526`).
  File-invariant execution then reads it and creates an authoritative run
  (`src/faber/proof_executors.py:1777-1903`).
- **Inert reproduction:** On NTFS create only `Evidence.txt`. Execute otherwise valid
  file-invariant entries whose catalog paths are `Evidence.txt `, `Evidence.txt.`, and
  `evidence.TXT`.
- **Reproduction command:**
  `python %TEMP%\faber-execution-boundary-795ff0a\harness.py`
  (case `windows_alias_path`).
- **Expected:** Each non-exact spelling fails before evidence or receipt creation.
- **Observed:** All three resolved to the same file, passed, and received authority.
- **Impact:** Catalog-owned file identity is ambiguous on Windows; a visually distinct
  path can authorize another file.
- **Root cause:** Portable lexical validation does not model Windows filename
  normalization/alias rules or compare the resolved path to an exact enumerated
  repository-relative identity.
- **Minimal remediation:** Reject trailing dots/spaces, reserved/device components,
  ADS, and case/normalization aliases on all platforms; on Windows verify exact
  directory-entry spelling component by component before access.
- **Required regression:** Windows-only matrix for trailing dot/space, case, reserved
  names, ADS, separator variants, and nested aliases; zero launch/read/receipt for every
  non-exact spelling.

### A2-P2-001 - Eval actual verdict is inferred from expectation

- **Invariant:** `actual_verdict` and `unjustified_pass_count` must be derived from
  observed runtime artifacts, independently of expected labels.
- **Source:** `build_eval_report` sets
  `actual_verdict = case.expected_verdict if assertion_passed else "NOT_EVALUATED"`
  (`src/faber/proof_evals.py:506-523`), then computes unjustified PASS from expected
  versus that copied value (`src/faber/proof_evals.py:525-543`).
- **Inert reproduction:** Define a case with expected BLOCK whose linked pytest test
  passes without returning a machine-readable verdict; call `build_eval_report`.
- **Expected:** Actual verdict is parsed from runtime evidence or recorded as an
  assertion-only outcome; the metric does not claim independent verdict coverage.
- **Observed:** Actual becomes BLOCK solely because expected is BLOCK, making reported
  unjustified PASS zero by construction for passing linked assertions.
- **Impact:** The 49/49 and zero-unjustified-PASS claims are useful regression-assertion
  results but overstate independent runtime verdict observation.
- **Root cause:** Eval metadata conflates test assertion success with product verdict.
- **Minimal remediation:** Require each eval to emit/return a validated observed
  verdict artifact, or rename fields/metric to assertion conformance and remove the
  unjustified-PASS claim.
- **Required regression:** A passing assertion paired with observed PASS when expected
  BLOCK must increment unjustified PASS and fail the suite.

### A2-P2-002 - NFKC-confusable claim IDs fail closed only after execution

- **Invariant:** Visually/compatibility-equivalent identifiers must be rejected before
  workflow execution.
- **Source:** Operational field names are NFKC-normalized
  (`src/faber/proof_planning.py:113-129`), but `ProofClaim.id` is only checked as a
  non-empty string (`src/faber/proofs.py:335-354`) and duplicate claims/selections use
  exact string sets (`src/faber/proofs.py:632-650`). Raw-authority reuse is detected
  only after an executor result returns (`src/faber/proof_workflow.py:1150-1173`).
- **Inert reproduction:** Build claims `claim.empty-input` and the same identifier with
  a full-width `e`; select executable evidence for both.
- **Expected:** Plan parsing rejects an NFKC/casefold collision before preflight or
  execution.
- **Observed:** Both claims materialized and reached execution. Later reuse checks
  prevented successful publication, so the path eventually failed closed.
- **Impact:** Fail-closed is late: unnecessary approved execution occurs and future
  executor/authority changes could expose an ambiguity.
- **Root cause:** Identifier uniqueness is exact-codepoint rather than normalized,
  unlike operational field-name defenses.
- **Minimal remediation:** Define one canonical identifier profile and reject any ID
  not already canonical or any NFKC/casefold collision across claims, selections,
  mandatory IDs, templates, and requirement references.
- **Required regression:** ASCII/full-width, composed/decomposed, compatibility, and
  casefold collision matrices must fail before any launcher/runner call.

### A2-P2-003 - Output byte budget is per stream, not aggregate

- **Invariant:** The singular `max_output_bytes` setting should cap total process output,
  or its per-stream semantics must be explicit throughout policy and documentation.
- **Source:** `launch_bounded_process` creates independent stdout and stderr
  `_BoundedCapture(max_output_bytes)` instances
  (`src/faber/proof_executors.py:324-344`, `src/faber/proof_executors.py:370-371`).
- **Inert reproduction:** Approved inert child writes 3000 bytes to stdout and 3000 to
  stderr with `max_output_bytes=4096`.
- **Reproduction command:**
  `python %TEMP%\faber-execution-boundary-795ff0a\harness.py`
  (case `aggregate_output_limit`).
- **Expected:** Under the singular aggregate interpretation, 6000 bytes triggers
  `output_limit` and cannot authorize PASS.
- **Observed:** Neither stream truncated; the verifier passed and a receipt was issued.
- **Impact:** A process can emit almost twice the advertised output budget.
- **Root cause:** Separate stream budgets are initialized from one singular policy
  field.
- **Minimal remediation:** Use one shared aggregate budget across concurrent drains, or
  rename/document the field as a per-stream cap and add a separate aggregate cap.
- **Required regression:** Split-stream totals just below, equal to, and above the
  aggregate threshold, including concurrent writes and timeout/partial-drain cases.

### A2-P2-004 - Missing capture manifest error exposes full temporary path

- **Invariant:** Capture/review errors must not echo machine-specific paths.
- **Source:** `_read_json` includes raw `OSError` text in a public `ProofDemoError`
  (`src/faber/proof_demo.py:133-138`); review calls it on the caller-supplied capture
  path (`src/faber/proof_demo.py:1313`).
- **Inert reproduction:** Inject a fake client that writes valid `bad.json` then fails
  before repaired capture and manifest creation. Call `review_live_demo_capture` on the
  partial temporary directory.
- **Reproduction command:**
  `python %TEMP%\faber_a2_conformance_795ff0ad.py`
  (case `capture.failure-between-candidates`).
- **Expected:** Generic missing-manifest error with no absolute path; fixtures remain
  unchanged.
- **Observed:** Fixtures remained fake-development and unchanged, but the error included
  the full `%TEMP%\...\capture-manifest.json` host path, including the local account
  path before this report normalized it.
- **Impact:** Error logs can disclose user and temporary-directory identity.
- **Root cause:** Raw OS exception text crosses the public error boundary.
- **Minimal remediation:** Map read failures to bounded path-role/name errors and keep
  raw exceptions only in non-persisted local debug state.
- **Required regression:** Missing, denied, malformed, non-UTF-8, and disappearing
  capture files must produce stable errors containing no home/temp/absolute path.

## Areas inspected with no finding

- Instruction-like comments and strings remained labeled untrusted data; mandatory
  policy and closed structured output still applied.
- Boolean integer spoofing, operational nested fields, deep/oversized structures,
  malformed/refused/partial planner output, and stale/unknown catalog selections failed
  closed in the tested cases.
- Six separate replay/context binding mutations, a selected-version mutation with
  recomputed digests, and bad/repaired swaps rejected before authoritative execution.
- Alternate-drive, UNC, device, ADS, separator, traversal, and symlink escapes rejected.
  The distinct Windows alias defect is A2-P1-004.
- Installed-package shadowing was isolated; source mutation between preflight and use,
  malformed non-UTF-8 helper output, real timeout with partial output, and output
  truncation failed closed.
- Combined failed/duplicate/substituted/missing evidence preserved deterministic BLOCK
  precedence; a direct summary-verdict mutation rejected.
- HTML injection markers were escaped and generated HTML was self-contained.
- Fake client failure before/among candidates, malformed capture, two-way capture swap,
  staged validation failure, interrupted directory publication, interrupted multi-file
  install, and privacy failure preserved prior authoritative fixtures/outputs.
- The standalone privacy scanner detected the seeded machine path without echoing the
  marked secret.
- The no-key demo retained the required ordinary PASS/PASS and Faber Proof BLOCK/PASS
  contrast with honest fake-development provenance.

The descendant-process probe observed a child surviving parent timeout. This is not a
new finding because `LOCAL_ISOLATION_DISCLOSURE` and the threat model explicitly disclaim
descendant-process isolation for the development-local runner.

## Uncertainty and residual risk

- No provider call was permitted or made. Real GPT-5.6 capture behavior and the final
  live-reviewed provenance addendum remain untested human gates.
- The execution/path probes were run on HB2 Windows/NTFS. Linux and Windows CI passed,
  but no fresh macOS audit was available and the Windows alias result is
  platform-specific.
- Temporary reviewer harnesses are machine-local and non-durable. Their relevant inputs
  and outcomes are captured above, but future re-verification should promote stable
  regressions into the repository.
- Nix and `just` were unavailable on HB2. Closest pytest, Ruff, and mypy equivalents
  passed as recorded.
- The local runner still does not provide OS, VM/container, network, hostile dependency,
  or descendant-process isolation. This is an explicit product non-claim, not evidence
  of production sandboxing.
- Repository-owner catalog policy remains trusted; digests provide integrity/context
  binding, not signer identity or non-repudiation.
- The privacy scanner is pattern-bounded and cannot establish comprehensive secret
  absence.

## Required next action

`$build-week-director` must address the highest-priority open finding,
A2-P0-001, then the remaining P0s before lower-severity work. Every finding remains
open with no fix commit. After fixes, use a fresh `$build-week-auditor` session to
re-run A2 against the exact fix commit and update the ledger only from independent
evidence.
