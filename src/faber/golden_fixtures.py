"""Deterministic golden fixture corpus for protocol and dataset snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from faber import schemas
from faber.adapters.github.funded_product_loop import run_fake_github_funded_product_loop
from faber.adapters.github.markers import parse_funded_issue_marker
from faber.attempts import Attempt
from faber.canonical_json import canonical_json
from faber.contracts import TaskContract
from faber.datasets import export_trajectories_jsonl
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.money import Money
from faber.platform_fixtures import cross_platform_harness_fixtures
from faber.receipts import VerificationReceipt
from faber.reviews import (
    HumanReviewReceipt,
    ReviewCriterion,
    ReviewFrictionSignal,
)
from faber.schema_registry import protocol_schema_registry
from faber.selection import AdvisoryRankingRecord, CandidateSelectionRecord
from faber.traces import (
    AttemptManifest,
    EpisodePackage,
    RedactionPolicy,
    TraceEvent,
    TrajectoryConsent,
    trace_manifest_from_events,
)
from faber.trajectory_quality import TrajectoryRequirement, validate_trajectory_quality
from faber.verifiers import VerifierRun

CREATED_AT = "2026-01-01T00:00:00Z"
GOLDEN_FIXTURE_NAMES = (
    "trajectory-pr-only",
    "trajectory-manifest",
    "trajectory-rl-trace",
    "trajectory-replayable-episode",
    "funded-github-issue",
    "trajectory-rejected",
    "trajectory-human-reviewed",
    "candidate-pool-advisory-ranked",
    "environment-nixos",
    "environment-cross-platform",
)
TRAJECTORY_FIXTURE_NAMES = (
    "trajectory-pr-only",
    "trajectory-manifest",
    "trajectory-rl-trace",
    "trajectory-replayable-episode",
    "trajectory-rejected",
    "trajectory-human-reviewed",
)


@dataclass(frozen=True)
class GoldenFixture:
    name: str
    payload: dict[str, object]

    @property
    def filename(self) -> str:
        return f"{self.name}.json"

    def canonical_json(self) -> str:
        return canonical_json(self.payload)

    def digest(self) -> str:
        return sha256_digest(self.payload)


def build_golden_fixture_corpus(work_dir: str | Path) -> list[GoldenFixture]:
    """Build all fixture categories from deterministic protocol constructors."""

    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    funded = run_fake_github_funded_product_loop(work_path / "funded-training.jsonl")
    platform_fixtures = cross_platform_harness_fixtures()
    nix_environment = next(
        fixture.environment_evidence
        for fixture in platform_fixtures
        if fixture.platform_family == "nixos"
    )
    windows_environment = next(
        fixture.environment_evidence
        for fixture in platform_fixtures
        if fixture.platform_family == "windows"
    )
    payloads = {
        "trajectory-pr-only": _trajectory_record("pr_only", "pr_only"),
        "trajectory-manifest": _trajectory_record("manifest", "manifest"),
        "trajectory-rl-trace": _trajectory_record("rl_trace", "trace"),
        "trajectory-replayable-episode": _trajectory_record("episode", "episode"),
        "funded-github-issue": parse_funded_issue_marker(funded.issue_text).to_dict(),
        "trajectory-rejected": _trajectory_record(
            "rejected",
            "trace",
            accepted=False,
        ),
        "trajectory-human-reviewed": _trajectory_record(
            "human_reviewed",
            "trace",
            human_reviewed=True,
        ),
        "candidate-pool-advisory-ranked": _candidate_selection_fixture(),
        "environment-nixos": nix_environment.to_dict(),
        "environment-cross-platform": windows_environment.to_dict(),
    }
    return [GoldenFixture(name=name, payload=payloads[name]) for name in GOLDEN_FIXTURE_NAMES]


def validate_golden_fixture_corpus(fixtures: list[GoldenFixture]) -> list[str]:
    """Validate names, schema compatibility, and category-specific invariants."""

    errors: list[str] = []
    names = [fixture.name for fixture in fixtures]
    if names != list(GOLDEN_FIXTURE_NAMES):
        errors.append("golden fixture names or order do not match the documented corpus")
    registry = protocol_schema_registry()
    expected_tiers = {
        "trajectory-pr-only": "pr_only",
        "trajectory-manifest": "manifest",
        "trajectory-rl-trace": "trace",
        "trajectory-replayable-episode": "episode",
        "trajectory-rejected": "trace",
        "trajectory-human-reviewed": "trace",
    }
    for fixture in fixtures:
        schema_id = fixture.payload.get("schema")
        if not isinstance(schema_id, str):
            errors.append(f"{fixture.name}: schema is missing")
            continue
        try:
            registry.validate(schema_id)
        except ValidationError as exc:
            errors.append(f"{fixture.name}: {exc}")
            continue
        if fixture.name in expected_tiers:
            report = validate_trajectory_quality(
                fixture.payload,
                report_id=f"trajectory-validation-report_golden_{fixture.name}",
                created_at=CREATED_AT,
            )
            if report.quality_tier != expected_tiers[fixture.name]:
                errors.append(f"{fixture.name}: unexpected trajectory quality tier")
            if not report.meets_requirement:
                errors.append(f"{fixture.name}: trajectory requirement is not satisfied")
            if fixture.name == "trajectory-rejected" and not report.failed_negative_useful:
                errors.append("trajectory-rejected: expected useful negative RL data")
            if fixture.name == "trajectory-human-reviewed":
                review = fixture.payload.get("human_review_receipt")
                if not isinstance(review, dict) or review.get("outcome") != "approved":
                    errors.append("trajectory-human-reviewed: approved review is missing")
        elif fixture.name == "funded-github-issue":
            if fixture.payload.get("settlement_authority") is not False:
                errors.append("funded-github-issue: marker must not grant settlement authority")
            _validate_embedded_digest(fixture, "contract", "contract_digest", errors)
            _validate_embedded_digest(fixture, "budget", "budget_digest", errors)
        elif fixture.name == "candidate-pool-advisory-ranked":
            candidates = fixture.payload.get("candidate_attempt_ids")
            selected = fixture.payload.get("selected_attempt_id")
            if not isinstance(candidates, list) or selected not in candidates:
                errors.append("candidate-pool-advisory-ranked: selected candidate is invalid")
        elif fixture.name == "environment-nixos":
            if fixture.payload.get("reproducibility_level") != "nix_flake":
                errors.append("environment-nixos: expected nix_flake evidence")
        elif fixture.name == "environment-cross-platform":
            if fixture.payload.get("platform") != "windows":
                errors.append("environment-cross-platform: expected Windows evidence")
    return errors


def write_golden_fixture_corpus(
    output_dir: str | Path,
    *,
    work_dir: str | Path,
) -> dict[str, object]:
    """Write canonical snapshots and their expected payload/dataset digests."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fixtures = build_golden_fixture_corpus(work_dir)
    validation_errors = validate_golden_fixture_corpus(fixtures)
    if validation_errors:
        raise ValidationError(f"invalid golden fixture corpus: {validation_errors}")
    fixture_entries: dict[str, dict[str, str]] = {}
    for fixture in fixtures:
        path = output / fixture.filename
        path.write_text(fixture.canonical_json() + "\n", encoding="utf-8")
        fixture_entries[fixture.name] = {
            "file": fixture.filename,
            "payload_digest": fixture.digest(),
        }
    dataset_path = Path(work_dir) / "golden-corpus-dataset.jsonl"
    dataset_manifest = export_trajectories_jsonl(
        [
            fixture.payload
            for fixture in fixtures
            if fixture.name in TRAJECTORY_FIXTURE_NAMES
        ],
        dataset_path,
        dataset_id="dataset_golden_fixture_corpus",
    )
    digest_manifest: dict[str, object] = {
        "schema": schemas.GOLDEN_FIXTURE_DIGEST_MANIFEST,
        "created_at": CREATED_AT,
        "fixtures": fixture_entries,
        "dataset": {
            "record_count": dataset_manifest.record_count,
            "jsonl_digest": dataset_manifest.jsonl_digest,
        },
    }
    (output / "digests.json").write_text(
        canonical_json(digest_manifest) + "\n",
        encoding="utf-8",
    )
    return digest_manifest


