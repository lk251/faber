# 0027 - NixOS Agent Harness Bounty Pilot

## Goal

Design a Faber dogfood bounty for NixOS-first agent harness support.

This issue is investigation and design first. Do not assume Hermes has or lacks
first-class NixOS support. Inspect available docs, issues, and upstream signals
before making claims or choosing a target.

## Scope

Candidate target:

- Hermes, if investigation confirms a clear NixOS support gap and the task is
  valuable to the harness community.
- Otherwise choose another important agent harness with a clear NixOS gap.

Create `docs/bounties/NIXOS_AGENT_HARNESS_PILOT.md`.

Define:

- a Faber `TaskContract` fixture for the bounty;
- required trace level for bounty attempts;
- how the bounty could attract harness community contributors;
- why the bounty is not a dependency of Faber itself.

## Acceptance Criteria For The Bounty

The candidate upstream contribution should provide:

- Nix flake or dev shell;
- reproducible setup;
- tests passing on NixOS;
- docs for NixOS users;
- CI or local verifier command;
- no hidden manual steps;
- clear upstream contribution path.

## Verifier Specs To Design

- flake check;
- setup smoke test;
- harness smoke test;
- docs presence.

## Requirements

- Do not make claims about Hermes status until investigated.
- Do not add real model provider APIs.
- Do not make this bounty a dependency of Faber.
- Keep all verifier specs local, deterministic, and auditable.

## Tests

Add fixture tests for:

- task contract shape;
- verifier spec shape;
- trace level requirement;
- acceptance-criteria checklist completeness.

## Acceptance Criteria

- The pilot design is actionable but does not require external changes during this
  issue.
- The selected target is justified by evidence.
