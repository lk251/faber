"""Fake cross-platform harness episodes for policy and validation tests."""

from __future__ import annotations

from dataclasses import dataclass

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.environments import EnvironmentEvidence, environment_satisfies_contract
from faber.receipts import VerificationReceipt
from faber.traces import (
    AttemptManifest,
    RedactionPolicy,
    TraceEvent,
    TraceManifest,
    TrajectoryConsent,
    trace_manifest_from_events,
)
from faber.trajectory_quality import TrajectoryRequirement, validate_trajectory_quality
from faber.verifiers import VerifierRun

CREATED_AT = "2026-07-09T00:00:00Z"
FIXTURE_SET_ID = "cross-platform-harness-fixtures-v1"
PLATFORM_FAMILIES = (
    "nixos",
    "linux",
    "macos",
    "windows",
    "container",
    "remote-runner",
)


@dataclass(frozen=True)
class CrossPlatformHarnessFixture:
    """Complete fake solver episode for one platform family."""

    platform_family: str
    contract: TaskContract
    environment_evidence: EnvironmentEvidence
    attempt_manifest: AttemptManifest
    trace_events: list[TraceEvent]
    trace_manifest: TraceManifest
    verifier_run: VerifierRun
    trajectory_record: dict[str, object]


def cross_platform_harness_fixtures() -> list[CrossPlatformHarnessFixture]:
    """Return one deterministic fake trajectory fixture per platform family."""

    return [_build_fixture(platform) for platform in PLATFORM_FAMILIES]


def validate_cross_platform_harness_fixtures(
    fixtures: list[CrossPlatformHarnessFixture] | None = None,
) -> list[str]:
    """Return cross-record and trajectory-policy validation errors."""

    values = fixtures if fixtures is not None else cross_platform_harness_fixtures()
    errors: list[str] = []
    families = [fixture.platform_family for fixture in values]
    if set(families) != set(PLATFORM_FAMILIES) or len(families) != len(PLATFORM_FAMILIES):
        errors.append("fixture set must contain each platform family exactly once")
    for fixture in values:
        prefix = fixture.platform_family
        fit = environment_satisfies_contract(fixture.environment_evidence, fixture.contract)
        if not fit.accepted:
            errors.append(f"{prefix}: environment does not satisfy its task contract")
        if fixture.attempt_manifest.task_contract_id != fixture.contract.id:
            errors.append(f"{prefix}: attempt manifest contract mismatch")
        if fixture.attempt_manifest.task_contract_digest != fixture.contract.digest():
            errors.append(f"{prefix}: attempt manifest contract digest mismatch")
        if fixture.trace_manifest.attempt_id != fixture.attempt_manifest.attempt_id:
            errors.append(f"{prefix}: trace manifest attempt mismatch")
        if fixture.trace_manifest.trace_event_count != len(fixture.trace_events):
            errors.append(f"{prefix}: trace event count mismatch")
        if [event.sequence for event in fixture.trace_events] != list(
            range(len(fixture.trace_events))
        ):
            errors.append(f"{prefix}: trace events are not ordered")
        if fixture.verifier_run.verifier_id not in fixture.contract.verifier_ids:
            errors.append(f"{prefix}: verifier result is not authorized by contract")
        if not fixture.verifier_run.passed:
            errors.append(f"{prefix}: fake verifier result should pass")
        report = validate_trajectory_quality(
            fixture.trajectory_record,
            report_id=f"trajectory-validation-report_fixture_{_slug(prefix)}",
            created_at=CREATED_AT,
        )
        if not report.is_rl_grade:
            errors.append(f"{prefix}: trajectory is not RL-grade")
    return errors


