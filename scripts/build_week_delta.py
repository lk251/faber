#!/usr/bin/env python3
"""Report the local Git delta eligible for OpenAI Build Week 2026."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_BASELINE = "build-week-2026-baseline"
SUBMISSION_PERIOD_START_TEXT = "2026-07-13T09:00:00-07:00"
SUBMISSION_PERIOD_START = datetime.fromisoformat(SUBMISSION_PERIOD_START_TEXT)
SCHEMA = "faber.build-week-delta.v1"
GROUP_ORDER = (
    "pre-existing",
    "build-week-core",
    "demo",
    "tests",
    "docs",
    "submission-support",
)


class GitCommandError(RuntimeError):
    """A local Git command could not produce the requested report data."""


def _decode_git(data: bytes) -> str:
    """Decode Git's configured UTF-8 output without consulting a console code page."""

    return data.decode("utf-8", errors="replace")


def _git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env.setdefault("GIT_OPTIONAL_LOCKS", "0")
    command = [
        "git",
        "-c",
        "color.ui=false",
        "-c",
        "core.quotepath=false",
        *args,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=os.fspath(repo),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise GitCommandError("Git is not installed or is not available on PATH.") from exc

    if check and result.returncode != 0:
        detail = _decode_git(result.stderr).strip() or f"exit status {result.returncode}"
        raise GitCommandError(f"git {' '.join(args)} failed: {detail}")
    return result


def _resolve_commit(repo: Path, ref: str) -> str | None:
    result = _git(
        repo,
        "rev-parse",
        "--verify",
        "--quiet",
        "--end-of-options",
        f"{ref}^{{commit}}",
        check=False,
    )
    if result.returncode != 0:
        return None
    sha = _decode_git(result.stdout).strip()
    if not sha or any(character not in "0123456789abcdefABCDEF" for character in sha):
        raise GitCommandError(f"Git returned an invalid commit ID for ref {ref!r}.")
    return sha.lower()


def _working_tree_is_dirty(repo: Path) -> bool:
    result = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return bool(result.stdout)


def _baseline_paths(repo: Path, baseline_sha: str) -> set[str]:
    result = _git(repo, "ls-tree", "-r", "-z", "--name-only", baseline_sha)
    return {_decode_git(path) for path in result.stdout.split(b"\0") if path}


def _commit_shas(repo: Path, baseline_sha: str, target_sha: str) -> list[str]:
    result = _git(
        repo,
        "rev-list",
        "--reverse",
        "--topo-order",
        f"{baseline_sha}..{target_sha}",
    )
    return [line for line in _decode_git(result.stdout).splitlines() if line]


def _canonical_iso_date(value: str) -> str:
    """Normalize Git's equivalent ``Z`` and ``+00:00`` renderings."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        return value
    return parsed.isoformat()


def _commit_record(repo: Path, sha: str) -> dict[str, str]:
    result = _git(
        repo,
        "show",
        "--no-patch",
        "--format=%H%x00%aI%x00%cI%x00%s",
        sha,
    )
    fields = _decode_git(result.stdout).rstrip("\r\n").split("\0", 3)
    if len(fields) != 4:
        raise GitCommandError(f"Git returned malformed metadata for commit {sha}.")
    return {
        "sha": fields[0].lower(),
        "author_date": _canonical_iso_date(fields[1]),
        "committer_date": _canonical_iso_date(fields[2]),
        "subject": fields[3],
    }


def _date_warnings(commits: Sequence[dict[str, str]]) -> list[str]:
    warnings: list[str] = []
    for commit in commits:
        for field, label in (
            ("author_date", "author date"),
            ("committer_date", "committer date"),
        ):
            value = commit[field]
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("date has no UTC offset")
            except ValueError:
                warnings.append(f"Commit {commit['sha']} has an invalid {label}: {value!r}.")
                continue
            if parsed < SUBMISSION_PERIOD_START:
                warnings.append(
                    f"Commit {commit['sha']} has {label} {value} before submission "
                    f"period start {SUBMISSION_PERIOD_START_TEXT}."
                )
    return warnings


def _purpose_groups(path: str, *, pre_existing: bool) -> list[str]:
    normalized = path.replace("\\", "/")
    lower = normalized.casefold()
    parts = lower.split("/")
    filename = parts[-1]
    selected: set[str] = set()

    if pre_existing:
        selected.add("pre-existing")

    if lower.startswith(("src/", "faber/")) or lower in {
        "flake.lock",
        "flake.nix",
        "justfile",
        "pyproject.toml",
    }:
        selected.add("build-week-core")

    if any(part in {"demo", "demos", "example", "examples"} for part in parts) or (
        "demo" in filename and filename.endswith(".py")
    ):
        selected.add("demo")

    if lower.startswith("tests/") or filename.startswith("test_"):
        selected.add("tests")

    if lower.startswith("docs/") or (
        "/" not in lower and (filename.startswith("readme") or filename.endswith(".md"))
    ):
        selected.add("docs")

    if lower.startswith((".agents/", ".github/", "codex/", "scripts/")) or (
        "/" not in lower and filename.startswith("readme")
    ):
        selected.add("submission-support")

    # A newly added, otherwise unclassified implementation file is Build Week core.
    # Existing unclassified files are already represented by the eligibility group.
    if not selected:
        selected.add("build-week-core")

    return [group for group in GROUP_ORDER if group in selected]


def _changed_files(
    repo: Path,
    baseline_sha: str,
    target_sha: str,
    baseline_paths: set[str],
) -> list[dict[str, Any]]:
    # Disabling rename detection keeps the NUL record format unambiguous for arbitrary
    # paths. A rename is deliberately reported as one removed and one added path.
    result = _git(
        repo,
        "diff",
        "--numstat",
        "--no-renames",
        "-z",
        baseline_sha,
        target_sha,
        "--",
    )
    changed: list[dict[str, Any]] = []
    for raw_record in result.stdout.split(b"\0"):
        if not raw_record:
            continue
        fields = raw_record.split(b"\t", 2)
        if len(fields) != 3:
            raise GitCommandError("Git returned malformed NUL-delimited line statistics.")
        raw_additions, raw_deletions, raw_path = fields
        path = _decode_git(raw_path)
        binary = raw_additions == b"-" or raw_deletions == b"-"
        try:
            additions = None if binary else int(raw_additions)
            deletions = None if binary else int(raw_deletions)
        except ValueError as exc:
            raise GitCommandError(f"Git returned invalid line statistics for {path!r}.") from exc
        pre_existing = path in baseline_paths
        changed.append(
            {
                "additions": additions,
                "binary": binary,
                "deletions": deletions,
                "groups": _purpose_groups(path, pre_existing=pre_existing),
                "path": path,
                "pre_existing": pre_existing,
            }
        )
    return sorted(changed, key=lambda item: str(item["path"]))


def _file_summary(changed_files: Sequence[dict[str, Any]]) -> dict[str, Any]:
    additions = sum(
        int(item["additions"]) for item in changed_files if item["additions"] is not None
    )
    deletions = sum(
        int(item["deletions"]) for item in changed_files if item["deletions"] is not None
    )
    return {
        "additions": additions,
        "binary_files": sum(bool(item["binary"]) for item in changed_files),
        "deletions": deletions,
        "files": len(changed_files),
    }


def _file_groups(changed_files: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        group: sorted(str(item["path"]) for item in changed_files if group in item["groups"])
        for group in GROUP_ORDER
    }


def build_report(repo: Path, baseline_ref: str, target_ref: str) -> dict[str, Any]:
    repo = repo.expanduser().resolve()
    if not repo.is_dir():
        raise GitCommandError(f"Repository path is not a directory: {repo}")
    _git(repo, "rev-parse", "--git-dir")

    target_sha = _resolve_commit(repo, target_ref)
    if target_sha is None:
        raise GitCommandError(f"Target ref {target_ref!r} does not resolve to a commit.")

    dirty = _working_tree_is_dirty(repo)
    warnings: list[str] = []
    baseline_sha = _resolve_commit(repo, baseline_ref)

    commits: list[dict[str, str]] = []
    changed_files: list[dict[str, Any]] = []
    if baseline_sha is None:
        warnings.append(
            f"Baseline tag {baseline_ref!r} is missing or does not resolve to a commit."
        )
    else:
        ancestor = _git(
            repo,
            "merge-base",
            "--is-ancestor",
            baseline_sha,
            target_sha,
            check=False,
        )
        if ancestor.returncode == 1:
            warnings.append(f"Baseline {baseline_sha} is not an ancestor of target {target_sha}.")
        elif ancestor.returncode != 0:
            detail = _decode_git(ancestor.stderr).strip() or str(ancestor.returncode)
            raise GitCommandError(f"Could not compare baseline and target ancestry: {detail}")

        commits = [
            _commit_record(repo, sha) for sha in _commit_shas(repo, baseline_sha, target_sha)
        ]
        warnings.extend(_date_warnings(commits))
        changed_files = _changed_files(
            repo,
            baseline_sha,
            target_sha,
            _baseline_paths(repo, baseline_sha),
        )

    if dirty:
        warnings.append("Working tree is dirty; uncommitted changes are not included in the delta.")

    return {
        "baseline": {"ref": baseline_ref, "sha": baseline_sha},
        "changed_files": changed_files,
        "commit_count": len(commits),
        "commits": commits,
        "file_groups": _file_groups(changed_files),
        "file_totals": _file_summary(changed_files),
        "grouping_note": (
            "File groups are non-exclusive; pre-existing means the path existed in the "
            "baseline tree."
        ),
        "schema": SCHEMA,
        "submission_period_start": SUBMISSION_PERIOD_START_TEXT,
        "target": {"ref": target_ref, "sha": target_sha},
        "warnings": warnings,
        "working_tree": {"dirty": dirty},
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _markdown_code(value: object) -> str:
    text = str(value)
    escaped = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("|", "\\|")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f"`{escaped}`"


def _group_title(group: str) -> str:
    return group.replace("-", " ").title()


def render_markdown(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    target = report["target"]
    lines = [
        "# Faber Build Week delta",
        "",
        f"- Baseline ref: {_markdown_code(baseline['ref'])}",
        f"- Baseline commit: {_markdown_code(baseline['sha'] or 'missing')}",
        f"- Target ref: {_markdown_code(target['ref'])}",
        f"- Target commit: {_markdown_code(target['sha'])}",
        f"- Eligible commits: {report['commit_count']}",
        f"- Working tree: {'dirty' if report['working_tree']['dirty'] else 'clean'}",
        "",
        "## Warnings",
        "",
    ]
    warnings = report["warnings"]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Commits",
            "",
            "| Commit | Author date | Committer date | Subject |",
            "|---|---|---|---|",
        ]
    )
    commits = report["commits"]
    if commits:
        for commit in commits:
            lines.append(
                "| "
                + " | ".join(
                    (
                        _markdown_code(commit["sha"]),
                        _markdown_code(commit["author_date"]),
                        _markdown_code(commit["committer_date"]),
                        _markdown_code(commit["subject"]),
                    )
                )
                + " |"
            )
    else:
        lines.append("| — | — | — | No eligible commits |")

    lines.extend(
        [
            "",
            "## Changed files",
            "",
            "| Path | Additions | Deletions | Binary |",
            "|---|---:|---:|:---:|",
        ]
    )
    changed_files = report["changed_files"]
    if changed_files:
        for item in changed_files:
            additions = "—" if item["additions"] is None else str(item["additions"])
            deletions = "—" if item["deletions"] is None else str(item["deletions"])
            lines.append(
                f"| {_markdown_code(item['path'])} | {additions} | {deletions} | "
                f"{'yes' if item['binary'] else 'no'} |"
            )
    else:
        lines.append("| — | — | — | — |")

    totals = report["file_totals"]
    lines.extend(
        [
            "",
            f"Totals: {totals['files']} files, +{totals['additions']} / "
            f"-{totals['deletions']}, {totals['binary_files']} binary.",
            "",
            "## File groups",
            "",
            report["grouping_note"],
        ]
    )
    for group in GROUP_ORDER:
        lines.extend(["", f"### {_group_title(group)}", ""])
        paths = report["file_groups"][group]
        if paths:
            lines.extend(f"- {_markdown_code(path)}" for path in paths)
        else:
            lines.append("- None")
    return "\n".join(lines) + "\n"


def _write_utf8(stream: Any, value: str) -> None:
    data = value.encode("utf-8")
    binary_stream = getattr(stream, "buffer", None)
    if binary_stream is not None:
        binary_stream.write(data)
        binary_stream.flush()
    else:
        stream.write(value)
        stream.flush()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a local Build Week baseline tag with a target ref and emit a "
            "deterministic eligibility report."
        )
    )
    parser.add_argument(
        "positional_target",
        nargs="?",
        help="target ref (default: HEAD)",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="local Git repository")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE, help="baseline tag or ref")
    parser.add_argument("--target", dest="target_option", help="target ref (default: HEAD)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--format",
        choices=("markdown", "json"),
        dest="output_format",
        help="output format (default: markdown)",
    )
    output.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="output_format",
        help="shortcut for --format json",
    )
    output.add_argument(
        "--markdown",
        action="store_const",
        const="markdown",
        dest="output_format",
        help="shortcut for --format markdown",
    )
    parser.set_defaults(output_format="markdown")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.positional_target is not None and args.target_option is not None:
        parser.error("provide the target either positionally or with --target, not both")
    target = args.target_option or args.positional_target or "HEAD"

    try:
        report = build_report(args.repo, args.baseline, target)
    except GitCommandError as exc:
        _write_utf8(sys.stderr, f"build_week_delta: error: {exc}\n")
        return 2

    rendered = render_json(report) if args.output_format == "json" else render_markdown(report)
    _write_utf8(sys.stdout, rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
