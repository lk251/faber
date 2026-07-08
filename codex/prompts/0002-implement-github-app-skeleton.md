# Codex Prompt 0002: Implement Faber for GitHub Adapter Skeleton

Implement the next slice of Faber: a GitHub App adapter skeleton that can turn GitHub evidence into Faber protocol objects and publish verifier receipts back to GitHub-like surfaces through a fake client.

This issue builds on the completed core from Issue #1.

## Strategic intent

Faber for GitHub is the first integration, but GitHub is an adapter, not the root abstraction.

The adapter should let repository owners turn issues, pull requests, commit metadata, checks, and approved verifier outputs into auditable task contracts, attempts, verification receipts, and trajectories.

Do not build a real GitHub App registration, web server, background worker, OAuth flow, payment integration, or model provider integration in this issue.

## Existing context to preserve

- `docs/GITHUB_APP.md` says Faber for GitHub is installed by repo owners/orgs, should support selected repositories, and should start with minimal permissions.
- `src/faber/adapters/github/permissions.py` already defines a minimal read/write permission direction.
- `src/faber/adapters/github/contracts.py` already has a basic `issue_contract(...)` helper.
- `src/faber/adapters/github/webhooks.py` already has a tiny `parse_event(...)` skeleton.
- `src/faber/receipts.py` already defines authoritative `VerificationReceipt` records.
- `src/faber/trajectories.py` already makes trajectories the scarce training/audit asset.

Use those existing files and extend them cleanly.

## Core requirement

Create a small, dependency-light GitHub adapter layer with no real network calls.

The adapter must support:

1. installation/repository scope modelling
2. GitHub event normalization
3. GitHub issue -> `TaskContract` conversion
4. GitHub pull request -> `Attempt` conversion
5. webhook signature verification using the Python standard library
6. contract marker rendering/parsing
7. verification receipt publication through a fake GitHub client
8. tests proving that candidate-owned CI is not treated as authoritative verification

## Proposed files to add or extend

Add or extend files under:

```text
src/faber/adapters/github/
  __init__.py
  client.py
  contracts.py
  events.py
  installation.py
  markers.py
  permissions.py
  publisher.py
  webhooks.py

tests/
  test_github_installation_scope.py
  test_github_webhook_signature.py
  test_github_issue_contract_adapter.py
  test_github_pr_attempt_adapter.py
  test_github_contract_marker.py
  test_github_receipt_publisher.py
  test_github_ci_is_signal_not_authority.py
```

Do not remove the existing tests from Issue #1.

## Data objects

Implement small dataclass-based objects where useful:

- `GitHubInstallation`
  - installation id
  - account login
  - selected repository full names
  - permissions mapping
  - created_at
  - `allows_repository(repository_full_name: str) -> bool`

- `GitHubRepositoryRef`
  - full name, owner, name, default branch if known

- `GitHubIssueRef`
  - repository full name
  - issue number
  - title
  - body
  - labels
  - author login
  - html url if present

- `GitHubPullRequestRef`
  - repository full name
  - pull request number
  - title
  - body
  - author login
  - base revision
  - head revision
  - html url if present

- `GitHubEvent`
  - event name
  - action if present
  - delivery id if present
  - repository full name if present
  - raw payload digest

Keep these plain and explicit. Do not introduce Pydantic or a web framework.

## Conversion behavior

### Issue to contract

Provide a function that converts a GitHub issue reference into a Faber `TaskContract`.

It should:

- set `task_source` to `github.issue`
- include repository and issue number in `environment`
- include GitHub URL/author/labels in environment metadata if available
- include required verifier IDs passed by caller
- reject issue references whose repository is not allowed by the installation scope
- not treat labels as verifier authority

### Pull request to attempt

Provide a function that converts a GitHub pull request reference into a Faber `Attempt`.

It should:

- bind to an existing `TaskContract`
- set `base_revision` from the PR base revision
- set `candidate_revision` from the PR head revision
- include a deterministic patch/diff reference or digest placeholder supplied by caller
- include tool/check summaries only as attempt metadata
- reject PRs whose repository is outside the installation scope
- reject PRs whose repository does not match the task contract repository

## Webhook behavior

Extend `webhooks.py` to include:

- `verify_github_signature(secret: str, body: bytes, signature_header: str) -> bool`
- use GitHub-style `sha256=<hex>` HMAC signatures
- use `hmac.compare_digest`
- return `False` on malformed signatures rather than raising, unless inputs have invalid types

Also provide event normalization:

- parse common payload fields into `GitHubEvent`
- include raw payload digest using Faber digest helpers or canonical JSON where appropriate
- do not execute business logic inside webhook parsing

## Contract marker behavior

Implement a small marker format for comments or issue bodies.

Requirements:

- render a machine-readable Faber contract marker using canonical JSON
- include contract id and contract digest
- include schema name/version
- parse the marker back out of text
- reject malformed or digest-mismatched markers
- make the marker robust when surrounded by human-readable text

Example conceptual marker shape:

```markdown
<!-- faber:task-contract
{canonical-json-payload}
-->
```

Use the exact shape you think is best, but test it.

## Receipt publishing behavior

Implement a fake client and publisher.

`FakeGitHubClient` should record intended side effects in memory only, such as:

- issue comments
- pull request comments
- check runs or status-like records

No network calls.

`publish_verification_receipt(...)` should:

- accept a `VerificationReceipt`
- accept a repository / PR or issue target
- publish a clear accepted/rejected result
- include receipt id, receipt digest, task contract id, task contract digest, attempt id, candidate revision, verifier id, and result digest
- not mark candidate-owned CI as authoritative
- return a structured publication record whose digest is stable

## CI signal vs authority

Add tests that prove:

- check-run or CI-like payloads can be captured as evidence or attempt metadata
- they do not create an accepted `VerificationReceipt` by themselves
- only a Faber `VerifierRun` / `VerificationReceipt` path can produce authoritative acceptance

## Documentation updates

Update `docs/GITHUB_APP.md` to describe:

- selected-repository installation scope
- event normalization
- issue-to-contract conversion
- PR-to-attempt conversion
- contract markers
- fake-client publication boundary
- candidate-owned CI as signal, not authority
- what remains out of scope for a future real GitHub App

Update `README.md` only if useful, and keep it concise.

## Tests / checks

Run:

```bash
nix develop --command just check
```

If Nix is unavailable, run the closest local equivalents:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

State exactly what was run and what could not be run.

## Out of scope

- No real GitHub API calls.
- No GitHub private key / JWT generation.
- No app registration automation.
- No webhook web server.
- No database persistence for GitHub events.
- No background worker.
- No payment provider.
- No model provider.
- No marketplace matching algorithm.
- No UI.

## Acceptance criteria

- GitHub installation scope is represented and tested.
- Webhook HMAC signature verification is implemented and tested.
- GitHub issue references can become `TaskContract`s and are tested.
- GitHub PR references can become `Attempt`s and are tested.
- Contract markers render, parse, and detect digest mismatches.
- Verification receipts can be published through an in-memory fake GitHub client.
- Tests prove candidate-owned CI is signal, not authority.
- `docs/GITHUB_APP.md` documents the adapter boundary clearly.
- All existing Issue #1 tests continue to pass.
