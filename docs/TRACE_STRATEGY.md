# Trace Strategy

Faber is verifier-first and trajectory-first. A pull request is a useful artifact,
but it is only one view of the work. For training, routing, verifier calibration,
and intelligence-per-euro measurement, Faber needs a ladder of trace evidence
that starts with low-friction PR submissions and can grow into replayable episode
packages for high-trust tasks.

## Terms

Raw trace:
An ordered record emitted by a solver, runner, harness, tool, or verifier during
work. Raw traces may contain observed commands, tool calls, file and context
reads, patch checkpoints, tests, verifier feedback, errors, interventions,
timestamps, costs, latency, and redaction markers. Raw traces are not
automatically safe to store or train on.

Normalized trajectory:
A Faber Protocol record that summarizes task context, routing, worker identity,
attempt metadata, trace evidence, verifier outcome, review signal, cost,
settlement, and final outcome. A normalized trajectory is stable, digestable, and
suitable for audit and dataset export.

Episode package:
A higher-fidelity bundle that can be inspected or replayed. It may include the
task contract, repository or environment snapshot, raw trace JSONL, normalized
Faber trajectory records, solver manifests, environment digests, tool registry
digests, verifier reports, verifier receipts, redaction policy, redaction reports,
intervention logs, reproduction instructions, and stable digests.

## Why PR-Only Is Useful But Insufficient

A GitHub PR gives a final diff, commit history, CI signal, review comments, and
review outcome. That is useful for basic marketplace verification and weak
supervised labels.

It is not enough to learn how the work happened. A PR usually loses:

- model, harness, runner, environment, and tool metadata;
- files and context inspected during the attempt;
- cost and latency attribution;
- failed intermediate attempts;
- intervention and recovery evidence;
- verifier progress signals;
- context pressure and maintenance burden;
- enough process data for reinforcement learning or harness imitation.

Faber should accept PR-only submissions early, but treat them as low-evidence
submissions. Richer traces should unlock stronger reputation, eligibility, and
possibly better economics when a task benefits from them.

## Evidence Ladder

### Level 0: PR-Only Fallback

Captures:

- repository and issue;
- pull request number or candidate revision;
- diff, commit history, and patch digest;
- base revision;
- CI or check signal as non-authoritative evidence;
- review comments and review outcome;
- worker id if known;
- authoritative verifier receipt if available;
- final outcome.

Supports:

- marketplace verification: yes, if an authoritative verifier or human review
  accepts the work;
- supervised router learning: weak labels only;
- attempt quality prediction: final outcome and patch metadata only;
- harness/orchestration learning: no;
- reinforcement learning: no dense signal;
- verifier calibration: limited to final outcome agreement.

### Level 1: PR + `.faber/attempt.json` Manifest

Captures Level 0 plus:

- task contract id and digest;
- attempt id;
- worker id;
- model disclosure class or model identifier;
- harness identifier and version;
- runner identifier and version;
- environment digest;
- tool registry digest;
- Nix flake lock digest if available;
- budget and cost metadata using integer minor units;
- latency metadata;
- trace level;
- redaction policy;
- solver attestation if available.

Supports:

- marketplace verification: stronger provenance around who and what produced the
  work;
- supervised router learning: worker, harness, platform, and cost features;
- attempt quality prediction: metadata-to-outcome examples;
- harness/orchestration learning: coarse metadata only;
- reinforcement learning: still weak unless progress fields are included later;
- verifier calibration: cost and environment stratification.

### Level 2: Faber Runner Trace

Captures Level 1 plus Faber Runner events:

- Faber-normalized event JSONL from a controlled local run;
- command and tool execution summaries;
- stdout/stderr digests, not necessarily raw logs;
- verifier run events;
- runner policy digest;
- environment and working-directory policy;
- capture limits and timeout evidence;
- redaction reports.

Supports:

- marketplace verification: high, because runner-attested evidence narrows trust
  gaps;
- supervised router learning: better cost, latency, tool, and verifier features;
- attempt quality prediction: observable process features;
- harness/orchestration learning: partial process imitation;
- reinforcement learning: possible prefix/process rewards if progress scores are
  added;
