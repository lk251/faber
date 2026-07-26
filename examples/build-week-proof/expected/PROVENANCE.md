# Committed sample report gate

Sanitized blocked and passing sample HTML reports are intentionally not committed while
`../replays/provenance.json` is `fake-development`. Work item 0081 may generate local
reports for validation, but final sample reports and their generation manifest require
human-reviewed live replay bundles first.

Development reports generated from the current fixture are valid only for layout,
installation, deterministic-regeneration, and no-key demonstration work. They are
scanned by `faber audit-proof-artifacts` for known credential forms, forbidden fixture
values, machine-specific paths, raw-output markers, and external HTML assets. Passing
that bounded privacy audit does not change `fake-development` provenance.

The final guarded transaction is documented in
`docs/LIVE_GPT56_CAPTURE_RUNBOOK.md`. It installs reports here only after both live
responses, complete authority bindings, ordinary `PASS`/`PASS`, Faber Proof
`BLOCK`/`PASS`, digest validation, and privacy checks pass as one atomic unit.
