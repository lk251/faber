# 0046 — RL-grade trajectory by default

## Goal

Make Faber default to collecting RL-grade trajectory data for Faber-native paid or training-eligible work, regardless of which solver, agent, harness, model, or platform produced the attempt.

This issue should turn the strategic principle into protocol objects, validation gates, docs, and tests.

## Design position

Faber should optimize for **successful verified trajectories**, not merely accepted PRs.

A raw trace is only the event stream from a solver run. An RL-grade trajectory is the normalized episode object that binds:

- task contract and verifier policy
- environment and repository snapshot evidence
- solver/worker/harness/model metadata with provenance
- action/observation trace or equivalent process evidence
- final artifact or patch
- verifier runs and authoritative receipt
- reward/cost/latency/review signal
- settlement/work-budget outcome when applicable
- redaction and disclosure policy
- stable digests

## Important product stance

Do not make Faber unusable by requiring everyone to reveal proprietary internals.

Instead:

- Faber-native paid work should declare a minimum trajectory quality requirement.
- Training-eligible trajectories should require RL-grade evidence.
- PR-only submissions can still exist as `low_evidence` or `imported` records, but should not be treated as high-quality RL training data.
- Solvers may use disclosure levels and redaction policies.
- Proprietary harnesses can submit structured event summaries or attested traces without revealing private prompts, finetune weights, or chain-of-thought.
- Task contracts can require richer evidence for higher rewards, premium tasks, or training consent.

## Scope

Add or extend protocol concepts for:

- `TrajectoryQualityTier`
- `TrajectoryRequirement`
- `EvidenceLevel`
- `TrainingEligibility`
- `TraceCompleteness`
- `ProcessEvidence`
- `RewardSignal`
- `EnvironmentReplayability`
- `TrajectoryValidationReport`
- `TrajectoryConsent` or equivalent training-use flag

## Suggested quality tiers

- `pr_only`: final diff and outcome only; useful but not RL-grade.
- `manifest`: PR plus `.faber/attempt.json`; useful for router supervised learning.
- `trace`: manifest plus action/observation trace JSONL; candidate RL-grade if verifier/reward data is present.
- `episode`: replayable episode package; strongest RL-grade tier.

## RL-grade minimum fields

Define an RL-grade trajectory as requiring at least:

1. task contract id and digest
2. base environment/repository snapshot reference
3. attempt id and worker id
4. solver metadata with provenance/disclosure level
5. environment evidence
6. ordered process evidence: action/observation trace, or a declared/attested equivalent
7. candidate artifact reference: patch, commit, output, or generated artifact
8. verifier run(s)
9. authoritative verification receipt or explicit unsuccessful terminal outcome
10. reward/outcome signal
11. cost and latency metadata where available
12. redaction policy
13. training eligibility/consent flag
14. stable digest of the complete trajectory record

## Validation behavior

Implement validation that can answer:

- is this trajectory usable for audit?
- is this trajectory usable for supervised router training?
- is this trajectory usable for attempt-quality prediction?
- is this trajectory usable for RL/harness/orchestration training?
- is this trajectory accepted and positive?
- is this trajectory failed but still useful as negative/process data?
- why is this trajectory not RL-grade?

Validation should produce a structured report, not only raise exceptions.

## Integration points

- `TaskContract` should be able to declare minimum trajectory requirement.
- `AttemptManifest` should declare evidence level and training-use consent.
- GitHub PR adapter should mark PR-only attempts as low evidence by default.
- Faber Runner traces should usually satisfy the trace-level requirement.
- Harness-native adapters should be able to satisfy trace-level or episode-level requirements if their data validates.
- Dataset export should include quality tier and training eligibility.
- Work budgets may require a minimum quality tier before full payout or bonus eligibility, but settlement must still require authoritative verification.

## Inadvisable edge to avoid

Do not make Faber reject all PR-only external work globally. That would hurt adoption and make the market less useful. Instead, make the distinction explicit:

- accepted work can be useful to a customer even when not RL-grade
- RL-grade training eligibility requires richer evidence
- premium/payout/bonus policies can require richer evidence task by task

## Tests

Add tests for:

- PR-only attempt validates as low evidence but not RL-grade
- manifest-backed attempt validates for supervised/router training but not RL-grade unless process evidence exists
- trace-backed attempt validates as RL-grade when verifier/reward/outcome fields are present
- replayable episode package validates as the highest tier
- missing reward signal makes trace non-RL-grade
- missing process evidence makes successful PR non-RL-grade
- redacted trace can still be RL-grade if required fields remain
- task requiring RL-grade rejects PR-only attempt for full eligibility
- training-ineligible trajectory is not exported into training dataset by default
- failed trajectory can be RL-useful as negative/process data when process evidence exists

## Docs

Update or create:

- `docs/TRACE_STRATEGY.md`
- `docs/TRAJECTORY_SCHEMA.md`
- `docs/DATA_REQUIREMENTS.md` if present
- `docs/REPRODUCIBILITY_AND_PLATFORMS.md`
- `docs/FUNDING_AND_WORK_BUDGETS.md`

Docs should clearly define:

- raw trace
- normalized trajectory
- RL-grade trajectory
- positive/successful trajectory
- failed but useful trajectory
- PR-only low-evidence record
- why Faber wants RL-grade data by default
- why Faber still accepts lower-evidence work when explicitly allowed

## Non-goals

- Do not train models.
- Do not add ML frameworks.
- Do not add real model provider integrations.
- Do not require private prompts, chain-of-thought, finetune weights, or proprietary harness internals.
- Do not add real payment provider integrations.
- Do not make NixOS mandatory for every task.
- Do not make GitHub the root abstraction.

## Acceptance criteria

- Faber has explicit trajectory quality tiers.
- Faber can validate whether a trajectory is RL-grade.
- Task contracts can require RL-grade or lower evidence tiers.
- Dataset export can filter for RL-grade training-eligible trajectories.
- PR-only work remains possible but is clearly low-evidence.
- Tests prove the boundary between accepted customer work and RL-grade training data.
- Docs explain the design tradeoff clearly.
