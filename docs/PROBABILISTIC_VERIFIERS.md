# Probabilistic Verifier Boundary

Faber exposes a provider-neutral `ScoringBackend` interface. The protocol models
criteria decomposition, repeated evaluation, aggregate score distributions,
uncertainty, pairwise preference, progress-prefix scores, digest-keyed caching,
latency, and integer-minor-unit scoring budgets.

The first backend is deterministic and fake. It performs no model or network
call and exists to make schemas, authority boundaries, caching, and accounting
testable. The read-only `llm-as-a-verifier` research reference informed these
interfaces but is not imported and is not a Faber dependency.

Probabilistic scores are advisory by default. They may rank candidates, monitor
progress, and become training evidence. They cannot produce an authoritative
`VerificationReceipt` unless the task's `VerificationPolicy` names that backend
in `authoritative_probabilistic_verifier_ids`. Even then, settlement consumes the
resulting accepted receipt, never the score object itself.

This boundary leaves future repeated scoring, pairwise tournaments, and model
provider adapters replaceable while keeping Faber core deterministic and
verifier authority explicit.
