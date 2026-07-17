"""Minimal Faber CLI."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

import faber
from faber.artifact_validation import (
    validate_attempt_file,
    validate_trace_file,
    validate_trajectory_file,
)
from faber.attempt_manifests import (
    generate_attempt_manifest,
    load_attempt_manifest,
    write_attempt_manifest,
)
from faber.canonical_json import canonical_json
from faber.datasets import dataset_summary, export_trajectories_jsonl
from faber.errors import FaberError
from faber.funded_demo import write_funded_trajectory_demo
from faber.golden import (
    create_demo_contract,
    export_demo_trajectory,
    issue_demo_receipt,
    register_demo_verifier,
    register_demo_worker,
    run_demo_verifier,
    run_golden_path,
    settle_demo,
    submit_demo_attempt,
)
from faber.proof_demo import ProofDemoError, run_proof_demo
from faber.proof_product import ProofProductError, run_proof_product
from faber.store import export_trajectory, init_local_store, list_records, store_summary
from faber.trajectories import build_demo_trajectory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="faber",
        description="Local/self-hosted Faber CLI; this build has no hosted commands.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check that the core package can load.")

    init_store = subparsers.add_parser("init-local-store", help="Create a local SQLite store.")
    init_store.add_argument("--path", required=True, help="Path to the SQLite database.")

    emit_demo = subparsers.add_parser("emit-demo-trajectory", help="Write a demo trajectory JSON.")
    emit_demo.add_argument("--out", required=True, help="Path to write the trajectory JSON.")

    summary = subparsers.add_parser("store-summary", help="Print a local store summary.")
    summary.add_argument("--path", required=True, help="Path to the SQLite database.")

    list_contracts = subparsers.add_parser("list-contracts", help="List stored task contracts.")
    list_contracts.add_argument("--path", required=True, help="Path to the SQLite database.")

    show_trajectory = subparsers.add_parser("show-trajectory", help="Print a stored trajectory.")
    show_trajectory.add_argument("trajectory_id", help="Trajectory id to print.")
    show_trajectory.add_argument("--path", required=True, help="Path to the SQLite database.")

    export_stored = subparsers.add_parser("export-trajectory", help="Export one stored trajectory.")
    export_stored.add_argument("trajectory_id", help="Trajectory id to export.")
    export_stored.add_argument("--store", required=True, help="Path to the SQLite database.")
    export_stored.add_argument("--out", required=True, help="Output JSON path.")

    export_dataset = subparsers.add_parser(
        "export-trajectories",
        help="Export stored trajectories as JSONL.",
    )
    export_dataset.add_argument("--store", required=True, help="Path to the SQLite database.")
    export_dataset.add_argument("--out", required=True, help="Output JSONL path.")
    export_dataset.add_argument("--require-rl-grade", action="store_true")
    export_dataset.add_argument("--require-training-eligible", action="store_true")
    export_dataset.add_argument("--minimum-quality-tier")

    dataset = subparsers.add_parser("dataset-summary", help="Summarize trajectory JSONL.")
    dataset.add_argument("path", help="Path to trajectory JSONL.")

    generate_manifest = subparsers.add_parser(
        "generate-attempt-manifest",
        help="Generate a .faber/attempt.json manifest from local metadata.",
    )
    generate_manifest.add_argument("--out", default=".faber/attempt.json", help="Output JSON path.")
    generate_manifest.add_argument("--task-contract-id", required=True)
    generate_manifest.add_argument("--task-contract-digest", required=True)
    generate_manifest.add_argument("--base-revision", required=True)
    generate_manifest.add_argument("--candidate-revision", required=True)
    generate_manifest.add_argument("--worker-id", required=True)
    generate_manifest.add_argument("--environment-digest", required=True)
    generate_manifest.add_argument("--attempt-id")
    generate_manifest.add_argument("--evidence-level", type=int, default=1)
    generate_manifest.add_argument("--model-disclosure", default="private")
    generate_manifest.add_argument("--model-family", default="undisclosed")
    generate_manifest.add_argument("--model-ref")
    generate_manifest.add_argument("--harness-family", default="generic")
    generate_manifest.add_argument("--harness-version")
    generate_manifest.add_argument("--runner-name", default="manual")
    generate_manifest.add_argument("--runner-version", default="1")
    generate_manifest.add_argument("--platform", default="declared")
    generate_manifest.add_argument("--cost-minor-units", type=int, default=0)
    generate_manifest.add_argument("--latency-seconds", type=int, default=0)
    generate_manifest.add_argument("--currency", default="EUR")
    generate_manifest.add_argument("--redact", action="append", default=None)
    generate_manifest.add_argument("--allow-training-use", action="store_true")
    generate_manifest.add_argument("--training-use", action="append", default=None)
    generate_manifest.add_argument("--training-license-ref", default="unspecified")
    generate_manifest.add_argument("--created-at")

    validate_manifest = subparsers.add_parser(
        "validate-attempt-manifest",
        help="Validate a .faber/attempt.json manifest.",
    )
    validate_manifest.add_argument("path", help="Path to an attempt manifest JSON file.")

    validate_attempt = subparsers.add_parser(
        "validate-attempt",
        help="Validate an attempt manifest and print a structured report.",
    )
    validate_attempt.add_argument("path", help="Path to an attempt manifest JSON file.")

    validate_trace = subparsers.add_parser(
        "validate-trace",
        help="Validate ordered trace JSONL and print a structured report.",
    )
    validate_trace.add_argument("path", help="Path to a trace JSONL file.")

    validate_trajectory = subparsers.add_parser(
        "validate-trajectory",
        help="Validate a normalized trajectory and its task requirement.",
    )
    validate_trajectory.add_argument("path", help="Path to a trajectory JSON file.")

    trajectory_quality = subparsers.add_parser(
        "trajectory-quality",
        help="Report audit, learning, consent, redaction, and RL-grade quality.",
    )
    trajectory_quality.add_argument("path", help="Path to a trajectory JSON file.")

    for name, help_text in [
        ("create-demo-contract", "Create and store the golden path demo contract."),
        ("register-demo-worker", "Create and store the golden path demo worker."),
        ("register-demo-verifier", "Create and store the golden path demo verifier spec."),
        ("submit-demo-attempt", "Create and store the golden path demo attempt."),
        ("run-demo-verifier", "Run and store the golden path verifier run."),
        ("issue-demo-receipt", "Create and store the golden path verification receipt."),
        ("settle-demo", "Create and store the golden path local settlement."),
    ]:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--store", required=True, help="Path to the SQLite database.")

    export_demo = subparsers.add_parser(
        "export-demo-trajectory",
        help="Create, store, and export the golden path trajectory.",
    )
    export_demo.add_argument("--store", required=True, help="Path to the SQLite database.")
    export_demo.add_argument("--out", required=True, help="Output trajectory JSON path.")

    golden = subparsers.add_parser(
        "run-golden-path",
        help="Run the full deterministic local golden path demo.",
    )
    golden.add_argument("--store", required=True, help="Path to the SQLite database.")
    golden.add_argument("--out", required=True, help="Output trajectory JSON path.")

    funded = subparsers.add_parser(
        "demo-funded-trajectory",
        help="Run the fake funded RL-grade task walkthrough.",
    )
    funded.add_argument(
        "--out-dir",
        default=".faber/funded-demo",
        help="Directory for the complete walkthrough artifacts.",
    )
    funded.add_argument(
        "--json",
        action="store_true",
        help="Print the machine-readable run summary instead of human output.",
    )

    demo = subparsers.add_parser("demo", help="Run an original self-contained demonstration.")
    demo_commands = demo.add_subparsers(dest="demo_command", required=True)
    proof_demo = demo_commands.add_parser(
        "proof",
        help="Compare ordinary tests with Faber Proof on bad and repaired patches.",
    )
    proof_demo.add_argument("--mode", choices=("live", "replay"), default="replay")
    proof_demo.add_argument("--out-dir", default=".faber/build-week-demo")
    proof_demo.add_argument(
        "--json",
        action="store_true",
        help="Print only the canonical machine-readable comparison.",
    )

    proof = subparsers.add_parser(
        "proof",
        help="Turn a local candidate commit into a proof bundle and evidence report.",
    )
    proof.add_argument("--repo", default=".", help="Exact local Git repository root.")
    proof.add_argument("--task", required=True, help="Validated task-contract JSON path.")
    proof.add_argument(
        "--catalog",
        required=True,
        help="Owner-approved proof configuration and executable catalog JSON path.",
    )
    proof.add_argument("--base", required=True, help="Base revision resolved locally by Git.")
    proof.add_argument(
        "--candidate", required=True, help="Candidate revision resolved locally by Git."
    )
    proof.add_argument("--mode", choices=("live", "replay"), required=True)
    proof.add_argument("--replay", help="Approved GPT-5.6 replay bundle for replay mode.")
    proof.add_argument("--model", default="gpt-5.6", help="Requested planner model identifier.")
    proof.add_argument("--critic-count", type=int, choices=(0, 1), default=0)
    proof.add_argument("--max-diff-bytes", type=int, default=262_144)
    proof.add_argument("--out-dir", default=".faber/proof")
    proof.add_argument(
        "--json",
        action="store_true",
        help="Print only the canonical machine-readable run summary.",
    )
    proof.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate context and planning without executing proof obligations.",
    )
    proof.add_argument(
        "--open-report",
        action="store_true",
        help="Ask the standard browser to open the generated local report.",
    )

    return parser


def doctor_lines(cwd: Path | None = None) -> list[str]:
    """Return deterministic, human-readable environment facts."""

    current_dir = (cwd or Path.cwd()).resolve()
    state_dir = current_dir / ".faber"
    return [
        "Faber doctor",
        f"Python: {sys.version.split()[0]} ({sys.executable})",
        f"Package import: ok (faber {faber.__version__})",
        f"SQLite: ok ({sqlite3.sqlite_version})",
        f"Working directory: {current_dir}",
        f"Local state directory .faber/: {'present' if state_dir.exists() else 'missing'}",
        "faber doctor: ok",
    ]


def _print_cli_error(failure: str, *, why: str, next_step: str) -> None:
    print(f"Failed: {failure}", file=sys.stderr)
    print(f"Why it matters: {why}", file=sys.stderr)
    print(f"Next step: {next_step}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        for line in doctor_lines():
            print(line)
        return 0

    if args.command == "proof":
        try:
            proof_result = run_proof_product(
                repository=args.repo,
                task_path=args.task,
                catalog_path=args.catalog,
                base_revision=args.base,
                candidate_revision=args.candidate,
                mode=args.mode,
                replay_path=args.replay,
                model=args.model,
                critic_count=args.critic_count,
                max_diff_bytes=args.max_diff_bytes,
                output_directory=args.out_dir,
                dry_run=args.dry_run,
            )
        except ProofProductError as exc:
            _print_cli_error(exc.failure, why=exc.why, next_step=exc.next_step)
            return 2
        if args.json:
            print(canonical_json(proof_result.summary))
        else:
            for line in proof_result.human_lines():
                print(line)
        if args.open_report:
            try:
                webbrowser.open(proof_result.report_path.resolve().as_uri(), new=2)
            except (OSError, webbrowser.Error):
                pass
        return proof_result.exit_code

    if args.command == "demo" and args.demo_command == "proof":
        try:
            demo_result = run_proof_demo(
                repository_root=".",
                mode=args.mode,
                output_directory=args.out_dir,
            )
        except ProofDemoError as exc:
            _print_cli_error(
                f"proof demo failed: {exc}",
                why="The required ordinary-test and Faber Proof contrast did not validate.",
                next_step="Inspect the fixture, replay provenance, and named failed binding.",
            )
            return 2
        if args.json:
            print(canonical_json(demo_result.summary))
        else:
            for line in demo_result.human_lines():
                print(line)
        return 0

    if args.command == "init-local-store":
        store_path = init_local_store(args.path)
        print(f"initialized local store: {store_path}")
        return 0

    if args.command == "emit-demo-trajectory":
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory = build_demo_trajectory()
        out_path.write_text(canonical_json(trajectory.to_dict()) + "\n", encoding="utf-8")
        print(f"wrote demo trajectory: {out_path}")
        return 0

    if args.command == "store-summary":
        print(canonical_json(store_summary(args.path)))
        return 0

    if args.command == "list-contracts":
        print(canonical_json(list_records(args.path, "task_contract")))
        return 0

    if args.command == "show-trajectory":
        records = list_records(args.path, "trajectory")
        for record in records:
            if record["id"] == args.trajectory_id:
                print(canonical_json(record["payload"]))
                return 0
        _print_cli_error(
            f"trajectory `{args.trajectory_id}` was not found in {args.path}",
            why="Faber cannot inspect or export a record that is absent from the local store.",
            next_step=f"Run `list-contracts --path {args.path}` or verify the trajectory ID.",
        )
        return 1

    if args.command == "export-trajectory":
        out_path = export_trajectory(args.store, args.trajectory_id, args.out)
        print(f"exported trajectory: {out_path}")
        return 0

    if args.command == "export-trajectories":
        trajectory_records: list[dict[str, object]] = []
        for record in list_records(args.store, "trajectory"):
            payload = record.get("payload")
            if isinstance(payload, dict):
                trajectory_records.append(payload)
        dataset_manifest = export_trajectories_jsonl(
            trajectory_records,
            args.out,
            source_paths=[args.store],
            require_rl_grade=args.require_rl_grade,
            require_training_eligible=args.require_training_eligible,
            minimum_quality_tier=args.minimum_quality_tier,
        )
        print(canonical_json(dataset_manifest.to_dict()))
        return 0

    if args.command == "dataset-summary":
        print(canonical_json(dataset_summary(args.path)))
        return 0

    if args.command == "generate-attempt-manifest":
        try:
            attempt_manifest = generate_attempt_manifest(
                task_contract_id=args.task_contract_id,
                task_contract_digest=args.task_contract_digest,
                base_revision=args.base_revision,
                candidate_revision=args.candidate_revision,
                worker_id=args.worker_id,
                environment_digest=args.environment_digest,
                attempt_id=args.attempt_id,
                evidence_level=args.evidence_level,
                model_disclosure=args.model_disclosure,
                model_family=args.model_family,
                model_ref=args.model_ref,
                harness_family=args.harness_family,
                harness_version=args.harness_version,
                runner_name=args.runner_name,
                runner_version=args.runner_version,
                platform=args.platform,
                cost_minor_units=args.cost_minor_units,
                latency_seconds=args.latency_seconds,
                currency=args.currency,
                redaction_field_paths=args.redact,
                training_use_allowed=args.allow_training_use,
                training_allowed_uses=args.training_use,
                training_license_ref=args.training_license_ref,
                created_at=args.created_at,
            )
            digest = write_attempt_manifest(attempt_manifest, args.out)
        except FaberError as exc:
            _print_cli_error(
                f"attempt manifest generation failed: {exc}",
                why="An invalid or unbound manifest cannot serve as attempt evidence.",
                next_step="Correct the named field and rerun `generate-attempt-manifest`.",
            )
            return 1
        print(
            canonical_json(
                {
                    "path": args.out,
                    "attempt_id": attempt_manifest.attempt_id,
                    "digest": digest,
                }
            )
        )
        return 0

    if args.command == "validate-attempt-manifest":
        try:
            attempt_manifest = load_attempt_manifest(args.path)
        except (FaberError, json.JSONDecodeError, OSError) as exc:
            _print_cli_error(
                f"attempt manifest validation failed: {exc}",
                why="Faber cannot bind malformed evidence to an attempt or trajectory.",
                next_step=f"Correct the named field in {args.path} and rerun this command.",
            )
            return 1
        print(
            canonical_json(
                {
                    "status": "valid",
                    "path": args.path,
                    "attempt_id": attempt_manifest.attempt_id,
                    "digest": attempt_manifest.digest(),
                }
            )
        )
        return 0

    if args.command == "validate-attempt":
        validation_result = validate_attempt_file(args.path)
        print(canonical_json(validation_result.to_dict()))
        return validation_result.exit_code

    if args.command == "validate-trace":
        validation_result = validate_trace_file(args.path)
        print(canonical_json(validation_result.to_dict()))
        return validation_result.exit_code

    if args.command in {"validate-trajectory", "trajectory-quality"}:
        validation_result = validate_trajectory_file(
            args.path,
            quality_only=args.command == "trajectory-quality",
        )
        print(canonical_json(validation_result.to_dict()))
        return validation_result.exit_code

    if args.command == "create-demo-contract":
        contract = create_demo_contract(args.store)
        print(f"created demo contract: {contract.id}")
        return 0

    if args.command == "register-demo-worker":
        worker = register_demo_worker(args.store)
        print(f"registered demo worker: {worker.id}")
        return 0

    if args.command == "register-demo-verifier":
        verifier = register_demo_verifier(args.store)
        print(f"registered demo verifier: {verifier.verifier_id}")
        return 0

    if args.command == "submit-demo-attempt":
        attempt = submit_demo_attempt(args.store)
        print(f"submitted demo attempt: {attempt.id}")
        return 0

    if args.command == "run-demo-verifier":
        verifier_run = run_demo_verifier(args.store)
        print(f"ran demo verifier: {verifier_run.id}")
        return 0

    if args.command == "issue-demo-receipt":
        receipt = issue_demo_receipt(args.store)
        print(f"issued demo receipt: {receipt.id}")
        return 0

    if args.command == "settle-demo":
        settlement = settle_demo(args.store)
        print(f"settled demo work: {settlement.id}")
        return 0

    if args.command == "export-demo-trajectory":
        trajectory = export_demo_trajectory(args.store, args.out)
        print(f"exported demo trajectory: {trajectory.id} -> {args.out}")
        return 0

    if args.command == "run-golden-path":
        golden_result = run_golden_path(args.store, args.out)
        print(canonical_json(golden_result))
        return 0

    if args.command == "demo-funded-trajectory":
        try:
            funded_demo = write_funded_trajectory_demo(args.out_dir)
        except (FaberError, OSError) as exc:
            _print_cli_error(
                f"funded trajectory walkthrough failed: {exc}",
                why="The walkthrough did not produce a fully validated local artifact set.",
                next_step="Inspect the reported field, keep the output directory, and rerun.",
            )
            return 1
        if args.json:
            print(canonical_json(funded_demo.summary))
        else:
            for line in funded_demo.human_lines():
                print(line)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
