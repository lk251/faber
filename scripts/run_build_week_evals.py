from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from faber.proof_evals import (  # noqa: E402
    eval_report_json,
    render_eval_markdown,
    run_eval_suite,
)

DEFAULT_JSON = REPOSITORY_ROOT / "docs" / "generated" / "BUILD_WEEK_EVAL_RESULTS.json"
DEFAULT_MARKDOWN = REPOSITORY_ROOT / "docs" / "generated" / "BUILD_WEEK_EVAL_RESULTS.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic Faber Proof adversarial evals.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail unless the committed reports match a fresh successful run.",
    )
    return parser


def _check(path: Path, expected: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == expected
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = run_eval_suite(REPOSITORY_ROOT)
    json_text = eval_report_json(report)
    markdown_text = render_eval_markdown(report)
    if args.check:
        reports_match = _check(args.json, json_text) and _check(args.markdown, markdown_text)
        return 0 if report["status"] == "PASS" and reports_match else 1
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json_text, encoding="utf-8", newline="\n")
    args.markdown.write_text(markdown_text, encoding="utf-8", newline="\n")
    print(
        f"{report['status']}: {report['passed_case_count']}/{report['case_count']} cases; "
        f"unjustified_pass_count={report['unjustified_pass_count']}"
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
