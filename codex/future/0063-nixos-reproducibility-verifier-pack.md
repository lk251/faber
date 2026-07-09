# 0063 — NixOS reproducibility verifier pack

## Goal

Create a reusable verifier pack for NixOS-first tasks and replayable agent episodes.

## Scope

Add verifier specs or fixtures for:

- `nix flake check`
- `nix develop` smoke command
- lockfile/digest presence
- package import smoke test
- local CLI smoke test
- docs command validation

## Requirements

- Keep this as local verifier specs, not a production sandbox.
- Do not make Nix mandatory for all Faber tasks.
- Task contracts may opt into the pack.
- Store verifier outputs as digests and structured metrics.
- Support a fake mode for environments without Nix in CI.

## Tests

- verifier spec digests are stable
- task requiring Nix pack validates verifier references
- fake Nix verifier success/failure fixtures
- missing lockfile produces warning or failure by policy

## Acceptance criteria

Faber can define high-replayability NixOS tasks with reusable verifier policy.