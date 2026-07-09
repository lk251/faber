# Trajectory Schema

A trajectory captures the scarce training and audit record for verified work.

## Supervised Learning Fields

Supervised learning can use task contract text, requirements, repository or
environment snapshot references, router decisions, worker capabilities, attempt
summaries, patch references, tool/action summaries, and final accepted outputs.

## Reinforcement and Preference Learning Fields

Reinforcement learning and preference learning can use accepted, rejected,
declined, failed, and abandoned attempts. Failed or declined work still teaches
routers which choices waste time, increase review friction, or fail verifier
policy.

Reward, cost, latency, verifier outcome, review friction, and settlement metadata
matter because Faber optimizes intelligence per euro rather than raw pass rate or
raw cheapness.

## Quality Tiers

Faber separates trace capture from trajectory quality:

- `pr_only`: final artifact and authoritative outcome only. Valid customer work
  when the task allows it, but low-evidence and not RL-grade.
- `manifest`: PR plus `AttemptManifest`. Useful for supervised/router training
  and attempt quality prediction, but not RL-grade without process events.
- `trace`: manifest plus ordered Faber Runner or harness-native trace evidence.
  This can be RL-grade when reward, replayability, verifier outcome, and
  training-use consent are present.
- `episode`: replayable episode package with manifests, trace evidence,
  artifacts, and replay instructions. This is the highest-quality tier.

`TaskContract.trajectory_requirement` can declare a minimum quality tier, require
RL-grade evidence, require training eligibility, or set a richer tier for full
payout or bonus eligibility.

## RL-Grade Validation

An RL-grade trajectory requires:

- process evidence with ordered context/action/tool/verifier/outcome events;
- environment replayability evidence such as declared platform metadata,
  lockfile/container evidence, or a replayable episode package;
- solver metadata from `AttemptManifest`;
- an authoritative verifier receipt and outcome;
- explicit reward signal, plus cost and latency when available;
- consent or equivalent training-use eligibility.

Redacted traces can still be RL-grade when required event classes, digests,
reward, outcome, and environment evidence remain. Private prompts,
chain-of-thought, proprietary harness internals, and private model weights are
not required.

## Review and Verifier Quality

Human review signals should be captured without making human review the only
verifier. Human review can label ambiguity, maintainability, product fit, and
review friction.

Verifier quality may itself become a market and training signal. A verifier that
predicts durable acceptance, reduces disputes, and catches important failures is
valuable evidence.

## Dataset Export

Trajectories can be exported as canonical JSONL with one trajectory record per
line. Dataset manifests record source paths, record counts, schema versions,
accepted/rejected counts, total cost, total reward, margin, the JSONL digest, and
quality issues.

Exports attach a `trajectory_quality` validation report. Training dataset export
can filter for RL-grade and training-eligible records so PR-only and
training-ineligible trajectories are excluded by default from RL-grade training
sets.

Stable split assignment uses deterministic hashing of the trajectory id into
`train`, `validation`, and `test`, so records stay in the same split across runs.

Quality checks flag missing receipts, router decisions, cost metadata, outcomes,
and digest mismatches where the payload includes enough information to verify a
digest.

Redaction hooks are explicit field-path replacements. They should be used before
sharing datasets outside the trust boundary when task descriptions, review notes,
or repository metadata contain sensitive information.

Training and publication rights are evaluated separately from trajectory
quality. Repository defaults and stricter task-level `TrainingUsePolicy` records
must agree with solver/operator and repository-owner/customer consent grants.
Private records remain excluded from public datasets even when they are
RL-grade. Audit-only retention may preserve authoritative receipts without
granting model-training rights. See `docs/DATA_RIGHTS.md`.

Use the local validation commands documented in
`docs/TRAJECTORY_VALIDATION.md` to inspect manifests, trace JSONL, normalized
trajectories, and RL-grade quality before submission or export.
