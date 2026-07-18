---
name: build-week-director
description: Continue the Faber Proof OpenAI Build Week implementation from the next incomplete repo prompt. Use when asked to continue Build Week, get to work, maximize the hackathon submission, resume the queue, address audit findings, or prepare the submission. Do not use for ordinary Faber roadmap work after the competition is closed.
---

# Build Week director

Drive the current Build Week queue without asking the user to restate decisions or
paste repository prompts.

## Route

1. Inspect the branch, latest commit, and working tree. Preserve unrelated changes and
   use `build-week/faber-proof`.
2. Read `codex/build-week/STATUS.md` and `codex/build-week/AUDIT_QUEUE.md`. Treat them as
   the current sources for work, findings, audit eligibility, and human gates.
3. Address the highest-priority open P0 finding; otherwise select the first incomplete
   eligible P0 item. Read its complete prompt or finding report and reproduction.
4. Load `docs/FABER_PROOF_PRODUCT.md`, `docs/BUILD_WEEK_2026.md`, or other references
   only when the selected work needs their policy or product detail. Read the handoff
   only on an actual session or machine resume.

## Execute

- Implement the smallest coherent solution that satisfies the selected acceptance
  criteria and preserves the winning vertical slice.
- Keep provider code in adapters and model output advisory and data-only. Never execute
  commands, source, imports, or paths supplied by untrusted input.
- Add regression and failure-path tests for changed behavior. Run the prompt-specific
  checks, the full available checks, and the demo when it is runnable.
- Update `STATUS.md` with the commit, exact validation, demo state, limitations, and
  next action. For a finding, update its ledger entry but leave verification to an
  independent audit. Update the handoff only when its baseline or next action changes.
- Create one focused commit, then continue through eligible P0 machine work while the
  tree is clean. A human-only gate blocks only work that actually depends on it.

## Boundaries

Preserve the authority and fail-closed rules in `AGENTS.md` and the product document.
Do not broaden P0 scope or rewrite settled product decisions unless an acceptance gate
cannot otherwise be met.

Stop only when an incomplete human-only gate blocks the selected work, an actual P0
failure prevents safe progress, or the tree cannot be made safe. Never request evidence
already recorded in `STATUS.md`. Leave a clean commit and the exact human action needed.

When `AUDIT_QUEUE.md` says an independent audit is eligible, record it and continue
machine-completable implementation. Include this instruction in the milestone report:

```text
Use $build-week-auditor and run the next eligible independent audit.
```

Do not independently audit the director's own work. Open P0 findings take priority;
open P0 findings or an incomplete final audit block final tagging.

Report completed work and commits, verification and demo verdicts, remaining P0 work,
the next eligible audit, and any human gate.
