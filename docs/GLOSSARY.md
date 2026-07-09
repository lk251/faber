# Glossary

- **TaskContract**: digest-bound definition of required work, verifier policy,
  environment, evidence, reward, and source reference.
- **Attempt**: one worker's candidate work bound to a task contract and revisions.
- **Raw trace**: source event stream from a solver, runner, or harness before Faber
  normalization.
- **Trajectory**: normalized audit and learning episode containing task, attempt,
  outcome, and supporting evidence.
- **RL-grade trajectory**: trajectory with sufficient process, environment, solver,
  verifier, reward/cost/latency, consent, and eligibility evidence for declared RL
  use.
- **Evidence level**: acquisition richness from PR-only fallback through manifest,
  trace, harness-native trace, and replayable episode evidence.
- **VerifierSpec**: approved, versioned policy describing how a verifier is run.
- **VerifierRun**: observed result, metrics, failure reasons, and digests from one
  approved verifier execution.
- **VerificationReceipt**: authoritative outcome binding contract, attempt,
  revisions, verifier, and result digests.
- **Advisory score**: ranking or quality signal that has no settlement authority
  unless task policy explicitly grants it.
- **HumanReviewReceipt**: structured reviewer outcome, criteria, authority, comments
  digest, and friction signal.
- **Work budget**: provider-neutral integer minor units assigned to solver work,
  verification, review, or trace-quality incentives.
- **Reservation**: idempotent hold of local budget units for one attempt; not custody
  or payment-provider authorization.
- **Settlement**: receipt-gated accounting outcome after authoritative verification.
- **Trace-quality bonus**: policy-controlled budget split for richer evidence; it
  never replaces authoritative verification.
- **Training eligibility**: consent, rights, redaction, retention, withdrawal, and
  quality decision for a declared learning use.
- **Tombstone**: minimal digest-bound record proving scoped deletion while retaining
  permitted audit references.
- **Faber Protocol**: portable schemas, validation, canonical serialization, and
  export formats.
- **Faber Runner**: local or self-hosted executor for approved verifier policy and
  evidence capture.
- **Faber Verifiers**: verifier specs, execution, calibration, receipts, and optional
  managed verifier services.
- **Faber Market**: work demand, worker supply, budgets, competition, routing,
  reputation, and receipt-gated settlement coordination.
- **Faber for GitHub**: GitHub source/submission/publication adapter; GitHub is not the
  protocol root.
- **Local mode**: account-free files, SQLite, local runner, fake adapters, and no
  telemetry or required external API.
- **Hosted mode**: future account and coordination services that must preserve
  canonical protocol export and explicit privacy/telemetry policy.
