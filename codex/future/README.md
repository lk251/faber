# Faber Future Queue

This directory tracks future implementation issues that are not part of the
completed 0003-0014 queue.

## Probabilistic Verification Scaling

Reference project: [lk251/llm-as-a-verifier](https://github.com/lk251/llm-as-a-verifier).
Use it as read-only reference for ideas, invariants, fixtures, and tests. Do not
copy provider-specific runtime assumptions into Faber core.

1. `0015-probabilistic-verifier-protocol.md`
2. `0016-probabilistic-pivot-tournament.md`
3. `0017-multi-attempt-selection-loop.md`
4. `0018-progress-scoring-and-agent-monitoring.md`
5. `0019-dense-reward-export-for-training.md`
6. `0020-verifier-quality-and-intelligence-per-euro.md`
7. `0021-authority-boundaries-for-llm-verifiers.md`
8. `0022-roadmap-update-probabilistic-verification.md`

Keep these issues provider-agnostic. Do not add real model APIs, payment
providers, or settlement authority from advisory scores unless a later issue
explicitly changes that boundary.
