"""Training rights, consent provenance, visibility, and retention policies."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

TRAINING_USES = {
    "all",
    "audit",
    "evaluation",
    "private_hosted_learning",
    "public_dataset",
    "research",
    "rl",
    "router",
    "supervised",
}
CONSENT_PARTIES = {"solver_operator", "repo_owner_customer"}
VISIBILITY_LEVELS = {"public", "restricted", "private"}
VISIBILITY_RANK = {"public": 0, "restricted": 1, "private": 2}
RETENTION_CLASSES = {"audit_only", "limited", "standard", "indefinite"}
WITHDRAWAL_SCOPES = {
    "training",
    "rl",
    "supervised",
    "router",
    "research",
    "evaluation",
    "public_dataset",
}
PRIVATE_TRACE_FIELDS = (
    "attempt_manifest",
    "trace_manifest",
    "episode_package",
    "trace_events",
    "raw_trace",
    "private_trace",
)
CONSENT_PROVENANCE = {
    "self_attested",
    "runner_attested",
    "platform_observed",
    "repo_owner_verified",
    "provider_attested",
}


class VisibilityLevel:
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"


class RetentionClass:
    AUDIT_ONLY = "audit_only"
    LIMITED = "limited"
    STANDARD = "standard"
    INDEFINITE = "indefinite"


def require_training_uses(values: object, field_name: str) -> list[str]:
    uses = require_string_list(values, field_name)
    unknown = sorted(set(uses) - TRAINING_USES)
    if unknown:
        raise ValidationError(f"{field_name} contains unsupported uses: {unknown}")
    return uses


def require_visibility(value: str, field_name: str = "visibility") -> str:
    require_non_empty_string(value, field_name)
    if value not in VISIBILITY_LEVELS:
        raise ValidationError(f"{field_name} must be one of {sorted(VISIBILITY_LEVELS)}")
    return value


@dataclass(frozen=True)
class ConsentGrant:
    """One party's permission grant, including provenance and grant time."""

    party: str
    actor_ref: str
    allowed_uses: list[str]
    granted_at: str
    provenance: str
    id: str = field(default_factory=lambda: new_id("consent-grant"))
    schema: str = schemas.CONSENT_GRANT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.CONSENT_GRANT)
        require_non_empty_string(self.id, "id")
        if self.party not in CONSENT_PARTIES:
            raise ValidationError(f"party must be one of {sorted(CONSENT_PARTIES)}")
        require_non_empty_string(self.actor_ref, "actor_ref")
        require_training_uses(self.allowed_uses, "allowed_uses")
        require_non_empty_string(self.granted_at, "granted_at")
        if self.provenance not in CONSENT_PROVENANCE:
            raise ValidationError(
                f"provenance must be one of {sorted(CONSENT_PROVENANCE)}"
            )

    def allows(self, use: str) -> bool:
        require_non_empty_string(use, "use")
        return "all" in self.allowed_uses or use in self.allowed_uses

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "party": self.party,
            "actor_ref": self.actor_ref,
            "allowed_uses": self.allowed_uses,
            "granted_at": self.granted_at,
            "provenance": self.provenance,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ConsentGrant:
        return cls(
            id=_required_string(payload, "id"),
            party=_required_string(payload, "party"),
            actor_ref=_required_string(payload, "actor_ref"),
            allowed_uses=require_training_uses(payload.get("allowed_uses", []), "allowed_uses"),
            granted_at=_required_string(payload, "granted_at"),
            provenance=_required_string(payload, "provenance"),
            schema=_string_or_default(payload, "schema", schemas.CONSENT_GRANT),
        )


