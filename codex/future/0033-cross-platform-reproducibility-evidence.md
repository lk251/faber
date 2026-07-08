# 0033 — Cross-platform reproducibility evidence

## Goal

Make Faber NixOS-first but not NixOS-only by representing environment evidence across platforms.

## Scope

Add platform evidence records for NixOS, Linux, macOS, Windows, containers, and remote runners.

## Requirements

- Add an `EnvironmentEvidence` object or equivalent.
- Record OS family/version, architecture, package manager, lockfiles, runtime versions, setup entrypoint, verifier command, and reproducibility level.
- Record Nix flake lock digest when available.
- Support non-Nix environments without marking them useless.
- Let task contracts require a platform or minimum reproducibility level.
- Let router training learn platform-worker-task fit.

## Tests

- NixOS environment with flake digest
- macOS environment with package-manager metadata
- Windows environment with tool path metadata
- Ubuntu/container environment metadata
- task requiring NixOS rejects non-Nix evidence
- task with no platform constraint accepts cross-platform attempts

## Acceptance criteria

Faber can use NixOS for stronger replay evidence while still learning from and serving other platforms.