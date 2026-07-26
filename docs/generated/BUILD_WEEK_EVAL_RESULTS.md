# Faber Proof Build Week Eval Results

- Status: **PASS**
- Suite digest: `sha256:eec59f8fcf20e546971010a466514841ffd5cdf60cbff978c9ddf43c1164c27c`
- Cases: 49/49 passed
- Unjustified PASS outcomes: 0

| Case | Category | Expected | Actual | Reason codes | Reproduce |
|---|---|---:|---:|---|---|
| `repository.prompt-injection-comment` | untrusted_repository | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `untrusted_repository_content` | `python -m pytest -q tests/test_openai_proof_planner.py::test_prompt_injection_in_diff_remains_labeled_untrusted_data` |
| `repository.instruction-like-string` | untrusted_repository | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `untrusted_repository_content` | `python -m pytest -q tests/test_openai_proof_planner.py::test_instruction_like_string_literal_remains_untrusted_data` |
| `repository.secret-like-value` | untrusted_repository | **BLOCK** | **BLOCK** | `secret_detected` | `python -m pytest -q tests/test_openai_proof_planner.py::test_secret_like_diff_values_are_redacted_before_serialization_and_digest` |
| `repository.oversized-diff` | untrusted_repository | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `request_too_large` | `python -m pytest -q tests/test_openai_proof_planner.py::test_request_size_limits_fail_closed` |
| `repository.generated-output-excluded` | untrusted_repository | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `generated_output_excluded` | `python -m pytest -q tests/test_proof_product.py::test_git_context_is_local_bounded_deterministic_and_excludes_outputs` |
| `repository.unicode-line-ending-digest` | untrusted_repository | **PASS** | **PASS** | `stable_normalized_digest` | `python -m pytest -q tests/test_openai_proof_planner.py::test_diff_line_endings_are_normalized_before_binding` |
| `repository.diff-attempt-mismatch` | untrusted_repository | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `attempt_binding_mismatch` | `python -m pytest -q tests/test_openai_proof_planner.py::test_diff_text_must_bind_to_attempt_patch_digest` |
| `planner.unknown-entry` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `unknown_template` | `python -m pytest -q tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan` |
| `planner.stale-entry-version` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `stale_catalog_entry` | `python -m pytest -q tests/test_proof_executors.py::test_catalog_rejects_duplicate_and_stale_active_entries` |
| `planner.extra-field` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `invalid_structured_output` | `python -m pytest -q tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan` |
| `planner.nested-operational-field` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `invalid_parameters` | `python -m pytest -q tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan` |
| `planner.missing-mandatory-template` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `missing_mandatory_template` | `python -m pytest -q tests/test_openai_proof_planner.py::test_missing_mandatory_template_fails_closed` |
| `planner.duplicate-claim` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `duplicate_claim` | `python -m pytest -q tests/test_proofs.py::test_plan_rejects_duplicate_claim_ids` |
| `planner.duplicate-selection` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `duplicate_selection` | `python -m pytest -q tests/test_proofs.py::test_plan_rejects_duplicate_claim_template_pair` |
| `planner.malformed-parameters` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `invalid_parameters` | `python -m pytest -q tests/test_openai_proof_planner.py::test_invalid_model_output_never_materializes_a_plan` |
| `planner.oversized-parameters` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `input_limit` | `python -m pytest -q tests/test_proof_executors.py::test_oversized_parameter_is_rejected_before_launch` |
| `planner.refusal` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `refusal` | `python -m pytest -q tests/test_openai_proof_planner.py::test_refusal_wins_over_valid_looking_structured_response_and_is_not_retried` |
| `planner.timeout` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `timeout` | `python -m pytest -q tests/test_openai_proof_planner.py::test_timeout_is_terminal_when_retry_budget_is_zero` |
| `planner.invalid-structured-response` | planner_output | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `invalid_structured_output` | `python -m pytest -q tests/test_openai_proof_planner.py::test_structured_response_parser_rejects_non_strict_json` |
| `replay.request-mismatch` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `replay_mismatch` | `python -m pytest -q tests/test_openai_proof_planner.py::test_replay_rejects_a_different_task_or_diff_context` |
| `replay.catalog-mismatch` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `replay_mismatch` | `python -m pytest -q tests/test_openai_proof_planner.py::test_replay_rejects_catalog_prompt_schema_and_model_mismatches` |
| `replay.prompt-schema-mismatch` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `replay_mismatch` | `python -m pytest -q tests/test_openai_proof_planner.py::test_replay_rejects_self_consistent_stale_prompt_and_schema_context` |
| `replay.response-digest-tamper` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `replay_mismatch` | `python -m pytest -q tests/test_openai_proof_planner.py::test_replay_rejects_structured_response_digest_tampering` |
| `replay.cross-candidate` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `replay_mismatch` | `python -m pytest -q tests/test_proof_demo.py::test_bad_replay_is_rejected_after_repaired_diff` |
| `replay.critic-disabled` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `configuration_error` | `python -m pytest -q tests/test_proof_product.py::test_critic_mode_is_disabled_fail_closed` |
| `replay.critic-contradiction` | replay | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `configuration_error` | `python -m pytest -q tests/test_proof_product.py::test_critic_mode_is_disabled_fail_closed` |
| `execution.path-traversal` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `path_not_allowed` | `python -m pytest -q tests/test_proof_executors.py::test_catalog_path_rejects_absolute_traversal_unc_drive_and_backslash_forms` |
| `execution.symlink-escape` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `path_not_allowed` | `python -m pytest -q tests/test_proof_executors.py::test_catalog_path_rejects_a_symlink_escape` |
| `execution.missing-verifier` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `registry_mismatch` | `python -m pytest -q tests/test_proof_executors.py::test_stale_registered_verifier_is_rejected_before_launch` |
| `execution.missing-callable` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `capability_preflight_failed` | `python -m pytest -q tests/test_proof_executors.py::test_missing_or_stale_catalog_capability_is_rejected_before_launch` |
| `execution.timeout` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `timeout` | `python -m pytest -q tests/test_proof_executors.py::test_timeout_and_output_cap_are_terminal_executor_errors` |
| `execution.output-truncation` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `output_limit` | `python -m pytest -q tests/test_proof_executors.py::test_existing_command_output_overflow_cannot_become_authoritative` |
| `execution.operational-error` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `operational_error` | `python -m pytest -q tests/test_proof_executors.py::test_operational_error_only_can_never_yield_pass` |
| `evidence.task-attempt-binding` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `authority_context_unbound` | `python -m pytest -q tests/test_proofs.py::test_plan_must_resolve_to_exact_task_attempt_diff_and_revisions` |
| `evidence.plan-selection-binding` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `verifier_run_binding_mismatch` | `python -m pytest -q tests/test_proofs.py::test_evidence_from_another_plan_cannot_pass` |
| `evidence.catalog-policy-binding` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `workflow_binding_mismatch` | `python -m pytest -q tests/test_proof_executors.py::test_workflow_binding_and_policy_mismatches_make_zero_launcher_calls` |
| `evidence.receipt-swap` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `verification_receipt_binding_mismatch` | `python -m pytest -q tests/test_proofs.py::test_valid_looking_but_unrelated_receipt_cannot_pass` |
| `evidence.duplicate` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `duplicate_evidence` | `python -m pytest -q tests/test_proofs.py::test_duplicate_identical_evidence_cannot_pass` |
| `evidence.contradictory` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `contradictory_evidence` | `python -m pytest -q tests/test_proofs.py::test_duplicate_contradictory_evidence_cannot_pass` |
| `evidence.ordinary-green-high-uncovered` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `high_risk_claim_uncovered` | `python -m pytest -q tests/test_proofs.py::test_high_risk_uncovered_claim_produces_human_review` |
| `evidence.candidate-success-authority-failure` | execution_evidence | **BLOCK** | **BLOCK** | `authoritative_failure` | `python -m pytest -q tests/test_proofs.py::test_authoritative_failure_blocks_even_if_evidence_lies_about_status` |
| `evidence.block-precedes-missing` | execution_evidence | **BLOCK** | **BLOCK** | `authoritative_failure, required_evidence_missing` | `python -m pytest -q tests/test_proofs.py::test_demonstrated_failure_precedes_other_missing_evidence` |
| `bundle.partial` | execution_evidence | **HUMAN_REVIEW** | **HUMAN_REVIEW** | `artifact_unavailable` | `python -m pytest -q tests/test_proof_product.py::test_partial_bundle_cannot_validate_as_complete` |
| `replay.stable-authority-digests` | execution_evidence | **PASS** | **PASS** | `stable_authority_digests` | `python -m pytest -q tests/test_proof_demo.py::test_repeated_replay_has_stable_plan_evidence_and_decision_digests` |
| `baseline.authoritative-pass` | baseline | **PASS** | **PASS** | `all_required_evidence_passed` | `python -m pytest -q tests/test_proofs.py::test_valid_authoritative_pass` |
| `baseline.demo-bad-block` | baseline | **BLOCK** | **BLOCK** | `assertion_failed` | `python -m pytest -q tests/test_proof_demo.py::test_one_command_demo_produces_memorable_authoritative_contrast` |
| `baseline.demo-repaired-pass` | baseline | **PASS** | **PASS** | `all_required_evidence_passed` | `python -m pytest -q tests/test_proof_demo.py::test_one_command_demo_produces_memorable_authoritative_contrast` |
| `privacy.safe-artifacts` | baseline | **PASS** | **PASS** | `privacy_audit_passed` | `python -m pytest -q tests/test_proof_privacy.py::test_safe_artifacts_produce_deterministic_pass_report` |
| `privacy.secret-path-asset-output` | baseline | **BLOCK** | **BLOCK** | `privacy_finding` | `python -m pytest -q tests/test_proof_privacy.py::test_covered_secrets_paths_assets_and_raw_output_fail_without_echoing_values` |

A case's actual verdict is recorded only when its linked assertion passes. A missing, failed, errored, or skipped assertion is `NOT_EVALUATED` and fails the suite.
