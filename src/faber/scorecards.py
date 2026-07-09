"""Observed worker reputation and value-per-euro scorecards."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isqrt

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.trajectory_quality import TRAJECTORY_QUALITY_ORDER
from faber.validation import require_non_empty_string, require_schema


@dataclass(frozen=True)
class TaskFamilyScorecard:
    task_family: str
    sample_size: int
    accepted_attempts: int
    rejected_attempts: int
    abandoned_attempts: int
    verifier_failures: int
    success_rate_milli: int
    total_cost_minor_units: int
    total_reward_minor_units: int
    value_per_euro_milli: int
    average_latency_seconds: int
    average_review_friction_milli: int
    average_trace_quality_milli: int
    uncertainty_milli: int

    def to_dict(self) -> dict[str, object]:
        return {
            "task_family": self.task_family,
            "sample_size": self.sample_size,
            "accepted_attempts": self.accepted_attempts,
            "rejected_attempts": self.rejected_attempts,
            "abandoned_attempts": self.abandoned_attempts,
            "verifier_failures": self.verifier_failures,
            "success_rate_milli": self.success_rate_milli,
            "total_cost_minor_units": self.total_cost_minor_units,
            "total_reward_minor_units": self.total_reward_minor_units,
            "value_per_euro_milli": self.value_per_euro_milli,
            "average_latency_seconds": self.average_latency_seconds,
            "average_review_friction_milli": self.average_review_friction_milli,
            "average_trace_quality_milli": self.average_trace_quality_milli,
            "uncertainty_milli": self.uncertainty_milli,
        }


@dataclass(frozen=True)
class WorkerScorecard:
    worker_id: str
    task_families: dict[str, TaskFamilyScorecard]
    sample_size: int
    success_rate_milli: int
    average_trace_quality_milli: int
    value_per_euro_milli: int
    uncertainty_milli: int
    observed_platforms: list[str]
    observed_trust_levels: list[str]
    self_attested_metadata: dict[str, object]
    private_trajectory_count: int
    id: str = field(default_factory=lambda: new_id("worker-scorecard"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.WORKER_SCORECARD

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.WORKER_SCORECARD)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.worker_id, "worker_id")

    def to_dict(self, *, public: bool = False) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "worker_id": self.worker_id,
            "task_families": {
                name: scorecard.to_dict()
                for name, scorecard in sorted(self.task_families.items())
            },
            "sample_size": self.sample_size,
            "success_rate_milli": self.success_rate_milli,
            "average_trace_quality_milli": self.average_trace_quality_milli,
            "value_per_euro_milli": self.value_per_euro_milli,
            "uncertainty_milli": self.uncertainty_milli,
            "observed_platforms": self.observed_platforms,
            "observed_trust_levels": self.observed_trust_levels,
            "self_attested_metadata": {} if public else self.self_attested_metadata,
            "private_trajectory_count": self.private_trajectory_count,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class _Observation:
    task_family: str
    outcome: str
    cost_minor_units: int
    reward_minor_units: int
    latency_seconds: int
    review_friction_milli: int
    trace_quality_milli: int
    platform: str | None
    trust_level: str | None
    private: bool


class WorkerScorecardBuilder:
    def __init__(
        self,
        worker_id: str,
        *,
        scorecard_id: str | None = None,
        created_at: str = "1970-01-01T00:00:00Z",
    ) -> None:
        self.worker_id = require_non_empty_string(worker_id, "worker_id")
        self.scorecard_id = scorecard_id or f"worker-scorecard_{worker_id}"
        self.created_at = created_at
        self._observations: list[_Observation] = []
        self._self_attested_metadata: dict[str, object] = {}

    def update(self, trajectory: dict[str, object]) -> WorkerScorecardBuilder:
        attempt = _mapping(trajectory.get("attempt"))
        if attempt.get("worker_id") != self.worker_id:
            raise ValidationError("trajectory worker_id does not match scorecard worker")
        contract = _mapping(trajectory.get("contract"))
        environment = _mapping(contract.get("environment"))
        task_family = str(
            environment.get("task_type")
            or contract.get("task_source")
            or "unknown"
        )
        outcome = str(trajectory.get("outcome") or "unknown")
        manifest = _mapping(trajectory.get("attempt_manifest"))
        manifest_environment = _mapping(manifest.get("environment_metadata"))
        quality_tier = _quality_tier(trajectory)
        worker_profile = _mapping(trajectory.get("worker_profile"))
        if worker_profile:
            self._self_attested_metadata = {
                "display_name": worker_profile.get("display_name"),
                "operator_id": worker_profile.get("operator_id"),
                "capabilities": worker_profile.get("capabilities"),
                "metadata_trust_level": worker_profile.get("metadata_trust_level"),
            }
        self._observations.append(
            _Observation(
                task_family=task_family,
                outcome=outcome,
                cost_minor_units=_sum_minor_units(
                    _mapping(trajectory.get("cost_metadata"))
                ),
                reward_minor_units=_reward_minor_units(trajectory),
                latency_seconds=_latency_seconds(trajectory),
                review_friction_milli=_review_friction_milli(trajectory),
                trace_quality_milli=_quality_milli(quality_tier),
                platform=_optional_string(
                    manifest_environment.get("platform") or environment.get("platform")
                ),
                trust_level=_optional_string(manifest.get("trust_level")),
                private=trajectory.get("private") is True,
            )
        )
        return self

    def build(self) -> WorkerScorecard:
        grouped: dict[str, list[_Observation]] = {}
        for observation in self._observations:
            grouped.setdefault(observation.task_family, []).append(observation)
        task_families = {
            task_family: _family_scorecard(task_family, observations)
            for task_family, observations in grouped.items()
        }
        total = len(self._observations)
        accepted = sum(item.outcome == "accepted" for item in self._observations)
        total_cost = sum(item.cost_minor_units for item in self._observations)
        total_reward = sum(item.reward_minor_units for item in self._observations)
        return WorkerScorecard(
            id=self.scorecard_id,
            created_at=self.created_at,
            worker_id=self.worker_id,
            task_families=task_families,
            sample_size=total,
            success_rate_milli=_ratio_milli(accepted, total),
            average_trace_quality_milli=_average(
                [item.trace_quality_milli for item in self._observations]
            ),
            value_per_euro_milli=(
                total_reward * 1000 // max(total_cost, 1) if total else 0
            ),
            uncertainty_milli=_uncertainty(total),
            observed_platforms=sorted(
                {item.platform for item in self._observations if item.platform}
            ),
            observed_trust_levels=sorted(
                {item.trust_level for item in self._observations if item.trust_level}
            ),
            self_attested_metadata=self._self_attested_metadata,
            private_trajectory_count=sum(item.private for item in self._observations),
        )


def _family_scorecard(
    task_family: str,
    observations: list[_Observation],
) -> TaskFamilyScorecard:
    sample_size = len(observations)
    accepted = sum(item.outcome == "accepted" for item in observations)
    rejected = sum(item.outcome == "rejected" for item in observations)
    abandoned = sum(item.outcome in {"abandoned", "declined", "timeout"} for item in observations)
    verifier_failures = sum(item.outcome == "verifier_failure" for item in observations)
    total_cost = sum(item.cost_minor_units for item in observations)
    total_reward = sum(item.reward_minor_units for item in observations)
    return TaskFamilyScorecard(
        task_family=task_family,
        sample_size=sample_size,
        accepted_attempts=accepted,
        rejected_attempts=rejected,
        abandoned_attempts=abandoned,
        verifier_failures=verifier_failures,
        success_rate_milli=_ratio_milli(accepted, sample_size),
        total_cost_minor_units=total_cost,
        total_reward_minor_units=total_reward,
        value_per_euro_milli=total_reward * 1000 // max(total_cost, 1),
        average_latency_seconds=_average([item.latency_seconds for item in observations]),
        average_review_friction_milli=_average(
            [item.review_friction_milli for item in observations]
        ),
        average_trace_quality_milli=_average(
            [item.trace_quality_milli for item in observations]
        ),
        uncertainty_milli=_uncertainty(sample_size),
    )


def _quality_tier(record: dict[str, object]) -> str:
    quality = _mapping(record.get("trajectory_quality"))
    tier = quality.get("quality_tier")
    if isinstance(tier, dict):
        tier = tier.get("name")
    if isinstance(tier, str) and tier in TRAJECTORY_QUALITY_ORDER:
        return tier
    if record.get("episode_package"):
        return "episode"
    if record.get("trace_manifest"):
        return "trace"
    if record.get("attempt_manifest"):
        return "manifest"
    return "pr_only"


def _quality_milli(tier: str) -> int:
    return {"pr_only": 0, "manifest": 333, "trace": 667, "episode": 1000}[tier]


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _sum_minor_units(metadata: dict[str, object]) -> int:
    return sum(
        value
        for key, value in metadata.items()
        if key.endswith("_minor_units")
        and isinstance(value, int)
        and not isinstance(value, bool)
    )


def _reward_minor_units(record: dict[str, object]) -> int:
    reward = _mapping(record.get("reward_metadata"))
    value = reward.get("reward_minor_units")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    settlement = _mapping(record.get("settlement"))
    amount = _mapping(settlement.get("amount"))
    value = amount.get("minor_units")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _latency_seconds(record: dict[str, object]) -> int:
    latency = _mapping(record.get("latency_metadata"))
    for field_name in ["total_seconds", "work_seconds"]:
        value = latency.get(field_name)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return 0


def _review_friction_milli(record: dict[str, object]) -> int:
    review = _mapping(record.get("review_metadata"))
    friction = _mapping(review.get("friction"))
    requested = friction.get("requested_changes", 0)
    rounds = friction.get("rounds", 0)
    if not isinstance(requested, int) or isinstance(requested, bool):
        requested = 0
    if not isinstance(rounds, int) or isinstance(rounds, bool):
        rounds = 0
    return min(1000, requested * 250 + max(0, rounds - 1) * 100)


def _ratio_milli(numerator: int, denominator: int) -> int:
    return numerator * 1000 // denominator if denominator else 0


def _average(values: list[int]) -> int:
    return sum(values) // len(values) if values else 0


def _uncertainty(sample_size: int) -> int:
    return 1000 // max(1, isqrt(sample_size)) if sample_size else 1000


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
