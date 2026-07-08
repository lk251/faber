# Solver Metadata

Solver metadata tells Faber who did the work, what system produced the attempt,
where it ran, how much it cost, and how much trust Faber should place in each
claim. Metadata is provenance-tagged. It is useful evidence, not automatically
truth.

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
- trace level;
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

- `self_attested`: supplied by the solver or worker without independent evidence.
- `runner_attested`: observed or signed by Faber Runner or another approved
  runner.
- `platform_observed`: observed by Faber's platform or adapter boundary.
- `repo_owner_verified`: confirmed by a repository owner or task owner.
- `provider_attested`: signed or otherwise attested by an external provider
  adapter.

Trust level should be explicit on every solver-supplied field that affects
routing, selection, payment eligibility, or training use.

## WorkerProfile

`WorkerProfile` is stable worker metadata.

Fields should include:

- worker id;
- operator id;
- display name;
- capabilities;
- supported task types;
- supported languages and frameworks;
- supported platforms, such as NixOS, Linux, macOS, and Windows where relevant;
- model family or disclosure level;
- harness family;
- cost model in integer minor units;
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
- trace level;
- redaction policy;
- attestation signature if available.

The manifest is optional for early GitHub adoption. If present, it should validate
strictly and produce clear warnings when evidence is malformed or untrusted.

## TraceManifest

`TraceManifest` describes a trace bundle or JSONL trace export.

Fields should include:

- trace id;
- attempt id;
- evidence level;
- trace event count;
- trace JSONL digest;
- redaction policy id;
- redaction report digest;
- included event classes;
- excluded event classes;
- privacy notes;
- provenance and trust level.

## HarnessManifest

`HarnessManifest` describes the system that orchestrated the solver attempt.

Fields should include:

- harness id;
- harness family;
- version or digest;
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

Faber should not require solvers to reveal proprietary prompts, private
chain-of-thought, finetune weights, or provider secrets.

## EnvironmentManifest

`EnvironmentManifest` describes the execution environment.

Fields should include:

- environment id;
- operating system or platform;
- architecture;
- dependency lock digest;
- Nix flake lock digest if available;
- tool registry digest;
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
