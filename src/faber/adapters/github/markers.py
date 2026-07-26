"""Machine-readable Faber contract markers for GitHub text surfaces."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from faber.canonical_json import canonical_json
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import DigestMismatchError, ValidationError

MARKER_BEGIN = "<!-- faber:task-contract"
MARKER_END = "-->"
MARKER_SCHEMA = "faber.github.task_contract_marker.v1"
FUNDED_MARKER_BEGIN = "<!-- faber:funded-issue"
FUNDED_MARKER_SCHEMA = "faber.github.funded_issue_marker.v1"
FUNDED_TARGET_KINDS = {
    "github.issue",
    "github.label",
    "github.milestone",
    "github.repository",
    "verifier.compute",
}
_MARKER_PATTERN = re.compile(
    r"<!--\s*faber:task-contract\s*(\{.*?\})\s*-->",
    flags=re.DOTALL,
)
_FUNDED_MARKER_PATTERN = re.compile(
    r"<!--\s*faber:funded-issue\s*(\{.*?\})\s*-->",
    flags=re.DOTALL,
)


@dataclass(frozen=True)
class ContractMarker:
    schema: str
    contract_id: str
    contract_digest: str
    contract: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "contract_id": self.contract_id,
            "contract_digest": self.contract_digest,
            "contract": self.contract,
        }


@dataclass(frozen=True)
class FundedIssueMarker:
    schema: str
    contract_id: str
    contract_digest: str
    budget_id: str
    budget_digest: str
    funding_source_ref: str
    target_kind: str
    contract: dict[str, object]
    budget: dict[str, object]
    budget_allocation_policy: dict[str, object]
    verifier_spend_budget: dict[str, object] | None
    trace_quality_bonus_policy: dict[str, object]

    @property
    def settlement_authority(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "contract_id": self.contract_id,
            "contract_digest": self.contract_digest,
            "budget_id": self.budget_id,
            "budget_digest": self.budget_digest,
            "funding_source_ref": self.funding_source_ref,
            "target_kind": self.target_kind,
            "contract": self.contract,
            "budget": self.budget,
            "budget_allocation_policy": self.budget_allocation_policy,
            "verifier_spend_budget": self.verifier_spend_budget,
            "trace_quality_bonus_policy": self.trace_quality_bonus_policy,
            "settlement_authority": self.settlement_authority,
        }


def render_contract_marker(contract: TaskContract) -> str:
    payload = {
        "schema": MARKER_SCHEMA,
        "contract_id": contract.id,
        "contract_digest": contract.digest(),
        "contract": contract.to_dict(),
    }
    return f"{MARKER_BEGIN}\n{canonical_json(payload)}\n{MARKER_END}"


def parse_contract_marker(text: str) -> ContractMarker:
    match = _MARKER_PATTERN.search(text)
    if not match:
        raise ValidationError("Faber task contract marker not found")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValidationError("malformed Faber task contract marker") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Faber task contract marker must contain an object")
    schema = payload.get("schema")
    contract_id = payload.get("contract_id")
    contract_digest = payload.get("contract_digest")
    contract = payload.get("contract")
    if (
        schema != MARKER_SCHEMA
        or not isinstance(contract_id, str)
        or not isinstance(contract_digest, str)
        or not isinstance(contract, dict)
    ):
        raise ValidationError("Faber task contract marker is missing required fields")
    if contract.get("id") != contract_id:
        raise DigestMismatchError("Faber task contract marker id mismatch")
    actual_digest = sha256_digest(contract)
    if not hmac_safe_equal(actual_digest, contract_digest):
        raise DigestMismatchError("Faber task contract marker digest mismatch")
    return ContractMarker(
        schema=schema,
        contract_id=contract_id,
        contract_digest=contract_digest,
        contract=contract,
    )


def render_funded_issue_marker(
    contract: TaskContract,
    budget: object,
    *,
    funding_source_ref: str,
    budget_allocation_policy: dict[str, object] | None = None,
    trace_quality_bonus_policy: dict[str, object] | None = None,
) -> str:
    from faber.budgets import WorkBudget

    if not isinstance(budget, WorkBudget):
        raise ValidationError("budget must be a WorkBudget")
    if budget.target_kind not in FUNDED_TARGET_KINDS:
        raise ValidationError(f"budget target_kind must be one of {sorted(FUNDED_TARGET_KINDS)}")
    if not funding_source_ref:
        raise ValidationError("funding_source_ref must be a non-empty string")
    verifier_spend = budget.purpose_allocations.get("verifier_spend")
    payload = {
        "schema": FUNDED_MARKER_SCHEMA,
        "contract_id": contract.id,
        "contract_digest": contract.digest(),
        "budget_id": budget.id,
        "budget_digest": budget.digest(),
        "funding_source_ref": funding_source_ref,
        "target_kind": budget.target_kind,
        "contract": contract.to_dict(),
        "budget": budget.to_dict(),
        "budget_allocation_policy": budget_allocation_policy or {},
        "verifier_spend_budget": verifier_spend.to_dict() if verifier_spend else None,
        "trace_quality_bonus_policy": trace_quality_bonus_policy or {},
        "settlement_authority": False,
    }
    return f"{FUNDED_MARKER_BEGIN}\n{canonical_json(payload)}\n{MARKER_END}"


def parse_funded_issue_marker(text: str) -> FundedIssueMarker:
    matches = _FUNDED_MARKER_PATTERN.findall(text)
    if not matches:
        raise ValidationError("Faber funded issue marker not found")
    parsed_markers = [_parse_funded_marker_payload(match) for match in matches]
    canonical_markers = {canonical_json(marker.to_dict()) for marker in parsed_markers}
    if len(canonical_markers) != 1:
        raise ValidationError("conflicting duplicate Faber funded issue markers")
    return parsed_markers[0]


def _parse_funded_marker_payload(raw_payload: str) -> FundedIssueMarker:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValidationError("malformed Faber funded issue marker") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Faber funded issue marker must contain an object")
    required_strings = [
        "contract_id",
        "contract_digest",
        "budget_id",
        "budget_digest",
        "funding_source_ref",
        "target_kind",
    ]
    if payload.get("schema") != FUNDED_MARKER_SCHEMA or any(
        not isinstance(payload.get(field), str) for field in required_strings
    ):
        raise ValidationError("Faber funded issue marker is missing required fields")
    contract = payload.get("contract")
    budget = payload.get("budget")
    allocation_policy = payload.get("budget_allocation_policy", {})
    trace_bonus_policy = payload.get("trace_quality_bonus_policy", {})
    verifier_spend = payload.get("verifier_spend_budget")
    if not isinstance(contract, dict):
        raise ValidationError("Faber funded issue marker contract must be a mapping")
    if not isinstance(budget, dict):
        raise ValidationError("Faber funded issue marker budget must be a mapping")
    if not isinstance(allocation_policy, dict):
        raise ValidationError("budget_allocation_policy must be a mapping")
    if not isinstance(trace_bonus_policy, dict):
        raise ValidationError("trace_quality_bonus_policy must be a mapping")
    if verifier_spend is not None and not isinstance(verifier_spend, dict):
        raise ValidationError("verifier_spend_budget must be a mapping or null")
    contract_id = str(payload["contract_id"])
    budget_id = str(payload["budget_id"])
    contract_digest = str(payload["contract_digest"])
    budget_digest = str(payload["budget_digest"])
    target_kind = str(payload["target_kind"])
    if contract.get("id") != contract_id:
        raise DigestMismatchError("Faber funded issue marker contract id mismatch")
    if budget.get("id") != budget_id:
        raise DigestMismatchError("Faber funded issue marker budget id mismatch")
    if not hmac_safe_equal(sha256_digest(contract), contract_digest):
        raise DigestMismatchError("Faber funded issue marker contract digest mismatch")
    if not hmac_safe_equal(sha256_digest(budget), budget_digest):
        raise DigestMismatchError("Faber funded issue marker budget digest mismatch")
    if target_kind not in FUNDED_TARGET_KINDS or budget.get("target_kind") != target_kind:
        raise ValidationError("Faber funded issue marker target_kind is invalid")
    if payload.get("settlement_authority") is not False:
        raise ValidationError("Faber funded issue marker cannot grant settlement authority")
    return FundedIssueMarker(
        schema=FUNDED_MARKER_SCHEMA,
        contract_id=contract_id,
        contract_digest=contract_digest,
        budget_id=budget_id,
        budget_digest=budget_digest,
        funding_source_ref=str(payload["funding_source_ref"]),
        target_kind=target_kind,
        contract=contract,
        budget=budget,
        budget_allocation_policy=allocation_policy,
        verifier_spend_budget=verifier_spend,
        trace_quality_bonus_policy=trace_bonus_policy,
    )


def hmac_safe_equal(left: str, right: str) -> bool:
    # Keep comparisons constant-time even though markers are public text.
    import hmac

    return hmac.compare_digest(left, right)
