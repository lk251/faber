# Can verification policy itself learn?

**Classification: unresolved and requiring a specific experiment.** Retaining
proposal-time context and delayed feedback is valuable now. Repository-specific
retrieval and approved policy memory are likely useful earlier than training. There
is credible precedent for learned test selection, but this sprint has no evidence
that trained policy proposals beat a frontier model with the same context and
retrieved history. That distinction changes both the implementation and the pitch.

The 2026-09-12 revenue decision remains a bounded acceptance-evidence pilot. It now
explicitly tests whether a customer's recurring verification decisions improve with
accumulated history. The commercial promise is reduced total acceptance effort at
required coverage, whichever method achieves it. A custom trained model is not the
initial deliverable.

## What is learnable, and why it is not one problem

The proposed mapping has several distinct targets:

| Target | Plausible first method | Appropriate feedback | Principal limit |
|---|---|---|---|
| Select existing checks for a change | Dependency/path rules, retrieval, then supervised ranking | Per-check outcomes, non-flaky regression detection, cost and coverage | Unselected-check outcomes usually missing; mandatory checks cannot be dropped by a score. |
| Propose new proof obligations | Frontier reasoning plus historical cases; structured proposals | Owner edits/approval, later counterexamples and executable regression evidence | Policy agreement is not program correctness; exact obligation phrasing has many valid forms. |
| Mandatory/optional and human-review classification | Owner policy + conservative rules; learned suggestions in shadow | Explicit owner classification with rationale and affected scope | Organizational risk tolerance is authority, not a latent label a model may override. |
| Allocate verification effort | Cost-aware ranking; contextual bandit only with support | Incremental fault detection, execution cost/latency, owner correction | Historical chosen actions confound success with ease and selection policy. |
| Propose policy evolution | Retrieval of incident → fix → test → subsequent changes | Accepted/rejected policy diff and later effectiveness | Improvement may mean an ordinary policy file edit, not training weights. |
| Sequence checks, repairs and escalation | Eventually a constrained sequential policy | Whole decision sequence and delayed outcomes | Credit assignment, rare failures, exploration cost and evolving environments make RL premature. |

Ranking a known catalog is substantially easier to supervise than authoring a new
test or deciding acceptable risk. LLM suggestions can identify an unknown scenario,
but a separately reviewed implementation must add its executable capability. Learning
the policy proposal does not authorize the proposal.

## Prior evidence: a real business class, not a novel premise

