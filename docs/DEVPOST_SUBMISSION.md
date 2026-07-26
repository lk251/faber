# Faber Proof Devpost submission draft

This is copy-ready English submission text for the Developer Tools category. It is not
evidence that a Devpost entry was submitted. The official submission deadline has
passed; use this text only if a timely entry already exists or the organizers explicitly
authorize a modification.

## Project name

Faber Proof

## Tagline

Codex can write the patch. Faber makes the patch prove itself.

## One-sentence description

Faber Proof turns an AI-generated patch into a proof-carrying patch: an independent
GPT-5.6 planner expresses falsifiable obligations, repository-approved capabilities
execute the evidence, and a deterministic policy returns `PASS`, `BLOCK`, or
`HUMAN_REVIEW`.

## Problem

Engineering teams are adopting coding agents faster than they can build confidence in
the resulting changes. A patch can look sensible, come with persuasive model prose,
and pass every ordinary test while still missing the exact boundary condition the issue
was meant to solve. Asking the same model for another opinion creates more prose, not
authoritative evidence.

Maintainers need to know which claims a patch makes, which risky cases matter, what was
actually executed, and what concrete counterexample should block acceptance.

## What it does

The original demo starts with a plausible Codex scheduler patch. Both the bad patch and
the repaired patch pass the ordinary test suite. The bad patch nevertheless discards a
complete report on the last permitted turn.

Faber Proof gives a bounded task and diff to an independent GPT-5.6 proof planner. The
model decomposes the contract into claims and selects only repository-approved,
data-only proof templates. Faber validates every binding, executes the approved
capabilities, creates verifier runs and receipts, and applies deterministic policy.

The bad patch receives `BLOCK` with the exact failed claim and a two-turn
budget-boundary counterexample. Codex uses that evidence to make one narrow ordering
repair. Ordinary tests stay green, and the same required proof returns `PASS`.

A self-contained HTML report makes the model analysis, authoritative evidence,
counterexample, receipts, and digests independently inspectable. Replay reproduces the
workflow without an API key, account, network request, or provider SDK.

## Why it is novel

Faber Proof is not a prose review bot and does not execute arbitrary model-generated
tests. GPT-5.6 must express its analysis in a closed proof language. It may select an
approved template and provide bounded JSON data, but it cannot provide a command,
source file, import, arbitrary path, or verdict.

The model helps decide what should be tested. Repository policy decides what may run.
Receipted verifier evidence decides whether the patch passes. Missing, stale,
contradictory, partial, or context-mismatched evidence fails closed.

## How it was built

Codex implemented the Build Week extension through one primary implementation thread,
a repository-scoped director skill, focused work-item prompts, test-driven repair, and
independent audit prompts.

The implementation adds provider-neutral proof records, a direct optional GPT-5.6
Responses API adapter with strict structured output, exact live/replay bindings, a
bounded proof catalog, five fixed executor families, Faber Runner evidence, verifier
runs and receipts, deterministic decision policy, atomic portable bundles, Markdown
and self-contained HTML reports, and the `$faber-proof` repository skill.

The original standard-library scheduler demo has separate bad and repaired candidate
commits. The release path includes 49 deterministic adversarial cases, a bounded
artifact privacy audit, conventional wheel and sdist packaging, an isolated
clean-install audit, a no-key installed demo, deterministic report regeneration, and a
prepared Linux/Windows workflow.

## GPT-5.6 use

GPT-5.6 receives the task title and requirements, exact revisions, a bounded redacted
diff, mandatory owner claims, the approved proof catalog, and prompt/schema
commitments. It returns strict structured claims, severities, risk rationale, approved
template selections, JSON-compatible parameters, coverage links, and uncovered risks.

It cannot define executable commands, Python source, imports, catalog entries, timeout
policy, filesystem authority, or the final verdict. Faber records requested and
returned model identifiers, response ID when available, token usage, latency, mode,
request digest, structured-response digest, and all relevant context commitments. It
does not require private chain-of-thought.

Live and replay responses use the same parser and validator. The current committed
replays are explicitly `fake-development` deterministic fixtures for accessible
no-key testing. Final `live-reviewed` provenance remains a guarded human gate and is
not fabricated here.

## Codex use

Codex implemented most of the post-baseline Faber Proof functionality in the primary
Build Week thread. The `$build-week-director` skill resumes the next eligible work item,
preserves audit and human-gate boundaries, runs validation, and records durable status.
The `$faber-proof` skill drives the user workflow from context validation through proof,
counterexample-guided repair, and rerun.

In the demo, Codex reads the failed last-turn obligation and moves only the completed
report check ahead of the budget-exhaustion return. It does not weaken the task or
replace the scheduler. The same proof then changes from `BLOCK` to `PASS`.

Primary `/feedback` session ID:

```text
019f6d53-0a3d-71d3-abd7-749dc4a3784c
```

## Human technical and product decisions

