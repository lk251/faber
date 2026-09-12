# Experiments and decision gates

These are small falsification steps, not a replacement multi-year feature queue.
Definitions and budgets are design choices, not measured sample-size guarantees.
The user addition on policy learning is incorporated: retaining otherwise-lost
decision context precedes model training.

## E0 — Public history and capture feasibility

**Question:** can useful policy decision examples be reconstructed without inventing
labels or allowing future evidence into inputs?

Use the pinned Hermes, Omarchy and nginx incident histories. Separate repository and
available-policy state at decision time from later failure reports, review decisions,
test additions and reversions. Record explicit missingness for actual executions,
unselected-check outcomes, owner intent, cost and active review time. A merged test
is a noisy policy-adoption label; a red-on-base/green-on-fix result is a stronger
behavioral label only when the environment and run evidence are available.

Deliver three or more inspectable records and a local data-capture/split demonstration.
Acceptance: immutable source references, temporal role separation, unknown labels
stay unknown, no code execution or training authority derived from data. This tests
data feasibility, not learned-policy effectiveness. Current results belong in the
[learning analysis](2026-09-12-policy-learning.md) and sprint handoff.

Kill or narrow: if most desired supervision cannot be reconstructed, do not scrape
thousands of PRs. Capture new decisions prospectively with a pilot owner. Public
histories remain retrieval/evaluation examples, not an automatically RL-grade corpus.

## E1 — Priced demand, highest priority

Show one source-backed evidence-gap example and the [exact offer](2026-09-12-first-revenue-plan.md)
to ten qualified leads. Owner: Javier for contact and commercial agreement; Codex for
preparation and authorized analysis. Record current alternative, frequency, buyer,
budget path, usable cases and actual purchase response. No product build prerequisite.

Go: one diagnostic paid, then pilot purchased. No-go: no payment after the bounded
two-round process in the revenue plan. Interest, GitHub stars and praise do not pass.

## E2 — Does persistent policy beat the best inference workflow?

**Pilot design:** one task family, ten historical cases for feasibility; a subsequent
30-case time-ordered set across participating repos if useful. Reserve the later
cases before inspecting outcomes. These are learning pilots, not adequate power to
certify rare-event safety. Group incident, fix, cherry-picks, related tests and copies
together; hold out an entire repo separately for transfer evaluation.

Compare six approaches, with identical owner constraints and approved capabilities:

| Arm | Inputs and permitted choice | First use |
|---|---|---|
| S | Existing handcrafted static/path-based policy | Required baseline; do not deliberately weaken it. |
| F | Frontier reasoning from contemporaneous repo/task/check context | Required baseline; model and context budget recorded. |
| R | Same F plus retrieved **pre-cutoff** failures and accepted decisions | Primary baseline to beat for any training claim. Retrieval index frozen. |
| L | Small learned ranking/check router over existing capabilities | Only after enough usable training rows; mandatory checks always retained. |
| P | Learned structured policy proposal, with deterministic schema and owner review | Conditional on R leaving repeated economically important errors. |
| O | Sequential learned verification effort/escalation | Later; needs action logging and counterfactual support. No autonomous policy relaxation. |

F/R outputs must be captured before revealing later fixes or tests. Historical cases
may be in a frontier model's pretraining: mark contamination risk and require prospective
private/novel cases before claiming generalization. This sprint's research agents saw
the incidents and therefore do **not** constitute blinded F/R experimental arms.

Use the customer's actual review product as an additional practical comparator when
available, including runtime validation rather than only prose review. Do not buy or
enable a third-party service without an agreed pilot scope.

For reviewer-time measurement, randomly assign comparable cases/arms to different
blinded reviewers, or counterbalance order with held-out equivalent cases. The same
reviewer seeing the identical known change twice can improve from memory alone.
Retrospective ten-case inspection establishes feasibility; prospective paired or
matched work is needed for credible time-saved claims. Keep adjudication separate
from the proposer and record familiarity with each incident.

First train L only with a small, interpretable ranker and time-ordered labels; no large
fine-tune. Compare selection recall for known non-flaky failures at equal compute,
missing mandatory obligations, unsupported proposed checks, human edits, active review
minutes, runtime and provider costs. Score abstention separately. Never label every
unselected test as passing, and never use PR merge as a correctness target.

Where safe, run the full approved check set in shadow for a subset of changes to
observe outcomes for checks each router did not select. Preserve these measurements
but keep them hidden from that decision's input. Run repeated failures to estimate
flakiness. If full shadow execution is unavailable, report partial identification;
do not fabricate inverse-propensity estimates from deterministic logs.

**Training go gate:** compared with R on held-out prospective cases, a learned arm
reduces total cost or active review effort by roughly 20% while retaining all mandated
checks and all observed serious known failures, with improvement across two customers
or a clearly documented within-repo benefit. Report uncertainty and per-case results;
a small zero-miss sample is not a bound on rare escaped defects. More data is needed
before reducing any owner-approved requirement.

**Training kill gate:** R matches the learned method at similar total cost after
including labeling, training, serving and maintenance, or gains vanish in chronological
/repository holdouts. Keep retrieval and customer memory; stop training. A retained
data loop can be valuable without changing model weights.

## E3 — Economics of a repeatable service

Deliver three paid pilots in one task family, with a human-approved check plan and
documented case rights. Measure founder setup/delivery/support time as well as buyer
time. Ask for a second paid period before adding hosting. Go only if two buyers renew
or purchase again and their reasons describe an ongoing job. No-go if customization
dominates or free alternatives provide equal value. Then reclassify as consulting or
research instead of manufacturing recurring revenue through subscriptions.

## E4 — Capacity routing, conditional

Only after an accepted verification policy exists, compare frontier-first,
cheap-first with a fixed escalation rule, and learned routing on 20 paired tasks.
Count all retries, verifier work, review, model costs and local machine opportunity
cost. The owner approves data routing and budgets. Go if total accepted-work cost
falls materially without losing observed required coverage; stop if a simpler
escalation rule is equivalent or human repair erases savings.

## E5 — Vertical access, conditional and cheap

If Javier has a real freight or clinic-billing introduction, use ten lawfully
sanitized retrospective cases to test whether existing software leaves a repeated,
valuable exception. Request a diagnostic purchase before connectors. No training
dataset, production integration, clinical decision, carrier/insurer outreach or
payment action is implied. A deposit and usable data can reorder the strategic ranking;
an interesting workflow description cannot.

## Recording outcomes

For each experiment preserve: chosen arm and version, decision cutoff, context and
retrieval references, owner constraints, available actions, selected and rejected
actions, explicit unknown counterfactuals, actual execution outcomes and environment,
human override and reason, costs with currency/units, elapsed versus active time,
delayed outcomes with observation horizon, rights/retention and next decision.

Link existing ProofPlan, verifier run, receipt and trajectory records where available.
Do not add private chain-of-thought. Record concise structured rationale and source
references. Do not imply that collecting a record approves its proposed policy or
permits training; these remain separate owner decisions.
