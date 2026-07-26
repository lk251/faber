"""Deterministic, bounded privacy checks for Faber Proof artifacts."""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.digests import sha256_digest
from faber.errors import ValidationError

PRIVACY_AUDIT_SCHEMA = "faber.proof_artifact_privacy_audit.v1"
DEFAULT_MAX_FILE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_RAW_OUTPUT_BYTES = 64_000

_CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b")),
    (
        "aws_access_key",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|authorization|password|secret|token)"
            r"[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_./+=:-]{12,})"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}")),
)
_MACHINE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+"),
    re.compile(r"(?i)\b[A-Z]:[\\/]+Windows[\\/]+Temp(?:[\\/]|\\b)"),
    re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s\"'<>]+"),
    re.compile(r"(?<![A-Za-z0-9_])/tmp(?:/|\\b)"),
)
_EXTERNAL_ASSET_PATTERN = re.compile(
    r"(?is)<(?:img|script|iframe)\b[^>]*\bsrc\s*=\s*[\"']https?://"
    r"|<link\b[^>]*\bhref\s*=\s*[\"']https?://"
)
_RAW_OUTPUT_KEYS = {
    "raw_model_output",
    "raw_provider_output",
    "raw_response",
    "raw_verifier_output",
    "unbounded_output",
}
_BOUNDED_OUTPUT_KEYS = {"stdout", "stderr", "output"}
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./+=:-]{8,}")


@dataclass(frozen=True)
class PrivacyFinding:
    code: str
    path: str
    evidence_digest: str
    message: str
    severity: str = "error"

    def __post_init__(self) -> None:
        if self.severity not in {"error", "warning"}:
            raise ValidationError("privacy finding severity must be error or warning")
        for field in ("code", "path", "evidence_digest", "message"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field):
                raise ValidationError(f"privacy finding {field} must be non-empty text")

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "evidence_digest": self.evidence_digest,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProofArtifactPrivacyReport:
    roots: Sequence[str]
    scanned_files: int
    scanned_bytes: int
    findings: Sequence[PrivacyFinding]
    scope: str = (
        "Deterministic checks for common credential shapes, explicitly forbidden values, "
        "machine paths, external HTML assets, symlinks, oversized files, and raw-output fields. "
        "This is not comprehensive secret detection or a substitute for human review."
    )
    schema: str = PRIVACY_AUDIT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PRIVACY_AUDIT_SCHEMA:
            raise ValidationError("unsupported privacy audit schema")
        if self.scanned_files < 0 or self.scanned_bytes < 0:
            raise ValidationError("privacy audit counters must be nonnegative")
        if any(not isinstance(item, PrivacyFinding) for item in self.findings):
            raise ValidationError("privacy audit findings must be PrivacyFinding records")
        object.__setattr__(self, "roots", tuple(sorted(set(self.roots))))
        object.__setattr__(
            self,
            "findings",
            tuple(
                sorted(
                    self.findings,
                    key=lambda item: (item.severity, item.path, item.code, item.evidence_digest),
                )
            ),
        )

    @property
    def passed(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 2

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": "pass" if self.passed else "fail",
            "scope": self.scope,
            "roots": list(self.roots),
            "scanned_files": self.scanned_files,
            "scanned_bytes": self.scanned_bytes,
            "finding_count": len(self.findings),
            "findings": [item.to_dict() for item in self.findings],
        }

    def markdown(self) -> str:
        lines = [
            "# Faber Proof artifact privacy audit",
            "",
            f"Status: **{'PASS' if self.passed else 'FAIL'}**",
            "",
            f"- Files scanned: {self.scanned_files}",
            f"- Bytes scanned: {self.scanned_bytes}",
            f"- Findings: {len(self.findings)}",
            f"- Scope: {self.scope}",
            "",
        ]
        if not self.findings:
            lines.append("No covered privacy or secret finding was detected.")
        else:
            lines.extend(
                [
                    "| Severity | Code | Path | Evidence digest |",
                    "|---|---|---|---|",
                ]
            )
            lines.extend(
                f"| {item.severity} | `{item.code}` | `{item.path}` | "
                f"`{item.evidence_digest}` |"
                for item in self.findings
            )
        return "\n".join(lines) + "\n"


