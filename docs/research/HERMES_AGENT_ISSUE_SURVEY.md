# Hermes Agent issue survey

Survey date: 2026-07-08.

Repository surveyed: `NousResearch/hermes-agent`.

This document is a planning input for Faber. It should not claim that Hermes needs Faber or that any upstream maintainer has endorsed these ideas. The goal is to identify respectful, useful, verifiable tasks that could engage the Hermes community while dogfooding Faber.

## High-signal themes observed

Open issues suggest several useful task families:

1. Nix/NixOS packaging and reproducibility
2. platform-specific install and runtime behavior
3. profile isolation and workspace correctness
4. tracing/observability reliability
5. durable feedback and learning signals
6. bundled skill/plugin lifecycle
7. adapter/gateway correctness for Discord, Telegram, Copilot ACP, Honcho, and other integrations
8. security and privacy hardening around local state and credentials

## Nix/NixOS-related candidates

Examples observed in open issues:

- bump sealed Nix venv from Python 3.12 to Python 3.13
- stable/classic Nix compatibility rather than flake-only coupling
- Nix-on-Droid setup failure
- systemd/NixOS deployment false positives
- file-based secret configuration compatible with systemd/NixOS secret managers
- state database permission hardening where managed NixOS mode may change group access assumptions

These are especially relevant to Faber because Nix can produce stronger environment evidence for training trajectories.

## Learning-signal candidates

Examples observed:

- durable feedback routing for memory, skills, and follow-up planning
- emoji reaction reinforcement from messaging platforms
- Langfuse/tracing dependency lifecycle issue where tracing can silently stop after environment refresh

These are relevant because Faber cares about trace capture, feedback signals, progress scoring, and dense training data.

## Product/UX reliability candidates

Examples observed:

- profile isolation bugs
- stale CWD/workspace bugs
- desktop delete profile behavior
- dashboard/chat availability issues
- adapter issues in Discord/Telegram/Copilot/Honcho paths

These may be good Faber tasks if they have crisp reproduction steps and local verifier commands.

## Recommended Faber posture

- Start with investigation and ranking, not a preselected target.
- Prefer tasks that are useful to Hermes even if Faber is ignored.
- Prefer tasks with local reproduction and verifier commands.
- Prefer tasks that can emit `.faber/attempt.json` and trace evidence.
- Avoid tasks requiring production credentials, broad account access, or subjective acceptance.
- Avoid claiming Hermes has a problem until verified from upstream docs/issues.

## Candidate first external task

The strongest candidate family is:

> Make a Hermes Agent Nix/NixOS packaging or reproducibility issue verifiable, documented, and trace-emitting through Faber.

A good pilot should deliver:

- clear upstream issue target
- task contract fixture
- Nix/dev shell or packaging improvement
- smoke verifier commands
- attempt manifest example
- trace JSONL example
- docs for users and maintainers
- upstream PR or patch branch

## Relationship to Faber

This should not make Hermes a Faber dependency. Hermes is a potential external bounty target and community bridge. Faber should remain a provider-agnostic market/protocol/trajectory system.