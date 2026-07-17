"""Guarded OpenAI Responses API backend and canonical planning-request builder."""

from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from importlib import import_module
from typing import Any

from faber.attempts import Attempt
from faber.canonical_json import canonical_json_bytes
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_planning import (
    PlannerCatalogEntryView,
    PlanningFileSummary,
    ProofPlanningError,
    ProofPlanningRequest,
    ProofPlanningResult,
    ProviderPlanningResponse,
    materialize_proof_plan,
    planner_catalog_digest,
)
from faber.proofs import ProofClaim
from faber.redaction import (
    SensitiveFieldPattern,
    default_sensitive_patterns,
    detect_sensitive_fields,
)
from faber.validation import require_digest, require_non_empty_string

from .prompt import (
    DEFAULT_MODEL,
    PROMPT_TEMPLATE_VERSION,
    REASONING_EFFORT,
    RESPONSE_SCHEMA_VERSION,
    SYSTEM_INSTRUCTIONS,
    prompt_template_digest,
    render_request_input,
)
from .schemas import structured_response_schema, structured_response_schema_digest

PROVIDER_ADAPTER_ID = "openai.responses.proof-planner.v1"
OPENAI_API_BASE_URL = "https://api.openai.com/v1"
DEFAULT_DIFF_BYTES = 16_384
DEFAULT_REQUEST_BYTES = 65_536
MAX_RAW_DIFF_MULTIPLIER = 4
MAX_RESPONSE_BYTES = 65_536
MAX_JSON_INTEGER = (1 << 63) - 1
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_OUTPUT_TOKENS = 8_000
DEFAULT_TRANSIENT_RETRIES = 1
DEFAULT_INVALID_OUTPUT_RETRIES = 1
MAX_TRANSIENT_RETRIES = 2
MAX_INVALID_OUTPUT_RETRIES = 1
MAX_TIMEOUT_SECONDS = 120.0
MAX_OUTPUT_TOKENS = 8_000
MAX_RETRY_DELAY_SECONDS = 5.0
DEFAULT_RETRY_DELAY_SECONDS = 0.25
REDACTION_REPLACEMENT = "[redacted]"
REDACTION_DETECTOR_VERSION = "faber-proof-request-secrets-v1"


def _planner_sensitive_patterns() -> list[SensitiveFieldPattern]:
    return [
        *default_sensitive_patterns(),
        SensitiveFieldPattern(
            name="openai_api_key",
            value_pattern=r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b",
        ),
        SensitiveFieldPattern(
            name="assigned_secret",
            value_pattern=(
                r"(?i)\b(?:openai_api_key|api[_-]?key|authorization|password|secret|token)"
                r"\s*[:=]\s*[^\s,;]{8,}"
            ),
        ),
    ]


def _contains_sensitive_content(value: object) -> bool:
    patterns = _planner_sensitive_patterns()

    def visit(item: object) -> bool:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                key_text = str(key)
                if detect_sensitive_fields({key_text: "present"}, patterns=patterns):
                    return True
                if detect_sensitive_fields({"mapping_key": key_text}, patterns=patterns):
                    return True
                if visit(nested):
                    return True
            return False
        if isinstance(item, Sequence) and not isinstance(item, str | bytes | bytearray):
            return any(visit(nested) for nested in item)
        if isinstance(item, str):
            return bool(detect_sensitive_fields({"value": item}, patterns=patterns))
        return False

    return visit(value)


def _line_ending(value: str) -> str:
    if value.endswith("\r\n"):
        return "\r\n"
    if value.endswith("\n"):
        return "\n"
    if value.endswith("\r"):
        return "\r"
    return ""


