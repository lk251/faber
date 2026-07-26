from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from faber.canonical_json import canonical_json  # noqa: E402
from faber.digests import sha256_digest  # noqa: E402
from faber.proof_demo import run_proof_demo  # noqa: E402
from faber.proof_privacy import audit_proof_artifacts  # noqa: E402

DEFAULT_JSON = REPOSITORY_ROOT / "docs" / "generated" / "DEVELOPMENT_REPORT_REGENERATION.json"
DEFAULT_MARKDOWN = REPOSITORY_ROOT / "docs" / "generated" / "DEVELOPMENT_REPORT_REGENERATION.md"


def _report() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="faber-report-regeneration-") as temporary:
        root = Path(temporary)
        first = run_proof_demo(
            repository_root=REPOSITORY_ROOT,
            mode="replay",
            output_directory=root / "first",
        )
        second = run_proof_demo(
            repository_root=REPOSITORY_ROOT,
            mode="replay",
            output_directory=root / "second",
        )
        reports: dict[str, object] = {}
        for candidate in ("bad", "repaired"):
            for extension in ("html", "md"):
                relative = f"{candidate}/report.{extension}"
                first_bytes = (first.output_directory / relative).read_bytes()
                second_bytes = (second.output_directory / relative).read_bytes()
                if first_bytes != second_bytes:
                    raise RuntimeError(f"{relative} is not byte-stable across replay")
                reports[relative] = {
                    "digest": sha256_digest(first_bytes),
                    "size_bytes": len(first_bytes),
                }
        privacy = audit_proof_artifacts([first.output_directory, second.output_directory])
        if not privacy.passed:
            raise RuntimeError("regenerated development reports failed the privacy audit")
        record_digests: dict[str, object] = {}
        for candidate in ("bad", "repaired"):
            summary = json.loads(
                (first.output_directory / candidate / "run-summary.json").read_text(
                    encoding="utf-8"
                )
            )
            records = summary["record_digests"]
            record_digests[candidate] = {
                "proof_plan": records["proof_plan"],
                "proof_evidence": records["proof_evidence"],
                "proof_decision": records["proof_decision"],
            }
        return {
            "schema": "faber.development_report_regeneration.v1",
            "status": "pass",
            "provenance": first.summary["provenance"],
            "scope": (
                "No-key fake-development replay used only to verify deterministic layout, "
                "bindings, and privacy. Final committed sample HTML remains gated on "
                "live-reviewed capture."
            ),
            "sample_reports_committed": False,
            "reports": reports,
            "record_digests": record_digests,
            "privacy_audit": {
                "status": "pass",
                "scanned_files": privacy.scanned_files,
                "finding_count": len(privacy.findings),
            },
        }


def _markdown(report: dict[str, object]) -> str:
    reports = report["reports"]
    assert isinstance(reports, dict)
    lines = [
        "# Development Report Regeneration",
        "",
        f"- Status: **{report['status']}**",
        f"- Provenance: **{report['provenance']}**",
        f"- Sample HTML committed: **{report['sample_reports_committed']}**",
        f"- Privacy findings: **{report['privacy_audit']['finding_count']}**",  # type: ignore[index]
        "",
        str(report["scope"]),
        "",
        "| Report | SHA-256 digest | Bytes |",
        "|---|---|---:|",
    ]
    for path, raw in reports.items():
        assert isinstance(raw, dict)
        lines.append(f"| `{path}` | `{raw['digest']}` | {raw['size_bytes']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = _report()
    except (OSError, RuntimeError) as exc:
        print(f"development report regeneration failed: {exc}", file=sys.stderr)
        return 1
    json_text = canonical_json(report) + "\n"
    markdown_text = _markdown(report)
    if args.check:
        try:
            matches = (
                args.json.read_text(encoding="utf-8") == json_text
                and args.markdown.read_text(encoding="utf-8") == markdown_text
            )
        except OSError:
            matches = False
        return 0 if matches else 1
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json_text, encoding="utf-8", newline="\n")
    args.markdown.write_text(markdown_text, encoding="utf-8", newline="\n")
    print(f"PASS: {len(report['reports'])} byte-stable reports; provenance={report['provenance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
