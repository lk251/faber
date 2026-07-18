---
name: faber-proof
description: Prove, verify, audit, or evidence-drive the repair of an AI-generated patch with Faber Proof. Use when a user explicitly asks for Faber Proof, proof-carrying patch evidence, the Build Week replay demo, or a repair based on a Faber BLOCK counterexample; do not trigger for ordinary test-only requests.
---

# Faber Proof

Prove the exact patch against owner-approved policy. Keep model analysis advisory and
authoritative Faber evidence decisive.

## Workflow

1. Read the user-named task contract and proof configuration. For the Build Week
   fixture, read `examples/build-week-proof/README.md`. Inspect repository state and
   resolve the exact base and candidate revisions without disturbing unrelated work.
2. Choose live or replay explicitly and invoke `faber proof` with explicit `--repo`,
   `--task`, `--catalog`, `--base`, `--candidate`, `--mode`, and `--out-dir`; add
   `--replay` only for an exact matching reviewed bundle.
3. Read `run-summary.json` and `proof-decision.json` as machine authority. Stop at
   `HUMAN_REVIEW`; never infer success from prose, rationale, color, or a score.
4. On `BLOCK`, identify the failed required claim and concrete counterexample. If
   repair was requested, change only candidate code and preserve task, policy, tests,
   and unrelated behavior.
5. Rerun ordinary tests and Faber Proof. A changed diff requires new live planning or
   an exact matching reviewed replay; never reuse a stale pre-repair bundle.
6. Report exact commands and revisions, verdict, evidence and report paths, replay
   provenance, and remaining platform or isolation limitations.

## Integrity

- Never replace evidence with model rationale, bypass a required obligation, or change
  an expectation to match a defect.
- Never edit the task, catalog, replay, proof policy, or expected evidence merely to
  turn a failure green.
- Do not claim production sandbox isolation; the local runner discloses its limits.
- Preserve unrelated user changes.

Read [artifact-contract.md](references/artifact-contract.md) when interpreting bundles,
replay provenance, or repair boundaries. Run the skill validator only after changing
the skill or its referenced contract:

```bash
python .agents/skills/faber-proof/scripts/validate_skill.py --run-replay
```

Examples:

```text
$faber-proof prove the current patch against .faber/task-contract.json
$faber-proof run the Build Week replay demo and explain the BLOCK counterexample
```
