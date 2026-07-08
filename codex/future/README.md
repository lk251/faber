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

## Trace Acquisition, Solver Metadata, And Harness Bounties

1. `0023-trace-protocol-and-evidence-ladder.md`
2. `0024-attempt-manifest-in-pr.md`
3. `0025-worker-and-harness-metadata-registry.md`
4. `0026-trace-incentives-and-market-policy.md`
5. `0027-nixos-agent-harness-bounty-pilot.md`
6. `0028-harness-trace-adapters.md`
7. `0029-supervised-and-rl-data-requirements.md`

Keep this track provider-agnostic and privacy-aware. PR-only submissions must
remain valid where task policy allows them. Richer traces should be rewarded and
provenance-tagged, not globally required. Do not assume Hermes or any other
harness has a specific NixOS support status without investigation.

## Trace, Funding, And External Pilot Queue

The 0030-0045 queue expands the trace track into concrete protocol objects,
adapters, fixtures, funded-work records, and external pilot planning.

1. `0030-trace-protocol-and-evidence-ladder.md`
2. `0031-attempt-manifest-in-pr.md`
3. `0032-worker-harness-model-metadata-registry.md`
4. `0033-cross-platform-reproducibility-evidence.md`
5. `0034-work-budgets-and-funded-issues.md`
6. `0035-github-funding-source-adapters.md`
7. `0036-hermes-issue-survey-and-candidate-ranking.md`
8. `0037-hermes-nixos-tier-one-packaging-pilot.md`
9. `0038-hermes-trace-adapter.md`
10. `0039-nixos-agent-harness-benchmark.md`
11. `0040-faber-attempt-manifest-generator-for-hermes-prs.md`
12. `0041-hermes-best-of-n-selection-pilot.md`
13. `0042-hermes-skills-and-plugin-safety-manifests.md`
14. `0043-real-external-faber-pilot-task-contract.md`
15. `0044-risk-review-for-funded-agent-work.md`
16. `0045-roadmap-update-traces-funding-hermes.md`
