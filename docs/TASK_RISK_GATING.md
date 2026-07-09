# Task risk gating

Faber evaluates task readiness before funded reservation or agent execution. Risk
review does not change `TaskContract` serialization and does not become verification
authority. A task declares structured risk metadata under
`TaskContract.environment["risk"]`; those declarations are therefore included in
the ordinary contract digest.

The risk components cover:

- external services, publication, or other writes;
- credentials and authenticated account access;
- private or personal data;
- regulated domains;
- security-sensitive areas such as authentication and secrets.

Low-risk local and open-source tasks can proceed without a human gate. Any task
requiring credentials, private data, external writes, regulated-domain work, or a
security-sensitive change requires explicit reviewer identity and approval metadata.
Funding and agent execution can be approved independently.

`review_task_risk()` creates the inspectable assessment and `HumanReviewGate`.
`require_task_risk_readiness()` is called before a funded loop registers or reserves
a work budget. An accepted verifier receipt is still required later for settlement;
risk approval cannot substitute for verification.

## First external pilot

The current Hermes Agent pilot selection in
`docs/research/HERMES_AGENT_PILOT_SELECTION_2026-07-09.md` favors issue #61631
because its reproduction and verification can remain local: no production
credentials, private data, provider calls, or real schedules are required. Opening
an upstream PR remains a separate external write and therefore requires explicit
human approval. This is the intended posture for early Faber pilots: choose useful,
bounded work first and keep publication under maintainer control.
