#!/usr/bin/env python3
"""Run deterministic machine and human-gate checks for the Faber Proof submission."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from faber.proof_privacy import audit_proof_artifacts  # noqa: E402

SCHEMA = "faber.final_submission_audit.v1"
EXPECTED_BRANCH = "build-week/faber-proof"
BASELINE_REF = "build-week-2026-baseline"
EXPECTED_BASELINE_SHA = "64f775cfe2f622837bd9aaa40f6369aa22af1d80"
FINAL_TAG = "build-week-2026-submission"
HUMAN_GATE_SCHEMA = "faber.build_week_submission_human_gates.v1"
HUMAN_GATE_IDS = (
    "feedback_session",
    "deadline_status",
    "live_provenance",
    "independent_audits",
    "judge_repository_access",
    "public_video",
    "devpost",
    "final_tag",
)
ALLOWED_HUMAN_MARKERS = {
    "HUMAN_GATE::FINAL_SUBMISSION_REF",
    "HUMAN_GATE::PUBLIC_YOUTUBE_URL",
    "HUMAN_GATE::VIDEO_DURATION",
    "HUMAN_GATE::VIDEO_MODE",
    "HUMAN_GATE::VIDEO_TAKE_ID",
}
ARCHIVED_SUBMISSION_README = "docs/BUILD_WEEK_SUBMISSION_README.md"
REQUIRED_ARTIFACTS = (
    "README.md",
    ARCHIVED_SUBMISSION_README,
    "docs/JUDGE_QUICKSTART.md",
    "docs/DEVPOST_SUBMISSION.md",
    "docs/DEMO_SCRIPT.md",
    "docs/DEMO_SHOT_LIST.md",
    "docs/DEMO_RECORDING_CHECKLIST.md",
    "docs/SUBMISSION_IMAGES.md",
    "docs/submission-assets/demo-comparison.svg",
    "docs/submission-assets/trust-boundary.svg",
    "scripts/check_demo_script.py",
    "scripts/final_submission_audit.py",
    "codex/build-week/submission-human-gates.json",
)
SUBMISSION_DOCS = (
    ARCHIVED_SUBMISSION_README,
    "docs/JUDGE_QUICKSTART.md",
    "docs/DEVPOST_SUBMISSION.md",
    "docs/DEMO_SCRIPT.md",
    "docs/DEMO_SHOT_LIST.md",
    "docs/DEMO_RECORDING_CHECKLIST.md",
    "docs/SUBMISSION_IMAGES.md",
)
PRIVACY_PATHS = (
    "README.md",
    ARCHIVED_SUBMISSION_README,
    "docs/JUDGE_QUICKSTART.md",
    "docs/DEVPOST_SUBMISSION.md",
    "docs/DEMO_SCRIPT.md",
    "docs/DEMO_SHOT_LIST.md",
    "docs/DEMO_RECORDING_CHECKLIST.md",
    "docs/SUBMISSION_IMAGES.md",
    "docs/submission-assets",
    "codex/build-week/submission-human-gates.json",
    "examples/build-week-proof/expected",
    "docs/generated/BUILD_WEEK_EVAL_RESULTS.json",
    "docs/generated/BUILD_WEEK_EVAL_RESULTS.md",
    "docs/generated/BUILD_WEEK_PERFORMANCE_HB2.json",
    "docs/generated/BUILD_WEEK_PERFORMANCE_HB2.md",
    "docs/generated/DEVELOPMENT_REPORT_REGENERATION.json",
    "docs/generated/DEVELOPMENT_REPORT_REGENERATION.md",
)
README_SECTIONS = (
    "Thirty-second explanation",
    "Watch the demo",
    "Run the no-key proof demo",
    "What the blocked report proves",
    "How it works",
    "Why this is not another AI code reviewer",
    "GPT-5.6 usage",
    "Codex usage and the repository-scoped skill",
    "What existed before Build Week and what was added during Build Week",
    "Technical decisions made by the human entrant",
    "Security, privacy, authority, and runtime limitations",
    "Supported platforms and installation paths",
    "Tests, evals, and clean-install evidence",
    "Business and adoption path",
    "Repository map and deeper Faber documentation",
)
GENERIC_PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|REPLACE_ME|INSERT_[A-Z0-9_]+)\b|<[^>\n]*placeholder[^>\n]*>",
    flags=re.IGNORECASE,
)
HUMAN_MARKER_PATTERN = re.compile(r"HUMAN_GATE::[A-Z0-9_]+")
YOUTUBE_PATTERN = re.compile(r"https://(?:www\.)?(?:youtube\.com|youtu\.be)/", re.IGNORECASE)


@dataclass(frozen=True)
class AuditCheck:
    id: str
    category: str
    status: str
    detail: str
    command: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AuditError(RuntimeError):
    """A deterministic audit prerequisite is malformed or unavailable."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path = REPOSITORY_ROOT,
    environment: Mapping[str, str] | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if environment is not None:
        env.update(environment)
    return subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )


