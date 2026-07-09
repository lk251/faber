# Naming

The project and platform are named Faber.

- GitHub App: Faber, publicly described as Faber for GitHub.
- Marketplace/dashboard: Faber Market.
- Open schemas/protocol: Faber Protocol.
- Self-hosted execution/verifier component: Faber Runner.
- Verifier layer or verifier marketplace: Faber Verifiers.
- Training/orchestration system: Faber Orchestration.
- Initial learned selector: Faber Router.
- Later orchestration models: Faber Models.

Avoid metaphor sprawl. Do not introduce Foundry, Loom, Guild, or woven-fabric
language into the architecture. Keep subsystem names literal and understandable.

## Core terminology

- **Raw trace**: the source event stream emitted by a solver, runner, or harness
  before Faber normalization.
- **Trajectory**: the normalized work episode used for audit, evaluation, routing,
  or learning. A trajectory is more than a raw trace.
- **RL-grade trajectory**: a trajectory with sufficient process, environment,
  solver, verifier, reward/cost/latency, consent, and eligibility evidence for the
  declared reinforcement-learning use.
- **Work budget**: provider-neutral integer minor units assigned to verified work,
  verifier spend, review, or a trace-quality bonus. It is not a payment-provider
  balance.
- **Verifier receipt**: the authoritative, digest-bound outcome emitted from a
  task-authorized verifier run. Candidate-owned CI remains signal only.

Use these exact terms in CLI output, documentation, and adapter publications. Do
not call a raw trace a trajectory, do not call every trajectory RL-grade, and do
not describe a work budget marker as settlement authority.
