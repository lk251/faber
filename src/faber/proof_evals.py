"""Deterministic Build Week adversarial-evaluation manifest and runner."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.digests import sha256_digest

EVAL_REPORT_SCHEMA = "faber.proof_eval_report.v1"
EVAL_VERDICTS = frozenset({"PASS", "BLOCK", "HUMAN_REVIEW"})


@dataclass(frozen=True)
class ProofEvalCase:
    id: str
    category: str
    description: str
    expected_verdict: str
    reason_codes: tuple[str, ...]
    pytest_nodeid: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "expected_verdict": self.expected_verdict,
            "reason_codes": list(self.reason_codes),
            "pytest_nodeid": self.pytest_nodeid,
            "reproduction_command": f"python -m pytest -q {self.pytest_nodeid}",
        }


def _case(
    id: str,
    category: str,
    description: str,
    verdict: str,
    reason_codes: Sequence[str],
    nodeid: str,
) -> ProofEvalCase:
    return ProofEvalCase(
        id=id,
        category=category,
        description=description,
        expected_verdict=verdict,
        reason_codes=tuple(reason_codes),
        pytest_nodeid=nodeid,
    )


PROOF_EVAL_CASES = (
    _case(
        "repository.prompt-injection-comment",
        "untrusted_repository",
        "A diff comment that demands PASS remains labeled untrusted planner data.",
        "HUMAN_REVIEW",
        ("untrusted_repository_content",),
        "tests/test_openai_proof_planner.py::test_prompt_injection_in_diff_remains_labeled_untrusted_data",
    ),
    _case(
        "repository.instruction-like-string",
        "untrusted_repository",
        "A string literal that imitates a system instruction has no control authority.",
        "HUMAN_REVIEW",
        ("untrusted_repository_content",),
        "tests/test_openai_proof_planner.py::test_instruction_like_string_literal_remains_untrusted_data",
    ),
    _case(
        "repository.secret-like-value",
        "untrusted_repository",
        "Secret-like diff values are redacted before provider serialization.",
        "BLOCK",
        ("secret_detected",),
        "tests/test_openai_proof_planner.py::test_secret_like_diff_values_are_redacted_before_serialization_and_digest",
    ),
    _case(
        "repository.oversized-diff",
        "untrusted_repository",
        "A diff over the configured byte budget fails before planning.",
        "HUMAN_REVIEW",
        ("request_too_large",),
        "tests/test_openai_proof_planner.py::test_request_size_limits_fail_closed",
    ),
    _case(
        "repository.generated-output-excluded",
        "untrusted_repository",
        "Changed .faber output cannot influence the planning diff.",
        "HUMAN_REVIEW",
        ("generated_output_excluded",),
        "tests/test_proof_product.py::test_git_context_is_local_bounded_deterministic_and_excludes_outputs",
    ),
    _case(
        "repository.unicode-line-ending-digest",
        "untrusted_repository",
        "Line endings normalize before exact attempt and request digest binding.",
        "PASS",
        ("stable_normalized_digest",),
        "tests/test_openai_proof_planner.py::test_diff_line_endings_are_normalized_before_binding",
    ),
    _case(
        "repository.diff-attempt-mismatch",
        "untrusted_repository",
        "Caller-supplied diff bytes cannot be relabeled as another attempt.",
        "HUMAN_REVIEW",
        ("attempt_binding_mismatch",),
        "tests/test_openai_proof_planner.py::test_diff_text_must_bind_to_attempt_patch_digest",
    ),
    _case(
        "planner.unknown-entry",
        "planner_output",
        "An unknown proof entry cannot materialize a plan.",
        "HUMAN_REVIEW",
        ("unknown_template",),
        "tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan",
    ),
    _case(
        "planner.stale-entry-version",
        "planner_output",
        "A stale active catalog entry is rejected.",
        "HUMAN_REVIEW",
        ("stale_catalog_entry",),
        "tests/test_proof_executors.py::test_catalog_rejects_duplicate_and_stale_active_entries",
    ),
    _case(
        "planner.extra-field",
        "planner_output",
        "Provider output cannot add a verdict or another unsupported field.",
        "HUMAN_REVIEW",
        ("invalid_structured_output",),
        "tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan",
    ),
    _case(
        "planner.nested-operational-field",
        "planner_output",
        "Nested command-like parameters are rejected.",
        "HUMAN_REVIEW",
        ("invalid_parameters",),
        "tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan",
    ),
    _case(
        "planner.missing-mandatory-template",
        "planner_output",
        "A mandatory owner-selected template cannot be omitted.",
        "HUMAN_REVIEW",
        ("missing_mandatory_template",),
        "tests/test_openai_proof_planner.py::test_missing_mandatory_template_fails_closed",
    ),
    _case(
        "planner.duplicate-claim",
        "planner_output",
        "Duplicate claim identifiers are rejected.",
        "HUMAN_REVIEW",
        ("duplicate_claim",),
        "tests/test_proofs.py::test_plan_rejects_duplicate_claim_ids",
    ),
    _case(
        "planner.duplicate-selection",
        "planner_output",
        "Duplicate claim-template selections are rejected.",
        "HUMAN_REVIEW",
        ("duplicate_selection",),
        "tests/test_proofs.py::test_plan_rejects_duplicate_claim_template_pair",
    ),
    _case(
        "planner.malformed-parameters",
        "planner_output",
        "Parameters that violate the catalog schema cannot execute.",
        "HUMAN_REVIEW",
        ("invalid_parameters",),
        "tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan",
    ),
    _case(
        "planner.oversized-parameters",
        "planner_output",
        "Oversized bound parameters fail before process launch.",
        "HUMAN_REVIEW",
        ("input_limit",),
        "tests/test_proof_executors.py::test_oversized_parameter_is_rejected_before_launch",
    ),
    _case(
        "planner.refusal",
        "planner_output",
        "A provider refusal wins over valid-looking structured data.",
        "HUMAN_REVIEW",
        ("refusal",),
        "tests/test_openai_proof_planner.py::test_refusal_wins_over_valid_looking_structured_response_and_is_not_retried",
    ),
    _case(
        "planner.timeout",
        "planner_output",
        "A provider timeout cannot produce a plan or verdict.",
        "HUMAN_REVIEW",
        ("timeout",),
        "tests/test_openai_proof_planner.py::test_timeout_is_terminal_when_retry_budget_is_zero",
    ),
    _case(
        "planner.invalid-structured-response",
        "planner_output",
        "Non-strict structured output is rejected.",
        "HUMAN_REVIEW",
        ("invalid_structured_output",),
        "tests/test_openai_proof_planner.py::test_structured_response_parser_rejects_non_strict_json",
    ),
    _case(
        "replay.request-mismatch",
        "replay",
        "A replay from another task or diff cannot be used.",
        "HUMAN_REVIEW",
        ("replay_mismatch",),
        "tests/test_openai_proof_planner.py::test_replay_rejects_a_different_task_or_diff_context",
    ),
    _case(
        "replay.catalog-mismatch",
        "replay",
        "A replay bound to another catalog cannot be used.",
        "HUMAN_REVIEW",
        ("replay_mismatch",),
        "tests/test_openai_proof_planner.py::test_replay_rejects_catalog_prompt_schema_and_model_mismatches",
    ),
    _case(
        "replay.prompt-schema-mismatch",
        "replay",
        "Stale trusted prompt or response schema commitments fail closed.",
        "HUMAN_REVIEW",
        ("replay_mismatch",),
        "tests/test_openai_proof_planner.py::test_replay_rejects_self_consistent_stale_prompt_and_schema_context",
    ),
    _case(
        "replay.response-digest-tamper",
        "replay",
        "A modified recorded response cannot retain the approved replay identity.",
        "HUMAN_REVIEW",
        ("replay_mismatch",),
        "tests/test_openai_proof_planner.py::test_replay_rejects_structured_response_digest_tampering",
    ),
    _case(
        "replay.cross-candidate",
        "replay",
        "The bad-patch replay cannot be applied to the repaired candidate.",
        "HUMAN_REVIEW",
        ("replay_mismatch",),
        "tests/test_proof_demo.py::test_bad_replay_is_rejected_after_repaired_diff",
    ),
    _case(
        "replay.critic-disabled",
        "replay",
        "Critic mode is rejected until a separately recorded advisory path exists.",
        "HUMAN_REVIEW",
        ("configuration_error",),
        "tests/test_proof_product.py::test_critic_mode_is_disabled_fail_closed",
    ),
    _case(
        "replay.critic-contradiction",
        "replay",
        "A requested critic cannot contradict or override authority while critic mode is disabled.",
        "HUMAN_REVIEW",
        ("configuration_error",),
        "tests/test_proof_product.py::test_critic_mode_is_disabled_fail_closed",
    ),
    _case(
        "execution.path-traversal",
        "execution_evidence",
        "Absolute and traversing catalog paths fail before execution.",
        "HUMAN_REVIEW",
        ("path_not_allowed",),
        "tests/test_proof_executors.py::test_catalog_path_rejects_absolute_traversal_unc_drive_and_backslash_forms",
    ),
    _case(
        "execution.symlink-escape",
        "execution_evidence",
        "A catalog path cannot escape through a symlink.",
        "HUMAN_REVIEW",
        ("path_not_allowed",),
        "tests/test_proof_executors.py::test_catalog_path_rejects_a_symlink_escape",
    ),
    _case(
        "execution.missing-verifier",
        "execution_evidence",
        "A missing or stale registered verifier prevents launch.",
        "HUMAN_REVIEW",
        ("registry_mismatch",),
        "tests/test_proof_executors.py::test_stale_registered_verifier_is_rejected_before_launch",
    ),
    _case(
        "execution.missing-callable",
        "execution_evidence",
        "A missing or stale owner-pinned capability prevents launch.",
        "HUMAN_REVIEW",
        ("capability_preflight_failed",),
        "tests/test_proof_executors.py::test_missing_or_stale_catalog_capability_is_rejected_before_launch",
    ),
    _case(
        "execution.timeout",
        "execution_evidence",
        "A timed-out child process cannot become authority.",
        "HUMAN_REVIEW",
        ("timeout",),
        "tests/test_proof_executors.py::test_timeout_and_output_cap_are_terminal_executor_errors",
    ),
    _case(
        "execution.output-truncation",
        "execution_evidence",
        "Truncated verifier output cannot become authoritative PASS.",
        "HUMAN_REVIEW",
        ("output_limit",),
        "tests/test_proof_executors.py::test_existing_command_output_overflow_cannot_become_authoritative",
    ),
    _case(
        "execution.operational-error",
        "execution_evidence",
        "An operational-only result cannot yield PASS.",
        "HUMAN_REVIEW",
        ("operational_error",),
        "tests/test_proof_executors.py::test_operational_error_only_can_never_yield_pass",
    ),
    _case(
        "evidence.task-attempt-binding",
        "execution_evidence",
        "A plan must resolve to the exact task, attempt, diff, and revisions.",
        "HUMAN_REVIEW",
        ("authority_context_unbound",),
        "tests/test_proofs.py::test_plan_must_resolve_to_exact_task_attempt_diff_and_revisions",
    ),
    _case(
        "evidence.plan-selection-binding",
        "execution_evidence",
        "Evidence from another plan or selection cannot authorize the current plan.",
        "HUMAN_REVIEW",
        ("verifier_run_binding_mismatch",),
        "tests/test_proofs.py::test_evidence_from_another_plan_cannot_pass",
    ),
    _case(
        "evidence.catalog-policy-binding",
        "execution_evidence",
        "Catalog, registry, attempt, and execution-policy mismatches launch nothing.",
        "HUMAN_REVIEW",
        ("workflow_binding_mismatch",),
        "tests/test_proof_executors.py::test_workflow_binding_and_policy_mismatches_make_zero_launcher_calls",
    ),
    _case(
        "evidence.receipt-swap",
        "execution_evidence",
        "A valid-looking receipt from unrelated authority cannot be swapped in.",
        "HUMAN_REVIEW",
        ("verification_receipt_binding_mismatch",),
        "tests/test_proofs.py::test_valid_looking_but_unrelated_receipt_cannot_pass",
    ),
    _case(
        "evidence.duplicate",
        "execution_evidence",
        "Duplicate identical evidence cannot satisfy multiple obligations.",
        "HUMAN_REVIEW",
        ("duplicate_evidence",),
        "tests/test_proofs.py::test_duplicate_identical_evidence_cannot_pass",
    ),
    _case(
        "evidence.contradictory",
        "execution_evidence",
        "Contradictory duplicate evidence cannot produce PASS.",
        "HUMAN_REVIEW",
        ("contradictory_evidence",),
        "tests/test_proofs.py::test_duplicate_contradictory_evidence_cannot_pass",
    ),
    _case(
        "evidence.ordinary-green-high-uncovered",
        "execution_evidence",
        "A high-risk uncovered claim remains HUMAN_REVIEW despite other green signals.",
        "HUMAN_REVIEW",
        ("high_risk_claim_uncovered",),
        "tests/test_proofs.py::test_high_risk_uncovered_claim_produces_human_review",
    ),
    _case(
        "evidence.candidate-success-authority-failure",
        "execution_evidence",
        "Candidate-owned success claims cannot override authoritative failure.",
        "BLOCK",
        ("authoritative_failure",),
        "tests/test_proofs.py::test_authoritative_failure_blocks_even_if_evidence_lies_about_status",
    ),
    _case(
        "evidence.block-precedes-missing",
        "execution_evidence",
        "One demonstrated failure plus missing evidence resolves to BLOCK.",
        "BLOCK",
        ("authoritative_failure", "required_evidence_missing"),
        "tests/test_proofs.py::test_demonstrated_failure_precedes_other_missing_evidence",
    ),
    _case(
        "bundle.partial",
        "execution_evidence",
        "A complete-marked bundle with a missing evidence artifact cannot load.",
        "HUMAN_REVIEW",
        ("artifact_unavailable",),
        "tests/test_proof_product.py::test_partial_bundle_cannot_validate_as_complete",
    ),
    _case(
        "replay.stable-authority-digests",
        "execution_evidence",
        "Repeated replay produces identical plan, evidence, and decision digests.",
        "PASS",
        ("stable_authority_digests",),
        "tests/test_proof_demo.py::test_repeated_replay_has_stable_plan_evidence_and_decision_digests",
    ),
    _case(
        "baseline.authoritative-pass",
        "baseline",
        "A fully bound passing run and receipt can justify PASS.",
        "PASS",
        ("all_required_evidence_passed",),
        "tests/test_proofs.py::test_valid_authoritative_pass",
    ),
    _case(
        "baseline.demo-bad-block",
        "baseline",
        "The bad demo patch keeps ordinary tests green but receives authoritative BLOCK.",
        "BLOCK",
        ("assertion_failed",),
        "tests/test_proof_demo.py::test_one_command_demo_produces_memorable_authoritative_contrast",
    ),
    _case(
        "baseline.demo-repaired-pass",
        "baseline",
        "The repaired demo patch earns PASS from complete authoritative evidence.",
        "PASS",
        ("all_required_evidence_passed",),
        "tests/test_proof_demo.py::test_one_command_demo_produces_memorable_authoritative_contrast",
    ),
    _case(
        "privacy.safe-artifacts",
        "baseline",
        "Safe generated artifacts pass the deterministic privacy audit.",
        "PASS",
        ("privacy_audit_passed",),
        "tests/test_proof_privacy.py::test_safe_artifacts_produce_deterministic_pass_report",
    ),
    _case(
        "privacy.secret-path-asset-output",
        "baseline",
        "Secrets, machine paths, external assets, and raw output fail the privacy audit.",
        "BLOCK",
        ("privacy_finding",),
        "tests/test_proof_privacy.py::test_covered_secrets_paths_assets_and_raw_output_fail_without_echoing_values",
    ),
)


def validate_eval_cases(cases: Sequence[ProofEvalCase] = PROOF_EVAL_CASES) -> None:
    ids: set[str] = set()
    if not cases:
        raise ValueError("the proof eval manifest must not be empty")
    for case in cases:
        if not isinstance(case, ProofEvalCase):
            raise TypeError("proof eval cases must be ProofEvalCase records")
        if not case.id or case.id in ids:
            raise ValueError("proof eval case IDs must be unique and non-empty")
        ids.add(case.id)
        if (
            not case.category
            or not case.description
            or case.expected_verdict not in EVAL_VERDICTS
            or not case.reason_codes
            or any(not code for code in case.reason_codes)
            or "::test_" not in case.pytest_nodeid
        ):
            raise ValueError(f"proof eval case {case.id!r} is malformed")


def eval_manifest_digest(cases: Sequence[ProofEvalCase] = PROOF_EVAL_CASES) -> str:
    validate_eval_cases(cases)
    return sha256_digest([case.to_dict() for case in cases])


def _selector_identity(nodeid: str) -> tuple[str, str]:
    path_text, function = nodeid.split("::", 1)
    module = Path(path_text).with_suffix("").as_posix().replace("/", ".")
    return module, function


def _junit_outcomes(path: Path) -> Mapping[tuple[str, str], tuple[str, ...]]:
    root = ElementTree.parse(path).getroot()
    grouped: dict[tuple[str, str], list[str]] = {}
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "")
        name = testcase.attrib.get("name", "")
        base_name = name.split("[", 1)[0]
        outcome = "passed"
        if testcase.find("failure") is not None:
            outcome = "failed"
        elif testcase.find("error") is not None:
            outcome = "error"
        elif testcase.find("skipped") is not None:
            outcome = "skipped"
        grouped.setdefault((classname, base_name), []).append(outcome)
    return {key: tuple(value) for key, value in grouped.items()}


def build_eval_report(
    cases: Sequence[ProofEvalCase],
    outcomes: Mapping[tuple[str, str], Sequence[str]],
    *,
    runner_returncode: int,
) -> dict[str, object]:
    validate_eval_cases(cases)
    results: list[dict[str, object]] = []
    for case in cases:
        matched = tuple(outcomes.get(_selector_identity(case.pytest_nodeid), ()))
        assertion_passed = bool(matched) and all(outcome == "passed" for outcome in matched)
        actual_verdict = case.expected_verdict if assertion_passed else "NOT_EVALUATED"
        results.append(
            {
                **case.to_dict(),
                "actual_verdict": actual_verdict,
                "assertion_status": "passed" if assertion_passed else "failed",
            }
        )
    failed_count = sum(item["assertion_status"] != "passed" for item in results)
    unjustified_pass_count = sum(
        item["actual_verdict"] == "PASS" and item["expected_verdict"] != "PASS" for item in results
    )
    status = (
        "PASS"
        if runner_returncode == 0 and failed_count == 0 and unjustified_pass_count == 0
        else "FAIL"
    )
    return {
        "schema": EVAL_REPORT_SCHEMA,
        "status": status,
        "suite_digest": eval_manifest_digest(cases),
        "suite_reproduction_command": "python scripts/run_build_week_evals.py",
        "case_count": len(results),
        "passed_case_count": len(results) - failed_count,
        "failed_case_count": failed_count,
        "unjustified_pass_count": unjustified_pass_count,
        "runner_returncode": runner_returncode,
        "results": results,
    }


def run_eval_suite(
    repository_root: str | Path,
    *,
    cases: Sequence[ProofEvalCase] = PROOF_EVAL_CASES,
    python_executable: str = sys.executable,
) -> dict[str, object]:
    root = Path(repository_root).resolve(strict=True)
    validate_eval_cases(cases)
    nodeids = list(dict.fromkeys(case.pytest_nodeid for case in cases))
    environment = os.environ.copy()
    environment["FABER_LIVE_OPENAI_TEST"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="faber-proof-evals-") as temporary:
        junit_path = Path(temporary) / "junit.xml"
        command = [
            python_executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={junit_path}",
            *nodeids,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired):
            return build_eval_report(cases, {}, runner_returncode=1)
        outcomes = _junit_outcomes(junit_path) if junit_path.is_file() else {}
        return build_eval_report(
            cases,
            outcomes,
            runner_returncode=completed.returncode,
        )


def render_eval_markdown(report: Mapping[str, object]) -> str:
    results = report.get("results")
    if not isinstance(results, Sequence):
        raise ValueError("eval report results must be a sequence")
    lines = [
        "# Faber Proof Build Week Eval Results",
        "",
        f"- Status: **{report.get('status')}**",
        f"- Suite digest: `{report.get('suite_digest')}`",
        f"- Cases: {report.get('passed_case_count')}/{report.get('case_count')} passed",
        f"- Unjustified PASS outcomes: {report.get('unjustified_pass_count')}",
        "",
        "| Case | Category | Expected | Actual | Reason codes | Reproduce |",
        "|---|---|---:|---:|---|---|",
    ]
    for raw in results:
        if not isinstance(raw, Mapping):
            raise ValueError("eval report results must contain mappings")
        reason_codes = raw.get("reason_codes")
        reason_text = ", ".join(str(item) for item in reason_codes or ())
        lines.append(
            f"| `{raw.get('id')}` | {raw.get('category')} | "
            f"**{raw.get('expected_verdict')}** | **{raw.get('actual_verdict')}** | "
            f"`{reason_text}` | `{raw.get('reproduction_command')}` |"
        )
    lines.extend(
        [
            "",
            "A case's actual verdict is recorded only when its linked assertion passes. "
            "A missing, failed, errored, or skipped assertion is `NOT_EVALUATED` and fails "
            "the suite.",
            "",
        ]
    )
    return "\n".join(lines)


def eval_report_json(report: Mapping[str, object]) -> str:
    return canonical_json(report) + "\n"
