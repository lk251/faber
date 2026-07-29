# Roadmap

Faber now has a coherent local foundation for verifier-first paid work and
RL-grade trajectory collection. The next strategic question is whether that
foundation survives a respectful external workflow, not whether another schema can
be added.

## Current state

**Protocol and evidence**

- Canonical task, attempt, verifier, receipt, trajectory, settlement, worker,
  routing, market, consent, retention, risk, and budget records.
- Explicit PR-only, manifest, trace, and replayable episode quality tiers.
- RL-grade validation across process, environment, solver, verifier, reward, cost,
  latency, consent, and training eligibility evidence.
- Schema registry, strict compatibility checks, canonical snapshots, stable
  digests, cross-platform fixtures, and withdrawal-aware dataset manifests.

**Verification and learning**

- Platform-owned hard verifiers, human review receipts, verifier calibration,
  deterministic probabilistic scoring, cost-aware tournaments, and authority
  boundaries that keep advisory scores from settling work.
- Router datasets, worker scorecards, negative/rejected trajectory support, and
  RL-grade training export filters.

**Market and product path**

- Work budgets, exact local reservations, reconciliation, receipt-gated
  settlement, competition policies, task templates, and risk gates.
- Generic task/submission adapters, fake GitHub funded markers, a complete local
  funded product loop, and an inspectable CLI walkthrough.
- Account-free local mode, no telemetry, no provider SDK dependency, a 2,000-record
  local performance smoke, and explicit hosted-product boundaries.

**Rights and privacy**

- Consent grants, licenses, visibility, redaction, secret detection, private trace
  envelopes, retention classes, dataset withdrawal, tombstones, and digest-bound
  deletion reports.

## Next milestone: no-money external pilot

