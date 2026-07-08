"""Minimal Faber CLI."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

import faber
from faber.attempt_manifests import (
    generate_attempt_manifest,
    load_attempt_manifest,
    write_attempt_manifest,
)
from faber.canonical_json import canonical_json
from faber.datasets import dataset_summary, export_trajectories_jsonl
from faber.errors import FaberError
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
from faber.store import export_trajectory, init_local_store, list_records, store_summary
from faber.trajectories import build_demo_trajectory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m faber.cli")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        for line in doctor_lines():
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
        print(f"trajectory not found: {args.trajectory_id}", file=sys.stderr)
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
            print(f"failed to generate attempt manifest: {exc}", file=sys.stderr)
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
            print(f"invalid attempt manifest: {exc}", file=sys.stderr)
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
        result = run_golden_path(args.store, args.out)
        print(canonical_json(result))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
