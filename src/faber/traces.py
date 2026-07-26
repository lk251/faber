"""Trace evidence ladder and manifest records."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from faber import schemas
from faber.canonical_json import canonical_json
from faber.data_rights import ConsentGrant
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.validation import (
    ValidationError,
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
    require_string_list,
)

TRUST_LEVELS = {
    "self_attested",
    "runner_attested",
    "platform_observed",
    "repo_owner_verified",
    "provider_attested",
}

EVIDENCE_LEVEL_NAMES = {
    0: "pr_only",
    1: "attempt_manifest",
    2: "faber_runner_trace",
    3: "harness_native_trace",
    4: "replayable_episode_package",
}


def require_trust_level(value: str, field: str = "trust_level") -> str:
    require_non_empty_string(value, field)
    if value not in TRUST_LEVELS:
        raise ValidationError(f"{field} must be one of {sorted(TRUST_LEVELS)}")
    return value


def require_evidence_level(value: int, field: str = "evidence_level") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field} must be an integer between 0 and 4")
    if value not in EVIDENCE_LEVEL_NAMES:
        raise ValidationError(f"{field} must be between 0 and 4")
    return value


@dataclass(frozen=True)
class EvidenceLevel:
    """A named level in Faber's trace evidence ladder."""

    level: int
    name: str
    description: str
    required_artifacts: list[str] = field(default_factory=list)
    schema: str = schemas.EVIDENCE_LEVEL

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.EVIDENCE_LEVEL)
        require_evidence_level(self.level)
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.description, "description")
        require_string_list(self.required_artifacts, "required_artifacts")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "level": self.level,
            "name": self.name,
            "description": self.description,
            "required_artifacts": self.required_artifacts,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def evidence_level(level: int) -> EvidenceLevel:
    require_evidence_level(level)
    descriptions = {
        0: "PR-only fallback with final patch and verifier outcome evidence.",
        1: "PR plus .faber/attempt.json manifest.",
        2: "Faber Runner trace with normalized local execution events.",
        3: "Harness-native trace adapter output normalized into Faber events.",
        4: "Replayable episode package with manifests, traces, artifacts, and replay steps.",
    }
    artifacts = {
        0: ["pull_request", "patch_digest"],
        1: ["pull_request", "attempt_manifest"],
        2: ["pull_request", "attempt_manifest", "trace_jsonl"],
        3: ["pull_request", "attempt_manifest", "harness_trace_adapter"],
        4: ["pull_request", "attempt_manifest", "trace_jsonl", "replay_package"],
    }
    return EvidenceLevel(
        level=level,
        name=EVIDENCE_LEVEL_NAMES[level],
        description=descriptions[level],
        required_artifacts=artifacts[level],
    )


@dataclass(frozen=True)
class RedactionPolicy:
    """Field-path redaction rules for trace and manifest payloads."""

    name: str
    field_paths: list[str]
    replacement: str = "[redacted]"
    allow_raw_trace: bool = False
    notes: str = ""
    excluded_event_types: list[str] = field(default_factory=list)
    detect_secrets: bool = True
    id: str = field(default_factory=lambda: new_id("redaction-policy"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.REDACTION_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.REDACTION_POLICY)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.name, "name")
        require_string_list(self.field_paths, "field_paths")
        require_non_empty_string(self.replacement, "replacement")
        if not isinstance(self.allow_raw_trace, bool):
            raise ValidationError("allow_raw_trace must be a boolean")
        require_string_list(self.excluded_event_types, "excluded_event_types")
        if not isinstance(self.detect_secrets, bool):
            raise ValidationError("detect_secrets must be a boolean")

    def apply(self, payload: dict[str, object]) -> dict[str, object]:
        redacted = copy.deepcopy(payload)
        for field_path in self.field_paths:
            _redact_path(redacted, field_path.split("."), self.replacement)
        return redacted

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "name": self.name,
            "field_paths": self.field_paths,
            "replacement": self.replacement,
            "allow_raw_trace": self.allow_raw_trace,
            "notes": self.notes,
            "excluded_event_types": self.excluded_event_types,
            "detect_secrets": self.detect_secrets,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RedactionPolicy:
        replacement = payload.get("replacement", "[redacted]")
        if not isinstance(replacement, str):
            raise ValidationError("replacement must be a string")
        allow_raw_trace = payload.get("allow_raw_trace", False)
        if not isinstance(allow_raw_trace, bool):
            raise ValidationError("allow_raw_trace must be a boolean")
        notes = payload.get("notes", "")
        if not isinstance(notes, str):
            raise ValidationError("notes must be a string")
        detect_secrets = payload.get("detect_secrets", True)
        if not isinstance(detect_secrets, bool):
            raise ValidationError("detect_secrets must be a boolean")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            name=_required_string(payload, "name"),
            field_paths=require_string_list(payload.get("field_paths"), "field_paths"),
            replacement=replacement,
            allow_raw_trace=allow_raw_trace,
            notes=notes,
            excluded_event_types=require_string_list(
                payload.get("excluded_event_types", []),
                "excluded_event_types",
            ),
            detect_secrets=detect_secrets,
            schema=_schema_or_default(payload, "schema", schemas.REDACTION_POLICY),
        )


