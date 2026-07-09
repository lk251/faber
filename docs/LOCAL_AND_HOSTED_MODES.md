# Local and hosted modes

Faber's current implementation is local and self-hostable. Hosted market
infrastructure is not implemented.

## Local mode expectations

- No account is required.
- No external API is required by protocol validation, local stores, local ledgers,
  dataset export, or the included walkthroughs.
- No telemetry is emitted. There is no analytics client, background uploader, or
  opt-out setting because local Faber does not collect telemetry.
- State is written only to paths selected by the operator, including SQLite, JSON,
  JSONL, Markdown, and trace artifacts.
- Fake GitHub adapters operate on supplied payloads and in-memory clients. They do
  not contact GitHub.
- The package has no required third-party Python dependencies or provider SDKs.

These expectations apply to Faber itself. `LocalVerifierRunner` is a development
runner, not a security sandbox, and does not isolate verifier network access. An
approved verifier command can use capabilities available to its host process. The
task owner or self-hosted operator must choose appropriate isolation and verifier
policy.

## Local-only CLI commands

Every CLI command in the current build is local-only:

| Group | Commands | External behavior |
| --- | --- | --- |
| Inspection | `doctor`, `store-summary`, `list-contracts`, `show-trajectory`, `dataset-summary` | Reads local runtime or files |
| Store and export | `init-local-store`, `export-trajectory`, `export-trajectories`, `emit-demo-trajectory` | Reads or writes operator-selected local paths |
| Evidence | `generate-attempt-manifest`, `validate-attempt-manifest`, `validate-attempt`, `validate-trace`, `validate-trajectory`, `trajectory-quality` | Generates or validates local artifacts |
| Golden path | `create-demo-contract`, `register-demo-worker`, `register-demo-verifier`, `submit-demo-attempt`, `run-demo-verifier`, `issue-demo-receipt`, `settle-demo`, `export-demo-trajectory`, `run-golden-path` | Uses local SQLite and approved local subprocesses |
| Funded walkthrough | `demo-funded-trajectory` | Uses fake payloads, local ledger state, and local dataset files |

None of these commands require GitHub, payment, model-provider, or hosted Faber
credentials.

## Self-hosted mode

Self-hosted operators can use the same protocol records while supplying stronger
runner isolation, durable storage, backups, and selected adapters. Adapters may use
external APIs when the operator explicitly configures them. That does not change
core record meaning or verifier authority.

Self-hosted deployments control their own logging and telemetry. The recommended
default remains no telemetry unless the operator configures a documented policy.

## Hosted mode is future work

A future hosted product may provide accounts, task discovery, market coordination,
work-budget operations, managed verifier compute, notifications, dispute handling,
dataset operations, and premium training or routing services. None of those
services exists in this repository today.

Future hosted work must define authentication, authorization, privacy, retention,
telemetry, abuse controls, custody/payment boundaries, regional storage, export,
and service-level behavior. Hosted records must remain exportable as canonical
protocol records. The detailed commercial boundary is in
[`PRODUCT_BOUNDARIES.md`](PRODUCT_BOUNDARIES.md).
