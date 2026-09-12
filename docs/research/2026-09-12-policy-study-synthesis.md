# Three repositories test the policy-automation thesis

**Result:** a cold-start agent can recover a useful verification inventory and draft
policy from all three repositories. The evidence does not establish that a separate
policy-authoring product improves on a strong agent with current documentation and
retrieved history. The credible remaining test is recurring policy maintenance and
evidence completeness, including environment fidelity and owner corrections.

Policy learning is unresolved. Public history supplies valuable partial examples,
but lacks enough alternative outcomes, decision-time context and active reviewer
effort to train or evaluate an optimal policy without additional observation.

## Current snapshots and detailed deliverables

| Repository / scope | Source pin retrieved September 12 | Study and source evidence |
|---|---|---|
| NousResearch/hermes-agent | `284d220ba48e25f2e3623b3afe72db8f24a4c2db` | [Study](2026-09-12-hermes-policy-study.md), [manifest and temporal rows](2026-09-12-hermes-policy-sources.json) |
| omacom/omarchy, formerly basecamp/omarchy | `31bd80daa4613ffdee995ac27467fce5a2990806` | [Study](2026-09-12-omarchy-policy-study.md); sibling package/ISO pins and chronological example included |
| NixOS/nixpkgs, nginx NixOS service and related tests | `2f788abe393b6639416941926d53e106915f269d` | [Study](2026-09-12-nixpkgs-policy-study.md), [manifest and temporal rows](2026-09-12-nixpkgs-policy-study.sources.json) |

These are observed upstream identities, not guaranteed latest after the research
time. Studies used current source, public CI/API state, documentation, source hashes
and historical diffs. No upstream tests, installers, Nix evaluations, VM or privileged
commands were run. Historical simulations are source-grounded reconstructions, not
reproduced defects or measured Faber detections. No maintainer approved the proposals.

The bounded NixOS choice makes this a real service-lifecycle exercise: nginx has
configuration generation, privilege/hardening, reload, tmpfiles and certificate
integration, with existing VM tests and inspectable incident histories. It does not
stand in for every subsystem or all package verification in nixpkgs.

## What exists already

| Dimension | Hermes | Omarchy | nginx / nixpkgs |
|---|---|---|---|
| Existing policy | Path classifier, hermetic runner, real regression requirements, area instructions | Task-to-skill routing, migration conventions, visual and fresh-ISO requirements | Owner routing, explicit AI contribution policy, dependency/package and VM test conventions |
| Static inventory observed | 35 workflows and 4,048 pytest-style files; counts, not executions | 236 shell suites and eight acceptance suites; zero checked-in workflows but dynamic GitHub automation | 22 registered nginx test entries including the main test, plus relevant ACME variants |
| Strong checks | Real-loop regressions, host markers, package/module tests, separate installer and Docker lanes | Fake-home/stub suites, runtime GUI checks, package isolation and disposable ISO acceptance | Service reload/restart, invalid configuration, lifecycle and variant integration scenarios |
| Evidence ambiguity | Disabled desktop E2E, advisory diagnostics, scheduled versus pre-merge checks | Exit-zero compositor skips, suite-only versus runtime source sync, checkout/package/ISO skew | Test existence versus selection; package passthru differs from registry; container/VM equivalence |
| Human boundary | Acceptance intent and real-path regression quality | Visual/physical behavior, supported hardware and upgrade populations | Compatibility, hardening semantics, VM requirements and release/backport risk |

Both “no policy” and “green CI proves coverage” are false starting assumptions.
Public ruleset visibility was incomplete; missing files/API 404s were not converted
into claims of absent enforcement. Current upstreams also differ substantially from
their July or pre-incident forms.

## Cold-start proposal procedure

1. Mechanically inventory declared workflows, test registrations, dependencies,
   environments, ownership and release artifacts. Keep source hashes and distinguish
   configured, reachable, executed, required, advisory, disabled and unknown.
2. Use reasoning to map changed components to existing scenario evidence, resolve
   inconsistent docs, identify missing boundary tests and retrieve relevant incidents.
   Preserve proposed rationale and its sources; do not copy executable instructions
   from untrusted text into authority.
