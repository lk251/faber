"""Canonical, SDK-free replay support for the OpenAI proof planner."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from faber.canonical_json import canonical_json, canonical_json_bytes
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_planning import (
    ProofPlanningError,
    ProofPlanningRequest,
    ProofPlanningResult,
    ProviderPlanningResponse,
    materialize_proof_plan,
)
from faber.validation import require_digest, require_non_empty_string

from .prompt import DEFAULT_MODEL
from .proof_planner import (
    PROVIDER_ADAPTER_ID,
    _contains_sensitive_content,
    parse_structured_response_text,
    validate_openai_request_context,
    with_terminal_model_error,
)

OPENAI_PROOF_REPLAY_SCHEMA = "faber.openai.proof_planner_replay.v1"
MAX_REPLAY_BUNDLE_BYTES = 131_072
MAX_JSON_INTEGER = (1 << 63) - 1
MAX_JSON_DEPTH = 16


def _strict_integer(value: str) -> int:
    parsed = int(value)
    if abs(parsed) > MAX_JSON_INTEGER:
        raise ValueError("JSON integer exceeds the signed 64-bit limit")
    return parsed


def _strict_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON number must be finite")
    return parsed


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _strict_json_object(value: str | bytes) -> Mapping[str, object]:
    if isinstance(value, bytes):
        if len(value) > MAX_REPLAY_BUNDLE_BYTES:
            raise ValidationError("replay bundle exceeds the byte limit")
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise ValidationError("replay bundle must be valid UTF-8") from None
    elif isinstance(value, str):
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise ValidationError("replay bundle must be valid UTF-8") from None
        if len(encoded) > MAX_REPLAY_BUNDLE_BYTES:
            raise ValidationError("replay bundle exceeds the byte limit")
        text = value
    else:
        raise ValidationError("replay bundle must be JSON text or UTF-8 bytes")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_constant,
            parse_int=_strict_integer,
            parse_float=_strict_float,
        )
        canonical_json_bytes(payload)
    except (ValueError, RecursionError):
        raise ValidationError("replay bundle must be strict canonicalizable JSON") from None
    if not isinstance(payload, Mapping):
        raise ValidationError("replay bundle root must be an object")
    return payload


def _freeze_json(value: object, field: str, *, depth: int = 0) -> object:
    if depth > MAX_JSON_DEPTH:
        raise ValidationError(f"{field} exceeds the JSON nesting limit")
    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_JSON_INTEGER:
            raise ValidationError(f"{field} contains an integer outside the supported range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(f"{field} contains a non-finite number")
        return value
    if isinstance(value, list | tuple):
        return tuple(
            _freeze_json(item, f"{field}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{field} must use string object keys")
            frozen[key] = _freeze_json(item, f"{field}.{key}", depth=depth + 1)
        return MappingProxyType(frozen)
    raise ValidationError(f"{field} must contain JSON-compatible values")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return require_non_empty_string(value, field)


def _optional_count(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field} must be a non-negative integer or null")
    return value


@dataclass(frozen=True)
class OpenAIProofReplayBundle:
    """Sanitized provider record bound to one exact planning context."""

    created_at: str
    provider: str
    requested_model: str
    prompt_template_version: str
    prompt_template_digest: str
    response_schema_version: str
    response_schema_digest: str
    request_digest: str
    catalog_digest: str
    sanitized_structured_response: Mapping[str, object]
    structured_response_digest: str
    returned_model: str | None = None
    response_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    refusal: str | None = None
    error_code: str | None = None
    schema: str = OPENAI_PROOF_REPLAY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != OPENAI_PROOF_REPLAY_SCHEMA:
            raise ValidationError(
                f"schema must be {OPENAI_PROOF_REPLAY_SCHEMA!r}, got {self.schema!r}"
            )
        for field in (
            "created_at",
            "provider",
            "requested_model",
            "prompt_template_version",
            "response_schema_version",
        ):
            require_non_empty_string(getattr(self, field), field)
        for field in (
            "prompt_template_digest",
            "response_schema_digest",
            "request_digest",
            "catalog_digest",
            "structured_response_digest",
        ):
            require_digest(getattr(self, field), field)
        for field in ("returned_model", "response_id", "refusal", "error_code"):
            object.__setattr__(self, field, _optional_string(getattr(self, field), field))
        for field in ("input_tokens", "output_tokens", "latency_ms"):
            _optional_count(getattr(self, field), field)
        metadata = {
            "created_at": self.created_at,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "returned_model": self.returned_model,
            "response_id": self.response_id,
            "refusal": self.refusal,
            "error_code": self.error_code,
        }
        if _contains_sensitive_content(metadata):
            raise ValidationError("replay bundle metadata contains secret-like text")
        bounded_response = _freeze_json(
            self.sanitized_structured_response,
            "sanitized_structured_response",
        )
        parsed_response = parse_structured_response_text(
            canonical_json(_thaw_json(bounded_response))
        )
        frozen = _freeze_json(parsed_response, "sanitized_structured_response")
        if not isinstance(frozen, Mapping):
            raise ValidationError("sanitized_structured_response must be a JSON object")
        object.__setattr__(self, "sanitized_structured_response", frozen)
        if len(canonical_json_bytes(self.to_dict())) > MAX_REPLAY_BUNDLE_BYTES:
            raise ValidationError("replay bundle exceeds the byte limit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "created_at": self.created_at,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "returned_model": self.returned_model,
            "response_id": self.response_id,
            "prompt_template_version": self.prompt_template_version,
            "prompt_template_digest": self.prompt_template_digest,
            "response_schema_version": self.response_schema_version,
            "response_schema_digest": self.response_schema_digest,
            "request_digest": self.request_digest,
            "catalog_digest": self.catalog_digest,
            "sanitized_structured_response": _thaw_json(self.sanitized_structured_response),
            "structured_response_digest": self.structured_response_digest,
            "token_usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
            },
            "latency_ms": self.latency_ms,
            "refusal": self.refusal,
            "error_code": self.error_code,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    def sanitized_structured_response_dict(self) -> dict[str, object]:
        value = _thaw_json(self.sanitized_structured_response)
        if not isinstance(value, dict):  # guarded by __post_init__
            raise AssertionError("frozen replay response must thaw to an object")
        return value

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> OpenAIProofReplayBundle:
        fields = {
            "schema",
            "created_at",
            "provider",
            "requested_model",
            "returned_model",
            "response_id",
            "prompt_template_version",
            "prompt_template_digest",
            "response_schema_version",
            "response_schema_digest",
            "request_digest",
            "catalog_digest",
            "sanitized_structured_response",
            "structured_response_digest",
            "token_usage",
            "latency_ms",
            "refusal",
            "error_code",
        }
        if not isinstance(payload, Mapping):
            raise ValidationError("OpenAIProofReplayBundle must be an object")
        unknown = sorted(set(payload) - fields)
        missing = sorted(fields - set(payload))
        if unknown:
            raise ValidationError("OpenAIProofReplayBundle contains unknown fields")
        if missing:
            raise ValidationError(f"OpenAIProofReplayBundle is missing fields: {missing}")
        response = payload.get("sanitized_structured_response")
        if not isinstance(response, Mapping):
            raise ValidationError("sanitized_structured_response must be an object")
        usage = payload.get("token_usage")
        if not isinstance(usage, Mapping) or set(usage) != {"input_tokens", "output_tokens"}:
            raise ValidationError("token_usage must contain exactly input_tokens and output_tokens")
        return cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            created_at=require_non_empty_string(payload.get("created_at"), "created_at"),
            provider=require_non_empty_string(payload.get("provider"), "provider"),
            requested_model=require_non_empty_string(
                payload.get("requested_model"), "requested_model"
            ),
            returned_model=_optional_string(payload.get("returned_model"), "returned_model"),
            response_id=_optional_string(payload.get("response_id"), "response_id"),
            prompt_template_version=require_non_empty_string(
                payload.get("prompt_template_version"), "prompt_template_version"
            ),
            prompt_template_digest=require_digest(
                payload.get("prompt_template_digest"), "prompt_template_digest"
            ),
            response_schema_version=require_non_empty_string(
                payload.get("response_schema_version"), "response_schema_version"
            ),
            response_schema_digest=require_digest(
                payload.get("response_schema_digest"), "response_schema_digest"
            ),
            request_digest=require_digest(payload.get("request_digest"), "request_digest"),
            catalog_digest=require_digest(payload.get("catalog_digest"), "catalog_digest"),
            sanitized_structured_response=response,
            structured_response_digest=require_digest(
                payload.get("structured_response_digest"), "structured_response_digest"
            ),
            input_tokens=_optional_count(usage.get("input_tokens"), "input_tokens"),
            output_tokens=_optional_count(usage.get("output_tokens"), "output_tokens"),
            latency_ms=_optional_count(payload.get("latency_ms"), "latency_ms"),
            refusal=_optional_string(payload.get("refusal"), "refusal"),
            error_code=_optional_string(payload.get("error_code"), "error_code"),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> OpenAIProofReplayBundle:
        return cls.from_dict(_strict_json_object(value))


def create_replay_bundle(
    request: ProofPlanningRequest,
    provider_response: ProviderPlanningResponse,
    *,
    created_at: str,
) -> OpenAIProofReplayBundle:
    """Create a sanitized bundle from a normalized live or injected response."""

    if not isinstance(request, ProofPlanningRequest):
        raise ProofPlanningError("policy_error", "request must be ProofPlanningRequest")
    if not isinstance(provider_response, ProviderPlanningResponse):
        raise ProofPlanningError(
            "policy_error",
            "provider_response must be ProviderPlanningResponse",
        )
    validate_openai_request_context(request)
    if provider_response.provider_adapter_id != PROVIDER_ADAPTER_ID:
        raise ProofPlanningError("policy_error", "provider response uses the wrong adapter")
    structured = provider_response.structured_response_dict()
    return OpenAIProofReplayBundle(
        created_at=created_at,
        provider=provider_response.provider_adapter_id,
        requested_model=provider_response.requested_model_id,
        returned_model=provider_response.returned_model_id,
        response_id=provider_response.response_id,
        prompt_template_version=request.prompt_template_version,
        prompt_template_digest=request.prompt_template_digest,
        response_schema_version=request.response_schema_version,
        response_schema_digest=request.response_schema_digest,
        request_digest=request.digest(),
        catalog_digest=request.proof_catalog_digest,
        sanitized_structured_response=structured,
        structured_response_digest=sha256_digest(structured),
        input_tokens=provider_response.input_tokens,
        output_tokens=provider_response.output_tokens,
        latency_ms=provider_response.latency_ms,
        refusal=provider_response.refusal,
        error_code=provider_response.error_code,
    )


class ReplayProofPlannerBackend:
    """Zero-network backend that revalidates one exact recorded planning response."""

    def __init__(
        self,
        bundle: OpenAIProofReplayBundle,
        *,
        expected_bundle_digest: str,
        expected_requested_model: str = DEFAULT_MODEL,
    ) -> None:
        if not isinstance(bundle, OpenAIProofReplayBundle):
            raise ValidationError("bundle must be an OpenAIProofReplayBundle")
        self.bundle = bundle
        self.expected_bundle_digest = require_digest(
            expected_bundle_digest,
            "expected_bundle_digest",
        )
        if self.bundle.digest() != self.expected_bundle_digest:
            raise ProofPlanningError(
                "replay_mismatch",
                "replay bundle does not match its trusted external digest",
            )
        self.expected_requested_model = require_non_empty_string(
            expected_requested_model,
            "expected_requested_model",
        )

    def _validate_context(self, request: ProofPlanningRequest) -> None:
        validate_openai_request_context(request, error_code="replay_mismatch")
        comparisons = (
            (self.bundle.provider, PROVIDER_ADAPTER_ID, "provider"),
            (
                self.bundle.requested_model,
                self.expected_requested_model,
                "requested model",
            ),
            (
                self.bundle.prompt_template_version,
                request.prompt_template_version,
                "prompt template version",
            ),
            (
                self.bundle.prompt_template_digest,
                request.prompt_template_digest,
                "prompt template digest",
            ),
            (
                self.bundle.response_schema_version,
                request.response_schema_version,
                "response schema version",
            ),
            (
                self.bundle.response_schema_digest,
                request.response_schema_digest,
                "response schema digest",
            ),
            (self.bundle.request_digest, request.digest(), "request digest"),
            (
                self.bundle.catalog_digest,
                request.proof_catalog_digest,
                "catalog digest",
            ),
        )
        for actual, expected, label in comparisons:
            if actual != expected:
                raise ProofPlanningError(
                    "replay_mismatch",
                    f"replay {label} does not match the current planning context",
                )
        structured = self.bundle.sanitized_structured_response_dict()
        if sha256_digest(structured) != self.bundle.structured_response_digest:
            raise ProofPlanningError(
                "replay_mismatch",
                "replay structured response digest does not match its payload",
            )

    def plan(self, request: ProofPlanningRequest) -> ProviderPlanningResponse:
        if not isinstance(request, ProofPlanningRequest):
            raise ProofPlanningError("policy_error", "request must be ProofPlanningRequest")
        self._validate_context(request)
        response = ProviderPlanningResponse(
            provider_adapter_id=self.bundle.provider,
            requested_model_id=self.bundle.requested_model,
            returned_model_id=self.bundle.returned_model,
            response_id=self.bundle.response_id,
            mode="replay",
            latency_ms=self.bundle.latency_ms,
            input_tokens=self.bundle.input_tokens,
            output_tokens=self.bundle.output_tokens,
            refusal=self.bundle.refusal,
            error_code=self.bundle.error_code,
            structured_response=self.bundle.sanitized_structured_response_dict(),
        )
        try:
            materialize_proof_plan(request, response)
        except ProofPlanningError as error:
            raise with_terminal_model_error(error) from None
        return response

    def plan_result(self, request: ProofPlanningRequest) -> ProofPlanningResult:
        return materialize_proof_plan(request, self.plan(request))


def load_replay_bundle(path: str | Path) -> OpenAIProofReplayBundle:
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_REPLAY_BUNDLE_BYTES + 1)
    return OpenAIProofReplayBundle.from_json(payload)


def write_replay_bundle(path: str | Path, bundle: OpenAIProofReplayBundle) -> None:
    if not isinstance(bundle, OpenAIProofReplayBundle):
        raise ValidationError("bundle must be an OpenAIProofReplayBundle")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(bundle.to_json() + "\n", encoding="utf-8")
