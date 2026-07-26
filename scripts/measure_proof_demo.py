from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.proof_demo import run_proof_demo  # noqa: E402
from faber.proof_privacy import audit_proof_artifacts  # noqa: E402

THRESHOLDS = {
    "maximum_replay_planning_seconds_per_candidate": 2.0,
    "maximum_proof_execution_seconds_per_candidate": 30.0,
    "maximum_report_generation_seconds_per_candidate": 2.0,
    "maximum_total_demo_seconds": 90.0,
    "maximum_candidate_bundle_bytes": 2_000_000,
}


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def measure() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="faber-proof-performance-") as temporary:
        output = Path(temporary) / "demo"
        started = time.perf_counter()
        outcome = run_proof_demo(
            repository_root=REPOSITORY_ROOT,
            mode="replay",
            output_directory=output,
        )
        total_seconds = time.perf_counter() - started
        candidates: dict[str, object] = {}
        checks: dict[str, bool] = {}
        for candidate in ("bad", "repaired"):
            summary = json.loads(
                (output / candidate / "run-summary.json").read_text(encoding="utf-8")
            )
            timings = summary["performance_timings"]
            bundle_bytes = _directory_size(output / candidate)
            candidates[candidate] = {
                "verdict": summary["verdict"],
                "replay_planning_seconds": timings["replay_planning_seconds"],
                "proof_execution_seconds": timings["proof_execution_seconds"],
                "report_generation_seconds": timings["report_generation_seconds"],
                "bundle_generation_seconds": timings["bundle_generation_seconds"],
                "candidate_total_seconds": timings["candidate_total_seconds"],
                "bundle_bytes": bundle_bytes,
                "html_report_bytes": (output / candidate / "report.html").stat().st_size,
                "markdown_report_bytes": (output / candidate / "report.md").stat().st_size,
            }
            checks[f"{candidate}.replay_planning"] = (
                timings["replay_planning_seconds"]
                <= THRESHOLDS["maximum_replay_planning_seconds_per_candidate"]
            )
            checks[f"{candidate}.proof_execution"] = (
                timings["proof_execution_seconds"]
                <= THRESHOLDS["maximum_proof_execution_seconds_per_candidate"]
            )
            checks[f"{candidate}.report_generation"] = (
                timings["report_generation_seconds"]
                <= THRESHOLDS["maximum_report_generation_seconds_per_candidate"]
            )
            checks[f"{candidate}.bundle_size"] = (
                bundle_bytes <= THRESHOLDS["maximum_candidate_bundle_bytes"]
            )
        checks["demo.total"] = total_seconds <= THRESHOLDS["maximum_total_demo_seconds"]
        privacy = audit_proof_artifacts([output])
        checks["demo.privacy"] = privacy.passed
        return {
            "schema": "faber.proof_demo_performance_report.v1",
            "status": "pass" if all(checks.values()) else "fail",
            "platform": {
                "machine": platform.node(),
                "system": platform.system(),
                "release": platform.release(),
                "python": platform.python_version(),
            },
            "provenance": outcome.summary["provenance"],
            "total_demo_seconds": round(total_seconds, 6),
            "total_demo_bytes": _directory_size(output),
            "candidates": candidates,
            "thresholds": THRESHOLDS,
            "threshold_checks": checks,
            "privacy_finding_count": len(privacy.findings),
            "memory_measurement": {
                "status": "not_recorded",
                "reason": (
                    "The demo launches child Git and Python processes; a portable aggregate "
                    "peak-memory measurement is not available from the stdlib harness."
                ),
            },
        }


def _markdown(report: dict[str, object]) -> str:
    platform_record = report["platform"]
    candidates = report["candidates"]
    assert isinstance(platform_record, dict)
    assert isinstance(candidates, dict)
    lines = [
        "# Faber Proof Performance Evidence",
        "",
        f"- Status: **{report['status']}**",
        f"- Machine: `{platform_record['machine']}`",
        f"- Platform: `{platform_record['system']} {platform_record['release']}`",
        f"- Python: `{platform_record['python']}`",
        f"- Replay provenance: `{report['provenance']}`",
        f"- Total bad/repaired demo: **{report['total_demo_seconds']} seconds**",
        f"- Total output: **{report['total_demo_bytes']} bytes**",
        f"- Privacy findings: **{report['privacy_finding_count']}**",
        "",
        "| Candidate | Verdict | Replay plan (s) | Proof execution (s) | "
        "Report generation (s) | Bundle bytes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("bad", "repaired"):
        candidate = candidates[name]
        assert isinstance(candidate, dict)
        lines.append(
            f"| {name} | **{candidate['verdict']}** | "
            f"{candidate['replay_planning_seconds']} | "
            f"{candidate['proof_execution_seconds']} | "
            f"{candidate['report_generation_seconds']} | "
            f"{candidate['bundle_bytes']} |"
        )
    lines.extend(
        [
            "",
            "Thresholds are deliberately generous smoke limits. They catch severe regressions "
            "without treating shared CI wall-clock variance as a product failure.",
            "",
            "Peak memory is not recorded because the demo launches child Git and Python "
            "processes and this stdlib harness cannot measure their portable aggregate peak.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = measure()
    except (OSError, RuntimeError) as exc:
        print(f"proof demo performance measurement failed: {exc}", file=sys.stderr)
        return 1
    json_text = canonical_json(report) + "\n"
    markdown_text = _markdown(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text, encoding="utf-8", newline="\n")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown_text, encoding="utf-8", newline="\n")
    print(
        f"{report['status'].upper()}: total={report['total_demo_seconds']}s "
        f"bytes={report['total_demo_bytes']}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
