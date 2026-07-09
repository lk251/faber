from pathlib import Path

from faber.adapters.github.funded_product_loop import run_fake_github_funded_product_loop
from faber.adapters.github.markers import (
    parse_contract_marker,
    parse_funded_issue_marker,
)
from faber.datasets import read_trajectory_jsonl


def test_full_fake_github_funded_product_loop_succeeds(tmp_path: Path) -> None:
    result = run_fake_github_funded_product_loop(tmp_path / "training.jsonl")

    assert parse_contract_marker(result.issue_text).contract_id == result.contract.id
    assert parse_funded_issue_marker(result.issue_text).budget_id == result.budget.id
    assert result.attempt.metadata["faber_attempt_manifest"]["status"] == "valid"
    assert {artifact.locator for artifact in result.artifact_references} == {
        ".faber/attempt.json",
        ".faber/trace.jsonl",
        ".faber/trace-manifest.json",
    }
    assert result.receipt.accepted is True
    assert result.budget_settlement is not None
    assert result.budget_release is None
    assert result.quality_report.is_rl_grade is True
    assert result.dataset_manifest.record_count == 1
    assert len(read_trajectory_jsonl(tmp_path / "training.jsonl")) == 1
    assert result.reconciliation.issues == []
    assert "Faber verification result: accepted" in result.maintainer_message
    assert "Next step: review the focused patch" in result.maintainer_message


def test_missing_trace_downgrades_trajectory_quality(tmp_path: Path) -> None:
    result = run_fake_github_funded_product_loop(
        tmp_path / "training.jsonl",
        include_trace=False,
    )

    assert result.quality_report.quality_tier == "manifest"
    assert result.quality_report.is_rl_grade is False
    assert result.quality_report.full_payout_eligible is False
    assert result.dataset_manifest.record_count == 0
    assert ".faber/trace.jsonl" not in result.pr_file_map


def test_missing_training_consent_excludes_dataset_export(tmp_path: Path) -> None:
    result = run_fake_github_funded_product_loop(
        tmp_path / "training.jsonl",
        training_consent=False,
    )

    assert result.quality_report.quality_tier == "trace"
    assert result.quality_report.training_eligibility.eligible is False
    assert result.dataset_manifest.record_count == 0
    assert read_trajectory_jsonl(tmp_path / "training.jsonl") == []


def test_rejected_verifier_prevents_settlement(tmp_path: Path) -> None:
    result = run_fake_github_funded_product_loop(
        tmp_path / "training.jsonl",
        verifier_passed=False,
    )

    assert result.receipt.accepted is False
    assert result.budget_settlement is None
    assert result.budget_release is not None
    assert result.reconciliation.settlement_count == 0
    assert result.reconciliation.release_count == 1
    assert result.settlement_blocked_reason == (
        "settlement requires an accepted authoritative receipt"
    )


def test_duplicate_webhook_like_events_and_ledger_operations_are_idempotent(
    tmp_path: Path,
) -> None:
    result = run_fake_github_funded_product_loop(tmp_path / "training.jsonl")

    assert result.delivery_attempt_count == 4
    assert result.delivery_count == 2
    assert result.budget_operation_attempt_count == 6
    assert len(result.budget_events) == 3
    assert [event.event_type for event in result.budget_events] == [
        "budget.registered",
        "budget.reserved",
        "budget.settled",
    ]
