from __future__ import annotations

import json
from pathlib import Path

from faber.digests import sha256_digest
from faber.proof_privacy import audit_proof_artifacts, write_privacy_report


def test_safe_artifacts_produce_deterministic_pass_report(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "summary.json").write_text(
        json.dumps({"status": "pass", "sanitized_structured_response": {"claims": []}}),
        encoding="utf-8",
    )
    (artifacts / "report.html").write_text(
        "<!doctype html><title>Faber Proof</title><p>Portable report.</p>",
        encoding="utf-8",
    )

    first = audit_proof_artifacts(
        [artifacts],
        home_directory=tmp_path / "home-not-present",
        temp_directory=tmp_path / "temp-not-present",
    )
    second = audit_proof_artifacts(
        [artifacts],
        home_directory=tmp_path / "home-not-present",
        temp_directory=tmp_path / "temp-not-present",
    )

    assert first.passed is True
    assert first.to_dict() == second.to_dict()
    assert first.scanned_files == 2


def test_covered_secrets_paths_assets_and_raw_output_fail_without_echoing_values(
    tmp_path: Path,
) -> None:
    secret = "sk-proj-example0123456789abcdef"
    artifact = tmp_path / "unsafe.json"
    artifact.write_text(
        json.dumps(
            {
                "api_key": secret,
                "raw_model_output": "unbounded provider prose",
                "path": "C:\\Users\\private-user\\work",
            }
        ),
        encoding="utf-8",
    )
    html = tmp_path / "unsafe.html"
    html.write_text('<script src="https://example.invalid/report.js"></script>', encoding="utf-8")

    report = audit_proof_artifacts(
        [artifact, html],
        home_directory=tmp_path / "home-not-present",
        temp_directory=tmp_path / "temp-not-present",
    )

    codes = {finding.code for finding in report.findings}
    assert report.passed is False
    assert {
        "openai_api_key",
        "assigned_secret",
        "raw_unbounded_output",
        "machine_specific_path",
        "external_report_asset",
    } <= codes
    serialized = json.dumps(report.to_dict())
    assert secret not in serialized
    assert "private-user" not in serialized


def test_explicit_forbidden_literal_and_hash_fail_closed(tmp_path: Path) -> None:
    artifact = tmp_path / "fixture.txt"
    artifact.write_text("known-sensitive-fragment\nhashed-environment-value\n", encoding="utf-8")

    report = audit_proof_artifacts(
        [artifact],
        forbidden_literals=["known-sensitive-fragment"],
        forbidden_hashes=[sha256_digest("hashed-environment-value")],
        home_directory=tmp_path / "home-not-present",
        temp_directory=tmp_path / "temp-not-present",
    )

    assert {finding.code for finding in report.findings} == {
        "forbidden_literal",
        "forbidden_value_hash",
    }


def test_privacy_report_writes_canonical_json_and_markdown(tmp_path: Path) -> None:
    artifact = tmp_path / "safe.txt"
    artifact.write_text("safe\n", encoding="utf-8")
    report = audit_proof_artifacts(
        [artifact],
        home_directory=tmp_path / "home-not-present",
        temp_directory=tmp_path / "temp-not-present",
    )
    json_path = tmp_path / "audit.json"
    markdown_path = tmp_path / "audit.md"

    write_privacy_report(report, json_path=json_path, markdown_path=markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "pass"
    assert "Status: **PASS**" in markdown_path.read_text(encoding="utf-8")
