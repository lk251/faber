# 0058 — Probabilistic verifier adapter boundary

## Goal

Prepare Faber to use LLM-as-a-Verifier-style scoring without coupling the core to any model provider or external package.

## Scope

Add adapter interfaces for:

- scoring backend
- criteria decomposition
- repeated evaluation
- pairwise preference
- progress scoring
- score cache
- budget accounting

## Requirements

- `lk251/llm-as-a-verifier` may be studied as a read-only reference.
- Do not import `llm-as-a-verifier` into Faber core.
- Do not call real model APIs.
- Implement deterministic fake scorer backends first.
- Advisory verifier scores cannot release settlement unless task policy explicitly makes a verifier authoritative.
- Store score distributions/uncertainty where available.

## Tests

- fake scorer emits stable scores
- repeated evaluation aggregates deterministically
- criteria decomposition is represented
- advisory score cannot settle work
- score cache is keyed by stable digests

## Acceptance criteria

Faber has a clean seam for future probabilistic verifiers while keeping authority boundaries intact.