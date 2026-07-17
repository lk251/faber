---
name: faber-proof
description: Prove, verify, audit, or evidence-drive the repair of an AI-generated patch with Faber Proof. Use when a user explicitly asks for Faber Proof, proof-carrying patch evidence, the Build Week replay demo, or a repair based on a Faber BLOCK counterexample; do not trigger for ordinary test-only requests.
---

# Faber Proof

Use the owner-approved task contract, proof catalog, and Faber evidence to prove the
exact patch. Keep model analysis advisory and authoritative verifier evidence decisive.

## Workflow

1. Read the task contract and proof configuration named by the user. For the Build Week
   fixture, first read `examples/build-week-proof/README.md`.
2. Run `git status --short`, resolve the repository root, base revision, candidate
   revision, and `HEAD`, and preserve unrelated user changes.
3. Choose an explicit mode. Use replay only when its externally pinned bundle binds to
   the exact current task, catalog, request, and diff. After any changed diff, use a
   separately reviewed matching replay, rerun live planning, or stop with the precise
   human action required.
4. Invoke `faber proof` with explicit `--repo`, `--task`, `--catalog`, `--base`,
   `--candidate`, `--mode`, and `--out-dir`; include `--replay` only in replay mode.
5. Read `run-summary.json` and `proof-decision.json`. Never infer the verdict from
   prose, model rationale, terminal color, or a score.
6. If the verdict is `BLOCK`, identify the failed required claim and bounded concrete
   counterexample. If repair was requested, make the smallest code change that
   satisfies that evidence without weakening the task, proof catalog, policy, ordinary
   tests, or unrelated behavior.
7. Run the ordinary tests and Faber Proof again. In live mode, rerun the planner for the
   new diff. In replay mode, never reuse the stale pre-repair bundle.
8. Stop at `HUMAN_REVIEW`. Do not claim success without an authoritative `PASS`.
9. Report exact commands, full base and candidate revisions, verdict, evidence/report
   paths, replay provenance, and remaining isolation or platform limitations.

## Integrity rules

- Do not treat model rationale as proof or replace evidence with a model score.
- Do not bypass a required obligation or change a test expectation to match a defect.
- Do not edit the task, catalog, replay, proof policy, or expected evidence merely to
  turn a failure green. Only redesign policy when the user explicitly asks for it.
- Do not use a replay that does not bind to the current task and diff.
- Do not claim production sandbox isolation; the local runner discloses its limits.
- Do not modify unrelated files silently.

Read [artifact-contract.md](references/artifact-contract.md) when interpreting bundles,
replay provenance, or repair boundaries. Validate this skill with:

```bash
python .agents/skills/faber-proof/scripts/validate_skill.py --run-replay
```

## Examples

```text
$faber-proof prove the current patch against .faber/task-contract.json
```

```text
$faber-proof run the Build Week replay demo and explain why the first patch is blocked
```

```text
$faber-proof use live GPT-5.6 to prove this patch, repair only demonstrated failures,
and rerun the proof
```
