"""Lightweight protocol schema registry and compatibility policy."""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ProtocolVersionError, ValidationError
from faber.validation import require_non_empty_string

SCHEMA_PATTERN = re.compile(r"^faber\.(?P<family>[a-z0-9_]+)\.v(?P<version>[1-9][0-9]*)$")


class CompatibilityPolicy(StrEnum):
    STRICT = "strict"
    WARN = "warn"


@dataclass(frozen=True)
class SchemaDescriptor:
    schema_id: str
    family: str
    version: int
    deprecated: bool = False
    deprecation_message: str = ""

    def __post_init__(self) -> None:
        parsed_family, parsed_version = parse_schema_id(self.schema_id)
        if self.family != parsed_family or self.version != parsed_version:
            raise ValidationError("schema descriptor family/version does not match schema_id")
        if not isinstance(self.deprecated, bool):
            raise ValidationError("deprecated must be a boolean")
        if not isinstance(self.deprecation_message, str):
            raise ValidationError("deprecation_message must be a string")
        if self.deprecated and not self.deprecation_message:
            raise ValidationError("deprecated schema requires a deprecation_message")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "family": self.family,
            "version": self.version,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
        }


@dataclass(frozen=True)
class SchemaCompatibilityReport:
    schema_id: str
    family: str
    version: int
    known: bool
    compatible: bool
    action: str
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "family": self.family,
            "version": self.version,
            "known": self.known,
            "compatible": self.compatible,
            "action": self.action,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class UpgradeResult:
    source_schema: str
    target_schema: str
    source_digest: str
    target_digest: str
    upgraded: bool
    record: dict[str, object]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_schema": self.source_schema,
            "target_schema": self.target_schema,
            "source_digest": self.source_digest,
            "target_digest": self.target_digest,
            "upgraded": self.upgraded,
            "record": self.record,
            "warnings": self.warnings,
        }


class SchemaRegistry:
    """Known schema IDs with explicit unknown-version policy."""

    def __init__(self, descriptors: Iterable[SchemaDescriptor]) -> None:
        self._descriptors: dict[str, SchemaDescriptor] = {}
        self._current_by_family: dict[str, SchemaDescriptor] = {}
        for descriptor in descriptors:
            if descriptor.schema_id in self._descriptors:
                raise ValidationError(f"duplicate schema id: {descriptor.schema_id}")
            self._descriptors[descriptor.schema_id] = descriptor
            current = self._current_by_family.get(descriptor.family)
            if current is None or descriptor.version > current.version:
                self._current_by_family[descriptor.family] = descriptor
        if not self._descriptors:
            raise ValidationError("schema registry requires at least one descriptor")

    def descriptors(self) -> list[SchemaDescriptor]:
        return [self._descriptors[key] for key in sorted(self._descriptors)]

    def current_schema(self, family: str) -> str:
        require_non_empty_string(family, "family")
        try:
            return self._current_by_family[family].schema_id
        except KeyError as exc:
            raise ProtocolVersionError(f"unknown schema family: {family}") from exc

    def validate(
        self,
        schema_id: str,
        *,
        policy: CompatibilityPolicy = CompatibilityPolicy.STRICT,
    ) -> SchemaCompatibilityReport:
        family, version = parse_schema_id(schema_id)
        descriptor = self._descriptors.get(schema_id)
        if descriptor is not None:
            warnings = (
                [descriptor.deprecation_message] if descriptor.deprecated else []
            )
            return SchemaCompatibilityReport(
                schema_id=schema_id,
                family=family,
                version=version,
                known=True,
                compatible=True,
                action=(
                    "read-with-deprecation-warning"
                    if descriptor.deprecated
                    else "read-current"
                ),
                warnings=warnings,
            )
        current = self._current_by_family.get(family)
        if current is not None and version > current.version:
            message = (
                f"future schema version is unsupported: {schema_id}; "
                f"current is {current.schema_id}"
            )
        elif current is not None:
            message = (
                f"unregistered historical schema version is unsupported: {schema_id}; "
                "an explicit upgrader is required"
            )
        else:
            message = f"unknown required schema family: {schema_id}"
        if policy == CompatibilityPolicy.STRICT:
            raise ProtocolVersionError(message)
        return SchemaCompatibilityReport(
            schema_id=schema_id,
            family=family,
            version=version,
            known=False,
            compatible=False,
            action="preserve-opaque",
            warnings=[message],
        )


def protocol_schema_registry() -> SchemaRegistry:
    """Build the registry from centralized schema constants."""

    schema_ids = {
        value
        for name, value in vars(schemas).items()
        if name.isupper() and isinstance(value, str) and SCHEMA_PATTERN.fullmatch(value)
    }
    return SchemaRegistry(
        SchemaDescriptor(
            schema_id=schema_id,
            family=parse_schema_id(schema_id)[0],
            version=parse_schema_id(schema_id)[1],
        )
        for schema_id in sorted(schema_ids)
    )


def upgrade_record(
    record: Mapping[str, object],
    *,
    target_schema: str | None = None,
    registry: SchemaRegistry | None = None,
    policy: CompatibilityPolicy = CompatibilityPolicy.STRICT,
) -> UpgradeResult:
    """No-op current-version upgrade stub; future migrations must be explicit."""

    source_schema = record.get("schema")
    if not isinstance(source_schema, str):
        raise ProtocolVersionError("record schema must be a non-empty string")
    active_registry = registry or protocol_schema_registry()
    compatibility = active_registry.validate(source_schema, policy=policy)
    if not compatibility.compatible:
        preserved = copy.deepcopy(dict(record))
        digest = sha256_digest(preserved)
        return UpgradeResult(
            source_schema=source_schema,
            target_schema=source_schema,
            source_digest=digest,
            target_digest=digest,
            upgraded=False,
            record=preserved,
            warnings=compatibility.warnings,
        )
    destination = target_schema or active_registry.current_schema(compatibility.family)
    if destination != source_schema:
        raise ProtocolVersionError(
            f"no explicit upgrade path from {source_schema} to {destination}"
        )
    preserved = copy.deepcopy(dict(record))
    digest = sha256_digest(preserved)
    return UpgradeResult(
        source_schema=source_schema,
        target_schema=destination,
        source_digest=digest,
        target_digest=digest,
        upgraded=False,
        record=preserved,
        warnings=compatibility.warnings,
    )


def schema_versions_in_records(records: Iterable[Mapping[str, object]]) -> list[str]:
    """Collect every nested Faber schema ID represented in exported records."""

    found: set[str] = set()
    for record in records:
        _collect_schema_ids(record, found)
    return sorted(found)


def parse_schema_id(schema_id: str) -> tuple[str, int]:
    require_non_empty_string(schema_id, "schema_id")
    match = SCHEMA_PATTERN.fullmatch(schema_id)
    if match is None:
        raise ProtocolVersionError(
            "schema_id must match faber.<family>.v<positive-integer>"
        )
    return match.group("family"), int(match.group("version"))


def _collect_schema_ids(value: object, found: set[str]) -> None:
    if isinstance(value, Mapping):
        schema_id = value.get("schema")
        if isinstance(schema_id, str) and SCHEMA_PATTERN.fullmatch(schema_id):
            found.add(schema_id)
        for nested in value.values():
            _collect_schema_ids(nested, found)
    elif isinstance(value, list):
        for nested in value:
            _collect_schema_ids(nested, found)
