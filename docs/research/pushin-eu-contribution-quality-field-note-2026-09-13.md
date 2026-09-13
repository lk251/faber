# Industry field note: Pushin.eu and low-quality contribution overload

Source date: 2026-09-13  
Primary source: [Pushin.eu](https://pushin.eu/)  
Organization discussed: Pushin.eu  
Source type: product site / builder self-description  
Evidence weight: **low-to-medium field signal**  
Authority for Faber: **none; non-normative**  
Independent verification: **not performed**

## How to use this note

Pushin is relevant to Faber in three distinct ways and should remain in the project
memory for all three:

1. **Problem evidence and a source of data.** Pushin is a real product being built around
   the claim that maintainers face too many low-effort contributions. That is useful
   market/problem-space evidence that contribution-quality overload is important enough
   for someone to design a Git host around it. It is not, by itself, independent proof
   of the prevalence or severity of the problem. Pushin's public repositories, policies,
   product choices, and future operational experience may provide data from which Faber
   can learn what "low quality" means in practice, what signals maintainers value, and
   where reviewer time is actually spent.
2. **Potential application surface for Faber.** Pushin explicitly wants to reduce
   low-quality pull requests and issues while leaving the final decision with
   maintainers. Faber may be useful there as an evidence-producing and verification
   layer that helps distinguish contributions with strong proof from contributions that
   impose unbounded review cost. This is a candidate application to investigate, not a
   claim that Pushin needs Faber or has agreed to use it.
3. **Application-discovery case study.** The structure of Pushin's problem can help us
   identify other places where Faber may apply: high-volume submissions, scarce expert
   review, heterogeneous contribution quality, at least partly machine-checkable claims,
   and a need to preserve human authority for ambiguous or high-risk cases.

Do not collapse these three uses into a generic competitor/reference mention. The point
is to learn from Pushin's problem, test whether Faber can help with the stated objective,
and generalize the pattern to other domains.

## What Pushin says it is addressing

Pushin describes itself as a European Git host "built for humans, not AI" and uses the
slogan "Bots are welcome. Slop gets blocked." Its site says maintainers are "drowning"
in low-effort contributions and frames maintainer burnout as a problem the product is
trying to reduce.

The anti-slop mechanisms described on the site are a mixture of current and planned
features:

- invite-only registration;
- a planned vouching/reputation system;
- combining reputation with other signals to assess new pull requests and issues;
- clearly marking and de-emphasizing contributions that appear low quality;
- keeping the maintainer as the final decision-maker; and
- limits on how many pull requests or issues a new contributor can open in repositories
  they do not own.

Pushin says it is currently in invite-only beta and plans general availability in early
2027. It also describes GitHub import and mirroring, plus a REST API with
GitHub-compatible request/response shapes for a large subset of the GitHub API. Those
properties could make a future read-only study or adapter experiment comparatively
cheap, but the available API surface must be checked before assuming compatibility.

These are Pushin's own product claims and plans. This note does not establish that its
anti-slop mechanisms work, that reputation is a reliable quality signal, or that the
problem has any particular measured prevalence.

## Relevance to Faber

Pushin exposes a useful distinction for Faber: **who submitted the work** and **what the
work can prove about itself** are different signals.

Reputation, vouching, account age, contribution limits, and similar controls may help
with abuse and triage, but they do not directly establish that a patch satisfies its
contract. Faber's comparative opportunity is to attach repository-approved evidence to
a contribution: explicit claims, hard verifier results, bounded proof evidence, and
clear escalation to human review when the evidence is missing or ambiguous.

That suggests several questions worth testing rather than assuming:

- Does proof-carrying contribution evidence predict maintainer acceptance or reviewer
  effort better than contributor reputation alone?
- Can Faber reduce the review cost of legitimate first-time contributors without
  creating a reputation moat that favors incumbents?
- Which low-quality contributions can be rejected or de-emphasized by deterministic
  evidence, and which require policy or human judgment?
- Can Faber make low-quality/high-volume submissions cheaper to triage without increasing
  false rejection of valuable contributions?
- Which measurements matter more than raw merge throughput: reviewer minutes,
  false-accept and false-reject rates, escaped defects, time to useful feedback,
  maintainer satisfaction, and newcomer acceptance?

Faber's existing adapter boundary makes this worth considering without making Pushin a
core dependency. [`TASK_AND_SUBMISSION_ADAPTERS.md`](../TASK_AND_SUBMISSION_ADAPTERS.md)
already treats GitHub as one platform adapter rather than the protocol itself.

## Deferred follow-up: three explicit tasks

These tasks are deliberately deferred research/application-discovery work. They do not
replace the current Build Week or external-pilot priorities unless a later roadmap
choice promotes them.

### 1. Study the problem and collect evidence

Use Pushin as a field site for learning about contribution-quality overload. As public
information becomes available, study its public repositories, contribution policies,
anti-slop mechanisms, API behavior, maintainer feedback, and any published outcomes.
Look for evidence about contribution volume, rejection reasons, review burden, newcomer
quality, gaming/abuse, and the tradeoff between filtering aggressively and accepting
good unfamiliar contributors.

Record observed data separately from Pushin's own claims. Do not collect private data,
create accounts, scrape behind access controls, or contact maintainers without the
appropriate human approval.

### 2. Evaluate Pushin as a concrete Faber application

Define what a low-risk, preferably read-only or no-money Faber pilot on Pushin would
need to demonstrate. The target objective should stay tied to Pushin's explicitly stated
problem: reduce the burden from low-quality contributions and help avoid maintainer
burnout without taking final authority away from maintainers.

A useful pilot would compare signals rather than merely add another score. Candidate
comparisons include reputation-only triage, Faber proof/evidence, and combined routing.
Define baselines and success metrics before implementation. If direct integration is
considered, first verify the actual REST API endpoints and whether a thin
`TaskSourceAdapter` / `SubmissionAdapter` is sufficient.

Any external contact, account creation, publication, or write action remains a human
approval gate.

### 3. Generalize the application pattern

Extract the structural features that make this problem potentially suitable for Faber
and use them as a search template for other application domains. Candidate features
include:

- open or semi-open submission surfaces;
- submission volume that can exceed expert review capacity;
- large variance in work quality;
- costly false acceptance and non-trivial cost from false rejection;
- claims that can be partly checked by deterministic or repository-approved verifiers;
- a useful `PASS` / `BLOCK` / `HUMAN_REVIEW` split; and
- incentives for contributors to produce stronger evidence rather than merely more
  submissions.

Search for adjacent systems with the same shape rather than limiting Faber to Git
hosting. Package/release ecosystems, plugin or extension marketplaces, benchmark and
model submissions, bug/issue intake, and other expert-review queues are hypotheses to
investigate, not assumed product markets.

## Evidence to seek before promoting this to a pilot

Before Pushin becomes more than a deferred research/application candidate, try to obtain
or estimate:

- a concrete definition/taxonomy of the contributions Pushin considers low quality;
- baseline contribution volumes and reviewer time;
- false-positive/false-negative costs of filtering;
- acceptance and retention of legitimate first-time contributors;
- examples where reputation and actual contribution quality disagree;
- which checks are deterministic versus heuristic/reputation-based;
- the minimum API and event surface needed for a read-only Faber adapter;
- whether maintainers actually want proof/evidence attached to incoming contributions;
  and
- a measurable pilot objective with a clear stop condition.

## Decision implication

When evaluating Faber's roadmap and product scope, keep Pushin visible as all three of:
(1) a real-world field signal and potential data source for the contribution-quality
problem, (2) a candidate place to apply Faber against an explicitly stated maintainer
pain point, and (3) a case study for discovering structurally similar Faber use cases.

Do not infer product-market fit from this note alone. Promote it only when the evidence,
maintainer/user demand, and a measurable low-risk experiment justify doing so.
