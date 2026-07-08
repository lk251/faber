# 0016 - Probabilistic Pivot Tournament

## Goal

Implement Probabilistic Pivot Tournament as a budget-aware candidate ranking
algorithm.

## Scope

Support:

- candidate attempt ranking;
- ring pass to reduce position bias;
- pivot selection;
- pivot comparison rounds;
- aggregated win mass or normalized preference score;
- budget accounting.

## Requirements

- Use a fake pairwise preference backend.
- Do not add real model APIs.
- Use deterministic tests with seeded randomness or explicit permutations.
- Support small candidate pools gracefully.
- Record all comparisons as auditable objects with stable digests.
- Return a structured `CandidateSelection` or similar object that can become
  trajectory and routing training data.

## Tests

Add tests proving:

- positional balance in the ring pass;
- pivot selection chooses empirical leaders;
- ranking improves over naive first-candidate selection on fixtures;
- comparison budget is less than full round robin when appropriate;
- output records selected attempt, rejected alternatives, scores, uncertainty,
  and budget used.

## Acceptance Criteria

- The algorithm is deterministic under test fixtures.
- Comparison records are exportable and digestable.
- Candidate ranking remains advisory unless a later authority policy promotes it.
