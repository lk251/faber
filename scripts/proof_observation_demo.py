"""No-key synthetic history demo using the existing approved development replay."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import (  # noqa: E402
    materialize_demo_repository,
    resolve_demo_fixture_root,
    review_demo_replays,
)
from faber.proof_observations import record_proof_feedback  # noqa: E402
from faber.proof_product import ProofProductError, run_proof_product  # noqa: E402


def run_demo(output_parent: Path) -> dict[str, object]:
    started = time.perf_counter()
    fixture = resolve_demo_fixture_root(REPOSITORY_ROOT)
    provenance = review_demo_replays(fixture)["provenance"]
    output_parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="run-", dir=output_parent))
    repository = materialize_demo_repository(fixture, output / "repository")
    history = output / "history"
    current = output / "current-proof"
    verdicts: list[str | None] = []
    first_observation: Path | None = None
    for name, revision in (
        ("bad", repository.bad_revision),
        ("repaired", repository.repaired_revision),
    ):
        subprocess.run(
            ["git", "checkout", "-q", "--detach", revision],
            cwd=repository.root,
            check=True,
        )
        outcome = run_proof_product(
            repository=repository.root,
            task_path=fixture / "task-contract.json",
            catalog_path=fixture / "proof-catalog.json",
            base_revision=repository.base_revision,
            candidate_revision=revision,
            mode="replay",
            replay_path=fixture / "replays" / f"{name}.json",
            output_directory=current,
            observations_directory=history,
        )
        verdicts.append(outcome.verdict)
        if first_observation is None:
            first_observation = next(history.iterdir())
    if verdicts != ["block", "pass"] or first_observation is None:
        raise AssertionError("the existing development replay contrast changed")

    # Deliberately supply the bad candidate's replay for the repaired candidate.
    # This is an injected stale-context planner failure, not a model-provider call.
    failure_code: str | None = None
    try:
        run_proof_product(
            repository=repository.root,
            task_path=fixture / "task-contract.json",
            catalog_path=fixture / "proof-catalog.json",
            base_revision=repository.base_revision,
            candidate_revision=repository.repaired_revision,
            mode="replay",
            replay_path=fixture / "replays" / "bad.json",
            output_directory=current,
            observations_directory=history,
        )
    except ProofProductError as error:
        failure_code = error.category
    if failure_code != "replay_mismatch":
        raise AssertionError("the deliberately stale replay must fail")

    record_proof_feedback(
        first_observation,
        reviewer_ref="synthetic-demo-owner",
        outcome="accepted",
        reason_codes=["useful_missing_check"],
    )
    runs = list(history.iterdir())
    events = [
        json.loads(path.read_text(encoding="utf-8"))
        for run in runs
        for path in sorted(run.glob("*-event.json"))
    ]
    counts: dict[str, int] = {}
    for event in events:
        event_type = event["event_type"]
        counts[event_type] = counts.get(event_type, 0) + 1
    expected = {
        "policy.proposal_observed": 3,
        "policy.proposal_result": 2,
        "policy.verification_observed": 2,
        "policy.proposal_failed": 1,
        "policy.owner_feedback_reported": 1,
    }
    if counts != expected or len(runs) != 3:
        raise AssertionError("the complete observation history was not retained")
    current_summary = json.loads((current / "run-summary.json").read_text(encoding="utf-8"))
    if current_summary["verdict"] != "pass":
        raise AssertionError("failed planning or feedback changed the last valid proof bundle")
    summary: dict[str, object] = {
        "synthetic_demo": True,
        "external_repository_benchmark": False,
        "fixture_provenance": provenance,
        "provider_calls": 0,
        "output_directory": str(output.resolve()),
        "same_proof_output_reused": True,
        "candidate_verdicts": verdicts,
        "injected_failure": failure_code,
        "retained_runs": len(runs),
        "event_counts": counts,
        "event_count": len(events),
        "training_permission_granted": False,
        "history_bytes": sum(path.stat().st_size for run in runs for path in run.iterdir()),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    (output / "summary.json").write_text(canonical_json(summary) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path, default=REPOSITORY_ROOT / ".faber" / "observation-demo"
    )
    arguments = parser.parse_args()
    print(canonical_json(run_demo(arguments.out_dir.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
