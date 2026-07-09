# Hermes Agent pilot selection - 2026-07-09

Repository surveyed: `NousResearch/hermes-agent`.

This is a Faber planning artifact. Hermes Agent is a read-only external reference,
no upstream maintainer has endorsed this pilot, and the placeholder budget does not
represent committed funds.

## Ranking

The survey favored narrow behavior, deterministic local verification, no production
credentials, low privacy risk, and a contribution that remains useful without Faber.

| Rank | Issue | Fit | Main reservation |
| ---: | --- | --- | --- |
| 1 | [#61631 scheduler report loss at turn-budget exhaustion](https://github.com/NousResearch/hermes-agent/issues/61631) | Clear cross-module mismatch, deterministic failure-path tests, no provider access | Must preserve failure handling for empty or incomplete runs |
| 2 | [#44456 desktop `/compress` command routing](https://github.com/NousResearch/hermes-agent/issues/44456) | Crisp command-dispatch behavior and local tests | Ten comments indicate more coordination and possible active work |
| 3 | [#61418 sessions search is page-local](https://github.com/NousResearch/hermes-agent/issues/61418) | Objective expected behavior and useful product fix | Requires broader UI/backend pagination fixtures |
| 4 | [#37179 cron ticker dies after a long job](https://github.com/NousResearch/hermes-agent/issues/37179) | High-value scheduler reliability work | Concurrency and timing make a first verifier less deterministic |
| 5 | [#61627 update restore approval is misrouted](https://github.com/NousResearch/hermes-agent/issues/61627) | Reproducible state-transition defect | Exercises update, restore, and approval state with greater external-state risk |
| 6 | [#32836 mobile thumbnail controls](https://github.com/NousResearch/hermes-agent/issues/32836) | Visible user-facing defect | Acceptance is more visual and the report lacks the referenced screenshots |

All six issues were open when checked on 2026-07-09. None had an assignee. Issue
#61420 was not ranked despite its small scope because the reporter explicitly said
they intended to implement it themselves.

## Selection

Issue #61631 is the proposed first pilot. The report identifies a concrete contract
mismatch: the scheduler recognizes an exit reason the conversation loop does not
emit, allowing a complete scheduled report to be discarded at budget exhaustion.
The fix can be constrained by tests for explicit exhaustion, loop-condition
fall-through, successful delivery with non-empty composed output, and continued
failure for incomplete output.

The executable package is
`src/faber/adapters/hermes/scheduler_delivery_pilot.py`. It contains the task
contract, three verifier specs, a trace-level evidence requirement, and a
provider-free EUR budget placeholder.

## Evidence and settlement

- A trace-tier trajectory is required for the pilot evidence package and full payout.
- A replayable episode is eligible for the separate trace-quality bonus.
- Training-use consent is independent of work acceptance and payout.
- Settlement still requires an accepted authoritative receipt from the focused and
  regression behavior verifiers.
- The Faber trajectory verifier is supplemental evidence, not upstream authority.

## Upstream path

1. Re-check issue #61631 immediately before work and ask the reporter or maintainer
   whether a contribution is welcome.
2. Work in a fork on a focused branch; avoid any production account, credential,
   private prompt, live provider, or real schedule.
3. Submit a small conventional PR that references the issue, explains the failure
   paths, and lists exact focused and regression test commands.
4. Keep `.faber` artifacts outside the upstream patch unless maintainers ask for
   them. Link them only as supplemental audit evidence.
5. Treat maintainer direction as authoritative and never imply endorsement,
   guaranteed funding, or a requirement to adopt Faber.
