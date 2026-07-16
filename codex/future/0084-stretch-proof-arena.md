# Work item 0084 — Optional Faber Proof Arena

## Priority

**P1 stretch. Do not start until every P0 machine gate is green, the final submission
package can be produced from a clean clone, and the primary video narrative fits below
2:50.**

If this item threatens reliability, judge clarity, final audit time, or human submission
tasks, leave it unimplemented and record that decision. A complete Faber Proof vertical
slice is stronger than an unfinished arena.

## Objective

Add one compact extension that demonstrates Faber's longer-term orchestration advantage:
compare multiple Codex candidate patches against the same proof contract and select an
accepted candidate using authoritative evidence, cost, and latency.

The stretch feature should add one memorable 10–15 second product moment, not a second
product story.

## Required context

Read all P0 Build Week work, the final demo timing, and existing Faber tournament,
router, scorecard, budget, and candidate-selection modules.

## Product behavior

Target command:

```bash
faber proof arena \
  --task .faber/task-contract.json \
  --catalog .faber/proof-catalog.json \
  --candidate <revision-a> \
  --candidate <revision-b> \
  --mode replay \
  --out-dir .faber/proof-arena
```

A smaller fixture-specific demo wrapper is acceptable when a general command would
require substantial new architecture.

The arena must:

1. Run the same task contract, proof catalog, mandatory obligations, and decision policy
   against every candidate.
2. Keep each candidate's task/diff/plan/evidence/receipt binding separate.
3. Reject every `BLOCK` candidate from selection.
4. Require human review rather than silently selecting when no candidate passes.
5. Rank only accepted candidates using a simple documented deterministic policy based
   on:
   - required evidence coverage;
   - authoritative pass status;
   - optional evidence quality;
   - proof execution cost;
   - latency;
   - patch-size or review-friction signal only when already available and justified.
6. Produce an arena result that references candidate decision and receipt digests.
7. Explain why the winner was chosen and why rejected candidates were ineligible.

A model score must never rescue a failed candidate. Reuse existing candidate-selection
or tournament records where their semantics fit; do not distort them merely to avoid a
small explicit adapter record.

## Demo scope

Prefer two original recorded Codex candidates for the same scheduler task:

- one plausible candidate that keeps ordinary tests green but fails the boundary proof;
- one accepted repair.

If both are already the bad and repaired fixture revisions, the arena should show:

```text
ordinary tests: both PASS
Faber Proof: candidate A BLOCK, candidate B PASS
arena selection: candidate B, because only it carries complete accepted evidence
```

This is useful only when it can be demonstrated immediately after the main proof moment
without introducing a new explanation burden.

## Report

Add a compact self-contained comparison section or report showing:

- candidate revisions;
- ordinary test result;
- proof verdict;
- failed/missing obligations;
- evidence coverage;
- cost and latency;
- selection eligibility;
- selected candidate and reason;
- decision and receipt digests.

Do not build a dashboard or hosted UI.

## Tests

Cover at minimum:

- failed candidate is never selected;
- human-review candidate is not silently treated as accepted;
- no accepted candidate yields an explicit no-selection result;
- one accepted candidate wins deterministically;
- two accepted candidates use the documented tie-break order;
- candidate evidence cannot be mixed across revisions;
- replay bundles remain bound to the correct candidate;
- repeated arena replay is deterministic;
- the existing one-candidate Faber Proof flow remains unchanged.

## Go/no-go gate

Before implementing, record in `codex/build-week/STATUS.md`:

- all P0 machine gates are green;
- remaining human-only tasks and time risk;
- current video rehearsal duration;
- estimated feature and audit surface;
- why this increases expected judging score rather than merely adding complexity.

After implementing, rehearse the video. Remove the arena from the video and submission
headline when it pushes runtime above 2:50 or weakens the proof-carrying-patch story.
The code may remain as an understated future-looking extension only when fully tested.

## Constraints

- No new external service.
- No new payment behavior.
- No model-generated executable behavior.
- No replacement of authoritative proof with probabilistic ranking.
- No broad marketplace UI.
- No changes to P0 verdict semantics.
- No implementation before all P0 machine gates are green.

## Acceptance criteria

- The arena compares candidates under identical proof policy.
- Only accepted candidates are eligible.
- Selection is deterministic and evidence-bound.
- The comparison adds no more than 15 seconds to the optional video path.
- Full tests, lint, mypy, clean-install replay, and final audit remain green.
- `codex/build-week/STATUS.md` records whether the feature is included in or excluded
  from the final video and why.

## Commit

Use one focused commit similar to:

```text
Implement optional work item 0084 Faber Proof Arena
```