"""Worker profile records."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.traces import require_trust_level
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
    require_string_list,
)

if TYPE_CHECKING:
    from faber.trajectories import Trajectory

DISCLOSURE_LEVELS = {"exact", "coarse", "private"}
PLATFORM_SUPPORT = {"nixos", "linux", "macos", "windows", "container", "remote-runner"}
TRUST_LEVEL_WEIGHTS = {
    "self_attested": 0,
    "runner_attested": 25,
    "platform_observed": 35,
    "repo_owner_verified": 45,
    "provider_attested": 40,
}


def require_disclosure_level(value: str, field: str = "disclosure_level") -> str:
    require_non_empty_string(value, field)
    if value not in DISCLOSURE_LEVELS:
        raise ValidationError(f"{field} must be one of {sorted(DISCLOSURE_LEVELS)}")
    return value


@dataclass(frozen=True)
class ModelManifest:
    """Solver model metadata at an exact, coarse, or private disclosure level."""

    display_name: str
    disclosure_level: str
    model_ref: str | None = None
    model_family: str = "undisclosed"
    provider_class: str = "undisclosed"
    context_window_class: str = "undisclosed"
    cost_model: Money | None = None
    trust_level: str = "self_attested"
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("model-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.MODEL_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.MODEL_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.display_name, "display_name")
        require_disclosure_level(self.disclosure_level)
        if self.model_ref is not None:
            require_non_empty_string(self.model_ref, "model_ref")
        if self.disclosure_level == "exact" and self.model_ref is None:
            raise ValidationError("exact model disclosure requires model_ref")
        require_non_empty_string(self.model_family, "model_family")
        require_non_empty_string(self.provider_class, "provider_class")
        require_non_empty_string(self.context_window_class, "context_window_class")
        require_trust_level(self.trust_level)
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "disclosure_level": self.disclosure_level,
            "model_ref": self.model_ref,
            "model_family": self.model_family,
            "provider_class": self.provider_class,
            "context_window_class": self.context_window_class,
            "cost_model": self.cost_model.to_dict() if self.cost_model else None,
            "trust_level": self.trust_level,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class HarnessManifest:
    """Harness and orchestration metadata used for routing and trace expectations."""

    display_name: str
    harness_family: str
    disclosure_level: str
    version: str | None = None
    supported_platforms: list[str] = field(default_factory=list)
    supported_task_sources: list[str] = field(default_factory=list)
    supported_languages: list[str] = field(default_factory=list)
    trace_adapter_version: str | None = None
    trust_level: str = "self_attested"
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("harness-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.HARNESS_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.HARNESS_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.display_name, "display_name")
        require_non_empty_string(self.harness_family, "harness_family")
        require_disclosure_level(self.disclosure_level)
        if self.version is not None:
            require_non_empty_string(self.version, "version")
        require_platform_list(self.supported_platforms, "supported_platforms")
        require_string_list(self.supported_task_sources, "supported_task_sources")
        require_string_list(self.supported_languages, "supported_languages")
        if self.trace_adapter_version is not None:
            require_non_empty_string(self.trace_adapter_version, "trace_adapter_version")
        require_trust_level(self.trust_level)
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "harness_family": self.harness_family,
            "disclosure_level": self.disclosure_level,
            "version": self.version,
            "supported_platforms": self.supported_platforms,
            "supported_task_sources": self.supported_task_sources,
            "supported_languages": self.supported_languages,
            "trace_adapter_version": self.trace_adapter_version,
            "trust_level": self.trust_level,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class EnvironmentManifest:
    """Execution-environment metadata without requiring proprietary internals."""

    platform: str
    architecture: str
    reproducibility_level: str
    package_manager: str | None = None
    dependency_lock_digest: str | None = None
    tool_registry_digest: str | None = None
    nix_flake_lock_digest: str | None = None
    trust_level: str = "self_attested"
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("environment-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ENVIRONMENT_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ENVIRONMENT_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_platform(self.platform, "platform")
        require_non_empty_string(self.architecture, "architecture")
        require_non_empty_string(self.reproducibility_level, "reproducibility_level")
        if self.package_manager is not None:
            require_non_empty_string(self.package_manager, "package_manager")
        for field_name, value in [
            ("dependency_lock_digest", self.dependency_lock_digest),
            ("tool_registry_digest", self.tool_registry_digest),
            ("nix_flake_lock_digest", self.nix_flake_lock_digest),
        ]:
            require_optional_digest(value, field_name)
        require_trust_level(self.trust_level)
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "platform": self.platform,
            "architecture": self.architecture,
            "package_manager": self.package_manager,
            "dependency_lock_digest": self.dependency_lock_digest,
            "tool_registry_digest": self.tool_registry_digest,
            "nix_flake_lock_digest": self.nix_flake_lock_digest,
            "reproducibility_level": self.reproducibility_level,
            "trust_level": self.trust_level,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class WorkerProfile:
    """Portable worker capability and reputation record."""

    display_name: str
    capabilities: list[str]
    owner_ref: str | None = None
    supported_task_sources: list[str] = field(default_factory=list)
    supported_languages: list[str] = field(default_factory=list)
    supported_platforms: list[str] = field(default_factory=list)
    cost_model: Money | None = None
    model_manifest: ModelManifest | None = None
    harness_manifest: HarnessManifest | None = None
    environment_manifest: EnvironmentManifest | None = None
    availability_status: str = "available"
    reputation: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("worker"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.WORKER_PROFILE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.WORKER_PROFILE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.display_name, "display_name")
        require_string_list(self.capabilities, "capabilities")
        if self.owner_ref is not None:
            require_non_empty_string(self.owner_ref, "owner_ref")
        require_string_list(self.supported_task_sources, "supported_task_sources")
        require_string_list(self.supported_languages, "supported_languages")
        require_platform_list(self.supported_platforms, "supported_platforms")
        if self.model_manifest is not None and not isinstance(self.model_manifest, ModelManifest):
            raise ValidationError("model_manifest must be a ModelManifest")
        if self.harness_manifest is not None and not isinstance(
            self.harness_manifest, HarnessManifest
        ):
            raise ValidationError("harness_manifest must be a HarnessManifest")
        if self.environment_manifest is not None and not isinstance(
            self.environment_manifest, EnvironmentManifest
        ):
            raise ValidationError("environment_manifest must be an EnvironmentManifest")
        require_non_empty_string(self.availability_status, "availability_status")
        require_mapping(self.reputation, "reputation")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "display_name": self.display_name,
            "capabilities": self.capabilities,
            "owner_ref": self.owner_ref,
            "supported_task_sources": self.supported_task_sources,
            "supported_languages": self.supported_languages,
            "supported_platforms": self.supported_platforms,
            "cost_model": self.cost_model.to_dict() if self.cost_model else None,
            "model_manifest": self.model_manifest.to_dict() if self.model_manifest else None,
            "harness_manifest": self.harness_manifest.to_dict()
            if self.harness_manifest
            else None,
            "environment_manifest": self.environment_manifest.to_dict()
            if self.environment_manifest
            else None,
            "availability_status": self.availability_status,
            "reputation": self.reputation,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


class WorkerRegistry:
    """In-memory registry of available workers."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerProfile] = {}

    def register(self, worker: WorkerProfile) -> WorkerProfile:
        existing = self._workers.get(worker.id)
        if existing is not None and existing.digest() != worker.digest():
            raise ValidationError(f"worker {worker.id!r} is already registered differently")
        self._workers[worker.id] = worker
        return worker

    def resolve(self, worker_id: str) -> WorkerProfile:
        require_non_empty_string(worker_id, "worker_id")
        try:
            return self._workers[worker_id]
        except KeyError as exc:
            raise ValidationError(f"worker {worker_id!r} is not registered") from exc

    def list_workers(self) -> list[WorkerProfile]:
        return [self._workers[key] for key in sorted(self._workers)]


