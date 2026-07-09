"""Bounded local store and dataset performance smoke harness."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.datasets import export_trajectories_jsonl
from faber.digests import sha256_digest
from faber.events import MarketEvent
from faber.money import Money
from faber.platform_fixtures import cross_platform_harness_fixtures
from faber.store import (
    save_lifecycle_events_batch,
    save_records_batch,
    store_summary,
)
from faber.validation import require_non_empty_string

CREATED_AT = "2026-01-01T00:00:00Z"


@dataclass(frozen=True)
class GeneratedProtocolRecord:
    """Small adapter for storing generated canonical payloads in smoke tests."""

    payload: dict[str, object]

    @property
    def id(self) -> str:
        value = self.payload.get("id")
        return require_non_empty_string(value, "payload.id")

    @property
    def created_at(self) -> str:
        value = self.payload.get("created_at")
        return require_non_empty_string(value, "payload.created_at")

    def to_dict(self) -> dict[str, object]:
        return copy.deepcopy(self.payload)

    def digest(self) -> str:
        return sha256_digest(self.payload)


@dataclass(frozen=True)
class LocalPerformanceSmokeReport:
    generated_record_count: int
    store_write_seconds: float
    dataset_export_seconds: float
    elapsed_seconds: float
    store_summary: dict[str, object]
    dataset_summary: dict[str, int]
    training_eligible_record_count: int
    duplicate_record_attempt_count: int
    duplicate_record_insert_count: int
    duplicate_event_attempt_count: int
    lifecycle_event_count_after_duplicates: int
    dataset_output_bytes: int
    store_path: str
    dataset_path: str
    external_database: bool = False
    hosted_service: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_record_count": self.generated_record_count,
            "store_write_seconds": self.store_write_seconds,
            "dataset_export_seconds": self.dataset_export_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "store_summary": self.store_summary,
            "dataset_summary": self.dataset_summary,
            "training_eligible_record_count": self.training_eligible_record_count,
            "duplicate_record_attempt_count": self.duplicate_record_attempt_count,
            "duplicate_record_insert_count": self.duplicate_record_insert_count,
            "duplicate_event_attempt_count": self.duplicate_event_attempt_count,
            "lifecycle_event_count_after_duplicates": (
                self.lifecycle_event_count_after_duplicates
            ),
            "dataset_output_bytes": self.dataset_output_bytes,
            "store_path": self.store_path,
            "dataset_path": self.dataset_path,
            "external_database": self.external_database,
            "hosted_service": self.hosted_service,
        }


def run_local_performance_smoke(
    root: str | Path,
    *,
    contract_count: int = 300,
    attempt_count: int = 500,
    event_count: int = 1_000,
    trajectory_count: int = 250,
) -> LocalPerformanceSmokeReport:
    """Measure a realistic development corpus without external infrastructure."""

    for name, value in [
        ("contract_count", contract_count),
        ("attempt_count", attempt_count),
        ("event_count", event_count),
        ("trajectory_count", trajectory_count),
    ]:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    output = Path(root)
    output.mkdir(parents=True, exist_ok=True)
    store_path = output / "performance.sqlite3"
    dataset_path = output / "training.jsonl"
    contracts = _contracts(contract_count)
    attempts = _attempts(attempt_count, contracts)
    events = _events(event_count, contracts, attempts)
    trajectory_payloads = _trajectory_payloads(trajectory_count)
    trajectory_records = [GeneratedProtocolRecord(payload) for payload in trajectory_payloads]

    started = perf_counter()
    store_started = perf_counter()
    save_records_batch(store_path, "task_contract", contracts)
    save_records_batch(store_path, "attempt", attempts)
    save_lifecycle_events_batch(store_path, events)
    save_records_batch(store_path, "trajectory", trajectory_records)
    duplicate_records = save_records_batch(store_path, "task_contract", contracts)
    save_lifecycle_events_batch(store_path, events)
    store_write_seconds = perf_counter() - store_started

    dataset_started = perf_counter()
    dataset_manifest = export_trajectories_jsonl(
        trajectory_payloads,
        dataset_path,
        dataset_id="dataset_local_performance_smoke",
        require_rl_grade=True,
        require_training_eligible=True,
    )
    dataset_export_seconds = perf_counter() - dataset_started
    elapsed_seconds = perf_counter() - started
    summary = store_summary(store_path)
    lifecycle_count = summary.get("lifecycle_event_count")
    if not isinstance(lifecycle_count, int):
        lifecycle_count = 0
    dataset_summary = {
        "record_count": dataset_manifest.record_count,
        "accepted_count": dataset_manifest.accepted_count,
        "rejected_count": dataset_manifest.rejected_count,
        "total_cost_minor_units": dataset_manifest.total_cost_minor_units,
        "total_reward_minor_units": dataset_manifest.total_reward_minor_units,
        "total_margin_minor_units": dataset_manifest.total_margin_minor_units,
    }
    return LocalPerformanceSmokeReport(
        generated_record_count=(
            contract_count + attempt_count + event_count + trajectory_count
        ),
        store_write_seconds=store_write_seconds,
        dataset_export_seconds=dataset_export_seconds,
        elapsed_seconds=elapsed_seconds,
        store_summary=summary,
        dataset_summary=dataset_summary,
        training_eligible_record_count=dataset_manifest.record_count,
        duplicate_record_attempt_count=len(duplicate_records),
        duplicate_record_insert_count=sum(result.inserted for result in duplicate_records),
        duplicate_event_attempt_count=len(events),
        lifecycle_event_count_after_duplicates=lifecycle_count,
        dataset_output_bytes=dataset_path.stat().st_size,
        store_path=str(store_path),
        dataset_path=str(dataset_path),
    )


def _contracts(count: int) -> list[TaskContract]:
    return [
        TaskContract(
            id=f"task-contract_performance_{index:04d}",
            created_at=CREATED_AT,
            title=f"Performance fixture task {index}",
            description="Generated local store performance fixture.",
            requirements=["Remain deterministic and local."],
            verifier_ids=["verifier.performance.local"],
            task_source="local.performance",
            repository="local/performance-fixtures",
        )
        for index in range(count)
    ]


def _attempts(count: int, contracts: list[TaskContract]) -> list[Attempt]:
    return [
        Attempt(
            id=f"attempt_performance_{index:04d}",
            created_at=CREATED_AT,
            task_contract_id=contracts[index % len(contracts)].id,
            worker_id=f"worker.performance.{index % 20:02d}",
            base_revision="performance-base",
            candidate_revision=f"performance-candidate-{index:04d}",
            summary=f"Generated attempt {index}.",
            patch_digest=sha256_digest({"performance_attempt": index}),
        )
        for index in range(count)
    ]


def _events(
    count: int,
    contracts: list[TaskContract],
    attempts: list[Attempt],
) -> list[MarketEvent]:
    return [
        MarketEvent(
            id=f"market-event_performance_{index:05d}",
            created_at=CREATED_AT,
            event_type="attempt.observed" if index % 2 else "contract.observed",
            subject_id=(
                attempts[index % len(attempts)].id
                if index % 2
                else contracts[index % len(contracts)].id
            ),
            actor_id="runner.performance.local",
            payload={"sequence": index, "fake_data": True},
        )
        for index in range(count)
    ]


def _trajectory_payloads(count: int) -> list[dict[str, object]]:
    base = next(
        fixture.trajectory_record
        for fixture in cross_platform_harness_fixtures()
        if fixture.platform_family == "windows"
    )
    records: list[dict[str, object]] = []
    for index in range(count):
        record = copy.deepcopy(base)
        record["id"] = f"trajectory_performance_{index:04d}"
        record["settlement"] = {
            "id": f"settlement_performance_{index:04d}",
            "status": "settled_locally",
            "amount": Money("EUR", 1000).to_dict(),
        }
        records.append(record)
    return records
