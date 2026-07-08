import pytest

from faber.attempts import Attempt
from faber.budgets import (
    BudgetReservationBook,
    FundingSource,
    RefundPolicy,
    allocate_budget_to_task,
    authorize_budget_spend,
    expire_reservation,
    issue_work_budget,
    rejected_reservation_refund_event,
)
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import SettlementError
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.verifiers import VerifierRun

CREATED_AT = "2026-01-01T00:00:00Z"


def _funding_source() -> FundingSource:
    return FundingSource(
        id="funding-source_test",
        created_at=CREATED_AT,
        source_type="sponsor_pool",
        display_name="Maintainer sponsor pool",
        currency="EUR",
        provider_ref="provider-adapter-owned-ref",
    )


def _contract() -> TaskContract:
    return TaskContract(
        id="task-contract_budget",
        created_at=CREATED_AT,
        title="Funded GitHub issue",
        description="Implement the funded task.",
        requirements=["pass tests"],
        verifier_ids=["verifier.budget"],
        task_source="github.issue",
        repository="lk251/faber",
    )


def _receipt(*, accepted: bool = True) -> VerificationReceipt:
    contract = _contract()
    attempt = Attempt(
        id="attempt_budget",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id="worker_budget",
        base_revision="base",
        candidate_revision="candidate",
        summary="Implemented the funded task.",
        patch_digest=sha256_digest("patch"),
    )
    run = VerifierRun(
        verifier_id="verifier.budget",
        name="Budget verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=accepted,
        metrics={"tests": 1},
        failure_reasons=[] if accepted else ["tests failed"],
    )
    return VerificationReceipt.from_verifier_run(contract, attempt, run)


def test_create_issue_work_budget() -> None:
    budget = issue_work_budget(
        repository="lk251/faber",
        issue_number=4,
        funding_source=_funding_source(),
        amount=Money("EUR", 10_000),
        verifier_policy={"required_verifier_ids": ["verifier.budget"]},
        purpose_allocations={
            "solver_payout": Money("EUR", 7_000),
            "verifier_spend": Money("EUR", 1_000),
            "trace_quality_bonus": Money("EUR", 1_500),
            "review_budget": Money("EUR", 500),
        },
        refund_policy=RefundPolicy(id="refund-policy_test", created_at=CREATED_AT),
    )

    assert budget.target_kind == "github.issue"
    assert budget.target_ref == "lk251/faber#4"
    assert budget.purpose_allocations["trace_quality_bonus"].minor_units == 1_500
    assert budget.digest().startswith("sha256:")


def test_allocate_budget_to_task_contract() -> None:
    budget = issue_work_budget(
        repository="lk251/faber",
        issue_number=4,
        funding_source=_funding_source(),
        amount=Money("EUR", 10_000),
        verifier_policy={"required_verifier_ids": ["verifier.budget"]},
    )
    contract = _contract()

    allocation = allocate_budget_to_task(
        budget,
        contract,
        amount=Money("EUR", 7_000),
        purpose="solver_payout",
    )

    assert allocation.task_contract_id == contract.id
    assert allocation.task_contract_digest == contract.digest()
    assert allocation.verifier_policy["required_verifier_ids"] == ["verifier.budget"]


def test_reserve_budget_for_attempt_is_idempotent() -> None:
    budget = issue_work_budget(
        repository="lk251/faber",
        issue_number=4,
        funding_source=_funding_source(),
        amount=Money("EUR", 10_000),
        verifier_policy={"required_verifier_ids": ["verifier.budget"]},
    )
    allocation = allocate_budget_to_task(
        budget,
        _contract(),
        amount=Money("EUR", 7_000),
        purpose="solver_payout",
    )
    book = BudgetReservationBook()

    first = book.reserve(
        allocation,
        attempt_id="attempt_budget",
        idempotency_key="reserve-budget-attempt",
    )
    second = book.reserve(
        allocation,
        attempt_id="attempt_budget",
        idempotency_key="reserve-budget-attempt",
    )

    assert first == second
    assert len(book.reservations()) == 1
    assert first.amount.minor_units == 7_000


def test_no_budget_payout_without_accepted_authoritative_receipt() -> None:
    allocation = allocate_budget_to_task(
        issue_work_budget(
            repository="lk251/faber",
            issue_number=4,
            funding_source=_funding_source(),
            amount=Money("EUR", 10_000),
            verifier_policy={"required_verifier_ids": ["verifier.budget"]},
        ),
        _contract(),
        amount=Money("EUR", 7_000),
        purpose="solver_payout",
    )
    reservation = BudgetReservationBook().reserve(
        allocation,
        attempt_id="attempt_budget",
        idempotency_key="reserve-budget-attempt",
    )

    with pytest.raises(SettlementError, match="accepted authoritative receipt"):
        authorize_budget_spend(reservation, _receipt(accepted=False))


def test_trace_quality_bonus_is_represented_but_not_paid_without_policy() -> None:
    allocation = allocate_budget_to_task(
        issue_work_budget(
            repository="lk251/faber",
            issue_number=4,
            funding_source=_funding_source(),
            amount=Money("EUR", 10_000),
            verifier_policy={"required_verifier_ids": ["verifier.budget"]},
            purpose_allocations={"trace_quality_bonus": Money("EUR", 1_500)},
        ),
        _contract(),
        amount=Money("EUR", 1_500),
        purpose="trace_quality_bonus",
        trace_quality_bonus_policy={"minimum_evidence_level": 2},
    )
    reservation = BudgetReservationBook().reserve(
        allocation,
        attempt_id="attempt_budget",
        idempotency_key="reserve-trace-bonus",
    )

    assert allocation.trace_quality_bonus_policy["minimum_evidence_level"] == 2
    with pytest.raises(SettlementError, match="trace-quality bonus requires"):
        authorize_budget_spend(reservation, _receipt(accepted=True))


def test_refund_and_expiry_paths_have_explicit_policy_states() -> None:
    refund_policy = RefundPolicy(
        id="refund-policy_expiry",
        created_at=CREATED_AT,
        on_rejected="refund_to_source",
        on_expired="manual_review",
        on_cancelled="return_to_budget",
    )
    allocation = allocate_budget_to_task(
        issue_work_budget(
            repository="lk251/faber",
            issue_number=4,
            funding_source=_funding_source(),
            amount=Money("EUR", 10_000),
            verifier_policy={"required_verifier_ids": ["verifier.budget"]},
            refund_policy=refund_policy,
        ),
        _contract(),
        amount=Money("EUR", 7_000),
        purpose="solver_payout",
    )
    reservation = BudgetReservationBook().reserve(
        allocation,
        attempt_id="attempt_budget",
        idempotency_key="reserve-expiring-attempt",
        expires_at="2026-02-01T00:00:00Z",
    )

    expired = expire_reservation(reservation, refund_policy)
    rejected = rejected_reservation_refund_event(reservation, refund_policy)

    assert expired.payload["refund_policy_state"] == "manual_review"
    assert rejected.payload["refund_policy_state"] == "refund_to_source"