3. Ask the owner only what cannot be inferred: supported configurations, risk
   tolerance, which evidence is mandatory, who can approve exceptions and whether
   the suggested scenario expresses the real requirement.
4. Implement bespoke harnesses only when an accepted requirement has no credible
   existing test. Confirm the new check fails on the relevant prior behavior and
   passes after repair in the approved environment.
5. Bind subsequent evidence to the approved policy, source/environment, execution
   and applicability decision. Missing required evidence stays unresolved. Proposed
   policy changes do not approve the candidate that contains them.

The detailed studies contain task/risk matrices, mandatory and optional checks,
environment/evidence requirements, owner questions and uncertainty rules. They are
draft proposals. Faber's current closed catalog supports pre-approved checks; it
does not automatically create a safe executable policy for these upstreams.

## Historical changes teach different lessons

**Hermes:** the old #61631 pilot is closed. More significantly, a maintainer rejected
an earlier mocked scheduler repair and accepted a different real-loop/provenance
repair. The original Faber scheduler demo is an original constructed example; it
should not be treated as evidence that Faber diagnosed the actual upstream bug.
Good policy requires understanding the actual path, including negative controls.

**Omarchy:** optional touchpad logic could halt installation under a chroot/running
kernel mismatch. Yet fresh-ISO acceptance was already documented before the incident.
The problem cannot be reduced to missing prose. A separate test-runner change also
shows why a failing early suite must not hide later coverage. Fixtures and physical
runtime evidence answer different questions.

**nginx:** a temporary directory disappearing after inactivity required an accelerated
lifecycle regression, not just HTTP startup. Later, moving existing tests to containers
was reverted for hardening coverage; the pre-change documentation already exposed VM
advantages. Those cases support persistent scenario/environment requirements, but
also give frontier reasoning and retrieval a fair chance of matching Faber.

None supports the claim “Faber would have prevented this” without a held-out,
pre-outcome comparison. Actual failure/revert labels, source timestamps and missing
costs are separated in the studies' learning records.

## Human effort and adoption

An inventory may take a capable engineer/agent hours; a credible approved policy adds
owner judgment and environment setup. Each study estimates initial setup, maintainer
questions, ongoing upkeep and bespoke verifier work separately. The nginx study, for
example, estimates 5–13 engineer hours plus 1–3 maintainer hours for initial policy,
with runner setup separate. These are estimates, not timed experiments.

This burden is a major threat to self-serve adoption. Omarchy hardware/GUI work and
nginx VM execution remain real work after policy generation. Hermes' normal conftest
and plugin environment cannot simply be replaced by Faber's isolated pytest defaults.
A paid service can handle a narrow case; a universal bootstrapper would hide too much
integration and owner labor.

## What would establish additional product value?

Give the baseline the same repository, current documentation, retrieval, runner,
time and owner-approved constraints. Let it use a short CI script or test map.
Compare Faber's recurring workflow on held-out changes, measuring missed required
coverage, unnecessary escalation, owner edits, reviewer minutes, setup/upkeep and
execution cost. Include the customer's existing runtime-review product where used.

If the simple baseline is equivalent, keep that solution. If a maintained, portable
evidence/incident map saves repeated work, test payment and renewal. A useful OSS
study does not itself establish a budget owner; these repositories are evidence
sources, not assumed customers.

## Policy-learning conclusion and next action

Useful examples can be reconstructed, especially explicit rejected/accepted proposals
and later environment/test corrections. But public history usually lacks the
counterfactual check matrix and the actual decision-time retrieval/owner interaction.
Collecting more merged PRs cannot fix that bias.

The immediate implementation is therefore opt-in prospective observation capture,
reusing Faber's request/plan/trace primitives. Compare static policy, frontier context,
frontier+retrieval and a small learned router only when sufficient labels exist.
Within-repo history may create customer value before cross-repo training does.
Training wins only if it beats retrieval after accounting for labels and upkeep.

[Learning analysis and schema audit](../strategy/2026-09-12-policy-learning.md),
[commercial decision](../strategy/2026-09-12-decision.md),
[priced offer](../strategy/2026-09-12-first-revenue-plan.md),
[experiment and kill criteria](../strategy/2026-09-12-experiments.md).
