"""Protocol adapters and narrow product-facing provider dispatch."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from faber.adapters.openai.prompt import RESPONSE_SCHEMA_VERSION
from faber.adapters.openai.proof_planner import (
    PROVIDER_ADAPTER_ID,
    OpenAIProofPlannerBackend,
)
from faber.adapters.openai.proof_planner import (
    build_planning_request as build_planning_request,
)
from faber.adapters.openai.replay import (
    ReplayProofPlannerBackend,
    create_replay_bundle,
    load_replay_bundle,
)
from faber.proof_planning import (
    ProofPlanningError,
    ProofPlanningRequest,
    ProofPlanningResult,
    ProviderPlanningResponse,
)


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


def create_planning_replay_record(
    request: ProofPlanningRequest,
    structured_response: Mapping[str, object],
    *,
    created_at: str,
    requested_model: str,
    returned_model: str,
    response_id: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
) -> tuple[dict[str, object], str]:
    """Create one sanitized replay record from explicitly injected development data."""

    response_payload = dict(structured_response)
    response_payload.setdefault("schema", RESPONSE_SCHEMA_VERSION)
    response = ProviderPlanningResponse(
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        requested_model_id=requested_model,
        returned_model_id=returned_model,
        response_id=response_id,
        mode="live",
        structured_response=response_payload,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    bundle = create_replay_bundle(request, response, created_at=created_at)
    return bundle.to_dict(), bundle.digest()


def capture_live_planning_replay_record(
    request: ProofPlanningRequest,
    *,
    model: str,
    created_at: str,
) -> tuple[dict[str, object], str]:
    """Capture one live response through the guarded adapter without persisting credentials."""

    response = OpenAIProofPlannerBackend(model=model).plan(request)
    bundle = create_replay_bundle(request, response, created_at=created_at)
    return bundle.to_dict(), bundle.digest()


def validate_planning_replay(
    path: str | Path,
    *,
    request: ProofPlanningRequest,
    expected_bundle_digest: str,
    expected_requested_model: str,
) -> dict[str, object]:
    """Revalidate a replay and return only safe review metadata."""

    bundle = load_replay_bundle(path)
    result = ReplayProofPlannerBackend(
        bundle,
        expected_bundle_digest=expected_bundle_digest,
        expected_requested_model=expected_requested_model,
    ).plan_result(request)
    return {
        "bundle_digest": bundle.digest(),
        "request_digest": request.digest(),
        "plan_digest": result.plan.digest(),
        "requested_model": bundle.requested_model,
        "returned_model": bundle.returned_model,
        "response_id": bundle.response_id,
    }
