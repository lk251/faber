# Faber for GitHub

The intended GitHub App is named Faber and publicly described as Faber for GitHub.

Faber is installed by repository owners or organizations. It should support
selected repositories and should not require all-repository access.

## Permission Direction

Start with minimal permissions. The app reads issues, pull requests, commit
metadata, and check metadata as task evidence. It writes comments, checks, or
statuses only when necessary to publish useful state back to a repository.

Candidate-owned CI is signal, not authority. Platform-owned or
repository-owner-approved verifiers produce authoritative receipts.

The GitHub App is the first integration, not the whole product. Its job is to adapt
GitHub evidence into Faber Protocol objects without making GitHub the root
abstraction.
