from __future__ import annotations

import os
from pathlib import Path

import pytest

from faber.adapters.openai.proof_planner import (
    OpenAIProofPlannerBackend,
    build_planning_request,
)
from faber.adapters.openai.replay import (
    ReplayProofPlannerBackend,
    create_replay_bundle,
    write_replay_bundle,
)
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.proof_planning import PlannerCatalogEntryView

LIVE_ENABLED = os.environ.get("FABER_LIVE_OPENAI_TEST") == "1" and bool(
    os.environ.get("OPENAI_API_KEY", "").strip()
)

pytestmark = pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="requires FABER_LIVE_OPENAI_TEST=1 and OPENAI_API_KEY",
)


def test_guarded_live_openai_planner_writes_replay_bundle() -> None:
    contract = TaskContract(
        id="task-contract_live-openai-smoke",
        created_at="2026-07-17T00:00:00Z",
        title="Preserve empty input",
        description="Plan proof for a tiny public formatter fixture.",
        requirements=["Empty input is returned unchanged."],
        verifier_ids=["verifier.proof.catalog"],
        environment={
            "acceptance_criteria": ["Formatting empty input returns the empty string."],
            "rejection_criteria": ["Formatting empty input raises an exception."],
        },
    )
    attempt = Attempt(
        id="attempt_live-openai-smoke",
        created_at="2026-07-17T00:00:00Z",
        task_contract_id=contract.id,
        worker_id="worker.live-smoke",
        base_revision="base-revision",
        candidate_revision="candidate-revision",
        summary="Preserve empty input.",
        patch_digest=sha256_digest("tiny sanitized live smoke diff"),
    )
    catalog_entry = PlannerCatalogEntryView(
        id="proof.python.empty-input",
        version="1",
        description="Exercise an approved formatter input case.",
        parameter_schema={
            "type": "object",
            "properties": {
                "case": {
                    "type": "string",
                    "enum": ["empty"],
                }
            },
            "required": ["case"],
            "additionalProperties": False,
        },
        assertion_operators=["equals"],
        capability_limits={"max_cases": 1, "network": False},
        capability_digest=sha256_digest("live smoke catalog capability"),
    )
    request = build_planning_request(
        contract,
        attempt,
        diff_text="@@ -1 +1 @@\n-return None\n+return value\n",
        catalog_entries=[catalog_entry],
    )

    provider_response = OpenAIProofPlannerBackend().plan(request)
    bundle = create_replay_bundle(
        request,
        provider_response,
        created_at="2026-07-17T00:00:00Z",
    )
    replay_result = ReplayProofPlannerBackend(
        bundle,
        expected_bundle_digest=bundle.digest(),
    ).plan_result(request)
    destination = Path(".faber") / "openai-proof-planner-live-replay.json"
    write_replay_bundle(destination, bundle)

    assert replay_result.plan.model_run.mode == "replay"
    print(
        f"plan_digest={replay_result.plan.digest()} "
        f"response_id={bundle.response_id} "
        f"model_id={bundle.returned_model} "
        f"bundle={destination.as_posix()}"
    )
