# Golden fixture corpus

The canonical snapshots in `tests/fixtures/golden/` protect Faber's core audit,
learning, review, funding, selection, and environment evidence from accidental
serialization drift.

| Fixture | Expected behavior |
| --- | --- |
| `trajectory-pr-only.json` | Valid customer/audit record with low process evidence |
| `trajectory-manifest.json` | Manifest-backed supervised/router evidence |
| `trajectory-rl-trace.json` | RL-grade ordered process evidence |
| `trajectory-replayable-episode.json` | Highest-tier replayable episode package |
| `funded-github-issue.json` | Contract- and budget-bound marker with no settlement authority |
| `trajectory-rejected.json` | RL-useful negative attempt with process evidence |
| `trajectory-human-reviewed.json` | Trace-backed attempt with a supplementary human review receipt |
| `candidate-pool-advisory-ranked.json` | Advisory candidate ranking without hard verification authority |
| `environment-nixos.json` | Nix flake lock evidence and strongest corpus replay level |
| `environment-cross-platform.json` | Windows lockfile evidence that remains useful across platforms |

Every file is one canonical JSON object with fixed IDs and timestamps. The
`digests.json` manifest records each semantic payload digest and the expected JSONL
digest for exporting the six trajectory fixtures in documented order.

Update snapshots only when protocol behavior changes intentionally. Rebuild through
`write_golden_fixture_corpus()`, inspect the semantic diff, and run the complete test
suite. Do not hand-edit payload digests to make a failing snapshot pass.
