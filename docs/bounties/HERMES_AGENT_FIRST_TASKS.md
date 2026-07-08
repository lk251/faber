# Hermes Agent first-task candidates

This document lists possible first external Faber tasks involving `NousResearch/hermes-agent`. These are candidates, not commitments.

## Ideal task attributes

A first Faber external task should:

- solve real pain for an active open-source community
- have crisp local verifier commands
- produce a useful PR or patch for the upstream project
- require at least an `.faber/attempt.json` manifest
- preferably produce `.faber/trace.jsonl`
- avoid production credentials or broad account access
- avoid subjective taste-based acceptance
- make Faber's verifier/trajectory model visibly useful
- be respectful of upstream maintainers

## Idea 1: NixOS reproducible harness pilot

Goal: make a Hermes Agent Nix/NixOS setup path more reproducible, verifiable, and documented.

Concrete pilot plan: `docs/bounties/HERMES_NIXOS_PILOT_PLAN.md`.

Potential targets:

- Python 3.13 Nix packaging update
- stable/classic Nix compatibility
- Nix-on-Droid setup issue
- NixOS/systemd deployment false-positive issue
- file-based secret configuration for systemd/NixOS-style deployments

Deliverables:

- upstream issue selection and reasoning
- reproducible setup path
- smoke verifier command
- docs
- `.faber/attempt.json`
- `.faber/trace.jsonl` if feasible
- upstream PR or patch branch

## Idea 2: Hermes trace adapter

Goal: map Hermes run/session/log artifacts into Faber TraceEvent JSONL.

Deliverables:

- adapter interface
- fake Hermes trace fixture
- parser/mapping
- redaction support
- tests
- docs for external harness communities

Current stub: `docs/HARNESS_TRACE_ADAPTERS.md` and the fake fixture adapter under
`src/faber/adapters/hermes/`.

## Idea 3: NixOS agent harness benchmark

Goal: create a small offline benchmark fixture that Hermes, Codex, OpenHands, or other harnesses can run under a Nix dev environment.

Deliverables:

- 3 to 5 tiny tasks
- Nix environment
- verifier commands
- expected traces
- dataset export
- docs

## Idea 4: Faber attempt manifest generator for Hermes PRs

Goal: make it easy for a Hermes contributor or agent to attach `.faber/attempt.json` to a PR.

Deliverables:

- manifest schema example
- generator command or script
- validation tests
- docs

## Idea 5: Best-of-N Hermes/Faber selection pilot

Goal: run multiple candidate attempts on a small task and use Faber verifier records to select the best candidate.

Deliverables:

- multi-attempt fixture
- candidate selection record
- hard/advisory verifier boundary
- trajectory exports
- docs

Current pilot rule: `docs/bounties/HERMES_BEST_OF_N_SELECTION_PILOT.md`.

## Idea 6: Hermes skills/plugin safety manifests

Goal: create a manifest/checking path for skills/plugins that declares platform support, permissions, dependencies, and safety assumptions.

Deliverables:

- manifest schema
- fake fixtures
- scanner tests
- docs

Current manifest path: `docs/bounties/HERMES_SKILL_PLUGIN_SAFETY_MANIFESTS.md`.

## Idea 7: Real external Faber pilot task contract

Goal: package one selected Hermes issue into a complete Faber `TaskContract` with budget, verifier policy, trace requirement, and acceptance criteria.

Deliverables:

- task contract fixture
- verifier specs
- funding/work-budget placeholder
- expected attempt manifest
- expected trace evidence level
- upstream contribution path

## Recommended ordering

1. Survey and rank Hermes issues.
2. Implement trace protocol / attempt manifest support in Faber.
3. Select a Nix/NixOS or trace/observability issue.
4. Define the Faber task contract.
5. Run the pilot with PR plus manifest plus trace.

Do not make Hermes a dependency of Faber. The goal is to use a useful external project as a proving ground for verified work and training-quality trajectories.
