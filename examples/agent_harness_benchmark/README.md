# Agent harness benchmark fixture

This example describes the offline benchmark built by `faber.benchmarks`.

It contains three local software tasks, each with:

- a `TaskContract`;
- a local verifier command;
- an expected `AttemptManifest`;
- expected `TraceEvent` records and a Level 3 `TraceManifest`;
- a trajectory record suitable for dataset export.

The benchmark declares the repository `flake.nix` as its preferred dev
environment and keeps the verifier commands runnable with the Python fallback
toolchain used on Windows. It does not require model providers, credentials, or
external services.