@dataclass(frozen=True)
class DataLicense:
    """Protocol metadata for permitted uses; not a legal conclusion."""

    license_id: str
    reference: str
    allowed_uses: list[str]
    public_redistribution: bool = False
    legal_review_required: bool = True
    schema: str = schemas.DATA_LICENSE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.DATA_LICENSE)
        require_non_empty_string(self.license_id, "license_id")
        require_non_empty_string(self.reference, "reference")
        require_training_uses(self.allowed_uses, "allowed_uses")
        if not isinstance(self.public_redistribution, bool):
            raise ValidationError("public_redistribution must be a boolean")
        if not isinstance(self.legal_review_required, bool):
            raise ValidationError("legal_review_required must be a boolean")

    def allows(self, use: str) -> bool:
        require_non_empty_string(use, "use")
        return "all" in self.allowed_uses or use in self.allowed_uses

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "license_id": self.license_id,
            "reference": self.reference,
            "allowed_uses": self.allowed_uses,
            "public_redistribution": self.public_redistribution,
            "legal_review_required": self.legal_review_required,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def audit_only(cls) -> DataLicense:
        return cls(
            license_id="audit-only",
            reference="faber:policy:audit-only",
            allowed_uses=["audit"],
            public_redistribution=False,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> DataLicense:
        return cls(
            license_id=_required_string(payload, "license_id"),
            reference=_required_string(payload, "reference"),
            allowed_uses=require_training_uses(payload.get("allowed_uses", []), "allowed_uses"),
            public_redistribution=_required_bool(
                payload,
                "public_redistribution",
                default=False,
            ),
            legal_review_required=_required_bool(
                payload,
                "legal_review_required",
                default=True,
            ),
            schema=_string_or_default(payload, "schema", schemas.DATA_LICENSE),
        )


@dataclass(frozen=True)
class TrainingUsePolicy:
    """Repository or task policy for training uses and visibility."""

    allowed_uses: list[str]
    required_consent_parties: list[str] = field(
        default_factory=lambda: ["solver_operator", "repo_owner_customer"]
    )
    visibility: str = VisibilityLevel.PRIVATE
    audit_retention_allowed: bool = True
    public_export_allowed: bool = False
    data_license: DataLicense | None = None
    id: str = field(default_factory=lambda: new_id("training-use-policy"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRAINING_USE_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRAINING_USE_POLICY)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_training_uses(self.allowed_uses, "allowed_uses")
        parties = require_string_list(
            self.required_consent_parties,
            "required_consent_parties",
        )
        unknown = sorted(set(parties) - CONSENT_PARTIES)
        if unknown:
            raise ValidationError(
                "required_consent_parties contains unsupported parties: "
                f"{unknown}"
            )
        require_visibility(self.visibility)
        if not isinstance(self.audit_retention_allowed, bool):
            raise ValidationError("audit_retention_allowed must be a boolean")
        if not isinstance(self.public_export_allowed, bool):
            raise ValidationError("public_export_allowed must be a boolean")
        if self.public_export_allowed and self.visibility != VisibilityLevel.PUBLIC:
            raise ValidationError("public_export_allowed requires public visibility")

    def allows(self, use: str) -> bool:
        require_non_empty_string(use, "use")
        policy_allows = "all" in self.allowed_uses or use in self.allowed_uses
        return policy_allows and (
            self.data_license is None or self.data_license.allows(use)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "allowed_uses": self.allowed_uses,
            "required_consent_parties": self.required_consent_parties,
            "visibility": self.visibility,
            "audit_retention_allowed": self.audit_retention_allowed,
            "public_export_allowed": self.public_export_allowed,
            "data_license": self.data_license.to_dict() if self.data_license else None,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> TrainingUsePolicy:
        raw_license = payload.get("data_license")
        if raw_license is None:
            data_license = None
        elif isinstance(raw_license, Mapping):
            data_license = DataLicense.from_dict(raw_license)
        else:
            raise ValidationError("data_license must be a mapping or null")
        return cls(
            id=_string_or_default(payload, "id", new_id("training-use-policy")),
            created_at=_string_or_default(payload, "created_at", utc_now()),
            allowed_uses=require_training_uses(payload.get("allowed_uses", []), "allowed_uses"),
            required_consent_parties=require_string_list(
                payload.get(
                    "required_consent_parties",
                    ["solver_operator", "repo_owner_customer"],
                ),
                "required_consent_parties",
            ),
            visibility=_string_or_default(payload, "visibility", VisibilityLevel.PRIVATE),
            audit_retention_allowed=_required_bool(
                payload,
                "audit_retention_allowed",
                default=True,
            ),
            public_export_allowed=_required_bool(
                payload,
                "public_export_allowed",
                default=False,
            ),
            data_license=data_license,
            schema=_string_or_default(payload, "schema", schemas.TRAINING_USE_POLICY),
        )


@dataclass(frozen=True)
class RetentionPolicy:
    retention_class: str
    private_content_days: int | None
    preserve_audit_receipts: bool = True
    accept_deletion_requests: bool = True
    id: str = field(default_factory=lambda: new_id("retention-policy"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.RETENTION_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.RETENTION_POLICY)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        if self.retention_class not in RETENTION_CLASSES:
            raise ValidationError(
                f"retention_class must be one of {sorted(RETENTION_CLASSES)}"
            )
        if self.private_content_days is not None and (
            not isinstance(self.private_content_days, int)
            or isinstance(self.private_content_days, bool)
            or self.private_content_days < 0
        ):
            raise ValidationError("private_content_days must be a non-negative integer or null")
        if not isinstance(self.preserve_audit_receipts, bool):
            raise ValidationError("preserve_audit_receipts must be a boolean")
        if not isinstance(self.accept_deletion_requests, bool):
            raise ValidationError("accept_deletion_requests must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "retention_class": self.retention_class,
            "private_content_days": self.private_content_days,
            "preserve_audit_receipts": self.preserve_audit_receipts,
            "accept_deletion_requests": self.accept_deletion_requests,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class DeletionRequest:
    trajectory_id: str
    requested_by: str
    scopes: list[str]
    requested_at: str = field(default_factory=utc_now)
    status: str = "requested"
    id: str = field(default_factory=lambda: new_id("deletion-request"))
    schema: str = schemas.DELETION_REQUEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.DELETION_REQUEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.trajectory_id, "trajectory_id")
        require_non_empty_string(self.requested_by, "requested_by")
        require_string_list(self.scopes, "scopes", allow_empty=False)
        require_non_empty_string(self.requested_at, "requested_at")
        require_non_empty_string(self.status, "status")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "trajectory_id": self.trajectory_id,
            "requested_by": self.requested_by,
            "scopes": self.scopes,
            "requested_at": self.requested_at,
            "status": self.status,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class DatasetWithdrawal:
    """Explicit withdrawal from future dataset uses, independent of audit retention."""

    trajectory_id: str
    requested_by: str
    reason: str
    effective_at: str
    scopes: list[str] = field(default_factory=lambda: ["training"])
    status: str = "active"
    id: str = field(default_factory=lambda: new_id("dataset-withdrawal"))
    schema: str = schemas.DATASET_WITHDRAWAL

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.DATASET_WITHDRAWAL)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.trajectory_id, "trajectory_id")
        require_non_empty_string(self.requested_by, "requested_by")
        require_non_empty_string(self.reason, "reason")
        require_non_empty_string(self.effective_at, "effective_at")
        scopes = require_string_list(self.scopes, "scopes", allow_empty=False)
        unknown = sorted(set(scopes) - WITHDRAWAL_SCOPES)
        if unknown:
            raise ValidationError(f"scopes contains unsupported withdrawals: {unknown}")
        if self.status not in {"active", "revoked"}:
            raise ValidationError("status must be active or revoked")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "trajectory_id": self.trajectory_id,
            "requested_by": self.requested_by,
            "reason": self.reason,
            "effective_at": self.effective_at,
            "scopes": self.scopes,
            "status": self.status,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class TombstoneRecord:
    """Minimal proof that content was removed while audit references remain."""

    trajectory_id: str
    original_record_digest: str
    retained_record_digest: str
    deletion_request_digest: str
    removed_fields: list[str]
    preserved_audit_references: dict[str, str]
    id: str
    created_at: str
    schema: str = schemas.TOMBSTONE_RECORD

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TOMBSTONE_RECORD)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.trajectory_id, "trajectory_id")
        require_digest(self.original_record_digest, "original_record_digest")
        require_digest(self.retained_record_digest, "retained_record_digest")
        require_digest(self.deletion_request_digest, "deletion_request_digest")
        require_string_list(self.removed_fields, "removed_fields")
        require_mapping(self.preserved_audit_references, "preserved_audit_references")
        for key, value in self.preserved_audit_references.items():
            require_non_empty_string(key, "preserved_audit_references key")
            require_non_empty_string(value, f"preserved_audit_references.{key}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "trajectory_id": self.trajectory_id,
            "original_record_digest": self.original_record_digest,
            "retained_record_digest": self.retained_record_digest,
            "deletion_request_digest": self.deletion_request_digest,
            "removed_fields": self.removed_fields,
            "preserved_audit_references": self.preserved_audit_references,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class DeletionReport:
    """Digest-preserving completion record for one deletion request."""

    trajectory_id: str
    deletion_request_id: str
    deletion_request_digest: str
    retention_policy_digest: str
    original_record_digest: str
    retained_record_digest: str
    removed_field_digests: dict[str, str]
    preserved_audit_references: dict[str, str]
    tombstone_digest: str
    id: str
    completed_at: str
    status: str = "completed"
    schema: str = schemas.DELETION_REPORT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.DELETION_REPORT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.completed_at, "completed_at")
        require_non_empty_string(self.trajectory_id, "trajectory_id")
        require_non_empty_string(self.deletion_request_id, "deletion_request_id")
        for field_name, value in [
            ("deletion_request_digest", self.deletion_request_digest),
            ("retention_policy_digest", self.retention_policy_digest),
            ("original_record_digest", self.original_record_digest),
            ("retained_record_digest", self.retained_record_digest),
            ("tombstone_digest", self.tombstone_digest),
        ]:
            require_digest(value, field_name)
        _require_digest_mapping(self.removed_field_digests, "removed_field_digests")
        require_mapping(self.preserved_audit_references, "preserved_audit_references")
        if self.status != "completed":
            raise ValidationError("deletion report status must be completed")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "completed_at": self.completed_at,
            "status": self.status,
            "trajectory_id": self.trajectory_id,
            "deletion_request_id": self.deletion_request_id,
            "deletion_request_digest": self.deletion_request_digest,
            "retention_policy_digest": self.retention_policy_digest,
            "original_record_digest": self.original_record_digest,
            "retained_record_digest": self.retained_record_digest,
            "removed_field_digests": self.removed_field_digests,
            "preserved_audit_references": self.preserved_audit_references,
            "tombstone_digest": self.tombstone_digest,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class DatasetExportPolicy:
    purpose: str
    public: bool = False
    include_restricted: bool = False

    def __post_init__(self) -> None:
        if self.purpose not in TRAINING_USES:
            raise ValidationError(f"purpose must be one of {sorted(TRAINING_USES)}")
        if not isinstance(self.public, bool):
            raise ValidationError("public must be a boolean")
        if not isinstance(self.include_restricted, bool):
            raise ValidationError("include_restricted must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "public": self.public,
            "include_restricted": self.include_restricted,
        }


