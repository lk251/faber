from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "final_submission_audit.py"
HUMAN_GATES_PATH = ROOT / "codex" / "build-week" / "submission-human-gates.json"
AUDITED_COMMIT = "a" * 40


def _load_script() -> object:
    spec = importlib.util.spec_from_file_location("final_submission_audit", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, object]:
    return json.loads(HUMAN_GATES_PATH.read_text(encoding="utf-8"))


def _gate(payload: dict[str, object], gate_id: str) -> dict[str, object]:
    gates = payload["gates"]
    assert isinstance(gates, list)
    return next(gate for gate in gates if gate["id"] == gate_id)


def test_committed_human_gate_state_is_valid_and_explicitly_incomplete() -> None:
    audit = _load_script()

    records, errors = audit.validate_human_gates(
        _payload(),
        audited_commit=AUDITED_COMMIT,
        final_tag_commit=None,
    )

    assert errors == []
    statuses = {record["id"]: record["status"] for record in records}
    assert statuses["feedback_session"] == "complete"
    assert statuses["live_provenance"] == "incomplete"
    assert statuses["public_video"] == "incomplete"
    assert statuses["devpost"] == "incomplete"
    assert statuses["final_tag"] == "incomplete"


def test_complete_human_attestations_must_bind_to_the_audited_commit() -> None:
    audit = _load_script()
    payload = copy.deepcopy(_payload())

    deadline = _gate(payload, "deadline_status")
    deadline["status"] = "complete"
    deadline["evidence"]["timely_submission_confirmed"] = True
    deadline["evidence"]["timely_submission_url"] = "https://example.invalid/submission"

    live = _gate(payload, "live_provenance")
    live["status"] = "complete"
    live["evidence"].update(
        {
            "provenance": "live-reviewed",
            "reviewer": "Javier",
            "review_manifest": "examples/build-week-proof/replays/review-manifest.json",
        }
    )

    audits = _gate(payload, "independent_audits")
    audits["status"] = "complete"
    audits["evidence"]["completed_audits"] = ["A1", "A2", "A3", "A4", "A5"]

    access = _gate(payload, "judge_repository_access")
    access["status"] = "complete"
    access["evidence"]["attested"] = True
    access["evidence"]["verified_from_clean_context"] = True

    video = _gate(payload, "public_video")
    video["status"] = "complete"
    video["evidence"].update(
        {
            "audio_attested": True,
            "duration_seconds": 167,
            "public_attested": True,
            "url": "https://www.youtube.com/watch?v=example",
            "verified_signed_out": True,
        }
    )

    devpost = _gate(payload, "devpost")
    devpost["status"] = "complete"
    devpost["evidence"].update(
        {
            "final_commit": AUDITED_COMMIT,
            "preview_attested": True,
            "submitted_at": "2026-07-21T16:00:00-07:00",
            "url": "https://openai.devpost.com/submissions/example",
        }
    )

    final_tag = _gate(payload, "final_tag")
    final_tag["status"] = "complete"
    final_tag["evidence"].update(
        {
            "audit_report_digest": "sha256:" + "b" * 64,
            "commit": AUDITED_COMMIT,
        }
    )

    records, errors = audit.validate_human_gates(
        payload,
        audited_commit=AUDITED_COMMIT,
        final_tag_commit=AUDITED_COMMIT,
    )

    assert errors == []
    assert all(record["status"] == "complete" for record in records)


def test_false_human_completion_fails_closed() -> None:
    audit = _load_script()
    payload = copy.deepcopy(_payload())
    video = _gate(payload, "public_video")
    video["status"] = "complete"

    _, errors = audit.validate_human_gates(
        payload,
        audited_commit=AUDITED_COMMIT,
        final_tag_commit=None,
    )

    assert any("public_video completion requires" in error for error in errors)


def test_placeholder_policy_allows_only_named_human_gates() -> None:
    audit = _load_script()

    valid = {"README.md": ("HUMAN_GATE::PUBLIC_YOUTUBE_URL HUMAN_GATE::FINAL_SUBMISSION_REF")}
    generic, unknown, missing = audit.placeholder_issues(valid)
    assert generic == []
    assert unknown == set()
    assert missing == set()

    invalid = {
        "README.md": (
            "TODO REPLACE_ME HUMAN_GATE::PUBLIC_YOUTUBE_URL "
            "HUMAN_GATE::FINAL_SUBMISSION_REF HUMAN_GATE::UNKNOWN"
        )
    }
    generic, unknown, missing = audit.placeholder_issues(invalid)
    assert generic
    assert unknown == {"HUMAN_GATE::UNKNOWN"}
    assert missing == set()


def test_exit_policy_separates_machine_and_submission_completion() -> None:
    audit = _load_script()
    report = {"machine_status": "pass", "human_status": "incomplete"}

    assert audit.audit_exit_code(report, "machine") == 0
    assert audit.audit_exit_code(report, "submission") == 2
    assert (
        audit.audit_exit_code(
            {"machine_status": "fail", "human_status": "incomplete"},
            "machine",
        )
        == 1
    )


def test_failed_command_is_recorded_without_false_pass() -> None:
    audit = _load_script()

    result = audit._command_check(
        "expected_failure",
        [sys.executable, "-c", "raise SystemExit(7)"],
    )

    assert result.status == "fail"
    assert result.detail == "Command exited 7."
    assert result.command == subprocess.list2cmdline(["python", "-c", "raise SystemExit(7)"])


def test_committed_static_submission_artifacts_pass_local_structure_checks() -> None:
    audit = _load_script()

    for result in (
        audit.check_required_artifacts(),
        audit.check_readme(),
        audit.check_submission_docs(),
        audit.check_placeholders(),
        audit.check_svg_assets(),
    ):
        assert result.status == "pass", result.detail
