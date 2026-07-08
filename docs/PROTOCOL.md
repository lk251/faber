# Faber Protocol

Faber Protocol is the open schema layer for verified work and trajectory export.

Initial objects:

- `TaskContract`
- `Attempt`
- `VerifierRun`
- `VerificationReceipt`
- `Trajectory`
- `SettlementEvent`
- `WorkerProfile`
- `RouterDecision`
- `MarketEvent`

The protocol should support JSON and JSONL export for audit and training. A JSONL
trajectory stream should be useful for supervised learning, reinforcement learning,
preference learning, router training, and verifier-quality analysis.

The protocol must remain compatible with hosted and self-hosted runners, multiple
payment providers, multiple model providers, and non-GitHub task sources.

GitHub evidence can seed task contracts and attempts, but receipts should bind
approved verifier outputs rather than trusting candidate-owned CI as authority.
