# Audit A1 — Architecture and authority

## Verdict

`not-green`

- Audited branch: `build-week/faber-proof`
- Audited implementation commit: `9314ddb51962aa194989e97a619a8dbedc19f04a`
  (`Implement work item 0079 bounded proof executors`)
- Initial working tree: clean (`git status --porcelain=v1` produced no output)
- Remote check: `git fetch --prune origin` succeeded; the Build Week branch has no
  configured upstream and no `origin/build-week/faber-proof` ref. `origin/master` is
  `c915523383dc58114bf748f7d7a64c1c398faaba`, the recorded branch starting commit.
- Audit prompt: `codex/audits/A1-architecture-and-authority.md`
- Prompt SHA-256: `56079a6b2af4af74cc107b205f84c464beeeaeb609a2cdaeb08d63a46d57961f`
- Findings: **1 P0, 0 P1, 0 P2**
- Source changes: none
- Audit-only test change: one narrowly scoped two-case failing regression test

The provider and catalog layering is substantially sound, but the public decision
function still has a false-`PASS` path. A receipted verifier run with no complete proof
authority binding can be relabeled as evidence for an unrelated advisory claim and
catalog selection. Both an entirely unbound run and a run carrying only caller-written
plan/selection metadata are accepted.

## Reconstructed authority flow

```text
TaskContract + Attempt + raw diff + ProofCatalog planner views
  │  TaskContract.digest, Attempt.digest, diff digest, planner_catalog_digest
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
  │  mandatory claim/template restoration; advisory ProofPlan
  ▼
_preflight_workflow
  src/faber/proof_workflow.py
  │  exact task/attempt/diff/catalog/registry/workspace/policy commitments;
  │  catalog.resolve(id, version); bind owner defaults; preflight all obligations
  ▼
execute_catalog_entry
  src/faber/proof_executors.py
  │  exact typed capability or registered VerifierSpec; bounded local execution
  ▼
_evidence_from_execution
  src/faber/proof_workflow.py
  │  wraps the raw VerifierRun with task, attempt, plan, selection, catalog entry,
  │  capability, execution-policy, workspace, verifier, and raw-run commitments;
  │  writes proof_authority_binding_digest in run metadata and result metrics
  ▼
VerificationReceipt.from_verifier_run + ProofEvidence
  src/faber/receipts.py and src/faber/proofs.py
  │  receipt binds task, attempt, worker, revisions, verifier and result;
  │  evidence cites exact run and receipt digests
  ▼
decide_proof
  src/faber/proofs.py
  │  resolves supplied runs/receipts; BLOCK > HUMAN_REVIEW > PASS
  ▼
ProofDecision
  src/faber/proofs.py
```

The intended workflow-generated path therefore has the right complete binding. The
finding is at the adjacent public `decide_proof` boundary, where that complete binding
is optional for selected proof evidence.

## Findings

### A1-P0-001 — Unbound receipted runs can be relabeled as unrelated selected proof evidence

**Severity:** P0 — produces an unjustified `PASS` and bypasses the catalog/executor
authority boundary.

**Verified fact.** In `src/faber/proofs.py`, `_verifier_run_binds_plan` returns `True`
when a run has neither executor nor advisory binding metadata (line 1324 at the audited
commit). It also returns `True` for metadata containing only a matching
`proof_plan_digest` and `selection_digest` (line 1338), without requiring the
owner-generated `proof_authority_binding_digest`, catalog, capability, execution
policy, workspace, or raw-run commitments.

`_resolve_authoritative_outcome` then accepts that run for a model-selected
`ProofEvidence` record because the receipt still binds the same task, attempt,
verifier, and result. Receipt semantics do not bind a plan, selection, or catalog, so
changing or omitting run metadata does not invalidate that receipt. `decide_proof`
counts the result as authoritative evidence for the unrelated claim and returns
`PASS`.

**Input and reproduction.** The audit test first proves that one ordinary untagged run
and receipt pass the original plan. It then creates an unrelated claim and template
selection for the same task and attempt, relabels the same authority records as that
selection's evidence, and expects fail-closed `HUMAN_REVIEW`. The second parameter adds
only caller-writable advisory plan/selection metadata. Both cases instead return
`PASS`. The unrelated plan and relabeled evidence are round-tripped through their
public `to_dict`/`from_dict` boundaries before the decision call.

```powershell
.\.faber\dev-venv\Scripts\python.exe -m pytest -q `
  tests\test_proofs.py::test_unbound_receipted_run_cannot_be_relabelled_as_another_selected_proof