@dataclass(frozen=True)
class Attestation:
    """Provenance statement for solver-supplied metadata."""

    subject_id: str
    issuer: str
    trust_level: str
    subject_digest: str | None = None
    signature: str | None = None
    issued_at: str = field(default_factory=utc_now)
    expires_at: str | None = None
    verification_method: str = "self_attestation"
    limitations: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("attestation"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ATTESTATION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ATTESTATION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.subject_id, "subject_id")
        require_non_empty_string(self.issuer, "issuer")
        require_trust_level(self.trust_level)
        require_optional_digest(self.subject_digest, "subject_digest")
        if self.signature is not None:
            require_non_empty_string(self.signature, "signature")
        require_non_empty_string(self.issued_at, "issued_at")
        if self.expires_at is not None:
            require_non_empty_string(self.expires_at, "expires_at")
        require_non_empty_string(self.verification_method, "verification_method")
        require_string_list(self.limitations, "limitations")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "subject_id": self.subject_id,
            "subject_digest": self.subject_digest,
            "issuer": self.issuer,
            "trust_level": self.trust_level,
            "signature": self.signature,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "verification_method": self.verification_method,
            "limitations": self.limitations,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Attestation:
        limitations = payload.get("limitations", [])
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            subject_id=_required_string(payload, "subject_id"),
            subject_digest=_optional_string(payload.get("subject_digest")),
            issuer=_required_string(payload, "issuer"),
            trust_level=_required_string(payload, "trust_level"),
            signature=_optional_string(payload.get("signature")),
            issued_at=_required_string(payload, "issued_at"),
            expires_at=_optional_string(payload.get("expires_at")),
            verification_method=_required_string(payload, "verification_method"),
            limitations=require_string_list(limitations, "limitations"),
            schema=_schema_or_default(payload, "schema", schemas.ATTESTATION),
        )


