# Revenue-validation sprint handoff

## Decision and next action

**Test a paid acceptance-evidence service before building a larger Faber product.**
The first buyer is a founder/CTO or engineering lead at a roughly 5–30 engineer B2B
software team already using coding agents and CI. The default job is dependency
upgrades in one Python backend service while preserving its API/CLI behavior.

Offer a **€250 diagnostic**, credited toward a **€1,000 two-week pilot**: one repo,
ten historical changes, an acceptance matrix, up to two owner-reviewed check
improvements, and an honest comparison with the team's current tools. First revenue
comes from that ordinary paid service, not a marketplace transaction. Three paid
pilots and two repeat purchases are the next evidence for repeatability.

Faber is currently **pre-revenue OSS/research with a plausible bootstrap experiment**.
Venture scale is unproven. Confidence is medium in this sequencing and low in demand;
the Python change family, prices, delivery hours and buyer access are hypotheses.
The [decision](2026-09-12-decision.md) and [offer](2026-09-12-first-revenue-plan.md)
contain the terms, economics and kill criteria.

**Verification-policy learning is unresolved and requires a specific experiment.**
Public histories provide useful, partially observed cases. They do not establish
that training beats a frontier model with the same context and retrieved history.
Use static policy, frontier context and frontier plus retrieval as baselines; train
a small check router only if the data and recurring errors justify it. Compare total
review effort and cost, retaining all owner requirements. Stop training if retrieval
matches it. Customer-owned policy memory can improve retention without weight updates;
it becomes a Faber data moat only with permitted reuse and measured economic advantage.
See [all twelve learning questions](2026-09-12-policy-learning.md) and
[the experimental protocol](2026-09-12-experiments.md).

The strongest changes to the prior view were:

- Current upstreams already have substantial, repository-specific verification
  knowledge. Omarchy's human/VM conventions matter even without checked-in CI;
  Hermes' old target issue is already fixed; nginx policy includes environment
  fidelity that a generic green-test summary misses.
- Qodo rules, Greptile runtime evidence and learning, and commercial predictive test
  selection make policy generation, execution and feedback insufficient standalone
  differentiation. Faber must win a specific customer's recurring acceptance job.
- Existing Proof records preserve rich context, but failures before publication and
  replaced bundles lose decision history. Small prospective capture is more justified
  than a new universal episode schema or premature training.

The top three unresolved questions are **payment**, **incremental value versus the
best existing workflow**, and **repeatable delivery/retention economics**, including
whether accumulated policy history improves future work cheaply enough to matter.

**Javier's exact next action:** select one reachable engineering lead with an active
Python dependency-upgrade queue and initiate the priced diagnostic offer. Agree on
lawful case access and payment through ordinary business operations. No outreach,
commercial commitment or private-data collection occurred in this sprint.

**Codex's exact next action:** once that owner supplies a permitted case, freeze its
decision-time context and owner constraints, run the existing static and frontier plus
retrieval baselines before seeing later outcomes, retain observations, then produce
one evidence-gap comparison. Do not resume the old marketplace, Hermes contribution
or Build Week queue automatically. Without buyer cases, the public histories support
data-reconstruction work, not a sales or blinded-performance claim.

## Branch, files and boundaries

Worktree: `C:/Users/javie/repos/Faber-revenue-sprint`.
Branch: `codex/revenue-validation-sprint`, based on
`96d6c7c4dd125a45e5c39e336d6a0515152428de`.
The final handoff commit identifies itself in Git; source and validation checkpoints
are recorded below to avoid a self-referential commit hash inside this file.

The durable deliverables are indexed in [strategy/README.md](README.md):
current-state reconciliation, seven commercial candidate profiles, ranked decision,
paid offer, learning analysis/schema audit, and experiments. The research folder has
current Hermes, Omarchy and bounded nginx inventories, historical incident/policy
simulations, source pins and a cross-repository synthesis. README, ROADMAP, MILESTONES,
OPEN_QUESTIONS and CODEX_SESSION_HANDOFF now point to this decision while retaining
the old material as history.

The original `C:/Users/javie/repos/Faber` checkout and its three Episode Envelope
planning edits remain separate. No merge to master, audited candidate modification,
audit ledger edit, upstream contribution, live provider call or customer contact is
part of this sprint. A2 remains independently not-green; local tests here cannot
retroactively clear its pending review or open P1/P2 findings.

Deliberately not built: a marketplace/payment path, general policy bootstrapper,
new universal trajectory envelope, hosted review platform, learned policy model,
capacity-routing product, production sandbox, or vertical connector. None resolves
the immediate payment/acceptance-value uncertainty more cheaply than this pilot.