def resolve_training_use_policy(
    repository_policy: TrainingUsePolicy,
    task_policy: TrainingUsePolicy | None,
) -> TrainingUsePolicy:
    """Resolve defaults by retaining the stricter permission from either level."""

    if task_policy is None:
        return repository_policy
    repository_uses = set(repository_policy.allowed_uses)
    task_uses = set(task_policy.allowed_uses)
    if "all" in repository_uses:
        allowed_uses = task_uses
    elif "all" in task_uses:
        allowed_uses = repository_uses
    else:
        allowed_uses = repository_uses & task_uses
    visibility = max(
        [repository_policy.visibility, task_policy.visibility],
        key=VISIBILITY_RANK.__getitem__,
    )
    policy_digest = sha256_digest(
        [repository_policy.digest(), task_policy.digest()]
    )[-16:]
    return TrainingUsePolicy(
        id=f"training-use-policy_resolved_{policy_digest}",
        created_at=max(repository_policy.created_at, task_policy.created_at),
        allowed_uses=sorted(allowed_uses),
        required_consent_parties=sorted(
            set(repository_policy.required_consent_parties)
            | set(task_policy.required_consent_parties)
        ),
        visibility=visibility,
        audit_retention_allowed=(
            repository_policy.audit_retention_allowed
            and task_policy.audit_retention_allowed
        ),
        public_export_allowed=(
            repository_policy.public_export_allowed
            and task_policy.public_export_allowed
            and visibility == VisibilityLevel.PUBLIC
        ),
        data_license=task_policy.data_license or repository_policy.data_license,
    )


