# ADR-0003: Traces And Solver Metadata

Status: Proposed

## Context

A pull request captures final patch evidence and may be enough for basic
marketplace verification. It loses most process evidence: model, harness, runner,
environment, tool usage, cost, latency, failed branches, interventions, progress,
and failure attribution.

Faber needs richer traces for supervised router learning, attempt quality
prediction, harness and orchestration learning, verifier calibration, dense
reward export, and intelligence-per-euro measurement. Recent harness engineering
work frames autonomous software engineering capability as a
model-harness-environment system, not only a model property. Faber should capture
that distinction while keeping GitHub, payments, and model providers as adapters.

## Decision

Faber will accept PR-only submissions initially, but it will define a
trace/manifest ladder and reward richer, attested traces.

The ladder is:

1. PR-only fallback.
2. PR plus `.faber/attempt.json` manifest.
3. Faber Runner trace.
4. Harness-native trace adapter.
5. Replayable episode package.

Faber will:

- support PR-only fallback;
- add `.faber/attempt.json` as the first low-friction manifest;
- add Faber Runner traces for high-quality submissions;
- add harness-native trace adapters later;
- add replayable episode packages for premium or high-trust tasks;
- treat solver metadata as provenance-tagged, not automatically true;
- incentivize richer traces with eligibility, reputation, and possibly better
  economics;
- avoid requiring private chain-of-thought, proprietary prompts, finetune weights,
  or provider secrets.

## Consequences

- Low adoption friction remains possible.
- High-quality training data becomes a market product.
- Solver IP and customer privacy can be protected through disclosure levels,
  redaction, and provenance tags.
- Faber can measure worker, harness, model, environment, verifier, and router
  value per euro more honestly.
- Premium tasks can require stronger trace evidence without excluding ordinary
  contributors from simpler tasks.
- Faber must build trust and redaction policies before using traces broadly for
  training.
