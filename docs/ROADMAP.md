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

## Deferred external validation, application discovery, and outreach

These items are deliberately deferred so they do not displace the current no-money
external pilot, but they should be reconsidered as Faber accumulates external proof
and a clearer product narrative.

1. **Study Pushin.eu as real-world evidence of the contribution-quality problem.**
   Pushin publicly treats low-quality contribution volume and maintainer overload as
   a product-level pain point and is building reputation, triage, and contribution
   limits around it. Use the field note in
   [`research/pushin-contribution-quality-field-note-2026-09-13.md`](research/pushin-contribution-quality-field-note-2026-09-13.md)
   as a starting point, track how its mechanisms evolve, and seek measurable data
   about review load, low-quality contribution rates, false positives/negatives, and
   maintainer time.
2. **Evaluate Pushin as a potential Faber application or pilot surface.** Distinguish
   account/contributor reputation from submission-specific verification evidence and
   test whether Faber can complement rather than duplicate Pushin's anti-slop layer.
   Look for the smallest maintainer-approved pilot before building any
   Pushin-specific adapter.
3. **Generalize from Pushin to other Faber markets.** Search for the same structural
   pattern — submissions becoming cheaper and more numerous faster than humans can
   verify them — across Git forges, open-source projects, package registries,
   security-report queues, agent/bounty markets, code-generation platforms, and
   high-volume internal engineering organizations. Rank opportunities by pain,
   verification tractability, access to operators/data, willingness to pilot, and
   eventual willingness to pay.
4. **Use existing European political/technology networks for human-led partner and
   funding discovery.** Once there is a concise Faber explanation and something
   concrete to show, tell relevant contacts in Volt DigiPub and, where appropriate,
   people in or around Guy Verhofstadt's party/political network about Faber. The
   goal is to discover startups and companies that may have the verification problem,
   potential pilot partners, and people who can make introductions to investors,
   grant/funding channels, or other supporters. Keep this as human-led relationship
   building rather than autonomous outreach, and keep any project/funding discussion
   appropriately separate from confidential or policy-advisory work.

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

## Decision rule

Complete the no-money external pilot before a real payment adapter, hosted market,
or model-training run. If #61631 closes or becomes active, re-rank the current open
Hermes issues and choose another narrow, locally verifiable, low-risk task rather
than forcing the stale target.
