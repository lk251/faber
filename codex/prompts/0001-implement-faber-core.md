# Codex Prompt 0001: Implement Faber Core

We are starting a fresh repository for a long-term project named Faber.

Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

This is not a continuation of the hackathon codebase except as reference. The old repo is `lk251/agent-bounty-market`; use it only as read-only reference for ideas, invariants, tests, and lessons.

Do not refactor `agent-bounty-market` in place. Do not copy hackathon demo, Stripe, NVIDIA, Hermes, Motoko-specific, or presentation-bundle assumptions into the new core.

## Strategic context

The new project is verifier-first and trajectory-first.

The first wedge is GitHub-native verified software work, but GitHub is an adapter, not the root abstraction.

The long-term goal is to build a profitable agent labor market that produces high-quality verified trajectories for training Fugu-like orchestrated models with excellent intelligence-per-euro.

Democratization here does not mean "always cheapest." It means discovering, measuring, and making accessible high-intelligence-per-euro solutions, including:

- open/self-hosted options
- paid hosted verifiers
- premium proprietary models
- future learned orchestrations
- transparent measurement of value per euro

## Branding

- Platform/project name: Faber.
- GitHub App name: Faber, described publicly as "Faber for GitHub".
- Marketplace/dashboard: Faber Market.
- Open schemas/protocol: Faber Protocol.
- Self-hosted execution/verifier component: Faber Runner.
- Verifier layer or verifier marketplace: Faber Verifiers.
- Training/orchestration system: Faber Orchestration.
- Initial learned selector: Faber Router.
- Later Fugu-like orchestration models: Faber Models.

Avoid metaphor sprawl:

- Do not use Foundry.
- Do not use Loom.
- Do not use Guild unless discussing historical inspiration.
- Do not use woven-fabric language.
- Keep subsystem names literal and understandable.
- The name Faber carries the meaning of maker/craftsperson; do not force additional metaphors into the architecture.

## Development environment

- This repo is developed on NixOS.
- Create a Nix-first setup with `flake.nix`.
- `nix develop` should provide Python 3.12+, git, sqlite, just, ruff, mypy, pytest, and minimal tooling required.
- Avoid Windows assumptions.
- Keep the initial implementation dependency-light.
- Prefer the Python standard library unless a dependency is clearly justified.
- Do not add Docker as a requirement for the initial commit.

## Core design principle

The root objects are not "bounties" or "payments".

The root objects are:

1. `TaskContract`
2. `Attempt`
3. `VerifierRun`
4. `VerificationReceipt`
5. `Trajectory`
6. `Settlement`
7. `WorkerProfile`
8. `RouterDecision`
9. `MarketEvent`

The key scarce asset is the `Trajectory`:

- task contract
- repo/environment snapshot reference
- worker/agent identity
- router/orchestration decision
- attempt metadata
- tool/action summaries
- diff/patch reference
- verifier result
- human review signal when present
- cost/latency
- settlement/reward/margin
- final accepted/rejected outcome

## Initial repository structure

Create this structure:

```text
README.md
AGENTS.md
flake.nix
pyproject.toml
justfile
docs/
  ARCHITECTURE.md
  NAMING.md
  ADR-0001-fresh-start.md
  GITHUB_APP.md
  PROTOCOL.md
  TRAJECTORY_SCHEMA.md
src/faber/
  __init__.py
  canonical_json.py
  digests.py
  money.py
  ids.py
  events.py
  contracts.py
  attempts.py
  verifiers.py
  receipts.py
  trajectories.py
  settlement.py
  workers.py
  routing.py
  store.py
  cli.py
  adapters/
    __init__.py
    github/
      __init__.py
      README.md
      permissions.py
      contracts.py
      webhooks.py
  runner/
    __init__.py
    README.md
    local.py
tests/
  test_canonical_json.py
  test_digests.py
  test_money.py
  test_contract_receipt_binding.py
  test_trajectory_export.py
  test_settlement_invariants.py
  test_router_decision_records_cost.py
```

## Implementation requirements

1. Implement canonical JSON serialization with stable key ordering and compact separators.
2. Implement sha256 digest helpers returning strings like `sha256:<hex>`.
3. Implement integer minor-unit money only. No floats for money.
4. Implement dataclass-based domain objects for:
   - `TaskContract`
   - `Attempt`
   - `VerifierRun`
   - `VerificationReceipt`
   - `Trajectory`
   - `Settlement`
   - `WorkerProfile`
   - `RouterDecision`
   - `MarketEvent`
5. Every domain object that can become training/audit data should have:
   - `schema`
   - `id`
   - `created_at`
   - `to_dict()`
   - `digest()`
6. `VerificationReceipt` must bind:
   - `task_contract_id`
   - `task_contract_digest`
   - `attempt_id`
   - `worker_id`
   - `verifier_id`
   - `verifier_digest`
   - `base_revision`
   - `candidate_revision`
   - `accepted` boolean
   - `metrics`
   - `failure_reasons`
   - `result_digest`
7. `Trajectory` must bind:
   - contract
   - attempt
   - receipt
   - optional settlement
   - router decision
   - cost metadata
   - latency metadata
   - review metadata
