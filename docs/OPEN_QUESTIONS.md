# Open Questions

These require human product, legal, security, or market judgment before the next
major implementation slice.

- What kinds of work should Faber Market support first: code changes, review,
  documentation, data labeling, operations tasks, or another narrower wedge?
- What is the minimum verifier standard for work to be considered payable?
- Which settlement flows require legal review before any real payment adapter is
  connected?
- How public should trajectories be by default, and what data must always be
  redacted before training or export?
- Who is allowed to approve verifier specs for a repository or buyer, and how is
  verifier approval revoked?
- What reputation signals should count against a worker: rejected attempts,
  timeouts, policy violations, stale claims, disputed outcomes, or manual review?
- How much human review is needed before trajectories train routing or
  orchestration models?
- What runner isolation guarantees are required before executing untrusted worker
  code outside local development?
- Should retained operating credit exist in early Faber Market flows, or should
  all accepted work settle externally until the economics are clearer?
- What governance model is needed for Faber Verifiers if third parties publish
  verifier specs?
