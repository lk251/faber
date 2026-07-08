import pytest

from faber.adapters.github.contracts import (
    ATTEMPT_MANIFEST_PATH,
    issue_to_task_contract,
    parse_pull_request_attempt_manifest,
    pull_request_to_attempt,
)
from faber.adapters.github.events import GitHubIssueRef, GitHubPullRequestRef
from faber.adapters.github.installation import GitHubInstallation
from faber.canonical_json import canonical_json
from faber.datasets import export_trajectories_jsonl, read_trajectory_jsonl
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.traces import AttemptManifest, RedactionPolicy, TrajectoryConsent
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRun


def _installation() -> GitHubInstallation:
    return GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"pull_requests": "read", "checks": "read"},
    )


def _contract(installation: GitHubInstallation):
    return issue_to_task_contract(
        GitHubIssueRef(
            repository_full_name="lk251/faber",
            issue_number=2,
            title="Implement adapter",
            body="Build the fake client boundary.",
        ),
        installation=installation,
        verifier_ids=["verifier.faber.local"],
    )


def _pull_request() -> GitHubPullRequestRef:
    return GitHubPullRequestRef(
        repository_full_name="lk251/faber",
        pull_request_number=7,
        title="Implement GitHub adapter",
        body="Adds fake client tests.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
        html_url="https://github.com/lk251/faber/pull/7",
    )


def _attempt_manifest(contract) -> AttemptManifest:
    return AttemptManifest(
        id="attempt-manifest_github_pr",
        created_at="2026-01-01T00:00:00Z",
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id="attempt_from_manifest",
        base_revision="base-sha",
        candidate_revision="head-sha",
        worker_id="worker.github.worker",
        evidence_level=1,
        redaction_policy=RedactionPolicy(
            id="redaction-policy_github_pr",
            created_at="2026-01-01T00:00:00Z",
            name="Public PR manifest policy",
            field_paths=["model_metadata.private_prompt"],
        ),
        model_metadata={"disclosure": "coarse", "family": "frontier-code-model"},
        harness_metadata={"family": "codex-cli", "version": "1"},
        runner_metadata={"runner": "github-pr", "version": "1"},
        environment_metadata={"platform": "windows", "arch": "x86_64"},
        budget_metadata={"currency": "EUR", "budget_minor_units": 5000},
        cost_metadata={"currency": "EUR", "compute_minor_units": 1200},
        latency_metadata={"work_seconds": 300},
        training_consent=TrajectoryConsent(
            id="trajectory-consent_github_pr",
            created_at="2026-01-01T00:00:00Z",
            training_use_allowed=True,
            allowed_uses=["supervised", "router"],
            license_ref="test-fixture",
        ),
        trust_level="self_attested",
    )


def test_github_pr_ref_becomes_attempt_with_ci_as_metadata_only() -> None:
    installation = _installation()
    contract = _contract(installation)
    pull_request = _pull_request()

    attempt = pull_request_to_attempt(
        pull_request,
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("patch diff"),
        check_summaries=[{"name": "candidate-ci", "conclusion": "success"}],
    )

    assert attempt.task_contract_id == contract.id
    assert attempt.base_revision == "base-sha"
    assert attempt.candidate_revision == "head-sha"
    assert attempt.tool_summaries == []
    assert attempt.metadata["pull_request_number"] == 7
    assert attempt.metadata["candidate_ci"]["authority"] == "signal_only"
    assert attempt.metadata["candidate_ci"]["check_summaries"][0]["conclusion"] == "success"
    assert attempt.metadata["faber_attempt_manifest"]["status"] == "missing"
    assert attempt.metadata["trajectory_quality"]["quality_tier"] == "pr_only"
    assert attempt.metadata["trajectory_quality"]["evidence_level"] == 0
    assert attempt.metadata["trajectory_quality"]["training_eligible"] is False


def test_valid_attempt_manifest_from_pr_file_map() -> None:
    installation = _installation()
    contract = _contract(installation)
    pull_request = _pull_request()
    manifest = _attempt_manifest(contract)

    attempt = pull_request_to_attempt(
        pull_request,
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("patch diff"),
        file_map={ATTEMPT_MANIFEST_PATH: canonical_json(manifest.to_dict())},
    )

    evidence = attempt.metadata["faber_attempt_manifest"]
    assert attempt.id == manifest.attempt_id
    assert evidence["status"] == "valid"
    assert evidence["manifest_digest"] == manifest.digest()
    assert evidence["manifest"]["attempt_id"] == manifest.attempt_id
    assert evidence["provenance"]["trust_level"] == "self_attested"
    assert attempt.metadata["trajectory_quality"]["quality_tier"] == "manifest"
    assert attempt.metadata["trajectory_quality"]["evidence_level"] == 1
    assert attempt.metadata["trajectory_quality"]["training_eligible"] is True


