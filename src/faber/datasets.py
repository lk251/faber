"""Trajectory dataset export and evaluation helpers."""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from faber import schemas
from faber.canonical_json import canonical_json
from faber.data_rights import DatasetExportPolicy, record_export_allowed
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.redaction import record_trace_export_allowed
from faber.schema_registry import schema_versions_in_records
from faber.trajectories import Trajectory

TrajectoryRecord = dict[str, object]
Redactor = Callable[[TrajectoryRecord], TrajectoryRecord]


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    source_paths: list[str]
    input_record_count: int
    record_count: int
    excluded_record_count: int
    withdrawn_excluded_count: int
    schema_versions: list[str]
    accepted_count: int
    rejected_count: int
    total_cost_minor_units: int
    total_reward_minor_units: int
    total_margin_minor_units: int
    jsonl_digest: str
    quality_issues: list[dict[str, object]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.DATASET_MANIFEST

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "dataset_id": self.dataset_id,
            "created_at": self.created_at,
            "source_paths": self.source_paths,
            "input_record_count": self.input_record_count,
            "record_count": self.record_count,
            "excluded_record_count": self.excluded_record_count,
            "withdrawn_excluded_count": self.withdrawn_excluded_count,
            "schema_versions": self.schema_versions,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "total_cost_minor_units": self.total_cost_minor_units,
            "total_reward_minor_units": self.total_reward_minor_units,
            "total_margin_minor_units": self.total_margin_minor_units,
            "jsonl_digest": self.jsonl_digest,
            "quality_issues": self.quality_issues,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def trajectory_record(trajectory: Trajectory | TrajectoryRecord) -> TrajectoryRecord:
    if isinstance(trajectory, Trajectory):
        return trajectory.to_dict()
    return copy.deepcopy(trajectory)


def assign_split(record_id: str, *, train: int = 80, validation: int = 10, test: int = 10) -> str:
    if train + validation + test != 100:
        raise ValueError("train, validation, and test percentages must sum to 100")
    bucket = int(sha256_digest(record_id).removeprefix("sha256:")[:8], 16) % 100
    if bucket < train:
        return "train"
    if bucket < train + validation:
        return "validation"
    return "test"


def redact_fields(
    record: TrajectoryRecord,
    field_paths: list[str],
    *,
    replacement: object = "[redacted]",
) -> TrajectoryRecord:
    redacted = copy.deepcopy(record)
    for field_path in field_paths:
        parts = field_path.split(".")
        current: Any = redacted
        for part in parts[:-1]:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if isinstance(current, dict) and parts[-1] in current:
            current[parts[-1]] = replacement
    return redacted


def quality_issues(record: TrajectoryRecord) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for field_name in ["receipt", "router_decision", "cost_metadata", "outcome"]:
        if not record.get(field_name):
            issues.append({"field": field_name, "issue": "missing"})
    digest = record.get("digest")
    payload = record.get("payload")
    if isinstance(digest, str) and isinstance(payload, dict) and sha256_digest(payload) != digest:
        issues.append({"field": "digest", "issue": "mismatch"})
    return issues


def summarize_records(records: list[TrajectoryRecord]) -> dict[str, int]:
    accepted = 0
    rejected = 0
    total_cost = 0
    total_reward = 0
    for record in records:
        outcome = record.get("outcome")
        receipt = record.get("receipt")
        if outcome == "accepted" or (isinstance(receipt, dict) and receipt.get("accepted") is True):
            accepted += 1
        elif outcome == "rejected" or (
            isinstance(receipt, dict) and receipt.get("accepted") is False
        ):
            rejected += 1
        cost_metadata = record.get("cost_metadata")
        if isinstance(cost_metadata, dict):
            total_cost += sum(
                value
                for key, value in cost_metadata.items()
                if key.endswith("_minor_units") and isinstance(value, int)
            )
        settlement = record.get("settlement")
        if isinstance(settlement, dict):
            amount = settlement.get("amount")
            if isinstance(amount, dict) and isinstance(amount.get("minor_units"), int):
                total_reward += amount["minor_units"]
    return {
        "record_count": len(records),
        "accepted_count": accepted,
        "rejected_count": rejected,
        "total_cost_minor_units": total_cost,
        "total_reward_minor_units": total_reward,
        "total_margin_minor_units": total_reward - total_cost,
    }


def export_trajectories_jsonl(
    trajectories: Sequence[Trajectory | TrajectoryRecord],
    out_path: str | Path,
    *,
    source_paths: list[str] | None = None,
    redactor: Redactor | None = None,
    dataset_id: str | None = None,
    require_rl_grade: bool = False,
    require_training_eligible: bool = False,
    minimum_quality_tier: str | None = None,
    export_policy: DatasetExportPolicy | None = None,
    exclude_withdrawn: bool = True,
) -> DatasetManifest:
    from faber.data_rights import record_withdrawn_for
    from faber.trajectory_quality import annotate_trajectory_record, filter_training_records

    records = [
        annotate_trajectory_record(trajectory_record(trajectory)) for trajectory in trajectories
    ]
    input_record_count = len(records)
    withdrawal_purpose = export_policy.purpose if export_policy is not None else "training"
    withdrawn_excluded_count = 0
    if exclude_withdrawn and withdrawal_purpose != "audit":
        active_records: list[TrajectoryRecord] = []
        for record in records:
            if record_withdrawn_for(record, withdrawal_purpose):
                withdrawn_excluded_count += 1
            else:
                active_records.append(record)
        records = active_records
    if require_rl_grade or require_training_eligible or minimum_quality_tier is not None:
        records = filter_training_records(
            records,
            require_rl_grade=require_rl_grade,
            require_training_eligible=require_training_eligible,
            minimum_quality_tier=minimum_quality_tier,
        )
    if export_policy is not None:
        records = [
            record
            for record in records
            if record_export_allowed(record, export_policy)
            and record_trace_export_allowed(record, export_policy)
        ]
    if redactor is not None:
        records = [redactor(record) for record in records]
    lines = [canonical_json(record) for record in records]
    text = "\n".join(lines) + ("\n" if lines else "")
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    summary = summarize_records(records)
    all_quality_issues: list[dict[str, object]] = []
    for record in records:
        for issue in quality_issues(record):
            all_quality_issues.append({"record_id": record.get("id"), **issue})
    return DatasetManifest(
        dataset_id=dataset_id or new_id("dataset"),
        source_paths=source_paths or [],
        input_record_count=input_record_count,
        record_count=summary["record_count"],
        excluded_record_count=input_record_count - summary["record_count"],
        withdrawn_excluded_count=withdrawn_excluded_count,
        schema_versions=schema_versions_in_records(records),
        accepted_count=summary["accepted_count"],
        rejected_count=summary["rejected_count"],
        total_cost_minor_units=summary["total_cost_minor_units"],
        total_reward_minor_units=summary["total_reward_minor_units"],
        total_margin_minor_units=summary["total_margin_minor_units"],
        jsonl_digest=sha256_digest(text.encode("utf-8")),
        quality_issues=all_quality_issues,
    )


def read_trajectory_jsonl(path: str | Path) -> list[TrajectoryRecord]:
    records: list[TrajectoryRecord] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        import json

        parsed = json.loads(line)
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def dataset_summary(path: str | Path) -> dict[str, object]:
    records = read_trajectory_jsonl(path)
    summary: dict[str, object] = dict(summarize_records(records))
    summary["jsonl_digest"] = sha256_digest(Path(path).read_bytes())
    summary["quality_issues"] = [
        {"record_id": record.get("id"), **issue}
        for record in records
        for issue in quality_issues(record)
    ]
    return summary
