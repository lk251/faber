# 0049 — Trajectory validation CLI and quality reports

## Goal

Give users and agents a clear command-line way to validate traces, manifests, and trajectories before submission or dataset export.

## Scope

Add CLI commands such as:

- `faber validate-attempt .faber/attempt.json`
- `faber validate-trace .faber/trace.jsonl`
- `faber validate-trajectory path/to/trajectory.json`
- `faber trajectory-quality path/to/trajectory.json`

## Requirements

- Validation output should be structured JSON with a human-readable summary.
- Reports should identify audit eligibility, supervised-learning eligibility, RL-grade eligibility, training consent, redaction status, and missing fields.
- Errors should name the bad field and expected shape.
- Exit codes should distinguish valid, warning, and invalid.
- Add examples to docs.

## Tests

- valid RL-grade trajectory returns success
- PR-only trajectory returns valid-but-not-RL-grade warning
- malformed manifest returns clear error
- missing consent blocks training export
- CLI output is stable enough for snapshot tests

## Acceptance criteria

Solvers can know before submission whether their artifacts meet Faber's trajectory requirements.