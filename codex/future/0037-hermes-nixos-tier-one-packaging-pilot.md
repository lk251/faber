# 0037 — Hermes NixOS tier-one packaging pilot

## Goal

Design and, if selected later, implement a Faber pilot task to improve a Hermes Agent Nix/NixOS packaging or reproducibility issue.

## Scope

Potential targets include Python version pinning, stable Nix compatibility, Nix-on-Droid setup, NixOS/systemd deployment behavior, and secret-file configuration.

## Requirements

- Verify the exact upstream issue before implementation.
- Do not claim Hermes lacks tier-one support unless supported by upstream text.
- Define a Faber `TaskContract` fixture.
- Define verifier specs for setup, smoke test, docs, and trace artifacts.
- Require at least Level 1 evidence; prefer Level 2 trace evidence.
- Produce upstream PR or patch branch if implementation is selected.
- Do not make Hermes a dependency of Faber.

## Acceptance criteria

A Nix/NixOS Hermes task is ready to run through Faber with clear verifiers, trace requirements, and upstream contribution path.