# Faber Runner

Faber Runner is the self-hosted execution and verifier component. It should run
platform-owned or repository-owner-approved verifier policy and emit evidence that
can be bound into verification receipts.

The initial implementation is local-only and does not require Docker.

## Local Development Runner

The local runner executes only verifier commands registered through
`VerifierRegistry`. Task contracts, pull requests, and other candidate-owned
metadata do not provide executable commands.

The local runner captures exit code, elapsed time, stdout/stderr digests, log
digests, and structured metrics when a verifier prints a JSON object with a
`metrics` field. It emits `VerifierRun` records that can be bound into
`VerificationReceipt` objects.

This runner is development infrastructure, not a production sandbox. It uses the
host operating system process model and does not provide complete network,
filesystem, or kernel isolation. A production Faber Runner should replace this
policy with stronger isolation while preserving the same receipt boundary.
