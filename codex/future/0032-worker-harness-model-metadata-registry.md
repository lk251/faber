# 0032 — Worker, harness, and model metadata registry

## Goal

Extend Faber's worker registry so routing can learn from model, harness, environment, disclosure, and platform-support metadata.

## Scope

Add or extend:

- `ModelManifest`
- `HarnessManifest`
- `EnvironmentManifest`
- disclosure levels
- trust/provenance levels
- platform support fields
- capability matching

## Requirements

- No real provider integrations.
- Allow exact, coarse, and private disclosure modes.
- Capture NixOS, Linux, macOS, Windows, container, and remote-runner support.
- Router can use metadata while preserving provenance/trust levels.
- Cost model must use integer minor units.
- Do not require proprietary solver internals.

## Tests

- exact/coarse/private disclosure modes
- routing with platform requirements
- NixOS-specific task matching
- self-attested versus runner-attested metadata
- digest stability

## Acceptance criteria

Faber can record enough solver attributes for supervised router learning without requiring solvers to disclose private implementation details.