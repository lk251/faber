"""Protocol adapters and narrow product-facing provider dispatch."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from faber.adapters.openai.proof_planner import (
    OpenAIProofPlannerBackend,
)
from faber.adapters.openai.proof_planner import (
    build_planning_request as build_planning_request,
)
from faber.adapters.openai.replay import ReplayProofPlannerBackend, load_replay_bundle
from faber.proof_planning import ProofPlanningError, ProofPlanningRequest, ProofPlanningResult


def plan_proof_request(
    *,
    mode: str,
    replay_path: str | Path | None,
    model: str,
    request: ProofPlanningRequest,
    approved_replay_bundle_digests: Sequence[str],
) -> ProofPlanningResult:
    """Dispatch the Build Week planner while keeping provider code in this boundary."""

    if mode == "replay":
        if replay_path is None:
            raise ProofPlanningError("configuration_error", "replay mode requires --replay")
        bundle = load_replay_bundle(replay_path)
        digest = bundle.digest()
        if digest not in approved_replay_bundle_digests:
            raise ProofPlanningError(
                "replay_mismatch",
                "replay bundle digest is not approved by repository-owner configuration",
            )
        return ReplayProofPlannerBackend(
            bundle,
            expected_bundle_digest=digest,
            expected_requested_model=model,
        ).plan_result(request)
    if mode == "live":
        if replay_path is not None:
            raise ProofPlanningError(
                "configuration_error",
                "--replay is not valid in live mode",
            )
        return OpenAIProofPlannerBackend(model=model).plan_result(request)
    raise ProofPlanningError("configuration_error", "mode must be live or replay")
