import pytest

from faber.adapters.github.funding import FakeGitHubFundingSourceAdapter
from faber.budgets import (
    FundingEvent,
    FundingEventLedger,
    issue_budget_from_repository_funding_event,
    work_budget_from_funding_event,
)
from faber.errors import ValidationError
from faber.money import Money


def test_fake_funding_source_emits_provider_tagged_events() -> None:
    adapter = FakeGitHubFundingSourceAdapter()

    event = adapter.emit_issue_funding_event(
        repository="lk251/faber",
        issue_number=4,
        amount=Money("EUR", 2_500),
        external_event_id="event-1",
        payload={"surface": "issue-funding-tool"},
    )

    assert event.provider == "github.fake"
    assert event.target_kind == "github.issue"
    assert event.target_ref == "lk251/faber#4"
    assert event.idempotency_key == "github.fake:event-1"
    assert adapter.spec().to_dict()["custody_claim"] == "none-adapter-only"


def test_duplicate_funding_events_are_idempotent() -> None:
    ledger = FundingEventLedger()
    adapter = FakeGitHubFundingSourceAdapter()
    first = adapter.emit_issue_funding_event(
        repository="lk251/faber",
        issue_number=4,
        amount=Money("EUR", 2_500),
        external_event_id="event-1",
    )
    duplicate = adapter.emit_issue_funding_event(
        repository="lk251/faber",
        issue_number=4,
        amount=Money("EUR", 2_500),
        external_event_id="event-1",
    )

    assert ledger.record(first) == ledger.record(duplicate)
    assert len(ledger.events()) == 1


def test_funding_event_creates_work_budget() -> None:
    event = FakeGitHubFundingSourceAdapter().emit_issue_funding_event(
        repository="lk251/faber",
        issue_number=4,
        amount=Money("EUR", 2_500),
        external_event_id="event-1",
    )

    source, budget = work_budget_from_funding_event(
        event,
        verifier_policy={"required_verifier_ids": ["verifier.github"]},
    )

    assert source.provider_ref == "github.fake:event-1"
    assert budget.target_ref == "lk251/faber#4"
    assert budget.metadata["provider"] == "github.fake"


def test_repository_level_funding_allocates_to_issue_budget_by_policy() -> None:
    event = FakeGitHubFundingSourceAdapter().emit_repository_funding_event(
        repository="lk251/faber",
        amount=Money("EUR", 10_000),
        external_event_id="repo-event-1",
        payload={"policy": "allocate-to-issue-4"},
    )

    _source, budget = issue_budget_from_repository_funding_event(
        event,
        issue_number=4,
        verifier_policy={"required_verifier_ids": ["verifier.github"]},
        purpose_allocations={"solver_payout": Money("EUR", 8_000)},
    )

    assert budget.target_kind == "github.issue"
    assert budget.target_ref == "lk251/faber#4"
    assert budget.metadata["source_target_kind"] == "github.repository"


def test_unknown_provider_is_represented_without_core_changes() -> None:
    event = FundingEvent(
        provider="unknown.future.provider",
        external_event_id="unknown-1",
        source_type="unknown_provider",
        target_kind="github.issue",
        target_ref="lk251/faber#4",
        amount=Money("EUR", 1_000),
        occurred_at="2026-01-01T00:00:00Z",
        payload={"raw": "kept for adapter audit"},
    )

    source, budget = work_budget_from_funding_event(
        event,
        verifier_policy={"required_verifier_ids": ["verifier.github"]},
    )

    assert source.metadata["provider"] == "unknown.future.provider"
    assert budget.metadata["provider"] == "unknown.future.provider"


def test_event_idempotency_rejects_conflicting_payloads() -> None:
    ledger = FundingEventLedger()
    adapter = FakeGitHubFundingSourceAdapter()
    ledger.record(
        adapter.emit_issue_funding_event(
            repository="lk251/faber",
            issue_number=4,
            amount=Money("EUR", 2_500),
            external_event_id="event-1",
        )
    )

    with pytest.raises(ValidationError, match="idempotency key reused"):
        ledger.record(
            adapter.emit_issue_funding_event(
                repository="lk251/faber",
                issue_number=4,
                amount=Money("EUR", 3_000),
                external_event_id="event-1",
            )
        )
