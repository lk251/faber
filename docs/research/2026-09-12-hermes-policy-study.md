# Hermes Agent: cold-start verification-policy study

Research date: **12 September 2026, UTC**. This is a public-source, read-only study,
not an upstream audit, an executed Hermes test campaign, or evidence of customer
demand. No upstream code, installer, test, or workflow was executed. No maintainer
was contacted. Public Git and GitHub API retrieval succeeded; the branch-protection
endpoint returned HTTP 404, so protection settings are **unknown**, not absent.

The current-source snapshot is upstream `main` at
[`284d220ba48e25f2e3623b3afe72db8f24a4c2db`](https://github.com/NousResearch/hermes-agent/commit/284d220ba48e25f2e3623b3afe72db8f24a4c2db),
committed 12 September 2026 at 02:58:07 UTC. Every current-source link below is pinned
to that revision. The separately retrieved latest release was
[`v2026.9.11`, Hermes 0.21.2](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11),
published 11 September at 19:20:31 UTC. These upstream dates are distinct from the
research date. The corresponding main-branch
[CI run](https://github.com/NousResearch/hermes-agent/actions/runs/34669093407)
reported success. That is an observed GitHub result, not a local reproduction and
not evidence that disabled or separately triggered checks ran.

## Decision this case supports

**Discovering tests and writing a policy draft is not a persuasive standalone product
for this repository.** Hermes already maintains a considerable policy layer in its
workflows, change classifier, isolated runners, contribution guide, and area-specific
agent instructions. A strong coding agent that actually follows those sources starts
far above “run pytest and hope.” The useful remaining hypothesis is narrower:
**maintain a reviewable account of what was required, what actually ran, what is
missing, and which repository-approved incident rules apply to this exact change.**
Whether that saves more reviewer time than it costs remains unmeasured.

Five concrete opportunities are visible without inventing new verifiers: distinguish
disabled Desktop E2E from passing CI; distinguish scheduled installer checks from
pre-merge evidence; distinguish advisory vulnerability/type diagnostics from blocking
checks; detect stale/mismatched platform selection; and preserve an incident's negative
controls instead of reducing it to “the reported happy path passes.” Most of these
could also be implemented as modest improvements to existing Hermes CI. Faber must
beat that alternative on ongoing effort, not merely produce another report.

## 1. Current verification assets

The tracked tree contains **35 workflow files**, **4,048 pytest-style `test*.py`
files under `tests/`**, and **12 `AGENTS.md` files**. These are static file counts,
not collected or executed test counts. No tracked `CODEOWNERS` file was found by
`git ls-files '*CODEOWNERS*'`. The complete workflow inventory and selected source
hashes are in [the source manifest](2026-09-12-hermes-policy-sources.json).

| Asset | Observed mechanism and actual boundary |
|---|---|
| CI orchestration | [`ci.yaml`][ci] calls reusable workflows according to [`scripts/ci/classify_changes.py`][classifier]. Unknown paths, empty diffs, and `.github/` changes conservatively enable lanes; main pushes enable all classifier lanes. The final aggregate rejects dependencies whose result is literally `failure`; it accepts skipped jobs and does not itself reject `cancelled`. This is a static observation of the aggregate, not proof of an exploitable bypass of GitHub branch protection. |
| Python tests | [`tests.yml`][tests-workflow] runs Python 3.11 on an Ubuntu 96-core runner with uv 0.9.28, `uv sync --locked`, `all`/`dev` and the additional lazy SDK extras exercised by tests. The main suite uses [`scripts/run_tests.sh`][runner] and a bounded per-file subprocess runner. Integration, E2E, and Docker directories are excluded from that discovery; a separate Linux job runs `python -m pytest tests/e2e/ -v --tb=short`. |
| Test isolation | [`tests/conftest.py`][conftest] redirects Hermes state, removes credentials, disables lazy installs, and guards writes to live state. The wrapper establishes UTC/UTF-8 and a temporary Hermes home. Per-file failures may retry once in a fresh process: retry-pass is green with a flake notice. This is deliberate noise management, not evidence the first failure never occurred. [`AGENTS.md`][agents] describes the contract. |
| Native OS tests | [`tests-os.yml`][os-tests] selects `macos_only` on macOS and `windows_only` on a Windows 32-core runner, both Python 3.11. A helper narrows imported files, then pytest markers select tests; zero matches fail. Linux-only tests live in the main suite. The supported Python range is 3.11–3.13, but the normal test lanes are not a full Python-version matrix. |
| Lint/type checking | [`lint.yml`][lint] has blocking `ruff check .`, Windows-footgun checks and plugin-compat-pointer checks. Current Ruff rules are `PLW1514`, `ASYNC210`, `ASYNC220`, `ASYNC221`, `ASYNC251`, with documented exclusions and a legacy ratchet. Ruff/`ty` diagnostic diffs and public-surface removals are advisory; a clean aggregate is not “the repository is fully type checked.” Lint tools are installed without exact versions in this workflow despite dev-extra pins. |
| JS/TS | [`js-tests.yml`][js-tests] uses Node 26/npm 12, root `npm ci` on a cache miss, and `.github/scripts/run-workspace-checks.mjs` to discover workspace checks, including split `check:*` scripts. These cover the relevant TypeScript/lint/Vitest checks. Empty discovery fails. This is considerably stronger than searching for one root test script. |
| Desktop E2E | [`e2e-desktop.yml`][desktop-e2e] contains Linux Playwright/Electron execution and screenshot/report artifacts. **Its orchestrator call is `if: false`**, with a September flakiness explanation. Presence of the workflow or Playwright tests does not imply current PR coverage. A previous disabling expression also caused workflow parsing failure, according to the adjacent maintainer comment. |
| Windows installer | [`installer-tests.yml`][installer-tests] runs long-path and Node-compatibility scripts on Windows in both PowerShell 7 and Windows PowerShell. [`windows-venv-e2e.yml`][windows-live] runs real process-topology tests only on `wine2e/**` branch pushes; it is not a normal PR/main gate. |
| Install/update matrix | [`install-e2e.yml`][install-e2e] runs twice daily, on release-tag pushes, and by manual dispatch. Linux, Windows, and macOS reusable drivers cover declared install/update routes across sampled release tags. Drivers explicitly skip unsupported method/version combinations. This is post-change operational coverage, not universally a pre-release or PR blocker. |
| Rust | [`rust-tests.yml`][rust-tests] runs `cargo test --lib` for the Tauri bootstrap installer on Ubuntu with system libraries. The workflow explicitly records that this crate's lockfile is ignored and `--locked` cannot be used; dependencies re-resolve. Unix process fixtures require Linux. This is not Windows GUI installer equivalence or a reproducibly locked Rust supply chain. |
| Python/package reproducibility | [`pyproject.toml`][pyproject] and `uv.lock` describe bounded/exact dependencies, extras, platform markers, a build backend, package data, resolution overrides and age exceptions. [`uv-lockfile-check.yml`][uv-check] checks consistency. Some current dependencies use bounded ranges, notwithstanding older exact-pin prose. Locked dependency resolution does not imply deterministic external service behavior, complete wheel contents, or identical packaging on all supported hosts. |
| Nix | [`flake.nix`][flake] declares x86_64-linux, aarch64-linux, aarch64-darwin and locked inputs. [`nix/checks.nix`][nix-checks] evaluates actual NixOS/Home Manager modules and checks package/config/service behavior. Build checks are Linux-only where dependency wheels limit Darwin; cross-system evaluation is a weaker separate guarantee. [`nix.yml`][nix-workflow] is a separate path-classified PR/main workflow, outside the CI aggregate. |
| Docker | [`docker.yml`][docker] separately builds native Linux amd64/arm64 images, exercises Docker integration tests, and gates publishing behind those builds and a protected publish job. It runs on PR/main/release events according to the source, despite stale comments elsewhere saying no PR builds. It is excluded from the normal CI aggregate. [`docker-lint.yml`][docker-lint] uses Hadolint and ShellCheck, with limited selected severity. |
| Security/static analysis | [`supply-chain-audit.yml`][supply] looks for a narrow set of install/import-time attack patterns and dependency bounds; critical findings require maintainer review. [`osv-scanner.yml`][osv] checks five Python/npm lockfiles, on CI and weekly; `fail-on-vuln: false` makes known vulnerabilities advisory. Weekly Dependabot configuration covers GitHub Actions only; comments describe separate security-update settings that were not independently inspected. No current dedicated CodeQL-analysis workflow was found; SARIF upload is not itself CodeQL source analysis. |
| Catalog admission | [`plugin-catalog-ci.yml`][catalog] validates schema and fetches a plugin at its stated commit for `hermes plugins validate`. It is a separate path-filtered PR workflow. Pinning a plugin identifies the content under review; it does not prove that content safe. MCP catalog changes also request the `ci-reviewed` label. |
| Review conventions | [`CONTRIBUTING.md`][contributing], [`AGENTS.md`][agents], the [PR template][pr-template], and area guides require reproduction against current main, behavioral regression tests, real-path evidence for boundary/config/I/O work, platform reporting, scope discipline, and preserving author credit. The template still names bare pytest while root agent instructions insist on the wrapper: an onboarding tool must surface this conflict, not silently choose the easiest command. |
| Maintainer review | [`review-labels.yml`][review-labels] requires the current `ci-reviewed` label for CI-sensitive changes, MCP catalog changes, and specified critical findings. The workflow reads label presence; it does not establish that a review is cryptographically bound to a particular diff. Actual reviewer requirements, label permissions and branch/ruleset enforcement were not established. |
| Release | [`scripts/release.py`][release-script] creates changelog/version/tag/GitHub release artifacts when explicitly published. Inspection of the publish path did not establish a mandatory whole-suite gate inside that script. Docker and installer checks react to release events; this is not evidence they were release prerequisites. Public releases and their reported validation are distinct from machine-enforced release policy. |
| Agent-specific acceptance | Area instructions, verification-on-stop/pre-verify hooks, tests of the real agent loop, and `evals/` fixtures exist. These cover selected behavior and prompt/tool integration. They do not establish calibrated reliability of every model/provider/configuration or authorization to execute arbitrary generated verifier code. |

The remaining workflows are not silently counted as tests. `history-check.yml` rejects
unrelated Git histories; `contributor-check.yml` checks attribution;
`case-collision-check.yml` and `profile-artifact-check.yml` guard filenames and accidental
profile archives; `infographic-check.yml` detects committed image artifacts (its job is
not listed in the aggregate's `needs`); `lockfile-diff.yml` summarizes npm changes.
`docs-site-checks.yml` generates skill docs and checks diagrams/builds.
`skills-index.yml`, `skills-index-freshness.yml`, and `deploy-site.yml` build, monitor,
and deploy documentation/indexes. `js-autofix.yml`, `label-rerun.yml`,
`ci-review-comment.yml`, and `publish-e2e-evidence.yml` modify/report workflow output
or assist review. Their existence is not additional behavioral coverage. See the
[pinned workflow directory][workflows] and machine-readable manifest for every file.

Manual knowledge is unusually explicit: prompt-cache stability, role alternation,
profile-specific state and authorization, supported host semantics, compatibility
names used by third-party plugins, packaging extras, and where CI selection can
silently miss a test are documented. Root and area `AGENTS.md` files are valuable
evidence of intent, but conflicting/stale statements remain possible. One example is
the Rust workflow's documented unlocked installer dependencies beside a broad pinning
policy. Another is `CONTRIBUTING.md`'s pytest alternative versus the stronger wrapper
requirement in the agent guide. Both are review questions, not grounds for an LLM to
invent a new owner policy. [Sources: agent guide][agents], [contributing guide][contributing],
[classifier][classifier], [Rust workflow][rust-tests].

## 2. What cold onboarding can actually infer

| Input | Safe draft inference | Important limit |
|---|---|---|
| Directory structure/build metadata | Languages, components, package targets, lockfiles, Python range, candidate test roots | A dependency-free pure helper and a credential router can share one folder. Structure does not give risk tolerance. |
| Workflow graph | Entry triggers, reusable calls, runner OS, literal disabled calls, matrix definitions, conditions, advisory flags, declared aggregate dependencies | Dynamic expressions, external actions and shell-generated matrices need bounded interpretation. A static file cannot establish actual GitHub protection or executed coverage. |
| Test configuration and fixtures | Excluded integration markers, per-file isolation, environment controls, native-host markers, empty-selection handling | A test name or imported function is not proof of an assertion's adequacy; mocks and autouse fixtures can remove the behavior of interest. |
| Contribution and agent guides | Draft rules for invariants, red-on-base proof, real paths, profiles, platforms, cache/alternation behavior | They contain intent, exceptions, duplication and obsolete examples. Ownership still must approve which version becomes binding. |
| History/issues/PRs | Candidate incident clusters, specific failing input/output relationships, previous rejected approaches, durable negative controls | Popularity, severity labels and convincing prose are untrusted claims. A merged fix is stronger evidence than an open allegation, but still needs reproduction. |
| Ownership | Area routing docs and maintainers visible in historical decisions | No CODEOWNERS was found. Commit frequency cannot safely appoint an owner or identify a buyer. |
| Dependency graph | Direct extras, imports, workflow consumers, platform markers, likely affected package checks | Hermes uses lazy imports, registry discovery and plugins; a Python AST graph alone misses runtime resolution and external consumers. |
| Previous failures | Propose a targeted regression rule with source/incident provenance | Learning “always deliver any non-empty output” from one lost report would reintroduce false success on unrelated errors. |

A credible first draft can mechanically inventory much of **existing** policy in
hours. It cannot mechanically fill all coverage gaps, declare authoritative checks,
or promise bug detection. “Percent of policy automated” is not a meaningful number
without a denominator: discovering 35 workflow files says little about authoring one
missing real gateway/cron/agent invariant.

## 3. Initial policy Faber should propose

This is an **unapproved proposal**, not permission to run fetched commands. Import
workflow commands as quoted evidence; a repository owner must approve registered
verifier capabilities and their execution environment. Resolve source freshness and
the exact base/head first. An issue that is already fixed is not a new pilot task.

### Common evidence contract

For every required check, record the repository identity, immutable base/head Git
objects, policy revision/digest, approved verifier identifier and source digest,
runner OS/architecture and Python/Node/tool versions, dependency-lock digests,
selected test identities or selector, collected/executed/skipped counts, timestamps,
exit status, raw-output digest and relevant counterexample. Capture initial failure
and retry separately. For regression work, bind the same test/harness to a failing
base and passing candidate, with negative controls. External-service simulations,
real calls and skipped calls must be distinguishable.

Missing, cancelled, unsupported, stale or unbound evidence yields **INCOMPLETE /
HUMAN_REVIEW**, not PASS. Unrelated legitimately skipped jobs remain skipped with a
policy reason. A vulnerability exception or flaky-check exception needs an owner,
reason, scope and expiry. Do not automatically override the repository's deliberate
advisory choices: ask the owner to choose which risks the proposed policy should gate.

### Task/risk classes

| Class and trigger | Mandatory proposed checks | Escalation / human boundary |
|---|---|---|
| P0: prose and non-executable docs | Changed-link/schema/doc build checks indicated by the current classifier; generated skills/index consistency where applicable | Skills are executable/instructional content and are not automatically P0. Documentation about trust, configuration or release semantics requires domain review. |
| P1: bounded pure behavior | Wrapper-run affected behavioral tests, base-red/candidate-green regression, configured Ruff/compatibility checks, relevant JS workspace checks; normal CI lanes required by the approved policy | Broaden to full suite for shared utilities; if dependencies or dynamic consumers cannot be bounded, classify upward. Avoid snapshot/count tests. |
| P2: agent/gateway/cron state transitions | P1 plus real-loop or real-router tests using temporary state and controlled provider responses; producer-to-consumer outcome contract; timeout, interruption, empty response, retry and failure controls | Agent output acceptance, partial-result delivery and Kanban accounting require maintainer-approved semantics. No live accounts necessary for deterministic response fixtures. |
| P3: authentication, profiles, tools, plugin installation or external surfaces | P2 plus cross-profile/unauthorized caller negative tests; approval-context propagation where applicable; environment/secret-scoping fixtures; plugin/source pin review; relevant scanner output | Security maintainer decides trust-boundary claims. Default-local execution is not containment. Real deployment isolation tests require an approved whole-process sandbox harness. |
| P4: OS/process/filesystem behavior | Affected native Linux/macOS/Windows tests and marker-selection evidence, live-process fixture for topology, filesystem semantics on the target host | Linux with a patched `sys.platform` is insufficient. Windows updater/venv work requires its live lane or equivalent approved harness. Missing host evidence remains visible. |
| P5: install, packaging, dependencies, release | Lock consistency, installed-wheel/package-data smoke, relevant Nix/Docker checks, relevant real install/update route from prior release, dependency/security diff | Release owner defines supported routes and exceptions; unlocked Rust resolution is an explicit unresolved input. Signed release publication and credentials remain outside automatic inference. |
| P6: verification infrastructure or policy | Existing tests plus classifier/selector negative tests, zero-tests guards, workflow graph/permissions review, explicit policy-diff approval | Changes that suppress tests, broaden exceptions, alter fixtures or replace verifier sources require review independent of the candidate's own claimed success. |

Baseline environment proposals reproduce the current locked Python 3.11 Linux suite,
not an invented all-version matrix. Python 3.12/3.13 become escalations for interpreter
compatibility or packaging work. Native Windows/macOS runners are mandatory for
host-specific behavior; Nix/Linux builders, Docker architectures, Node/npm and Tauri
libraries are selected only for relevant classes. Tests use a temporary home and
controlled responses; live provider behavior requires explicitly scoped credentials,
cost and data handling that cannot be inferred from public source.

For this repository, a good first artifact is a **small policy delta over its current
CI**, not a parallel replacement. For example: “this change touches Desktop behavior;
the normal Playwright call is disabled; provide these two reviewed interaction probes
or accept this named gap.” A permanent generic requirement to run every imaginable
check would erase the upstream classifier's cost savings and likely be rejected.

## 4. Who or what must supply each part

| Mechanical extraction | LLM/reasoning proposal | Maintainer input | Bespoke implementation | Cannot safely infer |
|---|---|---|---|---|
| Paths, commit/blob identities, workflow triggers, literal conditions, tool versions, markers, locks, selected source hashes | Reconcile contradictory docs; trace producer/consumer contracts; suggest sibling negative controls; map incident reports to likely impacted components | Whether report delivery counts as successful execution; acceptable risk and flake budget; supported platform/routes; authority and reviewer identity; exception expiry | Actual loop/router/provider fixture; OS process-tree probe; artifact parser; wheel-install smoke; profile isolation and database lifecycle harness | Authority from candidate text; safe execution from a workflow's presence; secrets permission; “all code paths covered”; containment from approval heuristics; buyer interest from OSS activity |

Use confidence on individual assertions and retain unresolved questions. In particular,
[Hermes's security policy][security] treats OS-level isolation as its containment
boundary and explicitly treats in-process approval/redaction/scanning as heuristics.
Its network surfaces still have authorization requirements. Faber must preserve that
distinction rather than declaring every heuristic bypass an isolation vulnerability,
or weakening network authorization because the local agent is single-tenant.

## 5. Historical simulation: verification itself loses a composed report

### Source receipt and chronology

- [Issue #61631][incident], opened **9 July 2026 at 20:11:20 UTC**, reported Hermes
  0.17.0 on macOS/Python 3.11.7, checkout prefix `60b1f6c`. The reporter described a
  composed report lost when verify-on-stop exhausted the remaining budget. The
  prefix resolves to **`60b1f6ce3f26c57dac480265fbf4a38e7a5c3a25`**, committed
  **1 July 2026 at 18:45:16 UTC**. This is a pre-disclosure source snapshot;
  it is distinct from the later candidate base used below.
- Earlier proposed PRs [#61636](https://github.com/NousResearch/hermes-agent/pull/61636)
  and [#61721](https://github.com/NousResearch/hermes-agent/pull/61721) preceded the
  final [#61900][fix-pr]. Its fetched GitHub PR base was
  **`f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a`** and head was
  **`6fa9465ce34c5e5db54fe8b34544fd79f797f423`**.
- #61900 merged **10 July 2026 at 06:23:59 UTC**, merge commit
  **`6abf1956829d93c487e18eb3051c395b111d3d39`**. The issue closed one second later;
  a [maintainer comment][closure] explicitly credits that fix and follow-up hardening.
- These Git objects were fetched and their code/tests inspected. **The old Faber
  pilot target is stale.** Do not solicit a new fix for #61631 or treat it as open
  demand. The current tree still has descendant regression files, with later changes;
  July's expected message sequence must not be blindly replayed as September policy.

### Policy before the final fix, and the pre-incident limit

At the exact candidate base, the [agent guide][old-agents] already required the
Hermes wrapper, behavioral invariants and real-path validation. It used an earlier
xdist/isolation arrangement, not September's runner. The historical CI entry file
was `.github/workflows/ci.yml`, not today's `ci.yaml`. That base was committed on
10 July at 04:32:01 UTC, **after the issue was disclosed**. It is appropriate for
base-red/candidate-green comparison, not a leakage-free pre-incident training input.
The reporter's 1 July source can be used for the latter; its finalizer already has
the normal budget-summary normalization, inspected here from the pinned Git object.

The [scheduler][old-scheduler] allowed a non-empty summary with
`completed=False` only when the agent reported the recognized maximum-iteration
reason and had not failed. An existing [scheduler regression][old-scheduler-tests]
covered that summarized-output shape. A sensible pre-incident policy would have
required scheduler/finalizer tests and preservation of error behavior. **The missing
assertion was the composition of the real verification continuation, finalizer and
scheduler**, not a total absence of tests or acceptance rules.

### Observed failure and available evidence

The issue's macOS scenario left a final report pending while verification consumed
the last turn. Its proposed explanation was a mismatch between loop and scheduler
exit reasons. That explanation was incomplete: normal finalization rewrites the
reason before delivery, and the exceptional verification path matters. The report includes a
confirmed workaround (disable verification-on-stop and raise the turn budget), but
that is a reporter observation, not a benchmark reproduced here. [Issue source][incident].

The [before/after production diff][fix-diff] fixes the producer/finalizer contract:
it explicitly remembers a response held by a verification gate, clears ordinary final
response state on continuation, and only uses the held response for eligible budget
exhaustion. It excludes interrupted/failed/unrelated exit paths, preserves timeout
accounting, and keeps an intermediate acknowledgment from masquerading as a report.
The scheduler was not changed in that final PR. This is more careful than merely
accepting `unknown` or delivering any non-empty text.

### Proposed learned policy update

For changes to verification continuation, iteration budgets, finalization, cron
delivery or Kanban completion, propose a repository-approved **outcome-provenance
contract** with the following probes:

1. At one remaining iteration, `verify_on_stop` and `pre_verify` each retain the
   composed answer, make no replacement-summary model call, and produce a recognized
   delivery outcome. Test through the real loop with a fake provider response.
2. API failure, guardrail halt, interruption/recovery, and unrelated non-empty error
   text must remain failures; “has text” does not establish successful completion.
3. Empty pending output follows the intended summary path; a later verified answer
   supersedes the older held response; a promise to do work is not a completed report.
4. Deliverability and task completion are separate: exhausted Kanban work remains
   timed out and advances the failure circuit. Record both outcomes in evidence.
5. Prove the two verification assignments matter with a targeted mutation or removal
   check, then run the same regression against the exact base and candidate.

The historical [real-loop regression][fix-loop-tests] and
[finalizer regressions][fix-finalizer-tests] provide concrete harness patterns. The
merged PR reports 98 passing targeted tests, real-loop/cron and Kanban exercises,
mutation checks, clean Ruff/diff checks, and unchanged type diagnostics with a
pre-existing analyzer failure. **Those are upstream-reported validation results;
this study did not execute them.** [PR validation source][fix-pr].

### Could Faber have learned this automatically?

After disclosure, extracting the contract, candidate tests and negative controls
from the merged diff is realistic. Porting them to a newer code layout and proving
meaningful failure on the base still requires implementation and execution. Choosing
whether a budget-exhausted report should be delivered is a product decision; the
maintainer's accepted implementation supplies the authority, not an LLM inference.

Before disclosure, a strong agent could trace the same finalizer/scheduler contract
and propose the same boundary test. Faber has not demonstrated that it would find
this incident more often or cheaply. Both July and September documentation already
ask contributors for invariant and real-path testing. A history-informed retrospective
is **not** evidence of prospective bug-finding lift. This incident favors evidence
preservation and policy maintenance more than an automatic test-authoring moat.

### Learning appendix: two decisions, one correlated incident

The source manifest contains two **reconstructed diagnostic rows**, grouped under
one incident so they cannot leak across train/test splits. They are observations
of upstream work, not Faber decisions. A Git commit timestamp is not a historical
receipt proving when the reviewer or model could access it. Public-source
availability at each proposed cutoff and a complete contemporaneous review input
bundle remain missing; `training_eligible` is therefore false.

| Row | Inputs before the observed decision | Decision and later feedback | Label quality / absent counterfactual |
|---|---|---|---|
| `hermes-61636-review` | Issue opened 9 July 20:11Z; proposed scheduler-only broadening plus mocked tests. Fetched PR base `8e3f9537db21b49ebe796f7b5a6ff489028fe1fb` was committed 21:40:09Z; final head `cc1af0c2d8ec90c1ca2d876df02c2ea999a052dd` 22:45:30Z. Proposed decision cutoff 23:42:03Z, one second before the public review. September source and successor fixes are excluded from input. | [Maintainer review](https://github.com/NousResearch/hermes-agent/pull/61636#issuecomment-4930549778) at 23:42:04Z rejects the premise because the proposal stops before finalizer normalization; it also identifies the risk of accepting generic `unknown` exits. PR closes unmerged at 23:42:05Z. Later #61900 establishes that a narrower underlying bug still needed repair. | Strong label for **this maintainer rejecting this patch/rationale**, not “the original user had no bug.” The mocked success tests do not show the patched branch is reached from the real loop. No independently executed regression, comparison with alternative reviewer, or downstream correctness outcome was collected. |
| `hermes-61900-review` | Accepted candidate base `f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a`, candidate head `6fa9465ce34c5e5db54fe8b34544fd79f797f423` committed 10 July 06:11:43Z, issue and earlier rejection already available in chronology. Proposed cutoff 06:23:58Z. Candidate adds explicit verification-response provenance and real-loop/finalizer probes. | PR merges at 06:23:59Z to `6abf1956829d93c487e18eb3051c395b111d3d39`; issue closes. PR description reports targeted, real-loop, error-control, Kanban and mutation results. | Strong label for **acceptance/closure**, weaker self-reported label for checks passing; neither establishes universal correctness or absence of later regression. Historical PR-body revision timing is not established, so the current validation prose belongs in later feedback, not guaranteed cutoff input. Cost, reviewer minutes, avoided incidents and Faber-versus-baseline outcome are unknown. |

Observable pre-decision features could include touched component graph, diff scope,
new success-condition predicates, mocked versus real producer calls, missing negative
controls, and whether a claimed runtime branch is actually reachable. This is a
plausible ranking/retrieval target: “require a real producer-to-consumer probe before
accepting a delivery-state fix.” It is not a license to learn the maintainer's wording
as ground truth or to infer hidden reasoning. Preserve only explicit comments,
public artifacts and decisions.

Within Hermes, retrieval of this incident when a later patch touches finalization,
cron delivery or verification hooks is immediately plausible. Across repositories,
the transferable concept is separating **deliverable output, successful completion,
and error provenance**; the exact exit strings, paths, tools and acceptable fallback
are repository-specific. Training a model to always recognize `unknown` as bad would
be brittle and could contradict another owner's contract.

**Could training beat inference-time retrieval? Unresolved.** First compare a frontier
coding/review model with the same current policy, retrieved incidents, candidate diff
and approved check catalog against any learned selector. Freeze retrieval at each
episode's cutoff; hold out whole incidents, later time windows and repositories.
Measure chosen checks' incremental defect coverage at equal compute/latency and
reviewer cost, including unnecessary escalation. Only train after enough repeated,
well-labeled decisions expose stable error patterns that retrieval plus prompting
does not solve cheaply. Two hindsight-reconstructed, correlated PRs cannot establish
that. A small repository-owned case library and explicit policy updates are the
appropriate first learning mechanism.

## 6. Human burden and operating cost

These are engineering estimates for one bounded subsystem and one technically capable
maintainer, not measured billable work or promised onboarding times. A working upstream
checkout/CI is assumed. Runtime cost, new cloud runners and real service accounts are
separate.

| Work | Plausible range | What drives the range |
|---|---|---|
| Mechanical inventory and initial policy draft | 2–6 engineer hours | 35 workflows, reusable graphs and shell-defined selection exceed a one-file pytest repository. A reusable extractor could reduce repeat cost. |
| Maintainer review of a bounded cron/agent policy | 1–3 hours, often over several exchanges | Resolve delivery vs completion semantics, authority, supported env and which checks are mandatory. |
| First integrated pilot including reusable receipt binding | 2–5 engineer days | Reuse existing CI/test artifacts; validate trust boundary, reruns, missing evidence and base/head identity. This is more than writing the draft. |
| Existing incident regression adaptation | Half a day–2 days | Existing harnesses and an accepted upstream fix reduce uncertainty; current decomposition and isolation changes still need work. |
| New real OS, installer or profile-isolation harness | 2–10 engineer days per missing surface | Real process/filesystem behavior, host access, reproducibility and flake control dominate; a text policy cannot substitute. |
| Ongoing bounded-policy review | 1–4 maintainer hours/week during active changes | Only plausible with automatic source/selector drift detection. A quiet subsystem may need less; cross-repository policy covering all Hermes surfaces could require a dedicated engineer. |
| Incident-driven update | 1–4 reviewer hours plus any harness implementation | Validate the causal explanation and exception scope; avoid accumulating duplicate tests and permanent expensive checks. |

The initial maintainer questions are specific: who approves a policy revision;
which exact checks/rulesets currently block merge; which real OS/install routes are
supported; what counts as delivery versus completion; which disabled/advisory/flaky
checks have accepted exceptions; and what evidence must stay private? These questions
cannot be answered by counting stars or parsing a workflow. They are a reason to
limit a paid pilot to one acceptance bottleneck rather than promise full onboarding.

## 7. Strong-agent-plus-CI baseline and falsification

| Work | Strong agent following upstream guidance | Incremental Faber hypothesis |
|---|---|---|
| Find/run appropriate existing tests | Already learns wrapper, isolation, native markers, path classification, locked extras and affected suites | A reusable inventory saves discovery time; easy to copy and probably small value alone. |
| Draft a new boundary regression | Can trace real loop, read history and implement the same regression | No measured reasoning advantage. Catalog-approved recurring contracts may reduce repetition after the first authoring effort. |
| Recognize missing coverage | Can read `if: false`, advisory settings, unavailable host and skipped tests | A maintained policy can keep these facts visible on every PR and record explicit exceptions. This is a workflow benefit to measure. |
| Relate a result to the change | GitHub CI already associates runs with commits, and reviewers inspect workflow changes | Faber can additionally bind owner policy, verifier source, lock/environment and base-red/head-green evidence. It must show that existing GitHub checks/artifacts cannot do this adequately with a small extension. |
| Learn from incidents | Maintainers already add tests, docs, footgun checks and classifier fixes | A persistent rule can route future relevant work and expire stale assumptions. Poorly managed, it just becomes another noisy policy backlog. |
| Accept/merge work | Maintainers retain intent and exception decisions | Deterministic missing-evidence decisions may reduce repeated review. Automatic acceptance would be unjustified where human semantics or coverage remain unresolved. |

**Falsification result:** this case rejects the premise that a sophisticated
agent-heavy OSS repository has no repository-owned verification policy, and provides
no evidence it would pay for a generic bootstrapper. It leaves open a narrower
commercial hypothesis: a team with recurring cross-component incidents and reviewer
overload may pay to keep existing acceptance evidence complete and fresh. Hermes is
a useful public test corpus, not an assumed customer. It also explicitly asks
third-party product integrations to ship as standalone plugins, so an in-core Faber
integration would conflict with current contribution policy. [Placement source][contributing].

### Reusable implementation experiment

Build or evaluate a **read-only coverage and authority inventory** that never executes
upstream commands. Its output should distinguish declared checks, reachable checks,
selection uncertainty, mandatory/advisory status, environment gaps, provenance and
unanswered ownership questions. Hermes supplies concrete acceptance fixtures:

- Discover `ci.yaml` and its reusable graph; report Desktop E2E as disabled.
- Report `OSV fail-on-vuln: false`, advisory `ty` and retry-green separately from
  blocking tests, without treating them as accidental defects.
- Report Nix/Docker/catalog workflows as separate from the aggregate and installer
  E2E as scheduled/tag/dispatch coverage. Do not claim all release gates are known.
- Report supported Python range versus executed CI Python version, native-host
  marker selection and the unlocked Rust crate.
- Preserve “actual protection settings unavailable” after the 404; never promote
  a workflow comment saying a check should be required into a fact that it is.
- Detect source drift with pinned hashes and keep #61631 classified as fixed.

Test the product hypothesis with a blinded, equal-budget comparison against a strong
agent given the **same pinned repository, docs, issue context and execution budget**.
Use prospective held-out changes or pre-incident snapshots; do not give only Faber
the known patch/tests. Score actionable omissions, false alarms, reviewer minutes,
required new harness effort and retained evidence after a revision/rerun. Suggested
pilot kill criteria: stop generic productization if fewer than two of five real
reviewers accept the artifact into their workflow, if it saves less than roughly an
hour per reviewer per week, or if maintenance consumes the claimed savings. These
are proposed decision thresholds, not achieved outcomes.

For a machine-only sprint, the inventory's correct classification can be tested now;
revenue or independent reviewer benefit cannot. Do not implement Hermes-specific
execution adapters merely to make a demonstration look integrated before this
adoption and value test.

[ci]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/ci.yaml
[classifier]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/scripts/ci/classify_changes.py
[tests-workflow]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/tests.yml
[runner]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/scripts/run_tests.sh
[conftest]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/tests/conftest.py
[agents]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/AGENTS.md
[os-tests]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/tests-os.yml
[lint]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/lint.yml
[js-tests]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/js-tests.yml
[desktop-e2e]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/e2e-desktop.yml
[installer-tests]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/installer-tests.yml
[windows-live]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/windows-venv-e2e.yml
[install-e2e]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/install-e2e.yml
[rust-tests]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/rust-tests.yml
[pyproject]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/pyproject.toml
[uv-check]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/uv-lockfile-check.yml
[flake]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/flake.nix
[nix-checks]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/nix/checks.nix
[nix-workflow]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/nix.yml
[docker]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/docker.yml
[docker-lint]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/docker-lint.yml
[supply]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/supply-chain-audit.yml
[osv]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/osv-scanner.yml
[catalog]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/plugin-catalog-ci.yml
[contributing]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/CONTRIBUTING.md
[pr-template]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/PULL_REQUEST_TEMPLATE.md
[review-labels]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows/review-labels.yml
[release-script]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/scripts/release.py
[security]: https://github.com/NousResearch/hermes-agent/blob/284d220ba48e25f2e3623b3afe72db8f24a4c2db/SECURITY.md
[workflows]: https://github.com/NousResearch/hermes-agent/tree/284d220ba48e25f2e3623b3afe72db8f24a4c2db/.github/workflows
[incident]: https://github.com/NousResearch/hermes-agent/issues/61631
[fix-pr]: https://github.com/NousResearch/hermes-agent/pull/61900
[closure]: https://github.com/NousResearch/hermes-agent/issues/61631#issuecomment-4932597300
[old-agents]: https://github.com/NousResearch/hermes-agent/blob/f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a/AGENTS.md
[old-scheduler]: https://github.com/NousResearch/hermes-agent/blob/f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a/cron/scheduler.py
[old-scheduler-tests]: https://github.com/NousResearch/hermes-agent/blob/f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a/tests/cron/test_scheduler.py
[fix-diff]: https://github.com/NousResearch/hermes-agent/compare/f8361d29c8e2a2be6ba9ada32f1d694bf47a4b6a...6fa9465ce34c5e5db54fe8b34544fd79f797f423
[fix-loop-tests]: https://github.com/NousResearch/hermes-agent/blob/6fa9465ce34c5e5db54fe8b34544fd79f797f423/tests/run_agent/test_verification_continuation_budget.py
[fix-finalizer-tests]: https://github.com/NousResearch/hermes-agent/blob/6fa9465ce34c5e5db54fe8b34544fd79f797f423/tests/agent/test_turn_finalizer_iteration_limit_exit.py
