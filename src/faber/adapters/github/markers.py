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
_MARKER_PATTERN = re.compile(
    r"<!--\s*faber:task-contract\s*(\{.*?\})\s*-->",
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


def hmac_safe_equal(left: str, right: str) -> bool:
    # Keep comparisons constant-time even though markers are public text.
    import hmac

    return hmac.compare_digest(left, right)
