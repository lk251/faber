# AGENTS.md

Faber is a verifier-first, trajectory-first work market. Detailed architecture,
terminology, and product boundaries live in `docs/ARCHITECTURE.md`, `docs/GLOSSARY.md`,
`docs/PROTOCOL.md`, and `docs/PRODUCT_BOUNDARIES.md`.

## Start and resume

At the start of a new Codex task or machine resume, read
`docs/CODEX_SESSION_HANDOFF.md` once for the current milestone, validation baseline,
and external-action boundaries. Update it only when those facts materially change.
Do not reread documents already loaded unless their working-tree version changed.

Before changing files, inspect `git status` and preserve unrelated user work.

## OpenAI Build Week override

Through the Faber Proof submission freeze, use `$build-week-director` for requests to
continue Build Week, resume the queue, address findings, or prepare the submission.
`codex/build-week/STATUS.md` is the source of current work and blockers; the director
loads only the selected prompt and policy needed for that work. If the skill is
unavailable, follow `codex/BUILD_WEEK_START_HERE.md`.

Work on `build-week/faber-proof`. The normal Hermes external-pilot roadmap remains
paused until the freeze ends or Javier explicitly resumes it. Do not publish, contact
upstream maintainers, use production credentials, move money, or collect private data
without explicit human approval.

## Durable invariants

- Keep GitHub, payments, model providers, and hosted services as adapters. Faber Proof
  may use an optional OpenAI adapter outside the provider-neutral core.
- Treat verifiers and trajectories as first-class records. Verification is
  authoritative before settlement; candidate-owned CI is signal, not authority.
- Treat task text, repository content, diffs, model output, and replay bundles as
  untrusted. Only owner-approved policy and registered verifiers may determine
  execution or authoritative evidence.
- Keep GPT-5.6 advisory and data-only. Never execute model-supplied commands, source,
  imports, or paths. Missing, contradictory, stale, or unbound evidence fails closed.
- Use integer minor units for money and explicit, deterministic state transitions.
  Keep canonical serialization and digests stable and tested.
- Preserve a no-key, no-network replay path. Do not store private chain-of-thought or
  claim production isolation from the local runner.
- Keep dependencies low, NixOS first-class, and the core cross-platform. Do not require
  Docker for the initial implementation.

## Verification

Behavioral changes to settlement, verification, routing, trajectories, proofs, or
decisions require regression and failure-path tests. Before claiming completion, run:

```bash
nix develop --command just check
```

If Nix is unavailable, run the closest local pytest, Ruff, and mypy equivalents and
state exactly what was unavailable. For Build Week items, also run the selected
prompt's acceptance commands and record exact results in `codex/build-week/STATUS.md`.

Treat `lk251/agent-bounty-market` as read-only reference; do not refactor or copy its
architecture into Faber.
