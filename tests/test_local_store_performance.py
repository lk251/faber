from pathlib import Path

import pytest

from faber.performance import LocalPerformanceSmokeReport, run_local_performance_smoke


@pytest.fixture(scope="module")
def performance_report(tmp_path_factory) -> LocalPerformanceSmokeReport:
    root = tmp_path_factory.mktemp("local-performance")
    return run_local_performance_smoke(root)


def test_local_store_modest_batch_completes_quickly(
    performance_report: LocalPerformanceSmokeReport,
) -> None:
    assert performance_report.generated_record_count >= 2_000
    assert performance_report.elapsed_seconds < 30
    assert performance_report.store_write_seconds < 15
    assert performance_report.dataset_export_seconds < 15


def test_local_store_and_dataset_summary_metrics_are_correct(
    performance_report: LocalPerformanceSmokeReport,
) -> None:
    counts = performance_report.store_summary["record_counts"]
    assert counts == {
        "attempt": 500,
        "task_contract": 300,
        "trajectory": 250,
    }
    assert performance_report.store_summary["lifecycle_event_count"] == 1_000
    assert performance_report.dataset_summary == {
        "record_count": 250,
        "accepted_count": 250,
        "rejected_count": 0,
        "total_cost_minor_units": 6_250,
        "total_reward_minor_units": 250_000,
        "total_margin_minor_units": 243_750,
    }
    assert performance_report.training_eligible_record_count == 250


def test_duplicate_batch_inserts_do_not_grow_store(
    performance_report: LocalPerformanceSmokeReport,
) -> None:
    assert performance_report.duplicate_record_attempt_count == 300
    assert performance_report.duplicate_record_insert_count == 0
    assert performance_report.duplicate_event_attempt_count == 1_000
    assert performance_report.lifecycle_event_count_after_duplicates == 1_000


def test_performance_smoke_uses_only_local_paths(
    performance_report: LocalPerformanceSmokeReport,
) -> None:
    assert Path(performance_report.store_path).exists()
    assert Path(performance_report.dataset_path).exists()
    assert performance_report.external_database is False
    assert performance_report.hosted_service is False
