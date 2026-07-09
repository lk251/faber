from dataclasses import replace

import pytest

from faber.adapters.github.funded_product_loop import run_fake_github_funded_product_loop
from faber.contracts import TaskContract
from faber.errors import ValidationError
from faber.risk import (
    CredentialRisk,
    ExternalActionRisk,
    HumanReviewGate,
    PrivateDataRisk,
    RegulatedDomainRisk,
    SecuritySensitiveRisk,
    TaskRiskLevel,
    require_task_risk_readiness,
    review_task_risk,
)

CREATED_AT = "2026-07-09T00:00:00Z"


def _contract(risk: dict[str, object]) -> TaskContract:
    return TaskContract(
        id="task-contract_structured_risk",
        created_at=CREATED_AT,
        title="Structured risk fixture",
        description="Review task risk before funding or execution.",
        requirements=["Pass an authoritative local verifier."],
        verifier_ids=["verifier.local"],
        environment={"external_services": [], "risk": risk},
    )


def test_low_risk_local_task_is_ready() -> None:
    contract = _contract(
        {
            "external_action": ExternalActionRisk().to_dict(),
            "credential": CredentialRisk().to_dict(),
            "private_data": PrivateDataRisk().to_dict(),
            "regulated_domain": RegulatedDomainRisk().to_dict(),
            "security_sensitive": SecuritySensitiveRisk().to_dict(),
        }
    )

    review = review_task_risk(contract, created_at=CREATED_AT)

    assert review.risk_level == TaskRiskLevel.LOCAL_ONLY_LOW.value
    assert review.human_review_gate.required is False
    assert require_task_risk_readiness(review) == review


def test_credential_task_is_blocked_without_review() -> None:
    contract = _contract(
        {"credential": CredentialRisk(required=True, credential_types=["api-token"]).to_dict()}
    )

    review = review_task_risk(contract, created_at=CREATED_AT)

    assert review.flags["credentials_or_account_access"] is True
    assert review.human_review_gate.required is True
    with pytest.raises(ValidationError, match="not ready for funding"):
        require_task_risk_readiness(review)


def test_private_data_task_is_blocked_without_review() -> None:
    contract = _contract(
        {"private_data": PrivateDataRisk(required=True, data_classes=["customer-log"]).to_dict()}
    )

    review = review_task_risk(contract, created_at=CREATED_AT)

    assert review.flags["private_data_exposure"] is True
    assert review.ready_for_agent_execution is False


def test_structured_risk_flags_are_bound_into_contract_digest() -> None:
    low = _contract({"external_action": ExternalActionRisk().to_dict()})
    external_write = replace(
        low,
        environment={
            **low.environment,
            "risk": {
                "external_action": ExternalActionRisk(
                    external_writes=True,
                    action_kinds=["publish-pull-request"],
                ).to_dict()
            },
        },
    )

    assert low.digest() != external_write.digest()
    assert external_write.to_dict()["environment"]["risk"]["external_action"][
        "external_writes"
    ] is True


def test_explicit_human_review_can_approve_high_risk_task() -> None:
    contract = _contract(
        {
            "regulated_domain": RegulatedDomainRisk(
                required=True,
                domains=["financial-advice"],
            ).to_dict(),
            "security_sensitive": SecuritySensitiveRisk(
                required=True,
                areas=["authentication"],
            ).to_dict(),
        }
    )
    metadata = {
        "human_reviewed": True,
        "approved": True,
        "approved_for_funding": True,
        "approved_for_agent_execution": True,
        "reviewer": "maintainer@example",
        "reviewed_at": CREATED_AT,
        "rationale": "Use a disposable local fixture and require manual publication.",
    }

    review = review_task_risk(contract, review_metadata=metadata, created_at=CREATED_AT)

    assert isinstance(review.human_review_gate, HumanReviewGate)
    assert review.human_review_gate.approved is True
    assert review.ready_for_funding is True
    assert review.ready_for_agent_execution is True
    assert require_task_risk_readiness(review, funding=True, execution=True) == review


def test_fake_funded_loop_enforces_low_risk_gate_before_ledger(tmp_path) -> None:
    result = run_fake_github_funded_product_loop(tmp_path / "training.jsonl")

    assert result.risk_review.ready_for_funding is True
    assert result.risk_review.ready_for_agent_execution is True
    assert result.budget_events[0].event_type == "budget.registered"
