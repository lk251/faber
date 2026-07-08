# Trace strategy

Faber should distinguish three related artifacts.

A **raw trace** is the event stream from a solver run: observed commands, tool calls, file/context reads, patch checkpoints, tests, verifier feedback, timestamps, cost/latency, and optional human interventions.

A **trajectory** is the normalized Faber training and audit object built from task contract, attempt, worker metadata, trace evidence, verifier result, review signal, cost, settlement, and outcome.

An **episode package** is the strongest replayable bundle: task contract, repo/environment snapshot, solver manifests, trace JSONL, patch, verifier reports, review/settlement evidence, redaction policy, and digests.

## Why PR-only is not enough

A GitHub PR gives a final diff, commit history, CI signal, and review outcome. That is useful for weak supervised labels, but it loses how the solution was produced: which files were inspected, what failed, what recovered, which verifier feedback mattered, how much compute was spent, and what harness/model/environment produced the work.

Faber should accept PR-only submissions early, but treat them as low-evidence submissions. Richer traces should unlock stronger reputation, eligibility, and possibly better economics.

## Evidence ladder

- Level 0: PR-only fallback. Captures issue, PR, diff, CI/check signal, review comments, and final verifier receipt.
- Level 1: PR plus `.faber/attempt.json`. Adds solver, model/harness disclosure, environment digest, cost/latency, trace level, and redaction policy.
- Level 2: Faber Runner trace. Adds Faber-normalized event JSONL from a controlled local run.
- Level 3: harness-native trace adapter. Converts Codex, Hermes, OpenHands, SWE-agent, or other harness logs into Faber TraceEvents.
- Level 4: replayable episode package. Adds environment locks, verifier specs, raw/normalized traces, artifacts, and replay instructions.

## Learning uses

- Supervised router learning can use task features, worker metadata, attempt outcome, cost, latency, and review friction.
- Attempt quality prediction can use task, diff, CI signal, manifest metadata, verifier output, and review outcome.
- Harness/orchestration learning needs trace events: context selection, command/tool use, patch checkpoints, verifier feedback, retries, and interventions.
- Reinforcement learning needs episode-like state/action/observation/reward records; Faber can start with high-level rewards before token-level or step-level policies.
- Verifier calibration needs agreement between advisory scores, hard verifiers, human review, costs, and downstream outcomes.

## Privacy and disclosure

Faber must not require solvers to reveal private prompts, finetune weights, proprietary harness internals, or chain-of-thought. It should support disclosure levels, redaction policies, and provenance tags.

Useful provenance tags include:

- `self_attested`
- `runner_attested`
- `platform_observed`
- `repo_owner_verified`
- `provider_attested`

## Incentives

Trace richness should be market-aligned:

- tasks may declare a minimum evidence level
- richer traces may qualify for higher rewards or bonuses
- premium tasks may require Level 2 or Level 4 evidence
- high-quality traces should improve worker reputation
- redacted traces should be allowed when the task policy permits them

## Platform stance

Do not require full traces on day one. Faber should be easy to adopt with PR-only submissions, while making the highest-quality training data economically and reputationally valuable.