Meta's 2018 engineering report and paper describe deployed predictive test selection
from change/test histories, including repeated runs to distinguish flaky failures.
That establishes technical feasibility at large scale; its reported coverage and
efficiency are specific to that system, not Faber benchmarks.
[Meta primary report](https://engineering.fb.com/2018/11/21/developer-tools/predictive-test-selection/),
[paper](https://arxiv.org/abs/1810.05286).

Develocity's current 2026.2 documentation describes learning from project history,
configurable selection profiles, must-run controls and running remaining tests. Its
Netflix customer story demonstrates an existing commercial category for learned
verification effort. It also raises the competitive bar: Faber should not build a
generic predictive-test selector and assume a vacant market.
[Current manual](https://docs.develocity.ai/2026.2/using-develocity/predictive-test-selection/),
[detailed selection documentation](https://docs.gradle.com/develocity/predictive-test-selection),
[Netflix case](https://develocity.ai/customers/story/netflix/).

Qodo's history-derived, versioned rule system overlaps with broader policy learning.
Its marketing is evidence of an offered product, not evidence of calibrated
deterministic acceptance. Faber must demonstrate an economically useful increment
over that product and a direct frontier+retrieval workflow.
[Qodo rules](https://www.qodo.ai/blog/introducing-qodo-rule-system/).

Greptile's runtime-validation beta and its separate feedback-learning product surface
also overlap: runtime evidence, scoped context and adaptation are already marketed.
Neither a persistent record nor the phrase “independent validator” establishes Faber's
moat. A pilot using that stack must compare against it where access is available.
[TREX](https://www.greptile.com/trex), [learning](https://www.greptile.com/learning).

## 1. Can repository histories supply useful examples?

Yes, as **partially observed decision histories**, not a ready RL dataset. Each
repository study includes exact source pins and a learning appendix. The strongest
examples connect real proposed changes with later corrections rather than treating
all merged PRs as positive examples.

| History | Input that can be reconstructed | Observed decision / later label | Valid learning use |
|---|---|---|---|
| Hermes #61631, rejected #61636, accepted #61900 | Reported source, finalizer and scheduler behavior, patch/test proposals, maintainer comments with dates | Earlier proposed repair rejected for a mistaken premise; later different fix accepted | Preference/structured-policy correction; correlated alternatives within one incident, not independent successes. It does not prove Faber would diagnose it cold. |
| Omarchy touchpad installation #6985/#7236 | Pre-incident release, install script, existing fresh-ISO policy, chroot/kernel conditions and subsequent patch/test | Reported installation interruption and later focused correction | Retrieve a supported environment distinction; accepted test is a policy-adoption label. Existing written policy means new prose alone may add little. |
| nginx temporary-directory #257812/#257828 | Pre-fix module/test state, report, regression added before repair | Maintainer requested red-before/green-after; later exclusion/test commits | Strong candidate behavioral label if runs are replayed; observed source/history alone is weaker than measured failing/passing executions. |
| nginx VM-to-container #536169 → revert #536256 | Exact test-environment change and prior hardening context | Merged, then reverted within hours because hardening coverage was wanted | Owner preference for environment fidelity. Revert is not proof of a production bug or an observed false acceptance. |

See the [Hermes](../research/2026-09-12-hermes-policy-study.md),
[Omarchy](../research/2026-09-12-omarchy-policy-study.md), and
[nginx](../research/2026-09-12-nixpkgs-policy-study.md) studies and adjacent source
manifests. None of these public histories was executed as a blinded model comparison
in this sprint. Rows reconstructed after reading the answer are development examples.

Commit timestamps alone do not establish when an actor could see a file or comment.
A PR's final base may postdate the incident, and edited issue bodies may contain later
information. Use observed/publication timestamps where available, mark uncertainty,
and exclude doubtful features from an as-of evaluation. A current test catalog is not
the catalog the pre-incident reviewer had.

## 2–4. Observable features, label strength and missing counterfactuals

**Usually observable mechanically:** commit/tree/diff identities; changed paths;
literal workflow/job/test definitions and declared dependencies; file history; owner
rules in source; check-run identities and statuses while retained; PR merge/revert,
review and test-addition events. Dynamic build graphs require controlled evaluation;
private rulesets and off-platform decisions may be inaccessible.

**Needs interpretation:** relationship between failure and policy; whether an
assertion tests the claimed behavior; whether an environment change weakens a guarantee;
implicit compatibility requirements; causal issue/fix links. Store the claim and its
source, who judged it and confidence, rather than silently promoting inferred labels.

| Label | Strength and intended use |
|---|---|
| Reproduced deterministic failure on the prior candidate, pass on repair, same approved environment and negative controls | Strong evidence for that specific behavior. Still not universal correctness. |
| Exact execution result with pinned inputs and non-flaky reruns | Strong observation of that check; false-accept classification requires a separate acceptance/ground-truth comparison. |
| Explicit maintainer acceptance/rejection of a policy scenario, with reason | Strong label for that maintainer's decision at that time; noisy label for correctness or all future maintainers. |
| Later linked escaped regression | Valuable negative feedback, often delayed and attribution-noisy. Needs independent review of whether the earlier policy should have covered it. |
| Added test, merged PR, reverted change, issue closure, green CI | Observable proxy. Ambiguous intent and censoring mean none is automatically a correctness reward. |
| No reported bug after a period | Right-censored observation, not a positive safety label. Record follow-up horizon and observation coverage. |
| Active reviewer effort and clarification | Valuable commercial feedback, rarely recoverable from elapsed review timestamps. Measure prospectively. |

Missing counterfactuals are severe: outcomes of checks not selected; whether a proposed
check would have caught the earlier fault; what a different reviewer or frontier model
would select; cost of alternatives; production exposure; and what the same change
would have done under another environment. Existing logs preferentially show the
checks owners already thought useful. Failed CI may be flakiness, infrastructure,
or the wrong base. Tests added after a bug are informative but leak the answer if
included in the decision context.

Historical deterministic selection rarely gives action probabilities or overlap
sufficient for unbiased off-policy evaluation. Do not turn missing probabilities into
uniform values. Limited full-suite shadow runs can produce a more complete outcome
matrix; exploration must remain owner-authorized and cannot omit mandatory checks.
Contextual-bandit methods address only identified feedback assumptions, not arbitrary
missing labels. [Foundational contextual-bandit research](https://proceedings.mlr.press/v80/foster18a.html).

## 5. Recommended learning formulation

Start with **retrieval plus structured reasoning over an owner-approved action set**.
Use supervised ranking for repeated check selection if a within-repo outcome matrix
exists. Treat maintainer corrections as preference/imitation data with provenance,
not ground-truth rewards. Keep risk and applicability as explicit constraints.

Train a small check ranker before a full structured-policy model; it needs fewer
labels and makes costs and mistakes easier to inspect. Structured prediction may
later learn common obligation or escalation templates. Contextual bandits become
appropriate for optional effort selection only when feedback, action sets and logged
propensities support evaluation. End-to-end RL is last: its delayed rare-failure reward
and owner-policy constraints make it an expensive first experiment.

The most useful hybrid may never involve fine-tuning: deterministic safety floor,
retrieved approved cases, frontier proposal, owner correction, persistent scenario
map, and measured outcomes. That is a learning loop in the product sense even if the
model weights remain fixed.

## 6. What must remain deterministic and authorized

Keep executable capabilities, mandatory checks, acceptable environments, resource
limits, network/data policy, owner identity/approval, revocation and merge/settlement
authority outside model control. The proposal must be data-only and validated against
the approved catalog. A learner cannot add a command, waive a mandatory check, redefine
evidence provenance, turn unknown into pass, or lower risk tolerance by confidence.

The policy used to accept a candidate must come from approved state, not a weakened
policy included in the same candidate. Changes to policy or verifiers require separate
owner review and historical validity/expiration. Learned selection never overrides
failed authoritative evidence; unavailable required evidence stays unresolved.

## 7–8. Preserve now; reuse the data model

The [schema audit](2026-09-12-policy-learning-schema-audit.md) identifies existing
records rather than proposing another universal Episode Envelope. Proof already
preserves much of the exact request, exposed catalog, selections, model provenance and
outcomes. Generic trajectories have room for review, cost, latency and rights.

The expensive losses are **proposal chronology and feedback linkage**. The current
product publishes its bundle after planning/execution, so failed planner attempts may
leave no durable proposal record. Reusing the output directory replaces earlier
bundles. Candidate commit time is not decision wall time. Neither a full current
checkout nor a final successful receipt can recreate what the planner was shown,
which historical cases were retrieved, which proposals were rejected, or what an
owner corrected before success.

Preserve, with customer-controlled retention:

- A proposal ID and actual observation time; repository/task/candidate identity;
  exact bounded request or digest-linked retained artifact; truncation indicators.
- The **then-available** approved catalog/policy and risk constraints, plus retrieval
  case IDs/versions/order and index cutoff. Empty retrieval and unknown retrieval are
  distinct states.
- Proposed selected and declined actions, explicit applicability/uncertainty,
  model/prompt/schema versions and bounded resource estimates. No private reasoning.
- Planner refusal/error as a real event; actual selected-check outcomes, environment,
  repeat/flake status, cost and latency where observed; unknowns explicitly missing.
- Owner correction/approval/rejection with concise reason, authority reference and
  effective scope/time; subsequent incident/fix links and observation horizon.
- Unselected checks as unobserved, plus shadow-run outcomes and selection probabilities
  only where actually recorded. Keep post-decision feedback outside inference inputs.
- Data rights, privacy/retention and training-use status. A public URL is not automatic
  permission to republish full contents or train; customer work acceptance is separate.

**Implementation priority:** an opt-in append-only observation path around the existing
planner flow, reusing existing trace/event and proof records, before training or new
policy-authoring runtime. It records attempts that would otherwise disappear, while
leaving normal Proof bundles and the frozen audit candidate unchanged. See the final
handoff for exact implemented scope and remaining gaps; do not infer a complete data
platform from this minimum capture change.

## 9–11. Local learning, transfer and moat

Both levels matter. Cross-repository learning can suggest generic hazards—cleanup
lifecycle, privilege/context propagation, test-environment substitutions—and sensible
retrieval features. It should not transfer one repo's mandatory checks or risk appetite
as authority to another. Within-repository learning is more likely to improve recurring
selection, environment compatibility and owner preferences because the action set and
decision makers are more stable.

Each firm can own a private loop: accept a policy, observe outcomes, correct it and
reduce repeated verification effort. This supports retention if it improves the next
real decision, not merely accumulates logs. Benefits may be scarce for low-volume
repos or rapidly changing architectures. The first buyer should pay for useful memory
and maintained coverage, not speculative future training.

Potential defensibility lies in trusted integration, accepted scenario history,
maintainer correction quality and a demonstrated cost/coverage frontier. Public
incident retrieval is easy to copy. A customer-owned corpus helps that customer but
is not automatically a company-wide Faber data moat; rights may prohibit aggregation
or leave on export. Respect portability rather than manufacturing lock-in. With
permission, aggregated non-sensitive policy patterns might transfer, but this needs
measured cross-repo lift and explicit rights.

Technical moat is weak until the system demonstrates repeatable improvement under
real constraints. A trained model by itself is not evidence of defensibility. Existing
predictive testing and rules vendors show that commercial value is possible and that
competition already owns substantial data and distribution.

## 12. The experiment that can falsify training

Use [E2](2026-09-12-experiments.md): compare static policy, frontier context only,
frontier plus temporally valid retrieval, learned check router, then learned structured
proposal if justified. Hold source visibility, owner safety floor, runner and budget
constant. Evaluate chronological within-repo holdout and unseen-repo transfer separately.
Use prospective cases to reduce pretraining contamination.

The primary competitor is **frontier + retrieval**, with the same retained private
history. Measure total reviewer time, compute/provider expense, wrong/missing mandatory
scenarios, unnecessary escalation and owner correction effort. A learned model must
save enough to pay for labels, training and upkeep. Historical reconstruction quality
is a feasibility metric, not evidence it wins.

If retrieval is sufficient, retain the observation loop and stop training. If a simple
ranker wins on repeated optional-check allocation, ship that narrow benefit. Only
promote policy learning to the central product/moat after multiple paying customers
see persistent gains and renew because those gains improve subsequent acceptance.
