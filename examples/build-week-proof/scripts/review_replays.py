"""Validate committed demo replays and their explicit provenance state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import (  # noqa: E402
    ProofDemoError,
    review_demo_replays,
    review_live_demo_capture,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-live-reviewed", action="store_true")
    parser.add_argument("--candidate-dir")
    parser.add_argument("--reviewer")
    parser.add_argument("--reviewed-at")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1]
    try:
        if args.candidate_dir:
            if not args.reviewer or not args.reviewed_at:
                parser.error("--candidate-dir requires --reviewer and --reviewed-at")
            result = review_live_demo_capture(
                fixture,
                Path(args.candidate_dir).resolve(strict=True),
                reviewer=args.reviewer,
                reviewed_at=args.reviewed_at,
                install=args.install,
            )
        else:
            if args.install:
                parser.error("--install requires --candidate-dir")
            result = review_demo_replays(
                fixture,
                require_live_reviewed=args.require_live_reviewed,
            )
    except ProofDemoError as exc:
        print(f"replay review failed: {exc}", file=sys.stderr)
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
