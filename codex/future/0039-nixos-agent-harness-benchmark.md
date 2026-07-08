# 0039 — NixOS agent harness benchmark

## Goal

Create a tiny offline benchmark fixture for agent harnesses under a Nix-first environment.

## Scope

Build a local benchmark that Hermes, Codex, OpenHands, SWE-agent, or another harness could attempt without external credentials.

## Requirements

- 3 to 5 small software tasks.
- Nix dev environment or flake.
- Local verifier commands.
- Expected attempt manifest examples.
- Expected trace JSONL examples.
- Dataset export fixture.
- No real model providers.
- No external services.

## Tests

- benchmark fixtures validate
- verifier commands are represented
- expected traces validate
- dataset export includes benchmark trajectories

## Acceptance criteria

Faber has a reusable local benchmark to test harness trace adapters and candidate selection without relying on external APIs.