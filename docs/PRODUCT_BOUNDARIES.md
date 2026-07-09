# Open protocol and hosted product boundaries

Faber can support an open ecosystem and a commercial product only if those
boundaries remain explicit. The protocol must be useful on its own; paid services
must state what operational value they add instead of quietly turning portable
records into account-locked data.

## Component boundary

| Surface | Open or self-hostable foundation | Possible hosted or commercial layer | Required boundary |
| --- | --- | --- | --- |
| Faber Protocol | Canonical schemas, validation, digests, task contracts, attempts, receipts, trajectories, budgets, settlements, rights metadata, and JSON/JSONL export | Compatibility testing, managed schema registries, and support | A conforming record works without a hosted Faber account |
| Faber Runner | Local execution policy, trace capture, approved-verifier execution, redaction, and evidence packaging | Managed runners, stronger isolation, fleet scheduling, and platform attestations | Runner output is portable protocol evidence; the hosted scheduler is not part of the schema |
| Faber Verifiers | Verifier specs, runs, receipts, calibration records, deterministic local packs, and provider-neutral scoring interfaces | Paid compute, specialist review, premium model judges, and managed calibration sets | Paying for a service does not make a verifier authoritative; task or repository policy does |
| Faber Market | Worker profiles, work budgets, reservations, competition policy, routing decisions, scorecards, and market events | Discovery, matching, reputation operations, fraud controls, support, and marketplace fees | Market records retain canonical protocol records and exportable identifiers |
| Hosted coordination and settlement | Provider-neutral obligations, accepted receipts, local ledgers, and adapter contracts | Accounts, queues, notifications, dispute operations, tax/compliance workflows, custody, and payment-provider adapters | Verification precedes settlement; hosted payment state cannot rewrite a receipt outcome |
| Premium models and training outputs | Dataset schemas, consent, redaction, quality reports, router examples, evaluation methods, and reproducible recipes where released | Private datasets, proprietary weights, premium routers, learned orchestrations, inference, and support | Model and dataset rights are declared separately from protocol compatibility |

The first four foundations should remain useful for local and community deployments.
A hosted service may provide reliability, coordination, compute, governance, and
support, but it must not redefine the meaning of exported protocol objects.

## Democratization

Faber's democratization goal is access to measured high-intelligence-per-euro
paths, not merely cheaper inference. A useful market should measure task outcome,
verification quality, total cost, latency, review friction, replayability, and
failure modes across open, self-hosted, hosted, and premium options.

The best route for one task may be a local open model, a paid verifier, a premium
solver, a human review, or an orchestration of several of them. Faber should make
that tradeoff inspectable and broaden access to the measured result. It should not
predeclare one provider class as universally democratic.

## Open, private, and paid data

**Open data may include:**

- protocol schemas, examples, migration notes, and conformance fixtures;
- public task contracts, public patches, verifier specs, and published receipts;
- redacted traces and trajectories when provenance, license, and consent allow;
- aggregate verifier calibration and market statistics that do not leak private
  records.

**Private data may include:**

- credentials, private prompts, hidden tests, customer repositories, and raw traces;
- account identity, dispute material, unpublished review notes, and abuse signals;
- private budget, pricing, or business data;
- trajectories retained for audit but not licensed for training or public export.

**Paid access may include:**

- managed runner or verifier compute;
- hosted coordination, indexing, search, monitoring, and support;
- premium evaluation datasets, routers, models, or orchestration endpoints;
- compliance, dispute, settlement, and marketplace operations.

Payment does not by itself grant training rights, public redistribution rights, or
ownership of a worker's private process data. `ConsentGrant`, `DataLicense`,
retention policy, visibility, and export policy records must carry those decisions.

## Portability rules

1. Protocol validation and canonical digests cannot require hosted service state.
2. GitHub, payment providers, model providers, and hosted accounts remain adapters.
3. Hosted identifiers may be metadata, but portable IDs and record digests remain
   sufficient for audit.
4. Self-hosted runners can emit receipts when the task policy recognizes their
   verifier authority.
5. Paid verifier scores remain advisory unless an explicit verification policy
   grants authority.
6. Training export follows consent, redaction, retention, and quality policy rather
   than subscription tier.
7. Hosted users can export canonical task, attempt, receipt, trajectory, and market
   records that they are entitled to access.

## Contributor decision guide

- Put stable work/audit/training semantics in protocol modules.
- Put local execution and evidence acquisition in runner or harness modules.
- Put source, payment, and model-specific behavior behind adapters.
- Put account operations, fleet control, abuse handling, and service-level behavior
  in hosted-product code rather than protocol objects.
- Treat premium model weights and learned routing policy as outputs that consume
  protocol data, not as prerequisites for using the protocol.

## TODO for legal review

- Choose and document code and specification licenses.
- Decide whether conformance fixtures need a separate data license.
- Define terms for public, private, and paid datasets without conflating access,
  copyright, privacy consent, and training permission.
- Define trademark and hosted-service terms separately from protocol compatibility.
- Review payment, employment, tax, privacy, and regulated-domain obligations before
  any real hosted settlement or marketplace launch.

These are legal-review TODOs, not license grants or legal conclusions.