Run one human-approved external pilot against
[NousResearch/hermes-agent issue #61631](https://github.com/NousResearch/hermes-agent/issues/61631):
preserve a composed scheduler report when turn-budget exhaustion occurs.

This is the strongest next milestone because it is narrow, locally verifiable,
credential-free, private-data-free, and useful upstream without Faber. It tests the
remaining uncertain parts: issue freshness, maintainer coordination, patch review,
real harness evidence, verifier fit, redaction, and review friction.

Pilot constraints:

1. Re-check that issue #61631 remains open and unclaimed.
2. Ask the reporter or maintainer whether a focused contribution is welcome.
3. Run the existing task risk review before solver execution or budget reservation.
4. Use a fork and local fixture tests; do not use production providers, accounts,
   credentials, private data, or real schedules.
5. Produce `.faber/attempt.json`, a redacted trace, verifier run, authoritative
   receipt, trajectory quality report, and optional training export only with
   explicit consent.
6. Keep the first pilot unpaid. A placeholder work budget may measure economics but
   must not imply committed funds, custody, or guaranteed payout.
7. Open an upstream PR only after human approval; keep Faber artifacts supplemental
   unless maintainers request them.

Exit criteria are defined as Milestone 2 in [`MILESTONES.md`](MILESTONES.md).

## Next five implementation items

1. **External pilot runbook and evidence bundle.** Add a single command/checklist
   that instantiates the #61631 contract, records risk approval, ingests a real
   redacted harness trace, runs approved verifier specs, and packages maintainer
   review artifacts without publishing anything.
2. **Durable GitHub delivery and publication journal.** Persist webhook delivery
   IDs, normalized events, publication intents, retries, dry runs, and replay state
   before any real GitHub App write permission.
3. **Runner backend and isolation contract.** Separate local subprocess execution
   from stronger sandbox backends; add signed/runner-attested environment evidence,
   resource limits, and explicit network policy.
4. **Verifier approval and revocation registry.** Bind verifier specs to repository
   owner approval, version compatibility, calibration status, revocation, and
   receipt authority at a point in time.
5. **Pilot dataset review gate.** Add deduplication, train/evaluation leakage checks,
   consent/license review, withdrawal propagation, verifier-quality thresholds, and
   a human approval report before any model-training experiment.

## Blockers before real money or external autonomous work

- Human approval of the task, verifier policy, risk review, publication action, and
  responsible operator.
- Current upstream issue state and a maintainer-friendly contribution path.
- Stronger runner isolation for untrusted code and external actions.
- Durable event/publication recovery, fraud/abuse controls, identity policy,
  disputes, cancellation, and support operations.
- Legal review of marketplace, worker classification, tax, payment, refund,
  privacy, sanctions, and jurisdiction obligations.
- A reviewed funding/custody/payment adapter; budget markers and local settlement
  are not money movement.

## Blockers before training on collected trajectories

- Explicit solver/operator and repository/customer consent plus a reviewed data
  license for the intended use.
- Secret scanning, redaction review, private-trace controls, and tested deletion or
  withdrawal propagation across derived datasets and backups.
- Dataset deduplication, split stability, benchmark contamination controls, and
  train/evaluation leakage review.
- Sufficient task, worker, platform, failure, and verifier diversity to avoid
  overfitting one pilot or harness.
- Calibrated verifier quality, interpretable reward/cost/latency labels, and human
  review of accepted and rejected examples.
- A documented experiment objective and stop criteria. Private chain-of-thought,
  proprietary prompts, and model weights are not required.

## Blockers before a real GitHub App installation

- App registration, least-privilege permission review, installation scoping, and a
  threat model for webhook and publication paths.
- Secure webhook verification, delivery replay protection, durable idempotency,
  retries, rate-limit handling, and dead-letter/manual recovery.
- Secret storage and rotation for app credentials on the chosen deployment target.
- Read-only dry runs against a test repository before comments, checks, labels, or
  other write permissions.
- Clear repository opt-in, maintainer-facing copy, retention/deletion behavior,
  privacy terms, support ownership, and uninstall/data-export behavior.

## Deferred wedge-discovery experiments

These are complementary hypotheses to test after the submission freeze, not roadmap
commitments or a decision to enter a vertical.

**Freight evidence and acceptance.** Investigate one narrow, repeatable
quote-to-cash exception among known counterparties: proof-of-delivery issues,
accessorial reconciliation, invoice disputes, or freight claims. The product
hypothesis is that Faber can ingest messy evidence, normalize it into a
machine-checkable case, route it under explicit authority, and emit an auditable
decision into existing systems of record. Freight is attractive because these
evidence-heavy exceptions cross organizational boundaries, recur, and delay cash or
consume operational labor. Discovery must identify a precise buyer, recurring
workflow, data rights, pain, and economic value. Falsify the hypothesis if incumbents
bundle an adequate solution, internal automation is sufficient, counterparties reject
a shared process, delivery remains excessively bespoke, value is weak, or the
necessary data rights are unavailable.

**Experiment-first agent transaction.** Before selecting a vertical, run the
smallest real productive transaction between two independently governed parties. A
buyer-side agent specifies a genuine task, constraints, budget, evidence requirements,
and acceptance criteria. A provider-side agent representing another party accepts or
negotiates, performs the task, and returns evidence. The buyer-side agent then accepts,
requests revision, or raises a structured objection. Humans retain approval over
consequential commitments and payments.

Instrument capability discovery, identity and organizational affiliation, delegated
authority, task specification and contracting, private-data boundaries, execution and
evidence, acceptance and evaluation, revisions and disputes, settlement or
system-of-record updates, and reputation or repeat transactions. Measure human
intervention, clarification rounds, cycle time, integration effort, failure types,
acceptance disagreements, and economic value against the current process. The
repeated bottleneck should reveal whether the possible wedge is capability
verification, task contracting, bounded delegation, evidence and acceptance, dispute
resolution, or settlement infrastructure.

If Faber controls both agents, the experiment tests plumbing rather than cross-company
trust. One buyer and provider test a transaction, not a full market.

## Decision rule

Complete the no-money external pilot before a real payment adapter, hosted market,
or model-training run. If #61631 closes or becomes active, re-rank the current open
Hermes issues and choose another narrow, locally verifiable, low-risk task rather
than forcing the stale target.
