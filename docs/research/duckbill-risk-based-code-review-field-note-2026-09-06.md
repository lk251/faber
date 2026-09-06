# Industry field note: Duckbill's risk-based code-review workflow

Source date: 2026-09-06  
Primary source: [Mike Julian on X](https://x.com/mikejulian/status/2096450476170694785)  
Organization discussed: Duckbill  
Source type: practitioner social-media report / self-report  
Evidence weight: **low**  
Authority for Faber: **none; non-normative**  
Independent verification: **not performed**

## How to use this note

This is a problem-space / industry-practice observation, not an endorsement or a model for
Faber to copy. It is useful for hypothesis generation and for tracking how real teams say
they are responding to the review and verification bottleneck created by much higher
agent-driven code throughput.

Do not treat the reported workflow, thresholds, or metrics as authoritative. Do not cite
this source alone as evidence that reducing human code review is safe, that the approach
caused the reported throughput change, or that its quality outcomes are acceptable. The
claims are self-reported in a social-media thread and are not accompanied here by an
independent repository audit, incident data, escaped-defect data, rollback rates, or a
controlled comparison.

## What the thread reports

Mike Julian reports that Duckbill accumulated roughly 60 open pull requests for a team
of five, representing about two days of code-review work. Instead of putting an AI
reviewer in front of every pull request, the team reportedly shifted to a risk-based
review policy and stronger automated guardrails.

The reported workflow includes:

- mandatory human review when changes touch selected higher-risk surfaces: the public
  API/MCP, authentication, the design system, non-additive database-schema changes, or
  agent skills;
- a shell script that labels changes requiring human review;
- stronger unit and end-to-end tests, linting, type checking, and post-deployment
  observability;
- broad activation of rules in tools including Ruff, Prettier, ESLint, and ty, plus a
  reported unit-test coverage floor of 85%;
- deterministic CI scripts for rules that do not require model judgment;
- isolation of changes to agent skills / `AGENTS.md` into their own pull requests;
- skill evals followed by deletion or revision of skills that no longer appeared useful
  with newer models;
- centralization of documentation after agent-generated Markdown reportedly accumulated
  and created context-quality problems, with documentation authorship restricted to
  humans in this workflow.

The thread also reports before/after delivery metrics:

- merged pull requests: 353 to 684, described as about 80/week to 154/week (+94%);
- merges within one hour: 28% to 45%;
- merges within 24 hours: 76% to 80%;
- median merge time for human-reviewed pull requests: 26 hours;
- median merge time for pull requests without human review: 1 hour.

These are operational claims from the source, not validated Faber benchmarks. In
particular, faster merges are not by themselves evidence of correctness, safety, or
better verification.

## Relevance to Faber Proof

The useful signal for Faber is not "stop reviewing code." It is that at least one small
software team reports responding to a review bottleneck by separating changes by risk,
routing scarce human attention to selected classes, and moving more of the routine
assurance burden onto deterministic checks and runtime evidence.

That overlaps with several Faber Proof questions:

1. **Risk-based escalation.** Which task or change classes can be verified mechanically,
   and which should produce `HUMAN_REVIEW` regardless of otherwise-green evidence?
2. **Deterministic checks first.** Which claims can be discharged by tests, type checks,
   linters, schema checks, reproducible builds, or other hard verifiers instead of an
   LLM judgment?
3. **Evidence after deployment.** When pre-merge proof is insufficient, can bounded
   post-deployment observability or smoke evidence be incorporated without pretending
   it proves more than it does?
4. **Agent-specific risk surfaces.** Changes to agent instructions, skills, and context
   structure may deserve their own verifier policy because they can alter future agent
   behavior without looking like ordinary application-code changes.
5. **Reviewer-time reduction as an outcome.** Faber should eventually measure whether
   proof evidence reduces human review effort while holding or improving quality, not
   merely whether it increases merge throughput.

Faber Proof is importantly different from the workflow described in the thread. Its aim
is proof-carrying patches: claims are bound to approved evidence and deterministic
policy decides `PASS`, `BLOCK`, or `HUMAN_REVIEW`. A risk-routing policy may be a useful
comparison point, but it is not a substitute for demonstrating that the relevant claims
were actually checked.

## Missing evidence and follow-up questions

This source would become more informative if paired with direct operational evidence,
for example:

- the actual CI/risk-label scripts and repository policy;
- exact before/after time windows and PR-size distributions;
- escaped defects, incidents, regressions, rollbacks, and hotfix rates;
- production error or SLO changes;
- false-negative rates for the risk classifier;
- reviewer-hours saved rather than merge latency alone;
- examples of low-risk changes that passed the guardrails and high-risk changes that
  were correctly escalated;
- evidence that the reported coverage and static-analysis changes test meaningful
  behavior rather than simply increasing nominal coverage.

Until evidence like that is available, retain this as a low-weight field signal in the
problem-space research corpus.
