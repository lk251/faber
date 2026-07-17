"""Strict repository-owner configuration loading for the Faber Proof product."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from faber import schemas
from faber.canonical_json import canonical_json_bytes
from faber.contracts import TaskContract
from faber.errors import ValidationError
from faber.money import Money
from faber.proof_catalog import (
    ArtifactValidatorCapability,
    ExistingCommandCapability,
    FileInvariantCapability,
    ProofCapability,
    ProofCapabilityPolicy,
    ProofCatalog,
    ProofCatalogEntry,
    PytestNodeCapability,
    PythonCallCapability,
)
from faber.proofs import ProofClaim, ProofPolicy
from faber.validation import require_digest, require_non_empty_string, require_schema
from faber.verifiers import VerifierRegistry, VerifierSpec

PROOF_CONFIGURATION_SCHEMA = "faber.proof_configuration.v1"
PROOF_EXECUTION_SETTINGS_SCHEMA = "faber.proof_execution_settings.v1"
MAX_CONFIGURATION_BYTES = 4 * 1024 * 1024
MAX_TASK_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_INTEGER = (1 << 63) - 1


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _strict_integer(value: str) -> int:
    result = int(value)
    if abs(result) > MAX_JSON_INTEGER:
        raise ValueError("JSON integer outside the signed 64-bit range")
    return result


def _strict_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number must be finite")
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def load_strict_json_object(path: str | Path, *, max_bytes: int) -> Mapping[str, object]:
    source = Path(path)
    try:
        payload = source.read_bytes()
    except OSError:
        raise ValidationError("JSON input could not be read") from None
    if len(payload) > max_bytes:
        raise ValidationError("JSON input exceeds its byte limit")
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_constant,
            parse_int=_strict_integer,
            parse_float=_strict_float,
        )
        canonical_json_bytes(value)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ValidationError("JSON input must be strict canonicalizable UTF-8 JSON") from None
    if not isinstance(value, Mapping):
        raise ValidationError("JSON input root must be an object")
    return value


def _record(
    value: object,
    label: str,
    fields: set[str],
    *,
    optional: frozenset[str] = frozenset(),
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be an object")
    unknown = set(value) - fields
    missing = (fields - set(value)) - optional
    if unknown:
        raise ValidationError(f"{label} contains unknown fields")
    if missing:
        raise ValidationError(f"{label} is missing required fields: {sorted(missing)}")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValidationError(f"{label} must be a sequence")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be an object")
    return value


def _string_sequence(value: object, label: str) -> tuple[str, ...]:
    return tuple(
        require_non_empty_string(item, f"{label}[{index}]")
        for index, item in enumerate(_sequence(value, label))
    )


def _string_mapping(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be an object")
    result: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = require_non_empty_string(raw_key, f"{label} key")
        result[key] = require_non_empty_string(raw_value, f"{label}.{key}")
    return result


def load_task_contract(path: str | Path) -> TaskContract:
    payload = _record(
        load_strict_json_object(path, max_bytes=MAX_TASK_BYTES),
        "TaskContract",
        {
            "schema",
            "id",
            "created_at",
            "title",
            "description",
            "requirements",
            "verifier_ids",
            "task_source",
            "repository",
            "environment",
            "trajectory_requirement",
            "source_reference",
            "reward",
        },
    )
    require_schema(payload.get("schema"), schemas.TASK_CONTRACT)
    repository = payload.get("repository")
    if repository is not None:
        repository = require_non_empty_string(repository, "repository")
    environment = _mapping(payload.get("environment"), "environment")
    trajectory_requirement = _mapping(
        payload.get("trajectory_requirement"), "trajectory_requirement"
    )
    source_reference = _mapping(payload.get("source_reference"), "source_reference")
    raw_reward = payload.get("reward")
    reward: Money | None = None
    if raw_reward is not None:
        reward_payload = _record(raw_reward, "reward", {"currency", "minor_units"})
        minor_units = reward_payload.get("minor_units")
        if isinstance(minor_units, bool) or not isinstance(minor_units, int):
            raise ValidationError("reward.minor_units must be an integer")
        reward = Money(
            currency=require_non_empty_string(reward_payload.get("currency"), "reward.currency"),
            minor_units=minor_units,
        )
    return TaskContract(
        schema=require_non_empty_string(payload.get("schema"), "schema"),
        id=require_non_empty_string(payload.get("id"), "id"),
        created_at=require_non_empty_string(payload.get("created_at"), "created_at"),
        title=require_non_empty_string(payload.get("title"), "title"),
        description=require_non_empty_string(payload.get("description"), "description"),
        requirements=list(_string_sequence(payload.get("requirements"), "requirements")),
        verifier_ids=list(_string_sequence(payload.get("verifier_ids"), "verifier_ids")),
        task_source=require_non_empty_string(payload.get("task_source"), "task_source"),
        repository=repository,
        environment=dict(environment),
        trajectory_requirement=dict(trajectory_requirement),
        source_reference=dict(source_reference),
        reward=reward,
    )


def _verifier_spec(value: object) -> VerifierSpec:
    payload = _record(
        value,
        "VerifierSpec",
        {
            "schema",
            "id",
            "created_at",
            "verifier_id",
            "name",
            "version",
            "description",
            "command_template",
            "working_directory_policy",
            "allowed_timeout_seconds",
            "expected_output_convention",
        },
    )
    require_schema(payload.get("schema"), schemas.VERIFIER_SPEC)
    timeout = payload.get("allowed_timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int):
        raise ValidationError("allowed_timeout_seconds must be an integer")
    return VerifierSpec(
        schema=require_non_empty_string(payload.get("schema"), "schema"),
        id=require_non_empty_string(payload.get("id"), "id"),
        created_at=require_non_empty_string(payload.get("created_at"), "created_at"),
        verifier_id=require_non_empty_string(payload.get("verifier_id"), "verifier_id"),
        name=require_non_empty_string(payload.get("name"), "name"),
        version=require_non_empty_string(payload.get("version"), "version"),
        description=require_non_empty_string(payload.get("description"), "description"),
        command_template=list(
            _string_sequence(payload.get("command_template"), "command_template")
        ),
        working_directory_policy=require_non_empty_string(
            payload.get("working_directory_policy"), "working_directory_policy"
        ),
        allowed_timeout_seconds=timeout,
        expected_output_convention=require_non_empty_string(
            payload.get("expected_output_convention"), "expected_output_convention"
        ),
    )


def _capability_policy(value: object) -> ProofCapabilityPolicy:
    payload = _record(
        value,
        "ProofCapabilityPolicy",
        {
            "verifier_id",
            "verifier_version",
            "verifier_spec_digest",
            "working_directory",
            "timeout_seconds",
            "max_output_bytes",
            "environment_variables",
            "trusted_file_digests",
        },
    )
    for field in ("timeout_seconds", "max_output_bytes"):
        if isinstance(payload.get(field), bool) or not isinstance(payload.get(field), int):
            raise ValidationError(f"{field} must be an integer")
    spec_digest = payload.get("verifier_spec_digest")
    if spec_digest is not None:
        spec_digest = require_digest(spec_digest, "verifier_spec_digest")
    return ProofCapabilityPolicy(
        verifier_id=require_non_empty_string(payload.get("verifier_id"), "verifier_id"),
        verifier_version=require_non_empty_string(
            payload.get("verifier_version"), "verifier_version"
        ),
        verifier_spec_digest=spec_digest,
        working_directory=require_non_empty_string(
            payload.get("working_directory"), "working_directory"
        ),
        timeout_seconds=payload["timeout_seconds"],  # type: ignore[arg-type]
        max_output_bytes=payload["max_output_bytes"],  # type: ignore[arg-type]
        environment_variables=_string_mapping(
            payload.get("environment_variables"), "environment_variables"
        ),
        trusted_file_digests=_string_mapping(
            payload.get("trusted_file_digests"), "trusted_file_digests"
        ),
    )


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_non_empty_string(value, label)


def _capability(value: object) -> ProofCapability:
    if not isinstance(value, Mapping):
        raise ValidationError("capability must be an object")
    family = require_non_empty_string(value.get("family"), "capability.family")
    policy = _capability_policy(value.get("policy"))
    if family == "existing-command":
        _record(value, "existing-command capability", {"family", "policy"})
        return ExistingCommandCapability(policy=policy)
    if family == "pytest-node":
        payload = _record(
            value,
            "pytest-node capability",
            {"family", "policy", "node_ids", "python_module"},
        )
        return PytestNodeCapability(
            policy=policy,
            node_ids=_string_sequence(payload.get("node_ids"), "node_ids"),
            python_module=require_non_empty_string(payload.get("python_module"), "python_module"),
        )
    if family == "python-call":
        payload = _record(
            value,
            "python-call capability",
            {
                "family",
                "policy",
                "module",
                "callable_name",
                "module_file",
                "import_root",
                "positional_parameter",
                "keyword_parameter",
                "assertion_parameter",
                "expected_parameter",
                "default_assertion",
                "allowed_assertions",
                "result_serializer",
            },
        )
        return PythonCallCapability(
            policy=policy,
            module=require_non_empty_string(payload.get("module"), "module"),
            callable_name=require_non_empty_string(payload.get("callable_name"), "callable_name"),
            module_file=_optional_string(payload.get("module_file"), "module_file"),
            import_root=require_non_empty_string(payload.get("import_root"), "import_root"),
            positional_parameter=_optional_string(
                payload.get("positional_parameter"), "positional_parameter"
            ),
            keyword_parameter=_optional_string(
                payload.get("keyword_parameter"), "keyword_parameter"
            ),
            assertion_parameter=_optional_string(
                payload.get("assertion_parameter"), "assertion_parameter"
            ),
            expected_parameter=_optional_string(
                payload.get("expected_parameter"), "expected_parameter"
            ),
            default_assertion=require_non_empty_string(
                payload.get("default_assertion"), "default_assertion"
            ),
            allowed_assertions=_string_sequence(
                payload.get("allowed_assertions"), "allowed_assertions"
            ),
            result_serializer=require_non_empty_string(
                payload.get("result_serializer"), "result_serializer"
            ),
        )
    if family == "file-invariant":
        payload = _record(
            value,
            "file-invariant capability",
            {
                "family",
                "policy",
                "repository_path",
                "operation",
                "expected_parameter",
                "json_pointer_parameter",
            },
        )
        return FileInvariantCapability(
            policy=policy,
            repository_path=require_non_empty_string(
                payload.get("repository_path"), "repository_path"
            ),
            operation=require_non_empty_string(payload.get("operation"), "operation"),
            expected_parameter=_optional_string(
                payload.get("expected_parameter"), "expected_parameter"
            ),
            json_pointer_parameter=_optional_string(
                payload.get("json_pointer_parameter"), "json_pointer_parameter"
            ),
        )
    if family == "artifact-validator":
        payload = _record(
            value,
            "artifact-validator capability",
            {"family", "policy", "artifact_kind", "repository_path", "quality_only"},
        )
        quality_only = payload.get("quality_only")
        if not isinstance(quality_only, bool):
            raise ValidationError("quality_only must be a boolean")
        return ArtifactValidatorCapability(
            policy=policy,
            artifact_kind=require_non_empty_string(payload.get("artifact_kind"), "artifact_kind"),
            repository_path=require_non_empty_string(
                payload.get("repository_path"), "repository_path"
            ),
            quality_only=quality_only,
        )
    raise ValidationError("capability family is not supported")


def _catalog(value: object) -> ProofCatalog:
    payload = _record(value, "ProofCatalog", {"schema", "entries", "planner_catalog_digest"})
    entries: list[ProofCatalogEntry] = []
    for index, raw_entry in enumerate(_sequence(payload.get("entries"), "entries")):
        item = _record(
            raw_entry,
            f"entries[{index}]",
            {
                "schema",
                "id",
                "version",
                "description",
                "family",
                "execution_parameter_schema",
                "parameter_defaults",
                "assertion_operators",
                "capability_limits",
                "capability",
                "capability_digest",
            },
        )
        execution_parameter_schema = _mapping(
            item.get("execution_parameter_schema"),
            f"entries[{index}].execution_parameter_schema",
        )
        parameter_defaults = _mapping(
            item.get("parameter_defaults"), f"entries[{index}].parameter_defaults"
        )
        capability_limits = _mapping(
            item.get("capability_limits"), f"entries[{index}].capability_limits"
        )
        capability = _capability(item.get("capability"))
        family = require_non_empty_string(item.get("family"), "family")
        if capability.family != family:
            raise ValidationError("catalog entry family does not match its capability")
        entry = ProofCatalogEntry(
            schema=require_non_empty_string(item.get("schema"), "schema"),
            id=require_non_empty_string(item.get("id"), "id"),
            version=require_non_empty_string(item.get("version"), "version"),
            description=require_non_empty_string(item.get("description"), "description"),
            execution_parameter_schema=dict(execution_parameter_schema),
            parameter_defaults=dict(parameter_defaults),
            assertion_operators=_string_sequence(
                item.get("assertion_operators"), "assertion_operators"
            ),
            capability_limits=dict(capability_limits),
            capability=capability,
        )
        if entry.capability_digest() != require_digest(
            item.get("capability_digest"), "capability_digest"
        ):
            raise ValidationError("catalog capability digest does not match its entry")
        entries.append(entry)
    catalog = ProofCatalog(
        schema=require_non_empty_string(payload.get("schema"), "schema"),
        entries=entries,
    )
    if catalog.digest() != require_digest(
        payload.get("planner_catalog_digest"), "planner_catalog_digest"
    ):
        raise ValidationError("planner_catalog_digest does not match the catalog")
    return catalog


@dataclass(frozen=True)
class ProofExecutionSettings:
    maximum_obligations: int = 32
    per_obligation_timeout_seconds: int = 30
    total_timeout_seconds: int = 120
    max_input_bytes: int = 65_536
    max_output_bytes: int = 64_000
    allowed_environment_variables: Sequence[str] = ()
    schema: str = PROOF_EXECUTION_SETTINGS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROOF_EXECUTION_SETTINGS_SCHEMA:
            raise ValidationError(f"schema must be {PROOF_EXECUTION_SETTINGS_SCHEMA!r}")
        for field, maximum in (
            ("maximum_obligations", 256),
            ("per_obligation_timeout_seconds", 3600),
            ("total_timeout_seconds", 14_400),
            ("max_input_bytes", 16 * 1024 * 1024),
            ("max_output_bytes", 16 * 1024 * 1024),
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValidationError(f"{field} must be a bounded positive integer")
        variables = _string_sequence(
            self.allowed_environment_variables, "allowed_environment_variables"
        )
        if len(set(variables)) != len(variables):
            raise ValidationError("allowed_environment_variables contains duplicates")
        object.__setattr__(self, "allowed_environment_variables", tuple(sorted(variables)))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "maximum_obligations": self.maximum_obligations,
            "per_obligation_timeout_seconds": self.per_obligation_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "max_input_bytes": self.max_input_bytes,
            "max_output_bytes": self.max_output_bytes,
            "allowed_environment_variables": list(self.allowed_environment_variables),
        }

    @classmethod
    def from_dict(cls, value: object) -> ProofExecutionSettings:
        payload = _record(
            value,
            "ProofExecutionSettings",
            {
                "schema",
                "maximum_obligations",
                "per_obligation_timeout_seconds",
                "total_timeout_seconds",
                "max_input_bytes",
                "max_output_bytes",
                "allowed_environment_variables",
            },
        )
        for field in (
            "maximum_obligations",
            "per_obligation_timeout_seconds",
            "total_timeout_seconds",
            "max_input_bytes",
            "max_output_bytes",
        ):
            if isinstance(payload.get(field), bool) or not isinstance(payload.get(field), int):
                raise ValidationError(f"{field} must be an integer")
        return cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            maximum_obligations=payload["maximum_obligations"],  # type: ignore[arg-type]
            per_obligation_timeout_seconds=payload[  # type: ignore[arg-type]
                "per_obligation_timeout_seconds"
            ],
            total_timeout_seconds=payload["total_timeout_seconds"],  # type: ignore[arg-type]
            max_input_bytes=payload["max_input_bytes"],  # type: ignore[arg-type]
            max_output_bytes=payload["max_output_bytes"],  # type: ignore[arg-type]
            allowed_environment_variables=_string_sequence(
                payload.get("allowed_environment_variables"), "allowed_environment_variables"
            ),
        )


@dataclass(frozen=True)
class ProofConfiguration:
    catalog: ProofCatalog
    verifier_specs: Sequence[VerifierSpec]
    proof_policy: ProofPolicy
    mandatory_claims: Sequence[ProofClaim]
    execution: ProofExecutionSettings
    approved_replay_bundle_digests: Sequence[str] = ()
    context_excluded_paths: Sequence[str] = ()
    schema: str = PROOF_CONFIGURATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROOF_CONFIGURATION_SCHEMA:
            raise ValidationError(f"schema must be {PROOF_CONFIGURATION_SCHEMA!r}")
        if not isinstance(self.catalog, ProofCatalog):
            raise ValidationError("catalog must be ProofCatalog")
        specs = tuple(self.verifier_specs)
        if not specs or any(not isinstance(spec, VerifierSpec) for spec in specs):
            raise ValidationError("verifier_specs must contain VerifierSpec records")
        if len({spec.verifier_id for spec in specs}) != len(specs):
            raise ValidationError("verifier_specs contains duplicate verifier IDs")
        if not isinstance(self.proof_policy, ProofPolicy):
            raise ValidationError("proof_policy must be ProofPolicy")
        claims = tuple(self.mandatory_claims)
        if any(not isinstance(claim, ProofClaim) for claim in claims):
            raise ValidationError("mandatory_claims must contain ProofClaim records")
        if {claim.id for claim in claims} != set(self.proof_policy.mandatory_claim_ids):
            raise ValidationError("mandatory_claims must exactly define proof_policy claim IDs")
        if not isinstance(self.execution, ProofExecutionSettings):
            raise ValidationError("execution must be ProofExecutionSettings")
        replay_digests = tuple(
            require_digest(value, f"approved_replay_bundle_digests[{index}]")
            for index, value in enumerate(self.approved_replay_bundle_digests)
        )
        if len(set(replay_digests)) != len(replay_digests):
            raise ValidationError("approved_replay_bundle_digests contains duplicates")
        exclusions = _string_sequence(self.context_excluded_paths, "context_excluded_paths")
        registry = VerifierRegistry()
        for spec in specs:
            registry.register(spec)
        for entry in self.catalog.entries:
            spec = registry.resolve(entry.policy.verifier_id)
            if (
                spec.version != entry.policy.verifier_version
                or spec.digest() != entry.policy.verifier_spec_digest
            ):
                raise ValidationError("catalog capability does not bind its registered verifier")
            if spec.verifier_id not in self.proof_policy.approved_verifier_ids:
                raise ValidationError("catalog capability uses an unapproved verifier")
        if set(self.proof_policy.mandatory_template_ids) - {
            entry.id for entry in self.catalog.entries
        }:
            raise ValidationError("proof policy references an unknown mandatory template")
        if set(self.proof_policy.mandatory_verifier_ids) - {spec.verifier_id for spec in specs}:
            raise ValidationError("proof policy references an unknown mandatory verifier")
        object.__setattr__(
            self, "verifier_specs", tuple(sorted(specs, key=lambda item: item.verifier_id))
        )
        object.__setattr__(
            self, "mandatory_claims", tuple(sorted(claims, key=lambda item: item.id))
        )
        object.__setattr__(self, "approved_replay_bundle_digests", tuple(sorted(replay_digests)))
        object.__setattr__(self, "context_excluded_paths", tuple(sorted(exclusions)))

    def verifier_registry(self) -> VerifierRegistry:
        registry = VerifierRegistry()
        for spec in self.verifier_specs:
            registry.register(spec)
        return registry

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "catalog": self.catalog.to_dict(),
            "verifier_registry": {
                "schema": "faber.verifier_registry_snapshot.v1",
                "specs": [spec.to_dict() for spec in self.verifier_specs],
            },
            "proof_policy": self.proof_policy.to_dict(),
            "mandatory_claims": [claim.to_dict() for claim in self.mandatory_claims],
            "execution": self.execution.to_dict(),
            "approved_replay_bundle_digests": list(self.approved_replay_bundle_digests),
            "context_excluded_paths": list(self.context_excluded_paths),
        }

    @classmethod
    def from_dict(cls, value: object) -> ProofConfiguration:
        payload = _record(
            value,
            "ProofConfiguration",
            {
                "schema",
                "catalog",
                "verifier_registry",
                "proof_policy",
                "mandatory_claims",
                "execution",
                "approved_replay_bundle_digests",
                "context_excluded_paths",
            },
        )
        registry_payload = _record(
            payload.get("verifier_registry"),
            "verifier_registry",
            {"schema", "specs"},
        )
        if registry_payload.get("schema") != "faber.verifier_registry_snapshot.v1":
            raise ValidationError("verifier_registry uses an unsupported schema")
        policy_payload = payload.get("proof_policy")
        if not isinstance(policy_payload, Mapping):
            raise ValidationError("proof_policy must be an object")
        claims: list[ProofClaim] = []
        for raw_claim in _sequence(payload.get("mandatory_claims"), "mandatory_claims"):
            if not isinstance(raw_claim, Mapping):
                raise ValidationError("mandatory_claims must contain objects")
            claims.append(ProofClaim.from_dict(raw_claim))
        return cls(
            schema=require_non_empty_string(payload.get("schema"), "schema"),
            catalog=_catalog(payload.get("catalog")),
            verifier_specs=tuple(
                _verifier_spec(spec)
                for spec in _sequence(registry_payload.get("specs"), "verifier_registry.specs")
            ),
            proof_policy=ProofPolicy.from_dict(policy_payload),
            mandatory_claims=claims,
            execution=ProofExecutionSettings.from_dict(payload.get("execution")),
            approved_replay_bundle_digests=tuple(
                require_digest(value, f"approved_replay_bundle_digests[{index}]")
                for index, value in enumerate(
                    _sequence(
                        payload.get("approved_replay_bundle_digests"),
                        "approved_replay_bundle_digests",
                    )
                )
            ),
            context_excluded_paths=_string_sequence(
                payload.get("context_excluded_paths"), "context_excluded_paths"
            ),
        )


def load_proof_configuration(path: str | Path) -> ProofConfiguration:
    return ProofConfiguration.from_dict(
        load_strict_json_object(path, max_bytes=MAX_CONFIGURATION_BYTES)
    )
