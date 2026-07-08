import sys
from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError, VerifierError
from faber.ledger import LedgerAccount, MarketLedger
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.runner.local import LocalVerifierRunner, RunnerPolicy
from faber.store import save_attempt, save_trajectory, store_summary
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRegistry, VerifierRun, VerifierSpec


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_reference",
        created_at="2026-01-01T00:00:00Z",
        title="Reference invariant task",
        description="Exercise reference invariants from agent-bounty-market.",
        requirements=["preserve verifier-first boundaries"],
        verifier_ids=["verifier.reference"],
        repository="lk251/faber",
        reward=Money("EUR", 1_000),
    )


def _attempt(*, candidate_revision: str = "candidate-a") -> Attempt:
    return Attempt(
        id=f"attempt_{candidate_revision}",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id="task-contract_reference",
        worker_id="worker_reference",
        base_revision="base",
        candidate_revision=candidate_revision,
        summary="Candidate says this passed.",
        patch_digest=sha256_digest({"candidate": candidate_revision}),
        metadata={"candidate_reported_status": "success"},
    )


def _verifier_run(*, passed: bool = True) -> VerifierRun:
    return VerifierRun(
        id="verifier-run_reference",
        created_at="2026-01-01T00:00:00Z",
        verifier_id="verifier.reference",
        name="Reference verifier",
        version="1",
        command=[sys.executable, "-m", "pytest"],
        passed=passed,
        metrics={"checks": 1},
        failure_reasons=[] if passed else ["failed"],
        logs_digest=sha256_digest("logs"),
    )


def _receipt(*, accepted: bool = True) -> VerificationReceipt:
    return VerificationReceipt.from_verifier_run(
        _contract(),
        _attempt(),
        _verifier_run(passed=accepted),
    )


def _router_decision() -> RouterDecision:
    return RouterDecision(
        id="router-decision_reference",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id="task-contract_reference",
        selected_worker_id="worker_reference",
        rejected_alternatives=[],
        estimated_cost=Money("EUR", 100),
        expected_value=Money("EUR", 1_000),
        policy_name="reference-invariant-router",
    )


def _ledger() -> MarketLedger:
    ledger = MarketLedger()
    for account in [
        LedgerAccount("external", "EUR", "external", allow_negative=True),
        LedgerAccount("buyer", "EUR", "buyer"),
        LedgerAccount("escrow", "EUR", "escrow"),
        LedgerAccount("worker", "EUR", "worker"),
    ]:
        ledger.add_account(account)
    ledger.record_entry(
        source_account_id="external",
        destination_account_id="buyer",
        amount=Money("EUR", 5_000),
        reason="local_funding",
        idempotency_key="fund-reference-buyer",
    )
    return ledger


def _timeout_spec() -> VerifierSpec:
    return VerifierSpec(
        verifier_id="verifier.reference",
        name="Reference verifier",
        version="1",
        description="Times out for invariant coverage.",
        command_template=[sys.executable, "-c", "import time; time.sleep(2)"],
        allowed_timeout_seconds=1,
    )


def test_receipt_for_one_candidate_revision_does_not_authorize_another_revision() -> None:
    receipt = _receipt()
    changed_attempt = _attempt(candidate_revision="candidate-b")

    assert receipt.accepted is True
    assert receipt.attempt_id != changed_attempt.id
    assert receipt.candidate_revision == "candidate-a"
    assert receipt.candidate_revision != changed_attempt.candidate_revision


def test_candidate_reported_success_is_not_an_authoritative_receipt(tmp_path: Path) -> None:
    attempt = _attempt()
    saved = save_attempt(tmp_path / ".faber" / "reference.sqlite3", attempt)

    summary = store_summary(tmp_path / ".faber" / "reference.sqlite3")

    assert saved.inserted is True
    assert attempt.metadata["candidate_reported_status"] == "success"
    assert summary["record_counts"]["attempt"] == 1
    assert "verification_receipt" not in summary["record_counts"]


