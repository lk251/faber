# Optional proof-proposal observations

Faber Proof can retain its proposal-time inputs, results and failed planning attempts across repair reruns. This is an opt-in local research feature. It reuses `TraceEvent`, `ProofPlanningRequest`, `ProofPlanningResult`, `ProofWorkflowResult` and `ProofDecision`; it does not change the proof protocol, acceptance authority, default reports or training permissions.

## Run the no-key demonstration

From a development checkout with Python 3.11+ and Git:

```text
python scripts/proof_observation_demo.py
```

The script reads the existing approved development replay fixtures, creates a disposable example Git repository beneath `.faber/observation-demo/run-*`, runs the bad and repaired candidates into the **same** proof output, deliberately tries a stale replay, and appends separately labeled synthetic owner feedback. Each invocation creates a fresh directory and prints a JSON summary. It makes no model-provider calls and modifies no Build Week fixtures.

Expected: three retained observation runs; nine events consisting of three proposal observations, two planning results, two verification observations, one planning failure and one feedback event. The ordinary proof output ends at `PASS` for the repaired candidate; the deliberately failed planning attempt and owner feedback do not rewrite that valid bundle. This is a synthetic archive regression demonstration, not an external-repository benchmark or model-learning result.

## Use with a real local proof

Add the optional flag to the existing owner-configured proof invocation:

```text
faber proof --repo . --task <task-contract.json> --catalog <approved-catalog.json> --base <base> --candidate <candidate> --mode replay --replay <approved-replay.json> --out-dir .faber/proof --observations-dir .faber/proof-observations
```

The Python API uses `run_proof_product(..., observations_directory=".faber/proof-observations")`. Omitting the argument/flag preserves existing behavior. The flag also works with a separately authorized live call; it does not authorize that call or provide a key. `--dry-run` archives the proposal and result without reporting verification success.

Before calling the planner, the writer exclusively creates a unique `observation-*` directory containing the already-redacted planning request, owner policy, and `000000-event.json`. The event records actual local observation time, configured model/mode, the explicit dry-run flag and digest references; it leaves unobserved alternatives, selection probability, counterfactual outcome and monetary cost null. The time is a local observation, not a trusted external timestamp.

After planning, the writer saves the validated result and a second event. A planner error instead produces a stable error code plus nullable usage/latency when the error's model record binds the exact request. Provider refusal text and arbitrary exception strings are not archived. After a workflow returns, the existing validated workflow—including per-check evidence, verifier runs, receipts, timings, execution policy/workspace references and diagnostics—and decision are retained with artifact/record digests. Execution or publication errors produce a closed failure-phase observation.

Historical raw partial executions that fail before a `ProofWorkflowResult` returns remain unavailable. The archive preserves only existing redacted inputs and validated result records, not raw provider responses, raw tool streams or private chain-of-thought. A planner failure before a request has been constructed is also outside this capture boundary.

## Delayed owner-reported feedback

After a planner result or failure exists, call the separate helper with a specific retained run:

```python
from faber.proof_observations import record_proof_feedback

record_proof_feedback(
    ".faber/proof-observations/observation-<run-id>",
    reviewer_ref="owner:example",
    outcome="edited",
    reason_codes=["unnecessary_check", "wrong_environment"],
    review_receipt_digest=None,
)
```

Outcomes are `accepted`, `edited`, `rejected`, or `inconclusive`. Reason codes are `useful_missing_check`, `unnecessary_check`, `wrong_environment`, `too_expensive`, `missing_evidence`, `policy_mismatch`, or `other`. They are short labels; this helper does not collect private review comments. An optional existing review-receipt digest supplies a reference, not an authentication assertion.

The helper checks the retained request and terminal planner event, including exact artifact and record digests. If a result was observed, its record must still exist and match; missing/tampered records are rejected. Feedback targets the exact retained planning result/plan when one exists, otherwise the failed request. Feedback is self-attested, with `authority="none"` and `training_permission_granted=false`. It cannot register a verifier, approve a policy, override a proof decision or grant dataset rights.

## Storage limits and current boundaries

- Every artifact and event is created exclusively; normal reruns never overwrite earlier observations. There is a 2 MiB cap per record and a 1,000-event cap per run. Reads are bounded before JSON parsing.
- In-repository history must be below `.faber/`, and must not overlap the replaceable proof-output directory. A dedicated external local directory is also supported. Symlink/reparse ancestry, explicit Windows device/UNC paths, and ordinary/short-path aliases of unsafe locations are rejected.
- Requested capture errors are explicit `observation_error` failures. The writer never silently falls back to losing history or treats a failed capture as a successful proof run.
- This is a single-user archive, not authenticated ownership, a tamper-proof log, hostile-concurrent-filesystem isolation or a hosted tenant boundary. A crash can leave a partial artifact without a terminal event; incomplete histories must remain incomplete. Concurrent feedback writers may collide and fail explicitly.
- No training/export command is added. The research corpus must separately satisfy existing consent, license, retention and withdrawal rules. Public source access and a local capture flag do not grant permission to train across customer repositories.

The [schema audit](strategy/2026-09-12-policy-learning-schema-audit.md) explains the narrow capture gap and the stronger frontier-model-plus-retrieval baseline this data could eventually test.
