# 0068 — Open protocol vs hosted product boundaries

## Goal

Clarify which parts of Faber are open protocol, self-hostable infrastructure, hosted product, paid verifier service, or proprietary model/training output.

## Scope

Add docs and, where useful, package boundaries for:

- Faber Protocol
- Faber Runner
- Faber Verifiers
- Faber Market
- hosted settlement/coordination service
- proprietary or premium trained models

## Requirements

- Keep protocol objects useful without hosted Faber.
- Keep hosted-product boundaries honest.
- Explain democratization as access to measured high-intelligence-per-euro paths, not merely cheaper inference.
- Document what data can be open, private, or paid.
- Do not add licensing boilerplate beyond TODOs for legal review.

## Tests

Docs-only is acceptable. If code changes are made, tests should ensure package imports remain clean and provider-free.

## Acceptance criteria

Future contributors understand which parts should be open/self-hostable and which parts may become commercial.