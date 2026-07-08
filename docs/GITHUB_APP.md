# Faber for GitHub

The intended GitHub App is named Faber and publicly described as Faber for GitHub.

Faber is installed by repository owners or organizations. It should support
selected repositories and should not require all-repository access.

## Installation Scope

A Faber installation records the GitHub installation id, account login, selected
repository full names, permissions, and creation time. Adapter operations must
check repository scope before converting issues or pull requests into protocol
objects.

## Permission Direction

Start with minimal permissions. The app reads issues, pull requests, commit
metadata, and check metadata as task evidence. It writes comments, checks, or
statuses only when necessary to publish useful state back to a repository.

## Event Normalization

Webhook parsing verifies GitHub-style HMAC signatures when a secret is provided
and normalizes payloads into small `GitHubEvent` records. Normalization captures
event name, action, delivery id, repository full name, and a raw payload digest. It
does not execute business logic.

## Contract and Attempt Conversion

GitHub issues can become `TaskContract` records with `task_source` set to
`github.issue`. The contract environment records repository, issue number, URL,
author, and labels when available. Verifier ids must come from Faber or the repo
owner configuration; labels are metadata, not verifier authority.

GitHub pull requests can become `Attempt` records bound to an existing
`TaskContract`. The adapter copies the PR base revision, head revision, PR
metadata, and caller-supplied patch digest. Candidate-owned checks are recorded as
attempt metadata only.

## Contract Markers

The adapter can render a machine-readable Faber task contract marker for comments
or issue bodies. The marker contains a schema, contract id, contract digest, and
canonical JSON payload. Parsing rejects malformed markers and digest mismatches.

## Publication Boundary

The current implementation uses an in-memory fake client. It records intended
issue comments, pull request comments, and check/status-like records without
network calls. Publishing a `VerificationReceipt` includes the accepted/rejected
result, receipt id and digest, contract id and digest, attempt id, candidate
revision, verifier id, and result digest.

Candidate-owned CI is signal, not authority. Platform-owned or
repository-owner-approved `VerifierRun` and `VerificationReceipt` objects produce
authoritative acceptance.

## Future Real App Work

Out of scope for the skeleton: real GitHub API calls, private key/JWT generation,
app registration automation, webhook web server, database persistence, background
workers, payments, model providers, marketplace matching, and UI.

## Fake End-to-End Example

1. Normalize an `issues.opened` payload into a `GitHubEvent`.
2. Convert the issue evidence into a `TaskContract` for an allowed installation.
3. Render a Faber task contract marker into a human-readable issue comment.
4. Convert a pull request payload into an `Attempt` bound to that contract.
5. Preserve candidate-owned check-run evidence as attempt metadata only.
6. Run an approved Faber verifier and issue a `VerificationReceipt`.
7. Publish the accepted or rejected receipt through the fake client as a PR comment
   or check-like record.
8. Export the resulting trajectory as canonical JSONL for audit and future router
   training.

The GitHub App is the first integration, not the whole product. Its job is to adapt
GitHub evidence into Faber Protocol objects without making GitHub the root
abstraction.
