from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from faber.adapters.openai.prompt import RESPONSE_SCHEMA_VERSION
from faber.adapters.openai.proof_planner import PROVIDER_ADAPTER_ID, build_planning_request
from faber.adapters.openai.replay import create_replay_bundle, write_replay_bundle
from faber.canonical_json import canonical_json
from faber.cli import main
from faber.contracts import TaskContract
from faber.errors import ValidationError
from faber.proof_catalog import (
    FileInvariantCapability,
    ProofCapabilityPolicy,
    ProofCatalog,
    ProofCatalogEntry,
)
from faber.proof_configuration import (
    ProofConfiguration,
    ProofExecutionSettings,
    load_proof_configuration,
)
from faber.proof_context import DEFAULT_MAX_DIFF_BYTES, GitContextError, collect_git_proof_context
from faber.proof_planning import ProviderPlanningResponse
from faber.proof_product import (
    ProofProductError,
    _attempt_for_context,
    run_proof_product,
    validate_proof_bundle,
)
from faber.proof_workflow import workspace_snapshot_digest
from faber.proofs import ProofClaim, ProofPolicy
from faber.verifiers import VerifierSpec

CREATED_AT = "2026-07-17T00:00:00+00:00"
MODEL = "gpt-5.6"


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path, candidate_text: str) -> tuple[Path, str, str]:
    repository = tmp_path / "proof repository with spaces"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Faber Test")
    _git(repository, "config", "user.email", "faber@example.test")
    _git(repository, "config", "core.autocrlf", "false")
    (repository / "evidence file.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "--", "evidence file.txt")
    _git(repository, "commit", "-q", "-m", "base")
    base = _git(repository, "rev-parse", "HEAD")
    (repository / "evidence file.txt").write_text(candidate_text, encoding="utf-8")
    _git(repository, "add", "--", "evidence file.txt")
    _git(repository, "commit", "-q", "-m", "candidate")
    candidate = _git(repository, "rev-parse", "HEAD")
    return repository, base, candidate


def _object_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"expected": {"type": "string", "maxLength": 256}},
        "required": ["expected"],
        "additionalProperties": False,
    }


