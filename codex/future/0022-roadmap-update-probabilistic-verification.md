# 0022 - Roadmap Update For Probabilistic Verification

## Goal

Update roadmap and open questions after adding the probabilistic verification
research queue.

## Scope

- Update `docs/ROADMAP.md`, creating it if missing.
- Update `docs/OPEN_QUESTIONS.md`, creating it if missing.
- Add a section named "Probabilistic Verification Scaling".
- Update the queue index if appropriate.

## Questions To Capture

- Which verifier models expose logprobs?
- What open verifier backends are best for self-hosted mode?
- When can an LLM verifier become authoritative?
- How should Faber price verifier compute?
- How should Faber compare cheap-many-attempts-plus-verifier versus
  expensive-single-frontier-attempt?
- How should human review be combined with probabilistic verifier scores?
- What calibration datasets should Faber build first?
- How do we prevent verifier gaming?
- How do we store reasoning traces without leaking private customer data?

## Acceptance Criteria

- Roadmap and open questions include probabilistic verification scaling.
- No implementation code is required for this issue.
- Existing docs still preserve GitHub/payment/model-provider adapter boundaries.
