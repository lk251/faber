"""Trajectory quality tiers and RL-grade validation."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from faber import schemas
from faber.canonical_json import to_jsonable
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

TrajectoryRecord = dict[str, object]

TRAJECTORY_QUALITY_ORDER = {
    "pr_only": 0,
    "manifest": 1,
    "trace": 2,
    "episode": 3,
}
RL_GRADE_TIERS = {"trace", "episode"}
PROCESS_EVENT_PREFIXES = (
    "action.",
    "tool.",
    "context.",
    "verification.",
    "verifier.",
    "failure.",
    "intervention.",
    "outcome.",
)
OBSERVATION_EVENT_PREFIXES = (
    "context.",
    "verification.",
    "verifier.",
    "failure.",
    "outcome.",
)
_EPOCH = "1970-01-01T00:00:00Z"


@dataclass(frozen=True)
class TrajectoryQualityTier:
    """Named quality tier for normalized trajectories."""

    name: str
    rank: int
    evidence_level_minimum: int
    rl_grade_candidate: bool
    description: str

    def __post_init__(self) -> None:
        require_quality_tier(self.name)
        if self.rank != TRAJECTORY_QUALITY_ORDER[self.name]:
            raise ValidationError("trajectory quality tier rank is invalid")
        if self.evidence_level_minimum < 0 or self.evidence_level_minimum > 4:
            raise ValidationError("evidence_level_minimum must be between 0 and 4")
        if not isinstance(self.rl_grade_candidate, bool):
            raise ValidationError("rl_grade_candidate must be a boolean")
        require_non_empty_string(self.description, "description")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "rank": self.rank,
            "evidence_level_minimum": self.evidence_level_minimum,
            "rl_grade_candidate": self.rl_grade_candidate,
            "description": self.description,
        }


def trajectory_quality_tier(name: str) -> TrajectoryQualityTier:
    """Return a named quality tier definition."""

    require_quality_tier(name)
    descriptions = {
        "pr_only": "Final artifact and outcome only; useful customer work, not RL-grade.",
        "manifest": "PR plus attempt manifest; useful for router supervised training.",
        "trace": "Manifest plus process trace; candidate RL-grade when reward and consent exist.",
        "episode": "Replayable episode package; strongest RL-grade trajectory evidence.",
    }
    evidence_minimums = {"pr_only": 0, "manifest": 1, "trace": 2, "episode": 4}
    return TrajectoryQualityTier(
        name=name,
        rank=TRAJECTORY_QUALITY_ORDER[name],
        evidence_level_minimum=evidence_minimums[name],
        rl_grade_candidate=name in RL_GRADE_TIERS,
        description=descriptions[name],
    )


@dataclass(frozen=True)
class TrajectoryRequirement:
    """Minimum trajectory quality policy declared by a task contract or budget."""

    minimum_quality_tier: str = "pr_only"
    require_training_eligible: bool = False
    require_rl_grade: bool = False
    full_payout_minimum_tier: str | None = None
    bonus_minimum_tier: str | None = None
    notes: str = ""
    id: str = field(default_factory=lambda: new_id("trajectory-requirement"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRAJECTORY_REQUIREMENT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRAJECTORY_REQUIREMENT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_quality_tier(self.minimum_quality_tier)
        if not isinstance(self.require_training_eligible, bool):
            raise ValidationError("require_training_eligible must be a boolean")
        if not isinstance(self.require_rl_grade, bool):
            raise ValidationError("require_rl_grade must be a boolean")
        if self.full_payout_minimum_tier is not None:
            require_quality_tier(self.full_payout_minimum_tier)
        if self.bonus_minimum_tier is not None:
            require_quality_tier(self.bonus_minimum_tier)
        if not isinstance(self.notes, str):
            raise ValidationError("notes must be a string")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "minimum_quality_tier": self.minimum_quality_tier,
            "require_training_eligible": self.require_training_eligible,
            "require_rl_grade": self.require_rl_grade,
            "full_payout_minimum_tier": self.full_payout_minimum_tier,
            "bonus_minimum_tier": self.bonus_minimum_tier,
            "notes": self.notes,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TrajectoryRequirement:
        require_training_eligible = payload.get("require_training_eligible", False)
        require_rl_grade = payload.get("require_rl_grade", False)
        if not isinstance(require_training_eligible, bool):
            raise ValidationError("require_training_eligible must be a boolean")
        if not isinstance(require_rl_grade, bool):
            raise ValidationError("require_rl_grade must be a boolean")
        return cls(
            id=_string_or_default(payload, "id", new_id("trajectory-requirement")),
            created_at=_string_or_default(payload, "created_at", utc_now()),
            minimum_quality_tier=_string_or_default(
                payload,
                "minimum_quality_tier",
                "pr_only",
            ),
            require_training_eligible=require_training_eligible,
            require_rl_grade=require_rl_grade,
            full_payout_minimum_tier=_optional_string(payload.get("full_payout_minimum_tier")),
            bonus_minimum_tier=_optional_string(payload.get("bonus_minimum_tier")),
            notes=str(payload.get("notes", "")),
            schema=_string_or_default(payload, "schema", schemas.TRAJECTORY_REQUIREMENT),
        )


@dataclass(frozen=True)
class TrainingEligibility:
    """Training-use eligibility derived from consent and redaction policy."""

    eligible: bool
    allowed_uses: list[str]
    consent_id: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.eligible, bool):
            raise ValidationError("eligible must be a boolean")
        require_string_list(self.allowed_uses, "allowed_uses")
        if self.consent_id is not None:
            require_non_empty_string(self.consent_id, "consent_id")
        if not isinstance(self.reason, str):
            raise ValidationError("reason must be a string")

    def allows(self, use: str) -> bool:
        require_non_empty_string(use, "use")
        return self.eligible and ("all" in self.allowed_uses or use in self.allowed_uses)

    def to_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "allowed_uses": self.allowed_uses,
            "consent_id": self.consent_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TraceCompleteness:
    """Completeness summary for ordered process traces."""

    event_count: int
    included_event_types: list[str]
    has_actions: bool
    has_observations: bool
    has_verifier_events: bool
    redacted: bool = False

    def __post_init__(self) -> None:
        if self.event_count < 0:
            raise ValidationError("event_count must be non-negative")
        require_string_list(self.included_event_types, "included_event_types")
        for field_name, value in [
            ("has_actions", self.has_actions),
            ("has_observations", self.has_observations),
            ("has_verifier_events", self.has_verifier_events),
            ("redacted", self.redacted),
        ]:
            if not isinstance(value, bool):
                raise ValidationError(f"{field_name} must be a boolean")

    @property
    def has_process_evidence(self) -> bool:
        return self.event_count > 0 and (
            self.has_actions or self.has_observations or self.has_verifier_events
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_count": self.event_count,
            "included_event_types": self.included_event_types,
            "has_actions": self.has_actions,
            "has_observations": self.has_observations,
            "has_verifier_events": self.has_verifier_events,
            "has_process_evidence": self.has_process_evidence,
            "redacted": self.redacted,
        }


@dataclass(frozen=True)
class ProcessEvidence:
    """Process evidence used to decide if a trajectory is RL-grade."""

    evidence_level: int
    has_ordered_events: bool
    trace_completeness: TraceCompleteness
    trace_manifest_digest: str | None = None
    episode_package_digest: str | None = None
    provenance: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.evidence_level < 0 or self.evidence_level > 4:
            raise ValidationError("evidence_level must be between 0 and 4")
        if not isinstance(self.has_ordered_events, bool):
            raise ValidationError("has_ordered_events must be a boolean")
        require_mapping(self.provenance, "provenance")

    @property
    def satisfies_rl_process(self) -> bool:
        return (
            self.evidence_level >= 2
            and self.has_ordered_events
            and self.trace_completeness.has_process_evidence
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_level": self.evidence_level,
            "has_ordered_events": self.has_ordered_events,
            "trace_completeness": self.trace_completeness.to_dict(),
            "trace_manifest_digest": self.trace_manifest_digest,
            "episode_package_digest": self.episode_package_digest,
            "provenance": self.provenance,
            "satisfies_rl_process": self.satisfies_rl_process,
        }


@dataclass(frozen=True)
class RewardSignal:
    """Outcome, reward, cost, and latency signal for learning."""

    present: bool
    outcome: str
    reward_minor_units: int | None = None
    cost_minor_units: int | None = None
    latency_seconds: int | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.present, bool):
            raise ValidationError("present must be a boolean")
        require_non_empty_string(self.outcome, "outcome")
        for field_name, value in [
            ("reward_minor_units", self.reward_minor_units),
            ("cost_minor_units", self.cost_minor_units),
            ("latency_seconds", self.latency_seconds),
        ]:
            if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValidationError(f"{field_name} must be an integer")
            if isinstance(value, int) and value < 0:
                raise ValidationError(f"{field_name} must be non-negative")
        if self.currency is not None:
            require_non_empty_string(self.currency, "currency")

    def to_dict(self) -> dict[str, object]:
        return {
            "present": self.present,
            "outcome": self.outcome,
            "reward_minor_units": self.reward_minor_units,
            "cost_minor_units": self.cost_minor_units,
            "latency_seconds": self.latency_seconds,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class EnvironmentReplayability:
    """Environment and repository replay evidence summary."""

    level: str
    has_environment_evidence: bool
    has_repository_snapshot: bool
    platform: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_string(self.level, "level")
        if not isinstance(self.has_environment_evidence, bool):
            raise ValidationError("has_environment_evidence must be a boolean")
        if not isinstance(self.has_repository_snapshot, bool):
            raise ValidationError("has_repository_snapshot must be a boolean")
        if self.platform is not None:
            require_non_empty_string(self.platform, "platform")

    @property
    def supports_rl_grade(self) -> bool:
        return self.has_environment_evidence and self.level != "opaque"

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "has_environment_evidence": self.has_environment_evidence,
            "has_repository_snapshot": self.has_repository_snapshot,
            "platform": self.platform,
            "supports_rl_grade": self.supports_rl_grade,
        }


@dataclass(frozen=True)
class TrajectoryValidationReport:
    """Structured quality report for a normalized trajectory record."""

    trajectory_id: str
    quality_tier: str
    evidence_level: int
    training_eligibility: TrainingEligibility
    process_evidence: ProcessEvidence
    reward_signal: RewardSignal
    environment_replayability: EnvironmentReplayability
    requirement: TrajectoryRequirement
    issues: list[dict[str, object]]
    complete_record_digest: str
    usable_for_audit: bool
    usable_for_supervised_training: bool
    usable_for_attempt_quality_prediction: bool
    usable_for_rl_training: bool
    accepted_positive: bool
    failed_negative_useful: bool
    meets_requirement: bool
    full_payout_eligible: bool
    bonus_eligible: bool
    id: str = field(default_factory=lambda: new_id("trajectory-validation-report"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.TRAJECTORY_VALIDATION_REPORT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TRAJECTORY_VALIDATION_REPORT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.trajectory_id, "trajectory_id")
        require_quality_tier(self.quality_tier)
        if self.evidence_level < 0 or self.evidence_level > 4:
            raise ValidationError("evidence_level must be between 0 and 4")
        for index, issue in enumerate(self.issues):
            require_mapping(issue, f"issues[{index}]")
        require_non_empty_string(self.complete_record_digest, "complete_record_digest")
        for field_name, value in [
            ("usable_for_audit", self.usable_for_audit),
            ("usable_for_supervised_training", self.usable_for_supervised_training),
            (
                "usable_for_attempt_quality_prediction",
                self.usable_for_attempt_quality_prediction,
            ),
            ("usable_for_rl_training", self.usable_for_rl_training),
            ("accepted_positive", self.accepted_positive),
            ("failed_negative_useful", self.failed_negative_useful),
            ("meets_requirement", self.meets_requirement),
            ("full_payout_eligible", self.full_payout_eligible),
            ("bonus_eligible", self.bonus_eligible),
        ]:
            if not isinstance(value, bool):
                raise ValidationError(f"{field_name} must be a boolean")

    @property
    def is_rl_grade(self) -> bool:
        return self.usable_for_rl_training

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "trajectory_id": self.trajectory_id,
            "quality_tier": trajectory_quality_tier(self.quality_tier).to_dict(),
            "evidence_level": self.evidence_level,
            "training_eligibility": self.training_eligibility.to_dict(),
            "process_evidence": self.process_evidence.to_dict(),
            "reward_signal": self.reward_signal.to_dict(),
            "environment_replayability": self.environment_replayability.to_dict(),
            "requirement": self.requirement.to_dict(),
            "issues": self.issues,
            "complete_record_digest": self.complete_record_digest,
            "usable_for_audit": self.usable_for_audit,
            "usable_for_supervised_training": self.usable_for_supervised_training,
            "usable_for_attempt_quality_prediction": self.usable_for_attempt_quality_prediction,
            "usable_for_rl_training": self.usable_for_rl_training,
            "is_rl_grade": self.is_rl_grade,
            "accepted_positive": self.accepted_positive,
            "failed_negative_useful": self.failed_negative_useful,
            "meets_requirement": self.meets_requirement,
            "full_payout_eligible": self.full_payout_eligible,
            "bonus_eligible": self.bonus_eligible,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def validate_trajectory_quality(
    trajectory: object,
    *,
    requirement: TrajectoryRequirement | None = None,
    report_id: str | None = None,
    created_at: str | None = None,
) -> TrajectoryValidationReport:
    """Validate whether a normalized trajectory is RL-grade."""

    record = trajectory_record(trajectory)
    record.pop("trajectory_quality", None)
    contract = _mapping(record.get("contract"))
    attempt = _mapping(record.get("attempt"))
    receipt = _mapping(record.get("receipt"))
    requirement_value = requirement or requirement_from_contract(contract)
    manifest = _attempt_manifest_payload(record, attempt)
    trace_manifest = _trace_manifest_payload(record, attempt)
    episode_package = _mapping_or_none(record.get("episode_package"))
    evidence_level = _evidence_level(record, manifest, trace_manifest, episode_package)
    quality_tier = _quality_tier(manifest, trace_manifest, episode_package)
    training_eligibility = _training_eligibility(record, manifest)
    process_evidence = _process_evidence(evidence_level, trace_manifest, episode_package)
    reward_signal = _reward_signal(record, receipt)
    environment_replayability = _environment_replayability(contract, manifest, episode_package)
    issues = _validation_issues(
        record=record,
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        manifest=manifest,
        process_evidence=process_evidence,
        reward_signal=reward_signal,
        environment_replayability=environment_replayability,
        training_eligibility=training_eligibility,
        quality_tier=quality_tier,
    )
    usable_for_audit = bool(attempt and receipt)
    usable_for_supervised = quality_rank(quality_tier) >= quality_rank("manifest")
    usable_for_attempt_quality = usable_for_supervised and bool(receipt)
    usable_for_rl = (
        quality_tier in RL_GRADE_TIERS
        and process_evidence.satisfies_rl_process
        and reward_signal.present
        and environment_replayability.supports_rl_grade
        and training_eligibility.allows("rl")
        and not _has_issue(issues, "blocker")
    )
    accepted = receipt.get("accepted") is True
    rejected = receipt.get("accepted") is False or record.get("outcome") in {
        "rejected",
        "failed",
    }
    meets_requirement = _meets_requirement(
        quality_tier=quality_tier,
        is_rl_grade=usable_for_rl,
        training_eligibility=training_eligibility,
        requirement=requirement_value,
    )
    full_payout_tier = requirement_value.full_payout_minimum_tier
    full_payout_eligible = meets_requirement and (
        full_payout_tier is None or quality_rank(quality_tier) >= quality_rank(full_payout_tier)
    )
    bonus_tier = requirement_value.bonus_minimum_tier
    bonus_eligible = (
        bonus_tier is not None
        and meets_requirement
        and quality_rank(quality_tier) >= quality_rank(bonus_tier)
    )
    requirement_issues = _requirement_issues(
        quality_tier=quality_tier,
        is_rl_grade=usable_for_rl,
        training_eligibility=training_eligibility,
        requirement=requirement_value,
        full_payout_eligible=full_payout_eligible,
        bonus_eligible=bonus_eligible,
    )
    issues.extend(requirement_issues)
    return TrajectoryValidationReport(
        id=report_id if report_id is not None else new_id("trajectory-validation-report"),
        created_at=created_at if created_at is not None else utc_now(),
        trajectory_id=str(record.get("id", "trajectory_unknown")),
        quality_tier=quality_tier,
        evidence_level=evidence_level,
        training_eligibility=training_eligibility,
        process_evidence=process_evidence,
        reward_signal=reward_signal,
        environment_replayability=environment_replayability,
        requirement=requirement_value,
        issues=issues,
        complete_record_digest=sha256_digest(record),
        usable_for_audit=usable_for_audit,
        usable_for_supervised_training=usable_for_supervised,
        usable_for_attempt_quality_prediction=usable_for_attempt_quality,
        usable_for_rl_training=usable_for_rl,
        accepted_positive=usable_for_rl and accepted,
        failed_negative_useful=usable_for_rl and rejected,
        meets_requirement=meets_requirement,
        full_payout_eligible=full_payout_eligible,
        bonus_eligible=bonus_eligible,
    )


def annotate_trajectory_record(trajectory: object) -> TrajectoryRecord:
    """Return a trajectory record with quality validation metadata attached."""

    record = trajectory_record(trajectory)
    record.pop("trajectory_quality", None)
    trajectory_id = str(record.get("id") or "trajectory_unknown")
    created_at = record.get("created_at")
    report = validate_trajectory_quality(
        record,
        report_id=f"trajectory-validation-report_{trajectory_id}",
        created_at=created_at if isinstance(created_at, str) and created_at else _EPOCH,
    )
    record["trajectory_quality"] = report.to_dict()
    return record


def filter_training_records(
    records: list[TrajectoryRecord],
    *,
    require_rl_grade: bool = True,
    require_training_eligible: bool = True,
    minimum_quality_tier: str | None = None,
) -> list[TrajectoryRecord]:
    """Filter annotated or raw records for training dataset export."""

    if minimum_quality_tier is not None:
        require_quality_tier(minimum_quality_tier)
    filtered: list[TrajectoryRecord] = []
    for record in records:
        report = validate_trajectory_quality(record)
        if require_rl_grade and not report.is_rl_grade:
            continue
        if require_training_eligible and not report.training_eligibility.eligible:
            continue
        if minimum_quality_tier is not None and quality_rank(report.quality_tier) < quality_rank(
            minimum_quality_tier
        ):
            continue
        annotated = copy.deepcopy(record)
        annotated["trajectory_quality"] = report.to_dict()
        filtered.append(annotated)
    return filtered


def requirement_from_contract(contract: dict[str, object]) -> TrajectoryRequirement:
    """Extract a trajectory requirement from a contract payload."""

    raw = contract.get("trajectory_requirement")
    if isinstance(raw, dict) and raw:
        return TrajectoryRequirement.from_dict(_requirement_payload(raw, contract, "contract"))
    environment = contract.get("environment")
    if isinstance(environment, dict):
        raw_environment = environment.get("trajectory_requirement")
        if isinstance(raw_environment, dict):
            return TrajectoryRequirement.from_dict(
                _requirement_payload(raw_environment, contract, "environment")
            )
        tier = environment.get("minimum_trajectory_quality_tier")
        if isinstance(tier, str):
            return TrajectoryRequirement(
                id=_requirement_id(contract, "environment"),
                created_at=_contract_created_at(contract),
                minimum_quality_tier=tier,
            )
    return TrajectoryRequirement(
        id=_requirement_id(contract, "default"),
        created_at=_contract_created_at(contract),
    )


def trajectory_record(trajectory: object) -> TrajectoryRecord:
    """Convert a trajectory dataclass or mapping into a mutable record."""

    if hasattr(trajectory, "to_dict"):
        converted = to_jsonable(trajectory)
    else:
        converted = to_jsonable(trajectory)
    if not isinstance(converted, dict):
        raise ValidationError("trajectory must be a mapping or provide to_dict")
    return copy.deepcopy(converted)


def require_quality_tier(value: str) -> str:
    require_non_empty_string(value, "quality_tier")
    if value not in TRAJECTORY_QUALITY_ORDER:
        raise ValidationError(f"quality_tier must be one of {sorted(TRAJECTORY_QUALITY_ORDER)}")
    return value


def quality_rank(value: str) -> int:
    require_quality_tier(value)
    return TRAJECTORY_QUALITY_ORDER[value]


def _attempt_manifest_payload(
    record: TrajectoryRecord,
    attempt: dict[str, object],
) -> dict[str, object] | None:
    manifest = _mapping_or_none(record.get("attempt_manifest"))
    if manifest is not None:
        return manifest
    metadata = _mapping(attempt.get("metadata"))
    direct = _mapping_or_none(metadata.get("attempt_manifest"))
    if direct is not None:
        return direct
    evidence = _mapping_or_none(metadata.get("faber_attempt_manifest"))
    if evidence and evidence.get("status") == "valid":
        return _mapping_or_none(evidence.get("manifest"))
    return None


def _trace_manifest_payload(
    record: TrajectoryRecord,
    attempt: dict[str, object],
) -> dict[str, object] | None:
    trace_manifest = _mapping_or_none(record.get("trace_manifest"))
    if trace_manifest is not None:
        return trace_manifest
    metadata = _mapping(attempt.get("metadata"))
    return _mapping_or_none(metadata.get("trace_manifest"))


def _evidence_level(
    record: TrajectoryRecord,
    manifest: dict[str, object] | None,
    trace_manifest: dict[str, object] | None,
    episode_package: dict[str, object] | None,
) -> int:
    if episode_package is not None:
        return 4
    for payload in [trace_manifest, manifest, _mapping_or_none(record.get("evidence_level"))]:
        value = _evidence_level_value(payload)
        if value is not None:
            return value
    return 0


def _quality_tier(
    manifest: dict[str, object] | None,
    trace_manifest: dict[str, object] | None,
    episode_package: dict[str, object] | None,
) -> str:
    if episode_package is not None:
        return "episode"
    if trace_manifest is not None:
        return "trace"
    if manifest is not None:
        return "manifest"
    return "pr_only"


def _training_eligibility(
    record: TrajectoryRecord,
    manifest: dict[str, object] | None,
) -> TrainingEligibility:
    consent = _mapping_or_none(record.get("training_consent"))
    if consent is None and manifest is not None:
        consent = _mapping_or_none(manifest.get("training_consent"))
    if consent is None:
        return TrainingEligibility(
            eligible=False,
            allowed_uses=[],
            reason="missing training consent",
        )
    allowed_uses = _string_values(consent.get("allowed_uses"))
    allowed = consent.get("training_use_allowed") is True
    reason = "training use allowed" if allowed else "training use not allowed"
    return TrainingEligibility(
        eligible=allowed,
        allowed_uses=allowed_uses,
        consent_id=_optional_string(consent.get("id")),
        reason=reason,
    )


def _process_evidence(
    evidence_level: int,
    trace_manifest: dict[str, object] | None,
    episode_package: dict[str, object] | None,
) -> ProcessEvidence:
    if episode_package is not None:
        trace_manifest = _mapping_or_none(episode_package.get("trace_manifest")) or trace_manifest
    event_count = _int_value(trace_manifest.get("trace_event_count")) if trace_manifest else 0
    included = _string_values(trace_manifest.get("included_event_types")) if trace_manifest else []
    has_actions = any(
        event_type.startswith("action.") or event_type.startswith("tool.")
        for event_type in included
    )
    has_observations = any(
        event_type.startswith(prefix)
        for event_type in included
        for prefix in OBSERVATION_EVENT_PREFIXES
    )
    has_verifier_events = any(
        "verifier" in event_type or "verification" in event_type for event_type in included
    )
    redacted = bool(trace_manifest.get("redaction_policy")) if trace_manifest else False
    trace_completeness = TraceCompleteness(
        event_count=event_count,
        included_event_types=included,
        has_actions=has_actions,
        has_observations=has_observations,
        has_verifier_events=has_verifier_events,
        redacted=redacted,
    )
    return ProcessEvidence(
        evidence_level=evidence_level,
        has_ordered_events=event_count > 0,
        trace_completeness=trace_completeness,
        trace_manifest_digest=_optional_string(trace_manifest.get("trace_jsonl_digest"))
        if trace_manifest
        else None,
        episode_package_digest=sha256_digest(episode_package) if episode_package else None,
        provenance=_mapping(trace_manifest.get("provenance")) if trace_manifest else {},
    )


def _reward_signal(record: TrajectoryRecord, receipt: dict[str, object]) -> RewardSignal:
    reward_metadata = _mapping(record.get("reward_metadata"))
    settlement = _mapping_or_none(record.get("settlement"))
    amount = _mapping(settlement.get("amount")) if settlement else {}
    cost_metadata = _mapping(record.get("cost_metadata"))
    latency_metadata = _mapping(record.get("latency_metadata"))
    reward_minor_units = _first_int(
        reward_metadata.get("reward_minor_units"),
        reward_metadata.get("score_minor_units"),
        amount.get("minor_units"),
    )
    cost_minor_units = _sum_minor_units(cost_metadata)
    latency_seconds = _first_int(
        latency_metadata.get("work_seconds"),
        latency_metadata.get("total_seconds"),
    )
    outcome = str(
        record.get("outcome") or ("accepted" if receipt.get("accepted") is True else "rejected")
    )
    present = reward_minor_units is not None
    return RewardSignal(
        present=present,
        outcome=outcome,
        reward_minor_units=reward_minor_units,
        cost_minor_units=cost_minor_units,
        latency_seconds=latency_seconds,
        currency=_optional_string(reward_metadata.get("currency") or amount.get("currency")),
    )


def _environment_replayability(
    contract: dict[str, object],
    manifest: dict[str, object] | None,
    episode_package: dict[str, object] | None,
) -> EnvironmentReplayability:
    environment = _mapping(contract.get("environment"))
    manifest_environment = _mapping(manifest.get("environment_metadata")) if manifest else {}
    if episode_package is not None:
        return EnvironmentReplayability(
            level="replayable_episode",
            has_environment_evidence=True,
            has_repository_snapshot=True,
            platform=_optional_string(
                manifest_environment.get("platform") or environment.get("platform")
            ),
        )
    level = _optional_string(
        manifest_environment.get("reproducibility_level")
        or environment.get("minimum_reproducibility_level")
        or environment.get("reproducibility_level")
    )
    if level is None:
        if manifest_environment.get("nix_flake_lock_digest") or manifest_environment.get(
            "dependency_lock_digest"
        ):
            level = "lockfile"
        elif manifest_environment:
            level = "declared"
        else:
            level = "opaque"
    has_snapshot = bool(
        manifest_environment.get("repository_snapshot_digest")
        or manifest_environment.get("base_revision")
        or environment.get("repository_snapshot")
        or contract.get("repository")
    )
    return EnvironmentReplayability(
        level=level,
        has_environment_evidence=bool(manifest_environment),
        has_repository_snapshot=has_snapshot,
        platform=_optional_string(
            manifest_environment.get("platform") or environment.get("platform")
        ),
    )


def _validation_issues(
    *,
    record: TrajectoryRecord,
    contract: dict[str, object],
    attempt: dict[str, object],
    receipt: dict[str, object],
    manifest: dict[str, object] | None,
    process_evidence: ProcessEvidence,
    reward_signal: RewardSignal,
    environment_replayability: EnvironmentReplayability,
    training_eligibility: TrainingEligibility,
    quality_tier: str,
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    if not contract:
        issues.append(_issue("blocker", "contract", "missing task contract"))
    if not attempt:
        issues.append(_issue("blocker", "attempt", "missing attempt"))
    if not receipt:
        issues.append(_issue("blocker", "receipt", "missing authoritative receipt"))
    if manifest is None and quality_tier != "pr_only":
        issues.append(_issue("blocker", "attempt_manifest", "missing attempt manifest"))
    if quality_tier == "pr_only":
        issues.append(_issue("info", "quality_tier", "PR-only trajectory is low evidence"))
    if manifest is not None and not _mapping(manifest.get("model_metadata")):
        issues.append(_issue("warning", "model_metadata", "missing solver model metadata"))
    if manifest is not None and not _mapping(manifest.get("harness_metadata")):
        issues.append(_issue("warning", "harness_metadata", "missing harness metadata"))
    if not process_evidence.satisfies_rl_process:
        issues.append(_issue("blocker", "process_evidence", "missing RL-grade process evidence"))
    if not reward_signal.present:
        issues.append(_issue("blocker", "reward_signal", "missing explicit reward signal"))
    if not environment_replayability.supports_rl_grade:
        issues.append(_issue("blocker", "environment", "missing replayability evidence"))
    if not training_eligibility.allows("rl"):
        issues.append(
            _issue(
                "blocker",
                "training_consent",
                "trajectory is not RL-training eligible",
            )
        )
    if not _mapping(record.get("cost_metadata")):
        issues.append(_issue("warning", "cost_metadata", "missing cost metadata"))
    if not _mapping(record.get("latency_metadata")):
        issues.append(_issue("warning", "latency_metadata", "missing latency metadata"))
    return issues


def _meets_requirement(
    *,
    quality_tier: str,
    is_rl_grade: bool,
    training_eligibility: TrainingEligibility,
    requirement: TrajectoryRequirement,
) -> bool:
    if quality_rank(quality_tier) < quality_rank(requirement.minimum_quality_tier):
        return False
    if requirement.require_rl_grade and not is_rl_grade:
        return False
    if requirement.require_training_eligible and not training_eligibility.eligible:
        return False
    return True


def _requirement_issues(
    *,
    quality_tier: str,
    is_rl_grade: bool,
    training_eligibility: TrainingEligibility,
    requirement: TrajectoryRequirement,
    full_payout_eligible: bool,
    bonus_eligible: bool,
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    if quality_rank(quality_tier) < quality_rank(requirement.minimum_quality_tier):
        issues.append(
            _issue(
                "blocker",
                "trajectory_requirement",
                "quality tier is below task minimum requirement",
            )
        )
    if requirement.require_rl_grade and not is_rl_grade:
        issues.append(
            _issue(
                "blocker",
                "trajectory_requirement",
                "task requires RL-grade trajectory evidence",
            )
        )
    if requirement.require_training_eligible and not training_eligibility.eligible:
        issues.append(
            _issue(
                "blocker",
                "trajectory_requirement",
                "task requires training-eligible consent",
            )
        )
    if not full_payout_eligible:
        issues.append(
            _issue(
                "warning",
                "full_payout_eligibility",
                "trajectory does not satisfy full payout quality policy",
            )
        )
    if requirement.bonus_minimum_tier is not None and not bonus_eligible:
        issues.append(
            _issue(
                "warning",
                "bonus_eligibility",
                "trajectory does not satisfy bonus quality policy",
            )
        )
    return issues


def _issue(severity: str, field: str, message: str) -> dict[str, object]:
    return {"severity": severity, "field": field, "message": message}


def _requirement_payload(
    raw: dict[str, object],
    contract: dict[str, object],
    source: str,
) -> dict[str, object]:
    payload = copy.deepcopy(raw)
    payload.setdefault("id", _requirement_id(contract, source))
    payload.setdefault("created_at", _contract_created_at(contract))
    return payload


def _requirement_id(contract: dict[str, object], source: str) -> str:
    contract_id = str(contract.get("id") or "contract_unknown")
    return f"trajectory-requirement_{contract_id}_{source}"


def _contract_created_at(contract: dict[str, object]) -> str:
    created_at = contract.get("created_at")
    if isinstance(created_at, str) and created_at:
        return created_at
    return _EPOCH


def _has_issue(issues: list[dict[str, object]], severity: str) -> bool:
    return any(issue.get("severity") == severity for issue in issues)


def _evidence_level_value(payload: dict[str, object] | None) -> int | None:
    if payload is None:
        return None
    value = payload.get("evidence_level")
    if isinstance(value, dict):
        value = value.get("level")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def _mapping_or_none(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _string_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _int_value(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _first_int(*values: object) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _sum_minor_units(metadata: dict[str, object]) -> int | None:
    values = [
        value
        for key, value in metadata.items()
        if key.endswith("_minor_units") and isinstance(value, int) and not isinstance(value, bool)
    ]
    if not values:
        return None
    return sum(values)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_or_default(payload: dict[str, object], field: str, default: str) -> str:
    value = payload.get(field, default)
    return require_non_empty_string(value, field)
