"""End-to-end Faber Proof orchestration and portable artifact bundles."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from faber.adapters import build_planning_request, plan_proof_request
from faber.attempts import Attempt
from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import FaberError, ValidationError
from faber.proof_configuration import (
    ProofConfiguration,
    load_proof_configuration,
    load_strict_json_object,
    load_task_contract,
)
from faber.proof_context import (
    DEFAULT_MAX_DIFF_BYTES,
    GitContextError,
    GitProofContext,
    collect_git_proof_context,
    ensure_executable_candidate,
)
from faber.proof_planning import ProofPlanningError, ProofPlanningResult
from faber.proof_reports import render_html_report, render_markdown_report
from faber.proof_workflow import (
    LOCAL_ISOLATION_DISCLOSURE,
    ProofExecutionPolicy,
    ProofWorkflowError,
    ProofWorkflowResult,
    run_proof_workflow,
    workspace_snapshot_digest,
)
from faber.proofs import ModelRunEvidence, ProofDecision, ProofEvidence, ProofPlan
from faber.validation import require_digest, require_non_empty_string

PROOF_RUN_SUMMARY_SCHEMA = "faber.proof_run_summary.v1"
PROOF_REDACTION_REPORT_SCHEMA = "faber.proof_redaction_report.v1"
PROOF_BUNDLE_VALIDATION_SCHEMA = "faber.proof_bundle_validation.v1"
PROOF_WORKER_ID = "worker.faber-proof.local"
MAX_SUMMARY_BYTES = 2 * 1024 * 1024


class ProofProductError(FaberError):
    """A secret-safe operational failure suitable for the public CLI."""

    def __init__(self, category: str, failure: str, *, why: str, next_step: str) -> None:
        self.category = require_non_empty_string(category, "category")
        self.failure = require_non_empty_string(failure, "failure")
        self.why = require_non_empty_string(why, "why")
        self.next_step = require_non_empty_string(next_step, "next_step")
        super().__init__(f"{self.category}: {self.failure}")


@dataclass(frozen=True)
class ProofRunOutcome:
    summary: Mapping[str, object]
    output_directory: Path
    report_path: Path

    @property
    def verdict(self) -> str | None:
        value = self.summary.get("verdict")
        return value if isinstance(value, str) else None

    @property
    def exit_code(self) -> int:
        if self.summary.get("status") == "dry_run":
            return 0
        return {"pass": 0, "block": 1, "human_review": 2}.get(self.verdict or "", 2)

    def human_lines(self) -> list[str]:
        verdict = "DRY RUN — NO VERDICT" if self.verdict is None else self.verdict.upper()
        raw_counts = self.summary.get("obligation_counts")
        if not isinstance(raw_counts, Mapping):
            raise ProofProductError(
                "invalid_bundle",
                "the proof summary is incomplete",
                why="Human output requires validated obligation counts.",
                next_step="Validate or regenerate the proof bundle before rendering it.",
            )
        lines = [
            f"Faber Proof: {verdict}",
            f"Task: {self.summary['task_title']}",
            f"Candidate: {str(self.summary['candidate_revision'])[:12]}",
            (
                "Obligations: "
                f"required {raw_counts['required']}, "
                f"passed {raw_counts['passed']}, "
                f"failed {raw_counts['failed']}, "
                f"missing {raw_counts['missing']}"
            ),
        ]
        failed_claim = self.summary.get("failed_claim")
        if failed_claim:
            lines.append(f"Failed claim: {failed_claim}")
        counterexample = self.summary.get("counterexample")
        if counterexample is not None:
            lines.append(f"Counterexample: {canonical_json(counterexample)}")
        lines.extend(
            [
                f"Model: {self.summary['model']} ({str(self.summary['mode']).upper()}, advisory)",
                f"Report: {self.report_path}",
            ]
        )
        return lines


def _attempt_for_context(
    context: GitProofContext,
    *,
    task_contract_id: str,
    workspace_digest: str,
    dry_run: bool,
) -> Attempt:
    del dry_run  # Planning identity is identical whether execution follows or not.
    identity_digest = sha256_digest(
        {
            "task_contract_id": task_contract_id,
            "base_revision": context.base_revision,
            "candidate_revision": context.candidate_revision,
            "planning_diff_digest": context.planning_diff_digest,
            "worker_id": PROOF_WORKER_ID,
        }
    )
    return Attempt(
        id=f"attempt-proof-{identity_digest.removeprefix('sha256:')[:24]}",
        created_at=context.candidate_created_at,
        task_contract_id=task_contract_id,
        worker_id=PROOF_WORKER_ID,
        base_revision=context.base_revision,
        candidate_revision=context.candidate_revision,
        summary="Faber Proof generated attempt binding for the selected local Git revisions.",
        patch_digest=context.planning_diff_digest,
        tool_summaries=[
            {
                "tool": "git",
                "base_revision": context.base_revision,
                "candidate_revision": context.candidate_revision,
                "changed_file_count": len(context.changed_files),
                "source_diff_digest": context.diff_digest,
            }
        ],
        metadata={
            "purpose": "faber-proof",
            "environment_evidence": {
                "workspace_digest": workspace_digest,
                "execution_boundary": "owner-approved-local-workspace",
            },
            "planning_diff_empty": context.empty_diff,
        },
    )


def _validate_task_policy(
    task_verifier_ids: Sequence[str], configuration: ProofConfiguration
) -> None:
    mandatory = set(configuration.proof_policy.mandatory_verifier_ids)
    missing = sorted(set(task_verifier_ids) - mandatory)
    if missing:
        raise ProofProductError(
            "policy_error",
            "the proof policy does not make every task verifier mandatory",
            why=(
                "A task-declared verifier cannot be advisory or silently omitted from a "
                "PASS decision."
            ),
            next_step="Add the named task verifier IDs to proof_policy.mandatory_verifier_ids.",
        )


def _json_bytes(value: object) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(value)
    path.write_bytes(payload)
    return sha256_digest(payload)


def _portable_relative_path(value: object, field: str) -> str:
    text = require_non_empty_string(value, field)
    windows = PureWindowsPath(text)
    path = PurePosixPath(text)
    if (
        windows.drive
        or windows.root
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValidationError(f"{field} must be a normalized relative bundle path")
    if path.as_posix() != text:
        raise ValidationError(f"{field} must use normalized POSIX separators")
    return text


def _artifact_file(stage: Path, relative_path: str, value: object) -> tuple[str, str]:
    normalized = _portable_relative_path(relative_path, "artifact path")
    return normalized, _write_json(stage / PurePosixPath(normalized), value)


def _record_paths(
    stage: Path,
    workflow: ProofWorkflowResult | None,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    paths: dict[str, list[str]] = {
        "proof_evidence": [],
        "verifier_runs": [],
        "verification_receipts": [],
    }
    digests: dict[str, str] = {}
    if workflow is None:
        for directory in ("proof-evidence", "verifier-runs", "verification-receipts"):
            (stage / directory).mkdir(parents=True, exist_ok=True)
        return paths, digests
    for index, evidence in enumerate(workflow.evidence):
        relative = f"proof-evidence/{index:03d}-{evidence.digest()[7:19]}.json"
        path, digest = _artifact_file(stage, relative, evidence.to_dict())
        paths["proof_evidence"].append(path)
        digests[path] = digest
    for index, run in enumerate(workflow.verifier_runs):
        relative = f"verifier-runs/{index:03d}-{run.digest()[7:19]}.json"
        path, digest = _artifact_file(stage, relative, run.to_dict())
        paths["verifier_runs"].append(path)
        digests[path] = digest
    for index, receipt in enumerate(workflow.verification_receipts):
        relative = f"verification-receipts/{index:03d}-{receipt.digest()[7:19]}.json"
        path, digest = _artifact_file(stage, relative, receipt.to_dict())
        paths["verification_receipts"].append(path)
        digests[path] = digest
    return paths, digests


def _obligation_counts(
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
) -> dict[str, int]:
    required = sum(1 for claim in planning.plan.claims if claim.evidence_required)
    if workflow is None:
        return {
            "required": required,
            "passed": 0,
            "failed": 0,
            "missing": 0,
            "uncovered": len(planning.plan.uncovered_claim_ids),
        }
    decision = workflow.decision
    return {
        "required": required,
        "passed": len(decision.passed_claim_ids),
        "failed": len(decision.failed_claim_ids),
        "missing": len(decision.missing_claim_ids),
        "uncovered": len(decision.uncovered_claim_ids),
    }


def _failure_focus(
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
) -> tuple[str | None, object | None]:
    if workflow is None:
        return None, None
    failed = set(workflow.decision.failed_claim_ids)
    claim_map = {claim.id: claim for claim in planning.plan.claims}
    for evidence in workflow.evidence:
        if evidence.claim_id in failed or evidence.status == "failed":
            claim = claim_map.get(evidence.claim_id)
            focus = evidence.counterexample_summary
            if focus is None:
                focus = {
                    "expected": evidence.expected_summary,
                    "observed": evidence.observed_summary,
                }
            return claim.statement if claim else evidence.claim_id, focus
    return None, None


def _reproduction_command(
    *,
    base_revision: str,
    candidate_revision: str,
    mode: str,
    model: str,
    max_diff_bytes: int,
    dry_run: bool,
) -> str:
    command = (
        "faber proof --repo . --task .faber/task-contract.json "
        "--catalog .faber/proof-catalog.json "
        f"--base {base_revision} --candidate {candidate_revision} --mode {mode} "
    )
    if mode == "replay":
        command += "--replay .faber/replays/gpt56-proof-plan.json "
    command += (
        f"--model {model} --critic-count 0 --max-diff-bytes {max_diff_bytes} --out-dir .faber/proof"
    )
    if dry_run:
        command += " --dry-run"
    return command


def _write_bundle(
    stage: Path,
    *,
    task: object,
    attempt: Attempt,
    configuration: ProofConfiguration,
    context_manifest: Mapping[str, object],
    request: object,
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
    execution_policy: ProofExecutionPolicy | None,
    model: str,
    mode: str,
    critic_count: int,
    max_diff_bytes: int,
    dry_run: bool,
    planning_seconds: float,
    proof_execution_seconds: float,
    product_started: float,
) -> dict[str, object]:
    from faber.contracts import TaskContract
    from faber.proof_planning import ProofPlanningRequest

    if not isinstance(task, TaskContract) or not isinstance(request, ProofPlanningRequest):
        raise AssertionError("bundle inputs must be validated records")
    bundle_started = time.perf_counter()
    artifact_paths: dict[str, object] = {
        "task_contract": "task-contract.json",
        "attempt": "attempt.json",
        "context": "context.json",
        "redaction_report": "redaction-report.json",
        "planning_request": "planning-request.json",
        "model_run_evidence": "model-run-evidence.json",
        "proof_plan": "proof-plan.json",
        "proof_catalog": "proof-catalog.json",
        "proof_policy": "proof-policy.json",
        "proof_evidence": [],
        "verifier_runs": [],
        "verification_receipts": [],
        "proof_decision": "proof-decision.json" if workflow else None,
        "execution_policy": "execution-policy.json" if execution_policy else None,
        "workflow_result": "workflow-result.json" if workflow else None,
        "run_summary": "run-summary.json",
        "markdown_report": "report.md",
        "html_report": "report.html",
    }
    artifact_digests: dict[str, str] = {}
    core_artifacts = {
        "task-contract.json": task.to_dict(),
        "attempt.json": attempt.to_dict(),
        "context.json": dict(context_manifest),
        "redaction-report.json": {
            "schema": PROOF_REDACTION_REPORT_SCHEMA,
            "source_diff_digest": context_manifest["source_diff_digest"],
            "planning_diff_digest": request.diff_digest,
            "redacted_diff_digest": request.redacted_diff_digest,
            "summary": dict(request.redaction_summary),
            "raw_diff_persisted": False,
        },
        "planning-request.json": request.to_dict(),
        "model-run-evidence.json": planning.model_run.to_dict(),
        "proof-plan.json": planning.plan.to_dict(),
        "proof-catalog.json": configuration.to_dict(),
        "proof-policy.json": configuration.proof_policy.to_dict(),
    }
    if workflow is not None and execution_policy is not None:
        core_artifacts.update(
            {
                "proof-decision.json": workflow.decision.to_dict(),
                "execution-policy.json": execution_policy.portable_dict(),
                "workflow-result.json": workflow.to_dict(),
            }
        )
    for relative, value in core_artifacts.items():
        path, digest = _artifact_file(stage, relative, value)
        artifact_digests[path] = digest
    record_paths, record_artifact_digests = _record_paths(stage, workflow)
    artifact_paths.update(record_paths)
    artifact_digests.update(record_artifact_digests)

    decision = workflow.decision if workflow else None
    failed_claim, counterexample = _failure_focus(planning, workflow)
    reproduction = _reproduction_command(
        base_revision=request.base_revision,
        candidate_revision=request.candidate_revision,
        mode=mode,
        model=model,
        max_diff_bytes=max_diff_bytes,
        dry_run=dry_run,
    )
    report_artifact_digests = {
        path: digest for path, digest in artifact_digests.items() if path != "workflow-result.json"
    }
    record_digests: dict[str, object] = {
        "task_contract": task.digest(),
        "attempt": attempt.digest(),
        "context": context_manifest["context_digest"],
        "planning_request": request.digest(),
        "structured_response": planning.structured_response_digest,
        "model_run": planning.model_run.digest(),
        "proof_plan": planning.plan.digest(),
        "proof_catalog": configuration.catalog.digest(),
        "proof_policy": configuration.proof_policy.digest(),
        "proof_evidence": [item.digest() for item in workflow.evidence] if workflow else [],
        "verifier_runs": [item.digest() for item in workflow.verifier_runs] if workflow else [],
        "verification_receipts": (
            [item.digest() for item in workflow.verification_receipts] if workflow else []
        ),
        "proof_decision": decision.digest() if decision else None,
        "workflow_result": workflow.digest() if workflow else None,
    }
    summary: dict[str, object] = {
        "schema": PROOF_RUN_SUMMARY_SCHEMA,
        "managed_by": "faber-proof",
        "status": "dry_run" if dry_run else "complete",
        "verdict": decision.verdict if decision else None,
        "reason_codes": list(decision.reason_codes) if decision else ["dry_run_no_verdict"],
        "task_id": task.id,
        "task_title": request.task_title,
        "attempt_id": attempt.id,
        "base_revision": request.base_revision,
        "candidate_revision": request.candidate_revision,
        "model": planning.model_run.returned_model_id or planning.model_run.requested_model_id,
        "requested_model": model,
        "mode": mode,
        "critic_count": critic_count,
        "obligation_counts": _obligation_counts(planning, workflow),
        "failed_claim_ids": list(decision.failed_claim_ids) if decision else [],
        "missing_claim_ids": list(decision.missing_claim_ids) if decision else [],
        "uncovered_claim_ids": (
            list(decision.uncovered_claim_ids)
            if decision
            else list(planning.plan.uncovered_claim_ids)
        ),
        "failed_claim": failed_claim,
        "counterexample": counterexample,
        "record_digests": record_digests,
        "artifact_paths": artifact_paths,
        "artifact_digests": {},
        "total_latency_ms": round(
            (workflow.timings.get("total_seconds", 0.0) * 1000 if workflow else 0.0)
            + float(planning.model_run.latency_ms or 0),
            3,
        ),
        "model_usage": {
            "input_tokens": planning.model_run.input_tokens,
            "output_tokens": planning.model_run.output_tokens,
            "cost": None,
        },
        "validation_status": "valid",
        "reproduction_command": reproduction,
        "runtime_boundary": LOCAL_ISOLATION_DISCLOSURE,
    }
    report_started = time.perf_counter()
    markdown = render_markdown_report(
        task_title=request.task_title,
        request=request,
        planning=planning,
        workflow=workflow,
        reproduction_command=reproduction,
        artifact_digests=report_artifact_digests,
    )
    report_generation_seconds = time.perf_counter() - report_started
    html = render_html_report(
        task_title=request.task_title,
        request=request,
        planning=planning,
        workflow=workflow,
        reproduction_command=reproduction,
        artifact_digests=report_artifact_digests,
    )
    (stage / "report.md").write_text(markdown, encoding="utf-8", newline="\n")
    (stage / "report.html").write_text(html, encoding="utf-8", newline="\n")
    artifact_digests["report.md"] = sha256_digest((stage / "report.md").read_bytes())
    artifact_digests["report.html"] = sha256_digest((stage / "report.html").read_bytes())
    summary["artifact_digests"] = dict(sorted(artifact_digests.items()))
    summary["performance_timings"] = {
        "replay_planning_seconds": round(planning_seconds, 6),
        "proof_execution_seconds": round(proof_execution_seconds, 6),
        "report_generation_seconds": round(report_generation_seconds, 6),
        "bundle_generation_seconds": round(time.perf_counter() - bundle_started, 6),
        "candidate_total_seconds": round(time.perf_counter() - product_started, 6),
    }
    _write_json(stage / "run-summary.json", summary)
    return summary


def _read_artifact(root: Path, relative_path: str) -> Mapping[str, object]:
    normalized = _portable_relative_path(relative_path, "artifact path")
    path = root / PurePosixPath(normalized)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        raise ValidationError("artifact path escapes the proof bundle") from None
    if not resolved.is_file() or resolved.is_symlink():
        raise ValidationError("artifact path must identify a regular in-bundle file")
    value = load_strict_json_object(resolved, max_bytes=MAX_SUMMARY_BYTES)
    if resolved.read_bytes() != _json_bytes(value):
        raise ValidationError("machine-readable artifacts must use canonical JSON plus newline")
    return value


def validate_proof_bundle(path: str | Path) -> Mapping[str, object]:
    """Re-read a bundle and fail closed on digest, path, or authority-graph tampering."""

    root = Path(path).resolve(strict=True)
    if not root.is_dir():
        raise ValidationError("proof bundle must be a directory")
    summary = _read_artifact(root, "run-summary.json")
    required_summary_fields = {
        "schema",
        "managed_by",
        "status",
        "verdict",
        "reason_codes",
        "task_id",
        "task_title",
        "attempt_id",
        "base_revision",
        "candidate_revision",
        "model",
        "requested_model",
        "mode",
        "critic_count",
        "obligation_counts",
        "failed_claim_ids",
        "missing_claim_ids",
        "uncovered_claim_ids",
        "failed_claim",
        "counterexample",
        "record_digests",
        "artifact_paths",
        "artifact_digests",
        "total_latency_ms",
        "model_usage",
        "validation_status",
        "reproduction_command",
        "runtime_boundary",
        "performance_timings",
    }
    if set(summary) != required_summary_fields:
        raise ValidationError("run summary uses an unsupported field set")
    if summary.get("schema") != PROOF_RUN_SUMMARY_SCHEMA:
        raise ValidationError("run summary uses an unsupported schema")
    if summary.get("managed_by") != "faber-proof" or summary.get("validation_status") != "valid":
        raise ValidationError("run summary is not a validated Faber Proof artifact")
    performance_timings = summary.get("performance_timings")
    expected_timing_fields = {
        "replay_planning_seconds",
        "proof_execution_seconds",
        "report_generation_seconds",
        "bundle_generation_seconds",
        "candidate_total_seconds",
    }
    if (
        not isinstance(performance_timings, Mapping)
        or set(performance_timings) != expected_timing_fields
        or any(
            isinstance(value, bool) or not isinstance(value, int | float) or value < 0
            for value in performance_timings.values()
        )
    ):
        raise ValidationError("performance_timings must contain non-negative stage timings")
    artifact_digests = summary.get("artifact_digests")
    if not isinstance(artifact_digests, Mapping):
        raise ValidationError("artifact_digests must be an object")
    for raw_path, raw_digest in artifact_digests.items():
        relative = _portable_relative_path(raw_path, "artifact_digests path")
        digest = require_digest(raw_digest, f"artifact_digests.{relative}")
        artifact = root / PurePosixPath(relative)
        if not artifact.is_file() or artifact.is_symlink():
            raise ValidationError("a declared artifact is unavailable")
        if sha256_digest(artifact.read_bytes()) != digest:
            raise ValidationError("an artifact byte digest does not match the run summary")

    paths = summary.get("artifact_paths")
    records = summary.get("record_digests")
    if not isinstance(paths, Mapping) or not isinstance(records, Mapping):
        raise ValidationError("artifact_paths and record_digests must be objects")
    task = _read_artifact(root, require_non_empty_string(paths.get("task_contract"), "task path"))
    attempt = _read_artifact(root, require_non_empty_string(paths.get("attempt"), "attempt path"))
    context = _read_artifact(root, require_non_empty_string(paths.get("context"), "context path"))
    request = _read_artifact(
        root, require_non_empty_string(paths.get("planning_request"), "planning request path")
    )
    plan_payload = _read_artifact(
        root, require_non_empty_string(paths.get("proof_plan"), "proof plan path")
    )
    model_payload = _read_artifact(
        root, require_non_empty_string(paths.get("model_run_evidence"), "model run path")
    )
    plan = ProofPlan.from_dict(plan_payload)
    model_run = ModelRunEvidence.from_dict(model_payload)
    configuration_path = require_non_empty_string(paths.get("proof_catalog"), "proof catalog path")
    configuration = load_proof_configuration(root / PurePosixPath(configuration_path))
    expected_record_digests = {
        "task_contract": sha256_digest(task),
        "attempt": sha256_digest(attempt),
        "planning_request": sha256_digest(request),
        "proof_plan": plan.digest(),
        "model_run": model_run.digest(),
    }
    for name, expected in expected_record_digests.items():
        if records.get(name) != expected:
            raise ValidationError(f"{name} record digest does not match the summary")
    if (
        records.get("proof_catalog") != configuration.catalog.digest()
        or records.get("proof_policy") != configuration.proof_policy.digest()
        or request.get("proof_catalog_digest") != configuration.catalog.digest()
        or plan.proof_catalog_digest != configuration.catalog.digest()
    ):
        raise ValidationError("catalog and proof-policy commitments are inconsistent")
    context_without_digest = dict(context)
    context_digest = context_without_digest.pop("context_digest", None)
    if (
        context_digest != sha256_digest(context_without_digest)
        or records.get("context") != context_digest
    ):
        raise ValidationError("context digest does not match the context manifest")
    if (
        task.get("id") != summary.get("task_id")
        or attempt.get("id") != summary.get("attempt_id")
        or request.get("task_contract_id") != task.get("id")
        or request.get("attempt_id") != attempt.get("id")
        or request.get("task_contract_digest") != sha256_digest(task)
        or request.get("attempt_digest") != sha256_digest(attempt)
        or request.get("base_revision") != summary.get("base_revision")
        or request.get("candidate_revision") != summary.get("candidate_revision")
        or request.get("diff_digest") != attempt.get("patch_digest")
        or plan.model_run.digest() != model_run.digest()
    ):
        raise ValidationError("task, attempt, revision, diff, or model bindings are inconsistent")

    status = summary.get("status")
    decision: ProofDecision | None = None
    if status == "dry_run":
        if summary.get("verdict") is not None or paths.get("proof_decision") is not None:
            raise ValidationError("dry-run bundles must not contain a verdict")
    elif status == "complete":
        decision_path = require_non_empty_string(paths.get("proof_decision"), "decision path")
        decision = ProofDecision.from_dict(_read_artifact(root, decision_path))
        raw_evidence_paths = paths.get("proof_evidence")
        if not isinstance(raw_evidence_paths, Sequence) or isinstance(raw_evidence_paths, str):
            raise ValidationError("proof_evidence paths must be a sequence")
        evidence = [
            ProofEvidence.from_dict(
                _read_artifact(root, _portable_relative_path(item, "proof evidence path"))
            )
            for item in raw_evidence_paths
        ]
        evidence_digests = sorted({item.digest() for item in evidence})
        if (
            decision.verdict != summary.get("verdict")
            or decision.proof_plan_digest != plan.digest()
            or list(decision.evidence_digests) != evidence_digests
            or records.get("proof_decision") != decision.digest()
            or records.get("proof_evidence") != [item.digest() for item in evidence]
        ):
            raise ValidationError("decision and evidence artifacts do not match the summary")
        receipt_paths = paths.get("verification_receipts")
        run_paths = paths.get("verifier_runs")
        if not isinstance(receipt_paths, Sequence) or isinstance(receipt_paths, str):
            raise ValidationError("verification_receipts paths must be a sequence")
        if not isinstance(run_paths, Sequence) or isinstance(run_paths, str):
            raise ValidationError("verifier_runs paths must be a sequence")
        receipt_payloads = [
            _read_artifact(root, _portable_relative_path(item, "receipt path"))
            for item in receipt_paths
        ]
        run_payloads = [
            _read_artifact(root, _portable_relative_path(item, "verifier run path"))
            for item in run_paths
        ]
        receipt_digests = {sha256_digest(item) for item in receipt_payloads}
        run_digests = {sha256_digest(item) for item in run_payloads}
        if records.get("verification_receipts") != [
            sha256_digest(item) for item in receipt_payloads
        ] or records.get("verifier_runs") != [sha256_digest(item) for item in run_payloads]:
            raise ValidationError("authority record digests do not match the summary")
        if not set(decision.authoritative_receipt_digests) <= receipt_digests:
            raise ValidationError("decision references an unavailable receipt")
        if any(
            item.verifier_run_digest is not None
            and item.verifier_run_digest not in run_digests
            or item.verification_receipt_digest is not None
            and item.verification_receipt_digest not in receipt_digests
            for item in evidence
        ):
            raise ValidationError("proof evidence references unavailable authority records")
        for receipt in receipt_payloads:
            if (
                receipt.get("task_contract_id") != task.get("id")
                or receipt.get("task_contract_digest") != sha256_digest(task)
                or receipt.get("attempt_id") != attempt.get("id")
                or receipt.get("base_revision") != summary.get("base_revision")
                or receipt.get("candidate_revision") != summary.get("candidate_revision")
            ):
                raise ValidationError("receipt context does not match the proof bundle")
        runs_by_digest = {sha256_digest(item): item for item in run_payloads}
        receipts_by_digest = {sha256_digest(item): item for item in receipt_payloads}
        for item in evidence:
            if item.verifier_run_digest is None or item.verification_receipt_digest is None:
                continue
            run = runs_by_digest[item.verifier_run_digest]
            receipt = receipts_by_digest[item.verification_receipt_digest]
            verifier_spec = {
                "verifier_id": run.get("verifier_id"),
                "name": run.get("name"),
                "version": run.get("version"),
                "command": run.get("command"),
            }
            run_result = {
                "passed": run.get("passed"),
                "metrics": run.get("metrics"),
                "failure_reasons": run.get("failure_reasons"),
                "logs_digest": run.get("logs_digest"),
            }
            if (
                run.get("verifier_digest") != sha256_digest(verifier_spec)
                or run.get("result_digest") != sha256_digest(run_result)
                or receipt.get("verifier_digest") != run.get("verifier_digest")
                or receipt.get("result_digest") != run.get("result_digest")
                or receipt.get("verifier_id") != run.get("verifier_id")
                or receipt.get("accepted") != run.get("passed")
                or receipt.get("metrics") != run.get("metrics")
                or receipt.get("failure_reasons") != run.get("failure_reasons")
            ):
                raise ValidationError("receipt and verifier-run authority do not match")
    else:
        raise ValidationError("run summary status must be complete or dry_run")
    counts = summary.get("obligation_counts")
    if not isinstance(counts, Mapping):
        raise ValidationError("obligation_counts must be an object")
    if status == "complete":
        if decision is None:
            raise AssertionError("complete bundle must have a decision")
        expected_counts = {
            "required": sum(1 for claim in plan.claims if claim.evidence_required),
            "passed": len(decision.passed_claim_ids),
            "failed": len(decision.failed_claim_ids),
            "missing": len(decision.missing_claim_ids),
            "uncovered": len(decision.uncovered_claim_ids),
        }
        if dict(counts) != expected_counts:
            raise ValidationError("obligation counts do not match the proof decision")
    report_markdown_path = _portable_relative_path(
        paths.get("markdown_report"), "markdown report path"
    )
    report_html_path = _portable_relative_path(paths.get("html_report"), "HTML report path")
    try:
        markdown = (root / PurePosixPath(report_markdown_path)).read_text(encoding="utf-8")
        html_report = (root / PurePosixPath(report_html_path)).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ValidationError("proof reports must be readable UTF-8 files") from None
    expected_label = (
        "DRY RUN — NO VERDICT"
        if status == "dry_run"
        else require_non_empty_string(summary.get("verdict"), "verdict").replace("_", " ").upper()
    )
    if (
        expected_label not in markdown
        or expected_label not in html_report
        or str(summary.get("candidate_revision")) not in markdown
        or str(summary.get("candidate_revision")) not in html_report
    ):
        raise ValidationError("Markdown and HTML reports do not match the decision artifact")
    lowered_html = html_report.casefold()
    if any(value in lowered_html for value in ("<script", "http://", "https://", " src=")):
        raise ValidationError("HTML report contains an external or executable asset reference")
    return {
        "schema": PROOF_BUNDLE_VALIDATION_SCHEMA,
        "status": "valid",
        "verdict": summary.get("verdict"),
        "summary_digest": sha256_digest(summary),
    }


def _safe_output_location(
    repository_root: Path,
    output_directory: str | Path,
    configuration: ProofConfiguration,
) -> Path:
    raw = Path(output_directory)
    target = raw if raw.is_absolute() else repository_root / raw
    target = target.resolve(strict=False)
    if target == repository_root or target == repository_root / ".git":
        raise ProofProductError(
            "output_error",
            "the proof output directory is unsafe",
            why="A proof bundle must never replace the repository or Git metadata.",
            next_step="Choose a dedicated path such as .faber/proof.",
        )
    try:
        relative = target.relative_to(repository_root).as_posix()
    except ValueError:
        return target
    allowed_prefixes = (".faber", "result", *configuration.context_excluded_paths)
    if not any(
        relative == prefix.strip("/") or relative.startswith(prefix.strip("/") + "/")
        for prefix in allowed_prefixes
        if prefix.strip("/")
    ) and not relative.startswith("result-"):
        raise ProofProductError(
            "output_error",
            "the in-repository output directory is not excluded from proof context",
            why="A generated report must not change the executable workspace it describes.",
            next_step="Use an output under .faber/ or add an owner-approved context exclusion.",
        )
    return target


def _managed_existing_output(target: Path) -> bool:
    if not target.exists():
        return False
    if target.is_symlink() or not target.is_dir():
        raise ProofProductError(
            "output_error",
            "the output path is not a safe directory",
            why="Faber will not overwrite a file or symlink at the proof bundle boundary.",
            next_step="Choose an empty output directory dedicated to Faber Proof.",
        )
    try:
        summary = load_strict_json_object(target / "run-summary.json", max_bytes=MAX_SUMMARY_BYTES)
    except ValidationError:
        raise ProofProductError(
            "output_error",
            "the existing output directory is not a managed Faber Proof bundle",
            why="Safe overwrite is restricted to directories with a validated ownership marker.",
            next_step="Move the existing directory aside or choose a new --out-dir.",
        ) from None
    if (
        summary.get("schema") != PROOF_RUN_SUMMARY_SCHEMA
        or summary.get("managed_by") != "faber-proof"
    ):
        raise ProofProductError(
            "output_error",
            "the existing output directory has no Faber Proof ownership marker",
            why="Overwriting an arbitrary directory could destroy unrelated work.",
            next_step="Move the directory aside or choose a new --out-dir.",
        )
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ProofProductError(
                "output_error",
                "the existing output bundle contains a symlink",
                why="Symlinks can redirect a safe overwrite outside the managed bundle.",
                next_step="Remove the bundle from use and choose a clean --out-dir.",
            )
    try:
        validate_proof_bundle(target)
    except ValidationError:
        raise ProofProductError(
            "output_error",
            "the existing managed output bundle does not validate",
            why="A tampered or partial bundle is not a safe overwrite authority.",
            next_step="Move the existing directory aside and rerun into a clean --out-dir.",
        ) from None
    return True


def _publish_stage(stage: Path, target: Path) -> None:
    existed = _managed_existing_output(target)
    backup = target.parent / f".{target.name}.faber-proof-backup-{os.getpid()}"
    if backup.exists():
        raise ProofProductError(
            "output_error",
            "a stale proof-output backup blocks safe publication",
            why="Faber cannot prove which directory version is authoritative.",
            next_step=f"Inspect and move aside {backup} before rerunning.",
        )
    try:
        if existed:
            target.replace(backup)
        stage.replace(target)
    except OSError:
        if backup.exists() and not target.exists():
            backup.replace(target)
        raise ProofProductError(
            "output_error",
            "the validated proof bundle could not be published atomically",
            why="A partially published bundle must not look complete.",
            next_step="Check directory permissions and rerun with a dedicated --out-dir.",
        ) from None
    if backup.exists():
        shutil.rmtree(backup)


def run_proof_product(
    *,
    repository: str | Path,
    task_path: str | Path,
    catalog_path: str | Path,
    base_revision: str,
    candidate_revision: str,
    mode: str,
    replay_path: str | Path | None,
    model: str = "gpt-5.6",
    critic_count: int = 0,
    max_diff_bytes: int = DEFAULT_MAX_DIFF_BYTES,
    output_directory: str | Path = ".faber/proof",
    dry_run: bool = False,
) -> ProofRunOutcome:
    """Run one proof from local commits and publish only a fully validated bundle."""

    if critic_count not in {0, 1}:
        raise ProofProductError(
            "configuration_error",
            "critic-count must be 0 or 1",
            why=(
                "The product permits at most one advisory critic and critics cannot decide "
                "verdicts."
            ),
            next_step="Use --critic-count 0 or --critic-count 1.",
        )
    if critic_count == 1:
        raise ProofProductError(
            "configuration_error",
            "the optional critic is not enabled by this product configuration",
            why="A critic requires a separately recorded, validated advisory response path.",
            next_step=(
                "Use --critic-count 0; work item 0080 accepts the validated final replay plan."
            ),
        )
    product_started = time.perf_counter()
    try:
        task = load_task_contract(task_path)
        configuration = load_proof_configuration(catalog_path)
        _validate_task_policy(task.verifier_ids, configuration)
        context = collect_git_proof_context(
            repository,
            base_revision=base_revision,
            candidate_revision=candidate_revision,
            max_diff_bytes=max_diff_bytes,
            policy_exclusions=configuration.context_excluded_paths,
        )
        output = _safe_output_location(context.repository_root, output_directory, configuration)
        if not dry_run:
            ensure_executable_candidate(context)
        workspace_digest = workspace_snapshot_digest(context.repository_root)
        attempt = _attempt_for_context(
            context,
            task_contract_id=task.id,
            workspace_digest=workspace_digest,
            dry_run=dry_run,
        )
        request = build_planning_request(
            task,
            attempt,
            diff_text=context.planning_diff_text,
            catalog_entries=configuration.catalog.planner_views(),
            proof_catalog_digest=configuration.catalog.digest(),
            mandatory_claims=configuration.mandatory_claims,
            mandatory_template_ids=configuration.proof_policy.mandatory_template_ids,
            max_diff_bytes=max_diff_bytes,
        )
        planning_started = time.perf_counter()
        planning = plan_proof_request(
            mode=mode,
            replay_path=replay_path,
            model=model,
            request=request,
            approved_replay_bundle_digests=(configuration.approved_replay_bundle_digests),
        )
        planning_seconds = time.perf_counter() - planning_started
        context_manifest = context.manifest(
            redacted_diff_text=request.redacted_diff_text,
            redacted_diff_digest=request.redacted_diff_digest,
            redaction_summary=request.redaction_summary,
        )
        workflow: ProofWorkflowResult | None = None
        execution_policy: ProofExecutionPolicy | None = None
        proof_execution_seconds = 0.0
        if not dry_run:
            settings = configuration.execution
            execution_policy = ProofExecutionPolicy(
                allowed_repository_root=str(context.repository_root),
                allowed_catalog_digest=configuration.catalog.digest(),
                verifier_registry_digest=configuration.verifier_registry().digest(),
                expected_attempt_digest=attempt.digest(),
                expected_workspace_digest=workspace_digest,
                maximum_obligations=settings.maximum_obligations,
                per_obligation_timeout_seconds=settings.per_obligation_timeout_seconds,
                total_timeout_seconds=settings.total_timeout_seconds,
                max_input_bytes=settings.max_input_bytes,
                max_output_bytes=settings.max_output_bytes,
                allowed_environment_variables=settings.allowed_environment_variables,
            )
            execution_started = time.perf_counter()
            workflow = run_proof_workflow(
                task_contract=task,
                attempt=attempt,
                plan=planning.plan,
                catalog=configuration.catalog,
                verifier_registry=configuration.verifier_registry(),
                proof_policy=configuration.proof_policy,
                execution_policy=execution_policy,
            )
            proof_execution_seconds = time.perf_counter() - execution_started
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(prefix=f".{output.name}.faber-proof-stage-", dir=output.parent)
        )
        try:
            summary = _write_bundle(
                stage,
                task=task,
                attempt=attempt,
                configuration=configuration,
                context_manifest=context_manifest,
                request=request,
                planning=planning,
                workflow=workflow,
                execution_policy=execution_policy,
                model=model,
                mode=mode,
                critic_count=critic_count,
                max_diff_bytes=max_diff_bytes,
                dry_run=dry_run,
                planning_seconds=planning_seconds,
                proof_execution_seconds=proof_execution_seconds,
                product_started=product_started,
            )
            validate_proof_bundle(stage)
            _publish_stage(stage, output)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return ProofRunOutcome(
            summary=summary,
            output_directory=output,
            report_path=output / "report.html",
        )
    except ProofProductError:
        raise
    except GitContextError as exc:
        raise ProofProductError(
            exc.code,
            exc.public_message,
            why=(
                "The proof plan and executable evidence must bind to one exact bounded local "
                "Git context."
            ),
            next_step=(
                "Correct the repository, revisions, working tree, exclusions, or diff limit "
                "and rerun."
            ),
        ) from None
    except ProofPlanningError as exc:
        raise ProofProductError(
            exc.code,
            exc.public_message,
            why=(
                "Invalid, unapproved, or mismatched advisory planning data cannot produce a "
                "verdict."
            ),
            next_step="Verify the replay pin and inputs, or retry the guarded live planner.",
        ) from None
    except ProofWorkflowError as exc:
        raise ProofProductError(
            exc.code,
            exc.public_message,
            why="An incomplete authority graph must fail closed before publication.",
            next_step=(
                "Correct the catalog, verifier registry, workspace, or execution policy and rerun."
            ),
        ) from None
    except (ValidationError, OSError) as exc:
        public = "proof inputs or generated artifacts failed validation"
        if isinstance(exc, ValidationError):
            public = str(exc)
        raise ProofProductError(
            "validation_error",
            public,
            why="Only a fully bound and internally consistent artifact graph may be reported.",
            next_step=(
                "Correct the named owner-controlled input and rerun into a managed output "
                "directory."
            ),
        ) from None
