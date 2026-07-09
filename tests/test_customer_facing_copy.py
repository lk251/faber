import json
from pathlib import Path

from faber.adapters.github.publisher import render_receipt_publication_body
from faber.cli import main
from faber.golden_fixtures import build_golden_fixture_corpus
from faber.receipts import VerificationReceipt


def test_validation_error_names_field_and_next_step(tmp_path: Path, capsys) -> None:
    path = tmp_path / "attempt.json"
    path.write_text("{}\n", encoding="utf-8")

    assert main(["validate-attempt", str(path)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["errors"][0]["field"] == "redaction_policy"
    assert "redaction_policy" in output["next_step"]
    assert "validate-attempt" in output["next_step"]


def test_cli_golden_path_output_includes_digest_path_and_next_step(
    tmp_path: Path,
    capsys,
) -> None:
    store = tmp_path / "golden.sqlite3"
    trajectory = tmp_path / "golden-trajectory.json"

    assert (
        main(
            [
                "run-golden-path",
                "--store",
                str(store),
                "--out",
                str(trajectory),
            ]
        )
        == 0
    )

    output = json.loads(capsys.readouterr().out)
    assert output["trajectory_path"] == str(trajectory)
    assert output["trajectory_digest"].startswith("sha256:")
    assert output["next_step"] == (
        f"Run `python -m faber.cli validate-trajectory {trajectory}` to inspect "
        "the exported evidence."
    )


def test_fake_github_receipt_publication_is_readable_for_both_outcomes(
    tmp_path: Path,
) -> None:
    fixtures = build_golden_fixture_corpus(tmp_path / "fixture-work")
    accepted_payload = next(
        fixture.payload for fixture in fixtures if fixture.name == "trajectory-rl-trace"
    )
    rejected_payload = next(
        fixture.payload for fixture in fixtures if fixture.name == "trajectory-rejected"
    )
    accepted = _receipt_from_payload(accepted_payload["receipt"])
    rejected = _receipt_from_payload(rejected_payload["receipt"])

    accepted_body = render_receipt_publication_body(accepted)
    rejected_body = render_receipt_publication_body(rejected)

    assert "Authority: task-authorized verifier receipt" in accepted_body
    assert "Candidate CI remains signal only." in accepted_body
    assert "merge policy and receipt-gated settlement policy separately" in accepted_body
    assert "Failure reasons: golden fixture rejection" in rejected_body
    assert "update the candidate revision" in rejected_body


def test_glossary_uses_core_terms_consistently() -> None:
    text = Path("docs/NAMING.md").read_text(encoding="utf-8")

    for term in [
        "Raw trace",
        "Trajectory",
        "RL-grade trajectory",
        "Work budget",
        "Verifier receipt",
    ]:
        assert f"**{term}**" in text


def _receipt_from_payload(payload: object) -> VerificationReceipt:
    assert isinstance(payload, dict)
    return VerificationReceipt(
        id=str(payload["id"]),
        created_at=str(payload["created_at"]),
        task_contract_id=str(payload["task_contract_id"]),
        task_contract_digest=str(payload["task_contract_digest"]),
        attempt_id=str(payload["attempt_id"]),
        worker_id=str(payload["worker_id"]),
        verifier_id=str(payload["verifier_id"]),
        verifier_digest=str(payload["verifier_digest"]),
        base_revision=str(payload["base_revision"]),
        candidate_revision=str(payload["candidate_revision"]),
        accepted=payload["accepted"] is True,
        metrics=dict(payload["metrics"]),
        failure_reasons=list(payload["failure_reasons"]),
        result_digest=str(payload["result_digest"]),
    )
