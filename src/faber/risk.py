"""Risk review records for funded or external agent work."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import require_mapping, require_non_empty_string, require_schema

LOCAL_ONLY_LOW = "local-only low risk"
OPEN_SOURCE_LOW_MEDIUM = "open-source repo low/medium risk"
EXTERNAL_SERVICE_RISK = "external-service risk"
PRIVATE_DATA_RISK = "private-data risk"
REGULATED_DOMAIN_RISK = "regulated-domain risk"
SECURITY_SENSITIVE_RISK = "security-sensitive risk"

TASK_RISK_LEVELS = {
    LOCAL_ONLY_LOW,
    OPEN_SOURCE_LOW_MEDIUM,
    EXTERNAL_SERVICE_RISK,
    PRIVATE_DATA_RISK,
    REGULATED_DOMAIN_RISK,
    SECURITY_SENSITIVE_RISK,
}
HIGH_RISK_LEVELS = {
    EXTERNAL_SERVICE_RISK,
    PRIVATE_DATA_RISK,
    REGULATED_DOMAIN_RISK,
    SECURITY_SENSITIVE_RISK,
}
FINDING_SEVERITIES = {"info", "warning", "blocker"}


@dataclass(frozen=True)
class RiskFinding:
    """One risk review finding."""

    severity: str
    field: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in FINDING_SEVERITIES:
            raise ValidationError(f"severity must be one of {sorted(FINDING_SEVERITIES)}")
        require_non_empty_string(self.field, "field")
        require_non_empty_string(self.message, "message")

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True)
class TaskRiskReview:
    """Risk classification and readiness gate for a task."""

    task_contract_id: str
    risk_level: str
    flags: dict[str, bool]
    findings: list[RiskFinding]
    review_metadata: dict[str, object] = field(default_factory=dict)
    ready_for_funding: bool = False
    ready_for_agent_execution: bool = False
    id: str = field(default_factory=lambda: new_id("task-risk-review"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TASK_RISK_REVIEW

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TASK_RISK_REVIEW)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_risk_level(self.risk_level)
        require_mapping(self.flags, "flags")
        for key, value in self.flags.items():
            if not isinstance(value, bool):
                raise ValidationError(f"flags.{key} must be a boolean")
        for index, finding in enumerate(self.findings):
            if not isinstance(finding, RiskFinding):
                raise ValidationError(f"findings[{index}] must be a RiskFinding")
        require_mapping(self.review_metadata, "review_metadata")
        if not isinstance(self.ready_for_funding, bool):
            raise ValidationError("ready_for_funding must be a boolean")
        if not isinstance(self.ready_for_agent_execution, bool):
            raise ValidationError("ready_for_agent_execution must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "risk_level": self.risk_level,
            "flags": self.flags,
            "findings": [finding.to_dict() for finding in self.findings],
            "review_metadata": self.review_metadata,
            "ready_for_funding": self.ready_for_funding,
            "ready_for_agent_execution": self.ready_for_agent_execution,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def review_task_risk(
    contract: TaskContract,
    *,
    review_metadata: dict[str, object] | None = None,
    review_id: str | None = None,
    created_at: str | None = None,
) -> TaskRiskReview:
    """Classify task risk and decide whether it is ready to fund or execute."""

    metadata = review_metadata or {}
    require_mapping(metadata, "review_metadata")
    flags = _risk_flags(contract)
    risk_level = _risk_level(contract, flags)
    findings = _risk_findings(flags)
    explicit_review = _has_explicit_review_metadata(metadata)
    if risk_level in HIGH_RISK_LEVELS and not explicit_review:
        findings.append(
            RiskFinding(
                severity="blocker",
                field="review_metadata",
                message="high-risk task requires explicit human review metadata",
            )
        )
    ready = not any(finding.severity == "blocker" for finding in findings)
    return TaskRiskReview(
        id=review_id if review_id is not None else new_id("task-risk-review"),
        created_at=created_at if created_at is not None else utc_now(),
        task_contract_id=contract.id,
        risk_level=risk_level,
        flags=flags,
        findings=findings,
        review_metadata=dict(metadata),
        ready_for_funding=ready,
        ready_for_agent_execution=ready,
    )


def require_risk_level(value: str) -> str:
    """Validate a task risk level string."""

    require_non_empty_string(value, "risk_level")
    if value not in TASK_RISK_LEVELS:
        raise ValidationError(f"risk_level must be one of {sorted(TASK_RISK_LEVELS)}")
    return value


def _risk_flags(contract: TaskContract) -> dict[str, bool]:
    environment = contract.environment
    external_services = environment.get("external_services", [])
    payment_integrations = environment.get("payment_provider_integrations")
    return {
        "private_data_exposure": _truthy(environment.get("private_data"))
        or _truthy(environment.get("private_data_exposure")),
        "credentials_or_account_access": _truthy(environment.get("requires_credentials"))
        or _truthy(environment.get("credentials_or_account_access")),
        "external_write_actions": _truthy(environment.get("external_write_actions")),
        "legal_or_regulated_domain": _truthy(environment.get("regulated_domain"))
        or _truthy(environment.get("legal_or_regulated_domain")),
        "security_sensitive_repository": _truthy(environment.get("security_sensitive"))
        or _truthy(environment.get("security_sensitive_repository")),
        "payment_provider_assumptions": payment_integrations
        not in (None, False, "out_of_scope", "none"),
        "maintainer_consent_missing": environment.get("maintainer_consent") is False,
        "trace_privacy_redaction_missing": environment.get("trace_redaction_required") is True
        and not environment.get("redaction_policy"),
        "false_accept_risk": _truthy(environment.get("false_accept_risk")),
        "reputational_risk": _truthy(environment.get("reputational_risk")),
        "external_services": isinstance(external_services, list) and bool(external_services),
    }


def _risk_level(contract: TaskContract, flags: dict[str, bool]) -> str:
    if flags["security_sensitive_repository"]:
        return SECURITY_SENSITIVE_RISK
    if flags["legal_or_regulated_domain"]:
        return REGULATED_DOMAIN_RISK
    if flags["private_data_exposure"]:
        return PRIVATE_DATA_RISK
    if (
        flags["credentials_or_account_access"]
        or flags["external_write_actions"]
        or flags["external_services"]
        or flags["payment_provider_assumptions"]
    ):
        return EXTERNAL_SERVICE_RISK
    if contract.repository is not None or contract.task_source.startswith("github."):
        return OPEN_SOURCE_LOW_MEDIUM
    return LOCAL_ONLY_LOW


def _risk_findings(flags: dict[str, bool]) -> list[RiskFinding]:
    field_messages = {
        "private_data_exposure": "task may expose private data",
        "credentials_or_account_access": "task requires credentials or account access",
        "external_write_actions": "task can perform external write actions",
        "legal_or_regulated_domain": "task touches a legal or regulated domain",
        "security_sensitive_repository": "task touches a security-sensitive repository",
        "payment_provider_assumptions": "task assumes payment provider behavior",
        "maintainer_consent_missing": "maintainer consent is explicitly missing",
        "trace_privacy_redaction_missing": "trace redaction policy is missing",
        "false_accept_risk": "task has elevated false-accept risk",
        "reputational_risk": "task has elevated reputational risk",
        "external_services": "task depends on external services",
    }
    findings: list[RiskFinding] = []
    for field_name, enabled in flags.items():
        if enabled:
            findings.append(
                RiskFinding(
                    severity="warning",
                    field=field_name,
                    message=field_messages[field_name],
                )
            )
    return findings


def _has_explicit_review_metadata(metadata: dict[str, object]) -> bool:
    reviewer = metadata.get("reviewer")
    return (
        metadata.get("human_reviewed") is True
        and metadata.get("approved") is True
        and isinstance(reviewer, str)
        and bool(reviewer.strip())
    )


def _truthy(value: object) -> bool:
    return value is True
