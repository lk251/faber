"""Canonical JSONL features and labels for future router training."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.trajectory_quality import trajectory_record, validate_trajectory_quality

NEGATIVE_OUTCOMES = {
    "rejected",
    "declined",
    "timeout",
    "verifier_failure",
    "failed",
    "abandoned",
}


@dataclass(frozen=True)
class RouterDatasetManifest:
    record_count: int
    negative_count: int
    excluded_for_consent_count: int
    jsonl_digest: str
    schema: str = "faber.router_dataset_manifest.v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "record_count": self.record_count,
            "negative_count": self.negative_count,
            "excluded_for_consent_count": self.excluded_for_consent_count,
            "jsonl_digest": self.jsonl_digest,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def router_training_record(trajectory: object) -> dict[str, object]:
    record = trajectory_record(trajectory)
    trajectory_id = str(record.get("id", "trajectory_unknown"))
    created_at = record.get("created_at")
    report = validate_trajectory_quality(
        record,
        report_id=f"trajectory-validation-report_{trajectory_id}",
        created_at=(
            created_at
            if isinstance(created_at, str) and created_at
            else "1970-01-01T00:00:00Z"
        ),
    )
    contract = _mapping(record.get("contract"))
    attempt = _mapping(record.get("attempt"))
    receipt = _mapping(record.get("receipt"))
    router = _mapping(record.get("router_decision"))
    worker = _mapping(record.get("worker_profile"))
    manifest = _mapping(record.get("attempt_manifest"))
    if not manifest:
        attempt_metadata = _mapping(attempt.get("metadata"))
        evidence = _mapping(attempt_metadata.get("faber_attempt_manifest"))
        manifest = _mapping(evidence.get("manifest"))
    model = _mapping(manifest.get("model_metadata"))
    harness = _mapping(manifest.get("harness_metadata"))
    environment = _mapping(manifest.get("environment_metadata"))
    verification_policy = _mapping(_mapping(contract.get("environment")).get("verification_policy"))
    cost_minor_units = _sum_minor_units(_mapping(record.get("cost_metadata")))
    reward_minor_units = _reward_minor_units(record)
    value_per_euro_milli = (
        reward_minor_units * 1000 // max(cost_minor_units, 1)
        if reward_minor_units is not None
        else None
    )
    outcome = str(
        record.get("outcome")
        or ("accepted" if receipt.get("accepted") is True else "rejected")
    )
    selected_worker_id = router.get("selected_worker_id") or attempt.get("worker_id")
    selected_verifier_id = receipt.get("verifier_id")
    review_metadata = _mapping(record.get("review_metadata"))
    return {
        "schema": "faber.router_training_record.v1",
        "trajectory_id": trajectory_id,
        "trajectory_digest": sha256_digest(record),
        "trajectory_quality_tier": report.quality_tier,
        "label_strength": "strong" if report.is_rl_grade else "weak",
        "training_consent": report.training_eligibility.to_dict(),
        "features": {
            "task": {
                "task_contract_id": contract.get("id"),
                "task_source": contract.get("task_source"),
                "requirement_count": len(_string_list(contract.get("requirements"))),
                "repository_present": isinstance(contract.get("repository"), str),
            },
            "worker": {
                "worker_id": attempt.get("worker_id"),
                "capabilities": _string_list(worker.get("capabilities")),
                "metadata_trust_level": worker.get("metadata_trust_level"),
            },
            "solver": {
                "model_family": model.get("family"),
                "model_disclosure": model.get("disclosure"),
                "harness_family": harness.get("family"),
                "harness_version": harness.get("version"),
                "platform": environment.get("platform"),
                "reproducibility_level": environment.get("reproducibility_level"),
            },
            "verifier_policy": {
                "verifier_ids": _string_list(contract.get("verifier_ids")),
                "human_review": verification_policy.get("human_review"),
                "advisory_ranking": verification_policy.get("advisory_ranking"),
                "minimum_trajectory_tier": _mapping(
                    contract.get("trajectory_requirement")
                ).get("minimum_quality_tier"),
            },
        },
        "labels": {
            "selected_worker_id": selected_worker_id,
            "selected_verifier_id": selected_verifier_id,
            "selected_budget_minor_units": _contract_budget_minor_units(contract),
            "outcome": outcome,
            "negative_example": outcome in NEGATIVE_OUTCOMES,
            "cost_minor_units": cost_minor_units,
            "reward_minor_units": reward_minor_units,
            "latency_seconds": _latency_seconds(record),
            "review_outcome": review_metadata.get("outcome"),
            "review_friction": review_metadata.get("friction"),
            "value_per_euro_milli": value_per_euro_milli,
        },
        "provenance": {
            "attempt_trust_level": manifest.get("trust_level"),
            "model_disclosure": model.get("disclosure"),
            "process_evidence": report.process_evidence.to_dict(),
            "quality_report_digest": report.digest(),
        },
    }


def export_router_training_jsonl(
    trajectories: Sequence[object],
    out_path: str | Path,
    *,
    require_training_consent: bool = True,
    include_negative: bool = True,
) -> RouterDatasetManifest:
    records: list[dict[str, object]] = []
    excluded_for_consent = 0
    for trajectory in trajectories:
        record = router_training_record(trajectory)
        consent = _mapping(record.get("training_consent"))
        allowed_uses = _string_list(consent.get("allowed_uses"))
        consent_allowed = consent.get("eligible") is True and (
            "all" in allowed_uses
            or "router" in allowed_uses
            or "supervised" in allowed_uses
        )
        if require_training_consent and not consent_allowed:
            excluded_for_consent += 1
            continue
        labels = _mapping(record.get("labels"))
        if not include_negative and labels.get("negative_example") is True:
            continue
        records.append(record)
    lines = [canonical_json(record) for record in records]
    text = "\n".join(lines) + ("\n" if lines else "")
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return RouterDatasetManifest(
        record_count=len(records),
        negative_count=sum(
            _mapping(record.get("labels")).get("negative_example") is True
            for record in records
        ),
        excluded_for_consent_count=excluded_for_consent,
        jsonl_digest=sha256_digest(text.encode("utf-8")),
    )


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _sum_minor_units(metadata: dict[str, object]) -> int:
    return sum(
        value
        for key, value in metadata.items()
        if key.endswith("_minor_units")
        and isinstance(value, int)
        and not isinstance(value, bool)
    )


def _reward_minor_units(record: dict[str, object]) -> int | None:
    reward = _mapping(record.get("reward_metadata"))
    value = reward.get("reward_minor_units")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    settlement = _mapping(record.get("settlement"))
    amount = _mapping(settlement.get("amount"))
    value = amount.get("minor_units")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _contract_budget_minor_units(contract: dict[str, object]) -> int | None:
    reward = _mapping(contract.get("reward"))
    value = reward.get("minor_units")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _latency_seconds(record: dict[str, object]) -> int | None:
    latency = _mapping(record.get("latency_metadata"))
    for field_name in ["total_seconds", "work_seconds"]:
        value = latency.get(field_name)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None
