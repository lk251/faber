# Faber Runner

Faber Runner is the self-hosted execution and verifier component. It should run
platform-owned or repository-owner-approved verifier policy and emit evidence that
can be bound into verification receipts.

The initial implementation is local-only and does not require Docker.

## Local Development Runner

The local runner executes only verifier commands registered through
`VerifierRegistry`. Task contracts, pull requests, and other candidate-owned
metadata do not provide executable commands.

The local runner is governed by an explicit `RunnerPolicy`. The policy records the
allowed working directory root, allowed environment variables, timeout, maximum
stdout/stderr capture length, shell execution flag, and local network-isolation
status.

The local runner captures exit code, elapsed time, truncated stdout/stderr digests,
log digests, and structured metrics when a verifier prints a JSON object with a
`metrics` field. It emits `VerifierRun` records that can be bound into
`VerificationReceipt` objects. It does not store raw logs in core records.

This runner is development infrastructure, not a production sandbox. It uses the
host operating system process model and does not provide complete network,
filesystem, or kernel isolation. Its default network-isolation value is explicit:
`none-local-runner-does-not-isolate-network`. A production Faber Runner should
replace this policy with stronger isolation while preserving the same receipt
boundary.
