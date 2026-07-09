from copy import deepcopy
from pathlib import Path

from faber.data_rights import (
    ConsentGrant,
    DataLicense,
    DatasetExportPolicy,
    DeletionRequest,
    RetentionPolicy,
    TrainingUsePolicy,
    audit_retained_record,
    record_export_allowed,
    resolve_training_use_policy,
)
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.traces import TrajectoryConsent
from faber.trajectories import build_demo_trajectory

CREATED_AT = "2026-01-01T00:00:00Z"


def _consent(*, allowed: bool) -> TrajectoryConsent:
    uses = ["rl", "supervised", "router"] if allowed else []
    return TrajectoryConsent(
        id=f"trajectory-consent_{'allowed' if allowed else 'denied'}",
        created_at=CREATED_AT,
        training_use_allowed=allowed,
        allowed_uses=uses,
        license_ref="fixture-license",
        grants=[
            ConsentGrant(
                party="solver_operator",
                actor_ref="worker_fixture",
                allowed_uses=uses,
                granted_at=CREATED_AT,
                provenance="self_attested",
            ),
            ConsentGrant(
                party="repo_owner_customer",
                actor_ref="repo-owner_fixture",
                allowed_uses=uses,
                granted_at=CREATED_AT,
                provenance="repo_owner_verified",
            ),
        ],
    )


def _record(*, allowed: bool, visibility: str = "private") -> dict[str, object]:
    record = build_demo_trajectory().to_dict()
    record["attempt_manifest"] = {"training_consent": _consent(allowed=allowed).to_dict()}
    record["contract"]["repository_training_policy"] = TrainingUsePolicy(
        id="training-policy_repository",
        created_at=CREATED_AT,
        allowed_uses=["rl", "supervised", "router"],
        visibility=visibility,
        public_export_allowed=visibility == "public",
    ).to_dict()
    return record


def test_training_ineligible_trajectory_is_excluded_from_training_export(
    tmp_path: Path,
) -> None:
    eligible = _record(allowed=True)
    ineligible = _record(allowed=False)
    ineligible["id"] = "trajectory_training_denied"
    out_path = tmp_path / "training.jsonl"

    manifest = export_trajectories_jsonl(
        [eligible, ineligible],
        out_path,
        export_policy=DatasetExportPolicy(purpose="rl"),
    )

    assert manifest.record_count == 1
    assert [record["id"] for record in read_trajectory_jsonl(out_path)] == [
        "trajectory_demo"
    ]


def test_audit_only_record_remains_available_for_verification_history() -> None:
    record = _record(allowed=False)
    record["contract"]["repository_training_policy"] = TrainingUsePolicy(
        allowed_uses=[],
        visibility="private",
        audit_retention_allowed=True,
    ).to_dict()

    assert record_export_allowed(record, DatasetExportPolicy(purpose="audit")) is True
    assert record_export_allowed(record, DatasetExportPolicy(purpose="rl")) is False


def test_task_policy_overrides_repository_default_when_stricter() -> None:
    repository = TrainingUsePolicy(
        allowed_uses=["rl", "supervised", "router"],
        visibility="public",
        public_export_allowed=True,
    )
    task = TrainingUsePolicy(
        allowed_uses=["supervised"],
        visibility="private",
        public_export_allowed=False,
    )

    resolved = resolve_training_use_policy(repository, task)

    assert resolved.allowed_uses == ["supervised"]
    assert resolved.visibility == "private"
    assert resolved.public_export_allowed is False


def test_public_dataset_export_excludes_private_records(tmp_path: Path) -> None:
    public = _record(allowed=True, visibility="public")
    private = _record(allowed=True, visibility="private")
    private["id"] = "trajectory_private"
    out_path = tmp_path / "public.jsonl"

    manifest = export_trajectories_jsonl(
        [public, private],
        out_path,
        export_policy=DatasetExportPolicy(purpose="rl", public=True),
    )

    assert manifest.record_count == 1
    assert read_trajectory_jsonl(out_path)[0]["id"] == "trajectory_demo"


def test_deletion_policy_preserves_audit_critical_receipt() -> None:
    record = _record(allowed=False)
    original_receipt = deepcopy(record["receipt"])
    retention = RetentionPolicy(
        retention_class="audit_only",
        private_content_days=0,
        preserve_audit_receipts=True,
    )
    request = DeletionRequest(
        trajectory_id=str(record["id"]),
        requested_by="worker_fixture",
        scopes=["private_trace", "training"],
        requested_at=CREATED_AT,
    )

    retained = audit_retained_record(record, request=request, policy=retention)

    assert retained["receipt"] == original_receipt
    assert retained["attempt_manifest"] is None
    assert retained["deletion"]["request_digest"] == request.digest()
    assert DataLicense.audit_only().allows("audit") is True
    assert DataLicense.audit_only().allows("rl") is False