def _redact_text(
    value: str,
    *,
    field_name: str,
    field_path: str,
) -> tuple[str, list[dict[str, str]]]:
    patterns = _planner_sensitive_patterns()
    lines = value.splitlines(keepends=True) or [value]
    redacted: list[str] = []
    summary: list[dict[str, str]] = []
    redact_entire_value = False
    for index, line in enumerate(lines):
        findings = detect_sensitive_fields({field_name: line}, patterns=patterns)
        if not findings:
            redacted.append(line)
            continue
        finding_patterns = sorted({str(item["pattern"]) for item in findings})
        if "private_key" in finding_patterns:
            redact_entire_value = True
        for pattern in finding_patterns:
            summary.append(
                {
                    "field_path": f"{field_path}.line[{index}]",
                    "pattern": pattern,
                }
            )
        redacted.append(REDACTION_REPLACEMENT + _line_ending(line))
    if redact_entire_value:
        return REDACTION_REPLACEMENT, summary
    return "".join(redacted), summary


def _safe_strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ProofPlanningError("policy_error", f"{field} must be a sequence of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        try:
            result.append(require_non_empty_string(item, f"{field}[{index}]"))
        except ValidationError:
            raise ProofPlanningError(
                "policy_error",
                f"{field} must contain only non-empty strings",
            ) from None
    return tuple(result)


def _criteria_from_contract(
    contract: TaskContract,
    explicit: Sequence[str] | None,
    field: str,
) -> tuple[str, ...]:
    if explicit is not None:
        return _safe_strings(explicit, field)
    return _safe_strings(contract.environment.get(field, ()), field)


def _ensure_no_control_secrets(
    catalog_entries: Sequence[PlannerCatalogEntryView],
    mandatory_claims: Sequence[ProofClaim],
) -> None:
    payload = {
        "catalog_entries": [entry.to_dict() for entry in catalog_entries],
        "mandatory_claims": [claim.to_dict() for claim in mandatory_claims],
    }
    if _contains_sensitive_content(payload):
        raise ProofPlanningError(
            "redaction_error",
            "trusted catalog or mandatory-claim data contains secret-like text",
        )


def _ensure_no_identity_secrets(contract: TaskContract, attempt: Attempt) -> None:
    identity_payload = {
        "task_contract_id": contract.id,
        "attempt_id": attempt.id,
        "base_revision": attempt.base_revision,
        "candidate_revision": attempt.candidate_revision,
    }
    if _contains_sensitive_content(identity_payload):
        raise ProofPlanningError(
            "redaction_error",
            "task or attempt identity data contains secret-like text",
        )


def build_planning_request(
    contract: TaskContract,
    attempt: Attempt,
    *,
    diff_text: str,
    catalog_entries: Sequence[PlannerCatalogEntryView],
    proof_catalog_digest: str | None = None,
    mandatory_claims: Sequence[ProofClaim] = (),
    mandatory_template_ids: Sequence[str] = (),
    acceptance_criteria: Sequence[str] | None = None,
    rejection_criteria: Sequence[str] | None = None,
    file_summaries: Sequence[PlanningFileSummary] = (),
    max_diff_bytes: int = DEFAULT_DIFF_BYTES,
    max_request_bytes: int = DEFAULT_REQUEST_BYTES,
) -> ProofPlanningRequest:
    """Build and digest the exact bounded, redacted data sent to the provider."""

    if not isinstance(contract, TaskContract):
        raise ProofPlanningError("policy_error", "contract must be a TaskContract")
    if not isinstance(attempt, Attempt):
        raise ProofPlanningError("policy_error", "attempt must be an Attempt")
    if attempt.task_contract_id != contract.id:
        raise ProofPlanningError("policy_error", "attempt does not bind to the task contract")
    _ensure_no_identity_secrets(contract, attempt)
    try:
        raw_diff = require_non_empty_string(diff_text, "diff_text")
    except ValidationError:
        raise ProofPlanningError("policy_error", "diff_text must be non-empty text") from None
    if (
        isinstance(max_diff_bytes, bool)
        or not isinstance(max_diff_bytes, int)
        or max_diff_bytes < 1
    ):
        raise ProofPlanningError("policy_error", "max_diff_bytes must be a positive integer")
    if (
        isinstance(max_request_bytes, bool)
        or not isinstance(max_request_bytes, int)
        or max_request_bytes < 1
    ):
        raise ProofPlanningError("policy_error", "max_request_bytes must be a positive integer")
    try:
        raw_diff_size = len(raw_diff.encode("utf-8"))
    except UnicodeEncodeError:
        raise ProofPlanningError("redaction_error", "diff_text is not valid UTF-8 text") from None
    if raw_diff_size > max_diff_bytes * MAX_RAW_DIFF_MULTIPLIER:
        raise ProofPlanningError("request_too_large", "raw diff exceeds the safety limit")

    entries = tuple(catalog_entries)
    if not entries or any(not isinstance(entry, PlannerCatalogEntryView) for entry in entries):
        raise ProofPlanningError(
            "policy_error",
            "catalog_entries must contain approved planner catalog views",
        )
    claims = tuple(mandatory_claims)
    if any(not isinstance(claim, ProofClaim) for claim in claims):
        raise ProofPlanningError(
            "policy_error",
            "mandatory_claims must contain ProofClaim records",
        )
    summaries = tuple(file_summaries)
    if any(not isinstance(item, PlanningFileSummary) for item in summaries):
        raise ProofPlanningError(
            "policy_error",
            "file_summaries must contain PlanningFileSummary records",
        )
    _ensure_no_control_secrets(entries, claims)

    raw_acceptance = _criteria_from_contract(
        contract,
        acceptance_criteria,
        "acceptance_criteria",
    )
    raw_rejection = _criteria_from_contract(
        contract,
        rejection_criteria,
        "rejection_criteria",
    )
    findings: list[dict[str, str]] = []

    redacted_title, found = _redact_text(
        contract.title,
        field_name="title",
        field_path="task.title",
    )
    findings.extend(found)
    redacted_description, found = _redact_text(
        contract.description,
        field_name="description",
        field_path="task.description",
    )
    findings.extend(found)

    def redact_sequence(values: Sequence[str], prefix: str) -> tuple[str, ...]:
        result: list[str] = []
        for index, value in enumerate(values):
            redacted_value, nested = _redact_text(
                value,
                field_name=prefix,
                field_path=f"task.{prefix}[{index}]",
            )
            findings.extend(nested)
            result.append(redacted_value)
        return tuple(result)

    redacted_requirements = redact_sequence(contract.requirements, "requirements")
    redacted_acceptance = redact_sequence(raw_acceptance, "acceptance_criteria")
    redacted_rejection = redact_sequence(raw_rejection, "rejection_criteria")
    redacted_diff, found = _redact_text(
        raw_diff,
        field_name="diff_text",
        field_path="diff_text",
    )
    findings.extend(found)
    try:
        redacted_diff_size = len(redacted_diff.encode("utf-8"))
    except UnicodeEncodeError:
        raise ProofPlanningError("redaction_error", "redacted diff is not valid UTF-8") from None
    if redacted_diff_size > max_diff_bytes:
        raise ProofPlanningError(
            "request_too_large",
            "redacted diff exceeds the configured byte limit",
        )

    redacted_summaries: list[PlanningFileSummary] = []
    for index, summary in enumerate(summaries):
        redacted_identifier, nested = _redact_text(
            summary.identifier,
            field_name="identifier",
            field_path=f"file_summaries[{index}].identifier",
        )
        findings.extend(nested)
        redacted_summary, nested = _redact_text(
            summary.summary,
            field_name="summary",
            field_path=f"file_summaries[{index}].summary",
        )
        findings.extend(nested)
        redacted_summaries.append(
            PlanningFileSummary(
                identifier=redacted_identifier,
                summary=redacted_summary,
                content_digest=summary.content_digest,
            )
        )

    summary_payload: dict[str, object] = {
        "detector_version": REDACTION_DETECTOR_VERSION,
        "finding_count": len(findings),
        "field_paths": sorted({finding["field_path"] for finding in findings}),
        "patterns": sorted({finding["pattern"] for finding in findings}),
    }
    catalog_digest = proof_catalog_digest or planner_catalog_digest(entries)
    try:
        require_digest(catalog_digest, "proof_catalog_digest")
        request = ProofPlanningRequest(
            task_contract_id=contract.id,
            task_contract_digest=contract.digest(),
            task_title=redacted_title,
            task_description=redacted_description,
            requirements=redacted_requirements,
            acceptance_criteria=redacted_acceptance,
            rejection_criteria=redacted_rejection,
            attempt_id=attempt.id,
            attempt_digest=attempt.digest(),
            base_revision=attempt.base_revision,
            candidate_revision=attempt.candidate_revision,
            diff_digest=attempt.patch_digest,
            redacted_diff_digest=sha256_digest(redacted_diff),
            redacted_diff_text=redacted_diff,
            max_diff_bytes=max_diff_bytes,
            diff_truncated=False,
            file_summaries=redacted_summaries,
            proof_catalog_digest=catalog_digest,
            catalog_entries=entries,
            mandatory_claims=claims,
            mandatory_template_ids=mandatory_template_ids,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            prompt_template_digest=prompt_template_digest(),
            response_schema_version=RESPONSE_SCHEMA_VERSION,
            response_schema_digest=structured_response_schema_digest(entries),
            redaction_summary=summary_payload,
        )
        request_size = len(canonical_json_bytes(request.to_dict()))
    except ProofPlanningError:
        raise
    except ValueError as exc:
        code = (
            "request_too_large" if "exceeds the protocol byte limit" in str(exc) else "policy_error"
        )
        raise ProofPlanningError(code, "planning request validation failed") from None
    if request_size > max_request_bytes:
        raise ProofPlanningError("request_too_large", "planning request exceeds the byte limit")
    return request


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


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


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def parse_structured_response_text(text: str) -> Mapping[str, object]:
    """Parse one bounded strict JSON object without duplicate keys or non-finite numbers."""

    if not isinstance(text, str):
        raise ProofPlanningError("invalid_structured_output", "provider output is not text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError:
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider output is not valid UTF-8 text",
        ) from None
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider output exceeds the response byte limit",
        )
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
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider output is not strict canonicalizable JSON",
        ) from None
    if not isinstance(payload, Mapping):
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider output root must be an object",
        )
    if _contains_sensitive_content(payload):
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider output contains secret-like text",
        )
    return dict(payload)


