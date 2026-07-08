"""Fake GitHub funding-source adapter boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.budgets import FundingEvent
from faber.money import Money
from faber.validation import require_non_empty_string


@dataclass(frozen=True)
class FundingSourceAdapterSpec:
    """Static adapter capability declaration; not a payment-provider integration."""

    provider: str
    supported_source_types: list[str]
    custody_claim: str = "none-adapter-only"
    compliance_claim: str = "none-adapter-only"

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "supported_source_types": self.supported_source_types,
            "custody_claim": self.custody_claim,
            "compliance_claim": self.compliance_claim,
        }


@dataclass
class FakeGitHubFundingSourceAdapter:
    """Local fake funding adapter for tests and future GitHub funding surfaces."""

    provider: str = "github.fake"
    emitted_events: list[FundingEvent] = field(default_factory=list)

    def spec(self) -> FundingSourceAdapterSpec:
        return FundingSourceAdapterSpec(
            provider=self.provider,
            supported_source_types=[
                "github_sponsors",
                "funding_yml",
                "open_collective",
                "issue_funding_tool",
                "membership_or_grant",
                "enterprise_budget",
                "unknown_provider",
            ],
        )

    def emit_issue_funding_event(
        self,
        *,
        repository: str,
        issue_number: int,
        amount: Money,
        external_event_id: str,
        source_type: str = "issue_funding_tool",
        occurred_at: str = "2026-01-01T00:00:00Z",
        payload: dict[str, object] | None = None,
    ) -> FundingEvent:
        require_non_empty_string(repository, "repository")
        event = FundingEvent(
            provider=self.provider,
            external_event_id=external_event_id,
            source_type=source_type,
            target_kind="github.issue",
            target_ref=f"{repository}#{issue_number}",
            amount=amount,
            occurred_at=occurred_at,
            payload=payload or {},
        )
        self.emitted_events.append(event)
        return event

    def emit_repository_funding_event(
        self,
        *,
        repository: str,
        amount: Money,
        external_event_id: str,
        source_type: str = "github_sponsors",
        occurred_at: str = "2026-01-01T00:00:00Z",
        payload: dict[str, object] | None = None,
    ) -> FundingEvent:
        require_non_empty_string(repository, "repository")
        event = FundingEvent(
            provider=self.provider,
            external_event_id=external_event_id,
            source_type=source_type,
            target_kind="github.repository",
            target_ref=repository,
            amount=amount,
            occurred_at=occurred_at,
            payload=payload or {},
        )
        self.emitted_events.append(event)
        return event