def record_export_allowed(
    record: Mapping[str, object],
    export_policy: DatasetExportPolicy,
) -> bool:
    """Return whether rights, consent, and visibility permit one export."""

    if export_policy.purpose != "audit" and record_withdrawn_for(record, export_policy.purpose):
        return False
    policy = _policy_from_record(record)
    if export_policy.purpose == "audit":
        return policy.audit_retention_allowed and isinstance(record.get("receipt"), Mapping)
    if not policy.allows(export_policy.purpose):
        return False
    if export_policy.public:
        if policy.visibility != VisibilityLevel.PUBLIC or not policy.public_export_allowed:
            return False
    elif policy.visibility == VisibilityLevel.RESTRICTED and not export_policy.include_restricted:
        return False
    consent = _consent_payload(record)
    if not consent or consent.get("training_use_allowed") is not True:
        return False
    allowed_uses = consent.get("allowed_uses", [])
    if not _use_allowed(allowed_uses, export_policy.purpose):
        return False
    grants = consent.get("grants", [])
    if policy.required_consent_parties:
        if not isinstance(grants, list):
            return False
        for party in policy.required_consent_parties:
            if not any(_grant_allows(grant, party, export_policy.purpose) for grant in grants):
                return False
    return True


def audit_retained_record(
    record: Mapping[str, object],
    *,
    request: DeletionRequest,
    policy: RetentionPolicy,
) -> dict[str, object]:
    """Remove private learning payloads while preserving minimal audit evidence."""

    retained, _report, _tombstone = apply_deletion_request(
        record,
        request=request,
        policy=policy,
        completed_at=request.requested_at,
    )
    return retained


