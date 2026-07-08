"""Minimal Faber CLI."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

import faber
from faber.canonical_json import canonical_json
from faber.datasets import dataset_summary, export_trajectories_jsonl
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

    dataset = subparsers.add_parser("dataset-summary", help="Summarize trajectory JSONL.")
    dataset.add_argument("path", help="Path to trajectory JSONL.")

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
        manifest = export_trajectories_jsonl(
            trajectory_records,
            args.out,
            source_paths=[args.store],
        )
        print(canonical_json(manifest.to_dict()))
        return 0

    if args.command == "dataset-summary":
        print(canonical_json(dataset_summary(args.path)))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
