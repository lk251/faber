# Faber Proof artifact contract

Treat these files as the machine authority:

- `run-summary.json`: portable entrypoint, exact revisions, mode, counts, paths, and
  record digests.
- `proof-decision.json`: deterministic `pass`, `block`, or `human_review` decision.
- `proof-evidence/*.json`: expected/observed summaries and bounded counterexamples.
- `verification-receipts/*.json`: accepted authoritative verifier outcomes.
- `report.html`: judge-facing rendering; useful for explanation, never the authority.

The task contract, configuration, diff, planning request, model response, proof plan,
evidence, verifier runs, receipts, and decision must form one validated digest graph.
Missing, contradictory, unbound, or stale evidence fails closed.

Replay is a no-network reproduction of one recorded advisory response, not proof of an
arbitrary new diff. Confirm its digest is owner-approved and its provenance is explicit.
The Build Week fixture uses separate bad and repaired bundles. `fake-development` means
the response was injected and is not final live-model evidence. `live-reviewed` means a
human reviewed the sanitized live capture and its exact request bindings.

Repair candidate code only. Do not weaken owner authority to make a verdict green.
After a changed diff, obtain a new live plan or an exact matching reviewed replay.
