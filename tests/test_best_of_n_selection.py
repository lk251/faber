from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.selection import (
    AdvisoryRankingRecord,
    select_best_attempt,
    selection_dataset_records,
)
from faber.verifiers import VerifierRun

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_best_of_n",
        created_at=CREATED_AT,
        title="Best-of-N pilot task",
        description="Select the best candidate from deterministic fake attempts.",
        requirements=["Run local verifier.", "Keep rejected candidates as learning data."],
        verifier_ids=["verifier.best-of-n.local"],
        task_source="external_pilot_fixture",
        repository="example/repository",
        environment={"external_services": []},
        reward=Money("EUR", 1000),
    )


def _attempt(contract: TaskContract, suffix: str) -> Attempt:
    return Attempt(
        id=f"attempt_{suffix}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id=f"worker_{suffix}",
        base_revision="base",
        candidate_revision=f"candidate-{suffix}",
        summary=f"Candidate {suffix}",
        patch_digest=sha256_digest(f"patch:{suffix}"),
        tool_summaries=[{"tool": "pytest", "outcome": "passed"}],
    )


def _ranking(attempt_id: str, score_milli: int, uncertainty_milli: int) -> AdvisoryRankingRecord:
    return AdvisoryRankingRecord(
        id=f"advisory-ranking_{attempt_id}",
        created_at=CREATED_AT,
        attempt_id=attempt_id,
        score_milli=score_milli,
        uncertainty_milli=uncertainty_milli,
        scorer_id="fake-advisory-ranker",
        rationale="Deterministic fixture score.",
    )


def _receipt(
    contract: TaskContract,
    attempt: Attempt,
    *,
    accepted: bool,
) -> VerificationReceipt:
    verifier_run = VerifierRun(
        id=f"verifier-run_{attempt.id}",
        created_at=CREATED_AT,
        verifier_id="verifier.best-of-n.local",
        name="Local hard verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=accepted,
        metrics={"tests": 1, "failures": 0 if accepted else 1},
        failure_reasons=[] if accepted else ["fixture failure"],
        logs_digest=sha256_digest(f"logs:{attempt.id}:{accepted}"),
    )
    return VerificationReceipt(
        id=f"verification-receipt_{attempt.id}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id=verifier_run.verifier_id,
        verifier_digest=verifier_run.verifier_digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics=verifier_run.metrics,
        failure_reasons=verifier_run.failure_reasons,
        result_digest=verifier_run.result_digest(),
    )


def _trajectory_record(
    contract: TaskContract,
    attempt: Attempt,
    receipt: VerificationReceipt,
) -> dict[str, object]:
    outcome = "accepted" if receipt.accepted else "rejected"
    return {
        "schema": "faber.trajectory.v1",
        "id": f"trajectory_{attempt.id}",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "receipt": receipt.to_dict(),
        "router_decision": {"policy_name": "best-of-n-fixture"},
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 10},
        "latency_metadata": {"work_seconds": 30},
        "review_metadata": {"human_reviewed": False},
        "outcome": outcome,
    }


def test_hard_accepted_attempt_wins_over_higher_advisory_score() -> None:
    contract = _contract()
    attempts = [_attempt(contract, suffix) for suffix in ["a", "b", "c"]]
    rankings = [
        _ranking("attempt_a", 950, 80),
        _ranking("attempt_b", 300, 40),
        _ranking("attempt_c", 200, 50),
    ]
    receipts = [
        _receipt(contract, attempts[1], accepted=True),
        _receipt(contract, attempts[2], accepted=False),
    ]

    selection = select_best_attempt(
        contract=contract,
        attempts=attempts,
        advisory_rankings=rankings,
        receipts=receipts,
        budget_used=Money("EUR", 75),
        selection_id="candidate-selection_hard",
        created_at=CREATED_AT,
    )

    assert selection.selected_attempt_id == "attempt_b"
    assert selection.selection_reason == "hard_authoritative_accept"
    assert selection.authoritative_receipt_id == "verification-receipt_attempt_b"
    assert selection.budget_used.minor_units == 75
    assert {item["reason"] for item in selection.rejected_alternatives} == {
        "hard_acceptance_dominated_advisory",
        "hard_rejected",
    }


def test_advisory_ranking_chooses_among_unverified_candidates() -> None:
    contract = _contract()
    attempts = [_attempt(contract, suffix) for suffix in ["a", "b", "c"]]
    rankings = [
        _ranking("attempt_a", 500, 80),
        _ranking("attempt_b", 900, 100),
        _ranking("attempt_c", 900, 200),
    ]

    selection = select_best_attempt(
        contract=contract,
        attempts=attempts,
        advisory_rankings=rankings,
        budget_used=Money("EUR", 25),
        selection_id="candidate-selection_advisory",
        created_at=CREATED_AT,
    )

    assert selection.selected_attempt_id == "attempt_b"
    assert selection.selection_reason == "advisory_ranking"
    assert selection.authoritative_receipt_id is None
    assert selection.uncertainty_milli == 100


def test_rejected_attempts_export_into_dataset(tmp_path) -> None:
    contract = _contract()
    attempts = [_attempt(contract, suffix) for suffix in ["a", "b", "c"]]
    receipts = [
        _receipt(contract, attempts[0], accepted=False),
        _receipt(contract, attempts[1], accepted=True),
        _receipt(contract, attempts[2], accepted=False),
    ]
    selection = select_best_attempt(
        contract=contract,
        attempts=attempts,
        advisory_rankings=[
            _ranking("attempt_a", 950, 80),
            _ranking("attempt_b", 300, 40),
            _ranking("attempt_c", 200, 50),
        ],
        receipts=receipts,
        selection_id="candidate-selection_dataset",
        created_at=CREATED_AT,
    )
    records = [
        _trajectory_record(contract, attempt, receipt)
        for attempt, receipt in zip(attempts, receipts, strict=True)
    ]
    annotated = selection_dataset_records(records, selection)
    out_path = tmp_path / "selection.jsonl"

    manifest = export_trajectories_jsonl(
        annotated,
        out_path,
        dataset_id="dataset_best_of_n_selection",
    )
    loaded = read_trajectory_jsonl(out_path)

    assert manifest.record_count == 3
    assert manifest.accepted_count == 1
    assert manifest.rejected_count == 2
    assert {record["selection_outcome"] for record in loaded} == {"selected", "rejected"}
    assert sum(record["selection_outcome"] == "rejected" for record in loaded) == 2


def test_selection_record_digest_is_stable() -> None:
    contract = _contract()
    attempts = [_attempt(contract, suffix) for suffix in ["a", "b"]]
    rankings = [_ranking("attempt_a", 500, 80), _ranking("attempt_b", 700, 30)]

    left = select_best_attempt(
        contract=contract,
        attempts=attempts,
        advisory_rankings=rankings,
        budget_used=Money("EUR", 25),
        selection_id="candidate-selection_stable",
        created_at=CREATED_AT,
    )
    right = select_best_attempt(
        contract=contract,
        attempts=attempts,
        advisory_rankings=rankings,
        budget_used=Money("EUR", 25),
        selection_id="candidate-selection_stable",
        created_at=CREATED_AT,
    )

    assert left.digest() == right.digest()
