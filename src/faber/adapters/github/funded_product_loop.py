"""Complete local funded-task loop built from fake GitHub adapter payloads."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from faber.adapters.github.contracts import issue_to_task_contract, pull_request_to_attempt
from faber.adapters.github.events import (
    GitHubEvent,
    GitHubIssueRef,
    GitHubPullRequestRef,
    normalize_github_event,
)
from faber.adapters.github.installation import GitHubInstallation
from faber.adapters.github.markers import (
    render_contract_marker,
    render_funded_issue_marker,
)
from faber.adapters.github.publisher import render_receipt_publication_body
from faber.attempts import Attempt
from faber.budget_ledger import (
    BudgetReconciliationReport,
    BudgetRelease,
    BudgetSettlement,
    WorkBudgetLedger,
)
from faber.budgets import (
    BudgetEvent,
    FundingSource,
    RefundPolicy,
    WorkBudget,
    allocate_budget_to_task,
    issue_work_budget,
)
from faber.canonical_json import canonical_json
from faber.contracts import TaskContract
from faber.datasets import DatasetManifest, export_trajectories_jsonl
from faber.digests import sha256_digest
from faber.errors import SettlementError, ValidationError
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.risk import (
    TaskRiskReview,
    require_task_risk_readiness,
    review_task_risk,
)
from faber.sources import ArtifactReference
from faber.traces import (
    AttemptManifest,
    RedactionPolicy,
    TraceEvent,
    TraceManifest,
    TrajectoryConsent,
    trace_manifest_from_events,
)
from faber.trajectory_quality import (
    TrajectoryRequirement,
    TrajectoryValidationReport,
    validate_trajectory_quality,
)
from faber.verifiers import VerifierRun

CREATED_AT = "2026-07-09T00:00:00Z"
REPOSITORY = "fake-maintainer/faber-demo"
ISSUE_NUMBER = 65
PULL_REQUEST_NUMBER = 165
VERIFIER_ID = "verifier.fake-github.authoritative"
WORKER_ID = "worker.fake-github.solver"


class FakeGitHubDeliveryLedger:
    """Idempotent local inbox for webhook-shaped fake deliveries."""

    def __init__(self) -> None:
        self._events: dict[str, GitHubEvent] = {}
        self._payload_digests: dict[str, str] = {}
        self.attempt_count = 0

    def record(
        self,
        event_name: str,
        payload: dict[str, object],
        *,
        delivery_id: str,
    ) -> GitHubEvent:
        self.attempt_count += 1
        if not delivery_id:
            raise ValidationError("delivery_id must be a non-empty string")
        payload_digest = sha256_digest({"event_name": event_name, "payload": payload})
        existing = self._events.get(delivery_id)
        if existing is not None:
            if self._payload_digests[delivery_id] != payload_digest:
                raise ValidationError("GitHub delivery id reused with different payload")
            return existing
        event = normalize_github_event(event_name, payload, delivery_id=delivery_id)
        self._events[delivery_id] = event
        self._payload_digests[delivery_id] = payload_digest
        return event

    def events(self) -> list[GitHubEvent]:
        return [self._events[key] for key in sorted(self._events)]


@dataclass(frozen=True)
class FakeGitHubFundedProductLoopResult:
    contract: TaskContract
    budget: WorkBudget
    risk_review: TaskRiskReview
    issue_text: str
    pr_file_map: dict[str, str]
    artifact_references: list[ArtifactReference]
    attempt: Attempt
    attempt_manifest: AttemptManifest
    trace_events: list[TraceEvent]
    trace_manifest: TraceManifest | None
    verifier_run: VerifierRun
    receipt: VerificationReceipt
    budget_settlement: BudgetSettlement | None
    budget_release: BudgetRelease | None
    settlement_blocked_reason: str | None
    quality_report: TrajectoryValidationReport
    trajectory_record: dict[str, object]
    dataset_manifest: DatasetManifest
    reconciliation: BudgetReconciliationReport
    budget_events: list[BudgetEvent]
    delivery_attempt_count: int
    delivery_count: int
    budget_operation_attempt_count: int
    maintainer_message: str


def run_fake_github_funded_product_loop(
    dataset_path: str | Path,
    *,
    include_trace: bool = True,
    training_consent: bool = True,
    verifier_passed: bool = True,
) -> FakeGitHubFundedProductLoopResult:
    """Run the complete offline product loop and export eligible training data."""

    installation = _installation()
    issue = _issue()
    contract = _contract(issue, installation)
    funding_source, budget = _budget(contract)
    risk_review = review_task_risk(
        contract,
        review_id="task-risk-review_fake_github_65",
        created_at=CREATED_AT,
    )
    require_task_risk_readiness(risk_review, funding=True, execution=True)
    issue_text = _issue_text(contract, budget, funding_source)

    delivery_ledger = FakeGitHubDeliveryLedger()
    issue_payload = _issue_payload(issue_text)
    delivery_ledger.record("issues", issue_payload, delivery_id="delivery-fake-issue-65")
    delivery_ledger.record("issues", issue_payload, delivery_id="delivery-fake-issue-65")

    pull_request = _pull_request()
    attempt_manifest = _attempt_manifest(
        contract,
        pull_request,
        include_trace=include_trace,
        training_consent=training_consent,
    )
    trace_events = _trace_events(attempt_manifest.attempt_id) if include_trace else []
    trace_manifest = (
        _trace_manifest(attempt_manifest.attempt_id, trace_events) if include_trace else None
    )
    pr_file_map, artifacts = _pr_artifacts(attempt_manifest, trace_events, trace_manifest)
    pr_payload = _pull_request_payload(pull_request)
    delivery_ledger.record(
        "pull_request",
        pr_payload,
        delivery_id="delivery-fake-pr-165",
    )
    delivery_ledger.record(
        "pull_request",
        pr_payload,
        delivery_id="delivery-fake-pr-165",
    )
    attempt = pull_request_to_attempt(
        pull_request,
        contract=contract,
        installation=installation,
        worker_id=WORKER_ID,
        patch_digest=sha256_digest("fake focused patch"),
        check_summaries=[{"name": "fake candidate CI", "conclusion": "success"}],
        file_map=pr_file_map,
    )
    attempt = replace(
        attempt,
        created_at=CREATED_AT,
        metadata={
            **attempt.metadata,
            "artifact_references": [artifact.to_dict() for artifact in artifacts],
            "trace_artifact_present": trace_manifest is not None,
        },
    )

    verifier_run = _verifier_run(verifier_passed)
    receipt = replace(
        VerificationReceipt.from_verifier_run(contract, attempt, verifier_run),
        id="verification-receipt_fake_github_165",
        created_at=CREATED_AT,
    )
    trajectory_record = _trajectory_record(
        contract=contract,
        attempt=attempt,
        attempt_manifest=attempt_manifest,
        trace_manifest=trace_manifest,
        verifier_run=verifier_run,
        receipt=receipt,
    )
    quality_report = validate_trajectory_quality(
        trajectory_record,
        report_id="trajectory-validation-report_fake_github_165",
        created_at=CREATED_AT,
    )

    budget_ledger = WorkBudgetLedger(clock=lambda: CREATED_AT)
    budget_operation_attempt_count = 0
    for _ in range(2):
        budget_operation_attempt_count += 1
        budget_ledger.register_budget(budget, idempotency_key="github:budget:65")
    reserved_amount = Money("EUR", 4000 if include_trace else 3500)
    allocation = replace(
        allocate_budget_to_task(
            budget,
            contract,
            amount=Money("EUR", 4000),
            purpose="solver_payout",
            trace_quality_bonus_policy={"minimum_quality_tier": "trace"},
        ),
        id="budget-allocation_fake_github_65",
        created_at=CREATED_AT,
    )
    reservations = []
    for _ in range(2):
        budget_operation_attempt_count += 1
        reservations.append(
            budget_ledger.reserve(
                allocation,
                attempt_id=attempt.id,
                amount=reserved_amount,
                idempotency_key="github:reservation:pr-165",
            )
        )
    reservation = reservations[0]
    budget_settlement: BudgetSettlement | None = None
    budget_release: BudgetRelease | None = None
    settlement_blocked_reason: str | None = None
    splits = _settlement_splits(include_trace=include_trace)
    if receipt.accepted:
        settlements = []
        for _ in range(2):
            budget_operation_attempt_count += 1
            settlements.append(
                budget_ledger.settle(
                    reservation,
                    receipt,
                    splits=splits,
                    trajectory_quality=quality_report.to_dict(),
                    idempotency_key="github:settlement:pr-165",
                )
            )
        budget_settlement = settlements[0]
    else:
        budget_operation_attempt_count += 1
        try:
            budget_ledger.settle(
                reservation,
                receipt,
                splits=splits,
                trajectory_quality=quality_report.to_dict(),
                idempotency_key="github:settlement:pr-165",
            )
        except SettlementError as exc:
            settlement_blocked_reason = str(exc)
        releases = []
        for _ in range(2):
            budget_operation_attempt_count += 1
            releases.append(
                budget_ledger.release_rejected(
                    reservation,
                    receipt,
                    refund_policy=budget.refund_policy,
                    idempotency_key="github:release:pr-165",
                )
            )
        budget_release = releases[0]

    if budget_settlement is not None:
        settlement_payload = budget_settlement.to_dict()
        settlement_payload["amount"] = Money("EUR", budget_settlement.total_minor_units).to_dict()
        settlement_payload["status"] = "settled_locally"
        trajectory_record["settlement"] = settlement_payload
    if budget_release is not None:
        trajectory_record["budget_release"] = budget_release.to_dict()
    quality_report = validate_trajectory_quality(
        trajectory_record,
        report_id="trajectory-validation-report_fake_github_165",
        created_at=CREATED_AT,
    )
    dataset_manifest = export_trajectories_jsonl(
        [trajectory_record],
        dataset_path,
        dataset_id="dataset_fake_github_funded_loop",
        source_paths=["fake-github://issue/65", "fake-github://pull/165"],
        require_rl_grade=True,
        require_training_eligible=True,
    )
    reconciliation = budget_ledger.reconcile(budget.id)
    maintainer_message = _maintainer_message(
        receipt,
        quality_report,
        budget_settlement,
        budget_release,
    )
    return FakeGitHubFundedProductLoopResult(
        contract=contract,
        budget=budget,
        risk_review=risk_review,
        issue_text=issue_text,
        pr_file_map=pr_file_map,
        artifact_references=artifacts,
        attempt=attempt,
        attempt_manifest=attempt_manifest,
        trace_events=trace_events,
        trace_manifest=trace_manifest,
        verifier_run=verifier_run,
        receipt=receipt,
        budget_settlement=budget_settlement,
        budget_release=budget_release,
        settlement_blocked_reason=settlement_blocked_reason,
        quality_report=quality_report,
        trajectory_record=trajectory_record,
        dataset_manifest=dataset_manifest,
        reconciliation=reconciliation,
        budget_events=budget_ledger.events(),
        delivery_attempt_count=delivery_ledger.attempt_count,
        delivery_count=len(delivery_ledger.events()),
        budget_operation_attempt_count=budget_operation_attempt_count,
        maintainer_message=maintainer_message,
    )


def _installation() -> GitHubInstallation:
    return GitHubInstallation(
        installation_id=65001,
        account_login="fake-maintainer",
        selected_repository_full_names=[REPOSITORY],
        permissions={"issues": "read", "pull_requests": "read", "checks": "read"},
    )


def _issue() -> GitHubIssueRef:
    return GitHubIssueRef(
        repository_full_name=REPOSITORY,
        issue_number=ISSUE_NUMBER,
        title="Keep the greeting formatter deterministic",
        body=(
            "Update the local greeting formatter and its focused tests. No network, "
            "credentials, private data, or real payment provider is involved."
        ),
        labels=["faber", "funded", "training-eligible"],
        author_login="fake-maintainer",
        html_url=f"https://github.example/{REPOSITORY}/issues/{ISSUE_NUMBER}",
    )


def _contract(issue: GitHubIssueRef, installation: GitHubInstallation) -> TaskContract:
    adapted = issue_to_task_contract(
        issue,
        installation=installation,
        verifier_ids=[VERIFIER_ID],
    )
    requirement = TrajectoryRequirement(
        id="trajectory-requirement_fake_github_65",
        created_at=CREATED_AT,
        minimum_quality_tier="manifest",
        require_training_eligible=False,
        require_rl_grade=False,
        full_payout_minimum_tier="trace",
        bonus_minimum_tier="trace",
        notes=(
            "Training consent is optional. Trace evidence controls full payout and "
            "the quality bonus; settlement always requires authoritative verification."
        ),
    )
    return replace(
        adapted,
        id="task-contract_fake_github_65",
        created_at=CREATED_AT,
        requirements=[
            "Resolve fake GitHub issue #65.",
            "Pass the platform-owned focused verifier.",
            "Attach .faber/attempt.json; attach trace artifacts for full evidence.",
        ],
        environment={
            **adapted.environment,
            "repository_snapshot": "fake-base-sha",
            "external_services": [],
            "fake_data": True,
            "risk": {
                "external_action": {
                    "external_writes": False,
                    "external_services": [],
                    "action_kinds": [],
                },
                "credential": {"required": False, "credential_types": []},
                "private_data": {"required": False, "data_classes": []},
                "regulated_domain": {"required": False, "domains": []},
                "security_sensitive": {"required": False, "areas": []},
            },
        },
        trajectory_requirement=requirement.to_dict(),
        reward=Money("EUR", 4000),
    )


def _budget(contract: TaskContract) -> tuple[FundingSource, WorkBudget]:
    source = FundingSource(
        id="funding-source_fake_github_65",
        created_at=CREATED_AT,
        source_type="fake-local",
        display_name="Fake local product-loop funds",
        currency="EUR",
        provider_ref=None,
        metadata={"fake_data": True, "funds_committed": False},
    )
    budget = issue_work_budget(
        repository=REPOSITORY,
        issue_number=ISSUE_NUMBER,
        funding_source=source,
        amount=Money("EUR", 5000),
        verifier_policy={"required_verifier_ids": contract.verifier_ids},
        purpose_allocations={
            "solver_payout": Money("EUR", 4000),
            "verifier_spend": Money("EUR", 500),
            "trace_quality_bonus": Money("EUR", 500),
        },
        refund_policy=RefundPolicy(
            id="refund-policy_fake_github_65",
            created_at=CREATED_AT,
            on_rejected="refund_to_source",
            on_expired="manual_review",
            on_cancelled="manual_review",
            notes="Fake local policy with no custody or payment provider.",
        ),
    )
    return source, replace(
        budget,
        id="work-budget_fake_github_65",
        created_at=CREATED_AT,
        metadata={**budget.metadata, "fake_data": True, "funds_committed": False},
    )


def _issue_text(
    contract: TaskContract,
    budget: WorkBudget,
    source: FundingSource,
) -> str:
    return "\n\n".join(
        [
            "## Faber local pilot\n\nA focused, fully local task with reviewable evidence.",
            render_contract_marker(contract),
            render_funded_issue_marker(
                contract,
                budget,
                funding_source_ref=source.id,
                budget_allocation_policy={
                    "scope": "github.issue",
                    "reservation_required": True,
                },
                trace_quality_bonus_policy={"minimum_quality_tier": "trace"},
            ),
        ]
    )


def _pull_request() -> GitHubPullRequestRef:
    return GitHubPullRequestRef(
        repository_full_name=REPOSITORY,
        pull_request_number=PULL_REQUEST_NUMBER,
        title="Fix deterministic greeting formatting",
        body=(
            "Focused fake patch with `.faber/attempt.json` and redacted trace "
            "artifacts attached for local verification."
        ),
        author_login="fake-solver",
        base_revision="fake-base-sha",
        head_revision="fake-candidate-sha",
        html_url=f"https://github.example/{REPOSITORY}/pull/{PULL_REQUEST_NUMBER}",
    )


def _attempt_manifest(
    contract: TaskContract,
    pull_request: GitHubPullRequestRef,
    *,
    include_trace: bool,
    training_consent: bool,
) -> AttemptManifest:
    consent = (
        TrajectoryConsent(
            id="trajectory-consent_fake_github_165",
            created_at=CREATED_AT,
            training_use_allowed=True,
            allowed_uses=["rl", "supervised", "router"],
            license_ref="fake-fixture-only",
            redaction_required=True,
            notes="Synthetic product-loop fixture; no private trace data.",
        )
        if training_consent
        else None
    )
    return AttemptManifest(
        id="attempt-manifest_fake_github_165",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id="attempt_fake_github_165",
        base_revision=pull_request.base_revision,
        candidate_revision=pull_request.head_revision,
        worker_id=WORKER_ID,
        evidence_level=2 if include_trace else 1,
        redaction_policy=_redaction_policy(),
        model_metadata={"family": "fake-code-solver", "disclosure": "synthetic"},
        harness_metadata={"family": "fake-local-harness", "version": "1"},
        runner_metadata={"runner": "fake-local-runner", "version": "1"},
        environment_metadata={
            "platform": "windows",
            "reproducibility_level": "lockfile",
            "repository_snapshot_digest": sha256_digest("fake repository snapshot"),
            "dependency_lock_digest": sha256_digest("fake requirements lock"),
            "fake_data": True,
        },
        tool_registry_digest=sha256_digest(["read", "edit", "pytest"]),
        budget_metadata={"currency": "EUR", "budget_minor_units": 5000},
        cost_metadata={"currency": "EUR", "compute_minor_units": 100},
        latency_metadata={"work_seconds": 45},
        training_consent=consent,
        trust_level="runner_attested",
    )


def _redaction_policy() -> RedactionPolicy:
    return RedactionPolicy(
        id="redaction-policy_fake_github_165",
        created_at=CREATED_AT,
        name="Fake GitHub product-loop redaction",
        field_paths=["payload.private_prompt", "payload.credentials"],
        allow_raw_trace=False,
    )


def _trace_events(attempt_id: str) -> list[TraceEvent]:
    event_data: list[tuple[str, dict[str, object]]] = [
        ("context.loaded", {"issue": ISSUE_NUMBER, "source": "fake-github"}),
        ("tool.call", {"tool": "pytest", "args": ["tests/test_greeting.py"]}),
        ("verification.result", {"verifier_id": VERIFIER_ID, "passed": True}),
        ("outcome.reported", {"status": "accepted", "reward_minor_units": 4000}),
    ]
    return [
        TraceEvent(
            id=f"trace-event_fake_github_165_{sequence:04d}",
            created_at=CREATED_AT,
            attempt_id=attempt_id,
            sequence=sequence,
            event_type=event_type,
            observed_at=CREATED_AT,
            payload=payload,
            trust_level="runner_attested",
            provenance={"adapter": "fake-github", "source": "synthetic"},
        )
        for sequence, (event_type, payload) in enumerate(event_data)
    ]


def _trace_manifest(attempt_id: str, events: list[TraceEvent]) -> TraceManifest:
    return trace_manifest_from_events(
        attempt_id=attempt_id,
        events=events,
        evidence_level_value=2,
        trace_jsonl_digest=sha256_digest([event.to_dict() for event in events]),
        trust_level="runner_attested",
        redaction_policy=_redaction_policy(),
        raw_trace_digest=sha256_digest("fake raw trace"),
        provenance={"adapter": "fake-github", "source": "synthetic"},
        privacy_notes="Synthetic and redacted fixture trace.",
        manifest_id="trace-manifest_fake_github_165",
        created_at=CREATED_AT,
    )


def _pr_artifacts(
    manifest: AttemptManifest,
    events: list[TraceEvent],
    trace_manifest: TraceManifest | None,
) -> tuple[dict[str, str], list[ArtifactReference]]:
    manifest_text = canonical_json(manifest.to_dict())
    file_map = {".faber/attempt.json": manifest_text}
    artifacts = [
        _artifact("artifact-reference_fake_github_attempt", ".faber/attempt.json", manifest_text)
    ]
    if trace_manifest is not None:
        trace_text = "\n".join(canonical_json(event.to_dict()) for event in events) + "\n"
        trace_manifest_text = canonical_json(trace_manifest.to_dict())
        file_map[".faber/trace.jsonl"] = trace_text
        file_map[".faber/trace-manifest.json"] = trace_manifest_text
        artifacts.extend(
            [
                _artifact(
                    "artifact-reference_fake_github_trace",
                    ".faber/trace.jsonl",
                    trace_text,
                    media_type="application/x-ndjson",
                ),
                _artifact(
                    "artifact-reference_fake_github_trace_manifest",
                    ".faber/trace-manifest.json",
                    trace_manifest_text,
                ),
            ]
        )
    return file_map, artifacts


def _artifact(
    artifact_id: str,
    path: str,
    content: str,
    *,
    media_type: str = "application/json",
) -> ArtifactReference:
    return ArtifactReference(
        id=artifact_id,
        kind="file",
        locator=path,
        digest=sha256_digest(content.encode("utf-8")),
        media_type=media_type,
        metadata={"adapter": "fake-github", "source": "pull_request_file_map"},
    )


def _verifier_run(passed: bool) -> VerifierRun:
    return VerifierRun(
        id="verifier-run_fake_github_165",
        created_at=CREATED_AT,
        verifier_id=VERIFIER_ID,
        name="Fake platform-owned greeting verifier",
        version="1",
        command=["python", "-m", "pytest", "tests/test_greeting.py"],
        passed=passed,
        metrics={"tests": 3, "failures": 0 if passed else 1},
        failure_reasons=[] if passed else ["focused greeting verifier failed"],
        logs_digest=sha256_digest(
            {"fixture": "fake-github", "passed": passed, "logs": "synthetic"}
        ),
        metadata={"authority": "platform-owned", "fake_data": True},
    )


def _trajectory_record(
    *,
    contract: TaskContract,
    attempt: Attempt,
    attempt_manifest: AttemptManifest,
    trace_manifest: TraceManifest | None,
    verifier_run: VerifierRun,
    receipt: VerificationReceipt,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": "faber.trajectory.v1",
        "id": "trajectory_fake_github_165",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "attempt_manifest": attempt_manifest.to_dict(),
        "verifier_run": verifier_run.to_dict(),
        "receipt": receipt.to_dict(),
        "router_decision": {
            "policy_name": "fake-local-fixed-worker",
            "selected_worker_id": attempt.worker_id,
        },
        "reward_metadata": {
            "currency": "EUR",
            "reward_minor_units": 4000 if receipt.accepted else 0,
        },
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 100},
        "latency_metadata": {"work_seconds": 45, "verification_seconds": 2},
        "review_metadata": {"human_reviewed": False, "source": "fake-github"},
        "outcome": "accepted" if receipt.accepted else "rejected",
    }
    if trace_manifest is not None:
        record["trace_manifest"] = trace_manifest.to_dict()
    return record


def _settlement_splits(*, include_trace: bool) -> dict[str, Money]:
    if include_trace:
        return {
            "worker": Money("EUR", 3500),
            "verifier": Money("EUR", 300),
            "trace_quality_bonus": Money("EUR", 200),
        }
    return {"worker": Money("EUR", 3000), "verifier": Money("EUR", 500)}


def _maintainer_message(
    receipt: VerificationReceipt,
    quality: TrajectoryValidationReport,
    settlement: BudgetSettlement | None,
    release: BudgetRelease | None,
) -> str:
    lines = [render_receipt_publication_body(receipt), "", "Local pilot summary:"]
    lines.append(f"- Evidence tier: {quality.quality_tier}")
    lines.append(f"- RL-grade and training-eligible: {'yes' if quality.is_rl_grade else 'no'}")
    if settlement is not None:
        lines.append(
            f"- Local ledger: {settlement.total_minor_units} EUR minor units settled; "
            "no payment provider was called."
        )
        lines.append("- Next step: review the focused patch and its authoritative receipt.")
    elif release is not None:
        lines.append("- Local ledger: reservation released after verifier rejection.")
        lines.append("- Next step: inspect the focused verifier failure before another attempt.")
    else:
        lines.append("- Local ledger: no settlement action recorded.")
    return "\n".join(lines)


def _issue_payload(issue_text: str) -> dict[str, object]:
    return {
        "action": "opened",
        "repository": {"full_name": REPOSITORY},
        "issue": {"number": ISSUE_NUMBER, "body": issue_text},
    }


def _pull_request_payload(pull_request: GitHubPullRequestRef) -> dict[str, object]:
    return {
        "action": "opened",
        "repository": {"full_name": REPOSITORY},
        "pull_request": {
            "number": pull_request.pull_request_number,
            "body": pull_request.body,
            "base": {"sha": pull_request.base_revision},
            "head": {"sha": pull_request.head_revision},
        },
    }