- Focus the entry on proof-carrying patches instead of the broader Faber market.
- Keep the GPT-5.6 integration behind a provider adapter.
- Make model planning advisory and deterministic verifier evidence authoritative.
- Use bounded owner-approved templates rather than generated executable tests.
- Build an original local demo without third-party project or service dependencies.
- Preserve no-key replay so judges can run the core experience immediately.
- Fail closed on missing, stale, contradictory, partial, or unbound evidence.
- Keep live fixture replacement atomic and human-reviewed.
- State the pre-existing versus new-work boundary explicitly.

## Challenges and tradeoffs

The hardest integrity problem was replay binding. A committed response is useful only if
it is bound to the exact task, candidate diff, catalog, prompt, schema, model, and
response digest. Faber recomputes those commitments and rejects cross-candidate or stale
reuse.

The hardest product tradeoff was safe expressiveness. An unrestricted test generator
would be flexible but would let untrusted model output define behavior. Faber instead
uses a small catalog of fixed executor families and closed parameter schemas.

Provider neutrality required keeping GPT-5.6 metadata and transport in an adapter while
proof plans, evidence, receipts, and verdict policy stay generic. Deterministic portable
reports required removing host paths and external assets while retaining enough
evidence to audit the result. The final workflow was deliberately kept small enough to
show the full reversal in under three minutes.

## Accomplishments

- Original bad/repaired demo: ordinary tests `PASS`/`PASS`, Faber Proof
  `BLOCK`/`PASS`.
- The blocked report shows one exact failed required claim and one concrete
  budget-boundary counterexample.
- 49/49 deterministic adversarial cases pass with zero unjustified `PASS` outcomes.
- At the completed 0083 machine checkpoint, 710 tests passed and one guarded live test
  skipped; Ruff and mypy also passed.
- Wheel, sdist, isolated base install, optional live-extra install, installed CLI,
  no-key replay, privacy audit, and four byte-stable report checks passed.
- The measured HB2 bad/repaired demo completed in 6.258291 seconds and generated
  232,259 bytes with zero covered privacy findings.
- The base package has no runtime dependencies; the OpenAI SDK is an optional extra.

These are local deterministic measurements, not customer, production, or universal
correctness claims.

## Potential impact and business path

The initial buyer is an engineering team paying to reduce review risk and safely accept
more agent-generated code. The adoption path is:

1. local Codex skill and CLI;
2. CI/check integration for engineering teams;
3. repository-approved proof catalogs for repeated task classes;
4. organization policy, audit export, and team reporting;
5. stronger isolated runners and broader proof libraries;
6. later evidence-aware routing and Faber market integration.

The product has no claimed customers or revenue today.

## What is next

Activate and harden CI/GitHub integration, move execution into stronger isolated
runners, expand repository-approved proof libraries, add signed policy and evidence
controls, and use proof quality, cost, and latency to route among multiple candidate
patches.

## Built with

- Python 3.11+
- Python standard library
- Git
- pytest
- Ruff
- mypy
- setuptools/build
- optional official OpenAI Python SDK
- OpenAI Responses API structured output
- GPT-5.6
- Codex repository skills
- Markdown, JSON, JSONL, and self-contained HTML/SVG

## Category

Developer Tools

## Links and IDs

| Field | Value | Validation |
|---|---|---|
| Public YouTube video | `HUMAN_GATE::PUBLIC_YOUTUBE_URL` | Incomplete; human recording/upload required |
| Repository | https://github.com/lk251/faber | Known; judge access remains a human attestation |
| Final submitted commit or tag | `HUMAN_GATE::FINAL_SUBMISSION_REF` | Incomplete; final tag intentionally absent |
| Primary Codex session | `019f6d53-0a3d-71d3-abd7-749dc4a3784c` | Complete and recorded |
| Local blocked report | `.faber/build-week-demo/bad/report.html` | Generated by no-key replay |
| Local passing report | `.faber/build-week-demo/repaired/report.html` | Generated by no-key replay |
| Static hosted sample report | Not hosted | Optional; do not invent a URL |

## Pre-existing versus Build Week work

Faber's protocol, task/attempt/receipt/trajectory objects, local runner, trajectory
quality system, source adapters, market records, and training-data foundations existed
before the competition.

Faber Proof is the post-baseline extension: proof records and policy, GPT-5.6 planner,
context-bound replay, bounded catalog and executors, complete authority binding, CLI,
atomic bundles, reports, Codex skill, original demo, guarded live capture, adversarial
evals, privacy/release tooling, packaging, and submission artifacts.

The annotated baseline is `build-week-2026-baseline` at
`64f775cfe2f622837bd9aaa40f6369aa22af1d80`. The repository-generated
`docs/generated/BUILD_WEEK_DELTA.md` is the auditable file-and-commit ledger.

## Security and limitations

The local runner is development infrastructure, not a production sandbox. It does not
provide OS, container, VM, network, or descendant-process isolation. The privacy
scanner is bounded, owner-approved catalog policy is trusted, and digests provide
integrity rather than signatures. Faber proves declared obligations, not universal
program correctness. A replay is not a new live model call.
