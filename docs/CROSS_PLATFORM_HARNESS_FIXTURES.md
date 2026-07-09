# Cross-platform harness fixtures

`faber.platform_fixtures` provides six synthetic, offline solver episodes for
NixOS, Linux, macOS, Windows, containers, and remote runners. They exercise the
same verifier-first trajectory policy without pretending that every environment
has equal replay strength.

Each fixture includes:

- a platform-specific `EnvironmentEvidence` record;
- a digest-bound `AttemptManifest` with explicit training consent;
- ordered context, tool, verification, and outcome trace events;
- a `TraceManifest` and authoritative fake `VerifierRun`;
- a normalized trajectory record with reward, cost, and latency signals.

All values are fake and carry synthetic-data markers. The fixtures do not invoke
Nix, a container runtime, a remote runner, or external services.

## Evidence strength

The NixOS fixture records a flake lock digest and uses `nix_flake` reproducibility,
the strongest level in this fixture set. The container fixture uses an image
digest. Linux, macOS, and Windows use dependency lockfiles but acknowledge that
their OS images are not fully pinned. The remote runner is runner-attested but
only declares its image.

The lower-strength fixtures can still be RL-grade because they include non-opaque
environment evidence, a repository snapshot, process events, authoritative
verification, reward and cost signals, and explicit consent. Platform-specific
task contracts are checked separately and reject incompatible attempts.
