# 0025 - Worker And Harness Metadata Registry

## Goal

Extend the worker registry to represent model, harness, and environment metadata.

## Scope

Add or extend records for:

- `ModelManifest`
- `HarnessManifest`
- `EnvironmentManifest`
- metadata disclosure levels;
- metadata trust levels;
- NixOS support field;
- capability matching for task routing.

## Requirements

- Do not add real provider integrations.
- Solvers can disclose exact model/harness details or a coarse class.
- Attestation level must be explicit.
- Router logic can use metadata, but it must know whether metadata is
  self-attested, runner-attested, platform-observed, repo-owner-verified, or
  provider-attested.
- Platform support must be explicit enough to distinguish NixOS, Linux, macOS,
  and Windows where relevant.

## Tests

Add tests for:

- matching tasks to workers based on capabilities;
- matching tasks to workers based on platform support;
- coarse disclosure class behavior;
- exact model/harness disclosure behavior;
- routing behavior when metadata is self-attested versus observed.

## Acceptance Criteria

- Metadata is useful for routing without becoming unquestioned truth.
- No provider-specific model APIs or harness packages are added.
- Faber can measure model-harness-environment fit per task class.
