# Open questions

## Active questions — revenue and policy learning

The [2026-09-12 decision](strategy/2026-09-12-decision.md) supersedes the old pilot
priority. The highest-value unresolved questions are:

1. Will a small engineering team's budget owner pay €250/€1,000 for repeated
   acceptance-evidence work after seeing what existing CI and a frontier agent can do?
2. Does persistent owner-approved policy reduce total reviewer/setup/maintenance effort,
   or would a short CI patch solve the entire job?
3. Do learned check selection or structured proposals beat frontier reasoning with
   the same temporally valid retrieved history? What paid retention/efficiency benefit
   results, rather than merely a better offline score?
4. Can proposal-time views, rejected/failed proposals, owner corrections, absent
   counterfactuals and delayed regressions be retained with explicit rights and
   observation horizons? See the [schema audit](strategy/2026-09-12-policy-learning-schema-audit.md).
5. Does value transfer across repositories, or primarily accumulate in customer-owned
   within-repository memory? The latter can support retention without granting Faber
   a shared data moat.
6. After a stable verifier exists, can heterogeneous agent routing improve accepted
   work per total euro beyond a simple escalation rule? This September master-branch
   dogfooding hypothesis remains conditional, not the next platform build.

The [experiment plan](strategy/2026-09-12-experiments.md) supplies specific falsifiers.
The historical questions below remain context; Hermes #61631 is closed and its
freshness question is resolved, not an invitation to reopen the old pilot.

These questions require product, maintainer, security, legal, or research judgment.
They are intentionally narrower than the completed 0047-0074 implementation queue.

## External pilot

- Will the Hermes Agent reporter or maintainer welcome a focused fix for issue
  #61631, and which upstream tests should be authoritative?
- Which harness can provide useful process evidence without collecting private
  prompts or hidden reasoning?
- Should the first pilot request training consent, or remain audit-only to minimize
  coordination and rights complexity?
- What review-friction and maintainer-satisfaction evidence should determine whether
  the pilot is repeated?

## Verification and execution

- What isolation guarantees are required before Faber executes untrusted candidate
  code or allows network access?
- Who approves, versions, and revokes authoritative verifier specs for a repository?
- What calibration threshold and uncertainty policy allow a probabilistic verifier
  to influence routing, and when must it force human review?
- How should verifier compute be priced when repeated scoring improves confidence?

## Market and money

- Which jurisdiction and operating model should receive legal review first?
- Who is the buyer, worker, verifier operator, and settlement counterparty in the
  first paid pilot?
- Which identity, dispute, cancellation, tax, fraud, refund, and support policies
  are required before funds are committed?
- Should richer trace evidence affect base payout, a separate bonus, or only future
  routing access?

## Data and training

- What minimum number and diversity of tasks, failures, platforms, workers, and
  verifiers makes the first training experiment informative?
- Which consent and license terms allow supervised, router, preference, evaluation,
  or RL use without tying work acceptance to training permission?
- How will withdrawal and deletion propagate to snapshots, derived datasets,
  backups, and already-trained models?
- What leakage, benchmark-contamination, and deduplication policy is required before
  publishing evaluation results?
- Which learned output should come first: attempt-quality prediction, worker routing,
  verifier routing, or orchestration policy?

## GitHub and hosted product

- Which deployment target should hold GitHub App credentials and durable delivery
  state?
- What is the smallest read-only GitHub installation scope that tests real event
  ingestion without publication risk?
- Which protocol records must a hosted customer always be able to export?
- What telemetry, if any, provides operational value in hosted mode, and what
  explicit consent and retention policy would govern it?