def test_timed_out_verifier_run_cannot_drive_payout(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    registry.register(_timeout_spec())
    policy = RunnerPolicy(
        allowed_working_directory_root=str(tmp_path),
        timeout_seconds=1,
    )

    result = LocalVerifierRunner(registry, policy=policy).run(
        "verifier.reference",
        working_directory=tmp_path,
    )
    receipt = VerificationReceipt.from_verifier_run(_contract(), _attempt(), result.verifier_run)
    ledger = _ledger()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 1_000),
        idempotency_key="reserve-reference",
    )

    assert result.timed_out is True
    assert receipt.accepted is False
    with pytest.raises(SettlementError, match="accepted verification receipt"):
        ledger.payout(
            escrow_account_id="escrow",
            worker_account_id="worker",
            receipt=receipt,
            amount=Money("EUR", 1_000),
            idempotency_key="payout-reference",
        )


def test_completed_trajectory_digest_replay_inserts_one_record(tmp_path: Path) -> None:
    contract = _contract()
    attempt = _attempt()
    receipt = _receipt()
    trajectory = Trajectory(
        id="trajectory_reference",
        created_at="2026-01-01T00:00:00Z",
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        router_decision=_router_decision(),
        cost_metadata={"currency": "EUR", "minor_units": 100},
        latency_metadata={"seconds": 1},
        review_metadata={"human_reviewed": False},
    )
    store_path = tmp_path / ".faber" / "reference.sqlite3"

    first = save_trajectory(store_path, trajectory)
    second = save_trajectory(store_path, trajectory)

    assert first.inserted is True
    assert second.inserted is False
    assert store_summary(store_path)["record_counts"]["trajectory"] == 1


def test_payout_idempotency_prevents_double_payment() -> None:
    ledger = _ledger()
    receipt = _receipt()
    ledger.reserve(
        buyer_account_id="buyer",
        escrow_account_id="escrow",
        amount=Money("EUR", 1_000),
        idempotency_key="reserve-reference",
    )

    first = ledger.payout(
        escrow_account_id="escrow",
        worker_account_id="worker",
        receipt=receipt,
        amount=Money("EUR", 1_000),
        idempotency_key="payout-reference",
    )
    second = ledger.payout(
        escrow_account_id="escrow",
        worker_account_id="worker",
        receipt=receipt,
        amount=Money("EUR", 1_000),
        idempotency_key="payout-reference",
    )

    assert first == second
    assert ledger.balance("worker").minor_units == 1_000
    assert ledger.reconciliation_summary()["idempotency_key_count"] == 3


def test_runner_policy_rejects_unapproved_candidate_environment(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    registry.register(
        VerifierSpec(
            verifier_id="verifier.reference",
            name="Reference verifier",
            version="1",
            description="Accepts no candidate environment.",
            command_template=[sys.executable, "-c", "print('ok')"],
        )
    )
    policy = RunnerPolicy(
        allowed_working_directory_root=str(tmp_path),
        allowed_environment_variables=["PATH"],
    )

    with pytest.raises(VerifierError, match="not allowed"):
        LocalVerifierRunner(registry, policy=policy).run(
            "verifier.reference",
            working_directory=tmp_path,
            extra_environment={"FABER_CANDIDATE_SECRET": "candidate-controlled"},
        )


def test_runner_policy_digest_is_bound_into_verifier_run(tmp_path: Path) -> None:
    registry = VerifierRegistry()
    registry.register(
        VerifierSpec(
            verifier_id="verifier.reference",
            name="Reference verifier",
            version="1",
            description="Binds runner policy metadata.",
            command_template=[sys.executable, "-c", "print('ok')"],
        )
    )
    policy = RunnerPolicy(allowed_working_directory_root=str(tmp_path))

    result = LocalVerifierRunner(registry, policy=policy).run(
        "verifier.reference",
        working_directory=tmp_path,
    )

    assert result.verifier_run.metadata["runner_policy_digest"] == policy.digest()
    assert result.verifier_run.metadata["shell"] is False
