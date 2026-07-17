# Audit A1 — Architecture and authority

## Verdict

`green`

- Audited branch: `build-week/faber-proof`
- Audited implementation commit: `6d11e7a76a8b3f235a026c877d4bf6710bda4925`
  (`Fix A1-P0-001 proof authority binding`)
- Initial working tree: clean (`git status --porcelain=v1` produced no output)
- Remote check: `git fetch --prune` succeeded. The Build Week branch still has no
  configured upstream or `origin/build-week/faber-proof` ref; `origin/master` is the
  recorded branch-start commit `c915523383dc58114bf748f7d7a64c1c398faaba`.
- Audit prompt: `codex/audits/A1-architecture-and-authority.md`
- Prompt SHA-256: `56079a6b2af4af74cc107b205f84c464beeeaeb609a2cdaeb08d63a46d57961f`
- Open findings: **0 P0, 0 P1, 0 P2**
- Verified finding: **1 P0** (`A1-P0-001`)
- Source and test changes by this verification audit: none

The focused director fix closes the original false-`PASS` path. Selected proof
evidence now requires an executor-tagged run and then the already-existing complete
owner binding. An ordinary untagged verifier run can still participate in the separate
mandatory-verifier compatibility scan, but it cannot authorize a model-selected claim.

## Reconstructed authority flow

```text
TaskContract + Attempt + raw diff + ProofCatalog planner views
  │  TaskContract.digest, Attempt.digest, raw/redacted diff digests,
  │  planner_catalog_digest
  ▼
build_planning_request
  src/faber/adapters/openai/proof_planner.py
  │  bounded/redacted ProofPlanningRequest + request digest
  ▼
ProofPlannerBackend.plan
  src/faber/proof_planning.py
  │  OpenAI, replay, or fake returns provider-neutral ProviderPlanningResponse
  ▼
materialize_proof_plan
  src/faber/proof_planning.py
  │  closed response fields; exact catalog id/version; parameter-schema validation;
  │  mandatory claim/template enforcement; advisory ProofPlan
  ▼
_preflight_workflow
  src/faber/proof_workflow.py
  │  exact task/attempt/diff/catalog/registry/workspace/policy commitments;
  │  ProofCatalog.resolve(id, version); owner defaults; preflight-all execution
  ▼
execute_catalog_entry
  src/faber/proof_executors.py
  │  exact typed capability or registered VerifierSpec; bounded local execution
  ▼
_evidence_from_execution
  src/faber/proof_workflow.py
  │  wraps the raw VerifierRun with task, attempt, plan, selection, catalog entry,
  │  capability, execution-policy, workspace, verifier, and raw-run commitments;
  │  duplicates proof_authority_binding_digest in metadata and result metrics
  ▼
VerificationReceipt.from_verifier_run + ProofEvidence
  src/faber/receipts.py and src/faber/proofs.py
  │  receipt binds task, attempt, worker, revisions, verifier, result, and metrics;
  │  evidence cites exact run and receipt digests
  ▼
decide_proof
  src/faber/proofs.py
  │  resolves supplied authority; selected evidence requires expected_selection;
  │  BLOCK > HUMAN_REVIEW > PASS
  ▼
ProofDecision
  src/faber/proofs.py
```

The exact selected-evidence boundary is
`src/faber/proofs.py::_resolve_authoritative_outcome`, which calls
`_verifier_run_binds_plan(..., expected_selection=selection)`. At the audited commit,
`_verifier_run_binds_plan` first rejects a selected outcome that has no executor-owned
metadata and then recomputes the complete binding from the task, attempt, plan,
selection, catalog entry/version, family, capability, execution policy, workspace,
verifier, and raw run. Both run metadata and receipted result metrics must contain that
same digest.

## Finding verification

### A1-P0-001 — Verified

**Original severity:** P0 — an unbound or advisory-metadata-only receipted run could be
relabeled as unrelated selected proof evidence and produce an unjustified `PASS`.

**Original audited commit:** `9314ddb51962aa194989e97a619a8dbedc19f04a`.

**Fix commit:** `6d11e7a76a8b3f235a026c877d4bf6710bda4925`.

**Fix inspected:** `src/faber/proofs.py::_verifier_run_binds_plan` now returns `False`
when `expected_selection` is present and the run has no executor-owned metadata. The
existing executor-tagged branch continues to require and recompute the complete
authority binding. No receipt semantics or mandatory-verifier compatibility behavior
was weakened.

**Exact original reproduction rerun:**

```powershell
.\.faber\dev-venv\Scripts\python.exe -m pytest -q `
  tests/test_proofs.py::test_unbound_receipted_run_cannot_be_relabelled_as_another_selected_proof
