"""Provider-neutral proof-carrying patch records and fail-closed policy."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from faber import schemas
from faber.attempts import Attempt
from faber.canonical_json import canonical_json_bytes
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.receipts import VerificationReceipt
from faber.validation import (
    require_digest,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
)
from faber.verifiers import VerifierRun

CLAIM_SEVERITIES = {"low", "medium", "high", "critical"}
HIGH_SEVERITIES = {"high", "critical"}
MODEL_RUN_MODES = {"live", "replay"}
EVIDENCE_STATUSES = {"passed", "failed", "missing", "error"}
PROOF_VERDICTS = {"pass", "block", "human_review"}
ADVISORY_AUTHORITY = "advisory"
MAX_JSON_DEPTH = 16
MAX_JSON_BYTES = 16_384
MAX_JSON_ITEMS = 256

_EXECUTABLE_FIELD_NAMES = {
    "code",
    "command",
    "commandtemplate",
    "cwd",
    "executable",
    "path",
    "python",
    "script",
    "shell",
    "source",
    "workingdirectory",
}


class _FrozenList(tuple[object, ...]):
    """Internal immutable representation of a validated JSON list."""


def _record_payload(
    payload: Mapping[str, object],
    record_name: str,
    allowed: set[str],
) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ValidationError(f"{record_name} must be a mapping")
    if any(not isinstance(key, str) for key in payload):
        raise ValidationError(f"{record_name} keys must be strings")
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValidationError(f"{record_name} contains unknown fields: {unknown}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise ValidationError(f"{record_name} is missing required fields: {missing}")
    return payload


def _required_string(payload: Mapping[str, object], field: str) -> str:
    return require_non_empty_string(payload.get(field), field)


def _optional_string(payload: Mapping[str, object], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    return require_non_empty_string(value, field)


def _require_optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return require_non_empty_string(value, field)


def _required_bool(payload: Mapping[str, object], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def _require_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def _optional_nonnegative_int(payload: Mapping[str, object], field: str) -> int | None:
    value = payload.get(field)
    if value is None:
        return None
    return _require_nonnegative_int(value, field)


def _require_nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field} must be a non-negative integer")
    return value


def _string_values(
    value: object,
    field: str,
    *,
    allow_empty: bool = True,
    sort: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError(f"{field} must be a sequence of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(require_non_empty_string(item, f"{field}[{index}]"))
    if not allow_empty and not result:
        raise ValidationError(f"{field} must contain at least one string")
    if len(set(result)) != len(result):
        raise ValidationError(f"{field} must not contain duplicate values")
    return tuple(sorted(result) if sort else result)


def _compact_field_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(character for character in normalized.casefold() if character.isalnum())


def _field_name_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value)
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", normalized)
    return {
        token.casefold() for token in re.split(r"[^\w]+|_+", separated, flags=re.UNICODE) if token
    }


def _is_executable_field_name(value: str) -> bool:
    compact = _compact_field_name(value)
    if compact in _EXECUTABLE_FIELD_NAMES:
        return True
    dangerous_tokens = {
        "code",
        "command",
        "cwd",
        "executable",
        "path",
        "python",
        "script",
        "shell",
        "source",
    }
    return bool(_field_name_tokens(value) & dangerous_tokens)


def _freeze_json(
    value: object,
    field: str,
    *,
    depth: int,
    reject_executable_keys: bool,
) -> object:
    if depth > MAX_JSON_DEPTH:
        raise ValidationError(f"{field} exceeds the JSON depth limit")
    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(f"{field} must contain only finite JSON numbers")
        return value
    if isinstance(value, list | _FrozenList):
        if len(value) > MAX_JSON_ITEMS:
            raise ValidationError(f"{field} exceeds the JSON item limit")
        return _FrozenList(
            _freeze_json(
                item,
                f"{field}[{index}]",
                depth=depth + 1,
                reject_executable_keys=reject_executable_keys,
            )
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_ITEMS:
            raise ValidationError(f"{field} exceeds the JSON item limit")
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{field} must use a string key for every JSON object")
            if reject_executable_keys and _is_executable_field_name(key):
                raise ValidationError(f"{field} contains executable-looking field key {key!r}")
            frozen[key] = _freeze_json(
                item,
                f"{field}.{key}",
                depth=depth + 1,
                reject_executable_keys=reject_executable_keys,
            )
        return MappingProxyType(frozen)
    raise ValidationError(
        f"{field} must contain only JSON-compatible null, boolean, finite number, "
        "string, list, or string-key object values"
    )


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, _FrozenList):
        return [_thaw_json(item) for item in value]
    return value


def _bounded_json(
    value: object,
    field: str,
    *,
    reject_executable_keys: bool = False,
) -> object:
    frozen = _freeze_json(
        value,
        field,
        depth=0,
        reject_executable_keys=reject_executable_keys,
    )
    try:
        payload_size = len(canonical_json_bytes(_thaw_json(frozen)))
    except UnicodeEncodeError as exc:
        raise ValidationError(f"{field} contains text that cannot be encoded as UTF-8") from exc
    except ValidationError:
        raise
    except ValueError as exc:
        raise ValidationError(f"{field} must be canonically serializable JSON") from exc
    if payload_size > MAX_JSON_BYTES:
        raise ValidationError(f"{field} exceeds the bounded JSON byte limit")
    return frozen


def _mapping_json(
    value: object,
    field: str,
    *,
    reject_executable_keys: bool = False,
) -> Mapping[str, object]:
    frozen = _bounded_json(
        value,
        field,
        reject_executable_keys=reject_executable_keys,
    )
    if not isinstance(frozen, Mapping):
        raise ValidationError(f"{field} must be a JSON object")
    return frozen


@dataclass(frozen=True)
class ProofClaim:
    """One advisory, falsifiable behavioral claim bound to task requirements."""

    id: str
    statement: str
    severity: str
    requirement_refs: Sequence[str]
    evidence_required: bool
    risk_rationale: str | None = None
    schema: str = schemas.PROOF_CLAIM

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_CLAIM)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.statement, "statement")
        if self.severity not in CLAIM_SEVERITIES:
            raise ValidationError(f"severity must be one of {sorted(CLAIM_SEVERITIES)}")
        refs = _string_values(
            self.requirement_refs,
            "requirement_refs",
            allow_empty=False,
        )
        object.__setattr__(self, "requirement_refs", refs)
        _require_bool(self.evidence_required, "evidence_required")
        if self.severity in HIGH_SEVERITIES and not self.evidence_required:
            raise ValidationError("high and critical claims require executable evidence")
        object.__setattr__(
            self,
            "risk_rationale",
            _require_optional_string(self.risk_rationale, "risk_rationale"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "statement": self.statement,
            "severity": self.severity,
            "requirement_refs": list(self.requirement_refs),
            "evidence_required": self.evidence_required,
            "risk_rationale": self.risk_rationale,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofClaim:
        fields = {
            "schema",
            "id",
            "statement",
            "severity",
            "requirement_refs",
            "evidence_required",
            "risk_rationale",
        }
        value = _record_payload(payload, "ProofClaim", fields)
        return cls(
            schema=_required_string(value, "schema"),
            id=_required_string(value, "id"),
            statement=_required_string(value, "statement"),
            severity=_required_string(value, "severity"),
            requirement_refs=_string_values(
                value.get("requirement_refs"),
                "requirement_refs",
                allow_empty=False,
            ),
            evidence_required=_required_bool(value, "evidence_required"),
            risk_rationale=_optional_string(value, "risk_rationale"),
        )


@dataclass(frozen=True)
class ModelRunEvidence:
    """Auditable metadata for a live or replay advisory model run."""

    provider_adapter_id: str
    requested_model_id: str
    prompt_template_version: str
    request_digest: str
    structured_response_digest: str
    response_schema_version: str
    mode: str
    returned_model_id: str | None = None
    response_id: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    refusal: str | None = None
    error_code: str | None = None
    schema: str = schemas.MODEL_RUN_EVIDENCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.MODEL_RUN_EVIDENCE)
        require_non_empty_string(self.provider_adapter_id, "provider_adapter_id")
        require_non_empty_string(self.requested_model_id, "requested_model_id")
        require_non_empty_string(self.prompt_template_version, "prompt_template_version")
        require_digest(self.request_digest, "request_digest")
        require_digest(self.structured_response_digest, "structured_response_digest")
        require_non_empty_string(self.response_schema_version, "response_schema_version")
        if self.mode not in MODEL_RUN_MODES:
            raise ValidationError(f"mode must be one of {sorted(MODEL_RUN_MODES)}")
        for field_name in ("returned_model_id", "response_id", "refusal", "error_code"):
            object.__setattr__(
                self,
                field_name,
                _require_optional_string(getattr(self, field_name), field_name),
            )
        for field_name in ("latency_ms", "input_tokens", "output_tokens"):
            value = getattr(self, field_name)
            if value is not None:
                _require_nonnegative_int(value, field_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "provider_adapter_id": self.provider_adapter_id,
            "requested_model_id": self.requested_model_id,
            "returned_model_id": self.returned_model_id,
            "response_id": self.response_id,
            "prompt_template_version": self.prompt_template_version,
            "request_digest": self.request_digest,
            "structured_response_digest": self.structured_response_digest,
            "response_schema_version": self.response_schema_version,
            "mode": self.mode,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "refusal": self.refusal,
            "error_code": self.error_code,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ModelRunEvidence:
        fields = {
            "schema",
            "provider_adapter_id",
            "requested_model_id",
            "returned_model_id",
            "response_id",
            "prompt_template_version",
            "request_digest",
            "structured_response_digest",
            "response_schema_version",
            "mode",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "refusal",
            "error_code",
        }
        value = _record_payload(payload, "ModelRunEvidence", fields)
        return cls(
            schema=_required_string(value, "schema"),
            provider_adapter_id=_required_string(value, "provider_adapter_id"),
            requested_model_id=_required_string(value, "requested_model_id"),
            returned_model_id=_optional_string(value, "returned_model_id"),
            response_id=_optional_string(value, "response_id"),
            prompt_template_version=_required_string(value, "prompt_template_version"),
            request_digest=require_digest(value.get("request_digest"), "request_digest"),
            structured_response_digest=require_digest(
                value.get("structured_response_digest"),
                "structured_response_digest",
            ),
            response_schema_version=_required_string(value, "response_schema_version"),
            mode=_required_string(value, "mode"),
            latency_ms=_optional_nonnegative_int(value, "latency_ms"),
            input_tokens=_optional_nonnegative_int(value, "input_tokens"),
            output_tokens=_optional_nonnegative_int(value, "output_tokens"),
            refusal=_optional_string(value, "refusal"),
            error_code=_optional_string(value, "error_code"),
        )


@dataclass(frozen=True)
class ProofTemplateSelection:
    """Advisory binding from one claim to a catalog-owned proof template."""

    claim_id: str
    template_id: str
    template_version: str
    parameters: Mapping[str, object]
    expected_behavior: str
    rationale: str
    authority: str = ADVISORY_AUTHORITY
    schema: str = schemas.PROOF_TEMPLATE_SELECTION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_TEMPLATE_SELECTION)
        require_non_empty_string(self.claim_id, "claim_id")
        require_non_empty_string(self.template_id, "template_id")
        require_non_empty_string(self.template_version, "template_version")
        object.__setattr__(
            self,
            "parameters",
            _mapping_json(
                self.parameters,
                "parameters",
                reject_executable_keys=True,
            ),
        )
        require_non_empty_string(self.expected_behavior, "expected_behavior")
        require_non_empty_string(self.rationale, "rationale")
        if self.authority != ADVISORY_AUTHORITY:
            raise ValidationError("ProofTemplateSelection authority must be 'advisory'")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "claim_id": self.claim_id,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "parameters": _thaw_json(self.parameters),
            "expected_behavior": self.expected_behavior,
            "rationale": self.rationale,
            "authority": self.authority,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofTemplateSelection:
        fields = {
            "schema",
            "claim_id",
            "template_id",
            "template_version",
            "parameters",
            "expected_behavior",
            "rationale",
            "authority",
        }
        value = _record_payload(payload, "ProofTemplateSelection", fields)
        parameters = value.get("parameters")
        if not isinstance(parameters, Mapping):
            raise ValidationError("parameters must be a JSON object")
        return cls(
            schema=_required_string(value, "schema"),
            claim_id=_required_string(value, "claim_id"),
            template_id=_required_string(value, "template_id"),
            template_version=_required_string(value, "template_version"),
            parameters=parameters,
            expected_behavior=_required_string(value, "expected_behavior"),
            rationale=_required_string(value, "rationale"),
            authority=_required_string(value, "authority"),
        )


def _record_list(value: object, field: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list of records")
    records: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field}[{index}] must be a mapping")
        records.append(item)
    return records


@dataclass(frozen=True)
class ProofPlan:
    """Advisory proof plan bound to immutable task, attempt, patch, and catalog data."""

    task_contract_id: str
    task_contract_digest: str
    attempt_id: str
    attempt_digest: str
    base_revision: str
    candidate_revision: str
    diff_digest: str
    proof_catalog_digest: str
    prompt_template_version: str
    claims: Sequence[ProofClaim]
    selections: Sequence[ProofTemplateSelection]
    mandatory_claim_ids: Sequence[str]
    mandatory_template_ids: Sequence[str]
    uncovered_claim_ids: Sequence[str]
    human_review_recommended: bool
    model_run: ModelRunEvidence
    authority: str = ADVISORY_AUTHORITY
    schema: str = schemas.PROOF_PLAN

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_PLAN)
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_digest(self.task_contract_digest, "task_contract_digest")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_digest(self.attempt_digest, "attempt_digest")
        require_non_empty_string(self.base_revision, "base_revision")
        require_non_empty_string(self.candidate_revision, "candidate_revision")
        require_digest(self.diff_digest, "diff_digest")
        require_digest(self.proof_catalog_digest, "proof_catalog_digest")
        require_non_empty_string(self.prompt_template_version, "prompt_template_version")
        if not isinstance(self.model_run, ModelRunEvidence):
            raise ValidationError("model_run must be ModelRunEvidence")
        if self.prompt_template_version != self.model_run.prompt_template_version:
            raise ValidationError(
                "prompt_template_version must match model_run.prompt_template_version"
            )
        _require_bool(self.human_review_recommended, "human_review_recommended")
        if self.authority != ADVISORY_AUTHORITY:
            raise ValidationError("ProofPlan authority must be 'advisory'")

        claims = list(self.claims)
        if not claims:
            raise ValidationError("claims must contain at least one proof claim")
        if any(not isinstance(claim, ProofClaim) for claim in claims):
            raise ValidationError("claims must contain only ProofClaim records")
        claim_ids = [claim.id for claim in claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValidationError("duplicate proof claim IDs are not allowed")
        claims.sort(key=lambda claim: claim.id)
        object.__setattr__(self, "claims", tuple(claims))

        selections = list(self.selections)
        if any(not isinstance(selection, ProofTemplateSelection) for selection in selections):
            raise ValidationError("selections must contain only ProofTemplateSelection records")
        pairs = [(selection.claim_id, selection.template_id) for selection in selections]
        if len(set(pairs)) != len(pairs):
            raise ValidationError("duplicate claim/template selection pairs are not allowed")
        unknown_selection_claims = sorted(
            {selection.claim_id for selection in selections} - set(claim_ids)
        )
        if unknown_selection_claims:
            raise ValidationError(
                f"selections reference unknown claims: {unknown_selection_claims}"
            )
        selections.sort(
            key=lambda selection: (
                selection.claim_id,
                selection.template_id,
                selection.template_version,
            )
        )
        object.__setattr__(self, "selections", tuple(selections))

        mandatory_claim_ids = _string_values(
            self.mandatory_claim_ids,
            "mandatory_claim_ids",
        )
        missing_mandatory_claims = sorted(set(mandatory_claim_ids) - set(claim_ids))
        if missing_mandatory_claims:
            raise ValidationError(
                f"mandatory claim IDs are missing from claims: {missing_mandatory_claims}"
            )
        object.__setattr__(self, "mandatory_claim_ids", mandatory_claim_ids)

        mandatory_template_ids = _string_values(
            self.mandatory_template_ids,
            "mandatory_template_ids",
        )
        selected_template_ids = {selection.template_id for selection in selections}
        missing_mandatory_templates = sorted(set(mandatory_template_ids) - selected_template_ids)
        if missing_mandatory_templates:
            raise ValidationError(
                f"mandatory template IDs are missing from selections: {missing_mandatory_templates}"
            )
        object.__setattr__(self, "mandatory_template_ids", mandatory_template_ids)

        uncovered_claim_ids = _string_values(
            self.uncovered_claim_ids,
            "uncovered_claim_ids",
        )
        unknown_uncovered = sorted(set(uncovered_claim_ids) - set(claim_ids))
        if unknown_uncovered:
            raise ValidationError(
                f"uncovered claim IDs reference unknown claims: {unknown_uncovered}"
            )
        selected_claim_ids = {selection.claim_id for selection in selections}
        covered_and_uncovered = sorted(set(uncovered_claim_ids) & selected_claim_ids)
        if covered_and_uncovered:
            raise ValidationError(
                f"claims cannot be both selected and uncovered: {covered_and_uncovered}"
            )
        missing_required_selections = sorted(
            claim.id
            for claim in claims
            if claim.evidence_required
            and claim.id not in selected_claim_ids
            and claim.id not in uncovered_claim_ids
        )
        if missing_required_selections:
            raise ValidationError(
                "evidence-required claims without selections must be marked uncovered: "
                f"{missing_required_selections}"
            )
        object.__setattr__(self, "uncovered_claim_ids", uncovered_claim_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "attempt_id": self.attempt_id,
            "attempt_digest": self.attempt_digest,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "diff_digest": self.diff_digest,
            "proof_catalog_digest": self.proof_catalog_digest,
            "prompt_template_version": self.prompt_template_version,
            "claims": [claim.to_dict() for claim in self.claims],
            "selections": [selection.to_dict() for selection in self.selections],
            "mandatory_claim_ids": list(self.mandatory_claim_ids),
            "mandatory_template_ids": list(self.mandatory_template_ids),
            "uncovered_claim_ids": list(self.uncovered_claim_ids),
            "human_review_recommended": self.human_review_recommended,
            "model_run": self.model_run.to_dict(),
            "authority": self.authority,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofPlan:
        fields = {
            "schema",
            "task_contract_id",
            "task_contract_digest",
            "attempt_id",
            "attempt_digest",
            "base_revision",
            "candidate_revision",
            "diff_digest",
            "proof_catalog_digest",
            "prompt_template_version",
            "claims",
            "selections",
            "mandatory_claim_ids",
            "mandatory_template_ids",
            "uncovered_claim_ids",
            "human_review_recommended",
            "model_run",
            "authority",
        }
        value = _record_payload(payload, "ProofPlan", fields)
        model_run = value.get("model_run")
        if not isinstance(model_run, Mapping):
            raise ValidationError("model_run must be a mapping")
        return cls(
            schema=_required_string(value, "schema"),
            task_contract_id=_required_string(value, "task_contract_id"),
            task_contract_digest=require_digest(
                value.get("task_contract_digest"),
                "task_contract_digest",
            ),
            attempt_id=_required_string(value, "attempt_id"),
            attempt_digest=require_digest(value.get("attempt_digest"), "attempt_digest"),
            base_revision=_required_string(value, "base_revision"),
            candidate_revision=_required_string(value, "candidate_revision"),
            diff_digest=require_digest(value.get("diff_digest"), "diff_digest"),
            proof_catalog_digest=require_digest(
                value.get("proof_catalog_digest"),
                "proof_catalog_digest",
            ),
            prompt_template_version=_required_string(value, "prompt_template_version"),
            claims=[
                ProofClaim.from_dict(item) for item in _record_list(value.get("claims"), "claims")
            ],
            selections=[
                ProofTemplateSelection.from_dict(item)
                for item in _record_list(value.get("selections"), "selections")
            ],
            mandatory_claim_ids=_string_values(
                value.get("mandatory_claim_ids"),
                "mandatory_claim_ids",
            ),
            mandatory_template_ids=_string_values(
                value.get("mandatory_template_ids"),
                "mandatory_template_ids",
            ),
            uncovered_claim_ids=_string_values(
                value.get("uncovered_claim_ids"),
                "uncovered_claim_ids",
            ),
            human_review_recommended=_required_bool(
                value,
                "human_review_recommended",
            ),
            model_run=ModelRunEvidence.from_dict(model_run),
            authority=_required_string(value, "authority"),
        )


@dataclass(frozen=True)
class ProofEvidence:
    """One bounded proof-execution outcome linked to existing verifier authority."""

    proof_plan_digest: str
    claim_id: str
    selection_digest: str
    status: str
    verifier_id: str
    verifier_version: str
    verifier_run_digest: str | None
    verification_receipt_digest: str | None
    expected_summary: object
    observed_summary: object
    counterexample_summary: object | None
    failure_reason_codes: Sequence[str]
    schema: str = schemas.PROOF_EVIDENCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_EVIDENCE)
        require_digest(self.proof_plan_digest, "proof_plan_digest")
        require_non_empty_string(self.claim_id, "claim_id")
        require_digest(self.selection_digest, "selection_digest")
        if self.status not in EVIDENCE_STATUSES:
            raise ValidationError(f"status must be one of {sorted(EVIDENCE_STATUSES)}")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_non_empty_string(self.verifier_version, "verifier_version")
        require_optional_digest(self.verifier_run_digest, "verifier_run_digest")
        require_optional_digest(
            self.verification_receipt_digest,
            "verification_receipt_digest",
        )
        object.__setattr__(
            self,
            "expected_summary",
            _bounded_json(self.expected_summary, "expected_summary"),
        )
        object.__setattr__(
            self,
            "observed_summary",
            _bounded_json(self.observed_summary, "observed_summary"),
        )
        object.__setattr__(
            self,
            "counterexample_summary",
            _bounded_json(self.counterexample_summary, "counterexample_summary"),
        )
        reason_codes = _string_values(
            self.failure_reason_codes,
            "failure_reason_codes",
        )
        if self.status == "passed" and reason_codes:
            raise ValidationError("passed evidence cannot contain failure reason codes")
        if self.status == "passed" and self.counterexample_summary is not None:
            raise ValidationError("passed evidence cannot contain a counterexample summary")
        if self.status in {"failed", "error"} and not reason_codes:
            raise ValidationError("failed or errored evidence requires failure reason codes")
        object.__setattr__(self, "failure_reason_codes", reason_codes)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "proof_plan_digest": self.proof_plan_digest,
            "claim_id": self.claim_id,
            "selection_digest": self.selection_digest,
            "status": self.status,
            "verifier_id": self.verifier_id,
            "verifier_version": self.verifier_version,
            "verifier_run_digest": self.verifier_run_digest,
            "verification_receipt_digest": self.verification_receipt_digest,
            "expected_summary": _thaw_json(self.expected_summary),
            "observed_summary": _thaw_json(self.observed_summary),
            "counterexample_summary": _thaw_json(self.counterexample_summary),
            "failure_reason_codes": list(self.failure_reason_codes),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofEvidence:
        fields = {
            "schema",
            "proof_plan_digest",
            "claim_id",
            "selection_digest",
            "status",
            "verifier_id",
            "verifier_version",
            "verifier_run_digest",
            "verification_receipt_digest",
            "expected_summary",
            "observed_summary",
            "counterexample_summary",
            "failure_reason_codes",
        }
        value = _record_payload(payload, "ProofEvidence", fields)
        return cls(
            schema=_required_string(value, "schema"),
            proof_plan_digest=require_digest(
                value.get("proof_plan_digest"),
                "proof_plan_digest",
            ),
            claim_id=_required_string(value, "claim_id"),
            selection_digest=require_digest(
                value.get("selection_digest"),
                "selection_digest",
            ),
            status=_required_string(value, "status"),
            verifier_id=_required_string(value, "verifier_id"),
            verifier_version=_required_string(value, "verifier_version"),
            verifier_run_digest=require_optional_digest(
                value.get("verifier_run_digest"),
                "verifier_run_digest",
            ),
            verification_receipt_digest=require_optional_digest(
                value.get("verification_receipt_digest"),
                "verification_receipt_digest",
            ),
            expected_summary=value.get("expected_summary"),
            observed_summary=value.get("observed_summary"),
            counterexample_summary=value.get("counterexample_summary"),
            failure_reason_codes=_string_values(
                value.get("failure_reason_codes"),
                "failure_reason_codes",
            ),
        )


@dataclass(frozen=True)
class ProofPolicy:
    """Repository-owner policy independent of advisory model output."""

    name: str
    version: str
    approved_verifier_ids: Sequence[str]
    mandatory_claim_ids: Sequence[str] = ()
    mandatory_template_ids: Sequence[str] = ()
    mandatory_verifier_ids: Sequence[str] = ()
    minimum_authoritative_outcomes: int = 1

    def __post_init__(self) -> None:
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.version, "version")
        for field_name in (
            "approved_verifier_ids",
            "mandatory_claim_ids",
            "mandatory_template_ids",
            "mandatory_verifier_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _string_values(getattr(self, field_name), field_name),
            )
        _require_nonnegative_int(
            self.minimum_authoritative_outcomes,
            "minimum_authoritative_outcomes",
        )
        if self.minimum_authoritative_outcomes < 1:
            raise ValidationError("minimum_authoritative_outcomes must be a positive integer")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "approved_verifier_ids": list(self.approved_verifier_ids),
            "mandatory_claim_ids": list(self.mandatory_claim_ids),
            "mandatory_template_ids": list(self.mandatory_template_ids),
            "mandatory_verifier_ids": list(self.mandatory_verifier_ids),
            "minimum_authoritative_outcomes": self.minimum_authoritative_outcomes,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofPolicy:
        fields = {
            "name",
            "version",
            "approved_verifier_ids",
            "mandatory_claim_ids",
            "mandatory_template_ids",
            "mandatory_verifier_ids",
            "minimum_authoritative_outcomes",
        }
        value = _record_payload(payload, "ProofPolicy", fields)
        return cls(
            name=_required_string(value, "name"),
            version=_required_string(value, "version"),
            approved_verifier_ids=_string_values(
                value.get("approved_verifier_ids"),
                "approved_verifier_ids",
            ),
            mandatory_claim_ids=_string_values(
                value.get("mandatory_claim_ids"),
                "mandatory_claim_ids",
            ),
            mandatory_template_ids=_string_values(
                value.get("mandatory_template_ids"),
                "mandatory_template_ids",
            ),
            mandatory_verifier_ids=_string_values(
                value.get("mandatory_verifier_ids"),
                "mandatory_verifier_ids",
            ),
            minimum_authoritative_outcomes=_require_nonnegative_int(
                value.get("minimum_authoritative_outcomes"),
                "minimum_authoritative_outcomes",
            ),
        )


def _digest_values(value: object, field: str) -> tuple[str, ...]:
    digests = _string_values(value, field)
    for index, digest in enumerate(digests):
        require_digest(digest, f"{field}[{index}]")
    return digests


@dataclass(frozen=True)
class ProofDecision:
    """Deterministic aggregate verdict derived from authoritative proof evidence."""

    proof_plan_digest: str
    task_contract_id: str
    task_contract_digest: str
    attempt_id: str
    attempt_digest: str
    evidence_digests: Sequence[str]
    verdict: str
    reason_codes: Sequence[str]
    passed_claim_ids: Sequence[str]
    failed_claim_ids: Sequence[str]
    missing_claim_ids: Sequence[str]
    uncovered_claim_ids: Sequence[str]
    authoritative_receipt_digests: Sequence[str]
    policy_name: str
    policy_version: str
    schema: str = schemas.PROOF_DECISION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PROOF_DECISION)
        require_digest(self.proof_plan_digest, "proof_plan_digest")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_digest(self.task_contract_digest, "task_contract_digest")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_digest(self.attempt_digest, "attempt_digest")
        object.__setattr__(
            self,
            "evidence_digests",
            _digest_values(self.evidence_digests, "evidence_digests"),
        )
        if self.verdict not in PROOF_VERDICTS:
            raise ValidationError(f"verdict must be one of {sorted(PROOF_VERDICTS)}")
        reason_codes = _string_values(
            self.reason_codes,
            "reason_codes",
            allow_empty=False,
        )
        object.__setattr__(self, "reason_codes", reason_codes)
        for field_name in (
            "passed_claim_ids",
            "failed_claim_ids",
            "missing_claim_ids",
            "uncovered_claim_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _string_values(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "authoritative_receipt_digests",
            _digest_values(
                self.authoritative_receipt_digests,
                "authoritative_receipt_digests",
            ),
        )
        require_non_empty_string(self.policy_name, "policy_name")
        require_non_empty_string(self.policy_version, "policy_version")

        passed = set(self.passed_claim_ids)
        failed = set(self.failed_claim_ids)
        missing = set(self.missing_claim_ids)
        if passed & failed or passed & missing or failed & missing:
            raise ValidationError(
                "inconsistent decision: passed, failed, and missing claim lists must be disjoint"
            )
        if self.verdict == "pass":
            if failed or missing or self.uncovered_claim_ids:
                raise ValidationError(
                    "pass decision cannot contain failed, missing, or uncovered claims"
                )
            if not passed or not self.evidence_digests or not self.authoritative_receipt_digests:
                raise ValidationError("pass decision requires non-empty authoritative evidence")
            if set(reason_codes) != {"proof_passed"}:
                raise ValidationError("pass decision reason codes must contain only proof_passed")
        if (
            self.verdict == "block"
            and not failed
            and "mandatory_verifier_failed" not in self.reason_codes
        ):
            raise ValidationError(
                "block decision requires a failed claim or mandatory verifier failure"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "proof_plan_digest": self.proof_plan_digest,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "attempt_id": self.attempt_id,
            "attempt_digest": self.attempt_digest,
            "evidence_digests": list(self.evidence_digests),
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "passed_claim_ids": list(self.passed_claim_ids),
            "failed_claim_ids": list(self.failed_claim_ids),
            "missing_claim_ids": list(self.missing_claim_ids),
            "uncovered_claim_ids": list(self.uncovered_claim_ids),
            "authoritative_receipt_digests": list(self.authoritative_receipt_digests),
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ProofDecision:
        fields = {
            "schema",
            "proof_plan_digest",
            "task_contract_id",
            "task_contract_digest",
            "attempt_id",
            "attempt_digest",
            "evidence_digests",
            "verdict",
            "reason_codes",
            "passed_claim_ids",
            "failed_claim_ids",
            "missing_claim_ids",
            "uncovered_claim_ids",
            "authoritative_receipt_digests",
            "policy_name",
            "policy_version",
        }
        value = _record_payload(payload, "ProofDecision", fields)
        return cls(
            schema=_required_string(value, "schema"),
            proof_plan_digest=require_digest(
                value.get("proof_plan_digest"),
                "proof_plan_digest",
            ),
            task_contract_id=_required_string(value, "task_contract_id"),
            task_contract_digest=require_digest(
                value.get("task_contract_digest"),
                "task_contract_digest",
            ),
            attempt_id=_required_string(value, "attempt_id"),
            attempt_digest=require_digest(value.get("attempt_digest"), "attempt_digest"),
            evidence_digests=_digest_values(
                value.get("evidence_digests"),
                "evidence_digests",
            ),
            verdict=_required_string(value, "verdict"),
            reason_codes=_string_values(
                value.get("reason_codes"),
                "reason_codes",
                allow_empty=False,
            ),
            passed_claim_ids=_string_values(
                value.get("passed_claim_ids"),
                "passed_claim_ids",
            ),
            failed_claim_ids=_string_values(
                value.get("failed_claim_ids"),
                "failed_claim_ids",
            ),
            missing_claim_ids=_string_values(
                value.get("missing_claim_ids"),
                "missing_claim_ids",
            ),
            uncovered_claim_ids=_string_values(
                value.get("uncovered_claim_ids"),
                "uncovered_claim_ids",
            ),
            authoritative_receipt_digests=_digest_values(
                value.get("authoritative_receipt_digests"),
                "authoritative_receipt_digests",
            ),
            policy_name=_required_string(value, "policy_name"),
            policy_version=_required_string(value, "policy_version"),
        )


def _authority_context_is_bound(
    plan: ProofPlan,
    task_contract: TaskContract | None,
    attempt: Attempt | None,
    reasons: set[str],
) -> bool:
    valid = True
    if task_contract is None:
        reasons.add("authority_task_contract_missing")
        valid = False
    else:
        if (
            task_contract.id != plan.task_contract_id
            or task_contract.digest() != plan.task_contract_digest
        ):
            reasons.add("task_contract_binding_mismatch")
            valid = False
    if attempt is None:
        reasons.add("authority_attempt_missing")
        valid = False
    else:
        if (
            attempt.id != plan.attempt_id
            or attempt.digest() != plan.attempt_digest
            or attempt.base_revision != plan.base_revision
            or attempt.candidate_revision != plan.candidate_revision
            or attempt.patch_digest != plan.diff_digest
            or attempt.task_contract_id != plan.task_contract_id
        ):
            reasons.add("attempt_binding_mismatch")
            valid = False
    return valid


def _authority_records_by_digest(
    records: Sequence[VerifierRun] | Sequence[VerificationReceipt],
    expected_type: type[VerifierRun] | type[VerificationReceipt],
    field: str,
) -> dict[str, VerifierRun | VerificationReceipt]:
    if isinstance(records, str | bytes | bytearray) or not isinstance(records, Sequence):
        raise ValidationError(f"{field} must be a sequence")
    result: dict[str, VerifierRun | VerificationReceipt] = {}
    for index, record in enumerate(records):
        if not isinstance(record, expected_type):
            raise ValidationError(f"{field}[{index}] has the wrong record type")
        result[record.digest()] = record
    return result


def _receipt_binds_run_and_context(
    receipt: VerificationReceipt,
    run: VerifierRun,
    task_contract: TaskContract,
    attempt: Attempt,
) -> bool:
    run_reasons_valid = (
        isinstance(run.failure_reasons, Sequence)
        and not isinstance(run.failure_reasons, str | bytes | bytearray)
        and all(isinstance(reason, str) and reason.strip() for reason in run.failure_reasons)
    )
    receipt_reasons_valid = (
        isinstance(receipt.failure_reasons, Sequence)
        and not isinstance(receipt.failure_reasons, str | bytes | bytearray)
        and all(isinstance(reason, str) and reason.strip() for reason in receipt.failure_reasons)
    )
    return (
        isinstance(run.passed, bool)
        and isinstance(receipt.accepted, bool)
        and run_reasons_valid
        and receipt_reasons_valid
        and (not run.passed or not run.failure_reasons)
        and (not receipt.accepted or not receipt.failure_reasons)
        and receipt.task_contract_id == task_contract.id
        and receipt.task_contract_digest == task_contract.digest()
        and receipt.attempt_id == attempt.id
        and receipt.worker_id == attempt.worker_id
        and receipt.base_revision == attempt.base_revision
        and receipt.candidate_revision == attempt.candidate_revision
        and receipt.verifier_id == run.verifier_id
        and receipt.verifier_digest == run.verifier_digest()
        and receipt.result_digest == run.result_digest()
        and receipt.accepted == run.passed
        and receipt.metrics == run.metrics
        and receipt.failure_reasons == run.failure_reasons
    )


def _resolve_authoritative_outcome(
    proof: ProofEvidence,
    *,
    context_bound: bool,
    task_contract: TaskContract | None,
    attempt: Attempt | None,
    policy: ProofPolicy,
    runs: Mapping[str, VerifierRun | VerificationReceipt],
    receipts: Mapping[str, VerifierRun | VerificationReceipt],
    reasons: set[str],
) -> tuple[str | None, str | None]:
    if proof.verifier_run_digest is None or proof.verification_receipt_digest is None:
        if proof.status == "missing":
            reasons.add("required_evidence_missing")
        elif proof.status == "error":
            reasons.add("required_evidence_error")
        reasons.add("authoritative_record_digest_missing")
        return None, None
    run = runs.get(proof.verifier_run_digest)
    receipt = receipts.get(proof.verification_receipt_digest)
    if not isinstance(run, VerifierRun) or not isinstance(receipt, VerificationReceipt):
        reasons.add("authoritative_record_unresolved")
        return None, None
    if not context_bound or task_contract is None or attempt is None:
        reasons.add("authority_context_unbound")
        return None, None
    if proof.verifier_id not in policy.approved_verifier_ids:
        reasons.add("verifier_not_approved_by_policy")
        return None, None
    if run.verifier_id != proof.verifier_id or run.version != proof.verifier_version:
        reasons.add("verifier_run_binding_mismatch")
        return None, None
    if not _receipt_binds_run_and_context(receipt, run, task_contract, attempt):
        reasons.add("verification_receipt_binding_mismatch")
        return None, None
    actual = "passed" if run.passed else "failed"
    if proof.status != actual:
        reasons.add("evidence_status_mismatch")
        if proof.status == "missing":
            reasons.add("required_evidence_missing")
        elif proof.status == "error":
            reasons.add("required_evidence_error")
    return actual, receipt.digest()


def decide_proof(
    plan: ProofPlan,
    evidence: Sequence[ProofEvidence],
    policy: ProofPolicy,
    *,
    task_contract: TaskContract | None = None,
    attempt: Attempt | None = None,
    verifier_runs: Sequence[VerifierRun] = (),
    verification_receipts: Sequence[VerificationReceipt] = (),
) -> ProofDecision:
    """Apply deterministic BLOCK > HUMAN_REVIEW > PASS precedence.

    Model output and digest-shaped strings are never authority. A passing or blocking
    outcome is authoritative only after resolving the platform-owned contract,
    attempt, verifier run, and verification receipt supplied to this pure function.
    """

    if not isinstance(plan, ProofPlan):
        raise ValidationError("plan must be a validated ProofPlan")
    if not isinstance(policy, ProofPolicy):
        raise ValidationError("policy must be a validated ProofPolicy")
    if isinstance(evidence, str | bytes | bytearray) or not isinstance(evidence, Sequence):
        raise ValidationError("evidence must be a sequence of ProofEvidence records")
    proofs = list(evidence)
    if any(not isinstance(item, ProofEvidence) for item in proofs):
        raise ValidationError("evidence must contain only ProofEvidence records")

    reasons: set[str] = set()
    plan_digest = plan.digest()
    context_bound = _authority_context_is_bound(plan, task_contract, attempt, reasons)
    run_records = _authority_records_by_digest(
        verifier_runs,
        VerifierRun,
        "verifier_runs",
    )
    receipt_records = _authority_records_by_digest(
        verification_receipts,
        VerificationReceipt,
        "verification_receipts",
    )

    claim_by_id = {claim.id: claim for claim in plan.claims}
    selection_by_digest = {selection.digest(): selection for selection in plan.selections}
    selected_claim_ids = {selection.claim_id for selection in plan.selections}
    selected_template_ids = {selection.template_id for selection in plan.selections}

    missing_policy_claims = set(policy.mandatory_claim_ids) - set(claim_by_id)
    missing_policy_templates = set(policy.mandatory_template_ids) - selected_template_ids
    if missing_policy_claims:
        reasons.add("policy_mandatory_claim_missing")
    if missing_policy_templates:
        reasons.add("policy_mandatory_template_missing")
    if set(policy.mandatory_claim_ids) - set(plan.mandatory_claim_ids):
        reasons.add("advisory_plan_weakened_mandatory_claims")
    if set(policy.mandatory_template_ids) - set(plan.mandatory_template_ids):
        reasons.add("advisory_plan_weakened_mandatory_templates")
    if not policy.approved_verifier_ids:
        reasons.add("policy_has_no_approved_verifiers")
    if plan.model_run.refusal is not None:
        reasons.add("model_refusal")
    if plan.model_run.error_code is not None:
        reasons.add("model_terminal_error")
    if plan.human_review_recommended:
        reasons.add("model_recommends_human_review")
    if plan.uncovered_claim_ids:
        reasons.add("plan_has_uncovered_claims")

    grouped: dict[str, list[ProofEvidence]] = {digest: [] for digest in selection_by_digest}
    for proof in proofs:
        if proof.proof_plan_digest != plan_digest:
            reasons.add("evidence_plan_binding_mismatch")
            continue
        claim = claim_by_id.get(proof.claim_id)
        selection = selection_by_digest.get(proof.selection_digest)
        if claim is None:
            reasons.add("evidence_references_unknown_claim")
            continue
        if selection is None or selection.claim_id != proof.claim_id:
            reasons.add("evidence_references_unknown_selection")
            continue
        grouped[proof.selection_digest].append(proof)

    failed_claim_ids: set[str] = set()
    missing_claim_ids: set[str] = set(missing_policy_claims)
    passed_selection_claims: dict[str, int] = {}
    selection_counts: dict[str, int] = {}
    authoritative_receipts: set[str] = set()
    authoritative_outcomes = 0
    verifier_outcomes: dict[str, list[str]] = {}

    for selection_digest, selection in selection_by_digest.items():
        selection_counts[selection.claim_id] = selection_counts.get(selection.claim_id, 0) + 1
        candidates = grouped[selection_digest]
        if not candidates:
            reasons.add("selected_evidence_missing")
            missing_claim_ids.add(selection.claim_id)
            continue
        if len(candidates) > 1:
            reasons.add("duplicate_or_contradictory_evidence")
            missing_claim_ids.add(selection.claim_id)
        outcomes: list[str] = []
        for proof in candidates:
            outcome, receipt_digest = _resolve_authoritative_outcome(
                proof,
                context_bound=context_bound,
                task_contract=task_contract,
                attempt=attempt,
                policy=policy,
                runs=run_records,
                receipts=receipt_records,
                reasons=reasons,
            )
            if outcome is None:
                missing_claim_ids.add(selection.claim_id)
                continue
            outcomes.append(outcome)
            authoritative_outcomes += 1
            verifier_outcomes.setdefault(proof.verifier_id, []).append(outcome)
            if receipt_digest is not None:
                authoritative_receipts.add(receipt_digest)
        if "failed" in outcomes:
            failed_claim_ids.add(selection.claim_id)
            missing_claim_ids.discard(selection.claim_id)
        elif len(candidates) == 1 and outcomes == ["passed"]:
            passed_selection_claims[selection.claim_id] = (
                passed_selection_claims.get(selection.claim_id, 0) + 1
            )

    required_claim_ids = {claim.id for claim in plan.claims if claim.evidence_required}
    required_claim_ids.update(plan.mandatory_claim_ids)
    required_claim_ids.update(policy.mandatory_claim_ids)
    required_claim_ids.update(selected_claim_ids)
    required_claim_ids.update(plan.uncovered_claim_ids)
    for claim_id in required_claim_ids:
        if claim_id not in claim_by_id or claim_id not in selected_claim_ids:
            missing_claim_ids.add(claim_id)

    passed_claim_ids = {
        claim_id
        for claim_id, expected_count in selection_counts.items()
        if passed_selection_claims.get(claim_id, 0) == expected_count
        and claim_id not in failed_claim_ids
        and claim_id not in missing_claim_ids
    }

    required_verifier_ids = set(policy.mandatory_verifier_ids)
    if task_contract is not None:
        required_verifier_ids.update(task_contract.verifier_ids)
    mandatory_verifier_failed = False
    for verifier_id in required_verifier_ids:
        if verifier_id not in policy.approved_verifier_ids:
            reasons.add("mandatory_verifier_not_approved")
        resolved_outcomes: set[str] = set(verifier_outcomes.get(verifier_id, []))
        if (
            context_bound
            and task_contract is not None
            and attempt is not None
            and verifier_id in policy.approved_verifier_ids
        ):
            for run_record in run_records.values():
                if not isinstance(run_record, VerifierRun):
                    continue
                if run_record.verifier_id != verifier_id:
                    continue
                for receipt_record in receipt_records.values():
                    if not isinstance(receipt_record, VerificationReceipt):
                        continue
                    if _receipt_binds_run_and_context(
                        receipt_record,
                        run_record,
                        task_contract,
                        attempt,
                    ):
                        authoritative_receipts.add(receipt_record.digest())
                        resolved_outcomes.add("passed" if run_record.passed else "failed")
        if not resolved_outcomes:
            reasons.add("mandatory_verifier_evidence_missing")
        if "failed" in resolved_outcomes:
            reasons.add("mandatory_verifier_failed")
            mandatory_verifier_failed = True
        if len(resolved_outcomes) > 1:
            reasons.add("mandatory_verifier_evidence_contradictory")

    if authoritative_outcomes < policy.minimum_authoritative_outcomes:
        reasons.add("minimum_authoritative_outcomes_not_met")
    if missing_claim_ids:
        reasons.add("required_claim_evidence_incomplete")
    if failed_claim_ids:
        reasons.add("authoritative_claim_failure")

    uncovered_claim_ids = set(plan.uncovered_claim_ids) | missing_policy_claims
    if failed_claim_ids or mandatory_verifier_failed:
        verdict = "block"
    elif reasons:
        verdict = "human_review"
        reasons.add("human_review_required")
    else:
        verdict = "pass"
        reasons.add("proof_passed")

    return ProofDecision(
        proof_plan_digest=plan_digest,
        task_contract_id=plan.task_contract_id,
        task_contract_digest=plan.task_contract_digest,
        attempt_id=plan.attempt_id,
        attempt_digest=plan.attempt_digest,
        evidence_digests=sorted({proof.digest() for proof in proofs}),
        verdict=verdict,
        reason_codes=sorted(reasons),
        passed_claim_ids=sorted(passed_claim_ids - failed_claim_ids - missing_claim_ids),
        failed_claim_ids=sorted(failed_claim_ids),
        missing_claim_ids=sorted(missing_claim_ids - failed_claim_ids),
        uncovered_claim_ids=sorted(uncovered_claim_ids),
        authoritative_receipt_digests=sorted(authoritative_receipts),
        policy_name=policy.name,
        policy_version=policy.version,
    )
