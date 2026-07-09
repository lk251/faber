# 0074 — Customer delight: copy and error messages

## Goal

Make Faber's CLI output, validation reports, docs, and fake GitHub publications feel precise, calm, and useful.

## Scope

Review and improve:

- CLI success messages
- CLI error messages
- validation report summaries
- fake GitHub comments/checks
- README/quickstart tone
- docs terminology consistency

## Requirements

- Error messages should say what failed, why it matters, and what to do next.
- Success messages should include IDs, digests, and paths without being noisy.
- Avoid hype and demo-speak.
- Keep language consistent: trace, trajectory, RL-grade trajectory, work budget, verifier receipt.
- Add tests/snapshots for important user-facing output.

## Tests

- validation error messages include field names
- CLI golden path output includes next steps
- fake GitHub receipt publication is readable
- docs glossary terms appear consistently

## Acceptance criteria

Faber feels like a carefully made tool, not a hackathon artifact.