def load_golden_fixture_corpus(root: str | Path) -> list[GoldenFixture]:
    directory = Path(root)
    fixtures: list[GoldenFixture] = []
    for name in GOLDEN_FIXTURE_NAMES:
        payload = json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValidationError(f"golden fixture {name} must contain an object")
        fixtures.append(GoldenFixture(name=name, payload=payload))
    return fixtures


def _trajectory_record(
    slug: str,
    tier: str,
    *,
    accepted: bool = True,
    human_reviewed: bool = False,
) -> dict[str, object]:
    minimum_tier = tier if tier in {"manifest", "trace", "episode"} else "pr_only"
    requirement = TrajectoryRequirement(
        id=f"trajectory-requirement_golden_{slug}",
        created_at=CREATED_AT,
        minimum_quality_tier=minimum_tier,
        require_training_eligible=tier in {"trace", "episode"},
        require_rl_grade=tier in {"trace", "episode"},
        full_payout_minimum_tier=minimum_tier,
    )
    contract = TaskContract(
        id=f"task-contract_golden_{slug}",
        created_at=CREATED_AT,
        title=f"Golden fixture {slug}",
        description="Deterministic protocol snapshot fixture.",
        requirements=["Produce the declared evidence tier."],
        verifier_ids=["verifier.golden.fixture"],
        task_source="golden.fixture",
        repository="local/golden-fixtures",
        environment={"platform": "windows", "repository_snapshot": "golden-snapshot"},
        trajectory_requirement=requirement.to_dict(),
    )
    attempt = Attempt(
        id=f"attempt_golden_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id="worker.golden.fixture",
        base_revision="golden-base",
        candidate_revision=f"golden-candidate-{slug}",
        summary=f"Completed golden fixture {slug}.",
        patch_digest=sha256_digest({"fixture": slug, "patch": True}),
    )
    verifier_run = VerifierRun(
        id=f"verifier-run_golden_{slug}",
        created_at=CREATED_AT,
        verifier_id="verifier.golden.fixture",
        name="Golden fixture verifier",
        version="1",
        command=["python", "-m", "pytest", "tests/golden_fixture_test.py"],
        passed=accepted,
        metrics={"tests": 1, "failures": 0 if accepted else 1},
        failure_reasons=[] if accepted else ["golden fixture rejection"],
        logs_digest=sha256_digest({"fixture": slug, "accepted": accepted}),
    )
    receipt = VerificationReceipt(
        id=f"verification-receipt_golden_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        worker_id=attempt.worker_id,
        verifier_id=verifier_run.verifier_id,
        verifier_digest=verifier_run.verifier_digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        accepted=accepted,
        metrics=verifier_run.metrics,
        failure_reasons=verifier_run.failure_reasons,
        result_digest=verifier_run.result_digest(),
    )
    record: dict[str, object] = {
        "schema": schemas.TRAJECTORY,
        "id": f"trajectory_golden_{slug}",
        "created_at": CREATED_AT,
        "contract": contract.to_dict(),
        "attempt": attempt.to_dict(),
        "verifier_run": verifier_run.to_dict(),
        "receipt": receipt.to_dict(),
        "router_decision": {"policy_name": "golden-fixed-worker"},
        "reward_metadata": {
            "currency": "EUR",
            "reward_minor_units": 1000 if accepted else 0,
        },
        "cost_metadata": {"currency": "EUR", "compute_minor_units": 50},
        "latency_metadata": {"work_seconds": 30, "verification_seconds": 1},
        "review_metadata": {"human_reviewed": human_reviewed},
        "outcome": "accepted" if accepted else "rejected",
    }
    attempt_manifest: AttemptManifest | None = None
    trace_manifest = None
    if tier in {"manifest", "trace", "episode"}:
        evidence_value = 4 if tier == "episode" else 2 if tier == "trace" else 1
        attempt_manifest = _attempt_manifest(contract, attempt, evidence_value)
        record["attempt_manifest"] = attempt_manifest.to_dict()
    if tier in {"trace", "episode"}:
        events = _trace_events(attempt, accepted=accepted)
        trace_manifest = trace_manifest_from_events(
            attempt_id=attempt.id,
            events=events,
            evidence_level_value=4 if tier == "episode" else 2,
            trace_jsonl_digest=sha256_digest([event.to_dict() for event in events]),
            trust_level="runner_attested",
            redaction_policy=_redaction_policy(slug),
            raw_trace_digest=sha256_digest({"fixture": slug, "raw": True}),
            provenance={"source": "golden-fixture", "slug": slug},
            manifest_id=f"trace-manifest_golden_{slug}",
            created_at=CREATED_AT,
        )
        record["trace_manifest"] = trace_manifest.to_dict()
    if tier == "episode" and attempt_manifest is not None and trace_manifest is not None:
        episode = EpisodePackage(
            id=f"episode-package_golden_{slug}",
            created_at=CREATED_AT,
            task_contract_id=contract.id,
            attempt_id=attempt.id,
            attempt_manifest=attempt_manifest,
            trace_manifest=trace_manifest,
            artifact_digests=[sha256_digest({"fixture": slug, "artifact": True})],
            replay_instructions=["Run the recorded verifier in the fixture workspace."],
        )
        record["episode_package"] = episode.to_dict()
    if human_reviewed:
        review = HumanReviewReceipt.from_comments(
            id=f"human-review-receipt_golden_{slug}",
            created_at=CREATED_AT,
            task_contract_id=contract.id,
            attempt_id=attempt.id,
            reviewer_ref="maintainer.golden.fixture",
            reviewer_relationship="repository-maintainer",
            outcome="approved",
            authority="supplementary",
            criteria=[
                ReviewCriterion(
                    name="maintainability",
                    outcome="passed",
                    weight_milli=1000,
                    evidence_digest=attempt.patch_digest,
                )
            ],
            comments="Focused and maintainable fixture patch.",
            comments_ref="fixture://review/human-reviewed",
            friction=ReviewFrictionSignal(
                rounds=1,
                requested_changes=0,
                reviewer_minutes=5,
            ),
        )
        record["human_review_receipt"] = review.to_dict()
        record["review_metadata"] = {
            "human_reviewed": True,
            "human_review_receipt_digest": review.digest(),
            "review_friction": review.friction.to_dict(),
        }
    return record


