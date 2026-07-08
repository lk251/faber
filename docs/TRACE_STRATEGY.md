# Trace Strategy

Faber is verifier-first and trajectory-first. A pull request is a useful artifact,
but it is only one view of the work. For training, routing, verifier calibration,
and intelligence-per-euro measurement, Faber needs a ladder of trace evidence
that starts with low-friction PR submissions and can grow into replayable episode
packages for high-trust tasks.

## Terms

Raw trace:
An ordered record emitted by a solver, runner, harness, tool, or verifier during
work. Raw traces may contain tool calls, commands, observations, context
references, verifier runs, errors, interventions, timing, costs, and redaction
markers. Raw traces are not automatically safe to store or train on.

Normalized trajectory:
A Faber Protocol record that summarizes task context, routing, worker identity,
attempt metadata, verifier outcome, review signal, cost, latency, reward, margin,
and final outcome. A normalized trajectory is stable, digestable, and suitable for
audit and dataset export.

Episode package:
A higher-fidelity bundle that can be inspected or replayed. It may include raw
trace JSONL, normalized Faber trajectory records, manifests, environment digests,
tool registry digests, verifier receipts, redaction reports, intervention logs,
and reproduction instructions.

## Why PR-Only Is Useful But Insufficient

A PR-only submission can tell Faber what changed, who submitted it, what base and
candidate revisions were involved, and whether authoritative verification
accepted the result. That is enough for basic marketplace verification and weak
supervised labels.

It is not enough to learn how the work happened. A PR usually loses:

- model, harness, runner, environment, and tool metadata;
- cost and latency attribution;
- failed intermediate attempts;
- intervention and recovery evidence;
- verifier progress signals;
- context pressure and maintenance burden;
- enough process data for reinforcement learning or harness imitation.

Faber should not require full traces on day one because adoption friction matters.
Instead, it should reward richer, provenance-tagged evidence when a task benefits
from it.

## Evidence Ladder

### Level 0: PR-Only Fallback

Captures:

- repository;
- pull request number or candidate revision;
- base revision;
- patch digest;
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
- reinforcement learning: still weak, unless progress fields are included later;
- verifier calibration: cost and environment stratification.

### Level 2: Faber Runner Trace

Captures Level 1 plus Faber Runner events:

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
- verifier receipts;
- setup and replay commands;
- intervention and redaction reports;
- reproduction limitations.

Supports:

- marketplace verification: strongest local audit path;
- supervised router learning: best dataset quality;
- attempt quality prediction: best process/outcome correlation;
- harness/orchestration learning: best non-private replay data;
- reinforcement learning: best source for dense rewards and offline analysis;
- verifier calibration: strongest calibration and failure-attribution evidence.

## Privacy And Redaction

Trace evidence can contain secrets, private prompts, customer data, repository
context, tool outputs, credentials, and solver IP. Faber should support:

- disclosure levels instead of requiring exact model or prompt details;
- explicit redaction policies;
- hashes and digests for private artifacts;
- raw-log exclusion with digest retention;
- private chain-of-thought exclusion;
- customer-data minimization;
- consent and licensing metadata for training use.

Richer traces should be accepted only when they fit the task's privacy policy.
Redacted traces can still be valuable if they preserve structure, timing, tool
types, verifier evidence, and outcome labels.

## Solver Incentives

Faber can encourage richer traces through:

- eligibility for premium tasks;
- trace-quality reputation;
- higher router preference when trace value is relevant;
- optional trace bonuses in task contracts;
- faster dispute resolution;
- better verifier calibration and fewer false rejects;
- clearer attribution for harness, model, and environment quality.

This should be opt-in at first. A global full-trace requirement would exclude
useful solvers, proprietary systems, and ordinary open-source contributors.

## Adoption Strategy

1. Keep PR-only submissions valid.
2. Add `.faber/attempt.json` as the first low-friction manifest.
3. Let Faber Runner emit trace summaries for tasks that require stronger evidence.
4. Add harness-native adapters only as schemas and fake fixtures first.
5. Use replayable episode packages for premium, high-trust, or calibration tasks.
6. Reward richer evidence without making private reasoning disclosure mandatory.
