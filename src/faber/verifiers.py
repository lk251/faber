"""Verifier execution records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError, VerifierError
from faber.ids import new_id, utc_now
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
    require_optional_digest,
    require_schema,
    require_sequence,
    require_string_list,
)


@dataclass(frozen=True)
class VerifierSpec:
    """Approved verifier policy that can be run by Faber Runner."""

    verifier_id: str
    name: str
    version: str
    description: str
    command_template: list[str]
    working_directory_policy: str = "provided-cwd"
    allowed_timeout_seconds: int = 30
    expected_output_convention: str = "exit-code"
    id: str = field(default_factory=lambda: new_id("verifier-spec"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.VERIFIER_SPEC

    def __post_init__(self) -> None:
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.schema, "schema")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.version, "version")
        require_non_empty_string(self.description, "description")
        require_string_list(self.command_template, "command_template", allow_empty=False)
        require_non_empty_string(self.working_directory_policy, "working_directory_policy")
        require_non_empty_string(self.expected_output_convention, "expected_output_convention")
        if self.allowed_timeout_seconds <= 0:
            raise VerifierError("allowed_timeout_seconds must be positive")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "verifier_id": self.verifier_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "command_template": self.command_template,
            "working_directory_policy": self.working_directory_policy,
            "allowed_timeout_seconds": self.allowed_timeout_seconds,
            "expected_output_convention": self.expected_output_convention,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    def command(self) -> list[str]:
        return list(self.command_template)


class VerifierRegistry:
    """In-memory registry of approved verifier specs."""

    def __init__(self) -> None:
        self._specs: dict[str, VerifierSpec] = {}

    def register(self, spec: VerifierSpec) -> VerifierSpec:
        existing = self._specs.get(spec.verifier_id)
        if existing is not None and existing.digest() != spec.digest():
            raise VerifierError(f"verifier_id {spec.verifier_id!r} is already registered")
        self._specs[spec.verifier_id] = spec
        return spec

    def resolve(self, verifier_id: str) -> VerifierSpec:
        require_non_empty_string(verifier_id, "verifier_id")
        try:
            return self._specs[verifier_id]
        except KeyError as exc:
            raise VerifierError(f"verifier_id {verifier_id!r} is not registered") from exc

    def list_specs(self) -> list[VerifierSpec]:
        return [self._specs[key] for key in sorted(self._specs)]

    def snapshot(self) -> dict[str, object]:
        """Return the canonical owner-approved registry state used by a workflow."""

        return {
            "schema": "faber.verifier_registry_snapshot.v1",
            "specs": [spec.to_dict() for spec in self.list_specs()],
        }

    def digest(self) -> str:
        """Bind execution policy to the exact registered verifier specifications."""

        return sha256_digest(self.snapshot())


@dataclass(frozen=True)
class VerifierRun:
    """Evidence from an approved verifier run."""

    verifier_id: str
    name: str
    version: str
    command: list[str]
    passed: bool
    metrics: dict[str, object] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)
    logs_digest: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("verifier-run"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.VERIFIER_RUN

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.VERIFIER_RUN)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.version, "version")
        require_string_list(self.command, "command", allow_empty=False)
        require_mapping(self.metrics, "metrics")
        require_sequence(self.failure_reasons, "failure_reasons")
        require_optional_digest(self.logs_digest, "logs_digest")
        require_mapping(self.metadata, "metadata")

    def verifier_spec(self) -> dict[str, object]:
        return {
            "verifier_id": self.verifier_id,
            "name": self.name,
            "version": self.version,
            "command": self.command,
        }

    def verifier_digest(self) -> str:
        return sha256_digest(self.verifier_spec())

    def result_digest(self) -> str:
        return sha256_digest(
            {
                "passed": self.passed,
                "metrics": self.metrics,
                "failure_reasons": self.failure_reasons,
                "logs_digest": self.logs_digest,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "verifier_id": self.verifier_id,
            "name": self.name,
            "version": self.version,
            "command": self.command,
            "passed": self.passed,
            "metrics": self.metrics,
            "failure_reasons": self.failure_reasons,
            "logs_digest": self.logs_digest,
            "metadata": self.metadata,
            "verifier_digest": self.verifier_digest(),
            "result_digest": self.result_digest(),
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> VerifierRun:
        fields = {
            "schema",
            "id",
            "created_at",
            "verifier_id",
            "name",
            "version",
            "command",
            "passed",
            "metrics",
            "failure_reasons",
            "logs_digest",
            "metadata",
            "verifier_digest",
            "result_digest",
        }
        if set(payload) != fields:
            raise ValidationError("VerifierRun must use the exact supported field set")
        passed = payload.get("passed")
        if not isinstance(passed, bool):
            raise ValidationError("passed must be a boolean")
        run = cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            id=require_non_empty_string(payload.get("id"), "id"),
            created_at=require_non_empty_string(payload.get("created_at"), "created_at"),
            verifier_id=require_non_empty_string(payload.get("verifier_id"), "verifier_id"),
            name=require_non_empty_string(payload.get("name"), "name"),
            version=require_non_empty_string(payload.get("version"), "version"),
            command=list(require_string_list(payload.get("command"), "command", allow_empty=False)),
            passed=passed,
            metrics=dict(require_mapping(payload.get("metrics"), "metrics")),
            failure_reasons=list(
                require_string_list(payload.get("failure_reasons"), "failure_reasons")
            ),
            logs_digest=require_optional_digest(payload.get("logs_digest"), "logs_digest"),
            metadata=dict(require_mapping(payload.get("metadata"), "metadata")),
        )
        if (
            require_digest(payload.get("verifier_digest"), "verifier_digest")
            != run.verifier_digest()
            or require_digest(payload.get("result_digest"), "result_digest") != run.result_digest()
            or run.to_dict() != dict(payload)
        ):
            raise ValidationError("VerifierRun derived fields do not match its contents")
        return run