def _records(repository: Path) -> tuple[TaskContract, ProofConfiguration]:
    spec = VerifierSpec(
        id="verifier-spec_proof-file",
        created_at=CREATED_AT,
        verifier_id="verifier.proof-file",
        name="Approved file proof",
        version="1",
        description="Checks one owner-approved repository file invariant.",
        command_template=[sys.executable, "-c", "pass"],
        allowed_timeout_seconds=5,
    )
    capability = FileInvariantCapability(
        policy=ProofCapabilityPolicy(
            verifier_id=spec.verifier_id,
            verifier_version=spec.version,
            verifier_spec_digest=spec.digest(),
            working_directory=".",
            timeout_seconds=5,
            max_output_bytes=4_096,
        ),
        repository_path="evidence file.txt",
        operation="contains_literal",
        expected_parameter="expected",
        json_pointer_parameter=None,
    )
    entry = ProofCatalogEntry(
        id="proof.file-contains",
        version="1",
        description="Prove that the candidate retains the required literal.",
        execution_parameter_schema=_object_schema(),
        capability=capability,
    )
    claim = ProofClaim(
        id="claim.required-literal",
        statement="The candidate contains the required boundary result.",
        severity="high",
        requirement_refs=["requirement:0"],
        evidence_required=True,
        risk_rationale="The exact boundary result is the task contract.",
    )
    policy = ProofPolicy(
        name="proof-product-test",
        version="1",
        approved_verifier_ids=[spec.verifier_id],
        mandatory_claim_ids=[claim.id],
        mandatory_template_ids=[entry.id],
        mandatory_verifier_ids=[spec.verifier_id],
        minimum_authoritative_outcomes=1,
    )
    task = TaskContract(
        id="task-contract_proof-product",
        created_at=CREATED_AT,
        title="Preserve the required boundary result",
        description="The candidate must retain a concrete required literal.",
        requirements=["The candidate file contains the word good."],
        verifier_ids=[spec.verifier_id],
        repository=repository.name,
    )
    configuration = ProofConfiguration(
        catalog=ProofCatalog([entry]),
        verifier_specs=[spec],
        proof_policy=policy,
        mandatory_claims=[claim],
        execution=ProofExecutionSettings(
            maximum_obligations=4,
            per_obligation_timeout_seconds=5,
            total_timeout_seconds=20,
            max_input_bytes=65_536,
            max_output_bytes=4_096,
        ),
    )
    return task, configuration


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _fixture(
    tmp_path: Path,
    *,
    candidate_text: str,
    human_review: bool = False,
) -> tuple[Path, str, str, Path, Path, Path]:
    repository, base, candidate = _repository(tmp_path, candidate_text)
    task, configuration = _records(repository)
    state = repository / ".faber"
    task_path = state / "task-contract.json"
    catalog_path = state / "proof-catalog.json"
    replay_path = state / "replays" / "gpt56-proof-plan.json"
    _write_json(task_path, task.to_dict())

    context = collect_git_proof_context(
        repository,
        base_revision=base,
        candidate_revision=candidate,
    )
    attempt = _attempt_for_context(
        context,
        task_contract_id=task.id,
        workspace_digest=workspace_snapshot_digest(repository),
        dry_run=False,
    )
    request = build_planning_request(
        task,
        attempt,
        diff_text=context.planning_diff_text,
        catalog_entries=configuration.catalog.planner_views(),
        proof_catalog_digest=configuration.catalog.digest(),
        mandatory_claims=configuration.mandatory_claims,
        mandatory_template_ids=configuration.proof_policy.mandatory_template_ids,
        max_diff_bytes=DEFAULT_MAX_DIFF_BYTES,
    )
    claim = configuration.mandatory_claims[0]
    entry = configuration.catalog.entries[0]
    structured_response = {
        "schema": RESPONSE_SCHEMA_VERSION,
        "claims": [
            {
                "id": claim.id,
                "statement": claim.statement,
                "severity": claim.severity,
                "requirement_refs": list(claim.requirement_refs),
                "evidence_required": claim.evidence_required,
                "risk_rationale": claim.risk_rationale,
            }
        ],
        "selections": [
            {
                "claim_id": claim.id,
                "template_id": entry.id,
                "template_version": entry.version,
                "parameters": {"expected": "good"},
                "expected_behavior": "The approved file contains the required literal.",
                "rationale": "The invariant directly checks the contract boundary.",
            }
        ],
        "uncovered_claim_ids": [],
        "human_review_recommended": human_review,
        "uncertainty_notes": ["Human review requested by fixture."] if human_review else [],
    }
    response = ProviderPlanningResponse(
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        requested_model_id=MODEL,
        returned_model_id="gpt-5.6-2026-07-01",
        response_id="resp_proof_product_fixture",
        mode="live",
        structured_response=structured_response,
        latency_ms=12,
        input_tokens=100,
        output_tokens=50,
    )
    replay = create_replay_bundle(request, response, created_at=CREATED_AT)
    write_replay_bundle(replay_path, replay)
    approved_configuration = replace(
        configuration,
        approved_replay_bundle_digests=[replay.digest()],
    )
    _write_json(catalog_path, approved_configuration.to_dict())
    return repository, base, candidate, task_path, catalog_path, replay_path


def test_git_context_is_local_bounded_deterministic_and_excludes_outputs(
    tmp_path: Path,
) -> None:
    repository, base, candidate = _repository(
        tmp_path,
        "good\r\nOPENAI_API_KEY=sk-proj-abcdefghijklmnop\r\n",
    )
    first = collect_git_proof_context(
        repository,
        base_revision=base,
        candidate_revision=candidate,
    )
    second = collect_git_proof_context(
        repository,
        base_revision=base[:12],
        candidate_revision="HEAD",
    )

    assert first.base_revision == base
    assert first.candidate_revision == candidate
    assert first.changed_files == ("evidence file.txt",)
    assert "\r" not in first.diff_text
    assert first.diff_digest == second.diff_digest
    assert first.diff_text == second.diff_text

    with pytest.raises(GitContextError, match="invalid_revision"):
        collect_git_proof_context(repository, base_revision="missing", candidate_revision="HEAD")
    with pytest.raises(GitContextError, match="diff_too_large"):
        collect_git_proof_context(
            repository,
            base_revision=base,
            candidate_revision=candidate,
            max_diff_bytes=64,
        )

    empty = collect_git_proof_context(
        repository,
        base_revision="HEAD",
        candidate_revision="HEAD",
    )
    assert empty.empty_diff is True
    assert empty.diff_text == ""
    assert "no included changes" in empty.planning_diff_text

    (repository / ".faber").mkdir()
    (repository / ".faber" / "generated.txt").write_text("generated\n", encoding="utf-8")
    _git(repository, "add", "-f", "--", ".faber/generated.txt")
    _git(repository, "commit", "-q", "-m", "generated output")
    excluded_candidate = _git(repository, "rev-parse", "HEAD")
    excluded = collect_git_proof_context(
        repository,
        base_revision=candidate,
        candidate_revision=excluded_candidate,
    )
    assert excluded.changed_files == ()
    assert excluded.excluded_changed_files == (".faber/generated.txt",)
    assert excluded.empty_diff is True


