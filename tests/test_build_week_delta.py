from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_week_delta.py"
BASELINE_TAG = "build-week-2026-baseline"
BEFORE_PERIOD = "2026-07-12T12:00:00+00:00"
AFTER_PERIOD = "2026-07-14T12:00:00+00:00"


def _run(
    command: list[str],
    *,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=check,
        shell=False,
    )


def _git(
    repo: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return _run(["git", *args], cwd=repo, extra_env=extra_env)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "symbolic-ref", "HEAD", "refs/heads/master")
    _git(path, "config", "user.name", "Faber Test")
    _git(path, "config", "user.email", "faber-test@example.invalid")
    _git(path, "config", "core.autocrlf", "false")
    return path


def _commit(repo: Path, message: str, date: str) -> str:
    _git(repo, "add", "--all")
    _git(
        repo,
        "commit",
        "-m",
        message,
        extra_env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
    )
    return _git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()


def _seed_baseline(repo: Path) -> str:
    (repo / "existing.txt").write_text("before\n", encoding="utf-8")
    sha = _commit(repo, "Pre-period baseline", BEFORE_PERIOD)
    _git(repo, "tag", BASELINE_TAG)
    return sha


def _run_delta(
    repo: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return _run(
        [sys.executable, os.fspath(SCRIPT), "--repo", os.fspath(repo), *args],
        cwd=ROOT,
        extra_env=extra_env,
        check=False,
    )


def _json_report(
    repo: Path, *args: str
) -> tuple[subprocess.CompletedProcess[bytes], dict[str, object]]:
    result = _run_delta(repo, "--json", *args)
    return result, json.loads(result.stdout.decode("utf-8"))


def test_missing_baseline_tag_emits_a_structured_warning(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "missing-baseline")
    (repo / "only.txt").write_text("content\n", encoding="utf-8")
    target_sha = _commit(repo, "Repository without tag", AFTER_PERIOD)

    result, report = _json_report(repo)

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert report["baseline"] == {"ref": BASELINE_TAG, "sha": None}
    assert report["target"] == {"ref": "HEAD", "sha": target_sha}
    assert report["commit_count"] == 0
    assert report["changed_files"] == []
    assert any("Baseline tag" in warning and "missing" in warning for warning in report["warnings"])


def test_valid_range_reports_commits_stats_and_file_groups(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "valid-range")
    baseline_sha = _seed_baseline(repo)
    (repo / "existing.txt").write_text("after\nmore\n", encoding="utf-8")
    source = repo / "src" / "faber" / "proof.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    target_sha = _commit(repo, "Add proof core", AFTER_PERIOD)

    result, report = _json_report(repo, "--target", "HEAD")

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert report["baseline"] == {"ref": BASELINE_TAG, "sha": baseline_sha}
    assert report["target"] == {"ref": "HEAD", "sha": target_sha}
    assert report["commit_count"] == 1
    assert report["commits"] == [
        {
            "author_date": AFTER_PERIOD,
            "committer_date": AFTER_PERIOD,
            "sha": target_sha,
            "subject": "Add proof core",
        }
    ]
    files = {item["path"]: item for item in report["changed_files"]}
    assert files["existing.txt"]["pre_existing"] is True
    assert files["existing.txt"]["additions"] == 2
    assert files["existing.txt"]["deletions"] == 1
    assert files["src/faber/proof.py"]["pre_existing"] is False
    assert files["src/faber/proof.py"]["groups"] == ["build-week-core"]
    assert report["file_totals"] == {
        "additions": 3,
        "binary_files": 0,
        "deletions": 1,
        "files": 2,
    }
    assert report["warnings"] == []


def test_dirty_working_tree_is_reported_without_including_uncommitted_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "dirty-tree")
    _seed_baseline(repo)
    (repo / "uncommitted.txt").write_text("not eligible yet\n", encoding="utf-8")

    result, report = _json_report(repo)

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert report["working_tree"] == {"dirty": True}
    assert report["changed_files"] == []
    assert any("Working tree is dirty" in warning for warning in report["warnings"])


