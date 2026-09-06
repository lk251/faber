# Verification leverage as an AI-capacity multiplier

Date: 2026-09-06

Status: deferred research / dogfooding idea. This is not a current Faber Proof priority.

## Hypothesis

Better verification may have a multiplicative economic effect on AI capacity.
If a task is sufficiently well specified and its result can be checked reliably, a
cheaper or weaker model can be allowed to attempt more of the work because failure
need not silently become accepted output. The verifier supplies an error signal: the
worker can retry, a different worker can be selected, or the task can be escalated to
a stronger model.

The relevant objective is not simply model quality per token. It is closer to
**verified useful work per euro of total AI capacity**: subscription spend, metered
API spend, and the electricity/opportunity cost of local inference.

This suggests a personal Faber dogfooding experiment using heterogeneous capacity such
as local Qwen 3.8 27B, coding/model subscriptions, and other providers where permitted
by data policy. The point is not to prefer weak models unconditionally. It is to use
verification to expand the set of tasks on which cheaper capacity is trustworthy.

## Proposed orchestration pattern

For tasks with strong verification:

1. Route the first attempt to the cheapest worker/model that has a plausible chance of
   success.
2. Run repository-owned or Faber-authored verification.
3. If verification fails, return concrete failed claims, counterexamples, or other
   bounded evidence as an error signal and retry.
4. After a retry budget, repeated identical failure, verifier uncertainty, or a risk
   threshold, escalate to a stronger model.
5. Record the worker, model class, attempts, verifier evidence, cost, latency, and final
   outcome so later routing can learn which tier is economical for that task family.

A stronger model could also be used selectively as planner, repairer, verifier
assistant, or escalation target rather than as the default worker for every step.

## Where this should *not* be applied by default

The strategy is least suitable when:

- the task is exploratory and the right objective is not yet known;
- success is subjective or difficult to verify independently;
- novelty, creativity, or deep open-ended reasoning is the main bottleneck;
- verifier coverage is weak enough that false acceptance is a serious risk;
- the consequence of an undetected error is too high for the available verifier.

These cases may still justify stronger-model-first work even if it costs more.

## Economic experiment

Once Faber Proof can produce stable repository-owned verification for a repeated task
family, compare at least three policies on the same task set:

- strong/frontier worker by default;
- cheaper worker plus verifier-guided retries;
- cheaper worker plus verifier-guided retries and escalation to a stronger worker.

Useful measurements include:

- authoritative acceptance rate;
- false-accept and false-reject rate of the verification stack;
- attempts and verifier runs per accepted result;
- escalation rate;
- wall-clock latency;
- estimated local energy cost;
- metered model cost where applicable;
- amortized subscription capacity consumed where it can be estimated sensibly;
- verified accepted work per euro;
- premium/frontier capacity avoided per accepted task.

The core falsifiable question is whether verification overhead is smaller than the
model-cost/capacity savings at a fixed acceptable quality and risk level.

## Why this matters to Faber

This would dogfood several Faber claims simultaneously:

- verification can make heterogeneous workers economically comparable;
- verifier failures can become useful repair signals rather than terminal outcomes;
- cost-aware routing can exploit cheaper capacity without treating low price as proof
  of quality;
- repeated verified trajectories can teach which worker tier should receive which task;
- Faber Proof can be evaluated not only as a correctness tool, but as an amplifier of
  scarce AI capacity.

If the hypothesis holds, improving verification could create an ongoing compounding
benefit: every future euro of local or hosted AI capacity can produce more trusted
work, rather than verification being a one-off productivity improvement.

## Data-governance constraint

Provider routing must respect the data policy of each service. Public/open-source work
can be routed more broadly; private, proprietary, credential-bearing, or otherwise
sensitive material must not be sent to providers whose retention, training, or privacy
terms are unacceptable or uncertain. Provider policy should be an explicit routing
constraint, not an afterthought.

## Priority boundary

Do not let this experiment displace the nearer-term Faber Proof roadmap or empirical
work on how large open-source repositories currently handle verification bottlenecks,
review load, and AI-generated PR volume. Revisit it when there is a stable verifier or
proof-policy path on a real repeated task family; at that point the experiment can be
small and highly measurable.

## Related existing work

This idea extends rather than replaces existing economic/routing work:

- [`0020-verifier-quality-and-intelligence-per-euro.md`](../../codex/future/0020-verifier-quality-and-intelligence-per-euro.md) measures verifier value and quality.
- [`0059-cost-aware-candidate-tournament.md`](../../codex/future/0059-cost-aware-candidate-tournament.md) allocates verifier budget across competing attempts.
- [`0061-worker-reputation-and-value-per-euro-scorecards.md`](../../codex/future/0061-worker-reputation-and-value-per-euro-scorecards.md) measures worker outcomes and value per euro.
- [`ROUTER_DATASETS.md`](../ROUTER_DATASETS.md) is relevant to learning later routing policies from observed outcomes.
- [`FABER_PROOF_PRODUCT.md`](../FABER_PROOF_PRODUCT.md) provides the current proof-carrying-patch direction that could eventually supply the verification layer for this experiment.
