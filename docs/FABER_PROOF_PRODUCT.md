# Faber Proof

## Product thesis

**Faber Proof creates proof-carrying patches for agentic software development.**

> Codex can write the patch. Faber makes the patch prove itself.

A green test suite is necessary but often insufficient for an AI-generated change. The
agent may solve the obvious path while missing the exact boundary condition that made
the issue difficult. Asking the same model for a prose self-review creates confidence,
not evidence.

Faber Proof separates these roles:

- Codex produces or repairs the candidate patch.
- A fresh GPT-5.6 Sol context converts the issue contract and candidate diff into
  falsifiable proof obligations.
- Faber accepts only bounded, data-only proof templates approved by policy.
- Faber executes those probes and existing verifiers, binds the results into receipts,
  and produces a deterministic verdict.
- Codex consumes the failed claim and counterexample to repair the patch.

## Target user

Primary user: a maintainer or engineering lead reviewing patches produced by Codex or
another coding agent.

The user needs to answer:

1. What behavior does this patch claim to provide?
2. Which risky boundary cases matter for this task?
3. Which claims have executable evidence?
4. What exact counterexample blocks the patch?
5. Can the evidence be replayed and audited independently of the model's prose?

## Competition positioning

Track: **Developer Tools**.

Faber Proof is not presented as the whole Faber market, protocol, payment layer, or
training system. Those are foundations and future expansion paths. The competition
entry is one complete developer experience from candidate patch to proof report.

The novelty is not that an LLM reviews code. The novelty is that the model must express
its analysis in a constrained proof language and is not trusted to determine the final
result.

## Core user journey

### In Codex

```text
$faber-proof prove the current patch against .faber/task-contract.json
```

The skill:

1. Verifies the repository and revision inputs.
2. Runs `faber proof` in live or replay mode.
3. Reads the resulting evidence report.
4. When blocked, repairs only the demonstrated failure.
5. Reruns the same proof until the decision is `PASS` or requires human review.
6. Reports exact commands, evidence paths, and unresolved limitations.

### From the CLI

Target interface:

```bash
faber proof \
  --repo . \
  --task .faber/task-contract.json \
  --catalog .faber/proof-catalog.json \
  --base <base-revision> \
  --candidate <candidate-revision> \
  --mode replay \
  --replay .faber/replays/gpt56-proof-plan.json \
  --out-dir .faber/proof
```

Additional target options:

```text
--mode live|replay
--model gpt-5.6
--critic-count 0|1
--max-diff-bytes
--json
--dry-run
--open-report
```

Target exit codes:

```text
0  PASS
1  BLOCK
2  HUMAN_REVIEW or operational failure
```

## Product architecture

```text
Task contract + bounded redacted diff + approved proof catalog
                              │
                              ▼
               GPT-5.6 proof planner adapter
                 - behavioral claims
                 - risk and severity
                 - template selections
                 - JSON parameters
                 - coverage gaps
                              │
                              ▼
                    Optional GPT-5.6 critic
                 - missing obligations
                 - contradictions
                 - unsupported assumptions
                              │
                              ▼
                 Faber plan validation and policy
                 - known templates only
                 - parameter schemas
                 - mandatory obligations
                 - no executable model output
                              │
                              ▼
                    Approved proof executors
                 - existing command verifier
                 - pytest-node verifier
                 - Python-call probe
                 - file/content invariant
                 - artifact/schema verifier
                              │
                              ▼
             Verifier runs + verification receipts
                              │
                              ▼
                   Aggregate proof decision
                 PASS | BLOCK | HUMAN_REVIEW
                              │
                              ▼
           Markdown + self-contained HTML evidence report
```

## Proof language

The initial proof catalog should be deliberately small, useful, and safe. The model may
select a template and provide JSON-compatible parameters, but it may never provide a
command or source code.

### `existing-command`

Runs a command already present in an approved `VerifierSpec`. The model supplies only
the registered verifier ID and explains the claim it covers.

### `pytest-node`

Selects one or more pre-approved pytest node IDs from the catalog. The model cannot
supply an arbitrary path or command. The executor resolves the node through the
catalog.

### `python-call`

Calls a catalog-approved module and callable with JSON-compatible positional and
keyword arguments. The model supplies values and an assertion operator such as:

```text
equals
not_equals
is_none
is_not_none
raises
contains
truthy
falsey
```