def _build_fixture(platform: str) -> CrossPlatformHarnessFixture:
    slug = _slug(platform)
    environment = _environment_evidence(platform)
    verifier_id = f"verifier.fixture.{slug}"
    requirement = TrajectoryRequirement(
        id=f"trajectory-requirement_fixture_{slug}",
        created_at=CREATED_AT,
        minimum_quality_tier="trace",
        require_training_eligible=True,
        require_rl_grade=True,
        full_payout_minimum_tier="trace",
        notes="Fake fixture policy used only for cross-platform validation.",
    )
    contract = TaskContract(
        id=f"task-contract_fixture_{slug}",
        created_at=CREATED_AT,
        title=f"Cross-platform harness fixture for {platform}",
        description="Validate the same offline solver episode across platform evidence levels.",
        requirements=[
            "Run the fake local verifier without external services.",
            "Capture ordered process evidence and training-use consent.",
        ],
        verifier_ids=[verifier_id],
        task_source="fake.cross-platform-fixture",
        repository="local/faber-fixture",
        environment={
            "required_platforms": [platform],
            "minimum_reproducibility_level": environment.reproducibility_level,
            "repository_snapshot": "fake-fixture-snapshot",
            "fixture_set_id": FIXTURE_SET_ID,
            "fake_data": True,
        },
        trajectory_requirement=requirement.to_dict(),
    )
    attempt = Attempt(
        id=f"attempt_fixture_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id=f"worker_fixture_{slug}",
        base_revision="fixture-base",
        candidate_revision=f"fixture-candidate-{slug}",
        summary=f"Completed the fake solver attempt on {platform}.",
        patch_digest=sha256_digest({"fixture": FIXTURE_SET_ID, "platform": platform}),
        metadata={"fake_data": True, "platform_family": platform},
    )
    redaction_policy = RedactionPolicy(
        id=f"redaction-policy_fixture_{slug}",
        created_at=CREATED_AT,
        name=f"Cross-platform fixture redaction for {platform}",
        field_paths=["payload.private_prompt", "payload.credentials"],
        allow_raw_trace=False,
    )
    consent = TrajectoryConsent(
        id=f"trajectory-consent_fixture_{slug}",
        created_at=CREATED_AT,
        training_use_allowed=True,
        allowed_uses=["rl", "supervised", "router"],
        license_ref="fake-fixture-only",
        redaction_required=True,
        notes="Synthetic fixture data only; no human or proprietary trace is present.",
    )
    environment_metadata = {
        **environment.to_dict(),
        "environment_evidence_digest": environment.digest(),
        "repository_snapshot_digest": sha256_digest(
            {"fixture": FIXTURE_SET_ID, "snapshot": platform}
        ),
        "fake_data": True,
    }
    attempt_manifest = AttemptManifest(
        id=f"attempt-manifest_fixture_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        worker_id=attempt.worker_id,
        evidence_level=2,
        redaction_policy=redaction_policy,
        model_metadata={"family": "fake-code-solver", "disclosure": "synthetic"},
        harness_metadata={
            "family": "fake-cross-platform-harness",
            "version": "1",
            "fixture_set_id": FIXTURE_SET_ID,
        },
        runner_metadata={"runner": f"fake-{slug}-runner", "version": "1"},
        environment_metadata=environment_metadata,
        tool_registry_digest=sha256_digest(
            {"fixture": FIXTURE_SET_ID, "tools": ["read", "edit", "pytest"]}
        ),
        nix_flake_lock_digest=environment.nix_flake_lock_digest,
        budget_metadata={"currency": "EUR", "budget_minor_units": 1000},
        cost_metadata={"currency": "EUR", "compute_minor_units": 25},
        latency_metadata={"work_seconds": 20},
        training_consent=consent,
        trust_level="runner_attested",
    )
    events = _trace_events(attempt, platform, verifier_id)
    trace_manifest = trace_manifest_from_events(
        attempt_id=attempt.id,
        events=events,
        evidence_level_value=2,
        trace_jsonl_digest=sha256_digest([event.to_dict() for event in events]),
        trust_level="runner_attested",
        redaction_policy=redaction_policy,
        raw_trace_digest=sha256_digest(
            {"fixture": FIXTURE_SET_ID, "platform": platform, "raw": True}
        ),
        provenance={
            "fixture_set_id": FIXTURE_SET_ID,
            "platform_family": platform,
            "source": "synthetic",
        },
        manifest_id=f"trace-manifest_fixture_{slug}",
        created_at=CREATED_AT,
    )
    verifier_run = VerifierRun(
        id=f"verifier-run_fixture_{slug}",
        created_at=CREATED_AT,
        verifier_id=verifier_id,
        name=f"Fake {platform} harness verifier",
        version="1",
        command=environment.verifier_command,
        passed=True,
        metrics={"tests": 1, "failures": 0, "fake_data": True},
        logs_digest=sha256_digest(
            {"fixture": FIXTURE_SET_ID, "platform": platform, "result": "passed"}
        ),
        metadata={
            "fixture_set_id": FIXTURE_SET_ID,
            "platform_family": platform,
            "fake_data": True,
        },
    )
    receipt = VerificationReceipt(
        id=f"verification-receipt_fixture_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id=verifier_id,
        verifier_digest=verifier_run.verifier_digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=True,
        metrics=verifier_run.metrics,
        failure_reasons=[],
        result_digest=verifier_run.result_digest(),
    )
    trajectory_record: dict[str, object] = {
        "schema": "faber.trajectory.v1",
        "id": f"trajectory_fixture_{slug}",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "attempt_manifest": attempt_manifest.to_dict(),
        "trace_manifest": trace_manifest.to_dict(),
        "verifier_run": verifier_run.to_dict(),
        "receipt": receipt.to_dict(),
        "environment_evidence": environment.to_dict(),
        "reward_metadata": {"currency": "EUR", "reward_minor_units": 1000},
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 25},
        "latency_metadata": {"work_seconds": 20, "verification_seconds": 1},
        "review_metadata": {"human_reviewed": False},
        "outcome": "accepted",
        "fixture": {"id": FIXTURE_SET_ID, "fake_data": True},
    }
    return CrossPlatformHarnessFixture(
        platform_family=platform,
        contract=contract,
        environment_evidence=environment,
        attempt_manifest=attempt_manifest,
        trace_events=events,
        trace_manifest=trace_manifest,
        verifier_run=verifier_run,
        trajectory_record=trajectory_record,
    )


