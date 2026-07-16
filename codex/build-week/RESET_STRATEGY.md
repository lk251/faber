# Build Week GPT-5.6 reset strategy

Use model resets to increase independent scrutiny, not to multiply product scope.

## Primary implementation thread

Keep one continuous Codex thread, using GPT-5.6 Sol at the strongest practical reasoning
setting available in the Codex interface, for the core implementation sequence:

```text
0076 boundary and baseline
0077 proof protocol and policy
0078 GPT-5.6 adapter
0079 proof catalog and executors
0080 CLI and report
0081 skill and winning demo
```

This should be the thread where the majority of core functionality is built. Before it
ends, Javier must run `/feedback` and record the returned session ID. Do not split core
ownership across many sessions merely because resets are available.

The instruction for this thread is:

```text
Use $build-week-director and continue until the next human-only gate.
```

## Independent reset sessions

Use fresh reset sessions after the named implementation gates. Their job is to find
faults that the primary thread is likely to miss, not to propose a new product.

### A1 — Architecture and authority audit

Eligible after 0079.

Focus:

- provider neutrality;
- proof-record boundaries;
- model advisory role;
- receipt authority;
- deterministic verdict semantics;
- accidental framework or scope growth.

### A2 — Adversarial security audit

Eligible after 0081.

Focus:

- untrusted task/diff/model/replay content;
- proof-catalog enforcement;
- repository and path boundaries;
- secret leakage;
- replay tampering;
- false-pass paths.

### A3 — Clean-room installation audit

Eligible after 0082.

Focus:

- fresh clone and wheel installation;
- no hidden `PYTHONPATH` or editable-install dependency;
- Windows and Linux commands;
- no-key demo reproducibility;
- package data and report paths.

### A4 — Judge comprehension audit

Eligible after 0082 and a generated blocked/passing report pair.

Focus:

- can a skeptical judge understand the value in 30 seconds;
- is the failed claim and counterexample visible immediately;
- does the product sound novel rather than generic;
- is the three-minute narrative overloaded;
- do the screenshots and README lead with the decisive reversal.

### A5 — Final compliance and submission audit

Eligible after 0083 machine work.

Focus:

- official-rule compliance;
- pre-existing/new-work boundary;
- repository and video access;
- `/feedback` ID;
- required README content;
- final tag and audited commit consistency;
- deadline and judging-period availability.

## Reset instruction

In a fresh session, use:

```text
Use $build-week-auditor and run the next eligible independent audit.
```

The auditor reads `codex/build-week/AUDIT_QUEUE.md`, selects the first eligible incomplete
audit, and writes a durable report. Javier should not paste an audit checklist.

## Separation of duties

- The primary director implements features and fixes accepted findings.
- The auditor produces independent findings and may add narrowly scoped failing tests or
  an audit report, but it must not redesign the product or weaken proof policy.
- Only one session should make overlapping source changes at a time.
- Do not run two audits against different uncommitted working trees.
- Rebase or refresh an audit session against the current implementation branch before
  trusting its conclusions.
- Every P0 finding must become a tracked status item with an owner and verification
  command.

## Audit severity

Use:

```text
P0  Can disqualify the submission, produce an unjustified PASS, break the core demo,
    leak sensitive data, or prevent clean judge use.
P1  Materially weakens a judging criterion or common product path.
P2  Useful improvement that must not delay P0 completion.
```

A finding is not resolved by explanation alone when a deterministic test, code fix, or
submission change is feasible.

## Stopping rule

Stop running new audit resets when:

- all P0 findings are resolved;
- all P1 findings that affect the three-minute experience are resolved or explicitly
  rejected with rationale;
- the final audit is green;
- remaining time is needed for human recording, repository sharing, `/feedback`, and
  Devpost submission.

More resets are not automatically better. A stable audited tag and completed human
submission steps dominate another speculative review.