def _git(*args: str, check: bool = True) -> str:
    result = _run(["git", "-c", "color.ui=false", *args], timeout=120)
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        raise AuditError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def _resolve_commit(ref: str) -> str | None:
    result = _run(
        ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"],
        timeout=120,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise AuditError(f"Git returned an invalid commit for {ref!r}.")
    return value


def _check(
    check_id: str,
    category: str,
    passed: bool,
    pass_detail: str,
    fail_detail: str,
    *,
    command: str | None = None,
) -> AuditCheck:
    return AuditCheck(
        id=check_id,
        category=category,
        status="pass" if passed else "fail",
        detail=pass_detail if passed else fail_detail,
        command=command,
    )


def _read_text(relative: str) -> str:
    return (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def check_required_artifacts() -> AuditCheck:
    missing = [path for path in REQUIRED_ARTIFACTS if not (REPOSITORY_ROOT / path).is_file()]
    return _check(
        "submission_artifacts",
        "static",
        not missing,
        f"{len(REQUIRED_ARTIFACTS)} required machine artifacts are present.",
        "Missing artifacts: " + ", ".join(missing),
    )


def check_readme() -> AuditCheck:
    text = _read_text(ARCHIVED_SUBMISSION_README)
    missing_sections = [section for section in README_SECTIONS if f"## {section}" not in text]
    required_fragments = (
        "Faber Proof",
        "Codex can write the patch. Faber makes the patch prove itself.",
        "BAD PATCH   REPAIRED PATCH",
        "Ordinary tests              PASS          PASS",
        "Faber Proof verdict        BLOCK          PASS",
        "faber demo proof --mode replay",
        "fake-development",
        "not a production sandbox",
        "not universal program correctness",
        "build-week-2026-baseline",
    )
    missing_fragments = [fragment for fragment in required_fragments if fragment not in text]
    passed = "# Faber Proof" in text and not missing_sections and not missing_fragments
    detail_parts = []
    if missing_sections:
        detail_parts.append("sections=" + ", ".join(missing_sections))
    if missing_fragments:
        detail_parts.append("fragments=" + ", ".join(missing_fragments))
    return _check(
        "judge_readme",
        "static",
        passed,
        (
            "Archived submission README has the required comparison, no-key path, "
            "honesty, and 15 sections."
        ),
        "Archived submission README requirements missing: " + "; ".join(detail_parts),
    )


def check_submission_docs() -> AuditCheck:
    missing_tokens: list[str] = []
    devpost = _read_text("docs/DEVPOST_SUBMISSION.md")
    for token in (
        "## Project name",
        "## Tagline",
        "## One-sentence description",
        "## Problem",
        "## What it does",
        "## Why it is novel",
        "## How it was built",
        "## GPT-5.6 use",
        "## Codex use",
        "## Human technical and product decisions",
        "## Challenges and tradeoffs",
        "## Accomplishments",
        "## Potential impact and business path",
        "## What is next",
        "## Built with",
        "## Category",
        "## Links and IDs",
    ):
        if token not in devpost:
            missing_tokens.append(f"DEVPOST:{token}")
    quickstart = _read_text("docs/JUDGE_QUICKSTART.md")
    for token in (
        "Windows",
        "Linux",
        "macOS",
        "Wheel install variant",
        "Editable development variant",
        "Validate bundle integrity",
        "Optional guarded live path",
        "Runtime expectations",
        "Troubleshooting",
        "Cleanup and uninstall",
    ):
        if token not in quickstart:
            missing_tokens.append(f"QUICKSTART:{token}")
    passed = not missing_tokens
    return _check(
        "submission_document_content",
        "static",
        passed,
        "Judge quickstart and Devpost draft contain all required machine sections.",
        "Missing document tokens: " + ", ".join(missing_tokens),
    )


def placeholder_issues(
    documents: Mapping[str, str],
) -> tuple[list[str], set[str], set[str]]:
    generic: list[str] = []
    unknown_human: set[str] = set()
    seen_human: set[str] = set()
    for relative, text in documents.items():
        if match := GENERIC_PLACEHOLDER_PATTERN.search(text):
            generic.append(f"{relative}:{match.group(0)}")
        markers = set(HUMAN_MARKER_PATTERN.findall(text))
        seen_human.update(markers)
        unknown_human.update(markers - ALLOWED_HUMAN_MARKERS)
    required_markers = {
        "HUMAN_GATE::FINAL_SUBMISSION_REF",
        "HUMAN_GATE::PUBLIC_YOUTUBE_URL",
    }
    missing_human = required_markers - seen_human
    return generic, unknown_human, missing_human


def check_placeholders() -> AuditCheck:
    documents = {relative: _read_text(relative) for relative in SUBMISSION_DOCS}
    generic, unknown_human, missing_human = placeholder_issues(documents)
    passed = not generic and not unknown_human and not missing_human
    details = []
    if generic:
        details.append("generic=" + ", ".join(generic))
    if unknown_human:
        details.append("unknown=" + ", ".join(sorted(unknown_human)))
    if missing_human:
        details.append("missing=" + ", ".join(sorted(missing_human)))
    return _check(
        "placeholder_policy",
        "static",
        passed,
        "No generic machine placeholder exists; only approved explicit human-gate markers remain.",
        "Placeholder policy failed: " + "; ".join(details),
    )


def check_svg_assets() -> AuditCheck:
    errors: list[str] = []
    for relative in (
        "docs/submission-assets/demo-comparison.svg",
        "docs/submission-assets/trust-boundary.svg",
    ):
        path = REPOSITORY_ROOT / relative
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        if not root.tag.endswith("svg"):
            errors.append(f"{relative}: root is not svg")
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?:https?:)?//", text.replace("http://www.w3.org/2000/svg", "")):
            errors.append(f"{relative}: external reference")
        if "<script" in text.casefold() or "<foreignobject" in text.casefold():
            errors.append(f"{relative}: active or foreign content")
    return _check(
        "submission_svg_assets",
        "static",
        not errors,
        "Original SVG sources parse and contain no external or active content.",
        "SVG validation failed: " + "; ".join(errors),
    )


def load_human_gates(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"human-gate state is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise AuditError("human-gate state must be a JSON object")
    return payload


def _gate_map(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if payload.get("schema") != HUMAN_GATE_SCHEMA:
        raise AuditError("human-gate schema is missing or unsupported")
    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list):
        raise AuditError("human-gate state must contain a gates array")
    gates: dict[str, Mapping[str, Any]] = {}
    for raw_gate in raw_gates:
        if not isinstance(raw_gate, dict):
            raise AuditError("every human gate must be an object")
        gate_id = raw_gate.get("id")
        status = raw_gate.get("status")
        evidence = raw_gate.get("evidence")
        if not isinstance(gate_id, str) or gate_id in gates:
            raise AuditError("human gate IDs must be unique strings")
        if status not in {"complete", "incomplete"}:
            raise AuditError(f"human gate {gate_id!r} has an invalid status")
        if not isinstance(evidence, dict):
            raise AuditError(f"human gate {gate_id!r} must contain evidence")
        gates[gate_id] = raw_gate
    missing = set(HUMAN_GATE_IDS) - set(gates)
    extra = set(gates) - set(HUMAN_GATE_IDS)
    if missing or extra:
        raise AuditError(
            "human gate IDs do not match the required set "
            f"(missing={sorted(missing)}, extra={sorted(extra)})"
        )
    return gates


def _gate_evidence(gate: Mapping[str, Any]) -> Mapping[str, Any]:
    evidence = gate["evidence"]
    assert isinstance(evidence, dict)
    return evidence


def validate_human_gates(
    payload: Mapping[str, Any],
    *,
    audited_commit: str,
    final_tag_commit: str | None,
) -> tuple[list[dict[str, object]], list[str]]:
    gates = _gate_map(payload)
    invalid: list[str] = []

    feedback = gates["feedback_session"]
    feedback_evidence = _gate_evidence(feedback)
    if (
        feedback["status"] != "complete"
        or feedback_evidence.get("session_id") != "019f6d53-0a3d-71d3-abd7-749dc4a3784c"
    ):
        invalid.append("feedback_session must retain the recorded primary session ID")

    deadline = gates["deadline_status"]
    deadline_evidence = _gate_evidence(deadline)
    deadline_supported = bool(deadline_evidence.get("timely_submission_confirmed")) or bool(
        deadline_evidence.get("organizer_authorized_modification")
    )
    if deadline["status"] == "complete" and not deadline_supported:
        invalid.append(
            "deadline_status completion requires timely-submission or organizer evidence"
        )

    live = gates["live_provenance"]
    live_evidence = _gate_evidence(live)
    if live["status"] == "complete" and (
        live_evidence.get("provenance") != "live-reviewed"
        or not live_evidence.get("reviewer")
        or not live_evidence.get("review_manifest")
    ):
        invalid.append("live_provenance completion requires reviewed live evidence")

    audits = gates["independent_audits"]
    audit_evidence = _gate_evidence(audits)
    required_audits = set(audit_evidence.get("required_audits", []))
    completed_audits = set(audit_evidence.get("completed_audits", []))
    if audits["status"] == "complete" and (
        required_audits != {"A1", "A2", "A3", "A4", "A5"}
        or completed_audits != required_audits
        or audit_evidence.get("open_p0_findings") != []
    ):
        invalid.append("independent_audits completion requires A1-A5 green and no P0 finding")

    access = gates["judge_repository_access"]
    access_evidence = _gate_evidence(access)
    required_addresses = {"testing@devpost.com", "build-week-event@openai.com"}
    if access["status"] == "complete" and (
        set(access_evidence.get("addresses", [])) != required_addresses
        or access_evidence.get("attested") is not True
        or access_evidence.get("verified_from_clean_context") is not True
    ):
        invalid.append("judge_repository_access completion requires both verified addresses")

    video = gates["public_video"]
    video_evidence = _gate_evidence(video)
    video_url = video_evidence.get("url")
    video_duration = video_evidence.get("duration_seconds")
    if video["status"] == "complete" and (
        not isinstance(video_url, str)
        or not YOUTUBE_PATTERN.match(video_url)
        or not isinstance(video_duration, int | float)
        or not 1 <= video_duration < 180
        or video_evidence.get("audio_attested") is not True
        or video_evidence.get("public_attested") is not True
        or video_evidence.get("verified_signed_out") is not True
    ):
        invalid.append(
            "public_video completion requires a public verified narrated video under 180s"
        )

    devpost = gates["devpost"]
    devpost_evidence = _gate_evidence(devpost)
    if devpost["status"] == "complete" and (
        not deadline_supported
        or not devpost_evidence.get("url")
        or not devpost_evidence.get("submitted_at")
        or devpost_evidence.get("preview_attested") is not True
        or devpost_evidence.get("final_commit") != audited_commit
    ):
        invalid.append("devpost completion requires permitted status and the audited commit")

    final_tag = gates["final_tag"]
    final_tag_evidence = _gate_evidence(final_tag)
    if final_tag["status"] == "complete" and (
        final_tag_evidence.get("tag") != FINAL_TAG
        or final_tag_evidence.get("commit") != audited_commit
        or final_tag_commit != audited_commit
        or not final_tag_evidence.get("audit_report_digest")
    ):
        invalid.append("final_tag completion requires the audited commit and report digest")
    if final_tag["status"] == "incomplete" and final_tag_commit is not None:
        invalid.append("final submission tag exists while its human gate is incomplete")

    records = [
        {
            "id": gate_id,
            "status": gates[gate_id]["status"],
            "evidence_present": bool(_gate_evidence(gates[gate_id])),
        }
        for gate_id in HUMAN_GATE_IDS
    ]
    return records, invalid


def _command_check(
    check_id: str,
    command: Sequence[str],
    *,
    timeout: int = 900,
    environment: Mapping[str, str] | None = None,
) -> AuditCheck:
    display = _display_command(command)
    result = _run(command, environment=environment, timeout=timeout)
    if result.returncode != 0:
        tail = (result.stdout + "\n" + result.stderr).strip()[-2000:]
        if tail:
            print(f"{check_id} failed:\n{tail}", file=sys.stderr)
        return AuditCheck(
            id=check_id,
            category="command",
            status="fail",
            detail=f"Command exited {result.returncode}.",
            command=display,
        )
    return AuditCheck(
        id=check_id,
        category="command",
        status="pass",
        detail="Command exited 0.",
        command=display,
    )


def _not_run_command_check(check_id: str, command: Sequence[str]) -> AuditCheck:
    return AuditCheck(
        id=check_id,
        category="command",
        status="not_run",
        detail="Pass --run-machine-checks to execute this release gate.",
        command=_display_command(command),
    )


def _display_command(command: Sequence[str]) -> str:
    portable = ["python" if item == sys.executable else item for item in command]
    return subprocess.list2cmdline(portable)


def _demo_check(*, run: bool) -> AuditCheck:
    command = [
        sys.executable,
        "-m",
        "faber.cli",
        "demo",
        "proof",
        "--mode",
        "replay",
        "--out-dir",
        "<temporary-directory>",
        "--json",
    ]
    if not run:
        return _not_run_command_check("replay_demo", command)
    with tempfile.TemporaryDirectory(prefix="faber-final-audit-demo-") as temporary:
        actual_command = [
            *command[:8],
            str(Path(temporary) / "demo"),
            "--json",
        ]
        environment = {"PYTHONPATH": os.fspath(SOURCE_ROOT), "FABER_LIVE_OPENAI_TEST": "0"}
        result = _run(actual_command, environment=environment, timeout=180)
        if result.returncode != 0:
            print((result.stdout + "\n" + result.stderr)[-2000:], file=sys.stderr)
            return AuditCheck(
                id="replay_demo",
                category="command",
                status="fail",
                detail=f"Replay demo exited {result.returncode}.",
                command=_display_command(command),
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return AuditCheck(
                id="replay_demo",
                category="command",
                status="fail",
                detail="Replay demo did not emit valid JSON.",
                command=_display_command(command),
            )
        expected = (
            payload.get("bad", {}).get("ordinary_tests") == "pass"
            and payload.get("bad", {}).get("verdict") == "block"
            and payload.get("repaired", {}).get("ordinary_tests") == "pass"
            and payload.get("repaired", {}).get("verdict") == "pass"
            and payload.get("provenance") == "fake-development"
        )
        return _check(
            "replay_demo",
            "command",
            expected,
            (
                "Ordinary PASS/PASS and Faber Proof BLOCK/PASS reproduced with "
                "fake-development provenance."
            ),
            "Replay demo comparison or provenance did not match the committed development gate.",
            command=_display_command(command),
        )


def _privacy_check() -> AuditCheck:
    paths = [REPOSITORY_ROOT / relative for relative in PRIVACY_PATHS]
    report = audit_proof_artifacts(paths)
    return _check(
        "submission_privacy",
        "static",
        report.passed,
        f"{report.scanned_files} submission files passed with zero covered findings.",
        f"Privacy audit found {len(report.findings)} covered issue(s).",
        command="faber audit-proof-artifacts <submission-artifacts>",
    )


def _ci_check() -> AuditCheck:
    active = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
    draft = REPOSITORY_ROOT / "codex" / "build-week" / "drafts" / "ci.yml"
    status = _read_text("codex/build-week/STATUS.md")
    if active.is_file():
        return AuditCheck(
            id="remote_ci_definition",
            category="external",
            status="pass",
            detail="Linux/Windows workflow is active at .github/workflows/ci.yml.",
        )
    blocker_recorded = (
        draft.is_file()
        and "remote CI activation is externally blocked" in status
        and "workflow" in status.casefold()
    )
    return AuditCheck(
        id="remote_ci_definition",
        category="external",
        status="external_blocked" if blocker_recorded else "fail",
        detail=(
            "Exact Linux/Windows workflow remains preserved as a draft; GitHub rejected "
            "workflow-path updates from the registered non-FIDO deploy credential."
            if blocker_recorded
            else "No active workflow or precise preserved external blocker was found."
        ),
    )


def _canonical_environment_check(*, run: bool) -> AuditCheck:
    command = ["nix", "develop", "--command", "just", "check"]
    if shutil.which("nix") is None or shutil.which("just") is None:
        return AuditCheck(
            id="canonical_environment",
            category="command",
            status="not_available",
            detail="Nix and/or just is unavailable; equivalent Python release gates are required.",
            command=_display_command(command),
        )
    if not run:
        return _not_run_command_check("canonical_environment", command)
    return _command_check("canonical_environment", command, timeout=1800)


def _delta_check(target_ref: str) -> tuple[AuditCheck, dict[str, object] | None]:
    command = [sys.executable, "scripts/build_week_delta.py", "--target", target_ref, "--json"]
    result = _run(command, timeout=180)
    if result.returncode != 0:
        return (
            AuditCheck(
                id="build_week_delta",
                category="git",
                status="fail",
                detail=f"Delta command exited {result.returncode}.",
                command=_display_command(command),
            ),
            None,
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (
            AuditCheck(
                id="build_week_delta",
                category="git",
                status="fail",
                detail="Delta command emitted malformed JSON.",
                command=_display_command(command),
            ),
            None,
        )
    valid = (
        payload.get("baseline", {}).get("sha") == EXPECTED_BASELINE_SHA
        and payload.get("target", {}).get("sha") is not None
        and payload.get("commit_count", 0) > 0
        and payload.get("warnings") == []
    )
    totals = payload.get("file_totals", {})
    summary = {
        "baseline_ref": payload.get("baseline", {}).get("ref"),
        "baseline_commit": payload.get("baseline", {}).get("sha"),
        "target_ref": payload.get("target", {}).get("ref"),
        "target_commit": payload.get("target", {}).get("sha"),
        "commit_count": payload.get("commit_count"),
        "file_count": totals.get("files"),
        "additions": totals.get("additions"),
        "deletions": totals.get("deletions"),
        "warnings": payload.get("warnings"),
    }
    return (
        _check(
            "build_week_delta",
            "git",
            valid,
            (
                f"{summary['commit_count']} eligible commits and {summary['file_count']} "
                "changed files have a warning-free baseline delta."
            ),
            "Baseline delta is missing, empty, or has warnings.",
            command=_display_command(command),
        ),
        summary,
    )


def _git_checks(
    *,
    target_ref: str,
    expected_branch: str,
) -> tuple[list[AuditCheck], dict[str, str | None]]:
    checks: list[AuditCheck] = []
    dirty = bool(_git("status", "--porcelain=v1", "--untracked-files=all"))
    branch = _git("branch", "--show-current")
    head = _resolve_commit("HEAD")
    target = _resolve_commit(target_ref)
    baseline = _resolve_commit(BASELINE_REF)
    final_tag = _resolve_commit(FINAL_TAG)
    checks.append(
        _check(
            "clean_working_tree",
            "git",
            not dirty,
            "Working tree is clean before report output.",
            "Working tree is dirty; uncommitted data is outside the audited commit.",
        )
    )
    checks.append(
        _check(
            "expected_branch",
            "git",
            branch == expected_branch,
            f"Current branch is {expected_branch}.",
            f"Current branch is {branch or 'detached'}, expected {expected_branch}.",
        )
    )
    checks.append(
        _check(
            "baseline_tag",
            "git",
            baseline == EXPECTED_BASELINE_SHA,
            f"{BASELINE_REF} resolves to the recorded pre-period commit.",
            f"{BASELINE_REF} resolved to {baseline or 'missing'}.",
        )
    )
    target_valid = target is not None and baseline is not None
    if target_valid:
        ancestry = _run(["git", "merge-base", "--is-ancestor", baseline, target], timeout=120)
        target_valid = ancestry.returncode == 0
    checks.append(
        _check(
            "audit_target",
            "git",
            target_valid,
            f"Audit target {target_ref} resolves to an eligible descendant.",
            f"Audit target {target_ref} is missing or not descended from the baseline.",
        )
    )
    return checks, {
        "branch": branch or None,
        "head_commit": head,
        "target_ref": target_ref,
        "target_commit": target,
        "baseline_ref": BASELINE_REF,
        "baseline_commit": baseline,
        "final_tag_commit": final_tag,
    }


def _release_commands(*, include_live_extra: bool) -> list[tuple[str, list[str], int]]:
    clean_install = [sys.executable, "scripts/clean_install_audit.py"]
    if not include_live_extra:
        clean_install.append("--skip-live-extra")
    return [
        ("pytest", [sys.executable, "-m", "pytest", "-q"], 1200),
        (
            "ruff_format",
            [sys.executable, "-m", "ruff", "format", "--check", "."],
            300,
        ),
        ("ruff_lint", [sys.executable, "-m", "ruff", "check", "."], 300),
        ("mypy", [sys.executable, "-m", "mypy", "src"], 600),
        (
            "adversarial_evals",
            [sys.executable, "scripts/run_build_week_evals.py", "--check"],
            600,
        ),
        (
            "report_regeneration",
            [sys.executable, "scripts/check_development_report_regeneration.py", "--check"],
            300,
        ),
        ("clean_install", clean_install, 1200),
        (
            "performance_smoke",
            [sys.executable, "scripts/measure_proof_demo.py"],
            300,
        ),
    ]


def run_audit(
    *,
    target_ref: str,
    expected_branch: str,
    human_gate_path: Path,
    run_machine_checks: bool,
    include_live_extra: bool,
) -> dict[str, object]:
    checks, audited = _git_checks(target_ref=target_ref, expected_branch=expected_branch)
    checks.extend(
        (
            check_required_artifacts(),
            check_readme(),
            check_submission_docs(),
            check_placeholders(),
            check_svg_assets(),
            _privacy_check(),
            _ci_check(),
        )
    )
    delta_result, delta = _delta_check(target_ref)
    checks.append(delta_result)

    try:
        human_payload = load_human_gates(human_gate_path)
        target_commit = audited["target_commit"]
        if not isinstance(target_commit, str):
            raise AuditError("audit target commit is unavailable")
        human_gates, human_errors = validate_human_gates(
            human_payload,
            audited_commit=target_commit,
            final_tag_commit=audited["final_tag_commit"],
        )
    except AuditError as exc:
        human_gates = []
        human_errors = [str(exc)]
    checks.append(
        _check(
            "human_gate_state",
            "static",
            not human_errors,
            "Human gates are explicit, structurally valid, and internally consistent.",
            "Human-gate state invalid: " + "; ".join(human_errors),
        )
    )

    for check_id, command, timeout in _release_commands(include_live_extra=include_live_extra):
        checks.append(
            _command_check(check_id, command, timeout=timeout)
            if run_machine_checks
            else _not_run_command_check(check_id, command)
        )
    checks.append(_demo_check(run=run_machine_checks))
    checks.append(_canonical_environment_check(run=run_machine_checks))

    hard_failures = [check for check in checks if check.status == "fail"]
    not_run = [check for check in checks if check.status == "not_run"]
    external_blockers = [check.to_dict() for check in checks if check.status == "external_blocked"]
    unavailable = [check.to_dict() for check in checks if check.status == "not_available"]
    if hard_failures:
        machine_status = "fail"
    elif not_run:
        machine_status = "incomplete"
    else:
        machine_status = "pass"
    human_status = (
        "pass"
        if human_gates
        and all(gate["status"] == "complete" for gate in human_gates)
        and not human_errors
        else "incomplete"
    )
    if machine_status == "fail":
        overall_status = "machine_fail"
    elif machine_status == "incomplete":
        overall_status = "machine_incomplete"
    elif human_status == "incomplete":
        overall_status = "human_incomplete"
    else:
        overall_status = "pass"

    return {
        "schema": SCHEMA,
        "overall_status": overall_status,
        "machine_status": machine_status,
        "human_status": human_status,
        "audited": audited,
        "delta": delta,
        "checks": [check.to_dict() for check in checks],
        "human_gates": human_gates,
        "external_blockers": external_blockers,
        "unavailable_checks": unavailable,
        "exit_policy": {
            "machine": "exit 0 only when machine_status is pass",
            "submission": "exit 0 only when machine_status and human_status are pass",
            "human_incomplete_exit": 2,
            "machine_failure_or_incomplete_exit": 1,
        },
    }


def render_json(report: Mapping[str, object]) -> str:
    return json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"


def _code(value: object) -> str:
    escaped = str(value).replace("`", "\\`").replace("|", "\\|")
    return f"`{escaped}`"


def render_markdown(report: Mapping[str, object]) -> str:
    audited = report["audited"]
    assert isinstance(audited, dict)
    delta = report.get("delta")
    checks = report["checks"]
    human_gates = report["human_gates"]
    assert isinstance(checks, list)
    assert isinstance(human_gates, list)
    lines = [
        "# Faber Proof final submission audit",
        "",
        f"- Overall status: **{str(report['overall_status']).upper()}**",
        f"- Machine status: **{str(report['machine_status']).upper()}**",
        f"- Human status: **{str(report['human_status']).upper()}**",
        f"- Branch: {_code(audited.get('branch'))}",
        f"- Audited target: {_code(audited.get('target_ref'))}",
        f"- Audited commit: {_code(audited.get('target_commit'))}",
        f"- Eligibility baseline: {_code(audited.get('baseline_commit'))}",
        "",
        "Machine completion and human submission completion are separate. An external "
        "workflow-authorization blocker or unavailable Nix command is reported explicitly; "
        "neither is represented as a successful remote run.",
        "",
    ]
    if isinstance(delta, dict):
        lines.extend(
            [
                "## Build Week delta",
                "",
                f"- Eligible commits: **{delta.get('commit_count')}**",
                f"- Changed files: **{delta.get('file_count')}**",
                f"- Additions/deletions: **+{delta.get('additions')} / -{delta.get('deletions')}**",
                f"- Warnings: **{len(delta.get('warnings', []))}**",
                "",
            ]
        )
    lines.extend(
        [
            "## Machine checks",
            "",
            "| Check | Category | Status | Detail |",
            "|---|---|---|---|",
        ]
    )
    for item in checks:
        assert isinstance(item, dict)
        lines.append(
            "| "
            + " | ".join(
                (
                    _code(item["id"]),
                    _code(item["category"]),
                    f"**{str(item['status']).upper()}**",
                    str(item["detail"]).replace("|", "\\|"),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Human gates",
            "",
            "| Gate | Status | Evidence present |",
            "|---|---|:---:|",
        ]
    )
    for gate in human_gates:
        assert isinstance(gate, dict)
        lines.append(
            f"| {_code(gate['id'])} | **{str(gate['status']).upper()}** | "
            f"{'yes' if gate['evidence_present'] else 'no'} |"
        )
    if not human_gates:
        lines.append("| invalid state | **INCOMPLETE** | no |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `machine_status=pass` means every available machine gate executed successfully.",
            "- `human_status=incomplete` is expected until live provenance, audits, access, "
            "video, permitted Devpost state, and final tag are human-attested.",
            "- Run with `--require submission` to receive exit code 2 while those human gates "
            "remain incomplete.",
            "- Do not create the final tag from this machine-only report.",
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def audit_exit_code(report: Mapping[str, object], requirement: str) -> int:
    if report.get("machine_status") != "pass":
        return 1
    if requirement == "submission" and report.get("human_status") != "pass":
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the Faber Proof machine candidate and explicit human gates."
    )
    parser.add_argument("--target-ref", default="HEAD")
    parser.add_argument("--expected-branch", default=EXPECTED_BRANCH)
    parser.add_argument(
        "--human-gates",
        type=Path,
        default=REPOSITORY_ROOT / "codex" / "build-week" / "submission-human-gates.json",
    )
    parser.add_argument("--run-machine-checks", action="store_true")
    parser.add_argument("--include-live-extra", action="store_true")
    parser.add_argument("--require", choices=("machine", "submission"), default="machine")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args(argv)

    try:
        report = run_audit(
            target_ref=args.target_ref,
            expected_branch=args.expected_branch,
            human_gate_path=args.human_gates,
            run_machine_checks=args.run_machine_checks,
            include_live_extra=args.include_live_extra,
        )
    except (AuditError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"final submission audit failed: {exc}", file=sys.stderr)
        return 1

    json_text = render_json(report)
    markdown_text = render_markdown(report)
    _write(args.json_out, json_text)
    _write(args.markdown_out, markdown_text)
    if args.json:
        print(json_text, end="")
    else:
        print(
            f"MACHINE {str(report['machine_status']).upper()}; "
            f"HUMAN {str(report['human_status']).upper()}; "
            f"OVERALL {str(report['overall_status']).upper()}"
        )

    return audit_exit_code(report, args.require)


if __name__ == "__main__":
    raise SystemExit(main())