def validate_openai_request_context(
    request: ProofPlanningRequest,
    *,
    error_code: str = "policy_error",
) -> None:
    """Bind a caller-supplied request to this exact adapter prompt and schema."""

    if not isinstance(request, ProofPlanningRequest):
        raise ProofPlanningError(error_code, "request must be ProofPlanningRequest")
    expected = (
        (request.prompt_template_version, PROMPT_TEMPLATE_VERSION),
        (request.prompt_template_digest, prompt_template_digest()),
        (request.response_schema_version, RESPONSE_SCHEMA_VERSION),
        (
            request.response_schema_digest,
            structured_response_schema_digest(request.catalog_entries),
        ),
    )
    if any(actual != current for actual, current in expected):
        raise ProofPlanningError(
            error_code,
            "planning request does not match the current OpenAI adapter context",
        )


def _value(record: object, field: str, default: object = None) -> object:
    if isinstance(record, Mapping):
        return record.get(field, default)
    return getattr(record, field, default)


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _optional_count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _safe_provider_text(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    bounded = value[:500]
    if _contains_sensitive_content({"provider_text": bounded}):
        return REDACTION_REPLACEMENT
    return bounded


def _safe_optional_provider_text(value: object) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    safe = _safe_provider_text(text, REDACTION_REPLACEMENT)
    return None if safe == REDACTION_REPLACEMENT else safe


def _response_content(response: object) -> tuple[str | None, str | None]:
    output = _value(response, "output", ())
    if not isinstance(output, Sequence) or isinstance(output, str | bytes | bytearray):
        return None, None
    messages = [item for item in output if _value(item, "type") == "message"]
    if len(messages) != 1:
        return None, None
    content = _value(messages[0], "content", ())
    if not isinstance(content, Sequence) or isinstance(content, str | bytes | bytearray):
        return None, None
    refusals = [item for item in content if _value(item, "type") == "refusal"]
    if refusals:
        return None, _safe_provider_text(_value(refusals[0], "refusal"), "provider refusal")
    text_items = [item for item in content if _value(item, "type") == "output_text"]
    if len(text_items) != 1:
        return None, None
    return _optional_text(_value(text_items[0], "text")), None


def _normalized_provider_response(
    response: object,
    *,
    requested_model: str,
    latency_ms: int,
) -> ProviderPlanningResponse:
    status = _optional_text(_value(response, "status"))
    response_error = _value(response, "error")
    if response_error is not None:
        provider_code = _optional_text(_value(response_error, "code"))
        if provider_code in {"rate_limit_exceeded", "rate_limit_error"}:
            code = "rate_limit_error"
            retryable = True
        elif provider_code in {"invalid_request", "invalid_prompt"}:
            code = "configuration_error"
            retryable = False
        else:
            code = "transient_provider_error"
            retryable = True
        raise ProofPlanningError(
            code,
            "provider response contained an error state",
            retryable=retryable,
        )
    text, refusal = _response_content(response)
    if status is None:
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider response did not include a completion status",
        )
    if status == "incomplete":
        details = _value(response, "incomplete_details", {})
        reason = _optional_text(_value(details, "reason"))
        if reason == "content_filter":
            refusal = "provider content filter"
        else:
            raise ProofPlanningError(
                "invalid_structured_output",
                "provider response was incomplete",
            )
    if status not in {None, "completed", "incomplete"}:
        raise ProofPlanningError(
            "transient_provider_error",
            "provider response did not complete",
            retryable=True,
        )

    usage = _value(response, "usage", {})
    input_tokens = _optional_count(_value(usage, "input_tokens"))
    output_tokens = _optional_count(_value(usage, "output_tokens"))
    returned_model = _safe_optional_provider_text(_value(response, "model"))
    response_id = _safe_optional_provider_text(_value(response, "id"))
    if refusal is not None:
        return ProviderPlanningResponse(
            provider_adapter_id=PROVIDER_ADAPTER_ID,
            requested_model_id=requested_model,
            returned_model_id=returned_model,
            response_id=response_id,
            mode="live",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            refusal=refusal,
            structured_response={},
        )
    if text is None:
        raise ProofPlanningError(
            "invalid_structured_output",
            "provider response contained no single structured output",
        )
    return ProviderPlanningResponse(
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        requested_model_id=requested_model,
        returned_model_id=returned_model,
        response_id=response_id,
        mode="live",
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        structured_response=parse_structured_response_text(text),
    )