def test_json_output_is_byte_for_byte_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "deterministic")
    _seed_baseline(repo)
    (repo / "zeta.txt").write_text("z\n", encoding="utf-8")
    (repo / "alpha.txt").write_text("a\n", encoding="utf-8")
    _commit(repo, "Two files", AFTER_PERIOD)

    first = _run_delta(repo, "--format", "json")
    second = _run_delta(repo, "--format", "json")

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    report = json.loads(first.stdout.decode("utf-8"))
    assert [item["path"] for item in report["changed_files"]] == ["alpha.txt", "zeta.txt"]


def test_paths_with_spaces_remain_single_changed_file_records(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "path-spaces")
    _seed_baseline(repo)
    notes = repo / "docs" / "notes with spaces.md"
    notes.parent.mkdir()
    notes.write_text("Build Week notes\n", encoding="utf-8")
    _commit(repo, "Add notes", AFTER_PERIOD)

    result, report = _json_report(repo)

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert [item["path"] for item in report["changed_files"]] == ["docs/notes with spaces.md"]
    assert report["file_groups"]["docs"] == ["docs/notes with spaces.md"]


def test_windows_safe_argument_invocation_and_utf8_output(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repository with spaces")
    _seed_baseline(repo)
    unicode_file = repo / "nested directory" / "café Ω.txt"
    unicode_file.parent.mkdir()
    unicode_file.write_text("naïve content\n", encoding="utf-8")
    _commit(repo, "Añadir café Ω", AFTER_PERIOD)

    # The script writes UTF-8 bytes directly, so even an ASCII Python console setting
    # cannot corrupt Git metadata or a repository path passed as one argv element.
    result = _run_delta(repo, "--json", extra_env={"PYTHONIOENCODING": "ascii:strict"})

    assert result.returncode == 0, result.stderr.decode("utf-8")
    report = json.loads(result.stdout.decode("utf-8"))
    assert report["commits"][0]["subject"] == "Añadir café Ω"
    assert report["changed_files"][0]["path"] == "nested directory/café Ω.txt"


def test_pre_submission_commit_dates_emit_warnings(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "old-date")
    _seed_baseline(repo)
    (repo / "late-history.txt").write_text("dated too early\n", encoding="utf-8")
    old_sha = _commit(repo, "Child commit with old dates", "2026-07-13T15:59:59+00:00")

    result, report = _json_report(repo)

    assert result.returncode == 0, result.stderr.decode("utf-8")
    warnings = report["warnings"]
    assert any(old_sha in warning and "author date" in warning for warning in warnings)
    assert any(old_sha in warning and "committer date" in warning for warning in warnings)


def test_markdown_output_contains_the_same_boundary_data(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "markdown")
    baseline_sha = _seed_baseline(repo)
    (repo / "change.txt").write_text("change\n", encoding="utf-8")
    target_sha = _commit(repo, "Markdown report", AFTER_PERIOD)

    result = _run_delta(repo, "--markdown")
    output = result.stdout.decode("utf-8")

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert "# Faber Build Week delta" in output
    assert baseline_sha in output
    assert target_sha in output
    assert "Markdown report" in output


def test_output_files_are_written_from_one_report_snapshot(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "output-files")
    _seed_baseline(repo)
    (repo / "change.txt").write_text("change\n", encoding="utf-8")
    target_sha = _commit(repo, "Write reports", AFTER_PERIOD)
    json_path = tmp_path / "reports" / "delta.json"
    markdown_path = tmp_path / "reports" / "delta.md"

    result = _run_delta(
        repo,
        "--json",
        "--json-out",
        os.fspath(json_path),
        "--markdown-out",
        os.fspath(markdown_path),
    )

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert json_path.read_bytes() == result.stdout
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["target"]["sha"] == target_sha
    assert report["working_tree"] == {"dirty": False}
    assert target_sha in markdown_path.read_text(encoding="utf-8")
