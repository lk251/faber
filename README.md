# Faber Proof

**Evidence-bound acceptance for code produced by AI agents.**

Faber Proof is a research prototype built around one principle:

> The agent producing a patch should not control the standard used to accept it.

A second model does not solve that problem by itself. If it may invent arbitrary
commands or tests and then judge its own evidence, it can create a circular acceptance
process. Faber instead separates model judgment from execution authority.

The current prototype:

1. gives an optional model planner a task contract, a bounded redacted diff, and an
   owner-approved catalog of proof capabilities;
2. accepts only structured claims and selections from that catalog—the model cannot
   supply commands, imports, source code, arbitrary paths, or a verdict;
3. executes the selected bounded capabilities;
4. binds the resulting evidence to the task, candidate, diff, catalog, policy, and
   execution context; and
5. maps complete evidence to `PASS`, `BLOCK`, or `HUMAN_REVIEW` using
   deterministic policy.

This branch is a technical work sample in agent evaluation, evidence provenance,
adversarial testing, and acceptance boundaries. It is an alpha, not a production
service.

## Demonstration

The included scheduler case contains a boundary defect: a complete report produced on
the final permitted turn is discarded as `budget_exhausted`.

```text
                         FLAWED PATCH   NARROW REPAIR
Ordinary tests                PASS           PASS
Faber Proof                  BLOCK           PASS
```

For a two-turn budget and responses `["NOTE: premise", "FINAL: summary"]`, ordinary
tests accept both candidates. Faber's additional obligation exposes the concrete
counterexample and accepts the repair that moves the completed-report check ahead of
the exhaustion return.

## Run the no-key replay

Python 3.11+ and Git are required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
faber doctor
faber demo proof --mode replay --out-dir .faber/proof-demo
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\faber.exe doctor
.\.venv\Scripts\faber.exe demo proof --mode replay --out-dir .faber\proof-demo
```

The command writes self-contained evidence reports to:

```text
.faber/proof-demo/bad/report.html
.faber/proof-demo/repaired/report.html
```

The committed planner fixtures are deliberately marked `fake-development`. They
reproduce parsing, binding, execution, decision, and reporting without a key or network
call. They are not live model output and are not presented as evidence that a model
independently discovered the defect.

## Current evidence

At remediation candidate `b254458d705d801631be8207a0ddce75fbf68c21`:

- 725 tests passed; one guarded live-provider test was skipped;
- Ruff formatting and lint passed;
- mypy passed across 93 source files;
- the 49-case deterministic adversarial regression campaign passed;
- direct and clean-installed replay both reproduced ordinary `PASS/PASS` and Faber
  `BLOCK/PASS`;
- wheel, source distribution, artifact privacy scan, and byte-stable report
  regeneration passed.

The repository's Ubuntu and Windows workflow has produced
[green CI runs](https://github.com/lk251/faber/actions/runs/30440995635). That run
predates this exact remediation candidate; the application branch must pass fresh CI
before the two checkpoints are represented as one verified state.

These are project-run results, not an independent product certification. Four P0
authority and provenance findings discovered by an adversarial audit have remediation
candidates and targeted regression tests, but still await fresh independent
re-verification. The audit is therefore not green. See
[`codex/build-week/AUDIT_QUEUE.md`](codex/build-week/AUDIT_QUEUE.md) for the exact
findings, commits, and remaining P1/P2 issues.

## Trust boundary

Task text, repository content, diffs, model responses, and replay files are treated as
untrusted data. Repository-owner policy defines which capabilities may execute and
which evidence may determine acceptance.

A demonstrated contract failure takes precedence and produces `BLOCK`. Missing,
contradictory, stale, incomplete, or improperly bound evidence cannot produce `PASS`;
it is referred for human review.

The intended distinction is:

> Models may propose what to examine. They may not grant themselves verification
> authority.

## Explicit limitations

Faber Proof does not currently provide:

- a production sandbox—the local runner has no OS, VM, container, network, or
  descendant-process isolation;
- automatic policy bootstrapping or lifecycle management—the executable catalog is
  currently authored and approved by the repository owner;
- general program correctness or comprehensive vulnerability detection;
- independently reviewed live-model provenance for the committed demo;
- evidence of effectiveness across unfamiliar repositories;
- customers, revenue, production deployments, or pilot commitments.

The next research question is whether useful repository-owned policies can be
bootstrapped and evolved economically, and whether they outperform hardened CI plus an
independent verifier agent under matched budgets.

## Code map

- [`src/faber/proof_product.py`](src/faber/proof_product.py) — local end-to-end
  workflow and atomic evidence bundles
- [`src/faber/proofs.py`](src/faber/proofs.py) — proof records and deterministic
  decision policy
- [`src/faber/proof_catalog.py`](src/faber/proof_catalog.py) — approved bounded
  capabilities
- [`src/faber/proof_executors.py`](src/faber/proof_executors.py) — fixed execution
  families
- [`src/faber/adapters/openai/`](src/faber/adapters/openai/) — optional live and
  replay planner adapters
- [`src/faber/proof_reports.py`](src/faber/proof_reports.py) — Markdown and
  self-contained HTML reports
- [`docs/FABER_PROOF_THREAT_MODEL.md`](docs/FABER_PROOF_THREAT_MODEL.md) — trust
  boundaries, residual risks, and non-claims
- [`docs/NAMING.md`](docs/NAMING.md) — broader experimental product vocabulary
- [`docs/BUILD_WEEK_SUBMISSION_README.md`](docs/BUILD_WEEK_SUBMISSION_README.md) —
  archived competition landing page
- [`docs/generated/BUILD_WEEK_EVAL_RESULTS.md`](docs/generated/BUILD_WEEK_EVAL_RESULTS.md)
  — adversarial regression cases and reproduction commands

## Development method

Faber was developed with coding agents. Javier Mares defined the product boundary,
acceptance-authority model, falsification criteria, and human gates, then used separate
implementation and adversarial-review passes to expose failures and develop candidate
remediations. The audit history is retained because the failures—and the decision not
to call remediated code independently verified before re-review—are part of the
engineering evidence.
