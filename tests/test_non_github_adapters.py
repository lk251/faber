from pathlib import Path

from faber.adapters.local import (
    LocalFilesystemSubmissionAdapter,
    LocalJsonTaskSource,
    artifact_reference_from_path,
)
from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.sources import ArtifactReference, ExternalTaskReference
from faber.trajectory_quality import validate_trajectory_quality

CREATED_AT = "2026-01-01T00:00:00Z"


def _task_file(tmp_path: Path) -> Path:
    path = tmp_path / "task.json"
    path.write_text(
        canonical_json(
            {
                "title": "Render a local report",
                "description": "Produce and verify a deterministic local report.",
                "requirements": ["Write report.txt", "Pass the local verifier"],
                "verifier_ids": ["verifier.local.report"],
                "environment": {"platform": "windows", "snapshot": "fixture"},
                "trajectory_requirement": {
                    "minimum_quality_tier": "trace",
                    "require_rl_grade": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_local_json_task_becomes_task_contract(tmp_path: Path) -> None:
    path = _task_file(tmp_path)
    reference = ExternalTaskReference(
        source="local_json",
        external_id="report-task",
        locator=str(path),
    )

    contract = LocalJsonTaskSource().load(reference)

    assert contract.title == "Render a local report"
    assert contract.task_source == "local.json"
    assert contract.source_reference["external_id"] == "report-task"
    assert contract.trajectory_requirement["minimum_quality_tier"] == "trace"


def test_local_patch_and_non_code_artifact_become_attempt(tmp_path: Path) -> None:
    contract = LocalJsonTaskSource().load(
        ExternalTaskReference(
            source="local_json",
            external_id="report-task",
            locator=str(_task_file(tmp_path)),
        )
    )
    patch_path = tmp_path / "change.patch"
    patch_path.write_text("diff --git a/report.txt b/report.txt\n", encoding="utf-8")
    report_path = tmp_path / "report.txt"
    report_path.write_text("verified report\n", encoding="utf-8")
    artifacts = [
        artifact_reference_from_path(patch_path, kind="patch"),
        artifact_reference_from_path(report_path, kind="non_code"),
    ]

    attempt = LocalFilesystemSubmissionAdapter().submit(
        contract,
        worker_id="worker.local",
        base_revision="workspace-before",
        summary="Produced the requested report.",
        artifacts=artifacts,
        attempt_id="attempt_local_report",
        created_at=CREATED_AT,
    )

    assert attempt.id == "attempt_local_report"
    assert attempt.metadata["artifacts"][0]["kind"] == "patch"
    assert attempt.metadata["artifacts"][1]["kind"] == "non_code"
    assert attempt.patch_digest == sha256_digest([artifact.to_dict() for artifact in artifacts])


def test_non_github_attempt_can_satisfy_trajectory_requirement(tmp_path: Path) -> None:
    contract = LocalJsonTaskSource().load(
        ExternalTaskReference(
            source="local_json",
            external_id="report-task",
            locator=str(_task_file(tmp_path)),
        )
    )
    artifact = ArtifactReference(
        kind="generated_output",
        locator=str(tmp_path / "report.txt"),
        digest=sha256_digest("report"),
    )
    attempt = LocalFilesystemSubmissionAdapter().submit(
        contract,
        worker_id="worker.local",
        base_revision="workspace-before",
        summary="Produced report.",
        artifacts=[artifact],
        attempt_id="attempt_local_report",
        created_at=CREATED_AT,
    )
    record = {
        "schema": "faber.trajectory.v1",
        "id": "trajectory_local_report",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "receipt": {
            "id": "verification-receipt_local_report",
            "accepted": True,
            "task_contract_id": contract.id,
            "attempt_id": attempt.id,
        },
        "router_decision": {"policy_name": "local"},
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 10},
        "latency_metadata": {"work_seconds": 5},
        "reward_metadata": {"currency": "EUR", "reward_minor_units": 100},
        "outcome": "accepted",
        "attempt_manifest": {
            "id": "attempt-manifest_local_report",
            "evidence_level": {"level": 2},
            "model_metadata": {"disclosure": "coarse"},
            "harness_metadata": {"family": "local"},
            "environment_metadata": {
                "platform": "windows",
                "repository_snapshot_digest": sha256_digest("workspace"),
            },
            "training_consent": {
                "id": "trajectory-consent_local_report",
                "training_use_allowed": True,
                "allowed_uses": ["rl"],
            },
        },
        "trace_manifest": {
            "evidence_level": {"level": 2},
            "trace_event_count": 3,
            "trace_jsonl_digest": sha256_digest("trace"),
            "included_event_types": [
                "context.read",
                "tool.call",
                "verification.result",
            ],
            "provenance": {"adapter": "local"},
        },
    }

    report = validate_trajectory_quality(record)

    assert report.is_rl_grade is True
    assert report.meets_requirement is True


def test_local_core_records_have_no_github_specific_fields(tmp_path: Path) -> None:
    contract = LocalJsonTaskSource().load(
        ExternalTaskReference(
            source="local_json",
            external_id="report-task",
            locator=str(_task_file(tmp_path)),
        )
    )
    serialized = canonical_json(contract.to_dict())

    for field in ["pull_request_number", "issue_number", "installation_id", "html_url"]:
        assert field not in serialized