The catalog controls the import target, working directory, timeout, and result
serialization. The model cannot choose a new module, callable, import, path, or code
fragment.

### `file-invariant`

Checks an approved repository-relative file or generated artifact using a bounded
operator such as exact digest, contains, does-not-contain, valid JSON, or schema-valid.
The catalog controls the allowed path.

### `artifact-validator`

Invokes an existing Faber artifact validator against an approved artifact type.

The first release does not need a universal testing language. It needs enough
expressiveness to prove the original demonstration and show a credible extension path.

## Execution authority and local isolation

The executable proof catalog is repository-owner policy, not planner output. Each
entry binds an immutable ID and version to an exact registered verifier, family,
working directory, environment, timeout, output limit, approved paths or targets, and
trusted source digests. Before any launch, Faber verifies the complete catalog and
registry commitments, every parameter schema, the trusted-source byte budget, and a
bounded digest of the executable workspace. It rechecks that workspace around each
obligation and fails closed if the visible state changes.

The initial executors deliberately use narrow launch paths:

- `existing-command` resolves an exact `VerifierSpec` and runner-policy digest, with
  only catalog-owned environment values;
- `pytest-node` uses isolated Python, a fixed Faber-owned temporary config, disabled
  ambient plugins and `conftest.py`, a fresh external bytecode cache, and only pinned
  node sources;
- `python-call` uses a fixed Faber helper, exact pinned source bytes, guarded
  repository-local imports, a closed assertion and exception vocabulary, and bounded
  typed JSON;
- file and artifact families resolve normalized in-root paths without following
  symlinks and persist bounded observations rather than unbounded content.

Child input, output, errors, and drain completion are bounded. Timeouts, truncation,
partial capture, missing evidence, source changes, and operational errors cannot create
passing authority. Each workflow run also places the same canonical proof-authority
binding in run metadata and receipted result metrics. That commitment covers the task,
attempt, plan, selection, catalog entry and catalog, capability, execution policy,
workspace, verifier identity, and raw verifier authority, preventing an old receipt
from being relabeled for a different proof.

This is still development-local execution, not a security sandbox. It does not provide
operating-system, container, network, or descendant-process isolation. Snapshot checks
detect ordinary workspace mutation but cannot eliminate every concurrent
swap-and-restore race. The local path is therefore for an owner-approved workspace;
production execution needs an immutable checkout plus an isolated process, VM, or
container boundary with enforceable network and process-tree policy.

## Model roles

### Planner

The planner receives:

- task title, description, requirements, acceptance and rejection criteria;
- base and candidate revisions;
- a bounded, redacted diff;
- selected relevant file summaries when needed;
- the approved proof-template catalog;
- mandatory verifier IDs;
- prompt-template and schema versions.

It returns structured data containing:

- claims;
- severity;
- risk rationale;
- selected template IDs;
- template parameters;
- expected behavior;
- coverage links;
- uncovered risks;
- a human-review recommendation.

### Critic

The optional critic receives the task, diff digest, catalog, and planner output. It may
identify missing obligations or contradictions and may propose additional selections
from the same catalog. It cannot remove mandatory obligations or make a verdict.

Use one critic in the polished live demo only when latency and reliability are already
acceptable. Replay should include the chosen final plan.

### Evidence record

Record only auditable model-run metadata:

- requested and returned model identifiers;
- response ID when available;
- prompt-template version;
- request digest;
- structured-response digest;
- token usage when available;
- latency;
- live or replay mode;
- refusal or error state.

Do not require or store private chain-of-thought.

## Authority and verdict policy

GPT-5.6 is advisory. It identifies what should be tested; it does not decide whether the
patch passes.

### `BLOCK`

Return `BLOCK` when any authoritative verifier or proof probe demonstrates that a
required claim is false.

### `HUMAN_REVIEW`

Return `HUMAN_REVIEW` when:

- the model call fails, refuses, times out, or returns invalid structured output;
- a mandatory verifier is unavailable;
- a high-severity claim lacks executable evidence;
- the planner and critic expose a material contradiction;
- the evidence bundle is incomplete or internally inconsistent;
- policy cannot deterministically classify the result.

### `PASS`

Return `PASS` only when:

- all mandatory obligations are present;
- every selected authoritative verifier passes;
- every required claim has accepted executable evidence;
- no uncovered high-severity risk remains;
- all plan, replay, receipt, and decision digests validate.

