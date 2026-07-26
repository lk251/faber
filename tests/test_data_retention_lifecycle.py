from copy import deepcopy
from pathlib import Path

from faber.data_rights import (
    DatasetExportPolicy,
    DatasetWithdrawal,
    DeletionRequest,
    RetentionPolicy,
    TrainingUsePolicy,
    apply_dataset_withdrawal,
    apply_deletion_request,
)
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.platform_fixtures import cross_platform_harness_fixtures

CREATED_AT = "2026-07-09T00:00:00Z"


def _record() -> dict[str, object]:
    fixture = next(
        item for item in cross_platform_harness_fixtures() if item.platform_family == "windows"
    )
    record = deepcopy(fixture.trajectory_record)
    contract = record["contract"]
    assert isinstance(contract, dict)
    contract["repository_training_policy"] = TrainingUsePolicy(
        id="training-use-policy_retention_fixture",
        created_at=CREATED_AT,
        allowed_uses=["rl", "supervised", "router"],
        required_consent_parties=[],
        visibility="private",
    ).to_dict()
    return record


def _withdrawal(trajectory_id: str) -> DatasetWithdrawal:
    return DatasetWithdrawal(
        id="dataset-withdrawal_retention_fixture",
        trajectory_id=trajectory_id,
        requested_by="worker.retention.fixture",
        reason="Withdraw synthetic episode from future training exports.",
        effective_at=CREATED_AT,
        scopes=["training"],
    )


def test_withdrawn_trajectory_is_excluded_from_training_export(tmp_path: Path) -> None:
    eligible = _record()
    withdrawn_source = _record()
    withdrawn_source["id"] = "trajectory_fixture_windows_withdrawn"
    withdrawn = apply_dataset_withdrawal(
        withdrawn_source,
        _withdrawal("trajectory_fixture_windows_withdrawn"),
    )
    out_path = tmp_path / "training.jsonl"

    manifest = export_trajectories_jsonl(
        [eligible, withdrawn],
        out_path,
        export_policy=DatasetExportPolicy(purpose="rl"),
    )

    assert manifest.record_count == 1
    assert manifest.withdrawn_excluded_count == 1
    assert [record["id"] for record in read_trajectory_jsonl(out_path)] == [
        "trajectory_fixture_windows"
    ]


def test_private_trace_deletion_preserves_minimal_audit_receipt_reference() -> None:
    record = _record()
    original_receipt = deepcopy(record["receipt"])
    request = DeletionRequest(
        id="deletion-request_retention_fixture",
        trajectory_id=str(record["id"]),
        requested_by="worker.retention.fixture",
        scopes=["private_trace", "training"],
        requested_at=CREATED_AT,
    )
    policy = RetentionPolicy(
        id="retention-policy_audit_fixture",
        created_at=CREATED_AT,
        retention_class="audit_only",
        private_content_days=0,
        preserve_audit_receipts=True,
    )

    retained, report, tombstone = apply_deletion_request(
        record,
        request=request,
        policy=policy,
        completed_at=CREATED_AT,
    )

    assert retained["receipt"] == original_receipt
    assert retained["attempt_manifest"] is None
    assert retained["trace_manifest"] is None
    assert tombstone.preserved_audit_references["receipt_id"] == original_receipt["id"]
    assert tombstone.preserved_audit_references["receipt_digest"].startswith("sha256:")
    assert report.removed_field_digests["trace_manifest"].startswith("sha256:")


def test_deletion_report_and_tombstone_digests_are_stable() -> None:
    record = _record()
    request = DeletionRequest(
        id="deletion-request_stable",
        trajectory_id=str(record["id"]),
        requested_by="worker.retention.fixture",
        scopes=["private_trace", "training"],
        requested_at=CREATED_AT,
    )
    policy = RetentionPolicy(
        id="retention-policy_stable",
        created_at=CREATED_AT,
        retention_class="audit_only",
        private_content_days=0,
    )

    left = apply_deletion_request(
        record,
        request=request,
        policy=policy,
        completed_at=CREATED_AT,
    )
    right = apply_deletion_request(
        record,
        request=request,
        policy=policy,
        completed_at=CREATED_AT,
    )

    assert left[1].digest() == right[1].digest()
    assert left[2].digest() == right[2].digest()
    assert left[1].original_record_digest != left[1].retained_record_digest


def test_dataset_manifest_records_all_exclusion_counts(tmp_path: Path) -> None:
    eligible = _record()
    withdrawn = deepcopy(eligible)
    withdrawn["id"] = "trajectory_fixture_windows_withdrawn"
    withdrawn = apply_dataset_withdrawal(
        withdrawn,
        _withdrawal("trajectory_fixture_windows_withdrawn"),
    )

    manifest = export_trajectories_jsonl(
        [eligible, withdrawn],
        tmp_path / "training.jsonl",
        export_policy=DatasetExportPolicy(purpose="rl"),
    )

    assert manifest.input_record_count == 2
    assert manifest.record_count == 1
    assert manifest.excluded_record_count == 1
    assert manifest.withdrawn_excluded_count == 1
    assert manifest.to_dict()["withdrawn_excluded_count"] == 1
