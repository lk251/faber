"""Risk review records for funded or external agent work."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from faber import schemas
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)


class TaskRiskLevel(StrEnum):
    """Stable task-level risk classifications."""

    LOCAL_ONLY_LOW = "local-only low risk"
    OPEN_SOURCE_LOW_MEDIUM = "open-source repo low/medium risk"
    EXTERNAL_SERVICE = "external-service risk"
    PRIVATE_DATA = "private-data risk"
    REGULATED_DOMAIN = "regulated-domain risk"
    SECURITY_SENSITIVE = "security-sensitive risk"


LOCAL_ONLY_LOW = TaskRiskLevel.LOCAL_ONLY_LOW.value
OPEN_SOURCE_LOW_MEDIUM = TaskRiskLevel.OPEN_SOURCE_LOW_MEDIUM.value
EXTERNAL_SERVICE_RISK = TaskRiskLevel.EXTERNAL_SERVICE.value
PRIVATE_DATA_RISK = TaskRiskLevel.PRIVATE_DATA.value
REGULATED_DOMAIN_RISK = TaskRiskLevel.REGULATED_DOMAIN.value
SECURITY_SENSITIVE_RISK = TaskRiskLevel.SECURITY_SENSITIVE.value

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
class ExternalActionRisk:
    """External services, publication, or other non-local write behavior."""

    external_writes: bool = False
    external_services: list[str] = field(default_factory=list)
    action_kinds: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_bool(self.external_writes, "external_writes")
        require_string_list(self.external_services, "external_services")
        require_string_list(self.action_kinds, "action_kinds")

    @property
    def active(self) -> bool:
        return self.external_writes or bool(self.external_services) or bool(self.action_kinds)

    def to_dict(self) -> dict[str, object]:
        return {
            "external_writes": self.external_writes,
            "external_services": self.external_services,
            "action_kinds": self.action_kinds,
            "active": self.active,
        }


@dataclass(frozen=True)
class CredentialRisk:
    """Credential or authenticated-account access required by a task."""

    required: bool = False
    credential_types: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_bool(self.required, "required")
        require_string_list(self.credential_types, "credential_types")

    @property
    def active(self) -> bool:
        return self.required or bool(self.credential_types)

    def to_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "credential_types": self.credential_types,
            "active": self.active,
        }


@dataclass(frozen=True)
class PrivateDataRisk:
    """Private, personal, or otherwise non-public data required by a task."""

    required: bool = False
    data_classes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_bool(self.required, "required")
        require_string_list(self.data_classes, "data_classes")

    @property
    def active(self) -> bool:
        return self.required or bool(self.data_classes)

    def to_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "data_classes": self.data_classes,
            "active": self.active,
        }


@dataclass(frozen=True)
class RegulatedDomainRisk:
    """Legal, financial, medical, or other regulated-domain exposure."""

    required: bool = False
    domains: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_bool(self.required, "required")
        require_string_list(self.domains, "domains")

    @property
    def active(self) -> bool:
        return self.required or bool(self.domains)

    def to_dict(self) -> dict[str, object]:
        return {"required": self.required, "domains": self.domains, "active": self.active}


@dataclass(frozen=True)
class SecuritySensitiveRisk:
    """Authentication, authorization, secrets, or security-boundary changes."""

    required: bool = False
    areas: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_bool(self.required, "required")
        require_string_list(self.areas, "areas")

    @property
    def active(self) -> bool:
        return self.required or bool(self.areas)

    def to_dict(self) -> dict[str, object]:
        return {"required": self.required, "areas": self.areas, "active": self.active}


@dataclass(frozen=True)
class TaskRiskAssessment:
    """Typed risk components derived from a task contract declaration."""

    external_action: ExternalActionRisk
    credential: CredentialRisk
    private_data: PrivateDataRisk
    regulated_domain: RegulatedDomainRisk
    security_sensitive: SecuritySensitiveRisk

    def to_dict(self) -> dict[str, object]:
        return {
            "external_action": self.external_action.to_dict(),
            "credential": self.credential.to_dict(),
            "private_data": self.private_data.to_dict(),
            "regulated_domain": self.regulated_domain.to_dict(),
            "security_sensitive": self.security_sensitive.to_dict(),
        }


@dataclass(frozen=True)
class HumanReviewGate:
    """Explicit human authorization for funding and/or agent execution."""

    task_contract_id: str
    required: bool
    approved: bool
    approved_for_funding: bool
    approved_for_agent_execution: bool
    reviewer: str | None = None
    reviewed_at: str | None = None
    rationale: str = ""
    restrictions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        for field_name, value in [
            ("required", self.required),
            ("approved", self.approved),
            ("approved_for_funding", self.approved_for_funding),
            ("approved_for_agent_execution", self.approved_for_agent_execution),
        ]:
            _require_bool(value, field_name)
        if self.reviewer is not None:
            require_non_empty_string(self.reviewer, "reviewer")
        if self.reviewed_at is not None:
            require_non_empty_string(self.reviewed_at, "reviewed_at")
        if not isinstance(self.rationale, str):
            raise ValidationError("rationale must be a string")
        require_string_list(self.restrictions, "restrictions")
        if self.approved and self.reviewer is None:
            raise ValidationError("approved human review requires reviewer metadata")

    @property
    def allows_funding(self) -> bool:
        return not self.required or (self.approved and self.approved_for_funding)

    @property
    def allows_agent_execution(self) -> bool:
        return not self.required or (self.approved and self.approved_for_agent_execution)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_contract_id": self.task_contract_id,
            "required": self.required,
            "approved": self.approved,
            "approved_for_funding": self.approved_for_funding,
            "approved_for_agent_execution": self.approved_for_agent_execution,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "rationale": self.rationale,
            "restrictions": self.restrictions,
            "allows_funding": self.allows_funding,
            "allows_agent_execution": self.allows_agent_execution,
        }


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
    risk_assessment: TaskRiskAssessment
    human_review_gate: HumanReviewGate
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
        if not isinstance(self.risk_assessment, TaskRiskAssessment):
            raise ValidationError("risk_assessment must be a TaskRiskAssessment")
        if not isinstance(self.human_review_gate, HumanReviewGate):
            raise ValidationError("human_review_gate must be a HumanReviewGate")
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
            "risk_assessment": self.risk_assessment.to_dict(),
            "human_review_gate": self.human_review_gate.to_dict(),
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
    risk_assessment = _risk_assessment(contract)
    flags = _risk_flags(contract, risk_assessment)
    risk_level = _risk_level(contract, flags)
    findings = _risk_findings(flags)
    gate = _human_review_gate(
        contract.id,
        required=risk_level in HIGH_RISK_LEVELS,
        metadata=metadata,
    )
    if gate.required and not gate.approved:
        findings.append(
            RiskFinding(
                severity="blocker",
                field="human_review_gate",
                message="high-risk task requires explicit human review metadata",
            )
        )
    no_blockers = not any(finding.severity == "blocker" for finding in findings)
    return TaskRiskReview(
        id=review_id if review_id is not None else new_id("task-risk-review"),
        created_at=created_at if created_at is not None else utc_now(),
        task_contract_id=contract.id,
        risk_level=risk_level,
        flags=flags,
        findings=findings,
        risk_assessment=risk_assessment,
        human_review_gate=gate,
        review_metadata=dict(metadata),
        ready_for_funding=no_blockers and gate.allows_funding,
        ready_for_agent_execution=no_blockers and gate.allows_agent_execution,
    )


def require_task_risk_readiness(
    review: TaskRiskReview,
    *,
    funding: bool = True,
    execution: bool = True,
) -> TaskRiskReview:
    """Reject funded/executed work until the applicable human gate is open."""

    if funding and not review.ready_for_funding:
        raise ValidationError("task is not ready for funding")
    if execution and not review.ready_for_agent_execution:
        raise ValidationError("task is not ready for agent execution")
    return review


def require_risk_level(value: str) -> str:
    """Validate a task risk level string."""

    require_non_empty_string(value, "risk_level")
    if value not in TASK_RISK_LEVELS:
        raise ValidationError(f"risk_level must be one of {sorted(TASK_RISK_LEVELS)}")
    return value


def _risk_flags(
    contract: TaskContract,
    assessment: TaskRiskAssessment,
) -> dict[str, bool]:
    environment = contract.environment
    payment_integrations = environment.get("payment_provider_integrations")
    return {
        "private_data_exposure": assessment.private_data.active,
        "credentials_or_account_access": assessment.credential.active,
        "external_write_actions": assessment.external_action.external_writes
        or bool(assessment.external_action.action_kinds),
        "legal_or_regulated_domain": assessment.regulated_domain.active,
        "security_sensitive_repository": assessment.security_sensitive.active,
        "payment_provider_assumptions": payment_integrations
        not in (None, False, "out_of_scope", "none"),
        "maintainer_consent_missing": environment.get("maintainer_consent") is False,
        "trace_privacy_redaction_missing": environment.get("trace_redaction_required") is True
        and not environment.get("redaction_policy"),
        "false_accept_risk": _truthy(environment.get("false_accept_risk")),
        "reputational_risk": _truthy(environment.get("reputational_risk")),
        "external_services": bool(assessment.external_action.external_services),
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


def _risk_assessment(contract: TaskContract) -> TaskRiskAssessment:
    environment = contract.environment
    risk = _mapping(environment.get("risk"))
    external = _mapping(risk.get("external_action"))
    credential = _mapping(risk.get("credential"))
    private_data = _mapping(risk.get("private_data"))
    regulated = _mapping(risk.get("regulated_domain"))
    security = _mapping(risk.get("security_sensitive"))
    environment_services = _string_values(environment.get("external_services"))
    return TaskRiskAssessment(
        external_action=ExternalActionRisk(
            external_writes=_truthy(external.get("external_writes"))
            or _truthy(environment.get("external_write_actions")),
            external_services=_string_values(external.get("external_services"))
            or environment_services,
            action_kinds=_string_values(external.get("action_kinds")),
        ),
        credential=CredentialRisk(
            required=_truthy(credential.get("required"))
            or _truthy(environment.get("requires_credentials"))
            or _truthy(environment.get("credentials_or_account_access")),
            credential_types=_string_values(credential.get("credential_types")),
        ),
        private_data=PrivateDataRisk(
            required=_truthy(private_data.get("required"))
            or _truthy(environment.get("private_data"))
            or _truthy(environment.get("private_data_exposure")),
            data_classes=_string_values(private_data.get("data_classes")),
        ),
        regulated_domain=RegulatedDomainRisk(
            required=_truthy(regulated.get("required"))
            or _truthy(environment.get("regulated_domain"))
            or _truthy(environment.get("legal_or_regulated_domain")),
            domains=_string_values(regulated.get("domains")),
        ),
        security_sensitive=SecuritySensitiveRisk(
            required=_truthy(security.get("required"))
            or _truthy(environment.get("security_sensitive"))
            or _truthy(environment.get("security_sensitive_repository")),
            areas=_string_values(security.get("areas")),
        ),
    )


def _human_review_gate(
    task_contract_id: str,
    *,
    required: bool,
    metadata: dict[str, object],
) -> HumanReviewGate:
    reviewer_value = metadata.get("reviewer")
    reviewer = reviewer_value if isinstance(reviewer_value, str) and reviewer_value else None
    reviewed_at_value = metadata.get("reviewed_at")
    reviewed_at = (
        reviewed_at_value if isinstance(reviewed_at_value, str) and reviewed_at_value else None
    )
    approved = (
        metadata.get("human_reviewed") is True
        and metadata.get("approved") is True
        and reviewer is not None
    )
    rationale = metadata.get("rationale", "")
    return HumanReviewGate(
        task_contract_id=task_contract_id,
        required=required,
        approved=approved,
        approved_for_funding=approved and metadata.get("approved_for_funding", True) is True,
        approved_for_agent_execution=approved
        and metadata.get("approved_for_agent_execution", True) is True,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        rationale=rationale if isinstance(rationale, str) else "",
        restrictions=_string_values(metadata.get("restrictions")),
    )


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _truthy(value: object) -> bool:
    return value is True


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean")
    return value
