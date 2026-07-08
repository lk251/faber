from faber.contracts import TaskContract
from faber.risk import (
    EXTERNAL_SERVICE_RISK,
    LOCAL_ONLY_LOW,
    PRIVATE_DATA_RISK,
    SECURITY_SENSITIVE_RISK,
    review_task_risk,
)

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract(*, environment: dict[str, object], repository: str | None = None) -> TaskContract:
    return TaskContract(
        id="task-contract_risk_review",
        created_at=CREATED_AT,
        title="Risk review fixture",
        description="Classify task risk before funding or agent execution.",
        requirements=["Run local verifier."],
        verifier_ids=["verifier.risk.fixture"],
        task_source="local.fixture" if repository is None else "github.issue",
        repository=repository,
        environment=environment,
    )


def test_low_risk_local_task_passes() -> None:
    contract = _contract(environment={"external_services": [], "local_only": True})

    review = review_task_risk(
        contract,
        review_id="task-risk-review_low",
        created_at=CREATED_AT,
    )

    assert review.risk_level == LOCAL_ONLY_LOW
    assert review.ready_for_funding is True
    assert review.ready_for_agent_execution is True
    assert review.findings == []


def test_task_requiring_credentials_is_flagged() -> None:
    contract = _contract(
        repository="example/repository",
        environment={
            "requires_credentials": True,
            "external_services": ["example-api"],
        },
    )

    review = review_task_risk(
        contract,
        review_id="task-risk-review_credentials",
        created_at=CREATED_AT,
    )

    assert review.risk_level == EXTERNAL_SERVICE_RISK
    assert review.flags["credentials_or_account_access"] is True
    assert any(finding.field == "credentials_or_account_access" for finding in review.findings)
    assert review.ready_for_funding is False


def test_task_with_private_data_is_flagged() -> None:
    contract = _contract(environment={"private_data": True})

    review = review_task_risk(
        contract,
        review_id="task-risk-review_private_data",
        created_at=CREATED_AT,
    )

    assert review.risk_level == PRIVATE_DATA_RISK
    assert review.flags["private_data_exposure"] is True
    assert any(finding.field == "private_data_exposure" for finding in review.findings)
    assert review.ready_for_agent_execution is False


def test_high_risk_task_requires_explicit_review_metadata() -> None:
    contract = _contract(environment={"security_sensitive": True})

    blocked = review_task_risk(
        contract,
        review_id="task-risk-review_security_blocked",
        created_at=CREATED_AT,
    )
    approved = review_task_risk(
        contract,
        review_id="task-risk-review_security_approved",
        created_at=CREATED_AT,
        review_metadata={
            "human_reviewed": True,
            "approved": True,
            "reviewer": "maintainer",
        },
    )

    assert blocked.risk_level == SECURITY_SENSITIVE_RISK
    assert blocked.ready_for_funding is False
    assert any(finding.severity == "blocker" for finding in blocked.findings)
    assert approved.ready_for_funding is True
    assert approved.ready_for_agent_execution is True
    assert not any(finding.severity == "blocker" for finding in approved.findings)