def _attempt_manifest(
    contract: TaskContract,
    attempt: Attempt,
    evidence_value: int,
) -> AttemptManifest:
    slug = attempt.id.removeprefix("attempt_golden_")
    return AttemptManifest(
        id=f"attempt-manifest_golden_{slug}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        worker_id=attempt.worker_id,
        evidence_level=evidence_value,
        redaction_policy=_redaction_policy(slug),
        model_metadata={"family": "golden-fake-solver", "disclosure": "synthetic"},
        harness_metadata={"family": "golden-fixture-harness", "version": "1"},
        runner_metadata={"runner": "golden-fixture-runner", "version": "1"},
        environment_metadata={
            "platform": "windows",
            "reproducibility_level": "lockfile",
            "repository_snapshot_digest": sha256_digest("golden repository snapshot"),
        },
        cost_metadata={"currency": "EUR", "compute_minor_units": 50},
        latency_metadata={"work_seconds": 30},
        training_consent=TrajectoryConsent(
            id=f"trajectory-consent_golden_{slug}",
            created_at=CREATED_AT,
            training_use_allowed=True,
            allowed_uses=["rl", "supervised", "router"],
            license_ref="golden-fixture-only",
        ),
        trust_level="runner_attested",
    )


def _redaction_policy(slug: str) -> RedactionPolicy:
    return RedactionPolicy(
        id=f"redaction-policy_golden_{slug}",
        created_at=CREATED_AT,
        name=f"Golden fixture redaction for {slug}",
        field_paths=["payload.private_prompt", "payload.credentials"],
    )


