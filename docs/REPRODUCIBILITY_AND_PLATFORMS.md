# Reproducibility and platforms

Faber should be NixOS-first without becoming NixOS-only.

NixOS is valuable because it can make solver environments more declarative, replayable, and inspectable. That matters for Faber because the goal is not only to accept work, but to produce high-quality trajectories for future routers and orchestrated models.

## Why NixOS helps Faber

Nix can provide:

- explicit dependency declarations
- lockfile/digest evidence
- reproducible dev shells
- less hidden system state
- stable verifier commands
- clearer environment provenance
- easier replay of solver episodes

For Faber training data, this improves the quality of environment evidence attached to trajectories. It helps answer: did the solver succeed because of skill, hidden local state, dependency luck, or a reproducible harness?

## Why other platforms still matter

Windows, macOS, and non-Nix Linux clients are still valuable. Many users, repos, agents, and failure modes live there. Faber should accept their contributions and record their environment evidence honestly.

The right design is not NixOS versus everything else. The right design is an evidence ladder:

- opaque local environment
- declared OS/runtime metadata
- lockfile-backed environment
- container-backed environment
- Nix flake/dev shell environment
- fully replayable episode package

NixOS often gives stronger replay evidence, but cross-platform traces are still useful for product coverage, portability, user delight, and training robust routers.

## Platform evidence fields

Environment records should capture:

- OS family and version
- architecture
- package manager
- lockfiles and digests
- runtime versions
- shell/dev environment entrypoint
- whether setup is reproducible
- verifier command used
- known platform limitations

## Policy

- Faber core must not assume NixOS.
- Faber development should remain NixOS-first.
- Task contracts may require NixOS when replayability is central.
- Other tasks may explicitly target Windows, macOS, Ubuntu, containers, or remote runners.
- Router training should learn platform-worker-task fit rather than treating one platform as universally superior.

## Customer delight

A great Faber task should tell the user exactly how reproducible the result is. A lower-reproducibility contribution is not worthless; it is just lower-evidence. Faber should make that distinction visible and useful.