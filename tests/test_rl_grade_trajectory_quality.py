from pathlib import Path

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.digests import sha256_digest
from faber.receipts import VerificationReceipt
from faber.traces import (
    AttemptManifest,
    EpisodePackage,
    RedactionPolicy,
    TraceEvent,
    TrajectoryConsent,
    trace_manifest_from_events,
)
from faber.trajectory_quality import TrajectoryRequirement, validate_trajectory_quality

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract(*, requirement: TrajectoryRequirement | None = None) -> TaskContract:
    return TaskContract(
        id="task-contract_rl_grade",
        created_at=CREATED_AT,
        title="RL-grade work",
        description="Validate trajectory quality.",
        requirements=["Produce verifiable work."],
        verifier_ids=["verifier.local"],
        task_source="test",
        repository="lk251/faber",
        environment={"platform": "windows", "repository_snapshot": "fixture"},
        trajectory_requirement=requirement.to_dict() if requirement else {},
    )


def _attempt(contract: TaskContract) -> Attempt:
    return Attempt(
        id="attempt_rl_grade",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id="worker.local",
        base_revision="base",
        candidate_revision="candidate",
        summary="Implemented task.",
        patch_digest=sha256_digest("patch"),
    )


def _receipt(
    contract: TaskContract,
    attempt: Attempt,
    *,
    accepted: bool = True,
) -> VerificationReceipt:
    return VerificationReceipt(
        id=f"verification-receipt_{'accepted' if accepted else 'rejected'}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id="verifier.local",
        verifier_digest=sha256_digest("verifier"),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics={"tests": 1},
        failure_reasons=[] if accepted else ["verification failed"],
        result_digest=sha256_digest({"accepted": accepted}),
    )


def _redaction_policy() -> RedactionPolicy:
    return RedactionPolicy(
        id="redaction-policy_rl_grade",
        created_at=CREATED_AT,
        name="RL fixture redaction",
        field_paths=["payload.private_prompt"],
    )


def _training_consent(*, allowed: bool = True) -> TrajectoryConsent:
    return TrajectoryConsent(
        id=f"trajectory-consent_{'allowed' if allowed else 'denied'}",
        created_at=CREATED_AT,
        training_use_allowed=allowed,
        allowed_uses=["rl", "supervised", "router"] if allowed else [],
        license_ref="test-fixture",
    )


def _manifest(
    contract: TaskContract,
    attempt: Attempt,
    *,
    evidence_level: int = 1,
    consent_allowed: bool = True,
) -> AttemptManifest:
    return AttemptManifest(
        id=f"attempt-manifest_level_{evidence_level}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        worker_id=attempt.worker_id,
        evidence_level=evidence_level,
        redaction_policy=_redaction_policy(),
        model_metadata={"family": "local-code", "disclosure": "coarse"},
        harness_metadata={"family": "faber-runner", "version": "1"},
        runner_metadata={"runner": "faber-runner", "version": "1"},
        environment_metadata={
            "platform": "windows",
            "reproducibility_level": "lockfile",
            "repository_snapshot_digest": sha256_digest("repo"),
        },
        budget_metadata={"currency": "EUR", "budget_minor_units": 1000},
        cost_metadata={"currency": "EUR", "compute_minor_units": 120},
        latency_metadata={"work_seconds": 30},
        training_consent=_training_consent(allowed=consent_allowed),
        trust_level="runner_attested",
    )


def _events(attempt: Attempt) -> list[TraceEvent]:
    return [
        TraceEvent(
            id="trace-event_context",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            sequence=0,
            event_type="context.read",
            observed_at=CREATED_AT,
            payload={"path": "docs/TRACE_STRATEGY.md"},
            trust_level="runner_attested",
        ),
        TraceEvent(
            id="trace-event_tool",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            sequence=1,
            event_type="tool.call",
            observed_at=CREATED_AT,
            payload={"tool": "pytest"},
            trust_level="runner_attested",
        ),
        TraceEvent(
            id="trace-event_verifier",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            sequence=2,
            event_type="verification.result",
            observed_at=CREATED_AT,
            payload={"passed": True},
            trust_level="runner_attested",
        ),
    ]


def _trace_manifest(
    attempt: Attempt,
    tmp_path: Path,
    *,
    evidence_level: int = 2,
    redacted: bool = False,
):
    events = _events(attempt)
    text = "\n".join(event.id for event in events).encode("utf-8")
    return trace_manifest_from_events(
        attempt_id=attempt.id,
        events=events,
        evidence_level_value=evidence_level,
        trace_jsonl_digest=sha256_digest(text),
        trust_level="runner_attested",
        redaction_policy=_redaction_policy() if redacted else None,
        raw_trace_digest=sha256_digest("raw trace") if redacted else None,
        provenance={"runner": "faber", "path": str(tmp_path / "trace.jsonl")},
        manifest_id=f"trace-manifest_level_{evidence_level}_{'redacted' if redacted else 'full'}",
        created_at=CREATED_AT,
    )