8. `Settlement` must refuse to mark paid unless there is an accepted verification receipt.
9. Add tests proving:
   - canonical JSON is stable across key order changes
   - digest changes when meaningful content changes
   - money rejects floats and negative amounts
   - a receipt is bound to the exact contract digest and candidate revision
   - settlement cannot pay rejected work
   - trajectory export includes enough information for later supervised learning or reinforcement learning
   - router decision records selected worker, rejected alternatives, estimated cost, expected value, and model/orchestration policy name
10. Add a minimal CLI:
    - `python -m faber.cli doctor`
    - `python -m faber.cli init-local-store --path .faber/faber.sqlite3`
    - `python -m faber.cli emit-demo-trajectory --out .faber/demo_trajectory.json`

The demo trajectory should be generic and not Motoko-specific.

## Documentation requirements

`README.md` should begin with exactly this sentence:

> Faber is a verified work market where humans and agents produce useful work, and successful trajectories train better orchestrators.

`README.md` should also explain:

- Faber for GitHub is the first integration.
- Faber Market is the buyer/seller marketplace.
- Faber Protocol is the open schema layer.
- Faber Runner is the self-hosted execution/verifier component.
- Faber Orchestration trains routers and orchestrated models from verified trajectories.
- Faber is not a bounty-only app.
- Faber is not a payment processor.
- GitHub is the first adapter, not the root abstraction.

`AGENTS.md` should instruct future agents:

- Keep the core verifier-first and trajectory-first.
- Do not introduce hackathon demo code.
- Do not hardcode Stripe, NVIDIA, Hermes, Motoko, OpenAI, Anthropic, Google, or any specific vendor into the core.
- Keep candidate code and platform/verifier policy separated by a trust boundary.
- Use integer money only.
- Keep state transitions explicit, inspectable, and idempotent.
- Add tests before extending settlement, verifier, routing, or trajectory behavior.
- Run `nix develop --command just check` before claiming completion.

`docs/ADR-0001-fresh-start.md` should state:

- We are starting fresh instead of refactoring the hackathon repo.
- Reason: the long-term scarce asset is verified trajectories for orchestration learning, not bounty settlement.
- We will port ideas, invariants, and tests from the hackathon repo later, but not its architecture.
- GitHub is an adapter.
- The core is task contracts, attempts, verifier receipts, trajectories, routing decisions, and settlement.

`docs/GITHUB_APP.md` should define the intended GitHub App behavior:

- Installed by repo owners/orgs as "Faber".
- Publicly described as "Faber for GitHub".
- Minimal permissions first.
- Reads issues, pull requests, commit metadata, and check metadata as task evidence.
- Writes comments, checks, or statuses only when necessary.
- Candidate-owned CI is signal, not authority.
- Platform-owned or repo-owner-approved verifiers produce authoritative receipts.
- The App should support selected repositories, not require all-repo access.
- The App is the first integration, not the whole product.

`docs/PROTOCOL.md` should define the open protocol direction:

- `TaskContract`
- `Attempt`
- `VerifierRun`
- `VerificationReceipt`
- `Trajectory`
- `SettlementEvent`
- `WorkerProfile`
- `RouterDecision`
- `MarketEvent`
- JSONL export for training
- future compatibility with hosted and self-hosted runners
- future compatibility with multiple payment providers
- future compatibility with multiple model providers
- future compatibility with non-GitHub task sources

`docs/TRAJECTORY_SCHEMA.md` should explain:

- which fields support supervised learning
- which fields support reinforcement learning / preference learning
- how successful, failed, declined, and abandoned attempts are useful training data
- why cost, latency, verifier outcome, review friction, and reward matter for intelligence-per-euro
- why human review signals should be captured without making human review the only verifier
- why verifier quality itself may become a market and training signal

## Testing/check commands

Support these commands:

```bash
nix develop --command just check
nix develop --command pytest
nix develop --command ruff check .
nix develop --command mypy src
```

## Do not overbuild

- No web UI yet.
- No real GitHub API calls yet.
- No payment provider yet.
- No model provider integration yet.
- No marketplace matching algorithm yet.
- No database migrations beyond a minimal local SQLite store skeleton.
- No background worker.
- No Docker requirement.
- No Kubernetes.
- No cloud-specific assumptions.

## Important architectural boundaries

- GitHub is an adapter, not the core.
- Payments are an adapter, not the core.
- Model providers are adapters, not the core.
- Verifiers are first-class objects, not incidental test scripts.
- Trajectories are first-class objects, not logs.
- Settlement follows verification; verification does not follow settlement.
- Market data should be exportable for later training.
- The open protocol should be useful even if the hosted Faber service does not exist.

## Initial implementation quality bar

- Keep code small and readable.
- Prefer explicit dataclasses over framework magic.
- Prefer boring, deterministic functions.
- Do not hide important behavior behind global state.
- Make digests stable and test them.
- Make serialization stable and test it.
- Make money handling strict and test it.
- Make settlement invariants strict and test them.
- Make trajectory export obviously useful for future learning.

## After creating files

Run formatting/tests if available, then summarize:

- created structure
- implemented primitives
- tests added
- commands run
- any tests that fail and why
- next recommended issue: `Implement Faber for GitHub installation/webhook skeleton with fake client and receipt-publishing contract tests.`
