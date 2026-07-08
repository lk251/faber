import json
from pathlib import Path

import pytest

from faber.attempt_manifests import (
    generate_attempt_manifest,
    load_attempt_manifest,
    write_attempt_manifest,
)
from faber.cli import main
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.traces import AttemptManifest

CREATED_AT = "2026-01-01T00:00:00Z"
CONTRACT_DIGEST = sha256_digest("contract")
ENVIRONMENT_DIGEST = sha256_digest("environment")


def _manifest() -> AttemptManifest:
    return generate_attempt_manifest(
        task_contract_id="task-contract_generator",
        task_contract_digest=CONTRACT_DIGEST,
        base_revision="base",
        candidate_revision="candidate",
        worker_id="worker_generator",
        environment_digest=ENVIRONMENT_DIGEST,
        evidence_level=3,
        model_disclosure="coarse",
        model_family="local-open-weight",
        harness_family="generic-agent-harness",
        harness_version="1",
        runner_name="local",
        runner_version="1",
        platform="windows",
        cost_minor_units=25,
        latency_seconds=60,
        redaction_field_paths=["secret", "context.private_prompt"],
        created_at=CREATED_AT,
    )


def test_generated_manifest_validates() -> None:
    manifest = _manifest()
    parsed = AttemptManifest.from_dict(manifest.to_dict())

    assert parsed.task_contract_id == "task-contract_generator"
    assert parsed.task_contract_digest == CONTRACT_DIGEST
    assert parsed.environment_metadata["digest"] == ENVIRONMENT_DIGEST
    assert parsed.model_metadata["disclosure"] == "coarse"
    assert parsed.harness_metadata["family"] == "generic-agent-harness"
    assert parsed.cost_metadata["compute_minor_units"] == 25
    assert parsed.latency_metadata["work_seconds"] == 60
    assert parsed.redaction_policy.field_paths == ["secret", "context.private_prompt"]


def test_invalid_required_fields_fail_clearly() -> None:
    with pytest.raises(ValidationError, match="worker_id"):
        generate_attempt_manifest(
            task_contract_id="task-contract_generator",
            task_contract_digest=CONTRACT_DIGEST,
            base_revision="base",
            candidate_revision="candidate",
            worker_id="",
            environment_digest=ENVIRONMENT_DIGEST,
            created_at=CREATED_AT,
        )


def test_generated_manifest_digest_is_stable() -> None:
    left = _manifest()
    right = _manifest()

    assert left.attempt_id == right.attempt_id
    assert left.digest() == right.digest()


def test_write_and_load_manifest_round_trip(tmp_path: Path) -> None:
    out_path = tmp_path / ".faber" / "attempt.json"
    manifest = _manifest()

    digest = write_attempt_manifest(manifest, out_path)
    loaded = load_attempt_manifest(out_path)

    assert digest == manifest.digest()
    assert loaded.digest() == manifest.digest()
    assert json.loads(out_path.read_text(encoding="utf-8"))["attempt_id"] == manifest.attempt_id


def test_cli_generates_and_validates_attempt_manifest(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / ".faber" / "attempt.json"

    assert (
        main(
            [
                "generate-attempt-manifest",
                "--out",
                str(out_path),
                "--task-contract-id",
                "task-contract_cli",
                "--task-contract-digest",
                CONTRACT_DIGEST,
                "--base-revision",
                "base",
                "--candidate-revision",
                "candidate",
                "--worker-id",
                "worker_cli",
                "--environment-digest",
                ENVIRONMENT_DIGEST,
                "--created-at",
                CREATED_AT,
            ]
        )
        == 0
    )
    generated_output = capsys.readouterr().out
    assert "attempt_id" in generated_output
    assert out_path.exists()

    assert main(["validate-attempt-manifest", str(out_path)]) == 0
    validation_output = capsys.readouterr().out
    assert '"status":"valid"' in validation_output


def test_example_hermes_manifest_fixture_validates() -> None:
    manifest = load_attempt_manifest("examples/hermes/attempt_manifest_48628.json")

    assert manifest.task_contract_id == "task-contract_hermes_nixos_lazy_deps_48628"
    assert manifest.harness_metadata["target_project"] == "NousResearch/hermes-agent"
    assert manifest.harness_metadata["target_issue"] == 48628
    assert manifest.evidence_level == 3
