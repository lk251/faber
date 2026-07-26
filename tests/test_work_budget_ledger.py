from dataclasses import replace
from pathlib import Path

import pytest

from faber.attempts import Attempt
from faber.budget_ledger import WorkBudgetLedger
from faber.budgets import (
    FundingSource,
    RefundPolicy,
    allocate_budget_to_task,
    issue_work_budget,
)
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.store import list_records
from faber.verifiers import VerifierRun

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_ledger",
        created_at=CREATED_AT,
        title="Ledger task",
        description="Exercise exact local work budget accounting.",
        requirements=["Pass verifier"],
        verifier_ids=["verifier.ledger"],
    )


def _attempt() -> Attempt:
    return Attempt(
        id="attempt_ledger",
        created_at=CREATED_AT,
        task_contract_id=_contract().id,
        worker_id="worker.ledger",
        base_revision="base",
        candidate_revision="candidate",
        summary="Completed ledger task.",
        patch_digest=sha256_digest("patch"),
    )


def _receipt(*, accepted: bool = True) -> VerificationReceipt:
    run = VerifierRun(
        id=f"verifier-run_{'accepted' if accepted else 'rejected'}",
        created_at=CREATED_AT,
        verifier_id="verifier.ledger",
        name="Ledger verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=accepted,
        metrics={"tests": 1},
        failure_reasons=[] if accepted else ["failed"],
    )
    receipt = VerificationReceipt.from_verifier_run(_contract(), _attempt(), run)
    return replace(
        receipt,
        id=f"verification-receipt_{'accepted' if accepted else 'rejected'}",
        created_at=CREATED_AT,
    )


def _budget_and_allocation(*, bonus_policy: bool = False):
    source = FundingSource(
        id="funding-source_ledger",
        created_at=CREATED_AT,
        source_type="fixture",
        display_name="Ledger fixture",
        currency="EUR",
    )
    budget = issue_work_budget(
        repository="lk251/faber",
        issue_number=6,
        funding_source=source,
        amount=Money("EUR", 10_000),
        verifier_policy={"required_verifier_ids": ["verifier.ledger"]},
        refund_policy=RefundPolicy(
            id="refund-policy_ledger",
            created_at=CREATED_AT,
            on_rejected="return_to_budget",
            on_expired="return_to_budget",
        ),
    )
    allocation = allocate_budget_to_task(
        budget,
        _contract(),
        amount=Money("EUR", 8_000),
        purpose="solver_payout",
        trace_quality_bonus_policy=({"minimum_quality_tier": "trace"} if bonus_policy else {}),
    )
    return budget, allocation


def _ledger(tmp_path: Path | None = None, *, bonus_policy: bool = False):
    budget, allocation = _budget_and_allocation(bonus_policy=bonus_policy)
    ledger = WorkBudgetLedger(
        store_path=tmp_path,
        clock=lambda: CREATED_AT,
    )
    ledger.register_budget(budget, idempotency_key="register-ledger-budget")
    return ledger, budget, allocation


def test_reserve_is_idempotent_and_persists_append_only_event(tmp_path: Path) -> None:
    store_path = tmp_path / "faber.sqlite3"
    ledger, _budget, allocation = _ledger(store_path)

    first = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        amount=Money("EUR", 8_000),
        idempotency_key="reserve-attempt",
    )
    second = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        amount=Money("EUR", 8_000),
        idempotency_key="reserve-attempt",
    )

    assert first == second
    assert ledger.account(first.work_budget_id).active_reserved_minor_units == 8_000
    assert len(list_records(store_path, "budget_event")) == 2


def test_duplicate_settle_does_not_double_pay() -> None:
    ledger, budget, allocation = _ledger()
    reservation = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        idempotency_key="reserve-attempt",
    )
    splits = {
        "worker": Money("EUR", 6_500),
        "verifier": Money("EUR", 500),
        "platform_margin": Money("EUR", 1_000),
    }

    first = ledger.settle(
        reservation,
        _receipt(),
        splits=splits,
        idempotency_key="settle-attempt",
    )
    second = ledger.settle(
        reservation,
        _receipt(),
        splits=splits,
        idempotency_key="settle-attempt",
    )

    assert first == second
    assert ledger.account(budget.id).settled_minor_units == 8_000


def test_rejected_attempt_releases_reservation_by_policy() -> None:
    ledger, budget, allocation = _ledger()
    reservation = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        idempotency_key="reserve-attempt",
    )

    release = ledger.release_rejected(
        reservation,
        _receipt(accepted=False),
        refund_policy=budget.refund_policy,
        idempotency_key="release-rejected",
    )

    assert release.refund_policy_state == "return_to_budget"
    assert ledger.account(budget.id).available_minor_units == 10_000


def test_split_settlement_must_sum_exactly() -> None:
    ledger, _budget, allocation = _ledger()
    reservation = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        idempotency_key="reserve-attempt",
    )

    with pytest.raises(SettlementError, match="sum exactly"):
        ledger.settle(
            reservation,
            _receipt(),
            splits={"worker": Money("EUR", 7_999)},
            idempotency_key="settle-short",
        )


def test_trace_quality_bonus_requires_policy_and_evidence() -> None:
    ledger, _budget, allocation = _ledger(bonus_policy=True)
    reservation = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        idempotency_key="reserve-attempt",
    )
    splits = {
        "worker": Money("EUR", 7_000),
        "trace_quality_bonus": Money("EUR", 1_000),
    }

    with pytest.raises(SettlementError, match="trajectory quality evidence"):
        ledger.settle(
            reservation,
            _receipt(),
            splits=splits,
            idempotency_key="settle-without-evidence",
        )

    settlement = ledger.settle(
        reservation,
        _receipt(),
        splits=splits,
        trajectory_quality={"quality_tier": "trace", "is_rl_grade": True},
        idempotency_key="settle-with-evidence",
    )

    assert settlement.splits["trace_quality_bonus"].minor_units == 1_000


def test_reconciliation_report_explains_exact_balances() -> None:
    ledger, budget, allocation = _ledger()
    reservation = ledger.reserve(
        allocation,
        attempt_id=_attempt().id,
        idempotency_key="reserve-attempt",
    )
    ledger.settle(
        reservation,
        _receipt(),
        splits={"worker": Money("EUR", 7_000), "platform_margin": Money("EUR", 1_000)},
        idempotency_key="settle-attempt",
    )

    report = ledger.reconcile(budget.id)

    assert report.opening_minor_units == 10_000
    assert report.settled_minor_units == 8_000
    assert report.available_minor_units == 2_000
    assert report.split_totals_minor_units == {"platform_margin": 1_000, "worker": 7_000}
    assert report.issues == []