def _finding(code: str, path: str, evidence: str | bytes, message: str) -> PrivacyFinding:
    return PrivacyFinding(
        code=code,
        path=path,
        evidence_digest=sha256_digest(evidence),
        message=message,
    )


def _root_label(path: Path) -> str:
    return path.name or "artifact-root"


def _iter_files(root: Path) -> Iterable[tuple[Path, str]]:
    if root.is_symlink():
        yield root, _root_label(root)
        return
    if root.is_file():
        yield root, _root_label(root)
        return
    if not root.is_dir():
        return
    label = _root_label(root)
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or path.is_file():
            yield path, f"{label}/{relative}"


def _string_values(value: object, *, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _string_values(value[key], prefix=child)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            yield from _string_values(item, prefix=f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


def _raw_output_findings(
    payload: object,
    *,
    path: str,
    max_raw_output_bytes: int,
) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for field, value in _string_values(payload):
        key = field.rsplit(".", 1)[-1].split("[", 1)[0]
        size = len(value.encode("utf-8"))
        if key in _RAW_OUTPUT_KEYS:
            findings.append(
                _finding(
                    "raw_unbounded_output",
                    path,
                    value,
                    f"Raw model or verifier output is stored in field {field!r}.",
                )
            )
        elif key in _BOUNDED_OUTPUT_KEYS and size > max_raw_output_bytes:
            findings.append(
                _finding(
                    "output_exceeds_audit_bound",
                    path,
                    value,
                    f"Output field {field!r} exceeds the configured privacy-audit bound.",
                )
            )
    return findings


def _forbidden_hash_findings(
    text: str,
    *,
    path: str,
    forbidden_hashes: set[str],
) -> list[PrivacyFinding]:
    if not forbidden_hashes:
        return []
    candidates = {text, *(line.strip() for line in text.splitlines())}
    candidates.update(_TOKEN_PATTERN.findall(text))
    findings: list[PrivacyFinding] = []
    for candidate in sorted(value for value in candidates if value):
        digest = sha256_digest(candidate)
        if digest in forbidden_hashes:
            findings.append(
                PrivacyFinding(
                    code="forbidden_value_hash",
                    path=path,
                    evidence_digest=digest,
                    message="Artifact contains a value whose digest is explicitly forbidden.",
                )
            )
    return findings


def audit_proof_artifacts(
    roots: Sequence[str | Path],
    *,
    forbidden_literals: Sequence[str] = (),
    forbidden_hashes: Sequence[str] = (),
    home_directory: str | Path | None = None,
    temp_directory: str | Path | None = None,
    username: str | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_raw_output_bytes: int = DEFAULT_MAX_RAW_OUTPUT_BYTES,
) -> ProofArtifactPrivacyReport:
    """Audit artifact trees without recording matched secret values."""

    if not roots:
        raise ValidationError("at least one privacy audit root is required")
    if max_file_bytes < 1 or max_raw_output_bytes < 1:
        raise ValidationError("privacy audit byte limits must be positive")
    forbidden = tuple(sorted({value for value in forbidden_literals if value}))
    forbidden_digests = set(forbidden_hashes)
    for digest in forbidden_digests:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValidationError("forbidden hashes must use canonical sha256:<hex> form")
    explicit_paths = {
        str(Path(home_directory).resolve()).casefold()
        if home_directory is not None
        else str(Path.home().resolve()).casefold(),
        str(Path(temp_directory).resolve()).casefold()
        if temp_directory is not None
        else str(Path(tempfile.gettempdir()).resolve()).casefold(),
    }
    explicit_paths.discard("")
    normalized_username = username.strip().casefold() if username else None

    resolved_roots = [Path(root).resolve(strict=False) for root in roots]
    findings: list[PrivacyFinding] = []
    scanned_files = 0
    scanned_bytes = 0
    for root in resolved_roots:
        if not root.exists() and not root.is_symlink():
            findings.append(
                _finding(
                    "missing_audit_root",
                    _root_label(root),
                    str(root),
                    "The requested artifact root does not exist.",
                )
            )
            continue
        for path, label in _iter_files(root):
            if path.is_symlink():
                findings.append(
                    _finding(
                        "symlink_not_audited",
                        label,
                        path.name,
                        "Symlinked artifacts are rejected because their target is "
                        "outside the audit tree.",
                    )
                )
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                findings.append(
                    _finding(
                        "artifact_unreadable",
                        label,
                        path.name,
                        "Artifact could not be read for privacy inspection.",
                    )
                )
                continue
            scanned_files += 1
            scanned_bytes += len(raw)
            if len(raw) > max_file_bytes:
                findings.append(
                    _finding(
                        "artifact_too_large",
                        label,
                        raw[:1024],
                        "Artifact exceeds the deterministic privacy-audit file-size bound.",
                    )
                )
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(
                    _finding(
                        "non_utf8_artifact",
                        label,
                        raw[:1024],
                        "Artifact is not UTF-8 and cannot be inspected by this text audit.",
                    )
                )
                continue

            for code, pattern in _CREDENTIAL_PATTERNS:
                for match in pattern.finditer(text):
                    evidence = match.group(0)
                    findings.append(
                        _finding(
                            code,
                            label,
                            evidence,
                            "Artifact matches a covered credential or private-key pattern.",
                        )
                    )
            for literal in forbidden:
                if literal in text:
                    findings.append(
                        _finding(
                            "forbidden_literal",
                            label,
                            literal,
                            "Artifact contains an explicitly forbidden fixture or "
                            "environment value.",
                        )
                    )
            findings.extend(
                _forbidden_hash_findings(
                    text,
                    path=label,
                    forbidden_hashes=forbidden_digests,
                )
            )
            folded = text.casefold()
            for explicit in explicit_paths:
                if explicit and explicit in folded:
                    findings.append(
                        _finding(
                            "machine_specific_path",
                            label,
                            explicit,
                            "Artifact contains the active home or temporary directory.",
                        )
                    )
            if normalized_username and normalized_username in folded:
                findings.append(
                    _finding(
                        "machine_specific_username",
                        label,
                        normalized_username,
                        "Artifact contains the explicitly supplied machine user name.",
                    )
                )
            for pattern in _MACHINE_PATH_PATTERNS:
                for match in pattern.finditer(text):
                    findings.append(
                        _finding(
                            "machine_specific_path",
                            label,
                            match.group(0),
                            "Artifact contains a covered absolute machine path.",
                        )
                    )
            if path.suffix.casefold() in {".html", ".htm"} and _EXTERNAL_ASSET_PATTERN.search(text):
                findings.append(
                    _finding(
                        "external_report_asset",
                        label,
                        "external-report-asset",
                        "Self-contained HTML references an external script, frame, "
                        "image, or stylesheet.",
                    )
                )
            if path.suffix.casefold() == ".json":
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    findings.append(
                        _finding(
                            "invalid_json_artifact",
                            label,
                            raw,
                            "JSON artifact is malformed and cannot be structurally audited.",
                        )
                    )
                else:
                    findings.extend(
                        _raw_output_findings(
                            payload,
                            path=label,
                            max_raw_output_bytes=max_raw_output_bytes,
                        )
                    )
    return ProofArtifactPrivacyReport(
        roots=[_root_label(path) for path in resolved_roots],
        scanned_files=scanned_files,
        scanned_bytes=scanned_bytes,
        findings=findings,
    )


def write_privacy_report(
    report: ProofArtifactPrivacyReport,
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> None:
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical_json(report.to_dict()) + "\n", encoding="utf-8", newline="\n")
    if markdown_path is not None:
        target = Path(markdown_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report.markdown(), encoding="utf-8", newline="\n")