def test_missing_attempt_manifest_is_allowed() -> None:
    installation = _installation()
    contract = _contract(installation)

    evidence = parse_pull_request_attempt_manifest(
        {},
        contract=contract,
        pull_request=_pull_request(),
        worker_id="worker.github.worker",
    )

    assert evidence.status == "missing"
    assert evidence.manifest is None
    assert evidence.errors == []


def test_malformed_attempt_manifest_becomes_adapter_error_metadata() -> None:
    installation = _installation()
    contract = _contract(installation)

    attempt = pull_request_to_attempt(
        _pull_request(),
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("patch diff"),
        file_map={ATTEMPT_MANIFEST_PATH: "{not-json"},
    )

    evidence = attempt.metadata["faber_attempt_manifest"]
    assert evidence["status"] == "invalid"
    assert evidence["manifest"] is None
    assert ".faber/attempt.json" in evidence["errors"][0]


def test_attempt_manifest_digest_is_stable_from_pr_file_map() -> None:
    installation = _installation()
    contract = _contract(installation)
    manifest = _attempt_manifest(contract)
    file_map = {ATTEMPT_MANIFEST_PATH: canonical_json(manifest.to_dict())}

    left = parse_pull_request_attempt_manifest(
        file_map,
        contract=contract,
        pull_request=_pull_request(),
        worker_id="worker.github.worker",
    )
    right = parse_pull_request_attempt_manifest(
        file_map,
        contract=contract,
        pull_request=_pull_request(),
        worker_id="worker.github.worker",
    )

    assert left.status == "valid"
    assert left.manifest_digest == right.manifest_digest == manifest.digest()


def test_attempt_manifest_is_visible_in_trajectory_export(tmp_path) -> None:
    installation = _installation()
    contract = _contract(installation)
    manifest = _attempt_manifest(contract)
    attempt = pull_request_to_attempt(
        _pull_request(),
        contract=contract,
        installation=installation,
        worker_id="worker.github.worker",
        patch_digest=sha256_digest("patch diff"),
        file_map={ATTEMPT_MANIFEST_PATH: canonical_json(manifest.to_dict())},
    )
    verifier_run = VerifierRun(
        verifier_id="verifier.faber.local",
        name="Local verifier",
        version="1",
        command=["python", "-m", "pytest"],
        passed=True,
        metrics={"tests": 1},
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)
    trajectory = Trajectory(
        contract=contract,
        attempt=attempt,
        receipt=receipt,
        router_decision=RouterDecision(
            task_contract_id=contract.id,
            selected_worker_id=attempt.worker_id,
            rejected_alternatives=[],
            estimated_cost=Money("EUR", 1000),
            expected_value=Money("EUR", 5000),
            policy_name="test-router",
        ),
        cost_metadata={"compute_minor_units": 1200},
        latency_metadata={"work_seconds": 300},
        review_metadata={"human_reviewed": False},
    )
    export_trajectories_jsonl([trajectory], tmp_path / "trajectories.jsonl")

    exported = read_trajectory_jsonl(tmp_path / "trajectories.jsonl")

    assert exported[0]["attempt"]["metadata"]["faber_attempt_manifest"]["status"] == "valid"
    assert (
        exported[0]["attempt"]["metadata"]["faber_attempt_manifest"]["manifest_digest"]
        == manifest.digest()
    )


def test_github_pr_attempt_rejects_contract_repository_mismatch() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber", "lk251/other"],
        permissions={"pull_requests": "read"},
    )
    contract = _contract(installation)
    pull_request = GitHubPullRequestRef(
        repository_full_name="lk251/other",
        pull_request_number=7,
        title="Wrong repo",
        body="Nope.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
    )

    with pytest.raises(ValueError, match="does not match task contract repository"):
        pull_request_to_attempt(
            pull_request,
            contract=contract,
            installation=installation,
            worker_id="worker",
            patch_digest=sha256_digest("patch"),
        )


def test_github_pr_attempt_rejects_out_of_scope_repository() -> None:
    installation = _installation()
    contract = _contract(installation)
    pull_request = GitHubPullRequestRef(
        repository_full_name="lk251/other",
        pull_request_number=7,
        title="Wrong repo",
        body="Nope.",
        author_login="worker",
        base_revision="base-sha",
        head_revision="head-sha",
    )

    with pytest.raises(ValueError, match="outside the GitHub installation scope"):
        pull_request_to_attempt(
            pull_request,
            contract=contract,
            installation=installation,
            worker_id="worker",
            patch_digest=sha256_digest("patch"),
        )