def _terminal_response_error(
    request: ProofPlanningRequest,
    raw_response: object,
    *,
    requested_model: str,
    latency_ms: int,
    error: ProofPlanningError,
) -> ProofPlanningError:
    """Attach sanitized metadata to an exhausted invalid/incomplete response."""

    usage = _value(raw_response, "usage", {})
    terminal_response = ProviderPlanningResponse(
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        requested_model_id=requested_model,
        returned_model_id=_safe_optional_provider_text(_value(raw_response, "model")),
        response_id=_safe_optional_provider_text(_value(raw_response, "id")),
        mode="live",
        latency_ms=latency_ms,
        input_tokens=_optional_count(_value(usage, "input_tokens")),
        output_tokens=_optional_count(_value(usage, "output_tokens")),
        error_code=error.code,
        structured_response={},
    )
    try:
        materialize_proof_plan(request, terminal_response)
    except ProofPlanningError as terminal:
        return ProofPlanningError(
            error.code,
            error.public_message,
            retryable=error.retryable,
            model_run=terminal.model_run,
        )
    raise AssertionError("terminal provider error unexpectedly materialized a plan")


def with_terminal_model_error(error: ProofPlanningError) -> ProofPlanningError:
    """Mark exhausted validation failure in its already-sanitized model evidence."""

    model_run = error.model_run
    if model_run is None or error.code == "refusal" or model_run.error_code is not None:
        return error
    return ProofPlanningError(
        error.code,
        error.public_message,
        retryable=error.retryable,
        model_run=replace(model_run, error_code=error.code),
    )


