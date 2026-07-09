"""Artifact writer for the local funded RL-grade CLI walkthrough."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faber.adapters.github.funded_product_loop import (
    FakeGitHubFundedProductLoopResult,
    run_fake_github_funded_product_loop,
)
from faber.artifact_validation import (
    ArtifactValidationResult,
    validate_attempt_file,
    validate_trace_file,
    validate_trajectory_file,
)
from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import ValidationError


@dataclass(frozen=True)
class FundedTrajectoryDemo:
    """Completed local walkthrough plus its machine-readable summary."""

    result: FakeGitHubFundedProductLoopResult
    summary: dict[str, object]

    def human_lines(self) -> list[str]:
        result = self.result
        settlement = result.budget_settlement
        if settlement is None:
            raise ValidationError("funded demo requires a local budget settlement")
        paths = self.summary.get("paths")
        if not isinstance(paths, dict):
            raise ValidationError("funded demo summary paths are missing")
        trajectory_path = paths.get("trajectory")
        dataset_path = paths.get("dataset")
        return [
            "Faber funded RL-grade demo: complete",
            f"Contract: {result.contract.id} ({result.contract.digest()})",
            f"Budget: {result.budget.id} ({result.budget.digest()})",
            f"Attempt: {result.attempt.id} ({result.attempt.digest()})",
            f"Receipt: {result.receipt.id} ({result.receipt.digest()})",
            f"Local settlement: {settlement.id} ({settlement.digest()})",
            (
                f"Trajectory: {result.quality_report.trajectory_id} "
                f"({result.quality_report.complete_record_digest}) - RL-grade"
            ),
            f"Dataset: {result.dataset_manifest.record_count} permitted record",
            f"Trajectory file: {trajectory_path}",
            f"Dataset file: {dataset_path}",
            "No network, payment provider, or model provider was used.",
        ]


def write_funded_trajectory_demo(out_dir: str | Path) -> FundedTrajectoryDemo:
    """Run the fake product loop, write every artifact, and validate the result."""

    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    dataset_path = output / "training.jsonl"
    result = run_fake_github_funded_product_loop(dataset_path)
    if result.budget_settlement is None:
        raise ValidationError("funded demo did not produce a local budget settlement")

    paths = {
        "issue": output / "issue.md",
        "contract": output / "contract.json",
        "budget": output / "budget.json",
        "attempt": output / "pr" / ".faber" / "attempt.json",
        "trace": output / "pr" / ".faber" / "trace.jsonl",
        "trace_manifest": output / "pr" / ".faber" / "trace-manifest.json",
        "verifier_run": output / "verifier-run.json",
        "receipt": output / "verification-receipt.json",
        "budget_settlement": output / "budget-settlement.json",
        "budget_reconciliation": output / "budget-reconciliation.json",
        "trajectory": output / "trajectory.json",
        "dataset": dataset_path,
        "dataset_manifest": output / "dataset-manifest.json",
        "maintainer_message": output / "maintainer-message.md",
        "run_summary": output / "run-summary.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    paths["issue"].write_text(result.issue_text + "\n", encoding="utf-8")
    _write_json(paths["contract"], result.contract.to_dict())
    _write_json(paths["budget"], result.budget.to_dict())
    for source_path, content in result.pr_file_map.items():
        destination = output / "pr" / Path(source_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    _write_json(paths["verifier_run"], result.verifier_run.to_dict())
    _write_json(paths["receipt"], result.receipt.to_dict())
    _write_json(paths["budget_settlement"], result.budget_settlement.to_dict())
    _write_json(paths["budget_reconciliation"], result.reconciliation.to_dict())
    _write_json(paths["trajectory"], result.trajectory_record)
    _write_json(paths["dataset_manifest"], result.dataset_manifest.to_dict())
    paths["maintainer_message"].write_text(
        result.maintainer_message + "\n",
        encoding="utf-8",
    )

    validations = _validate_artifacts(paths)
    summary: dict[str, object] = {
        "status": "complete",
        "contract": {"id": result.contract.id, "digest": result.contract.digest()},
        "budget": {"id": result.budget.id, "digest": result.budget.digest()},
        "attempt": {"id": result.attempt.id, "digest": result.attempt.digest()},
        "verifier_run": {
            "id": result.verifier_run.id,
            "digest": result.verifier_run.digest(),
        },
        "receipt": {"id": result.receipt.id, "digest": result.receipt.digest()},
        "budget_settlement": {
            "id": result.budget_settlement.id,
            "digest": result.budget_settlement.digest(),
            "total_minor_units": result.budget_settlement.total_minor_units,
        },
        "trajectory": {
            "id": result.quality_report.trajectory_id,
            "digest": sha256_digest(result.trajectory_record),
            "quality_report_digest": result.quality_report.digest(),
            "quality_tier": result.quality_report.quality_tier,
            "rl_grade": result.quality_report.is_rl_grade,
        },
        "dataset": {
            "id": result.dataset_manifest.dataset_id,
            "digest": result.dataset_manifest.jsonl_digest,
            "record_count": result.dataset_manifest.record_count,
        },
        "validations": {
            name: validation.to_dict() for name, validation in validations.items()
        },
        "paths": {name: str(path) for name, path in paths.items()},
        "external_integrations": {
            "network": False,
            "payment_provider": False,
            "model_provider": False,
        },
    }
    _write_json(paths["run_summary"], summary)
    return FundedTrajectoryDemo(result=result, summary=summary)


def _validate_artifacts(
    paths: dict[str, Path],
) -> dict[str, ArtifactValidationResult]:
    validations = {
        "attempt": validate_attempt_file(paths["attempt"]),
        "trace": validate_trace_file(paths["trace"]),
        "trajectory": validate_trajectory_file(paths["trajectory"]),
    }
    invalid = [name for name, result in validations.items() if result.status != "valid"]
    if invalid:
        raise ValidationError(f"funded demo generated invalid artifacts: {invalid}")
    return validations


def _write_json(path: Path, payload: object) -> None:
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
