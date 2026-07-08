# 0036 — Hermes issue survey and candidate ranking

## Goal

Turn the Hermes Agent issue survey into a ranked list of candidate Faber external tasks.

## Scope

Use `NousResearch/hermes-agent` as a read-only target. Inspect issues and rank candidate tasks by Faber suitability.

## Requirements

- Do not assume a single best issue before inspection.
- Consider Nix/NixOS, tracing/observability, durable feedback, profile/workspace correctness, plugin lifecycle, and adapter correctness issues.
- Score each candidate by:
  - real upstream value
  - objective verifier feasibility
  - trace/trajectory richness
  - community engagement potential
  - risk level
  - implementation boundedness
  - likelihood of maintainer acceptance
- Create `docs/bounties/HERMES_AGENT_CANDIDATE_RANKING.md`.
- Propose top 3 pilot tasks with acceptance criteria.

## Tests

If code is added, add tests only for scoring helpers or fixtures. This can also be a docs-only issue.

## Acceptance criteria

Faber has a ranked, respectful, evidence-based list of Hermes Agent task candidates before selecting a first external bounty.