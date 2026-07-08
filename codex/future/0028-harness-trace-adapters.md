# 0028 - Harness Trace Adapters

## Goal

Plan and stub harness-native trace adapters.

## Scope

Add:

- generic adapter interface;
- fake Codex trace adapter;
- fake Hermes trace adapter placeholder;
- fake OpenHands or SWE-agent adapter placeholder if useful;
- mapping from native events to Faber `TraceEvent`.

## Requirements

- Do not depend on real harness packages.
- Do not add real model APIs.
- Do not make claims about Hermes internals unless verified.
- All adapter placeholders must be clearly marked as schemas or stubs.
- Native traces must map into provider-agnostic Faber trace events.
- Do not require private chain-of-thought.

## Tests

Add tests for:

- mapping fake Codex native traces into Faber trace events;
- mapping fake Hermes placeholder traces into Faber trace events;
- redaction markers;
- unsupported event behavior;
- stable digest behavior.

## Docs

Explain how external harness communities can add adapters without making their
harness a dependency of Faber core.

## Acceptance Criteria

- Adapter stubs are useful examples and safe placeholders.
- Faber core remains independent from harness packages.
