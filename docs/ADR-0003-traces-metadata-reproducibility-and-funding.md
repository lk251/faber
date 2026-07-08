# ADR-0003: Traces, metadata, reproducibility, and work budgets

Status: Proposed

## Context

Faber's long-term asset is not only accepted PRs. It is verified trajectories that can train routers, verifiers, and orchestrated models. A PR-only submission is useful but thin; it lacks process evidence, solver metadata, environment provenance, and dense verifier signals.

Faber also needs an economic surface where people can attach budgets to work they care about. GitHub issues, labels, milestones, and repositories are natural funding targets, but payments must remain adapter-level behavior.

NixOS is important because declarative environments improve replayability and data quality. Other platforms remain valuable and should be represented through explicit environment evidence rather than excluded.

## Decision

Faber will:

- accept PR-only submissions initially
- define an evidence ladder from PR-only to replayable episode packages
- support `.faber/attempt.json` as the first low-friction manifest
- support trace JSONL and harness-native trace adapters later
- record solver metadata with provenance and disclosure levels
- record environment metadata across NixOS, Linux, macOS, Windows, containers, and remote runners
- prefer NixOS for high-replayability tasks without making it mandatory
- define provider-agnostic work budgets for funded issues and task contracts
- keep payment providers outside the core

## Consequences

- Low-friction adoption remains possible.
- Better traces can become a market advantage for solvers.
- Faber can learn worker, harness, model, verifier, and platform value per euro.
- Richer contributions can be rewarded with eligibility, reputation, and budget bonuses.
- Cross-platform contributions remain useful, while Nix-based episodes often carry stronger replay evidence.
- Funding can be routed toward verified work without hardcoding a payment provider.

## Non-goals

- No requirement to capture private prompts, private finetune weights, or chain-of-thought.
- No real payment provider in core.
- No real model provider in core.
- No claim that one platform is universally superior.
- No dependency on Hermes Agent or any external harness.