def worker_supported_platforms(worker: WorkerProfile) -> list[str]:
    platforms = {_normalize_platform(platform) for platform in worker.supported_platforms}
    if worker.harness_manifest is not None:
        platforms.update(
            _normalize_platform(platform)
            for platform in worker.harness_manifest.supported_platforms
        )
    if worker.environment_manifest is not None:
        platforms.add(_normalize_platform(worker.environment_manifest.platform))
    return sorted(platforms)


def worker_metadata_trust_score(worker: WorkerProfile) -> int:
    trust_levels: list[str] = []
    for manifest in [
        worker.model_manifest,
        worker.harness_manifest,
        worker.environment_manifest,
    ]:
        if manifest is not None:
            trust_levels.append(manifest.trust_level)
    metadata_trust_level = worker.metadata.get("trust_level")
    if isinstance(metadata_trust_level, str):
        require_trust_level(metadata_trust_level)
        trust_levels.append(metadata_trust_level)
    if not trust_levels:
        return 0
    return max(TRUST_LEVEL_WEIGHTS[level] for level in trust_levels)


def update_reputation_from_trajectory(
    worker: WorkerProfile,
    trajectory: Trajectory,
) -> WorkerProfile:
    """Return a worker profile with reputation updated from a verified trajectory."""

    reputation = dict(worker.reputation)
    accepted = _int_value(reputation.get("accepted_attempts", 0))
    rejected = _int_value(reputation.get("rejected_attempts", 0))
    verifier_failures = _int_value(reputation.get("verifier_failures", 0))
    if trajectory.receipt.accepted:
        accepted += 1
    else:
        rejected += 1
        verifier_failures += 1
    reputation["accepted_attempts"] = accepted
    reputation["rejected_attempts"] = rejected
    reputation["verifier_failures"] = verifier_failures
    reputation["last_outcome"] = trajectory.outcome()
    reputation["total_latency_seconds"] = _int_value(
        reputation.get("total_latency_seconds", 0)
    ) + _int_value(trajectory.latency_metadata.get("work_seconds", 0))
    cost_units = _int_value(trajectory.cost_metadata.get("compute_minor_units", 0)) + _int_value(
        trajectory.cost_metadata.get("review_minor_units", 0)
    )
    reputation["total_cost_minor_units"] = (
        _int_value(reputation.get("total_cost_minor_units", 0)) + cost_units
    )
    if trajectory.review_metadata.get("review_friction") not in (None, "none", "low"):
        reputation["review_friction_count"] = (
            _int_value(reputation.get("review_friction_count", 0)) + 1
        )
    return replace(worker, reputation=reputation)


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def require_platform(value: str, field: str = "platform") -> str:
    normalized = _normalize_platform(value)
    if normalized not in PLATFORM_SUPPORT:
        raise ValidationError(f"{field} must be one of {sorted(PLATFORM_SUPPORT)}")
    return value


def require_platform_list(value: object, field: str) -> list[str]:
    platforms = require_string_list(value, field)
    for index, platform in enumerate(platforms):
        require_platform(platform, f"{field}[{index}]")
    return platforms


def _normalize_platform(value: str) -> str:
    normalized = value.strip().casefold().replace("_", "-")
    aliases = {
        "darwin": "macos",
        "mac-os": "macos",
        "mac": "macos",
        "nix": "nixos",
        "remote": "remote-runner",
        "remote-runner": "remote-runner",
        "remote-runner-support": "remote-runner",
    }
    return aliases.get(normalized, normalized)
