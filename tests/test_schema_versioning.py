from pathlib import Path

import pytest

from faber.datasets import export_trajectories_jsonl
from faber.errors import ProtocolVersionError
from faber.platform_fixtures import cross_platform_harness_fixtures
from faber.schema_registry import (
    CompatibilityPolicy,
    SchemaDescriptor,
    SchemaRegistry,
    protocol_schema_registry,
    upgrade_record,
)
from faber.schemas import TRAJECTORY


def _record() -> dict[str, object]:
    return cross_platform_harness_fixtures()[0].trajectory_record


def test_known_schema_validates() -> None:
    report = protocol_schema_registry().validate(TRAJECTORY)

    assert report.known is True
    assert report.compatible is True
    assert report.action == "read-current"
    assert report.warnings == []


def test_unknown_future_schema_warns_or_fails_by_policy() -> None:
    registry = protocol_schema_registry()

    with pytest.raises(ProtocolVersionError, match="future schema version"):
        registry.validate("faber.trajectory.v99")

    report = registry.validate(
        "faber.trajectory.v99",
        policy=CompatibilityPolicy.WARN,
    )
    assert report.known is False
    assert report.compatible is False
    assert report.action == "preserve-opaque"
    assert "future schema version" in report.warnings[0]


def test_dataset_manifest_records_nested_schema_versions(tmp_path: Path) -> None:
    manifest = export_trajectories_jsonl([_record()], tmp_path / "dataset.jsonl")

    assert "faber.trajectory.v1" in manifest.schema_versions
    assert "faber.task_contract.v1" in manifest.schema_versions
    assert "faber.attempt.v1" in manifest.schema_versions
    assert "faber.verification_receipt.v1" in manifest.schema_versions
    assert "faber.trace_manifest.v1" in manifest.schema_versions
    assert "faber.dataset_manifest.v1" == manifest.schema


def test_current_schema_upgrade_is_noop_and_preserves_digest() -> None:
    record = _record()

    result = upgrade_record(record)

    assert result.upgraded is False
    assert result.source_schema == TRAJECTORY
    assert result.target_schema == TRAJECTORY
    assert result.source_digest == result.target_digest
    assert result.record == record
    assert result.record is not record


def test_deprecated_schema_returns_explicit_warning() -> None:
    registry = SchemaRegistry(
        [
            SchemaDescriptor(
                schema_id="faber.example.v1",
                family="example",
                version=1,
                deprecated=True,
                deprecation_message="Use faber.example.v2 after migration support lands.",
            )
        ]
    )

    report = registry.validate("faber.example.v1")

    assert report.compatible is True
    assert report.action == "read-with-deprecation-warning"
    assert report.warnings == ["Use faber.example.v2 after migration support lands."]
