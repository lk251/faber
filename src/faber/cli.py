"""Minimal Faber CLI."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

import faber
from faber.canonical_json import canonical_json
from faber.store import init_local_store
from faber.trajectories import build_demo_trajectory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m faber.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check that the core package can load.")

    init_store = subparsers.add_parser("init-local-store", help="Create a local SQLite store.")
    init_store.add_argument("--path", required=True, help="Path to the SQLite database.")

    emit_demo = subparsers.add_parser("emit-demo-trajectory", help="Write a demo trajectory JSON.")
    emit_demo.add_argument("--out", required=True, help="Path to write the trajectory JSON.")

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

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
