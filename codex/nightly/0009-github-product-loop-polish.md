# 0009 — GitHub product loop polish

## Goal

Make Faber for GitHub feel like the beginning of a real product loop: issue intake, contract marker, PR attempt, verifier receipt publication, and trajectory export should read coherently end to end.

This still uses fake/in-memory GitHub clients and local objects. Do not make real GitHub API calls.

## Scope

Improve the GitHub adapter around:

- issue intake
- contract marker UX
- PR attempt conversion
- receipt publication text
- check/status-like publication structure
- example fixtures
- documentation

## Requirements

1. Add realistic GitHub fixture payloads under `tests/fixtures/github/`:
   - issue opened
   - pull request opened
   - check run completed
   - installation repositories selected
2. Add example issue body and PR body fixtures that feel like real developer workflows.
3. Make contract markers readable and robust when surrounded by human text.
4. Improve receipt publication copy so a repo maintainer can understand:
   - accepted or rejected result
   - verifier used
   - candidate revision
   - receipt digest
   - next action if rejected
5. Add a single high-level test that demonstrates the fake GitHub product loop:
   - issue evidence becomes a task contract
   - marker is rendered
   - PR evidence becomes an attempt
   - approved verifier run creates a receipt
   - receipt is published through fake client
   - trajectory can be exported
6. Ensure CI/check-run payloads remain signal only, never authoritative acceptance.
7. Update `docs/GITHUB_APP.md` with a concise end-to-end example.
8. Keep GitHub adapter code separate from core objects.

## Craftsmanship bar

This should start to feel like a product a maintainer would trust. The text written back to GitHub should be clear, calm, and precise.

## Tests

Add tests for:

- realistic fixtures parsing
- readable publication text
- contract marker round trip in a human issue body
- full fake GitHub product loop
- rejected verifier publication path

## Acceptance criteria

- A fake end-to-end GitHub workflow exists and is tested.
- Maintainer-facing copy is clear and includes audit identifiers.
- Docs include a coherent GitHub example.
- No real GitHub API calls are added.
- Existing tests still pass.