def _classify_provider_exception(exc: Exception) -> tuple[str, bool]:
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if name == "AuthenticationError" or status == 401:
        return "authentication_error", False
    if name == "PermissionDeniedError" or status == 403:
        return "permission_error", False
    if name == "RateLimitError" or status == 429:
        return "rate_limit_error", True
    if name in {"APITimeoutError", "TimeoutError"} or status == 408:
        return "timeout", True
    if name in {"APIConnectionError", "ConnectionError", "InternalServerError"}:
        return "transient_provider_error", True
    if status in {409} or isinstance(status, int) and status >= 500:
        return "transient_provider_error", True
    if name in {
        "BadRequestError",
        "NotFoundError",
        "UnprocessableEntityError",
    } or status in {400, 404, 422}:
        return "configuration_error", False
    return "transient_provider_error", False


class OpenAIProofPlannerBackend:
    """Synchronous guarded Responses API backend with explicit bounded retries."""

    def __init__(
        self,
        *,
        client: object | None = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        transient_retries: int = DEFAULT_TRANSIENT_RETRIES,
        invalid_output_retries: int = DEFAULT_INVALID_OUTPUT_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self.model = require_non_empty_string(model, "model")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int | float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or timeout_seconds > MAX_TIMEOUT_SECONDS
        ):
            raise ValidationError(
                f"timeout_seconds must be positive and at most {MAX_TIMEOUT_SECONDS:g}"
            )
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens < 1
            or max_output_tokens > MAX_OUTPUT_TOKENS
        ):
            raise ValidationError(f"max_output_tokens must be between 1 and {MAX_OUTPUT_TOKENS}")
        for value, field in (
            (transient_retries, "transient_retries"),
            (invalid_output_retries, "invalid_output_retries"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{field} must be a non-negative integer")
        if transient_retries > MAX_TRANSIENT_RETRIES:
            raise ValidationError(f"transient_retries must not exceed {MAX_TRANSIENT_RETRIES}")
        if invalid_output_retries > MAX_INVALID_OUTPUT_RETRIES:
            raise ValidationError(
                f"invalid_output_retries must not exceed {MAX_INVALID_OUTPUT_RETRIES}"
            )
        if (
            isinstance(retry_delay_seconds, bool)
            or not isinstance(retry_delay_seconds, int | float)
            or not math.isfinite(retry_delay_seconds)
            or retry_delay_seconds < 0
            or retry_delay_seconds > MAX_RETRY_DELAY_SECONDS
        ):
            raise ValidationError(
                f"retry_delay_seconds must be non-negative and at most {MAX_RETRY_DELAY_SECONDS:g}"
            )
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = max_output_tokens
        self.transient_retries = transient_retries
        self.invalid_output_retries = invalid_output_retries
        self.retry_delay_seconds = float(retry_delay_seconds)
        self._clock = clock
        self._sleeper = sleeper

    def _default_client(self) -> object:
        if os.environ.get("OPENAI_LOG", "").strip():
            raise ProofPlanningError(
                "configuration_error",
                "OPENAI_LOG must be unset for the guarded live planner",
            )
        try:
            sdk = import_module("openai")
            client_type = sdk.OpenAI
            return client_type(
                base_url=OPENAI_API_BASE_URL,
                max_retries=0,
                timeout=self.timeout_seconds,
            )
        except (ImportError, AttributeError):
            raise ProofPlanningError(
                "configuration_error",
                "install the live-openai optional dependency for live planning",
            ) from None
        except Exception:
            raise ProofPlanningError(
                "configuration_error",
                "the OpenAI client could not be configured",
            ) from None

    def _responses_create(self, request: ProofPlanningRequest) -> object:
        client = self._client or self._default_client()
        with_options = getattr(client, "with_options", None)
        if callable(with_options):
            client = with_options(max_retries=0, timeout=self.timeout_seconds)
        responses = getattr(client, "responses", None)
        create = getattr(responses, "create", None)
        if not callable(create):
            raise ProofPlanningError(
                "configuration_error",
                "injected client does not expose responses.create",
            )
        return create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=render_request_input(request),
            reasoning={"effort": REASONING_EFFORT},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "faber_proof_plan_v1",
                    "strict": True,
                    "schema": structured_response_schema(request.catalog_entries),
                }
            },
            max_output_tokens=self.max_output_tokens,
            store=False,
            truncation="disabled",
        )

    def plan(self, request: ProofPlanningRequest) -> ProviderPlanningResponse:
        validate_openai_request_context(request)
        if os.environ.get("OPENAI_LOG", "").strip():
            raise ProofPlanningError(
                "configuration_error",
                "OPENAI_LOG must be unset for the guarded live planner",
            )
        if os.environ.get("OPENAI_BASE_URL", "").strip():
            raise ProofPlanningError(
                "configuration_error",
                "OPENAI_BASE_URL must be unset for the guarded live planner",
            )
        transient_remaining = self.transient_retries
        invalid_remaining = self.invalid_output_retries
        started = self._clock()
        while True:
            try:
                raw_response = self._responses_create(request)
            except ProofPlanningError:
                raise
            except Exception as exc:
                code, retryable = _classify_provider_exception(exc)
                if retryable and transient_remaining > 0:
                    transient_remaining -= 1
                    self._sleeper(self.retry_delay_seconds)
                    continue
                raise ProofPlanningError(
                    code,
                    "the OpenAI provider request failed",
                    retryable=retryable,
                ) from None
            latency_ms = max(0, round((self._clock() - started) * 1000))
            try:
                normalized = _normalized_provider_response(
                    raw_response,
                    requested_model=self.model,
                    latency_ms=latency_ms,
                )
                materialize_proof_plan(request, normalized)
                return normalized
            except ValidationError as caught:
                planning_error = (
                    caught
                    if isinstance(caught, ProofPlanningError)
                    else ProofPlanningError(
                        "invalid_structured_output",
                        "provider output failed bounded response validation",
                    )
                )
                if planning_error.code == "invalid_structured_output" and invalid_remaining > 0:
                    invalid_remaining -= 1
                    continue
                if planning_error.retryable and transient_remaining > 0:
                    transient_remaining -= 1
                    self._sleeper(self.retry_delay_seconds)
                    continue
                if planning_error.model_run is None:
                    raise _terminal_response_error(
                        request,
                        raw_response,
                        requested_model=self.model,
                        latency_ms=latency_ms,
                        error=planning_error,
                    ) from None
                raise with_terminal_model_error(planning_error) from None

    def plan_result(self, request: ProofPlanningRequest) -> ProofPlanningResult:
        """Return the validated provider-neutral plan through the shared materializer."""

        return materialize_proof_plan(request, self.plan(request))


