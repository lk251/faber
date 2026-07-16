# Audit A4 — Judge comprehension and winning narrative

## Eligibility

Run only after work item 0082 is complete and the repository contains generated blocked
and passing reports. Use the current README, sample reports, Devpost draft if available,
and video draft. Do not begin by reading implementation details beyond what a judge
would see.

## Objective

Evaluate whether a skeptical hackathon judge can understand, remember, and reward Faber
Proof from the submission surfaces alone. Identify anything that makes it look like a
generic AI reviewer, an unfinished framework, or an overbroad marketplace rather than a
complete developer tool.

A report that hides the failed claim, a video that exceeds three minutes, or a narrative
that does not clearly use both Codex and GPT-5.6 is P0.

## Cold-read protocol

Before reading internal architecture documents:

1. Open the top-level README and inspect only the first viewport for 30 seconds.
2. Open the blocked report and inspect only the first viewport for 5 seconds.
3. Open the passing report and inspect only the first viewport for 5 seconds.
4. Read the current Devpost summary once.
5. Read or time the video narration once at natural pace.
6. Record immediate answers to:
   - What is the product?
   - Who is it for?
   - What surprising result does it demonstrate?
   - What does GPT-5.6 do?
   - What does Codex do?
   - What creates the authoritative verdict?
   - Why is this different from AI code review or test generation?
   - What would a team pay for?

Do not revise these answers after deeper reading; they are evidence of first impression.

## Judging-criterion review

Score each official criterion from 1 to 10 using only submission-visible evidence, then
explain the largest score limiter.

### Technological implementation

Look for visible evidence of:

- direct GPT-5.6 structured planning;
- meaningful Codex collaboration and skill integration;
- bounded proof language;
- separation of advisory planning and authoritative execution;
- deterministic, digest-bound evidence;
- live and replay modes;
- adversarial evals and clean installation.

Flag architecture detail that is impressive but impossible to perceive in the video or
README.

### Design

Evaluate:

- one-command or one-skill flow;
- clarity of blocked and passing reports;
- failed claim and counterexample visibility;
- terminology burden;
- installation friction;
- recovery path from block to repair;
- consistency between terminal, report, README, and video.

### Potential impact

Determine whether the submission makes a concrete case for:

- maintainers accepting more agent-generated code safely;
- reduced review risk and faster evidence-based repair;
- a plausible local-to-CI adoption path;
- a credible paying user without unsupported customer claims.

### Quality of the idea

Determine whether the phrase **proof-carrying patches** is earned by the behavior and
whether the independent planner plus bounded executable evidence is memorable and
specific.

Flag any wording that collapses the idea into:

- AI code review;
- LLM-as-a-judge;
- generated tests;
- CI with a model summary;
- a marketplace pitch unrelated to the demo.

## Video audit

Time the full narration at a natural speaking rate and the planned screen actions.
Verify:

- hook in the first 12 seconds;
- ordinary tests visibly green before the block;
- task and diff understandable without scrolling through code;
- GPT-5.6 role visible but not overexplained;
- red `BLOCK` and concrete counterexample receive enough screen time;
- authority boundary explained in one sentence;
- Codex repair is visibly derived from evidence;
- final `PASS` is clear;
- no dead provider latency is included unless deliberately edited;
- live and replay labels are honest;
- total runtime target is 2:35–2:50 and never above 3:00;
- spoken audio explicitly covers Codex and GPT-5.6.

Identify exact cuts when the script is overloaded.

## Visual audit

Inspect at intended recording resolution and browser zoom:

- README first viewport;
- blocked report first viewport;
- passing report first viewport;
- terminal comparison;
- architecture diagram;
- proposed Devpost images.

Check that:

- status is not communicated by color alone;
- text remains legible in a compressed video player;
- the counterexample is readable without narration;
- no digest wall dominates the primary view;
- no machine path, secret, private notification, or unrelated repository context is
  visible;
- the visual system looks coherent rather than like raw developer output.

## Competitive clarity

Write the strongest plausible skeptical objections, such as:

- "This is just an LLM generating tests."
- "The model already knows the expected answer."
- "Replay mode is only a canned demo."
- "The approved catalog is too limited to matter."
- "The local runner is not secure enough for production."
- "Faber existed before the hackathon."

For each, determine whether the current submission answers it in under two sentences
with evidence. Recommend precise copy or one visible proof point when it does not.

## Deliverable

Write:

```text
codex/build-week/audits/A4-judge-comprehension-report.md
```

Include:

- cold-read answers;
- criterion scores and limiting factors;
- exact P0/P1/P2 findings;
- recommended headline and one-sentence description;
- video timing and exact cuts;
- visual findings;
- skeptical objections and concise answers;
- the three highest-leverage submission changes;
- verdict.

Update the audit queue and finding ledger. Route accepted wording, layout, or script
changes to `$build-week-director` or the 0083 submission work rather than redesigning
core code.

## Green criteria

Return `green` only when:

- the product, audience, surprise, model role, authority boundary, and impact are clear
  from a 30-second cold read;
- the blocked counterexample is visible within five seconds;
- the narrative is unmistakably proof-carrying patches rather than generic review;
- every judging criterion has strong visible evidence;
- the rehearsed video remains below 2:50;
- no P0 or unresolved P1 judge-experience finding remains.