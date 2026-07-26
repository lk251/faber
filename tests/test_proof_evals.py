from __future__ import annotations

from faber.proof_evals import (
    EVAL_REPORT_SCHEMA,
    PROOF_EVAL_CASES,
    build_eval_report,
    eval_manifest_digest,
    eval_report_json,
    render_eval_markdown,
    validate_eval_cases,
)


def _passing_outcomes() -> dict[tuple[str, str], tuple[str, ...]]:
    outcomes: dict[tuple[str, str], tuple[str, ...]] = {}
    for case in PROOF_EVAL_CASES:
        path, function = case.pytest_nodeid.split("::", 1)
        module = path.removesuffix(".py").replace("/", ".")
        outcomes[(module, function)] = ("passed",)
    return outcomes


def test_eval_manifest_is_complete_unique_and_digestible() -> None:
    validate_eval_cases()

    assert len(PROOF_EVAL_CASES) >= 45
    assert eval_manifest_digest() == eval_manifest_digest(tuple(PROOF_EVAL_CASES))
    assert {case.category for case in PROOF_EVAL_CASES} == {
        "baseline",
        "execution_evidence",
        "planner_output",
        "replay",
        "untrusted_repository",
    }
    assert {case.expected_verdict for case in PROOF_EVAL_CASES} == {
        "BLOCK",
        "HUMAN_REVIEW",
        "PASS",
    }


def test_successful_eval_report_is_deterministic_and_has_no_unjustified_pass() -> None:
    first = build_eval_report(PROOF_EVAL_CASES, _passing_outcomes(), runner_returncode=0)
    second = build_eval_report(PROOF_EVAL_CASES, _passing_outcomes(), runner_returncode=0)

    assert first == second
    assert first["schema"] == EVAL_REPORT_SCHEMA
    assert first["status"] == "PASS"
    assert first["unjustified_pass_count"] == 0
    assert first["failed_case_count"] == 0
    assert eval_report_json(first) == eval_report_json(second)
    markdown = render_eval_markdown(first)
    assert "Expected | Actual" in markdown
    assert "| **NOT_EVALUATED** |" not in markdown


def test_missing_or_failed_assertion_fails_the_eval_report() -> None:
    outcomes = _passing_outcomes()
    first = PROOF_EVAL_CASES[0]
    path, function = first.pytest_nodeid.split("::", 1)
    outcomes[(path.removesuffix(".py").replace("/", "."), function)] = ("failed",)

    report = build_eval_report(PROOF_EVAL_CASES, outcomes, runner_returncode=1)

    assert report["status"] == "FAIL"
    assert report["failed_case_count"] >= 1
    assert report["results"][0]["actual_verdict"] == "NOT_EVALUATED"  # type: ignore[index]
