"""Offline benchmark fixtures for local agent harness evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.settlement import Settlement
from faber.traces import (
    AttemptManifest,
    RedactionPolicy,
    TraceEvent,
    TraceManifest,
    trace_manifest_from_events,
)
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRun, VerifierSpec
from faber.workers import WorkerProfile

BENCHMARK_ID = "agent-harness-offline-benchmark-v1"
CREATED_AT = "2026-01-01T00:00:00Z"
REPOSITORY = "local/faber-agent-harness-benchmark"


@dataclass(frozen=True)
class BenchmarkTaskFixture:
    """Complete local benchmark fixture for one tiny software task."""

    slug: str
    contract: TaskContract
    verifier_spec: VerifierSpec
    attempt_manifest: AttemptManifest
    expected_trace_events: list[TraceEvent]
    expected_trace_manifest: TraceManifest
    trajectory: Trajectory

    def dataset_record(self) -> dict[str, object]:
        """Return a trajectory record annotated with benchmark fixture metadata."""

        record = self.trajectory.to_dict()
        record["benchmark"] = {
            "id": BENCHMARK_ID,
            "task_slug": self.slug,
            "verifier_spec": self.verifier_spec.to_dict(),
            "attempt_manifest": self.attempt_manifest.to_dict(),
            "trace_manifest": self.expected_trace_manifest.to_dict(),
            "expected_trace_event_count": len(self.expected_trace_events),
        }
        return record


def benchmark_dev_environment() -> dict[str, object]:
    """Return the local benchmark environment contract."""

    return {
        "flake_path": "flake.nix",
        "dev_shell": "default",
        "fallback_commands": [
            "python -m pytest",
            "python -m ruff check .",
            "python -m mypy src",
        ],
        "external_services": [],
    }


def agent_harness_benchmark() -> list[BenchmarkTaskFixture]:
    """Build the deterministic offline benchmark task fixtures."""

    return [
        _build_fixture(
            slug="canonical-json",
            title="Preserve canonical JSON digests",
            description="Keep stable JSON ordering and digest formatting intact.",
            requirements=[
                "Run the canonical JSON tests locally.",
                "Do not contact external services.",
                "Attach an attempt manifest and trace summary.",
            ],
            verifier_id="verifier.benchmark.canonical-json",
            verifier_name="Canonical JSON unit tests",
            verifier_command=["python", "-m", "pytest", "tests/test_canonical_json.py"],
            patch_summary="Confirmed canonical serialization remains deterministic.",
            metrics={"tests": 1, "failures": 0},
        ),
        _build_fixture(
            slug="trace-redaction",
            title="Preserve trace redaction behavior",
            description="Keep explicit trace redaction stable across JSONL export.",
            requirements=[
                "Run the trace protocol tests locally.",
                "Verify private fields are replaced by the configured marker.",
                "Attach an attempt manifest and trace summary.",
            ],
            verifier_id="verifier.benchmark.trace-redaction",
            verifier_name="Trace redaction unit tests",
            verifier_command=["python", "-m", "pytest", "tests/test_traces_protocol.py"],
            patch_summary="Confirmed trace JSONL redaction and manifests remain stable.",
            metrics={"tests": 6, "failures": 0},
        ),
        _build_fixture(
            slug="budget-accounting",
            title="Preserve budget accounting invariants",
            description="Keep funded work reservations and receipt-gated payout rules intact.",
            requirements=[
                "Run the work budget tests locally.",
                "Verify money stays in integer minor units.",
                "Attach an attempt manifest and trace summary.",
            ],
            verifier_id="verifier.benchmark.budget-accounting",
            verifier_name="Work budget invariant tests",
            verifier_command=["python", "-m", "pytest", "tests/test_work_budgets.py"],
            patch_summary="Confirmed budget reservation and payout invariants remain stable.",
            metrics={"tests": 6, "failures": 0},
        ),
    ]


def validate_agent_harness_benchmark(
    fixtures: list[BenchmarkTaskFixture] | None = None,
) -> list[str]:
    """Return validation errors for the offline benchmark fixtures."""

    task_fixtures = fixtures if fixtures is not None else agent_harness_benchmark()
    errors: list[str] = []
    if not 3 <= len(task_fixtures) <= 5:
        errors.append("benchmark must contain 3 to 5 tasks")
    seen_contract_ids: set[str] = set()
    for fixture in task_fixtures:
        _validate_fixture(fixture, seen_contract_ids, errors)
    return errors


def agent_harness_dataset_records() -> list[dict[str, object]]:
    """Return dataset-ready benchmark trajectory records."""

    return [fixture.dataset_record() for fixture in agent_harness_benchmark()]


def _build_fixture(
    *,
    slug: str,
    title: str,
    description: str,
    requirements: list[str],
    verifier_id: str,
    verifier_name: str,
    verifier_command: list[str],
    patch_summary: str,
    metrics: dict[str, object],
) -> BenchmarkTaskFixture:
    contract = _task_contract(slug, title, description, requirements, verifier_id)
    verifier_spec = _verifier_spec(slug, verifier_id, verifier_name, verifier_command)
    redaction_policy = _redaction_policy(slug)
    attempt_manifest = _attempt_manifest(slug, contract, redaction_policy)
    trace_events = _trace_events(slug, attempt_manifest, verifier_id)
    trace_digest = sha256_digest([event.to_dict() for event in trace_events])
    trace_manifest = trace_manifest_from_events(
        attempt_id=attempt_manifest.attempt_id,
        events=trace_events,
        evidence_level_value=3,
        trace_jsonl_digest=trace_digest,
        trust_level="self_attested",
        redaction_policy=redaction_policy,
        raw_trace_digest=sha256_digest({"benchmark": BENCHMARK_ID, "task": slug}),
        provenance={
            "benchmark_id": BENCHMARK_ID,
            "task_slug": slug,
            "source": "expected_trace_fixture",
        },
        manifest_id=f"trace-manifest_benchmark_{slug}",
        created_at=CREATED_AT,
    )
    trajectory = _trajectory(
        slug=slug,
        contract=contract,
        verifier_spec=verifier_spec,
        attempt_manifest=attempt_manifest,
        trace_manifest=trace_manifest,
        patch_summary=patch_summary,
        metrics=metrics,
    )
    return BenchmarkTaskFixture(
        slug=slug,
        contract=contract,
        verifier_spec=verifier_spec,
        attempt_manifest=attempt_manifest,
        expected_trace_events=trace_events,
        expected_trace_manifest=trace_manifest,
        trajectory=trajectory,
    )


def _task_contract(
    slug: str,
    title: str,
    description: str,
    requirements: list[str],
    verifier_id: str,
) -> TaskContract:
    environment = benchmark_dev_environment()
    return TaskContract(
        id=f"task-contract_benchmark_{slug}",
        created_at=CREATED_AT,
        title=title,
        description=description,
        requirements=requirements,
        verifier_ids=[verifier_id],
        task_source="agent_harness_benchmark",
        repository=REPOSITORY,
        environment={
            "benchmark_id": BENCHMARK_ID,
            "required_platforms": ["nixos"],
            "dev_environment": environment,
            "external_services": [],
        },
        reward=Money("EUR", 1000),
    )


def _verifier_spec(
    slug: str,
    verifier_id: str,
    verifier_name: str,
    verifier_command: list[str],
) -> VerifierSpec:
    return VerifierSpec(
        id=f"verifier-spec_benchmark_{slug}",
        created_at=CREATED_AT,
        verifier_id=verifier_id,
        name=verifier_name,
        version="1",
        description="Local offline benchmark verifier.",
        command_template=verifier_command,
        allowed_timeout_seconds=60,
    )


def _redaction_policy(slug: str) -> RedactionPolicy:
    return RedactionPolicy(
        id=f"redaction-policy_benchmark_{slug}",
        created_at=CREATED_AT,
        name=f"Benchmark redaction for {slug}",
        field_paths=["context.private_prompt", "credentials.api_key"],
        allow_raw_trace=False,
    )


def _attempt_manifest(
    slug: str,
    contract: TaskContract,
    redaction_policy: RedactionPolicy,
) -> AttemptManifest:
    return AttemptManifest(
        id=f"attempt-manifest_benchmark_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=f"attempt_benchmark_{slug}",
        base_revision="benchmark-base",
        candidate_revision=f"benchmark-candidate-{slug}",
        worker_id="worker_agent_harness_benchmark",
        evidence_level=3,
        redaction_policy=redaction_policy,
        model_metadata={"disclosure": "private", "provider_class": "none"},
        harness_metadata={"benchmark_id": BENCHMARK_ID, "harness_family": "local"},
        runner_metadata={"runner": "local-benchmark-runner", "version": "1"},
        environment_metadata=benchmark_dev_environment(),
        tool_registry_digest=sha256_digest({"benchmark": BENCHMARK_ID, "task": slug, "tools": []}),
        cost_metadata={"currency": "EUR", "compute_minor_units": 0},
        latency_metadata={"work_seconds": 60},
        trust_level="self_attested",
    )


def _trace_events(
    slug: str,
    attempt_manifest: AttemptManifest,
    verifier_id: str,
) -> list[TraceEvent]:
    attempt_id = attempt_manifest.attempt_id
    base_provenance: dict[str, object] = {
        "benchmark_id": BENCHMARK_ID,
        "task_slug": slug,
        "source": "expected_trace_fixture",
    }
    return [
        TraceEvent(
            id=f"trace-event_benchmark_{slug}_0000",
            created_at=CREATED_AT,
            attempt_id=attempt_id,
            sequence=0,
            event_type="context.loaded",
            observed_at=CREATED_AT,
            payload={
                "task_contract_id": attempt_manifest.task_contract_id,
                "context": {"private_prompt": "fixture-private-plan", "public_summary": slug},
            },
            provenance=base_provenance,
        ),
        TraceEvent(
            id=f"trace-event_benchmark_{slug}_0001",
            created_at=CREATED_AT,
            attempt_id=attempt_id,
            sequence=1,
            event_type="tool.call",
            observed_at=CREATED_AT,
            payload={"tool": "pytest", "verifier_id": verifier_id},
            provenance=base_provenance,
        ),
        TraceEvent(
            id=f"trace-event_benchmark_{slug}_0002",
            created_at=CREATED_AT,
            attempt_id=attempt_id,
            sequence=2,
            event_type="verification.result",
            observed_at=CREATED_AT,
            payload={"verifier_id": verifier_id, "passed": True},
            provenance=base_provenance,
        ),
        TraceEvent(
            id=f"trace-event_benchmark_{slug}_0003",
            created_at=CREATED_AT,
            attempt_id=attempt_id,
            sequence=3,
            event_type="outcome.reported",
            observed_at=CREATED_AT,
            payload={"status": "accepted", "accepted": True},
            provenance=base_provenance,
        ),
    ]


def _trajectory(
    *,
    slug: str,
    contract: TaskContract,
    verifier_spec: VerifierSpec,
    attempt_manifest: AttemptManifest,
    trace_manifest: TraceManifest,
    patch_summary: str,
    metrics: dict[str, object],
) -> Trajectory:
    worker = WorkerProfile(
        id="worker_agent_harness_benchmark",
        created_at=CREATED_AT,
        display_name="Offline Benchmark Worker",
        capabilities=["python", "tests", "trace-jsonl"],
        supported_task_sources=["agent_harness_benchmark"],
        supported_languages=["python"],
        supported_platforms=["nixos", "linux", "windows", "macos"],
        reputation={"accepted_attempts": 3, "rejected_attempts": 0},
    )
    attempt = Attempt(
        id=attempt_manifest.attempt_id,
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id=worker.id,
        base_revision=attempt_manifest.base_revision,
        candidate_revision=attempt_manifest.candidate_revision,
        summary=patch_summary,
        patch_digest=sha256_digest({"benchmark": BENCHMARK_ID, "task": slug, "patch": "fixture"}),
        tool_summaries=[
            {
                "tool": "pytest",
                "outcome": "passed",
                "verifier_id": verifier_spec.verifier_id,
            }
        ],
        metadata={
            "benchmark_id": BENCHMARK_ID,
            "attempt_manifest_digest": attempt_manifest.digest(),
            "trace_manifest_digest": trace_manifest.digest(),
            "evidence_level": 3,
        },
    )
    verifier_run = VerifierRun(
        id=f"verifier-run_benchmark_{slug}",
        created_at=CREATED_AT,
        verifier_id=verifier_spec.verifier_id,
        name=verifier_spec.name,
        version=verifier_spec.version,
        command=verifier_spec.command(),
        passed=True,
        metrics=metrics,
        logs_digest=sha256_digest({"benchmark": BENCHMARK_ID, "task": slug, "logs": "passed"}),
        metadata={"benchmark_id": BENCHMARK_ID, "task_slug": slug},
    )
    receipt = VerificationReceipt(
        id=f"verification-receipt_benchmark_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=worker.id,
        verifier_id=verifier_run.verifier_id,
        verifier_digest=verifier_run.verifier_digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=True,
        metrics=verifier_run.metrics,
        failure_reasons=[],
        result_digest=verifier_run.result_digest(),
    )
    settlement = Settlement(
        id=f"settlement_benchmark_{slug}",
        created_at=CREATED_AT,
        receipt_id=receipt.id,
        worker_id=worker.id,
        amount=Money("EUR", 1000),
        status="paid",
        receipt_accepted=True,
        transaction_ref=f"benchmark-{slug}",
        paid_at=CREATED_AT,
    )
    router_decision = RouterDecision(
        id=f"router-decision_benchmark_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        selected_worker_id=worker.id,
        rejected_alternatives=[],
        estimated_cost=Money("EUR", 0),
        expected_value=Money("EUR", 1000),
        policy_name="offline-benchmark-fixed-worker",
        decision_factors={
            "benchmark_id": BENCHMARK_ID,
            "required_platforms": contract.environment["required_platforms"],
            "external_services": [],
        },
    )
    return Trajectory(
        id=f"trajectory_benchmark_{slug}",
        created_at=CREATED_AT,
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        settlement=settlement,
        router_decision=router_decision,
        worker_profile=worker,
        cost_metadata={"currency": "EUR", "compute_minor_units": 0, "review_minor_units": 0},
        latency_metadata={"queue_seconds": 0, "work_seconds": 60, "verification_seconds": 5},
        review_metadata={"human_reviewed": False, "review_friction": "none"},
    )


def _validate_fixture(
    fixture: BenchmarkTaskFixture,
    seen_contract_ids: set[str],
    errors: list[str],
) -> None:
    if fixture.contract.id in seen_contract_ids:
        errors.append(f"{fixture.slug}: duplicate contract id")
    seen_contract_ids.add(fixture.contract.id)
    if fixture.verifier_spec.verifier_id not in fixture.contract.verifier_ids:
        errors.append(f"{fixture.slug}: verifier spec is not referenced by contract")
    if not fixture.verifier_spec.command_template:
        errors.append(f"{fixture.slug}: verifier command is empty")
    if fixture.contract.environment.get("external_services") != []:
        errors.append(f"{fixture.slug}: benchmark must not require external services")
    dev_environment = fixture.contract.environment.get("dev_environment")
    if not isinstance(dev_environment, dict) or not dev_environment.get("flake_path"):
        errors.append(f"{fixture.slug}: benchmark must declare a flake path")
    if fixture.attempt_manifest.task_contract_id != fixture.contract.id:
        errors.append(f"{fixture.slug}: attempt manifest contract mismatch")
    if fixture.attempt_manifest.task_contract_digest != fixture.contract.digest():
        errors.append(f"{fixture.slug}: attempt manifest contract digest mismatch")
    if fixture.expected_trace_manifest.attempt_id != fixture.attempt_manifest.attempt_id:
        errors.append(f"{fixture.slug}: trace manifest attempt mismatch")
    if fixture.expected_trace_manifest.trace_event_count != len(fixture.expected_trace_events):
        errors.append(f"{fixture.slug}: trace manifest event count mismatch")
    for index, event in enumerate(fixture.expected_trace_events):
        if event.attempt_id != fixture.attempt_manifest.attempt_id:
            errors.append(f"{fixture.slug}: trace event {index} attempt mismatch")
        if event.sequence != index:
            errors.append(f"{fixture.slug}: trace event {index} sequence mismatch")
    if fixture.trajectory.contract.id != fixture.contract.id:
        errors.append(f"{fixture.slug}: trajectory contract mismatch")
    if fixture.trajectory.receipt.accepted is not True:
        errors.append(f"{fixture.slug}: benchmark trajectory should be accepted")


def benchmark_flake_exists(root: str | Path = ".") -> bool:
    """Return whether the declared benchmark flake path exists under root."""

    environment = benchmark_dev_environment()
    flake_path = environment["flake_path"]
    if not isinstance(flake_path, str):
        return False
    return (Path(root) / flake_path).exists()
