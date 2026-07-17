"""Deterministic, bounded local Git context for Faber Proof."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.proof_executors import ProcessCapture, launch_bounded_process
from faber.validation import require_digest, require_non_empty_string

GIT_CONTEXT_SCHEMA = "faber.proof_git_context.v1"
DEFAULT_MAX_DIFF_BYTES = 262_144
MAX_DIFF_BYTES = 1024 * 1024
MAX_CHANGED_FILES = 512
MAX_GIT_METADATA_BYTES = 512 * 1024
GIT_TIMEOUT_SECONDS = 30

DEFAULT_EXCLUDED_PATHS = (
    ".faber/",
    ".git/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    "__pycache__/",
    "build/",
    "dist/",
    "result/",
)
DEFAULT_EXCLUDED_PREFIXES = ("result-",)
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


class GitContextError(ValidationError):
    """A local repository cannot safely provide proof-planning context."""

    def __init__(self, code: str, public_message: str) -> None:
        self.code = require_non_empty_string(code, "code")
        self.public_message = require_non_empty_string(public_message, "public_message")
        super().__init__(f"{self.code}: {self.public_message}")


def _normalized_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _normalized_path(value: str) -> str:
    if not value or "\x00" in value or "\\" in value:
        raise GitContextError("invalid_git_path", "Git returned an invalid repository path")
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value)
    if windows.drive or windows.root or posix.is_absolute():
        raise GitContextError("invalid_git_path", "Git returned a non-relative repository path")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise GitContextError("invalid_git_path", "Git returned a non-normalized repository path")
    normalized = posix.as_posix()
    if normalized != value:
        raise GitContextError("invalid_git_path", "Git returned a non-normalized repository path")
    return normalized


def _is_excluded(path: str, policy_exclusions: Sequence[str]) -> bool:
    folded = path.casefold()
    components = folded.split("/")
    if "__pycache__" in components:
        return True
    for prefix in (*DEFAULT_EXCLUDED_PATHS, *policy_exclusions):
        normalized = prefix.replace("\\", "/").strip("/").casefold()
        if not normalized:
            continue
        if folded == normalized or folded.startswith(normalized + "/"):
            return True
    return any(folded.startswith(prefix.casefold()) for prefix in DEFAULT_EXCLUDED_PREFIXES)


def _git_environment() -> dict[str, str]:
    environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
    }
    for name in ("SYSTEMROOT", "WINDIR"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise GitContextError("git_unavailable", "Git is not available on PATH")
    return str(Path(executable).resolve())


def _run_git(
    root: Path,
    arguments: Sequence[str],
    *,
    max_output_bytes: int,
    allowed_exit_codes: Sequence[int] = (0,),
) -> ProcessCapture:
    capture = launch_bounded_process(
        [_git_executable(), *arguments],
        cwd=root,
        environment=_git_environment(),
        stdin=None,
        timeout_seconds=GIT_TIMEOUT_SECONDS,
        max_output_bytes=max_output_bytes,
    )
    if capture.timed_out:
        raise GitContextError("git_timeout", "A bounded local Git operation timed out")
    if capture.output_truncated or capture.capture_incomplete:
        raise GitContextError("git_output_limit", "A local Git operation exceeded its output limit")
    if capture.exit_code not in allowed_exit_codes:
        raise GitContextError("git_error", "A local Git operation failed")
    return capture


def _decode(value: bytes, label: str) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise GitContextError("invalid_git_text", f"Git {label} is not valid UTF-8") from None


def _resolve_repository_root(repository: str | Path) -> Path:
    supplied = Path(repository).resolve(strict=True)
    if not supplied.is_dir():
        raise GitContextError("invalid_repository", "The repository path is not a directory")
    result = _run_git(
        supplied,
        ["rev-parse", "--show-toplevel"],
        max_output_bytes=8_192,
    )
    reported = Path(_decode(result.stdout, "repository root").strip()).resolve(strict=True)
    if supplied != reported:
        raise GitContextError(
            "invalid_repository_root",
            "--repo must identify the Git repository root exactly",
        )
    if (reported / ".git").is_symlink():
        raise GitContextError("invalid_repository", "A symlinked .git boundary is not supported")
    return reported


def _resolve_revision(root: Path, revision: str, field: str) -> str:
    value = require_non_empty_string(revision, field)
    if "\x00" in value or "\n" in value or "\r" in value or len(value.encode("utf-8")) > 1024:
        raise GitContextError("invalid_revision", f"{field} is malformed")
    result = _run_git(
        root,
        ["rev-parse", "--verify", "--end-of-options", f"{value}^{{commit}}"],
        max_output_bytes=8_192,
        allowed_exit_codes=(0, 1, 128),
    )
    resolved = _decode(result.stdout, field).strip()
    if result.exit_code != 0 or _COMMIT.fullmatch(resolved) is None:
        raise GitContextError("invalid_revision", f"{field} does not resolve to one commit")
    return resolved


def _candidate_created_at(root: Path, candidate_revision: str) -> str:
    result = _run_git(
        root,
        ["show", "-s", "--format=%cI", candidate_revision],
        max_output_bytes=8_192,
    )
    return require_non_empty_string(
        _decode(result.stdout, "commit timestamp").strip(), "created_at"
    )


def _changed_paths(
    root: Path,
    base_revision: str,
    candidate_revision: str,
    policy_exclusions: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    result = _run_git(
        root,
        [
            "diff",
            "--name-only",
            "-z",
            "--no-ext-diff",
            "--no-renames",
            base_revision,
            candidate_revision,
            "--",
        ],
        max_output_bytes=MAX_GIT_METADATA_BYTES,
    )
    decoded = _decode(result.stdout, "changed-file list")
    raw_paths = decoded.split("\x00")
    if raw_paths and raw_paths[-1] == "":
        raw_paths.pop()
    included: list[str] = []
    excluded: list[str] = []
    seen: set[str] = set()
    for raw in raw_paths:
        path = _normalized_path(raw)
        folded = path.casefold()
        if folded in seen:
            raise GitContextError("invalid_git_path", "Git paths are not case-insensitively unique")
        seen.add(folded)
        (excluded if _is_excluded(path, policy_exclusions) else included).append(path)
    if len(included) > MAX_CHANGED_FILES:
        raise GitContextError("context_too_large", "The diff changes too many included files")
    return tuple(sorted(included)), tuple(sorted(excluded))


def _diff_statistics(diff_text: str) -> Mapping[str, int]:
    additions = 0
    deletions = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return {"additions": additions, "deletions": deletions}


@dataclass(frozen=True)
class GitProofContext:
    repository_root: Path
    base_revision: str
    candidate_revision: str
    candidate_created_at: str
    changed_files: Sequence[str]
    excluded_changed_files: Sequence[str]
    diff_text: str
    diff_digest: str
    additions: int
    deletions: int
    empty_diff: bool
    policy_exclusions: Sequence[str]

    def __post_init__(self) -> None:
        root = self.repository_root.resolve(strict=True)
        if not root.is_dir():
            raise GitContextError("invalid_repository", "repository_root must be a directory")
        object.__setattr__(self, "repository_root", root)
        for name in ("base_revision", "candidate_revision"):
            if _COMMIT.fullmatch(getattr(self, name)) is None:
                raise GitContextError("invalid_revision", f"{name} must be a full commit ID")
        require_non_empty_string(self.candidate_created_at, "candidate_created_at")
        object.__setattr__(self, "changed_files", tuple(self.changed_files))
        object.__setattr__(self, "excluded_changed_files", tuple(self.excluded_changed_files))
        object.__setattr__(self, "policy_exclusions", tuple(self.policy_exclusions))
        if _normalized_text(self.diff_text) != self.diff_text:
            raise GitContextError("invalid_git_text", "diff_text line endings are not normalized")
        require_digest(self.diff_digest, "diff_digest")
        if sha256_digest(self.diff_text) != self.diff_digest:
            raise GitContextError("digest_mismatch", "diff_digest does not bind diff_text")
        if self.empty_diff != (self.diff_text == ""):
            raise GitContextError("invalid_git_text", "empty_diff does not match diff_text")

    @property
    def planning_diff_text(self) -> str:
        if self.empty_diff:
            return "Faber Proof context: no included changes between the selected revisions.\n"
        return self.diff_text

    @property
    def planning_diff_digest(self) -> str:
        return sha256_digest(self.planning_diff_text)

    def manifest(
        self,
        *,
        redacted_diff_text: str,
        redacted_diff_digest: str,
        redaction_summary: Mapping[str, object],
    ) -> dict[str, object]:
        manifest: dict[str, object] = {
            "schema": GIT_CONTEXT_SCHEMA,
            "repository": ".",
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "changed_files": list(self.changed_files),
            "excluded_changed_files": list(self.excluded_changed_files),
            "statistics": {
                "changed_files": len(self.changed_files),
                "additions": self.additions,
                "deletions": self.deletions,
            },
            "empty_diff": self.empty_diff,
            "source_diff_digest": self.diff_digest,
            "planning_diff_digest": self.planning_diff_digest,
            "redacted_diff_digest": redacted_diff_digest,
            "redacted_diff_text": redacted_diff_text,
            "redaction_summary": dict(redaction_summary),
            "excluded_paths": sorted(set((*DEFAULT_EXCLUDED_PATHS, *self.policy_exclusions))),
        }
        manifest["context_digest"] = sha256_digest(manifest)
        return manifest


def collect_git_proof_context(
    repository: str | Path,
    *,
    base_revision: str,
    candidate_revision: str,
    max_diff_bytes: int = DEFAULT_MAX_DIFF_BYTES,
    policy_exclusions: Sequence[str] = (),
) -> GitProofContext:
    """Collect one exact local commit diff without consulting a remote."""

    if (
        isinstance(max_diff_bytes, bool)
        or not isinstance(max_diff_bytes, int)
        or not 1 <= max_diff_bytes <= MAX_DIFF_BYTES
    ):
        raise GitContextError(
            "invalid_diff_limit",
            f"max_diff_bytes must be between 1 and {MAX_DIFF_BYTES}",
        )
    normalized_exclusions: list[str] = []
    for index, value in enumerate(policy_exclusions):
        text = require_non_empty_string(value, f"policy_exclusions[{index}]")
        if "\x00" in text or ".." in PurePosixPath(text.replace("\\", "/")).parts:
            raise GitContextError("invalid_exclusion", "A context exclusion is malformed")
        normalized_exclusions.append(text.replace("\\", "/").strip("/"))

    root = _resolve_repository_root(repository)
    base = _resolve_revision(root, base_revision, "base revision")
    candidate = _resolve_revision(root, candidate_revision, "candidate revision")
    changed_files, excluded_files = _changed_paths(root, base, candidate, normalized_exclusions)
    if changed_files:
        result = _run_git(
            root,
            [
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--unified=3",
                "--src-prefix=a/",
                "--dst-prefix=b/",
                base,
                candidate,
                "--",
                *changed_files,
            ],
            max_output_bytes=MAX_DIFF_BYTES,
        )
        raw_diff = _decode(result.stdout, "diff")
    else:
        raw_diff = ""
    diff_text = _normalized_text(raw_diff)
    try:
        diff_size = len(diff_text.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        raise GitContextError(
            "invalid_git_text", "The normalized diff is not valid UTF-8"
        ) from None
    if diff_size > max_diff_bytes:
        raise GitContextError("diff_too_large", "The included diff exceeds --max-diff-bytes")
    statistics = _diff_statistics(diff_text)
    return GitProofContext(
        repository_root=root,
        base_revision=base,
        candidate_revision=candidate,
        candidate_created_at=_candidate_created_at(root, candidate),
        changed_files=changed_files,
        excluded_changed_files=excluded_files,
        diff_text=diff_text,
        diff_digest=sha256_digest(diff_text),
        additions=statistics["additions"],
        deletions=statistics["deletions"],
        empty_diff=not diff_text,
        policy_exclusions=tuple(sorted(normalized_exclusions)),
    )


def ensure_executable_candidate(context: GitProofContext) -> None:
    """Require execution bytes to be the clean candidate commit named in the report."""

    root = context.repository_root
    head = _resolve_revision(root, "HEAD", "HEAD")
    if head != context.candidate_revision:
        raise GitContextError(
            "candidate_not_checked_out",
            "Normal proof execution requires the candidate commit to be checked out at HEAD",
        )
    for arguments in (
        ["diff", "--quiet", "--no-ext-diff", "--"],
        ["diff", "--cached", "--quiet", "--no-ext-diff", "--"],
    ):
        result = _run_git(
            root,
            arguments,
            max_output_bytes=8_192,
            allowed_exit_codes=(0, 1),
        )
        if result.exit_code != 0:
            raise GitContextError(
                "dirty_worktree",
                "Normal proof execution requires no included tracked working-tree changes",
            )
    untracked = _run_git(
        root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        max_output_bytes=MAX_GIT_METADATA_BYTES,
    )
    decoded = _decode(untracked.stdout, "untracked-file list")
    for raw_path in decoded.split("\x00"):
        if not raw_path:
            continue
        path = _normalized_path(raw_path)
        if not _is_excluded(path, context.policy_exclusions):
            raise GitContextError(
                "dirty_worktree",
                "Normal proof execution requires no included untracked files",
            )
