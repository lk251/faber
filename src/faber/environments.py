"""Cross-platform reproducibility evidence records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.traces import require_trust_level
from faber.validation import (
    ValidationError,
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
    require_string_list,
)
from faber.workers import PLATFORM_SUPPORT, require_platform

REPRODUCIBILITY_LEVELS = {
    "opaque": 0,
    "declared": 1,
    "lockfile": 2,
    "container": 3,
    "nix_flake": 4,
    "replayable": 5,
}


@dataclass(frozen=True)
class EnvironmentEvidence:
    """Observed or self-attested environment evidence for a specific attempt."""

    platform: str
    os_family: str
    os_version: str
    architecture: str
    reproducibility_level: str
    setup_entrypoint: list[str]
    verifier_command: list[str]
    package_manager: str | None = None
    lockfile_digests: dict[str, str] = field(default_factory=dict)
    runtime_versions: dict[str, str] = field(default_factory=dict)
    tool_path_metadata: dict[str, object] = field(default_factory=dict)
    nix_flake_lock_digest: str | None = None
    container_image_digest: str | None = None
    remote_runner_ref: str | None = None
    limitations: list[str] = field(default_factory=list)
    trust_level: str = "self_attested"
    id: str = field(default_factory=lambda: new_id("environment-evidence"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ENVIRONMENT_EVIDENCE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ENVIRONMENT_EVIDENCE)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_platform(self.platform, "platform")
        require_non_empty_string(self.os_family, "os_family")
        require_non_empty_string(self.os_version, "os_version")
        require_non_empty_string(self.architecture, "architecture")
        require_reproducibility_level(self.reproducibility_level)
        require_string_list(self.setup_entrypoint, "setup_entrypoint", allow_empty=False)
        require_string_list(self.verifier_command, "verifier_command", allow_empty=False)
        if self.package_manager is not None:
            require_non_empty_string(self.package_manager, "package_manager")
        _require_digest_mapping(self.lockfile_digests, "lockfile_digests")
        _require_string_mapping(self.runtime_versions, "runtime_versions")
        require_mapping(self.tool_path_metadata, "tool_path_metadata")
        require_optional_digest(self.nix_flake_lock_digest, "nix_flake_lock_digest")
        require_optional_digest(self.container_image_digest, "container_image_digest")
        if self.remote_runner_ref is not None:
            require_non_empty_string(self.remote_runner_ref, "remote_runner_ref")
        require_string_list(self.limitations, "limitations")
        require_trust_level(self.trust_level)
        if self.reproducibility_level == "nix_flake" and self.nix_flake_lock_digest is None:
            raise ValidationError("nix_flake reproducibility requires nix_flake_lock_digest")
        if self.reproducibility_level == "container" and self.container_image_digest is None:
            raise ValidationError("container reproducibility requires container_image_digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "platform": self.platform,
            "os_family": self.os_family,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "package_manager": self.package_manager,
            "lockfile_digests": self.lockfile_digests,
            "runtime_versions": self.runtime_versions,
            "setup_entrypoint": self.setup_entrypoint,
            "verifier_command": self.verifier_command,
            "tool_path_metadata": self.tool_path_metadata,
            "nix_flake_lock_digest": self.nix_flake_lock_digest,
            "container_image_digest": self.container_image_digest,
            "remote_runner_ref": self.remote_runner_ref,
            "reproducibility_level": self.reproducibility_level,
            "limitations": self.limitations,
            "trust_level": self.trust_level,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class EnvironmentFit:
    """Contract compatibility result for one environment evidence record."""

    task_contract_id: str
    environment_evidence_digest: str
    accepted: bool
    required_platforms: list[str]
    minimum_reproducibility_level: str | None
    platform_match: bool
    reproducibility_match: bool
    reasons: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("environment-fit"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ENVIRONMENT_FIT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ENVIRONMENT_FIT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_digest(self.environment_evidence_digest, "environment_evidence_digest")
        require_platform_list(self.required_platforms, "required_platforms")
        if self.minimum_reproducibility_level is not None:
            require_reproducibility_level(self.minimum_reproducibility_level)
        require_string_list(self.reasons, "reasons")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "environment_evidence_digest": self.environment_evidence_digest,
            "accepted": self.accepted,
            "required_platforms": self.required_platforms,
            "minimum_reproducibility_level": self.minimum_reproducibility_level,
            "platform_match": self.platform_match,
            "reproducibility_match": self.reproducibility_match,
            "reasons": self.reasons,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def environment_satisfies_contract(
    evidence: EnvironmentEvidence,
    contract: TaskContract,
) -> EnvironmentFit:
    required_platforms = required_platforms_from_contract(contract)
    minimum_level = minimum_reproducibility_level_from_contract(contract)
    platform_match = not required_platforms or any(
        _platform_requirement_satisfied(platform, evidence.platform)
        for platform in required_platforms
    )
    reproducibility_match = minimum_level is None or reproducibility_rank(
        evidence.reproducibility_level
    ) >= reproducibility_rank(minimum_level)
    reasons: list[str] = []
    if not platform_match:
        reasons.append("platform requirement not satisfied")
    if not reproducibility_match:
        reasons.append("minimum reproducibility level not satisfied")
    return EnvironmentFit(
        task_contract_id=contract.id,
        environment_evidence_digest=evidence.digest(),
        accepted=platform_match and reproducibility_match,
        required_platforms=required_platforms,
        minimum_reproducibility_level=minimum_level,
        platform_match=platform_match,
        reproducibility_match=reproducibility_match,
        reasons=reasons,
    )


def reproducibility_rank(level: str) -> int:
    require_reproducibility_level(level)
    return REPRODUCIBILITY_LEVELS[level]


def require_reproducibility_level(value: str, field: str = "reproducibility_level") -> str:
    require_non_empty_string(value, field)
    if value not in REPRODUCIBILITY_LEVELS:
        raise ValidationError(f"{field} must be one of {sorted(REPRODUCIBILITY_LEVELS)}")
    return value


def required_platforms_from_contract(contract: TaskContract) -> list[str]:
    platforms: set[str] = set()
    required = contract.environment.get("required_platforms")
    if isinstance(required, list):
        platforms.update(_normalize_platform(item) for item in required if isinstance(item, str))
    platform = contract.environment.get("platform")
    if isinstance(platform, str):
        platforms.add(_normalize_platform(platform))
    task_text = " ".join([contract.title, contract.description, *contract.requirements]).casefold()
    for known_platform in PLATFORM_SUPPORT:
        if known_platform in task_text:
            platforms.add(known_platform)
    require_platform_list(sorted(platforms), "required_platforms")
    return sorted(platforms)


def minimum_reproducibility_level_from_contract(contract: TaskContract) -> str | None:
    level = contract.environment.get("minimum_reproducibility_level")
    if level is None:
        return None
    if not isinstance(level, str):
        raise ValidationError("minimum_reproducibility_level must be a string")
    return require_reproducibility_level(level, "minimum_reproducibility_level")


def require_platform_list(value: object, field: str) -> list[str]:
    platforms = require_string_list(value, field)
    for index, platform in enumerate(platforms):
        require_platform(platform, f"{field}[{index}]")
    return platforms


def _platform_requirement_satisfied(required: str, observed: str) -> bool:
    required = _normalize_platform(required)
    observed = _normalize_platform(observed)
    if required == observed:
        return True
    return required == "linux" and observed == "nixos"


def _require_digest_mapping(value: dict[str, str], field: str) -> None:
    require_mapping(value, field)
    for key, digest in value.items():
        require_non_empty_string(key, f"{field} key")
        require_digest(digest, f"{field}.{key}")


def _require_string_mapping(value: dict[str, str], field: str) -> None:
    require_mapping(value, field)
    for key, item in value.items():
        require_non_empty_string(key, f"{field} key")
        require_non_empty_string(item, f"{field}.{key}")


def _normalize_platform(value: str) -> str:
    normalized = value.strip().casefold().replace("_", "-")
    aliases = {
        "darwin": "macos",
        "mac-os": "macos",
        "mac": "macos",
        "nix": "nixos",
        "remote": "remote-runner",
    }
    return aliases.get(normalized, normalized)