```

Observed at the fix commit:

```text
2 passed in 0.11s
```

Both public-boundary variants now return `HUMAN_REVIEW` with
`verifier_run_binding_mismatch`: all owner metadata removed, and caller-written
`proof_plan_digest`/`selection_digest` metadata only. Before the fix, both variants
returned `PASS` and the test produced two failures.

**Independent adjacent matrix:** a real workflow-generated bound run first produced
`PASS`. The audit then removed each of the following fields one at a time and rebuilt
the evidence record through `ProofEvidence.from_dict`:

```text
attempt_digest
capability_digest
catalog_digest
catalog_entry_id
catalog_entry_version
execution_policy_digest
family
proof_authority_binding_digest
proof_plan_digest
raw_verifier_run_digest
raw_verifier_run_id
selection_digest
task_contract_digest
workspace_digest
```

It also removed the receipted metrics binding and tried an executor tag plus only the
two advisory digests. All **16** tampered cases returned `HUMAN_REVIEW` with
`verifier_run_binding_mismatch`; none produced `PASS` or `BLOCK`.

Adjacent committed tests also verified:

- a complete workflow-generated binding still passes;
- a direct executor run without plan/selection authority cannot authorize replay;
- a stale bound run cannot satisfy a current plan or mandatory-verifier requirement;
- changing the complete metadata binding to another plan still fails because the
  binding in receipted metrics cannot be relabeled;
- ordinary untagged receipts remain usable only by the separate mandatory-verifier
  scan;
- missing receipts, cross-plan/cross-attempt evidence, stale catalog entries, and
  contradictory evidence fail closed.

## Findings

### P0 findings

None open. `A1-P0-001` is verified.

### P1 findings

None.

### P2 findings

None.

## Verified controls with no finding

### Provider boundary

- `src/faber/proofs.py`, `proof_planning.py`, `proof_catalog.py`,
  `proof_executors.py`, and `proof_workflow.py` do not import the OpenAI SDK or
  provider response types.
- Base dependencies remain empty. `openai>=2.45.0,<3` exists only in the optional
  `live-openai` extra.
- An isolated `python -I -S` process had no `openai` module available and imported all
  core proof modules successfully.
- `ProofPlannerBackend` is a provider-neutral protocol. Fake and replay backends pass
  through the same `materialize_proof_plan` validator as live output.
- The `gpt-5.6` default remains under `src/faber/adapters/openai/`.

### Advisory planning and catalog boundary

- `ProofPlan` and `ProofTemplateSelection` force `authority="advisory"`.
- Structured model output has a closed schema and no verdict or executable field.
  Unknown templates, stale versions, invalid parameters, missing mandatory templates,
  conflicting mandatory claims, and uncovered high-risk claims fail closed.
- Owner catalog entries control the exact capability family, target/path,
  `VerifierSpec`, source digests, working directory, environment, timeout, output
  limit, parameter defaults, and capability digest.
- Workflow preflight binds the exact catalog, registry, task, attempt, patch,
  workspace, proof policy, and execution policy before launch.

### Receipt authority and deterministic policy

- Every selected authoritative outcome requires the complete executor tag and binding
  in both run metadata and receipt-bound metrics.
- Receipts bind the exact task, attempt, worker, revisions, verifier, result, metrics,
  and failure reasons. One raw authority cannot satisfy multiple selections.
- Valid pass, authoritative block, missing/error human-review, high-risk uncovered,
  missing receipt, cross-plan/cross-attempt, stale catalog, contradictory evidence,
  mandatory-verifier failure, and mandatory-verifier compatibility paths behaved as
  documented.
- Demonstrated authoritative failure keeps precedence over missing evidence. All
  reason lists and decisions remain deterministic for fixed authority inputs.
- Existing receipt schemas, golden digests, and compatibility tests stayed green.

### Scope, dependencies, and isolation

- Proof behavior remains independent of settlement, payments, marketplace routing,
  GitHub, Hermes, and trajectory training.
- Records remain explicit frozen dataclasses with bounded canonical data.
- No base runtime dependency was added.
- Local execution is honestly described as not providing OS, container, network, or
  descendant-process isolation.

## Commands and results

| Command or check | Result |
|---|---|
| `git fetch --prune` | passed |
| exact `A1-P0-001` regression | 2 passed in 0.11s |
| named A1 pass/block/human-review and adjacent negative paths | 17 passed in 0.23s |
| independent complete-binding deletion/tamper matrix | valid baseline `PASS`; 16/16 tampered cases `HUMAN_REVIEW` |
| focused proofs/planner/executors/verifier tests | 342 passed, 1 guarded-live skip in 3.12s |
| `python -m pytest -q` | 652 passed, 1 guarded-live skip in 13.31s |
| isolated base import with `python -I -S` and no `openai` spec | passed |
| `python -m ruff check .` | passed |
| `python -m ruff format --check src/faber/proofs.py tests/test_proofs.py` | 2 files already formatted |
| `python -m mypy src` | passed across 86 source files |
| `nix develop --command just check` | unavailable: neither `nix` nor `just` is installed on HB3 |

Environment: Python 3.12.2, pytest 9.0.2, Ruff 0.15.10, and mypy 2.1.0 from
the ignored `.faber/dev-venv` workspace environment.

## Untested and incomplete areas

- Work item 0080 has not started, so no proof CLI or evidence-report generator exists
  to test for a displayed verdict that differs from a freshly derived decision. That
  work must render the workflow decision rather than trust an unrelated serialized
  verdict.
- No live network/API request was made. The guarded live test skipped without a
  human-supplied credential; request construction, response handling, fake backend,
  and replay behavior were covered locally.
- Nix, Linux, container/VM isolation, network isolation, descendant-process isolation,
  and concurrent swap-and-restore races were not tested on HB3. The product does not
  claim those local isolation properties.
- This architecture audit traced the five capability families and their authority
  integration. It is not the later A2 adversarial security audit of every parser,
  path, process, replay, and secret boundary.

## Required next action

Resume `$build-week-director` at work item 0080. No A1 P0 or P1 finding remains open.
No new independent audit is eligible now; A2 becomes eligible after work item 0081.
