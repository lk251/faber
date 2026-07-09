"""Inspectable local, self-hosted, and future-hosted runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.validation import require_non_empty_string, require_string_list


class RuntimeMode(StrEnum):
    LOCAL = "local"
    SELF_HOSTED = "self-hosted"
    HOSTED_FUTURE = "hosted-future"


@dataclass(frozen=True)
class RuntimeBoundary:
    """Declared operational expectations, separate from protocol semantics."""

    mode: RuntimeMode
    implementation_status: str
    account_required: bool
    external_api_required: bool
    telemetry_enabled: bool
    telemetry_policy: str
    state_location: str
    available_components: list[str]
    limitations: list[str]
    schema: str = schemas.RUNTIME_BOUNDARY

    def __post_init__(self) -> None:
        if not isinstance(self.mode, RuntimeMode):
            raise ValidationError("mode must be a RuntimeMode")
        if self.implementation_status not in {"available", "future-design-only"}:
            raise ValidationError("implementation_status is invalid")
        for field_name, value in [
            ("account_required", self.account_required),
            ("external_api_required", self.external_api_required),
            ("telemetry_enabled", self.telemetry_enabled),
        ]:
            if not isinstance(value, bool):
                raise ValidationError(f"{field_name} must be a boolean")
        require_non_empty_string(self.telemetry_policy, "telemetry_policy")
        require_non_empty_string(self.state_location, "state_location")
        require_string_list(self.available_components, "available_components")
        require_string_list(self.limitations, "limitations")
        require_non_empty_string(self.schema, "schema")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "mode": self.mode.value,
            "implementation_status": self.implementation_status,
            "account_required": self.account_required,
            "external_api_required": self.external_api_required,
            "telemetry_enabled": self.telemetry_enabled,
            "telemetry_policy": self.telemetry_policy,
            "state_location": self.state_location,
            "available_components": self.available_components,
            "limitations": self.limitations,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def local_runtime_boundary() -> RuntimeBoundary:
    """Return the policy for account-free local CLI and library use."""

    return RuntimeBoundary(
        mode=RuntimeMode.LOCAL,
        implementation_status="available",
        account_required=False,
        external_api_required=False,
        telemetry_enabled=False,
        telemetry_policy="disabled-no-collection-or-transmission",
        state_location="operator-selected local files and SQLite databases",
        available_components=[
            "protocol-validation",
            "local-runner",
            "local-event-store",
            "fake-github-adapter",
            "local-budget-ledger",
            "trajectory-and-dataset-export",
        ],
        limitations=[
            "LocalVerifierRunner is not a production sandbox.",
            "Approved verifier commands retain host network access unless separately isolated.",
            "No real account, marketplace, custody, payment, or hosted training service exists.",
        ],
    )


def self_hosted_runtime_boundary() -> RuntimeBoundary:
    """Return the intended boundary for operator-managed runner infrastructure."""

    return RuntimeBoundary(
        mode=RuntimeMode.SELF_HOSTED,
        implementation_status="available",
        account_required=False,
        external_api_required=False,
        telemetry_enabled=False,
        telemetry_policy="operator-controlled-disabled-by-default",
        state_location="operator-controlled infrastructure",
        available_components=[
            "protocol-validation",
            "runner-and-verifier-policy",
            "operator-managed-store",
            "adapter-selected-integrations",
        ],
        limitations=[
            "Isolation, availability, backups, and adapter credentials are operator "
            "responsibilities.",
            "Self-hosting does not grant verifier authority absent task or repository policy.",
        ],
    )


def future_hosted_boundary() -> RuntimeBoundary:
    """Describe the proposed hosted surface without implementing a service."""

    return RuntimeBoundary(
        mode=RuntimeMode.HOSTED_FUTURE,
        implementation_status="future-design-only",
        account_required=True,
        external_api_required=True,
        telemetry_enabled=False,
        telemetry_policy="not-implemented-explicit-policy-and-consent-required",
        state_location="future hosted account and regional service policy",
        available_components=[],
        limitations=[
            "No hosted market, work-budget service, verifier fleet, or training service exists.",
            "Future hosted state must export canonical protocol records.",
            "Legal, privacy, abuse, custody, and service-level policies require review.",
        ],
    )