def test_proof_configuration_round_trips_owner_authority(tmp_path: Path) -> None:
    repository, _, _ = _repository(tmp_path, "good\n")
    _, configuration = _records(repository)
    path = repository / ".faber" / "proof-catalog.json"
    _write_json(path, configuration.to_dict())

    loaded = load_proof_configuration(path)

    assert loaded.to_dict() == configuration.to_dict()
    assert loaded.catalog.digest() == configuration.catalog.digest()
    assert loaded.verifier_registry().digest() == configuration.verifier_registry().digest()


@pytest.mark.parametrize(
    ("candidate_text", "human_review", "expected_verdict", "expected_exit"),
    [
        ("good\n", False, "pass", 0),
        ("bad\n", False, "block", 1),
        ("good\n", True, "human_review", 2),
    ],
)
def test_replay_product_emits_bound_bundle_and_exit_status(
    tmp_path: Path,
    candidate_text: str,
    human_review: bool,
    expected_verdict: str,
    expected_exit: int,
) -> None:
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text=candidate_text,
        human_review=human_review,
    )
    output = repository / ".faber" / "proof"

    result = run_proof_product(
        repository=repository,
        task_path=task_path,
        catalog_path=catalog_path,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay_path,
        output_directory=output,
    )

    assert result.verdict == expected_verdict
    assert result.exit_code == expected_exit
    assert result.summary["validation_status"] == "valid"
    assert validate_proof_bundle(output)["verdict"] == expected_verdict
    assert (output / "report.html").is_file()
    assert (output / "report.md").is_file()
    html = (output / "report.html").read_text(encoding="utf-8")
    assert "ADVISORY" in html
    assert "Authoritative evidence" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html
    if expected_verdict == "block":
        assert html.index("Failed claim") < html.index("Model analysis")
        assert html.index("Concrete counterexample") < html.index("Model analysis")

    repeated = run_proof_product(
        repository=repository,
        task_path=task_path,
        catalog_path=catalog_path,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay_path,
        output_directory=output,
    )
    assert repeated.verdict == expected_verdict
    assert validate_proof_bundle(output)["status"] == "valid"


def test_dry_run_never_reports_pass_and_json_cli_output_is_isolated(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text="good\n",
    )
    output = repository / ".faber" / "dry-proof"

    exit_code = main(
        [
            "proof",
            "--repo",
            str(repository),
            "--task",
            str(task_path),
            "--catalog",
            str(catalog_path),
            "--base",
            base,
            "--candidate",
            candidate,
            "--mode",
            "replay",
            "--replay",
            str(replay_path),
            "--out-dir",
            str(output),
            "--dry-run",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["status"] == "dry_run"
    assert payload["verdict"] is None
    assert (
        "PASS"
        not in (output / "report.html").read_text(encoding="utf-8").split("Model analysis", 1)[0]
    )


def test_tampered_artifact_fails_bundle_validation(tmp_path: Path) -> None:
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text="good\n",
    )
    output = repository / ".faber" / "proof"
    run_proof_product(
        repository=repository,
        task_path=task_path,
        catalog_path=catalog_path,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay_path,
        output_directory=output,
    )
    decision = output / "proof-decision.json"
    decision.write_text(decision.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(ValidationError, match="artifact byte digest"):
        validate_proof_bundle(output)


def test_partial_bundle_cannot_validate_as_complete(tmp_path: Path) -> None:
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text="good\n",
    )
    output = repository / ".faber" / "proof"
    run_proof_product(
        repository=repository,
        task_path=task_path,
        catalog_path=catalog_path,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay_path,
        output_directory=output,
    )
    evidence_path = next((output / "proof-evidence").glob("*.json"))
    evidence_path.unlink()

    with pytest.raises(ValidationError, match="declared artifact is unavailable"):
        validate_proof_bundle(output)


def test_critic_mode_is_disabled_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ProofProductError, match="critic is not enabled") as error:
        run_proof_product(
            repository=tmp_path,
            task_path=tmp_path / "task.json",
            catalog_path=tmp_path / "catalog.json",
            base_revision="base",
            candidate_revision="candidate",
            mode="replay",
            replay_path=tmp_path / "replay.json",
            critic_count=1,
        )

    assert error.value.category == "configuration_error"


