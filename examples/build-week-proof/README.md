# Faber Proof: the last-turn report

This original, stdlib-only project demonstrates a subtle scheduler defect. A patch adds
an explicit `budget_exhausted` result, but checks the budget before accepting a complete
report on the last permitted turn. The ordinary suite covers early completion,
incomplete work, cancellation, and deterministic composition; both candidates pass it.

Faber Proof additionally exercises the missing boundary:

```text
turn_budget: 2
responses: ["NOTE: premise", "FINAL: summary"]
expected: {"status": "complete", "report": "premise\nsummary"}
```

The bad candidate returns `budget_exhausted`. The repaired candidate moves the complete
report check before the exhaustion failure and changes nothing else.

## Three-command judge path

From the Faber repository root:

```bash
python -m pip install -e .
faber doctor
faber demo proof --mode replay --out-dir .faber/build-week-demo
```

The replay command uses no account, credential, provider SDK, or network. It creates an
isolated deterministic Git repository, runs the same ordinary tests for both candidate
commits, executes Faber Proof, validates the expected `BLOCK`/`PASS` contrast, and
writes complete bundles to:

```text
.faber/build-week-demo/bad/report.html
.faber/build-week-demo/repaired/report.html
```

Add `--json` for the canonical comparison object. The equivalent repository recipe is
`just demo-proof` where `just` is available.

## Replay provenance

`replays/provenance.json` is authoritative. The initial committed bundles are labeled
`fake-development`: they are deterministic injected responses for no-key development,
not real model output and not final submission evidence. Never describe them as a live
GPT-5.6 result.

The guarded human-gate command is:

```bash
python examples/build-week-proof/scripts/capture_live_reviewed_demo.py --reviewer "Javier"
```

It requires a human-supplied API key, the expected clean branch, and the optional live
dependency. It captures both candidates into temporary staging, applies the strict
parser and all request/catalog/prompt/schema/model bindings, validates ordinary tests,
bad `BLOCK`, repaired `PASS`, portable reports, bundle digests, and artifact privacy,
then atomically replaces the fixture and reruns the offline demo. Any failure leaves or
restores the existing fixture. The complete preflight, review, and rollback procedure
is in `docs/LIVE_GPT56_CAPTURE_RUNBOOK.md`.

The lower-level `capture_live_replays.py` and `review_replays.py` utilities remain
available for debugging, but they are not the recommended final transaction. The
review command intentionally fails while provenance remains `fake-development`.

## Evidence-driven Codex repair path

For the live video, start from the materialized bad candidate and invoke:

```text
$faber-proof use live GPT-5.6 to prove this patch, repair only demonstrated failures,
and rerun the proof
```

Screen sequence:

1. Show the four ordinary tests passing for the bad commit.
2. Run `faber proof --mode live` against the exact base and bad revisions.
3. Open the blocked report and show the failed last-turn claim and bounded transcript.
4. Let Codex move only the final-report check ahead of the exhaustion return.
5. Run the same ordinary tests and a new live proof against the repaired diff.
6. Show `PASS`, complete required coverage, and the exact candidate revision.

In replay mode, the bad bundle must never be reused after the repair. The repaired diff
has a separate reviewed request-bound bundle. Outside this fixture, a changed diff
requires a new live plan or a precise stop for human action.

## Platform boundary

The demo is designed for Python 3.11+ and Git on Linux and Windows. It has no runtime
package dependency beyond Faber itself. macOS is expected to work but is not yet a
declared CI platform. The local proof runner honestly provides no operating-system,
container, descendant-process, or network isolation; production use requires a
separate enforceable sandbox.