def apply_dataset_withdrawal(
    record: Mapping[str, object],
    withdrawal: DatasetWithdrawal,
) -> dict[str, object]:
    """Attach an inspectable withdrawal without deleting audit evidence."""

    if str(record.get("id")) != withdrawal.trajectory_id:
        raise ValidationError("dataset withdrawal trajectory_id does not match record id")
    updated = copy.deepcopy(dict(record))
    updated["dataset_withdrawal"] = withdrawal.to_dict()
    updated["training_withdrawn"] = withdrawal.status == "active" and (
        "training" in withdrawal.scopes
    )
    return updated


def record_withdrawn_for(record: Mapping[str, object], purpose: str = "training") -> bool:
    """Return whether an active withdrawal covers the requested dataset purpose."""

    if record.get("training_withdrawn") is True and purpose != "audit":
        return True
    withdrawal = record.get("dataset_withdrawal")
    if isinstance(withdrawal, Mapping) and withdrawal.get("status") == "active":
        if withdrawal.get("trajectory_id") != record.get("id"):
            return False
        scopes = withdrawal.get("scopes", [])
        if isinstance(scopes, list) and (
            "training" in scopes or purpose in scopes
        ):
            return True
    deletion = record.get("deletion")
    if isinstance(deletion, Mapping):
        scopes = deletion.get("scopes", [])
        if isinstance(scopes, list) and "training" in scopes and purpose != "audit":
            return True
    return False


def apply_deletion_request(
    record: Mapping[str, object],
    *,
    request: DeletionRequest,
    policy: RetentionPolicy,
    completed_at: str | None = None,
) -> tuple[dict[str, object], DeletionReport, TombstoneRecord]:
    """Apply scoped deletion and return retained content plus audit records."""

    if str(record.get("id")) != request.trajectory_id:
        raise ValidationError("deletion request trajectory_id does not match record id")
    if not policy.accept_deletion_requests:
        raise ValidationError("retention policy does not accept deletion requests")
    completion_time = completed_at or utc_now()
    require_non_empty_string(completion_time, "completed_at")
    original = copy.deepcopy(dict(record))
    original_digest = sha256_digest(original)
    retained = copy.deepcopy(original)
    removed_field_digests: dict[str, str] = {}
    if "private_trace" in request.scopes:
        for field_name in PRIVATE_TRACE_FIELDS:
            if field_name in retained and retained[field_name] is not None:
                removed_field_digests[field_name] = sha256_digest(retained[field_name])
                retained[field_name] = None
    preserved_references = _audit_references(original)
    if not policy.preserve_audit_receipts and retained.get("receipt") is not None:
        removed_field_digests["receipt"] = sha256_digest(retained["receipt"])
        retained["receipt"] = None
    if "training" in request.scopes:
        withdrawal = DatasetWithdrawal(
            id=f"dataset-withdrawal_{request.id}",
            trajectory_id=request.trajectory_id,
            requested_by=request.requested_by,
            reason="Training withdrawal requested with private-content deletion.",
            effective_at=completion_time,
            scopes=["training"],
        )
        retained["dataset_withdrawal"] = withdrawal.to_dict()
        retained["training_withdrawn"] = True
    retained["deletion"] = {
        "request_digest": request.digest(),
        "retention_policy_digest": policy.digest(),
        "scopes": request.scopes,
        "original_record_digest": original_digest,
        "removed_field_digests": dict(sorted(removed_field_digests.items())),
        "audit_receipt_preserved": isinstance(retained.get("receipt"), Mapping),
    }
    retained_digest = sha256_digest(retained)
    stable_suffix = request.digest().split(":", 1)[1][:24]
    tombstone = TombstoneRecord(
        id=f"tombstone-record_{stable_suffix}",
        created_at=completion_time,
        trajectory_id=request.trajectory_id,
        original_record_digest=original_digest,
        retained_record_digest=retained_digest,
        deletion_request_digest=request.digest(),
        removed_fields=sorted(removed_field_digests),
        preserved_audit_references=preserved_references,
    )
    report = DeletionReport(
        id=f"deletion-report_{stable_suffix}",
        completed_at=completion_time,
        trajectory_id=request.trajectory_id,
        deletion_request_id=request.id,
        deletion_request_digest=request.digest(),
        retention_policy_digest=policy.digest(),
        original_record_digest=original_digest,
        retained_record_digest=retained_digest,
        removed_field_digests=dict(sorted(removed_field_digests.items())),
        preserved_audit_references=preserved_references,
        tombstone_digest=tombstone.digest(),
    )
    return retained, report, tombstone


