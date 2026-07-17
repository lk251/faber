"""Capture unreviewed live demo planner responses outside the committed fixture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import (  # noqa: E402
    ProofDemoError,
    capture_live_demo_replays,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1]
    try:
        result = capture_live_demo_replays(fixture, Path(args.out_dir).resolve(strict=False))
    except (ProofDemoError, OSError) as exc:
        print(f"live replay capture failed: {exc}", file=sys.stderr)
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
