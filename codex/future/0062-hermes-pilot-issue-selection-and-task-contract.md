# 0062 — Hermes pilot issue selection and task contract

## Goal

Select one concrete Hermes Agent issue as the first external Faber pilot candidate and package it as a complete Faber task contract.

## Scope

Use `NousResearch/hermes-agent` as read-only reference.

Candidate families:

- Nix/NixOS packaging or reproducibility
- tracing/observability reliability
- durable feedback signals
- profile/workspace correctness
- plugin lifecycle
- local security/privacy hardening

## Requirements

- Inspect current open issues before choosing.
- Rank at least five candidates.
- Select one top candidate with justification.
- Create a Faber task contract fixture.
- Define verifier specs and trajectory/evidence requirement.
- Define work budget placeholder.
- Define maintainer-friendly upstream contribution path.
- Do not make Hermes a dependency.
- Do not claim upstream endorsement.

## Tests

- selected task contract validates
- verifier specs validate
- evidence requirement validates
- work budget placeholder validates

## Acceptance criteria

Faber has a concrete, respectful external pilot ready for human approval.