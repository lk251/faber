# Hermes Agent candidate ranking

Survey date: 2026-07-08.

Repository surveyed: `NousResearch/hermes-agent`.

This ranking is a Faber planning artifact. It does not imply Hermes maintainer
endorsement, and it does not make Hermes Agent a Faber dependency. Issue state
and upstream priorities can change, so re-check every issue before proposing,
funding, or starting an external bounty.

## Scoring model

Scores are 1 to 5. Higher is better. `Risk` is inverted: 5 means low risk and 1
means high risk.

Criteria:

- `Value`: real upstream user or maintainer value.
- `Verifier`: feasibility of objective local verifier commands.
- `Trace`: usefulness for Faber trajectory and trace learning.
- `Engagement`: likely community interest or feedback.
- `Risk`: bounded external, credential, platform, or product risk.
- `Bounded`: implementation size and ability to stop cleanly.
- `Acceptance`: likely maintainer acceptance if implemented well.

## Ranked candidates

| Rank | Issue | Theme | Value | Verifier | Trace | Engagement | Risk | Bounded | Acceptance | Total | Notes |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | [#48628](https://github.com/NousResearch/hermes-agent/issues/48628) | Managed/read-only NixOS lazy dependency startup cost | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 31 | Strong first candidate: clear repro, measurable startup behavior, NixOS evidence, no external credentials. |
| 2 | [#59026](https://github.com/NousResearch/hermes-agent/issues/59026) | Langfuse observability can silently stop after venv refresh | 4 | 4 | 5 | 4 | 4 | 4 | 4 | 29 | Direct trace/observability value. Needs careful fail-open behavior and no live Langfuse dependency in tests. |
| 3 | [#60598](https://github.com/NousResearch/hermes-agent/issues/60598) | Skill scanner verdict provenance and multi-file skill install | 4 | 4 | 4 | 4 | 3 | 4 | 3 | 26 | Good plugin lifecycle candidate with fake fixtures; avoid over-claiming scanner internals. |
| 4 | [#58937](https://github.com/NousResearch/hermes-agent/issues/58937) | Bump sealed Nix venv from Python 3.12 to 3.13 | 4 | 5 | 3 | 3 | 4 | 5 | 2 | 26 | Very bounded Nix task, but acceptance may depend on upstream release and dependency policy. |
| 5 | [#43810](https://github.com/NousResearch/hermes-agent/issues/43810) | Nix extraPythonPackages collision filtering | 4 | 5 | 4 | 3 | 3 | 3 | 3 | 25 | Strong verifier story, but body says implementation is already complete; re-check for PR/duplication first. |
| 6 | [#60578](https://github.com/NousResearch/hermes-agent/issues/60578) | Plugin hook omits `turn_id` | 4 | 4 | 4 | 3 | 3 | 3 | 3 | 24 | Useful durable feedback/plugin correctness task; may need broader dispatch-chain changes. |
| 7 | [#60624](https://github.com/NousResearch/hermes-agent/issues/60624) | Windows ffmpeg discovery for Discord voice/TTS | 4 | 4 | 3 | 3 | 4 | 4 | 2 | 24 | Concrete Windows task, but a zip patch exists in comments and platform verification may be awkward. |
| 8 | [#48897](https://github.com/NousResearch/hermes-agent/issues/48897) | Stable/classic Nix compatibility | 5 | 3 | 4 | 4 | 2 | 1 | 3 | 22 | High value, but too broad for a first Faber bounty unless split into a tiny first slice. |
| 9 | [#60609](https://github.com/NousResearch/hermes-agent/issues/60609) | Gateway-originated session orphan reaping loop | 5 | 3 | 4 | 4 | 1 | 2 | 3 | 22 | High upstream value but risky: session-state bug, many components, possible production data sensitivity. |
| 10 | [#60633](https://github.com/NousResearch/hermes-agent/issues/60633) | Desktop thumbs-up/thumbs-down durable preference | 3 | 3 | 5 | 3 | 3 | 3 | 1 | 21 | Good learning-signal theme, but issue body says it was implemented in #60581. Re-check before considering. |

## Top 3 pilot tasks

### 1. Managed NixOS lazy-dependency startup fix

Target: [#48628](https://github.com/NousResearch/hermes-agent/issues/48628).

Why it fits Faber:

- Clear objective symptom: repeated ensurepip/pip bootstrap on managed/read-only installs.
- Strong verifier path: fake managed install, missing optional backend, assert no ensurepip subprocess.
- Strong trajectory value: environment evidence, startup timing, command traces, and negative-cache behavior.
- NixOS-first without being NixOS-only: the same managed-install boundary can cover Homebrew-style installs.

Acceptance criteria:

- Add a managed/read-only install guard before lazy dependency install attempts.
- Preserve user-facing remediation for missing optional features.
- Add tests proving managed installs do not invoke ensurepip/pip for doomed writes.
- Add or update docs for the managed-install remediation.
- Produce `.faber/attempt.json` with environment evidence and verifier command.
- Prefer Level 2 evidence with a Faber Runner trace showing the guarded path.

### 2. Langfuse tracing dependency health signal

Target: [#59026](https://github.com/NousResearch/hermes-agent/issues/59026).

Why it fits Faber:

- Directly aligned with trace/observability reliability.
- Bounded initial scope: manifest dependency metadata plus a visible health or doctor signal.
- Can be verified with fake import state and without real Langfuse credentials.
- Produces useful evidence about fail-open trace plugins.

Acceptance criteria:

- Declare or otherwise persist the Langfuse SDK dependency for the bundled plugin setup path.
- Add a visible warning or health check when plugin enabled plus credentials present but SDK import fails.
- Keep runtime plugin behavior fail-open so agent execution is not broken by tracing.
- Add tests with a fake missing SDK/import path.
- Add `.faber/attempt.json` and a redacted trace showing setup, verifier, and health-check events.

### 3. Third-party skill install and scanner provenance fixture

Target: [#60598](https://github.com/NousResearch/hermes-agent/issues/60598).

Why it fits Faber:

- Good external-harness safety-manifest bridge.
- Can use fake skill repos with `SKILL.md`, `references/`, `templates/`, and `examples/`.
- Creates meaningful trace data about install decisions, scanner verdicts, and copied artifacts.
- Avoids real provider credentials.

Acceptance criteria:

- Add a minimal fake fixture that proves current multi-file skill expectations.
- Either copy referenced support files or emit a clear warning that only `SKILL.md` is installed.
- Expose scanner verdict provenance enough to distinguish current-content, cache, or heuristic sources.
- Add tests for content-hash changes and multi-file install behavior.
- Add `.faber/attempt.json`; Level 2 trace preferred for scanner and install decisions.

## Recommended next step

Use #48628 as the default first external Faber pilot if it is still open and not
already solved when the pilot starts. It has the best mix of upstream value,
objective verification, NixOS-first replay evidence, bounded implementation, and
training-quality trajectory potential.
