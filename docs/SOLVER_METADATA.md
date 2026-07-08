# Solver Metadata

Faber needs solver metadata to learn which workers, harnesses, models,
environments, and verification policies produce the most value per euro. This
metadata should be useful without forcing solvers to reveal proprietary secrets.
It is provenance-tagged evidence, not automatically truth.

## Stable And Per-Attempt Metadata

Stable metadata describes a worker or system over many tasks:

- `WorkerProfile`
- recurring model disclosure class;
- harness family;
- supported platforms;
- capability and reputation summaries;
- default cost model.

Per-attempt metadata describes one attempt:

- `AttemptManifest`
- trace or evidence level;
- exact base and candidate revisions;
- environment digest;
- tool registry digest;
- Nix flake lock digest if available;
- cost and latency;
- redaction policy;
- attestation.

Faber should prefer stable metadata for routing priors and per-attempt metadata
for audit, verifier calibration, and training examples.

## Metadata Trust Levels

Metadata is not automatically true. Record provenance explicitly:

- `self_attested`: supplied by the solver or worker without independent evidence.
- `runner_attested`: observed or signed by Faber Runner or another approved
  runner.
- `platform_observed`: observed by Faber's platform or adapter boundary.
- `repo_owner_verified`: confirmed by a repository owner, task owner, or
  maintainer.
- `provider_attested`: signed or otherwise attested by an external provider
  adapter.

Routing can use self-attested data, but should weight it differently from
observed or attested data. Trust level should be explicit on every
solver-supplied field that affects routing, selection, payment eligibility, or
training use.

## Disclosure Levels

Faber should allow solvers to disclose exact, coarse, or private metadata:

- exact: concrete model or harness identifiers such as `qwen3-coder-480b`,
  `codex-cli 0.x`, or `hermes-agent v0.18.0`;
- coarse: classes such as `frontier-closed-code-model`,
  `local-open-weight-32b`, or `custom-harness`;
- private: undisclosed details with trace, cost, and outcome evidence.

The market can reward greater transparency without banning proprietary solvers.
Faber should not require solvers to reveal proprietary prompts, private
chain-of-thought, finetune weights, private model weights, or provider secrets.

## WorkerProfile

`WorkerProfile` is stable worker metadata.

Fields should include:

- worker id;
- operator id;
- display name;
- capabilities;
- supported task types;
- supported languages and frameworks;
- supported platforms, such as NixOS, Linux, macOS, Windows, containers, and
  remote runners where relevant;
- model family or disclosure level;
- harness family;
- cost model in integer minor units;
- availability or status;
- reputation summary;
- metadata trust level.

## AttemptManifest

`AttemptManifest` is per-attempt metadata. A low-friction version can live at
`.faber/attempt.json` in a pull request.

Fields should include:

- task contract id and digest;
- attempt id;
- base revision;
- candidate revision;
- worker id;
- model identifier or disclosure class;
- harness identifier and version;
- runner identifier and version;
- environment digest;
- tool registry digest;
- Nix flake lock digest if available;
- budget and cost metadata using integer minor units;
- latency metadata;
- training-use consent and allowed-use policy;
- evidence level;
- trace level when distinct from evidence level;
- redaction policy;
- attestation signature if available.

The manifest is optional for early GitHub adoption. If present, it should validate
strictly and produce clear warnings when evidence is malformed or untrusted.
Manifest-backed attempts can support supervised/router training, but they are not
RL-grade unless paired with process trace evidence, reward signal, replayability
evidence, verifier outcome, and training eligibility.

## TraceManifest

`TraceManifest` describes a trace bundle or JSONL trace export.

Fields should include:

- trace id;
- attempt id;
- evidence level;
- trace event count;
- raw trace digest where retained;
- normalized trace JSONL digest;
- redaction policy id;
- redaction report digest;
- included event classes;
- excluded event classes;
- privacy notes;
- provenance and trust level.

For RL-grade validation, trace manifests should preserve enough event-class
coverage to prove process evidence even when raw payloads are redacted. At a
minimum, the normalized trajectory needs ordered context, action or tool, and
verifier or outcome evidence.

## HarnessManifest

`HarnessManifest` describes the system that orchestrated the solver attempt.

Fields should include:

- harness id;
- harness family;
- version or digest;
- adapter interface version;
- tool interfaces;
- runner compatibility;
- supported trace adapter version;
- supported platforms;
- known limitations;
- provenance and trust level.

## ModelManifest

`ModelManifest` describes the solver model at a disclosure level acceptable to
the worker and task policy.

Fields should include:

- model identifier, family, or disclosure class;
- hosted, local, open, proprietary, or undisclosed class;
- finetune or adapter disclosure class;
- context budget class;
- cost class or cost model;
- provenance and trust level.

## EnvironmentManifest

`EnvironmentManifest` describes the execution environment.

Fields should include:

- environment id;
- operating system or platform;
- architecture;
- package manager;
- dependency lock digest;
- Nix flake lock digest if available;
- tool registry digest;
- relevant runtime versions;
- reproducibility level;
- runner policy digest;
- setup command digest;
- verifier command digest;
- provenance and trust level.

## Attestation

`Attestation` records who or what vouched for metadata.

Fields should include:

- attestation id;
- subject id and digest;
- issuer;
- trust level;
- signature or signed digest if available;
- issued_at timestamp;
- expiration timestamp if applicable;
- verification method;
- limitations.

Attestation can improve routing and eligibility, but it should not override
authoritative verification or settlement rules.

## Why This Matters

Supervised routing needs worker attributes before the attempt. Attempt quality
prediction needs attempt-level metadata. Orchestration learning needs trace
events. Intelligence-per-euro accounting needs cost, latency, outcome, and
verifier quality. All of this must be captured as structured data rather than
hidden in pull request prose.