## Implementation and validation checkpoint

Validated source HEAD: **`41adc10de40c057389ab6df099be4dfb41523051`**. The subsequent
handoff commit changes documentation only. Earlier coherent commits are `2b61006`
(state/decision) and `b0a27f8` (upstream/commercial/learning research).

The machine implementation is optional `--observations-dir` / Python
`observations_directory`, default off. It preserves the actual bounded, redacted
request and owner policy before planning; model/mode/dry-run metadata; planner result
or safe failure metadata; the existing workflow, per-check evidence, runs, receipts,
timings and decision; and separately bound, self-attested feedback. Repeated runs use
exclusive files in distinct directories, even when the normal proof output is reused.
No core schema, canonical proof digest, default report or acceptance rule changed.

Source/test/demo files: `src/faber/proof_observations.py`, `src/faber/proof_product.py`,
`src/faber/cli.py`, `tests/test_proof_observations.py` and
`scripts/proof_observation_demo.py`. [Usage, acceptance and limits](../PROOF_OBSERVATIONS.md)
and [schema audit](2026-09-12-policy-learning-schema-audit.md) explain the design.

Checks ran locally on HB2 with Python **3.12.14**, pytest **9.0.2**, Ruff **0.15.10**
and mypy **2.1.0**, in `.faber/sprint-venv`. Nix and `just` are unavailable on this
host, so `nix develop --command just check` could not run. The closest local checks
cover formatting, lint, typing, all tests and the smoke recipe:

| Command, using `.faber\sprint-venv\Scripts\python.exe` | Result |
|---|---|
| `-m pytest -q` | **744 passed, 2 skipped in 160.38 seconds**. |
| `-m ruff check .` | All checks passed. |
| `-m ruff format --check .` | 196 files already formatted. |
| `-m mypy src` | No issues in 94 source files. |
| `-m faber.cli doctor` | Package/Python/SQLite checks passed. |
| `-m faber.cli init-local-store --path .faber/revenue-smoke.sqlite3` | Store initialized. |
| `-m faber.cli emit-demo-trajectory --out .faber/revenue-smoke-trajectory.json` | Trajectory written. |
| `scripts/check_development_report_regeneration.py --check` | Exit 0; checked development reports reproduce. |
| `scripts/proof_observation_demo.py` | Exit 0; measured result below. |

For the three `-m faber.cli` commands, PowerShell used `$env:PYTHONPATH = 'src'`.
The two skipped tests are the deliberately guarded live-provider test and symlink
creation unavailable on HB2. Native Windows device-prefix/short-path alias regressions
passed. No live call was attempted. The pre-change baseline was 725 passed/1 guarded
skip; the new observation module independently passed 19 tests/1 symlink skip.

The final root demo took **7.662 seconds**, retained **95,362 bytes**, **3 runs** and
**9 events**, and made **0 provider calls**. It preserved the bad candidate's `BLOCK`
and repaired candidate's `PASS` workflows, the intentionally stale replay's
`replay_mismatch` failure and one separate feedback event. The current proof remained
the last valid `PASS` bundle. Output is local ignored state at
`.faber/observation-demo/run-49wcdk7r/summary.json`; the checked-in script reproduces
the assertions in a fresh directory. Runtime varies; this is not a performance claim.

`git diff --check` passed. Independent review found no remaining actionable P1/P2
findings in the added capture path. Documentation review checked source pins, counts,
links and inference-versus-measurement language; a final local check parsed all three
research JSON manifests and found no missing relative targets across 14 new research,
strategy and usage Markdown files. This is ordinary implementation review, not A2
clearance or evidence of production isolation.

**Experimental result boundary:** this sprint reconstructed public historical cases
and demonstrated prospective capture using `fake-development` replay fixtures. It did
not run a blinded frontier/context/retrieval comparison, train a router, replay the
three full upstream environments, or measure a customer's payment/productivity.

Remaining capture limits: raw partial runs before a workflow result exists and errors
before request construction are unavailable. Retrieval order/cutoff, rejected check
sets, active review minutes, later incidents and actual counterfactual outcomes must
be recorded when those mechanisms are introduced; they are not inferred here. Workflow
records retain existing environment/configuration references, not a complete source or
machine snapshot for standalone replay. Local timestamps and feedback are self-attested;
the archive is not authenticated or safe against hostile concurrent filesystem changes.
Collection grants no training/export rights and cannot waive owner-approved checks.
