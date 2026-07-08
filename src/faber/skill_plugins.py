"""Skill and plugin safety manifest records."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_sequence,
    require_string_list,
)
from faber.verifiers import VerifierRun
from faber.workers import require_platform_list

COMPONENT_TYPES = {"skill", "plugin"}
PERMISSION_RISK_LEVELS = {"low", "medium", "high"}
ISSUE_SEVERITIES = {"warning", "error"}


@dataclass(frozen=True)
class PermissionDeclaration:
    """A declared permission a skill or plugin expects to use."""

    name: str
    scope: str
    justification: str
    required: bool = True
    risk_level: str = "low"
    id: str = field(default_factory=lambda: new_id("permission-declaration"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.PERMISSION_DECLARATION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.PERMISSION_DECLARATION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.scope, "scope")
        require_non_empty_string(self.justification, "justification")
        if not isinstance(self.required, bool):
            raise ValidationError("required must be a boolean")
        if self.risk_level not in PERMISSION_RISK_LEVELS:
            raise ValidationError(f"risk_level must be one of {sorted(PERMISSION_RISK_LEVELS)}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "name": self.name,
            "scope": self.scope,
            "justification": self.justification,
            "required": self.required,
            "risk_level": self.risk_level,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> PermissionDeclaration:
        required = payload.get("required", True)
        if not isinstance(required, bool):
            raise ValidationError("required must be a boolean")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            name=_required_string(payload, "name"),
            scope=_required_string(payload, "scope"),
            justification=_required_string(payload, "justification"),
            required=required,
            risk_level=_required_string(payload, "risk_level"),
            schema=_schema_or_default(payload, "schema", schemas.PERMISSION_DECLARATION),
        )


@dataclass(frozen=True)
class DependencyDeclaration:
    """A declared dependency a skill or plugin expects to load."""

    name: str
    source: str
    version_constraint: str = "unspecified"
    optional: bool = False
    digest: str | None = None
    id: str = field(default_factory=lambda: new_id("dependency-declaration"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.DEPENDENCY_DECLARATION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.DEPENDENCY_DECLARATION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.source, "source")
        require_non_empty_string(self.version_constraint, "version_constraint")
        if not isinstance(self.optional, bool):
            raise ValidationError("optional must be a boolean")
        if self.digest is not None:
            require_non_empty_string(self.digest, "digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "name": self.name,
            "source": self.source,
            "version_constraint": self.version_constraint,
            "optional": self.optional,
            "digest": self.digest,
        }

    def digest_record(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> DependencyDeclaration:
        optional = payload.get("optional", False)
        if not isinstance(optional, bool):
            raise ValidationError("optional must be a boolean")
        digest = payload.get("digest")
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            name=_required_string(payload, "name"),
            source=_required_string(payload, "source"),
            version_constraint=_required_string(payload, "version_constraint"),
            optional=optional,
            digest=_optional_string(digest),
            schema=_schema_or_default(payload, "schema", schemas.DEPENDENCY_DECLARATION),
        )


@dataclass(frozen=True)
class SkillPluginManifest:
    """Declared metadata for a skill or plugin package."""

    component_type: str
    name: str
    version: str
    description: str
    supported_platforms: list[str]
    permissions: list[PermissionDeclaration]
    dependencies: list[DependencyDeclaration]
    verifier_ids: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("skill-plugin-manifest"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.SKILL_PLUGIN_MANIFEST

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.SKILL_PLUGIN_MANIFEST)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        if self.component_type not in COMPONENT_TYPES:
            raise ValidationError(f"component_type must be one of {sorted(COMPONENT_TYPES)}")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.version, "version")
        require_non_empty_string(self.description, "description")
        require_platform_list(self.supported_platforms, "supported_platforms")
        for index, permission in enumerate(self.permissions):
            if not isinstance(permission, PermissionDeclaration):
                raise ValidationError(f"permissions[{index}] must be a PermissionDeclaration")
        for index, dependency in enumerate(self.dependencies):
            if not isinstance(dependency, DependencyDeclaration):
                raise ValidationError(f"dependencies[{index}] must be a DependencyDeclaration")
        require_string_list(self.verifier_ids, "verifier_ids")
        require_mapping(self.metadata, "metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "component_type": self.component_type,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "supported_platforms": self.supported_platforms,
            "permissions": [permission.to_dict() for permission in self.permissions],
            "dependencies": [dependency.to_dict() for dependency in self.dependencies],
            "verifier_ids": self.verifier_ids,
            "metadata": self.metadata,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SkillPluginManifest:
        permissions_payload = require_sequence(payload.get("permissions", []), "permissions")
        dependencies_payload = require_sequence(payload.get("dependencies", []), "dependencies")
        permissions = [
            PermissionDeclaration.from_dict(dict(require_mapping(item, f"permissions[{index}]")))
            for index, item in enumerate(permissions_payload)
        ]
        dependencies = [
            DependencyDeclaration.from_dict(dict(require_mapping(item, f"dependencies[{index}]")))
            for index, item in enumerate(dependencies_payload)
        ]
        return cls(
            id=_required_string(payload, "id"),
            created_at=_required_string(payload, "created_at"),
            component_type=_required_string(payload, "component_type"),
            name=_required_string(payload, "name"),
            version=_required_string(payload, "version"),
            description=_required_string(payload, "description"),
            supported_platforms=require_string_list(
                payload.get("supported_platforms", []),
                "supported_platforms",
            ),
            permissions=permissions,
            dependencies=dependencies,
            verifier_ids=require_string_list(payload.get("verifier_ids", []), "verifier_ids"),
            metadata=dict(require_mapping(payload.get("metadata", {}), "metadata")),
            schema=_schema_or_default(payload, "schema", schemas.SKILL_PLUGIN_MANIFEST),
        )


@dataclass(frozen=True)
class SkillPluginScanIssue:
    """A scanner finding for a skill/plugin manifest."""

    severity: str
    field: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in ISSUE_SEVERITIES:
            raise ValidationError(f"severity must be one of {sorted(ISSUE_SEVERITIES)}")
        require_non_empty_string(self.field, "field")
        require_non_empty_string(self.message, "message")

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True)
class SkillPluginScanResult:
    """Result of checking declared skill/plugin metadata."""

    manifest_id: str
    manifest_digest: str
    issues: list[SkillPluginScanIssue]
    scanner_id: str = "faber.skill-plugin-manifest-scanner"
    scanner_version: str = "1"
    id: str = field(default_factory=lambda: new_id("skill-plugin-scan"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.SKILL_PLUGIN_SCAN_RESULT

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.SKILL_PLUGIN_SCAN_RESULT)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.manifest_id, "manifest_id")
        require_non_empty_string(self.manifest_digest, "manifest_digest")
        for index, issue in enumerate(self.issues):
            if not isinstance(issue, SkillPluginScanIssue):
                raise ValidationError(f"issues[{index}] must be a SkillPluginScanIssue")
        require_non_empty_string(self.scanner_id, "scanner_id")
        require_non_empty_string(self.scanner_version, "scanner_version")

    @property
    def passed(self) -> bool:
        return all(issue.severity != "error" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "manifest_id": self.manifest_id,
            "manifest_digest": self.manifest_digest,
            "passed": self.passed,
            "issues": [issue.to_dict() for issue in self.issues],
            "scanner_id": self.scanner_id,
            "scanner_version": self.scanner_version,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    def to_verifier_run(self, *, verifier_id: str | None = None) -> VerifierRun:
        """Represent the scan as a verifier run for receipt binding."""

        issue_counts: dict[str, object] = {
            "errors": sum(issue.severity == "error" for issue in self.issues),
            "warnings": sum(issue.severity == "warning" for issue in self.issues),
        }
        return VerifierRun(
            id=f"verifier-run_{self.id}",
            created_at=self.created_at,
            verifier_id=verifier_id or self.scanner_id,
            name="Skill/plugin manifest scanner",
            version=self.scanner_version,
            command=["faber", "scan-skill-plugin-manifest", self.manifest_id],
            passed=self.passed,
            metrics=issue_counts,
            failure_reasons=[
                issue.message for issue in self.issues if issue.severity == "error"
            ],
            logs_digest=self.digest(),
            metadata={
                "manifest_id": self.manifest_id,
                "manifest_digest": self.manifest_digest,
                "scan_result_digest": self.digest(),
            },
        )


def load_skill_plugin_manifest(path: str | Path) -> SkillPluginManifest:
    """Load and validate a skill/plugin manifest fixture."""

    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValidationError("skill/plugin manifest must be a JSON object")
    return SkillPluginManifest.from_dict(parsed)


def scan_skill_plugin_manifest(
    manifest: SkillPluginManifest,
    *,
    scan_id: str | None = None,
    created_at: str | None = None,
) -> SkillPluginScanResult:
    """Check explicit platform, permission, and dependency declarations."""

    issues: list[SkillPluginScanIssue] = []
    if not manifest.supported_platforms:
        issues.append(
            SkillPluginScanIssue(
                severity="error",
                field="supported_platforms",
                message="missing platform declaration",
            )
        )
    expected_dependencies = _expected_dependency_names(manifest)
    declared_dependencies = {dependency.name for dependency in manifest.dependencies}
    for dependency_name in expected_dependencies:
        if dependency_name not in declared_dependencies:
            issues.append(
                SkillPluginScanIssue(
                    severity="error",
                    field="dependencies",
                    message=f"missing dependency declaration: {dependency_name}",
                )
            )
    if not manifest.permissions:
        issues.append(
            SkillPluginScanIssue(
                severity="warning",
                field="permissions",
                message="no permissions declared",
            )
        )
    if not manifest.verifier_ids:
        issues.append(
            SkillPluginScanIssue(
                severity="warning",
                field="verifier_ids",
                message="no verifier checks declared",
            )
        )
    return SkillPluginScanResult(
        id=scan_id if scan_id is not None else new_id("skill-plugin-scan"),
        created_at=created_at if created_at is not None else utc_now(),
        manifest_id=manifest.id,
        manifest_digest=manifest.digest(),
        issues=issues,
    )


def _expected_dependency_names(manifest: SkillPluginManifest) -> list[str]:
    expected = manifest.metadata.get("expected_dependencies", [])
    if not isinstance(expected, list):
        raise ValidationError("metadata.expected_dependencies must be a list when present")
    names: list[str] = []
    for index, item in enumerate(expected):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"metadata.expected_dependencies[{index}] must be a non-empty string"
            )
        names.append(item)
    return names


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _required_string(payload: dict[str, object], field: str) -> str:
    return require_non_empty_string(payload.get(field), field)


def _schema_or_default(payload: dict[str, object], field: str, default: str) -> str:
    return require_non_empty_string(payload.get(field, default), field)