No model score, explanation, or confidence value may override failed or missing
authoritative evidence.

## Mandatory original demonstration

Create a small original Python package with a scheduler or bounded conversation loop.
The task contract requires the system to preserve and return a complete composed result
when a turn or work budget is exhausted, while incomplete or empty executions must
remain failures.

### Base behavior

The original code has clear behavior and an ordinary test suite.

### Bad AI patch

The bad patch appears plausible and makes the ordinary tests pass, but loses the final
composed result on the exact budget-exhaustion boundary.

Faber Proof must:

- show the ordinary tests passing;
- have GPT-5.6 identify the budget-exhaustion claim;
- select or parameterize a catalog-approved proof probe;
- produce a concrete failing input and observed result;
- return `BLOCK`;
- generate a red report with the failed claim visible above the fold.

### Repaired AI patch

Codex repairs the narrow defect using the counterexample. The same proof plan or its
valid equivalent must:

- keep ordinary tests passing;
- satisfy the boundary proof;
- preserve rejection of empty or incomplete runs;
- return `PASS`;
- generate a green report with all claims bound to evidence.

### Demonstration command

Target:

```bash
faber demo proof --mode replay --out-dir .faber/build-week-demo
```

It should produce both reports and print a concise comparison:

```text
ordinary tests:       PASS -> PASS
Faber Proof verdict: BLOCK -> PASS
failed claims:          1  ->  0
```

## Evidence report design

The report must be self-contained HTML with no external runtime assets. The first
screen must show:

- `PASS`, `BLOCK`, or `HUMAN_REVIEW`;
- task and candidate revision;
- the one-sentence reason;
- failed claim and counterexample when present;
- GPT-5.6 model and live/replay status;
- number of required, passed, failed, and missing obligations;
- reproduction command.

The full report should separate:

### Model analysis

- claim decomposition;
- risks;
- chosen proof templates;
- critic findings;
- uncovered areas.

### Authoritative evidence

- approved verifier or probe specification;
- parameters after policy validation;
- exit status and metrics;
- expected versus observed values;
- log and result digests;
- receipt digests;
- aggregate policy reason codes.

### Audit metadata

- task, diff, catalog, plan, evidence, and decision digests;
- prompt and schema versions;
- cost, latency, and token usage when available;
- redaction and replay validation status.

## Live and replay modes

### Live

- Uses the optional OpenAI SDK dependency.
- Requires `OPENAI_API_KEY`.
- Defaults to `gpt-5.6`.
- Uses structured output.
- Has explicit timeouts and narrowly bounded retries for transient failures.
- Never logs credentials or unredacted sensitive values.

### Replay

- Requires no account, API key, or network.
- Binds the sanitized request digest to the recorded response.
- Uses the same parser, validator, policy, executors, and report generator as live mode.
- Fails if schema, prompt, catalog, or request digests do not match.

Replay is the primary judge path. Live mode demonstrates the real integration.

## Installation and supported platforms

Target support:

- Python 3.11 or newer.
- Linux, macOS, and Windows.
- Base Faber installation without the OpenAI SDK.
- Optional `openai` extra for live mode.
- Repository-scoped Codex skill under `.agents/skills/faber-proof/`.

The clean judge path should be no more than five documented commands from clone to
opening both reports.

## Success metrics

P0 product success means:

- bad patch ordinary tests pass;
- bad patch Faber Proof blocks with a concrete counterexample;
- fixed patch ordinary tests pass;
- fixed patch Faber Proof passes;
- live and replay plans validate through the same code path;
- no adversarial model response can define executable behavior or cause false `PASS`;
- a clean installation reproduces both reports;
- a judge understands the product within the first 30 seconds of the video.

## Non-goals before submission

- A universal theorem prover.
- Arbitrary model-generated test execution.
- Production-grade sandboxing claims.
- Real settlement or payments.
- A hosted marketplace.
- Model training.
- A production GitHub App.
- External autonomous work.
- Multiple unrelated demo repositories.

## P1 stretch only after P0 is green

A small **Faber Proof Arena** may compare two recorded Codex candidate patches against
the same proof contract and select the best accepted patch by evidence quality, cost,
and latency. It is valuable only when it adds a clear 10–15 second demo moment without
weakening installation, reliability, or the core proof narrative.