def _policy_from_record(record: Mapping[str, object]) -> TrainingUsePolicy:
    contract = record.get("contract")
    if not isinstance(contract, Mapping):
        return _default_policy()
    repository_raw = contract.get("repository_training_policy")
    task_raw = contract.get("training_use_policy")
    repository_policy = (
        TrainingUsePolicy.from_dict(repository_raw)
        if isinstance(repository_raw, Mapping)
        else _default_policy()
    )
    task_policy = (
        TrainingUsePolicy.from_dict(task_raw) if isinstance(task_raw, Mapping) else None
    )
    return resolve_training_use_policy(repository_policy, task_policy)


def _default_policy() -> TrainingUsePolicy:
    return TrainingUsePolicy(
        id="training-use-policy_default-audit-only",
        created_at="1970-01-01T00:00:00Z",
        allowed_uses=["audit"],
        required_consent_parties=[],
        visibility=VisibilityLevel.PRIVATE,
        audit_retention_allowed=True,
    )


def _consent_payload(record: Mapping[str, object]) -> Mapping[str, object] | None:
    direct = record.get("trajectory_consent")
    if isinstance(direct, Mapping):
        return direct
    manifest = record.get("attempt_manifest")
    if isinstance(manifest, Mapping):
        consent = manifest.get("training_consent")
        if isinstance(consent, Mapping):
            return consent
    return None


def _grant_allows(grant: object, party: str, purpose: str) -> bool:
    return (
        isinstance(grant, Mapping)
        and grant.get("party") == party
        and _use_allowed(grant.get("allowed_uses", []), purpose)
    )


def _use_allowed(raw_uses: object, purpose: str) -> bool:
    return isinstance(raw_uses, list) and (
        "all" in raw_uses or purpose in raw_uses
    )


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    return require_non_empty_string(value, field_name)


def _string_or_default(
    payload: Mapping[str, object],
    field_name: str,
    default: str,
) -> str:
    value = payload.get(field_name, default)
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    return require_non_empty_string(value, field_name)


def _required_bool(
    payload: Mapping[str, object],
    field_name: str,
    *,
    default: bool,
) -> bool:
    value = payload.get(field_name, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean")
    return value


def _audit_references(record: Mapping[str, object]) -> dict[str, str]:
    references: dict[str, str] = {}
    for field_name in ["contract", "attempt", "receipt", "settlement"]:
        payload = record.get(field_name)
        if not isinstance(payload, Mapping):
            continue
        record_id = payload.get("id")
        if isinstance(record_id, str) and record_id:
            references[f"{field_name}_id"] = record_id
        references[f"{field_name}_digest"] = sha256_digest(dict(payload))
    return references


def _require_digest_mapping(value: Mapping[str, str], field_name: str) -> None:
    require_mapping(value, field_name)
    for key, digest in value.items():
        require_non_empty_string(key, f"{field_name} key")
        require_digest(digest, f"{field_name}.{key}")
