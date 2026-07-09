# 0064 — Cross-platform agent harness fixtures

## Goal

Add fake but realistic fixtures for solver attempts from NixOS, Linux, macOS, Windows, containers, and remote runners.

## Scope

Create fixtures that exercise environment evidence and trajectory validation across platforms.

## Requirements

- Include one fixture per platform family.
- Include environment metadata, attempt manifest, trace sample, verifier result, and trajectory record.
- Use fake data only.
- Mark reproducibility level clearly.
- Demonstrate that non-Nix contributions are still useful but have different evidence strength.

## Tests

- all fixtures validate
- Nix fixture has strongest replay evidence
- Windows/macOS/Linux fixtures remain training-eligible if they meet process evidence and consent requirements
- platform-specific task requirements reject incompatible attempts

## Acceptance criteria

Faber's platform policy is tested rather than merely documented.