def test_operational_cli_error_uses_failure_significance_and_next_step(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, base, candidate, task_path, catalog_path, _ = _fixture(
        tmp_path,
        candidate_text="good\n",
    )

    exit_code = main(
        [
            "proof",
            "--repo",
            str(repository),
            "--task",
            str(task_path),
            "--catalog",
            str(catalog_path),
            "--base",
            base,
            "--candidate",
            candidate,
            "--mode",
            "replay",
            "--out-dir",
            str(repository / ".faber" / "failed-proof"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Failed:" in captured.err
    assert "Why it matters:" in captured.err
    assert "Next step:" in captured.err
    assert not (repository / ".faber" / "failed-proof" / "run-summary.json").exists()


def test_safe_overwrite_rejects_unmanaged_output(tmp_path: Path) -> None:
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text="good\n",
    )
    output = repository / ".faber" / "unmanaged"
    output.mkdir()
    note = output / "keep.txt"
    note.write_text("user data\n", encoding="utf-8")

    with pytest.raises(ProofProductError, match="not a managed"):
        run_proof_product(
            repository=repository,
            task_path=task_path,
            catalog_path=catalog_path,
            base_revision=base,
            candidate_revision=candidate,
            mode="replay",
            replay_path=replay_path,
            output_directory=output,
        )

    assert note.read_text(encoding="utf-8") == "user data\n"


def test_live_mode_without_sdk_or_client_configuration_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, base, candidate, task_path, catalog_path, _ = _fixture(
        tmp_path,
        candidate_text="good\n",
    )
    output = repository / ".faber" / "live-proof"

    def missing_sdk(_: str) -> object:
        raise ImportError

    monkeypatch.setattr("faber.adapters.openai.proof_planner.import_module", missing_sdk)
    with pytest.raises(ProofProductError, match="optional dependency"):
        run_proof_product(
            repository=repository,
            task_path=task_path,
            catalog_path=catalog_path,
            base_revision=base,
            candidate_revision=candidate,
            mode="live",
            replay_path=None,
            output_directory=output,
        )
    assert not (output / "run-summary.json").exists()

    class UnconfiguredClient:
        def __init__(self, **_: object) -> None:
            raise RuntimeError("missing API key")

    monkeypatch.setattr(
        "faber.adapters.openai.proof_planner.import_module",
        lambda _: SimpleNamespace(OpenAI=UnconfiguredClient),
    )
    with pytest.raises(ProofProductError, match="could not be configured"):
        run_proof_product(
            repository=repository,
            task_path=task_path,
            catalog_path=catalog_path,
            base_revision=base,
            candidate_revision=candidate,
            mode="live",
            replay_path=None,
            output_directory=output,
        )


def test_secret_is_redacted_before_request_and_reports(tmp_path: Path) -> None:
    secret = "sk-proj-abcdefghijklmnop"
    repository, base, candidate, task_path, catalog_path, replay_path = _fixture(
        tmp_path,
        candidate_text=f"good\nOPENAI_API_KEY={secret}\n",
    )
    output = repository / ".faber" / "proof"

    run_proof_product(
        repository=repository,
        task_path=task_path,
        catalog_path=catalog_path,
        base_revision=base,
        candidate_revision=candidate,
        mode="replay",
        replay_path=replay_path,
        output_directory=output,
    )

    for name in ("context.json", "planning-request.json", "report.md", "report.html"):
        assert secret not in (output / name).read_text(encoding="utf-8")
    context = json.loads((output / "context.json").read_text(encoding="utf-8"))
    assert "[redacted]" in context["redacted_diff_text"]
