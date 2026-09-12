# Repository state reconciliation

Observed on 2026-09-12 after `git fetch --all --prune`. This is the starting
state for the revenue-validation sprint, not a new Build Week audit.

## Branches and authority

| Ref | Exact observed tip | Meaning |
|---|---|---|
| `origin/master` | `ae28645668d6f478ccaf5ec3aff003c710dcee1c` | Four September research/documentation commits beyond `c915523`; lacks the Proof implementation. Local `master` was still `c915523`. |
| `origin/build-week/faber-proof` | `96d6c7c4dd125a45e5c39e336d6a0515152428de` | Most advanced product source plus July freight/Spain wedge notes. Contains all four A2 P0 fixes. |
| `origin/build-week/a2-remediation-c215` | `324d506220c415dfe92bc8bb1232e071ab49db95` | Already an ancestor of the product tip; no missing source fix needs merging. Product-source candidate is `b254458d705d801631be8207a0ddce75fbf68c21`; final commit is ledger-only. |
| `origin/portfolio/faber-proof` | `8c7f73a19f1938684b586d1ed61b000c4340bdd3` | Four later commits curate README, make skill opt-in, simplify guidance, scope competition CI, and adjust package copy. Useful presentation work, no new verification capability. |
| local `strategy/convergence-audit` | `2940c0663b5b3154370dcb4513641e3c8320ebea` | Separate July strategic archaeology report; inspected via `git show`. Not present on the product branch and not fetched from a remote. |
| sprint branch | `codex/revenue-validation-sprint`, initially `96d6c7c` | Separate worktree at `C:/Users/javie/repos/Faber-revenue-sprint`; authorized strategic reassessment and bounded experiment. |

`origin/master...origin/build-week/faber-proof` has **4 commits unique to master
and 32 unique to Proof**. The July handoff statement that the remote has only two
branches is stale. Fetch updated `origin/master`; the current product branch was
already synchronized, so there was no incoming product change to pull. The sprint
uses that clean product tip, without changing local master or another worktree.

The original `C:/Users/javie/repos/Faber` checkout had modified
`docs/ROADMAP.md`, modified `codex/future/README.md`, and untracked
`codex/future/0085-compact-canonical-episode-envelope.md`. These are unrelated
Episode Envelope planning changes. They are preserved in place, excluded from this
branch and its commits. The remediation and convergence worktrees are also untouched.

The current request explicitly supersedes automatic continuation of the old queue
for this sprint and explicitly authorizes a new branch and safe push. It does not
authorize customer contact, upstream contributions, production use, or declaring
competition gates satisfied. No merge to master or candidate modification is needed.

## Current versus stale claims

| Prior surface | Actual current interpretation |
|---|---|
| `docs/CODEX_SESSION_HANDOFF.md`: last audit A1 green, source `f2518bd` | Stale operational summary. A2 later found four P0 defects, now fixed but independently unverified. `STATUS.md`, `AUDIT_QUEUE.md`, report and issue #9 are newer evidence. |
| README / generated final audit: machine pass; 710 tests; 49/49 cases | Historical checkpoint observations, not current security clearance. A2-P2-001 says the campaign's actual-verdict field is inferred from expected results; do not cite zero unjustified PASS as a measured real-world rate. |
| A2 source changes | Integrated into the current product branch. The prior convergence audit's statement that there were no later fixes is stale; its broader lack-of-validation conclusion remains supported. |
| Roadmap / Milestone 2 / open questions: Hermes #61631 next | Issue closed 2026-07-10; repair #61900 merged at `6abf1956829d93c487e18eb3051c395b111d3d39`. Historical pilot proposal, no longer an actionable issue. See the current Hermes study. |
| Build Week phase and external submission | Final tag absent; live capture and human submission evidence unresolved in the ledger. The sprint does not infer contest status from elapsed time. |
| September notes on master | Duckbill field note and verification-leverage dogfooding hypothesis are useful, explicitly low-evidence/deferred. They do not exist on the product branch. |
| Portfolio branch | Cleaner presentation exists already. Rebuilding that surface or claiming extraction is a strategic breakthrough would duplicate work. |
| Market, paid loop, RL-grade exports | Tested local records and fake adapters. No verified customer purchase, real settlement, learned routing advantage, or production adoption found. |

Primary upstream references: [Hermes #61631](https://github.com/NousResearch/hermes-agent/issues/61631),
[repair #61900](https://github.com/NousResearch/hermes-agent/pull/61900).
Faber audit evidence: [issue #9](https://github.com/lk251/faber/issues/9),
[A2 report](../../codex/build-week/audits/A2-adversarial-security-report.md),
[finding ledger](../../codex/build-week/AUDIT_QUEUE.md).

## Open issue reconciliation

`gh issue list --repo lk251/faber --state open --limit 100` returned eight issues:

- #4 (0030–0045), #5 (0046), #6 (0047–0075): historical queues whose implementation
  is recorded as completed. Open issue status alone is not an outstanding feature order.
- #8: umbrella independent audit wave.
- #9: A2 remains open and `not-green`; last comment acknowledges all four fixes and
  requires fresh independent verification against `324d506` / source `b254458`.
- #10, #11, #12: A3 installation, A4 judge comprehension, conditional A5 compliance.

No issue provides evidence of a buyer, invoice, paid pilot, or current external
deployment. Issues were read, not edited. No speculative issue backlog was created.

## What exists and what it cannot establish

The useful technical asset is the separation of advisory planning from
owner-approved execution, exact-context evidence, deterministic decision rules,
counterexamples, and portable reports. The dependency-light no-key demo is tangible.
`proof_configuration.py` loads strict owner configuration; `proof_catalog.py`
provides five closed capability families; `proof_workflow.py` and
`proof_product.py` bind execution and evidence. These are code observations, not
assurance that every implementation path is correct.

The existing planner selects from a **pre-approved** catalog. It does not safely
invent an executable verifier for an unfamiliar repository. In particular, Faber's
isolated pytest mode suppresses ambient plugins and conftest; arbitrary upstream
test suites may need their normal repository environment through an approved command
or bespoke harness. That onboarding work cannot be wished away by a model.

The local runner provides no production OS/network/process-tree sandbox; digests are
not signatures. No-key fixtures are `fake-development`, not a live planner quality
study. A2's evidence leaves four P0 fixes independently unverified plus four P1 and
four P2 open. Sell neither production merge authority nor security certification.

The pre-Proof market and trajectory system is useful research substrate. Its
schemas, fake funding loop, consent/export checks and routing scorecards have no
demonstrated buyer or measured economic multiplier. Payment infrastructure is not
required to sell ordinary engineering services and is deferred.

## Reading record and retained history

Inspected the current AGENTS, README, roadmap, milestones, open questions, handoff,
Build Week status/queue, Proof product/threat model, product boundaries, July Hermes
survey/selection, verifier literature note, work item 0075 and relevant pilot/demo
handoffs. Also inspected the September master-only research and the July convergence
audit at their branch refs. The current studies supersede old upstream assumptions.

The earlier convergence audit correctly warned against building a market without
external use. Its proposed 192-attempt calibration gate and larger routing study are
too expensive as the first revenue-learning step. Its narrower invariants are
retained; its experiment sequence is superseded by the smaller paid-validation plan.

The sprint's final validation, generated artifacts, branch and remote status are
recorded in [the sprint handoff](2026-09-12-sprint-handoff.md). No new test result
in that file retroactively clears the independent Build Week audit queue.
