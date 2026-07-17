"""Regenerate or check deterministic fake-development replay fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import (  # noqa: E402
    ProofDemoError,
    generate_development_fixture_payloads,
    write_development_fixtures,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1]
    if args.write:
        provenance_path = fixture / "replays" / "provenance.json"
        if provenance_path.is_file() and '"status":"live-reviewed"' in provenance_path.read_text(
            encoding="utf-8"
        ):
            print("refusing to overwrite live-reviewed replays", file=sys.stderr)
            return 1
        try:
            write_development_fixtures(fixture)
        except ProofDemoError as exc:
            print(f"fixture generation failed: {exc}", file=sys.stderr)
            return 1
        print("wrote deterministic fake-development fixtures")
        return 0
    provenance_path = fixture / "replays" / "provenance.json"
    if provenance_path.is_file() and '"status":"live-reviewed"' in provenance_path.read_text(
        encoding="utf-8"
    ):
        print("live-reviewed fixtures are protected from development regeneration")
        return 0
    payloads = generate_development_fixture_payloads(fixture)
    paths = {
        "task_contract": fixture / "task-contract.json",
        "proof_catalog": fixture / "proof-catalog.json",
        "bad_replay": fixture / "replays" / "bad.json",
        "repaired_replay": fixture / "replays" / "repaired.json",
        "provenance": fixture / "replays" / "provenance.json",
    }
    mismatches = [
        str(path.relative_to(fixture))
        for key, path in paths.items()
        if not path.is_file()
        or path.read_text(encoding="utf-8") != canonical_json(payloads[key]) + "\n"
    ]
    if mismatches:
        print("fixture mismatch: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print("development fixtures are byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