- verifier calibration: strong verifier/run metadata.

### Level 3: Harness-Native Trace Adapter

Captures Level 2 plus normalized events from a solver harness:

- action traces;
- tool traces;
- context traces;
- verification traces;
- failure-attribution traces;
- intervention logs;
- entropy and maintenance evidence;
- outcome and recovery markers.

A Level 3 adapter may convert native Codex, Hermes, OpenHands, SWE-agent, or
other harness logs into Faber `TraceEvent` records. These adapters should start as
fake fixtures and schemas, not core dependencies on those harnesses.

Supports:

- marketplace verification: strong, subject to attestation and redaction;
- supervised router learning: strong harness/model/environment features;
- attempt quality prediction: strong process data;
- harness/orchestration learning: useful imitation and debugging evidence;
- reinforcement learning: prefix scores and process rewards become feasible;
- verifier calibration: rich comparison between process evidence and outcomes.

### Level 4: Replayable Episode Package

Captures Level 3 plus reproduction material:

- normalized trajectory bundle;
- raw or redacted trace JSONL;
- manifests;
- environment locks and digests;
- verifier specs and reports;
- setup and replay commands;
- artifacts;
- intervention and redaction reports;
- reproduction limitations.

Supports:

- marketplace verification: strongest local audit path;
- supervised router learning: best dataset quality;
- attempt quality prediction: best process/outcome correlation;
- harness/orchestration learning: best non-private replay data;
- reinforcement learning: best source for dense rewards and offline analysis;
- verifier calibration: strongest calibration and failure-attribution evidence.

## Learning Uses

- Supervised router learning can use task features, worker metadata, attempt
  outcome, cost, latency, and review friction.
- Attempt quality prediction can use task, diff, CI signal, manifest metadata,
  verifier output, and review outcome.
- Harness/orchestration learning needs trace events: context selection,
  command/tool use, patch checkpoints, verifier feedback, retries, and
  interventions.
- Reinforcement learning needs episode-like state/action/observation/reward
  records. Faber can start with high-level rewards before token-level or
  step-level policies.
- Verifier calibration needs agreement between advisory scores, hard verifiers,
  human review, costs, and downstream outcomes.

## Privacy And Disclosure

Trace evidence can contain secrets, private prompts, customer data, repository
context, tool outputs, credentials, and solver IP. Faber must not require solvers
to reveal private prompts, finetune weights, proprietary harness internals, or
chain-of-thought.

Faber should support:

- exact, coarse, and private disclosure levels;
- explicit redaction policies;
- hashes and digests for private artifacts;
- raw-log exclusion with digest retention;
- private chain-of-thought exclusion;
- customer-data minimization;
- consent and licensing metadata for training use;
- provenance tags such as `self_attested`, `runner_attested`,
  `platform_observed`, `repo_owner_verified`, and `provider_attested`.

Richer traces should be accepted only when they fit the task's privacy policy.
Redacted traces can still be valuable if they preserve structure, timing, tool
types, verifier evidence, and outcome labels.

## Incentives

Trace richness should be market-aligned:

- tasks may declare a minimum evidence level;
- richer traces may qualify for higher rewards or bonuses;
- premium tasks may require Level 2 or Level 4 evidence;
- high-quality traces should improve worker reputation;
- redacted traces should be allowed when task policy permits them;
- richer traces can speed dispute resolution;
- richer traces can improve verifier calibration and reduce false rejects;
- richer traces can improve attribution for harness, model, and environment
  quality.

This should be opt-in at first. A global full-trace requirement would exclude
useful solvers, proprietary systems, and ordinary open-source contributors.

## Platform Stance

Do not require full traces on day one. Faber should be easy to adopt with PR-only
submissions, while making the highest-quality training data economically and
reputationally valuable.

## Adoption Strategy

1. Keep PR-only submissions valid.
2. Add `.faber/attempt.json` as the first low-friction manifest.
3. Let Faber Runner emit trace summaries for tasks that require stronger evidence.
4. Add harness-native adapters only as schemas and fake fixtures first.
5. Use replayable episode packages for premium, high-trust, or calibration tasks.
6. Reward richer evidence without making private reasoning disclosure mandatory.
