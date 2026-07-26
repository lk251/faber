"""Guarded one-command live capture, review, install, and offline verification."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import ProofDemoError, run_guarded_live_demo_capture  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--expected-branch", default="build-week/faber-proof")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT / ".faber" / "live-gpt56-review-manifest.json",
    )
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1]
    try:
        result = run_guarded_live_demo_capture(
            fixture,
            reviewer=args.reviewer,
            expected_branch=args.expected_branch,
            review_manifest_path=args.manifest,
        )
    except (ProofDemoError, OSError) as exc:
        print(f"guarded live capture failed: {exc}", file=sys.stderr)
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