```

Observed:

```text
FF
expected: human_review
observed: pass
2 failed in 0.19s
```

Exact regression test: `tests/test_proofs.py`,
`test_unbound_receipted_run_cannot_be_relabelled_as_another_selected_proof`.

**Why this is authoritative rather than speculative.** The reused receipt is valid for
the exact task and attempt, so this does not depend on forging a receipt or crossing an
attempt boundary. The missing link is specifically from that real authority record to
the advisory claim and catalog capability it is claimed to prove. Model-selected data
can therefore change what a legitimate but unrelated run is treated as proving.

**Minimal fix.** When `_resolve_authoritative_outcome` resolves evidence for a selected
proof obligation, require the complete workflow-generated executor binding, including
the matching authority digest in both run metadata and metrics. Do not accept untagged
or advisory-metadata-only runs for selected claim evidence. If legacy ordinary
verifier runs must remain valid for the independent mandatory-verifier cross-scan,
keep that path separate; they must not satisfy a model-selected claim. Update older
passing proof fixtures to use a workflow-generated/catalog-bound run.

**Regression coverage required.** Make both audit parameter cases fail closed, retain
the existing exact executor-binding pass test, retain the direct-executor/stale-plan
negative tests, and verify that an ordinary untagged task-contract verifier may only
satisfy the separately defined mandatory-verifier requirement if that compatibility is
intentional.

## P1 findings

None.

## P2 findings

None.

## Verified controls with no finding

### Provider boundary

- `src/faber/proofs.py`, `proof_planning.py`, `proof_catalog.py`, and
  `proof_workflow.py` do not import the OpenAI SDK or provider-specific response types.
- Base dependencies remain empty; the SDK is only the `live-openai` optional extra.
- An isolated `-I -S` import with site packages disabled successfully imported Faber's
  core proof modules while `openai` was absent.
- `ProofPlannerBackend` is a provider-neutral protocol. Fake and replay paths pass
  through the same `materialize_proof_plan` validator as live output.
- The `gpt-5.6` default occurs only under `src/faber/adapters/openai/`.

### Advisory planning and catalog boundary

- `ProofPlan` and `ProofTemplateSelection` close authority to `advisory`.
- Structured model output has closed fields and no verdict field. Executable-looking
  parameter keys, unknown templates, stale versions, malformed parameters, missing
  mandatory templates, conflicting mandatory claims, and incomplete high-risk
  coverage fail closed.
- Catalog entries own immutable operational family, paths/targets, verifier identity
  and version, exact `VerifierSpec` digest, environment, timeout, output limit, trusted
  source digests, parameter defaults, and capability digest.
- Workflow preflight binds the exact catalog, registry, attempt, workspace, proof
  policy, and execution policy before launching any obligation.

### Workflow-generated authority and deterministic policy

- Workflow-generated runs carry a full proof authority digest covering task, attempt,
  plan, selection, catalog entry/version, family, capability, execution policy,
  workspace, verifier, and raw verifier run. Receipts commit the wrapped result.
- Exact task/attempt/revision/diff mismatches, missing receipts, stale catalog entries,
  direct executor results missing the full binding, stale tagged runs, contradictory
  evidence, raw authority reuse, workspace mutation, and operational errors do not
  pass through the tested workflow.
- Demonstrated authoritative failure takes precedence over missing evidence and model
  refusal. Missing, invalid, refused, timed-out, and contradictory states otherwise
  become `HUMAN_REVIEW`.
- Reason lists and proof decisions are sorted and deterministic for fixed authority
  inputs. Existing receipt semantics and registered schema/golden tests remained green
  at the audited implementation commit.

### Scope, dependencies, and isolation

- Proof code remains detached from settlement, payments, marketplace routing, GitHub,
  Hermes, and trajectory training decisions.
- New proof records use explicit frozen dataclasses and bounded canonical data.
- No base runtime dependency was added. The local executor's lack of OS, container,
  network, and descendant-process isolation is stated explicitly and enforced as an
  honest disclosure rather than a sandbox claim.

## Commands and results

All green baselines below were run against the clean audited implementation commit
before adding the audit-only failing regression test.

| Command | Result |
|---|---|
| `git fetch --prune origin` | passed |
| focused proof/planner/executor/verifier pytest command | 340 passed, 1 guarded-live skip in 2.99s |
| `python -m pytest -q` | 650 passed, 1 skip in 13.00s |
| `python -m ruff check .` | passed |
| `python -m mypy src` | passed across 86 source files |
| isolated base import with `python -I -S` and no `openai` spec | passed |
| 12 named A1 positive and negative boundary tests | 12 passed in 0.19s |
| audit P0 regression test | 2 failed; both observed `PASS` instead of `HUMAN_REVIEW` |
| full pytest after adding audit test | 2 failed, 650 passed, 1 skipped in 12.84s |
| `python -m ruff check tests/test_proofs.py` | passed |

`nix develop --command just check` was unavailable because neither `nix` nor `just` is
installed on HB3.

## Untested and incomplete areas

- Work item 0080 has not started, so no proof CLI or evidence-report generator exists
  to test for a displayed verdict that differs from the decision artifact. That work
  must consume a freshly derived authoritative decision rather than trust an arbitrary
  serialized `ProofDecision` in isolation.
- No live network/API call was made; the guarded live test remains skipped without a
  human-supplied credential. Live request construction and mocked response handling
  were covered locally.
- Linux, Nix, container, VM, network, descendant-process isolation, and concurrent
  swap-and-restore races were not tested on HB3. The product does not currently claim
  those isolation properties.
- This audit traced the five executor families' authority integration and relevant
  negative tests, but it was not a replacement for the later A2 adversarial security
  audit of every family-specific parser and process boundary.

## Required next action

Resume `$build-week-director` before work item 0080. Fix `A1-P0-001` without weakening
catalog or receipt policy, make the committed regression test green, run focused and
full checks, and record the fix commit. A fresh A1 verification audit is required
against that exact clean fix commit. No new independent audit is eligible before that
verification; A2 becomes eligible only after work item 0081.
