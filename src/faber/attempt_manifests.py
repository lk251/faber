"""Helpers for generating and validating `.faber/attempt.json` manifests."""

from __future__ import annotations

import json
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import utc_now
from faber.traces import AttemptManifest, RedactionPolicy, TrajectoryConsent
from faber.validation import require_digest, require_non_empty_string

DEFAULT_REDACTION_FIELD_PATHS = [
    "context.private_prompt",
    "credentials.api_key",
    "secret",
]


def generate_attempt_manifest(
    *,
    task_contract_id: str,
    task_contract_digest: str,
    base_revision: str,
    candidate_revision: str,
    worker_id: str,
    environment_digest: str,
    attempt_id: str | None = None,
    evidence_level: int = 1,
    model_disclosure: str = "private",
    model_family: str = "undisclosed",
    model_ref: str | None = None,
    harness_family: str = "generic",
    harness_version: str | None = None,
    runner_name: str = "manual",
    runner_version: str = "1",
    platform: str = "declared",
    cost_minor_units: int = 0,
    latency_seconds: int = 0,
    currency: str = "EUR",
    redaction_field_paths: list[str] | None = None,
    training_use_allowed: bool = False,
    training_allowed_uses: list[str] | None = None,
    training_license_ref: str = "unspecified",
    created_at: str | None = None,
    manifest_id: str | None = None,
    redaction_policy_id: str | None = None,
) -> AttemptManifest:
    """Generate a valid attempt manifest from local PR metadata."""

    require_non_empty_string(task_contract_id, "task_contract_id")
    require_digest(task_contract_digest, "task_contract_digest")
    require_non_empty_string(base_revision, "base_revision")
    require_non_empty_string(candidate_revision, "candidate_revision")
    require_non_empty_string(worker_id, "worker_id")
    require_digest(environment_digest, "environment_digest")
    require_non_empty_string(model_disclosure, "model_disclosure")
    require_non_empty_string(model_family, "model_family")
    if model_ref is not None:
        require_non_empty_string(model_ref, "model_ref")
    require_non_empty_string(harness_family, "harness_family")
    if harness_version is not None:
        require_non_empty_string(harness_version, "harness_version")
    require_non_empty_string(runner_name, "runner_name")
    require_non_empty_string(runner_version, "runner_version")
    require_non_empty_string(platform, "platform")
    require_non_negative_int(cost_minor_units, "cost_minor_units")
    require_non_negative_int(latency_seconds, "latency_seconds")
    require_non_empty_string(currency, "currency")
    require_non_empty_string(training_license_ref, "training_license_ref")

    timestamp = created_at or utc_now()
    suffix = _stable_attempt_suffix(
        task_contract_id=task_contract_id,
        base_revision=base_revision,
        candidate_revision=candidate_revision,
        worker_id=worker_id,
    )
    attempt_id_value = attempt_id or f"attempt_{suffix}"
    field_paths = redaction_field_paths or list(DEFAULT_REDACTION_FIELD_PATHS)
    redaction_policy = RedactionPolicy(
        id=redaction_policy_id or f"redaction-policy_{suffix}",
        created_at=timestamp,
        name="Generated attempt manifest redaction",
        field_paths=field_paths,
        allow_raw_trace=False,
    )
    training_consent = TrajectoryConsent(
        id=f"trajectory-consent_{suffix}",
        created_at=timestamp,
        training_use_allowed=training_use_allowed,
        allowed_uses=training_allowed_uses or [],
        license_ref=training_license_ref,
        redaction_required=True,
    )
    model_metadata: dict[str, object] = {
        "disclosure": model_disclosure,
        "family": model_family,
    }
    if model_ref is not None:
        model_metadata["model_ref"] = model_ref
    harness_metadata: dict[str, object] = {"family": harness_family}
    if harness_version is not None:
        harness_metadata["version"] = harness_version
    return AttemptManifest(
        id=manifest_id or f"attempt-manifest_{suffix}",
        created_at=timestamp,
        task_contract_id=task_contract_id,
        task_contract_digest=task_contract_digest,
        attempt_id=attempt_id_value,
        base_revision=base_revision,
        candidate_revision=candidate_revision,
        worker_id=worker_id,
        evidence_level=evidence_level,
        redaction_policy=redaction_policy,
        model_metadata=model_metadata,
        harness_metadata=harness_metadata,
        runner_metadata={"runner": runner_name, "version": runner_version},
        environment_metadata={
            "digest": environment_digest,
            "platform": platform,
            "external_services": [],
        },
        cost_metadata={"currency": currency.upper(), "compute_minor_units": cost_minor_units},
        latency_metadata={"work_seconds": latency_seconds},
        training_consent=training_consent,
        trust_level="self_attested",
    )


def require_non_negative_int(value: int, field: str) -> int:
    """Validate an integer minor-unit or duration field."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    if value < 0:
        raise ValidationError(f"{field} must be non-negative")
    return value


def attempt_manifest_json(manifest: AttemptManifest) -> str:
    """Return canonical manifest JSON with a trailing newline."""

    return canonical_json(manifest.to_dict()) + "\n"


def write_attempt_manifest(manifest: AttemptManifest, out_path: str | Path) -> str:
    """Write `.faber/attempt.json` and return the manifest digest."""

    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(attempt_manifest_json(manifest), encoding="utf-8")
    return manifest.digest()


def load_attempt_manifest(path: str | Path) -> AttemptManifest:
    """Load and validate an attempt manifest from JSON."""

    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValidationError("attempt manifest must be a JSON object")
    return AttemptManifest.from_dict(parsed)


def _stable_attempt_suffix(
    *,
    task_contract_id: str,
    base_revision: str,
    candidate_revision: str,
    worker_id: str,
) -> str:
    digest = sha256_digest(
        {
            "task_contract_id": task_contract_id,
            "base_revision": base_revision,
            "candidate_revision": candidate_revision,
            "worker_id": worker_id,
        }
    ).removeprefix("sha256:")
    return digest[:16]
