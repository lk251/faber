# 0042 — Hermes skills and plugin safety manifests

## Goal

Explore a Faber-style manifest/checking path for agent skills and plugins, using Hermes-style skills/plugins as a possible external reference.

## Scope

- skill/plugin manifest schema
- platform support declarations
- permission declarations
- dependency declarations
- verifier checks
- fake fixtures

## Requirements

- Do not depend on Hermes internals.
- Do not audit or judge upstream skills without clear scope.
- Represent permissions and platform support explicitly.
- Add scanner/checker for fake fixtures.
- Connect manifest checks to Faber verifier receipts when appropriate.

## Tests

- safe fixture passes
- missing platform declaration is flagged
- missing dependency declaration is flagged
- permission manifest digest is stable

## Acceptance criteria

Faber has a path for verified skill/plugin metadata that could later help Hermes or other harness ecosystems.