def _trace_events(attempt: Attempt, *, accepted: bool) -> list[TraceEvent]:
    slug = attempt.id.removeprefix("attempt_golden_")
    event_data: list[tuple[str, dict[str, object]]] = [
        ("context.loaded", {"fixture": slug}),
        ("tool.call", {"tool": "pytest"}),
        ("verification.result", {"passed": accepted}),
        ("outcome.reported", {"accepted": accepted}),
    ]
    return [
        TraceEvent(
            id=f"trace-event_golden_{slug}_{sequence:04d}",
            created_at=CREATED_AT,
            attempt_id=attempt.id,
            sequence=sequence,
            event_type=event_type,
            observed_at=CREATED_AT,
            payload=payload,
            trust_level="runner_attested",
            provenance={"source": "golden-fixture", "slug": slug},
        )
        for sequence, (event_type, payload) in enumerate(event_data)
    ]


def _candidate_selection_fixture() -> dict[str, object]:
    rankings = [
        AdvisoryRankingRecord(
            id="advisory-ranking_golden_a",
            created_at=CREATED_AT,
            attempt_id="attempt_golden_candidate_a",
            score_milli=820,
            uncertainty_milli=90,
            scorer_id="verifier.golden.advisory",
            rationale="Higher deterministic fixture score.",
        ),
        AdvisoryRankingRecord(
            id="advisory-ranking_golden_b",
            created_at=CREATED_AT,
            attempt_id="attempt_golden_candidate_b",
            score_milli=710,
            uncertainty_milli=120,
            scorer_id="verifier.golden.advisory",
            rationale="Lower deterministic fixture score.",
        ),
    ]
    selection = CandidateSelectionRecord(
        id="candidate-selection_golden_advisory",
        created_at=CREATED_AT,
        task_contract_id="task-contract_golden_candidate_pool",
        candidate_attempt_ids=[ranking.attempt_id for ranking in rankings],
        selected_attempt_id="attempt_golden_candidate_a",
        rejected_alternatives=[
            {
                "attempt_id": "attempt_golden_candidate_b",
                "reason": "lower_advisory_score",
            }
        ],
        advisory_rankings=rankings,
        budget_used=Money("EUR", 20),
        selection_reason="advisory_ranking",
        uncertainty_milli=90,
        authoritative_receipt_id=None,
    )
    payload = selection.to_dict()
    payload["candidate_pool"] = {
        "schema": schemas.CANDIDATE_POOL,
        "id": "candidate-pool_golden_advisory",
        "attempt_ids": [ranking.attempt_id for ranking in rankings],
        "authority": "advisory-only",
    }
    return payload


def _validate_embedded_digest(
    fixture: GoldenFixture,
    payload_field: str,
    digest_field: str,
    errors: list[str],
) -> None:
    payload = fixture.payload.get(payload_field)
    expected = fixture.payload.get(digest_field)
    if not isinstance(payload, dict) or expected != sha256_digest(payload):
        errors.append(f"{fixture.name}: {payload_field} digest mismatch")
