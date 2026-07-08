# Solver metadata

Faber needs solver metadata to learn which workers, harnesses, environments, and verification policies produce the most value per euro. This metadata should be useful without forcing solvers to reveal proprietary secrets.

## Stable metadata: WorkerProfile

A `WorkerProfile` describes a worker or solver over time:

- worker id
- operator id
- display name
- capabilities
- supported task types
- supported languages/frameworks
- supported platforms: NixOS, Linux, macOS, Windows, containers, remote runners
- model family or disclosure class
- harness family
- cost model in integer minor units
- availability/status
- reputation summary
- metadata trust level

## Per-attempt metadata: AttemptManifest

An `.faber/attempt.json` manifest describes one run:

- task contract id and digest
- attempt id
- base revision
- candidate revision
- worker id
- model identifier or disclosure class
- harness identifier and version
- runner identifier and version
- environment digest
- tool registry digest
- Nix flake lock digest when available
- budget/cost metadata
- latency metadata
- evidence level
- redaction policy
- attestation signature when available

## Other manifests

- `TraceManifest`: describes raw and normalized trace files, event counts, redactions, and digests.
- `HarnessManifest`: describes the harness, adapters, tool interfaces, and known platform support.
- `ModelManifest`: describes the model family or disclosed model id without requiring private weights.
- `EnvironmentManifest`: records OS, platform, package manager, lockfiles, relevant runtime versions, and reproducibility level.
- `Attestation`: records who or what produced the metadata and what trust level it carries.

## Trust levels

Metadata is not automatically true. Record provenance explicitly:

- `self_attested`: supplied by solver/operator.
- `runner_attested`: captured by Faber Runner or a trusted harness adapter.
- `platform_observed`: observed by Faber infrastructure.
- `repo_owner_verified`: confirmed by repository owner or maintainer.
- `provider_attested`: confirmed by a model, execution, or payment provider through an adapter.

Routing can use self-attested data, but should weight it differently from observed or attested data.

## Disclosure levels

Faber should allow solvers to disclose exact, coarse, or private metadata:

- exact: `qwen3-coder-480b`, `codex-cli 0.x`, `hermes-agent v0.18.0`
- coarse: `frontier-closed-code-model`, `local-open-weight-32b`, `custom-harness`
- private: undisclosed, but with trace/cost/outcome evidence

The market can reward greater transparency without banning proprietary solvers.

## Why this matters

Supervised routing needs worker attributes before the attempt. Attempt quality prediction needs attempt-level metadata. Orchestration learning needs trace events. Intelligence-per-euro accounting needs cost, latency, outcome, and verifier quality. All of this must be captured as structured data rather than hidden in PR prose.