@dataclass(frozen=True)
class TrajectoryConsent:
    """Consent and policy metadata for training use of trajectory evidence."""

    training_use_allowed: bool
    allowed_uses: list[str] = field(default_factory=list)
    license_ref: str = "unspecified"
    redaction_required: bool = True
    notes: str = ""
    grants: list[ConsentGrant] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("trajectory-consent"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRAJECTORY_CONSENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRAJECTORY_CONSENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        if not isinstance(self.training_use_allowed, bool):
            raise ValidationError("training_use_allowed must be a boolean")
        require_string_list(self.allowed_uses, "allowed_uses")
        require_non_empty_string(self.license_ref, "license_ref")
        if not isinstance(self.redaction_required, bool):
            raise ValidationError("redaction_required must be a boolean")
        if not isinstance(self.notes, str):
            raise ValidationError("notes must be a string")
        if any(not isinstance(grant, ConsentGrant) for grant in self.grants):
            raise ValidationError("grants must contain ConsentGrant records")

    def allows(self, use: str) -> bool:
        require_non_empty_string(use, "use")
        return self.training_use_allowed and (
            "all" in self.allowed_uses or use in self.allowed_uses
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "training_use_allowed": self.training_use_allowed,
            "allowed_uses": self.allowed_uses,
            "license_ref": self.license_ref,
            "redaction_required": self.redaction_required,
            "notes": self.notes,
            "grants": [grant.to_dict() for grant in self.grants],
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TrajectoryConsent:
        training_use_allowed = payload.get("training_use_allowed")
        if not isinstance(training_use_allowed, bool):
            raise ValidationError("training_use_allowed must be a boolean")
        redaction_required = payload.get("redaction_required", True)
        if not isinstance(redaction_required, bool):
            raise ValidationError("redaction_required must be a boolean")
        notes = payload.get("notes", "")
        if not isinstance(notes, str):
            raise ValidationError("notes must be a string")
        grants_payload = payload.get("grants", [])
        if not isinstance(grants_payload, list) or any(
            not isinstance(grant, dict) for grant in grants_payload
        ):
            raise ValidationError("grants must be a list of mappings")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            training_use_allowed=training_use_allowed,
            allowed_uses=require_string_list(payload.get("allowed_uses", []), "allowed_uses"),
            license_ref=_required_string(payload, "license_ref"),
            redaction_required=redaction_required,
            notes=notes,
            grants=[ConsentGrant.from_dict(grant) for grant in grants_payload],
            schema=_schema_or_default(payload, "schema", schemas.TRAJECTORY_CONSENT),
        )


@dataclass(frozen=True)
class TraceEvent:
    """A normalized event in a Faber trace JSONL stream."""

    attempt_id: str
    sequence: int
    event_type: str
    payload: dict[str, object]
    observed_at: str
    trust_level: str = "self_attested"
    provenance: dict[str, object] = field(default_factory=dict)
    redaction_policy_id: str | None = None
    id: str = field(default_factory=lambda: new_id("trace-event"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRACE_EVENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRACE_EVENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.attempt_id, "attempt_id")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise ValidationError("sequence must be an integer")
        if self.sequence < 0:
            raise ValidationError("sequence must be non-negative")
        require_non_empty_string(self.event_type, "event_type")
        require_mapping(self.payload, "payload")
        require_non_empty_string(self.observed_at, "observed_at")
        require_trust_level(self.trust_level)
        require_mapping(self.provenance, "provenance")
        if self.redaction_policy_id is not None:
            require_non_empty_string(self.redaction_policy_id, "redaction_policy_id")

    def redacted(self, policy: RedactionPolicy) -> TraceEvent:
        return TraceEvent(
            id=self.id,
            created_at=self.created_at,
            attempt_id=self.attempt_id,
            sequence=self.sequence,
            event_type=self.event_type,
            payload=policy.apply(self.payload),
            observed_at=self.observed_at,
            trust_level=self.trust_level,
            provenance=self.provenance,
            redaction_policy_id=policy.id,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "attempt_id": self.attempt_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "observed_at": self.observed_at,
            "payload": self.payload,
            "trust_level": self.trust_level,
            "provenance": self.provenance,
            "redaction_policy_id": self.redaction_policy_id,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TraceEvent:
        event_payload = payload.get("payload")
        if not isinstance(event_payload, dict):
            raise ValidationError("trace event payload must be a mapping")
        provenance = payload.get("provenance", {})
        if not isinstance(provenance, dict):
            raise ValidationError("trace event provenance must be a mapping")
        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise ValidationError("sequence must be an integer")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            attempt_id=_required_string(payload, "attempt_id"),
            sequence=sequence,
            event_type=_required_string(payload, "event_type"),
            observed_at=_required_string(payload, "observed_at"),
            payload=event_payload,
            trust_level=str(payload.get("trust_level", "self_attested")),
            provenance=provenance,
            redaction_policy_id=_optional_string(payload.get("redaction_policy_id")),
            schema=str(payload.get("schema", schemas.TRACE_EVENT)),
        )


@dataclass(frozen=True)
class TraceManifest:
    """Digest and provenance summary for a trace JSONL export."""

    attempt_id: str
    evidence_level: int
    trace_event_count: int
    trace_jsonl_digest: str
    trust_level: str
    included_event_types: list[str]
    redaction_policy: RedactionPolicy | None = None
    raw_trace_digest: str | None = None
    excluded_event_types: list[str] = field(default_factory=list)
    provenance: dict[str, object] = field(default_factory=dict)
    privacy_notes: str = ""
    id: str = field(default_factory=lambda: new_id("trace-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRACE_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRACE_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_evidence_level(self.evidence_level)
        if self.evidence_level < 2:
            raise ValidationError("trace manifest requires evidence level 2 or higher")
        if self.trace_event_count < 0:
            raise ValidationError("trace_event_count must be non-negative")
        require_digest(self.trace_jsonl_digest, "trace_jsonl_digest")
        require_optional_digest(self.raw_trace_digest, "raw_trace_digest")
        require_trust_level(self.trust_level)
        require_string_list(self.included_event_types, "included_event_types")
        require_string_list(self.excluded_event_types, "excluded_event_types")
        require_mapping(self.provenance, "provenance")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "attempt_id": self.attempt_id,
            "evidence_level": evidence_level(self.evidence_level).to_dict(),
            "trace_event_count": self.trace_event_count,
            "trace_jsonl_digest": self.trace_jsonl_digest,
            "raw_trace_digest": self.raw_trace_digest,
            "trust_level": self.trust_level,
            "included_event_types": self.included_event_types,
            "excluded_event_types": self.excluded_event_types,
            "redaction_policy": self.redaction_policy.to_dict() if self.redaction_policy else None,
            "provenance": self.provenance,
            "privacy_notes": self.privacy_notes,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class AttemptManifest:
    """Low-friction per-attempt manifest, suitable for .faber/attempt.json."""

    task_contract_id: str
    task_contract_digest: str
    attempt_id: str
    base_revision: str
    candidate_revision: str
    worker_id: str
    evidence_level: int
    redaction_policy: RedactionPolicy
    model_metadata: dict[str, object] = field(default_factory=dict)
    harness_metadata: dict[str, object] = field(default_factory=dict)
    runner_metadata: dict[str, object] = field(default_factory=dict)
    environment_metadata: dict[str, object] = field(default_factory=dict)
    tool_registry_digest: str | None = None
    nix_flake_lock_digest: str | None = None
    budget_metadata: dict[str, object] = field(default_factory=dict)
    cost_metadata: dict[str, object] = field(default_factory=dict)
    latency_metadata: dict[str, object] = field(default_factory=dict)
    training_consent: TrajectoryConsent | None = None
    trust_level: str = "self_attested"
    attestation: Attestation | None = None
    id: str = field(default_factory=lambda: new_id("attempt-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ATTEMPT_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ATTEMPT_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_digest(self.task_contract_digest, "task_contract_digest")
        require_non_empty_string(self.attempt_id, "attempt_id")
        require_non_empty_string(self.base_revision, "base_revision")
        require_non_empty_string(self.candidate_revision, "candidate_revision")
        require_non_empty_string(self.worker_id, "worker_id")
        require_evidence_level(self.evidence_level)
        if self.evidence_level < 1:
            raise ValidationError("attempt manifest requires evidence level 1 or higher")
        for field_name, value in [
            ("model_metadata", self.model_metadata),
            ("harness_metadata", self.harness_metadata),
            ("runner_metadata", self.runner_metadata),
            ("environment_metadata", self.environment_metadata),
            ("budget_metadata", self.budget_metadata),
            ("cost_metadata", self.cost_metadata),
            ("latency_metadata", self.latency_metadata),
        ]:
            require_mapping(value, field_name)
        if self.training_consent is not None and not isinstance(
            self.training_consent,
            TrajectoryConsent,
        ):
            raise ValidationError("training_consent must be a TrajectoryConsent")
        require_optional_digest(self.tool_registry_digest, "tool_registry_digest")
        require_optional_digest(self.nix_flake_lock_digest, "nix_flake_lock_digest")
        require_trust_level(self.trust_level)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "task_contract_digest": self.task_contract_digest,
            "attempt_id": self.attempt_id,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "worker_id": self.worker_id,
            "evidence_level": evidence_level(self.evidence_level).to_dict(),
            "model_metadata": self.model_metadata,
            "harness_metadata": self.harness_metadata,
            "runner_metadata": self.runner_metadata,
            "environment_metadata": self.environment_metadata,
            "tool_registry_digest": self.tool_registry_digest,
            "nix_flake_lock_digest": self.nix_flake_lock_digest,
            "budget_metadata": self.budget_metadata,
            "cost_metadata": self.cost_metadata,
            "latency_metadata": self.latency_metadata,
            "training_consent": self.training_consent.to_dict() if self.training_consent else None,
            "redaction_policy": self.redaction_policy.to_dict(),
            "trust_level": self.trust_level,
            "attestation": self.attestation.to_dict() if self.attestation else None,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> AttemptManifest:
        redaction_policy_payload = payload.get("redaction_policy")
        if not isinstance(redaction_policy_payload, dict):
            raise ValidationError("redaction_policy must be a mapping")
        attestation_payload = payload.get("attestation")
        if attestation_payload is None:
            attestation = None
        elif isinstance(attestation_payload, dict):
            attestation = Attestation.from_dict(attestation_payload)
        else:
            raise ValidationError("attestation must be a mapping or null")
        training_consent_payload = payload.get("training_consent")
        if training_consent_payload is None:
            training_consent = None
        elif isinstance(training_consent_payload, dict):
            training_consent = TrajectoryConsent.from_dict(training_consent_payload)
        else:
            raise ValidationError("training_consent must be a mapping or null")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            task_contract_id=_required_string(payload, "task_contract_id"),
            task_contract_digest=_required_string(payload, "task_contract_digest"),
            attempt_id=_required_string(payload, "attempt_id"),
            base_revision=_required_string(payload, "base_revision"),
            candidate_revision=_required_string(payload, "candidate_revision"),
            worker_id=_required_string(payload, "worker_id"),
            evidence_level=_evidence_level_number(payload.get("evidence_level")),
            redaction_policy=RedactionPolicy.from_dict(redaction_policy_payload),
            model_metadata=_mapping_field(payload, "model_metadata"),
            harness_metadata=_mapping_field(payload, "harness_metadata"),
            runner_metadata=_mapping_field(payload, "runner_metadata"),
            environment_metadata=_mapping_field(payload, "environment_metadata"),
            tool_registry_digest=_optional_string(payload.get("tool_registry_digest")),
            nix_flake_lock_digest=_optional_string(payload.get("nix_flake_lock_digest")),
            budget_metadata=_mapping_field(payload, "budget_metadata"),
            cost_metadata=_mapping_field(payload, "cost_metadata"),
            latency_metadata=_mapping_field(payload, "latency_metadata"),
            training_consent=training_consent,
            trust_level=_required_string(payload, "trust_level"),
            attestation=attestation,
            schema=_schema_or_default(payload, "schema", schemas.ATTEMPT_MANIFEST),
        )


@dataclass(frozen=True)
class EpisodePackage:
    """Replay-oriented evidence package for high-trust tasks."""

    task_contract_id: str
    attempt_id: str
    attempt_manifest: AttemptManifest
    trace_manifest: TraceManifest
    artifact_digests: list[str]
    replay_instructions: list[str]
    limitations: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("episode-package"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.EPISODE_PACKAGE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.EPISODE_PACKAGE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.attempt_id, "attempt_id")
        if self.attempt_manifest.attempt_id != self.attempt_id:
            raise ValidationError("episode package attempt manifest must match attempt_id")
        if self.trace_manifest.attempt_id != self.attempt_id:
            raise ValidationError("episode package trace manifest must match attempt_id")
        if self.trace_manifest.evidence_level < 4:
            raise ValidationError("episode package requires level 4 trace evidence")
        for digest in self.artifact_digests:
            require_digest(digest, "artifact_digests[]")
        require_string_list(self.replay_instructions, "replay_instructions", allow_empty=False)
        require_string_list(self.limitations, "limitations")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "attempt_id": self.attempt_id,
            "evidence_level": evidence_level(4).to_dict(),
            "attempt_manifest": self.attempt_manifest.to_dict(),
            "trace_manifest": self.trace_manifest.to_dict(),
            "artifact_digests": self.artifact_digests,
            "replay_instructions": self.replay_instructions,
            "limitations": self.limitations,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def write_trace_jsonl(
    events: list[TraceEvent],
    out_path: str | Path,
    *,
    redaction_policy: RedactionPolicy | None = None,
) -> str:
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = [
        (event.redacted(redaction_policy) if redaction_policy else event).to_dict()
        for event in events
        if redaction_policy is None or event.event_type not in redaction_policy.excluded_event_types
    ]
    text = "\n".join(canonical_json(record) for record in records)
    if records:
        text += "\n"
    output.write_text(text, encoding="utf-8")
    return sha256_digest(text.encode("utf-8"))


def read_trace_jsonl(path: str | Path) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValidationError("trace JSONL lines must be JSON objects")
        events.append(TraceEvent.from_dict(parsed))
    return events


def trace_manifest_from_events(
    *,
    attempt_id: str,
    events: list[TraceEvent],
    evidence_level_value: int,
    trace_jsonl_digest: str,
    trust_level: str,
    redaction_policy: RedactionPolicy | None = None,
    raw_trace_digest: str | None = None,
    provenance: dict[str, object] | None = None,
    privacy_notes: str = "",
    manifest_id: str | None = None,
    created_at: str | None = None,
) -> TraceManifest:
    included = sorted({event.event_type for event in events})
    return TraceManifest(
        id=manifest_id if manifest_id is not None else new_id("trace-manifest"),
        created_at=created_at if created_at is not None else utc_now(),
        attempt_id=attempt_id,
        evidence_level=evidence_level_value,
        trace_event_count=len(events),
        trace_jsonl_digest=trace_jsonl_digest,
        raw_trace_digest=raw_trace_digest,
        trust_level=trust_level,
        included_event_types=included,
        redaction_policy=redaction_policy,
        provenance=provenance or {},
        privacy_notes=privacy_notes,
    )


def trajectory_evidence_bundle(
    *,
    evidence_level_value: int,
    attempt_manifest: AttemptManifest | None = None,
    trace_manifest: TraceManifest | None = None,
    episode_package: EpisodePackage | None = None,
) -> dict[str, object]:
    require_evidence_level(evidence_level_value)
    if evidence_level_value >= 1 and attempt_manifest is None:
        raise ValidationError("level 1 or higher evidence requires an attempt manifest")
    if evidence_level_value >= 2 and trace_manifest is None:
        raise ValidationError("level 2 or higher evidence requires a trace manifest")
    if evidence_level_value >= 4 and episode_package is None:
        raise ValidationError("level 4 evidence requires an episode package")
    return {
        "evidence_level": evidence_level(evidence_level_value).to_dict(),
        "attempt_manifest": attempt_manifest.to_dict() if attempt_manifest else None,
        "trace_manifest": trace_manifest.to_dict() if trace_manifest else None,
        "episode_package": episode_package.to_dict() if episode_package else None,
        "richness_score": evidence_level_value,
    }


def _redact_path(payload: dict[str, object], path: list[str], replacement: str) -> None:
    if not path:
        return
    current: object = payload
    for part in path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(part)
    if isinstance(current, dict) and path[-1] in current:
        current[path[-1]] = replacement


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _required_string(payload: dict[str, object], field: str) -> str:
    return require_non_empty_string(payload.get(field), field)


def _schema_or_default(payload: dict[str, object], field: str, default: str) -> str:
    return require_non_empty_string(payload.get(field, default), field)


def _mapping_field(payload: dict[str, object], field: str) -> dict[str, object]:
    value = payload.get(field, {})
    return dict(require_mapping(value, field))


def _evidence_level_number(value: object) -> int:
    if isinstance(value, dict):
        value = value.get("level")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("evidence_level must be an integer between 0 and 4")
    return require_evidence_level(value)
