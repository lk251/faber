# Open questions

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
- Can verifier-guided routing, retry, and escalation turn heterogeneous local and
  hosted model capacity into more verified useful work per euro without increasing
  false-accept risk? See
  [`verification-leverage-ai-capacity-dogfooding-2026-09-06.md`](research/verification-leverage-ai-capacity-dogfooding-2026-09-06.md).

## Adoption, application, and outreach

- What measurable evidence can Pushin.eu or willing maintainers provide about the
  scale and cost of low-quality contribution volume: rejection rates, review time,
  abandoned work, false-positive triage, contributor gaming, or burnout?
- Where should contributor/account reputation stop and submission-specific proof
  begin? Can Faber's evidence layer complement reputation-based triage without
  creating another opaque quality score?
- Would Pushin itself, or a project hosted there, be willing to test a small
  maintainer-approved Faber pilot, and what outcome would make the pilot valuable?
  See
  [`pushin-contribution-quality-field-note-2026-09-13.md`](research/pushin-contribution-quality-field-note-2026-09-13.md).
- Which adjacent domain has the strongest version of the same structural problem:
  work becoming cheap to generate while trustworthy verification remains scarce?
- Which relevant contacts in Volt DigiPub and, where appropriate, in or around Guy
  Verhofstadt's party/political network can provide warm introductions to startups,
  companies, technical operators, pilot partners, investors, or grant/funding
  channels? What concise Faber artifact and ask should be prepared before that
  outreach?

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
