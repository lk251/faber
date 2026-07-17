"""Validate repository skill structure and optionally run its no-key replay example."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _failure(message: str) -> int:
    print(f"skill validation failed: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-replay", action="store_true")
    parser.add_argument("--out-dir", default=".faber/skill-validation-demo")
    args = parser.parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    repository = Path(__file__).resolve().parents[4]
    skill_path = skill_root / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    expected_prefix = "---\nname: faber-proof\ndescription: "
    if not text.replace("\r\n", "\n").startswith(expected_prefix):
        return _failure("required name and description frontmatter is missing")
    closing = text.replace("\r\n", "\n").find("\n---\n", len(expected_prefix))
    if closing < 0:
        return _failure("frontmatter is not closed")
    required_paths = (
        skill_root / "references" / "artifact-contract.md",
        skill_root / "agents" / "openai.yaml",
        repository / "examples" / "build-week-proof" / "README.md",
        repository / "examples" / "build-week-proof" / "task-contract.json",
        repository / "examples" / "build-week-proof" / "proof-catalog.json",
    )
    missing = [str(path.relative_to(repository)) for path in required_paths if not path.is_file()]
    if missing:
        return _failure("missing referenced files: " + ", ".join(missing))
    required_text = (
        "run-summary.json",
        "proof-decision.json",
        "faber proof",
        "--mode",
        "HUMAN_REVIEW",
        "production sandbox isolation",
        "stale pre-repair bundle",
    )
    absent = [value for value in required_text if value not in text]
    if absent:
        return _failure("missing required instructions: " + ", ".join(absent))
    if args.run_replay:
        environment = os.environ.copy()
        environment.pop("OPENAI_API_KEY", None)
        environment["PYTHONPATH"] = str(repository / "src")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "faber.cli",
                "demo",
                "proof",
                "--mode",
                "replay",
                "--out-dir",
                args.out_dir,
                "--json",
            ],
            cwd=repository,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode != 0:
            return _failure("no-key replay command failed: " + result.stderr.strip())
        try:
            summary = json.loads(result.stdout)
        except json.JSONDecodeError:
            return _failure("no-key replay did not emit isolated JSON")
        if (
            summary.get("bad", {}).get("verdict") != "block"
            or summary.get("repaired", {}).get("verdict") != "pass"
        ):
            return _failure("no-key replay emitted the wrong verdict contrast")
    print("faber-proof skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
