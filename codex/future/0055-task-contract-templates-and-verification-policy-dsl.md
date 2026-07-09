# 0055 — Task contract templates and verification policy DSL

## Goal

Make task creation repeatable by defining templates for common Faber tasks and a small verification policy vocabulary.

## Scope

Add:

- task contract templates
- verification policy objects
- evidence requirement presets
- budget presets
- GitHub issue task template
- NixOS/harness task template
- bugfix/code task template
- documentation task template

## Requirements

- Keep the DSL data-first and simple.
- No arbitrary code execution in templates.
- Verification policy should express hard tests, human review, advisory ranking, minimum trajectory tier, and budget constraints.
- Templates should render to ordinary `TaskContract` objects.
- Add docs and examples.

## Tests

- GitHub bug template renders valid task contract
- NixOS harness template requires platform evidence
- RL-grade template requires trace/episode tier
- budget preset binds to work budget marker
- invalid template fails clearly

## Acceptance criteria

Maintainers can create consistent Faber tasks without hand-writing every protocol field.