class FakeProofPlannerBackend:
    """Deterministic zero-network backend for orchestration and tests."""

    def __init__(self, responses: Sequence[ProviderPlanningResponse]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    def plan(self, request: ProofPlanningRequest) -> ProviderPlanningResponse:
        validate_openai_request_context(request)
        if self.call_count >= len(self._responses):
            raise ProofPlanningError(
                "configuration_error",
                "fake proof planner has no response configured",
            )
        response = self._responses[self.call_count]
        self.call_count += 1
        try:
            materialize_proof_plan(request, response)
        except ProofPlanningError as error:
            raise with_terminal_model_error(error) from None
        return response

    def plan_result(self, request: ProofPlanningRequest) -> ProofPlanningResult:
        return materialize_proof_plan(request, self.plan(request))


def response_call_shape(
    request: ProofPlanningRequest, *, model: str = DEFAULT_MODEL
) -> dict[str, Any]:
    """Return the sanitized documented call shape for syntax and judge inspection."""

    validate_openai_request_context(request)
    return {
        "model": model,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": render_request_input(request),
        "reasoning": {"effort": REASONING_EFFORT},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "faber_proof_plan_v1",
                "strict": True,
                "schema": structured_response_schema(request.catalog_entries),
            }
        },
        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "store": False,
        "truncation": "disabled",
    }