def _trace_events(attempt: Attempt, platform: str, verifier_id: str) -> list[TraceEvent]:
    slug = _slug(platform)
    event_data: list[tuple[str, dict[str, object]]] = [
        ("context.loaded", {"platform": platform, "source": "synthetic"}),
        ("tool.call", {"tool": "pytest", "command": ["python", "-m", "pytest"]}),
        ("verification.result", {"verifier_id": verifier_id, "passed": True}),
        ("outcome.reported", {"accepted": True, "reward_minor_units": 1000}),
    ]
    return [
        TraceEvent(
            id=f"trace-event_fixture_{slug}_{sequence:04d}",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            sequence=sequence,
            event_type=event_type,
            observed_at=CREATED_AT,
            payload=payload,
            trust_level="runner_attested",
            provenance={
                "fixture_set_id": FIXTURE_SET_ID,
                "platform_family": platform,
                "source": "synthetic",
            },
        )
        for sequence, (event_type, payload) in enumerate(event_data)
    ]


def _environment_evidence(platform: str) -> EnvironmentEvidence:
    slug = _slug(platform)
    lock_digest = sha256_digest({"fixture": FIXTURE_SET_ID, "lockfile": platform})
    if platform == "nixos":
        return EnvironmentEvidence(
            id=f"environment-evidence_fixture_{slug}",
            created_at=CREATED_AT,
            platform=platform,
            os_family="NixOS",
            os_version="24.11-fixture",
            architecture="x86_64",
            package_manager="nix",
            lockfile_digests={"flake.lock": lock_digest},
            runtime_versions={"python": "3.12.0-fixture"},
            setup_entrypoint=["nix", "develop"],
            verifier_command=["nix", "develop", "--command", "python", "-m", "pytest"],
            tool_path_metadata={"source": "synthetic", "fake_data": True},
            nix_flake_lock_digest=lock_digest,
            reproducibility_level="nix_flake",
            limitations=["Synthetic Nix store paths; no real Nix evaluation was performed."],
            trust_level="runner_attested",
        )
    if platform == "container":
        return EnvironmentEvidence(
            id=f"environment-evidence_fixture_{slug}",
            created_at=CREATED_AT,
            platform=platform,
            os_family="Linux container",
            os_version="fixture-image-v1",
            architecture="x86_64",
            package_manager="pip",
            runtime_versions={"python": "3.12.0-fixture"},
            setup_entrypoint=["container-runtime", "run", "fixture-image"],
            verifier_command=["python", "-m", "pytest"],
            tool_path_metadata={"source": "synthetic", "fake_data": True},
            container_image_digest=sha256_digest("fake-container-image"),
            reproducibility_level="container",
            limitations=["Synthetic image digest; no container was started."],
            trust_level="runner_attested",
        )
    if platform == "remote-runner":
        return EnvironmentEvidence(
            id=f"environment-evidence_fixture_{slug}",
            created_at=CREATED_AT,
            platform=platform,
            os_family="Remote Linux runner",
            os_version="fixture-runner-v1",
            architecture="x86_64",
            package_manager="pip",
            runtime_versions={"python": "3.12.0-fixture"},
            setup_entrypoint=["runner", "prepare", "fixture"],
            verifier_command=["python", "-m", "pytest"],
            tool_path_metadata={"source": "synthetic", "fake_data": True},
            remote_runner_ref="fake-runner://cross-platform/1",
            reproducibility_level="declared",
            limitations=["Runner image is declared but not independently replayable."],
            trust_level="runner_attested",
        )
    os_families = {"linux": "Linux", "macos": "macOS", "windows": "Windows"}
    setup = (
        ["py", "-m", "venv", ".venv"]
        if platform == "windows"
        else ["python", "-m", "venv", ".venv"]
    )
    return EnvironmentEvidence(
        id=f"environment-evidence_fixture_{slug}",
        created_at=CREATED_AT,
        platform=platform,
        os_family=os_families[platform],
        os_version="fixture-v1",
        architecture="x86_64",
        package_manager="pip",
        lockfile_digests={"requirements.lock": lock_digest},
        runtime_versions={"python": "3.12.0-fixture"},
        setup_entrypoint=setup,
        verifier_command=["python", "-m", "pytest"],
        tool_path_metadata={"source": "synthetic", "fake_data": True},
        reproducibility_level="lockfile",
        limitations=["OS image and system packages are not fully pinned."],
        trust_level="runner_attested",
    )


def _slug(platform: str) -> str:
    return platform.replace("-", "_")