def _record(
    tmp_path: Path,
    *,
    requirement: TrajectoryRequirement | None = None,
    manifest: bool = False,
    trace: bool = False,
    episode: bool = False,
    accepted: bool = True,
    reward: bool = True,
    consent_allowed: bool = True,
    redacted: bool = False,
) -> dict[str, object]:
    contract = _contract(requirement=requirement)
    attempt = _attempt(contract)
    receipt = _receipt(contract, attempt, accepted=accepted)
    evidence_level = 4 if episode else 2 if trace else 1
    attempt_manifest = (
        _manifest(
            contract,
            attempt,
            evidence_level=evidence_level,
            consent_allowed=consent_allowed,
        )
        if manifest or trace or episode
        else None
    )
    trace_manifest = (
        _trace_manifest(
            attempt,
            tmp_path,
            evidence_level=4 if episode else 2,
            redacted=redacted,
        )
        if trace or episode
        else None
    )
    episode_package = (
        EpisodePackage(
            id="episode-package_rl_grade",
            created_at=CREATED_AT,
            task_contract_id=contract.id,
            attempt_id=attempt.id,
            attempt_manifest=attempt_manifest,
            trace_manifest=trace_manifest,
            artifact_digests=[sha256_digest("artifact")],
            replay_instructions=["Run verifier in the recorded workspace snapshot."],
        )
        if episode and attempt_manifest and trace_manifest
        else None
    )
    record: dict[str, object] = {
        "schema": "faber.trajectory.v1",
        "id": f"trajectory_{'accepted' if accepted else 'rejected'}",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "receipt": receipt.to_dict(),
        "router_decision": {"policy_name": "fixture"},
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 120},
        "latency_metadata": {"work_seconds": 30},
        "review_metadata": {"human_reviewed": False},
        "outcome": "accepted" if accepted else "rejected",
    }
    if reward:
        record["reward_metadata"] = {
            "currency": "EUR",
            "reward_minor_units": 100 if accepted else 0,
        }
    if attempt_manifest:
        record["attempt_manifest"] = attempt_manifest.to_dict()
    if trace_manifest:
        record["trace_manifest"] = trace_manifest.to_dict()
    if episode_package:
        record["episode_package"] = episode_package.to_dict()
    return record


def _issue_fields(report) -> set[object]:
    return {issue["field"] for issue in report.issues}


def test_pr_only_attempt_validates_as_low_evidence_not_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path))

    assert report.quality_tier == "pr_only"
    assert report.usable_for_audit is True
    assert report.is_rl_grade is False
    assert report.usable_for_supervised_training is False


def test_manifest_backed_attempt_is_supervised_not_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path, manifest=True))

    assert report.quality_tier == "manifest"
    assert report.usable_for_supervised_training is True
    assert report.usable_for_attempt_quality_prediction is True
    assert report.is_rl_grade is False


def test_trace_backed_attempt_validates_as_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path, manifest=True, trace=True))

    assert report.quality_tier == "trace"
    assert report.is_rl_grade is True
    assert report.accepted_positive is True


def test_replayable_episode_package_is_highest_tier(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path, episode=True))

    assert report.quality_tier == "episode"
    assert report.evidence_level == 4
    assert report.is_rl_grade is True


def test_missing_reward_signal_makes_trace_non_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path, manifest=True, trace=True, reward=False))

    assert report.is_rl_grade is False
    assert "reward_signal" in _issue_fields(report)


def test_missing_process_evidence_makes_successful_pr_non_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(_record(tmp_path, manifest=True))

    assert report.is_rl_grade is False
    assert "process_evidence" in _issue_fields(report)


def test_redacted_trace_can_still_be_rl_grade(tmp_path: Path) -> None:
    report = validate_trajectory_quality(
        _record(tmp_path, manifest=True, trace=True, redacted=True)
    )

    assert report.is_rl_grade is True
    assert report.process_evidence.trace_completeness.redacted is True


def test_task_requiring_rl_grade_rejects_pr_only_for_full_eligibility(tmp_path: Path) -> None:
    requirement = TrajectoryRequirement(
        minimum_quality_tier="trace",
        require_rl_grade=True,
        require_training_eligible=True,
        full_payout_minimum_tier="trace",
        bonus_minimum_tier="episode",
    )

    report = validate_trajectory_quality(_record(tmp_path, requirement=requirement))

    assert report.meets_requirement is False
    assert report.full_payout_eligible is False
    assert report.bonus_eligible is False
    assert "trajectory_requirement" in _issue_fields(report)


def test_training_ineligible_trajectory_is_not_exported_by_default(tmp_path: Path) -> None:
    eligible = _record(tmp_path, manifest=True, trace=True, consent_allowed=True)
    ineligible = _record(tmp_path, manifest=True, trace=True, consent_allowed=False)
    ineligible["id"] = "trajectory_training_denied"
    out_path = tmp_path / "training.jsonl"

    manifest = export_trajectories_jsonl(
        [eligible, ineligible],
        out_path,
        require_rl_grade=True,
        require_training_eligible=True,
    )
    exported = read_trajectory_jsonl(out_path)

    assert manifest.record_count == 1
    assert [record["id"] for record in exported] == ["trajectory_accepted"]
    assert exported[0]["trajectory_quality"]["is_rl_grade"] is True


def test_failed_trajectory_is_rl_useful_negative_process_data(tmp_path: Path) -> None:
    report = validate_trajectory_quality(
        _record(tmp_path, manifest=True, trace=True, accepted=False)
    )

    assert report.is_rl_grade is True
    assert report.accepted_positive is False
    assert report.failed_negative_useful is True
