"""Opt-in local observations of proof proposals; never acceptance authority.

Existing records are saved in unique run directories. Immutable event files use
TraceEvent rather than changing the proof protocol or the current-result bundle.
This is single-user archival storage, not a tamper-proof or authenticated journal.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import utc_now
from faber.proof_planning import (
    PLANNING_ERROR_CODES,
    ProofPlanningError,
    ProofPlanningRequest,
    ProofPlanningResult,
)
from faber.proof_workflow import ProofWorkflowResult
from faber.proofs import ProofDecision, ProofPolicy
from faber.redaction import detect_sensitive_fields
from faber.traces import TraceEvent
from faber.validation import require_digest

MAX_OBSERVATION_BYTES = 2 * 1024 * 1024
MAX_OBSERVATION_EVENTS = 1000
FEEDBACK_OUTCOMES = frozenset({"accepted", "edited", "rejected", "inconclusive"})
FEEDBACK_REASONS = frozenset(
    {
        "useful_missing_check",
        "unnecessary_check",
        "wrong_environment",
        "too_expensive",
        "missing_evidence",
        "policy_mismatch",
        "other",
    }
)
_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")


class ProofObservationError(ValidationError):
    """A fixed, secret-safe observation storage or validation failure."""


def _safe_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and _REFERENCE.fullmatch(value) is not None
        and not value.startswith(("sk-", "sk_"))
        and not detect_sensitive_fields({"identifier": value})
    )


def _safe_directory(path: Path) -> Path:
    """Reject links/reparse points before resolving; do not follow caller data."""
    if str(path).replace("/", "\\").startswith("\\\\"):
        raise ProofObservationError("observation paths must use ordinary local drive paths")
    absolute = Path(os.path.abspath(path))
    for part in (absolute, *absolute.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise ProofObservationError("observation directory is unavailable") from None
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ProofObservationError("observation directories must not contain links")
        if not stat.S_ISDIR(info.st_mode):
            raise ProofObservationError("observation destination must be a directory")
    try:
        return absolute.resolve(strict=False)
    except (OSError, RuntimeError):
        raise ProofObservationError("observation directory could not be resolved") from None


def _write_record(directory: Path, name: str, value: Mapping[str, object]) -> dict[str, str]:
    directory = _safe_directory(directory)
    data = (canonical_json(dict(value)) + "\n").encode("utf-8")
    if len(data) > MAX_OBSERVATION_BYTES:
        raise ProofObservationError("observation record exceeds the byte limit")
    try:
        with (directory / name).open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise ProofObservationError("observation record could not be created exclusively") from None
    return {"artifact": name, "artifact_digest": sha256_digest(data)}


def _read_record(directory: Path, name: str) -> tuple[dict[str, object], str]:
    source = _safe_directory(directory) / name
    try:
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ProofObservationError("observation artifacts must be regular files")
        with source.open("rb") as stream:
            data = stream.read(MAX_OBSERVATION_BYTES + 1)
        if len(data) > MAX_OBSERVATION_BYTES:
            raise ProofObservationError("observation record exceeds the byte limit")
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, dict) or (canonical_json(value) + "\n").encode("utf-8") != data:
            raise ProofObservationError("observation artifact must be canonical object JSON")
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError):
        raise ProofObservationError("observation artifact could not be read safely") from None
    return value, sha256_digest(data)


def _event(directory: Path, attempt_id: str, event_type: str, payload: dict[str, object]) -> None:
    directory = _safe_directory(directory)
    try:
        names = []
        with os.scandir(directory) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) > MAX_OBSERVATION_EVENTS + 10:
                    raise ProofObservationError("observation directory exceeds the entry limit")
    except OSError:
        raise ProofObservationError("observation events could not be inspected") from None
    indices = [int(name[:6]) for name in names if re.fullmatch(r"[0-9]{6}-event.json", name)]
    sequence = max(indices, default=-1) + 1
    if sequence >= MAX_OBSERVATION_EVENTS:
        raise ProofObservationError("observation event limit reached")
    event = TraceEvent(
        attempt_id=attempt_id,
        sequence=sequence,
        event_type=event_type,
        payload=payload,
        observed_at=utc_now(),
        trust_level="self_attested",
        provenance={
            "observer": "faber-proof.local-observation",
            "authority": "none",
            "training_permission_granted": False,
        },
    )
    _write_record(directory, f"{sequence:06d}-event.json", event.to_dict())


@dataclass(frozen=True)
class ProofObservationRun:
    directory: Path
    request: ProofPlanningRequest

    def record_result(self, result: ProofPlanningResult) -> None:
        if (
            not isinstance(result, ProofPlanningResult)
            or result.model_run.request_digest != self.request.digest()
        ):
            raise ProofObservationError("planning result does not match the observed request")
        reference = _write_record(self.directory, "planning-result.json", result.to_dict())
        _event(
            self.directory,
            self.request.attempt_id,
            "policy.proposal_result",
            {
                "planning_request_digest": self.request.digest(),
                "planning_result_digest": result.digest(),
                "result_reference": reference,
                "counterfactual_outcome": None,
                "cost_minor_units": None,
            },
        )

    def record_failure(self, error: ProofPlanningError) -> None:
        # Even public exception strings and provider refusal text can echo inputs.
        # Only the closed error code and retryability cross this archive boundary.
        if (
            not isinstance(error, ProofPlanningError)
            or error.code not in PLANNING_ERROR_CODES
            or not isinstance(error.retryable, bool)
        ):
            raise ProofObservationError("planning failure must use a supported error code")
        model_run = error.model_run
        if model_run is not None and model_run.request_digest != self.request.digest():
            model_run = None
        _event(
            self.directory,
            self.request.attempt_id,
            "policy.proposal_failed",
            {
                "planning_request_digest": self.request.digest(),
                "error_code": error.code,
                "retryable": error.retryable,
                "input_tokens": model_run.input_tokens if model_run else None,
                "output_tokens": model_run.output_tokens if model_run else None,
                "latency_ms": model_run.latency_ms if model_run else None,
                "counterfactual_outcome": None,
                "cost_minor_units": None,
            },
        )

    def record_decision(
        self, decision: ProofDecision, *, workflow_reference: dict[str, str] | None = None
    ) -> None:
        raw_result, _ = _read_record(self.directory, "planning-result.json")
        result = ProofPlanningResult.from_dict(raw_result)
        if (
            not isinstance(decision, ProofDecision)
            or decision.proof_plan_digest != result.plan.digest()
            or decision.attempt_digest != self.request.attempt_digest
            or decision.task_contract_digest != self.request.task_contract_digest
        ):
            raise ProofObservationError("proof decision does not match the observed request")
        reference = _write_record(self.directory, "proof-decision.json", decision.to_dict())
        _event(
            self.directory,
            self.request.attempt_id,
            "policy.verification_observed",
            {
                "planning_request_digest": self.request.digest(),
                "proof_decision_digest": decision.digest(),
                "decision_reference": reference,
                "workflow_reference": workflow_reference,
                "counterfactual_outcome": None,
            },
        )

    def record_workflow(self, workflow: ProofWorkflowResult) -> None:
        if not isinstance(workflow, ProofWorkflowResult):
            raise ProofObservationError("workflow observation requires a validated result")
        retained, _ = _read_record(self.directory, "planning-result.json")
        result = ProofPlanningResult.from_dict(retained)
        if (
            workflow.plan.digest() != result.plan.digest()
            or workflow.plan.model_run.request_digest != self.request.digest()
            or workflow.decision.proof_plan_digest != result.plan.digest()
        ):
            raise ProofObservationError("workflow does not match the observed proposal")
        reference = _write_record(self.directory, "workflow-result.json", workflow.to_dict())
        reference["record_digest"] = workflow.digest()
        self.record_decision(workflow.decision, workflow_reference=reference)

    def record_run_failure(self, phase: str) -> None:
        if phase not in {"execution", "publication"}:
            raise ProofObservationError("observation failure phase is unsupported")
        _event(
            self.directory,
            self.request.attempt_id,
            "policy.run_failed",
            {"planning_request_digest": self.request.digest(), "phase": phase},
        )


def start_proof_observation(
    *,
    request: ProofPlanningRequest,
    proof_policy: ProofPolicy,
    directory: str | Path,
    repository_root: Path,
    proof_output_directory: Path,
    requested_model_id: str,
    mode: str,
    dry_run: bool,
) -> ProofObservationRun:
    """Persist the already-redacted view before planning; never replace a run."""
    if not isinstance(request, ProofPlanningRequest) or not isinstance(proof_policy, ProofPolicy):
        raise ProofObservationError("observations require validated request and policy records")
    if not _safe_identifier(requested_model_id) or mode not in {"live", "replay"}:
        raise ProofObservationError("observations require a bounded model identifier and mode")
    if not isinstance(dry_run, bool):
        raise ProofObservationError("observation dry_run must be a boolean")
    root = _safe_directory(repository_root)
    raw = Path(directory)
    destination = _safe_directory(raw if raw.is_absolute() else root / raw)
    output = _safe_directory(proof_output_directory)
    if destination == Path(destination.anchor):
        raise ProofObservationError("observation destination must be a dedicated directory")
    if destination == root or root.is_relative_to(destination):
        raise ProofObservationError("observation destination must not contain the repository")
    if destination.is_relative_to(root):
        local_state = root / ".faber"
        if destination == local_state or not destination.is_relative_to(local_state):
            raise ProofObservationError("in-repository observations must be below .faber")
    if destination.is_relative_to(output) or output.is_relative_to(destination):
        raise ProofObservationError("observation and proof output directories must not overlap")
    try:
        destination.mkdir(parents=True, exist_ok=True)
        destination = _safe_directory(destination)
        run_directory = Path(tempfile.mkdtemp(prefix="observation-", dir=destination))
    except OSError:
        raise ProofObservationError("observation directory could not be created") from None
    request_reference = _write_record(run_directory, "planning-request.json", request.to_dict())
    policy_reference = _write_record(run_directory, "proof-policy.json", proof_policy.to_dict())
    _event(
        run_directory,
        request.attempt_id,
        "policy.proposal_observed",
        {
            "planning_request_digest": request.digest(),
            "request_reference": request_reference,
            "proof_policy_digest": proof_policy.digest(),
            "policy_reference": policy_reference,
            "requested_model_id": requested_model_id,
            "mode": mode,
            "dry_run": dry_run,
            "considered_alternatives": None,
            "selection_probability": None,
            "counterfactual_outcome": None,
            "cost_minor_units": None,
        },
    )
    return ProofObservationRun(run_directory, request)


def record_proof_feedback(
    run_directory: str | Path,
    *,
    reviewer_ref: str,
    outcome: str,
    reason_codes: Sequence[str],
    review_receipt_digest: str | None = None,
) -> None:
    """Add delayed self-attested feedback; this cannot approve policy or training."""
    if not _safe_identifier(reviewer_ref):
        raise ProofObservationError("reviewer reference must be a bounded identifier")
    if outcome not in FEEDBACK_OUTCOMES:
        raise ProofObservationError("feedback outcome is unsupported")
    if (
        isinstance(reason_codes, str | bytes)
        or not isinstance(reason_codes, Sequence)
        or not reason_codes
        or len(reason_codes) > len(FEEDBACK_REASONS)
        or any(reason not in FEEDBACK_REASONS for reason in reason_codes)
    ):
        raise ProofObservationError("feedback requires supported reason codes")
    if review_receipt_digest is not None:
        require_digest(review_receipt_digest, "review_receipt_digest")
    directory = _safe_directory(Path(run_directory))
    result_digest: str | None = None
    plan_digest: str | None = None
    try:
        raw_request, artifact_digest = _read_record(directory, "planning-request.json")
        request = ProofPlanningRequest.from_dict(raw_request)
        raw_proposal, _ = _read_record(directory, "000000-event.json")
        proposal = TraceEvent.from_dict(raw_proposal)
        if (
            proposal.event_type != "policy.proposal_observed"
            or proposal.sequence != 0
            or proposal.attempt_id != request.attempt_id
            or proposal.payload.get("planning_request_digest") != request.digest()
            or proposal.payload.get("request_reference")
            != {
                "artifact": "planning-request.json",
                "artifact_digest": artifact_digest,
            }
        ):
            raise ProofObservationError("feedback request does not match the original observation")
        raw_event, _ = _read_record(directory, "000001-event.json")
        result_event = TraceEvent.from_dict(raw_event)
        if (
            result_event.sequence != 1
            or result_event.attempt_id != request.attempt_id
            or result_event.payload.get("planning_request_digest") != request.digest()
            or result_event.event_type not in {"policy.proposal_result", "policy.proposal_failed"}
        ):
            raise ProofObservationError("feedback requires a matching terminal planner observation")
        if result_event.event_type == "policy.proposal_result" or os.path.lexists(
            directory / "planning-result.json"
        ):
            raw_result, result_artifact_digest = _read_record(directory, "planning-result.json")
            result = ProofPlanningResult.from_dict(raw_result)
            if (
                result.model_run.request_digest != request.digest()
                or result_event.event_type != "policy.proposal_result"
                or result_event.payload.get("planning_result_digest") != result.digest()
                or result_event.payload.get("result_reference")
                != {
                    "artifact": "planning-result.json",
                    "artifact_digest": result_artifact_digest,
                }
            ):
                raise ProofObservationError("feedback result does not match its observation")
            result_digest = result.digest()
            plan_digest = result.plan.digest()
    except (ValidationError, OSError):
        raise ProofObservationError("feedback requires a valid observed planning request") from None
    _event(
        directory,
        request.attempt_id,
        "policy.owner_feedback_reported",
        {
            "planning_request_digest": request.digest(),
            "planning_result_digest": result_digest,
            "proof_plan_digest": plan_digest,
            "feedback_target": "planning_result" if result_digest else "planning_request",
            "reviewer_ref": reviewer_ref,
            "outcome": outcome,
            "reason_codes": sorted(set(reason_codes)),
            "review_receipt_digest": review_receipt_digest,
            "authority": "none",
            "training_permission_granted": False,
            "counterfactual_outcome": None,
        },
    )
