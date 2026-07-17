from __future__ import annotations

import math
from dataclasses import FrozenInstanceError, dataclass, replace
from typing import Any

import pytest

from faber import schemas
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ProtocolVersionError, ValidationError
from faber.golden_fixtures import (
    load_golden_fixture_corpus,
    validate_golden_fixture_corpus,
)
from faber.proofs import (
    ModelRunEvidence,
    ProofClaim,
    ProofDecision,
    ProofEvidence,
    ProofPlan,
    ProofPolicy,
    ProofTemplateSelection,
    decide_proof,
)
from faber.receipts import VerificationReceipt
from faber.schema_registry import protocol_schema_registry
from faber.verifiers import VerifierRun

CREATED_AT = "2026-07-17T00:00:00Z"
VERIFIER_ID = "verifier.proof.pytest"
VERIFIER_VERSION = "1"
BASE_REVISION = "base-revision"
CANDIDATE_REVISION = "candidate-revision"
DIFF_DIGEST = sha256_digest("bounded diff")
CATALOG_DIGEST = sha256_digest("proof catalog")
PROMPT_VERSION = "proof-planner.v1"
RESPONSE_SCHEMA_VERSION = "proof-plan-response.v1"


def _contract(*, verifier_ids: list[str] | None = None, suffix: str = "main") -> TaskContract:
    return TaskContract(
        id=f"task-contract_{suffix}",
        created_at=CREATED_AT,
        title="Prove the patch",
        description="A deterministic proof protocol fixture.",
        requirements=["The formatter preserves empty input."],
        verifier_ids=verifier_ids or [VERIFIER_ID],
    )


def _attempt(contract: TaskContract, *, suffix: str = "main") -> Attempt:
    return Attempt(
        id=f"attempt_{suffix}",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id="worker.fixture",
        base_revision=BASE_REVISION,
        candidate_revision=CANDIDATE_REVISION,
        summary="Implemented the patch.",
        patch_digest=DIFF_DIGEST,
    )


def _claim(
    claim_id: str = "claim.empty-input",
    *,
    severity: str = "high",
    evidence_required: bool = True,
) -> ProofClaim:
    return ProofClaim(
        id=claim_id,
        statement=f"{claim_id} behaves as required.",
        severity=severity,
        requirement_refs=["requirement:0"],
        evidence_required=evidence_required,
        risk_rationale="A regression would violate the task contract.",
    )


def _model_run(*, refusal: str | None = None, error_code: str | None = None) -> ModelRunEvidence:
    return ModelRunEvidence(
        provider_adapter_id="adapter.openai.proof-planner",
        requested_model_id="gpt-5.6",
        returned_model_id="gpt-5.6-2026-07-01",
        response_id="resp_fixture",
        prompt_template_version=PROMPT_VERSION,
        request_digest=sha256_digest("request"),
        structured_response_digest=sha256_digest("structured response"),
        response_schema_version=RESPONSE_SCHEMA_VERSION,
        mode="replay",
        latency_ms=123,
        input_tokens=200,
        output_tokens=50,
        refusal=refusal,
        error_code=error_code,
    )


def _selection(
    claim_id: str = "claim.empty-input",
    *,
    template_id: str = "template.pytest.empty-input",
    parameters: dict[str, object] | None = None,
) -> ProofTemplateSelection:
    return ProofTemplateSelection(
        claim_id=claim_id,
        template_id=template_id,
        template_version="1",
        parameters=parameters if parameters is not None else {"case": {"value": ""}},
        expected_behavior="The approved check passes.",
        rationale="This template directly exercises the claim.",
    )


def _plan(
    contract: TaskContract,
    attempt: Attempt,
    *,
    claims: list[ProofClaim] | None = None,
    selections: list[ProofTemplateSelection] | None = None,
    mandatory_claim_ids: list[str] | None = None,
    mandatory_template_ids: list[str] | None = None,
    uncovered_claim_ids: list[str] | None = None,
    human_review_recommended: bool = False,
    model_run: ModelRunEvidence | None = None,
) -> ProofPlan:
    actual_claims = claims if claims is not None else [_claim()]
    actual_selections = selections if selections is not None else [_selection()]
    return ProofPlan(
        task_contract_id=contract.id,
        task_contract_digest=contract.digest(),
        attempt_id=attempt.id,
        attempt_digest=attempt.digest(),
        base_revision=attempt.base_revision,
        candidate_revision=attempt.candidate_revision,
        diff_digest=attempt.patch_digest,
        proof_catalog_digest=CATALOG_DIGEST,
        prompt_template_version=PROMPT_VERSION,
        claims=actual_claims,
        selections=actual_selections,
        mandatory_claim_ids=(
            mandatory_claim_ids if mandatory_claim_ids is not None else [actual_claims[0].id]
        ),
        mandatory_template_ids=(
            mandatory_template_ids
            if mandatory_template_ids is not None
            else ([actual_selections[0].template_id] if actual_selections else [])
        ),
        uncovered_claim_ids=uncovered_claim_ids or [],
        human_review_recommended=human_review_recommended,
        model_run=model_run or _model_run(),
    )


def _run(*, passed: bool = True, suffix: str = "main") -> VerifierRun:
    return VerifierRun(
        id=f"verifier-run_{suffix}",
        created_at=CREATED_AT,
        verifier_id=VERIFIER_ID,
        name="Approved proof verifier",
        version=VERIFIER_VERSION,
        command=["python", "-m", "pytest", "approved-node"],
        passed=passed,
        metrics={"failures": 0 if passed else 1, "tests": 1},
        failure_reasons=[] if passed else ["assertion_failed"],
        logs_digest=sha256_digest(f"logs:{suffix}:{passed}"),
    )


def _receipt(
    contract: TaskContract,
    attempt: Attempt,
    run: VerifierRun,
    *,
    suffix: str = "main",
) -> VerificationReceipt:
    generated = VerificationReceipt.from_verifier_run(contract, attempt, run)
    return replace(
        generated,
        id=f"verification-receipt_{suffix}",
        created_at=CREATED_AT,
    )


def _evidence(
    plan: ProofPlan,
    selection: ProofTemplateSelection,
    run: VerifierRun | None,
    receipt: VerificationReceipt | None,
    *,
    status: str | None = None,
    claim_id: str | None = None,
    selection_digest: str | None = None,
) -> ProofEvidence:
    if status is None:
        status = "passed" if run is not None and run.passed else "failed"
    return ProofEvidence(
        proof_plan_digest=plan.digest(),
        claim_id=claim_id or selection.claim_id,
        selection_digest=selection_digest or selection.digest(),
        status=status,
        verifier_id=VERIFIER_ID,
        verifier_version=VERIFIER_VERSION,
        verifier_run_digest=run.digest() if run is not None else None,
        verification_receipt_digest=receipt.digest() if receipt is not None else None,
        expected_summary={"outcome": "pass"},
        observed_summary={"outcome": status},
        counterexample_summary=({"reason": "empty input changed"} if status == "failed" else None),
        failure_reason_codes=[] if status == "passed" else ["assertion_failed"],
    )


def _policy(
    *,
    mandatory_claim_ids: list[str] | None = None,
    mandatory_template_ids: list[str] | None = None,
    mandatory_verifier_ids: list[str] | None = None,
    approved_verifier_ids: list[str] | None = None,
    minimum_authoritative_outcomes: int = 1,
) -> ProofPolicy:
    return ProofPolicy(
        name="faber-proof-default",
        version="1",
        approved_verifier_ids=(
            approved_verifier_ids if approved_verifier_ids is not None else [VERIFIER_ID]
        ),
        mandatory_claim_ids=(
            mandatory_claim_ids if mandatory_claim_ids is not None else ["claim.empty-input"]
        ),
        mandatory_template_ids=(
            mandatory_template_ids
            if mandatory_template_ids is not None
            else ["template.pytest.empty-input"]
        ),
        mandatory_verifier_ids=(
            mandatory_verifier_ids if mandatory_verifier_ids is not None else [VERIFIER_ID]
        ),
        minimum_authoritative_outcomes=minimum_authoritative_outcomes,
    )


def _decide(
    plan: ProofPlan,
    evidence: list[ProofEvidence],
    policy: ProofPolicy,
    contract: TaskContract | None,
    attempt: Attempt | None,
    runs: list[VerifierRun] | tuple[VerifierRun, ...] = (),
    receipts: list[VerificationReceipt] | tuple[VerificationReceipt, ...] = (),
) -> ProofDecision:
    return decide_proof(
        plan,
        evidence,
        policy,
        task_contract=contract,
        attempt=attempt,
        verifier_runs=runs,
        verification_receipts=receipts,
    )


def _passing_fixture() -> tuple[
    TaskContract,
    Attempt,
    ProofPlan,
    ProofPolicy,
    VerifierRun,
    VerificationReceipt,
    ProofEvidence,
]:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    policy = _policy()
    run = _run()
    receipt = _receipt(contract, attempt, run)
    evidence = _evidence(plan, plan.selections[0], run, receipt)
    return contract, attempt, plan, policy, run, receipt, evidence


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_claim(), id="claim"),
        pytest.param(_model_run(), id="model-run"),
        pytest.param(_selection(), id="selection"),
    ],
)
def test_leaf_records_round_trip_and_have_stable_digests(record: Any) -> None:
    parsed = type(record).from_dict(record.to_dict())

    assert parsed == record
    assert parsed.to_dict() == record.to_dict()
    assert parsed.digest() == record.digest()
    assert parsed.digest() == record.digest()


def test_leaf_record_golden_digests_are_pinned() -> None:
    assert _claim().digest() == (
        "sha256:a9c9e428b95adb055e8b5f49cad6b8369619bd88d4c1b19b6d1dfa12bab66fe8"
    )
    assert _model_run().digest() == (
        "sha256:80282a588fb47463ac1e586f372a3ac0943183588f4618857dd7d4fb494c968f"
    )
    assert _selection().digest() == (
        "sha256:0bcbc6718d052a816254c68ba56e660fa71e7884b1cf018f50a12535a3b663b6"
    )


def test_plan_evidence_and_decision_round_trip_and_have_stable_digests() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    for record in (plan, evidence, decision):
        parsed = type(record).from_dict(record.to_dict())
        assert parsed == record
        assert parsed.to_dict() == record.to_dict()
        assert parsed.digest() == record.digest()


def test_plan_evidence_and_decision_golden_digests_are_pinned() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert plan.digest() == (
        "sha256:c0f833796093bbb250855cb5c132de1f52722825d42957be52d764be12f616c4"
    )
    assert evidence.digest() == (
        "sha256:f501155365db5a4b1a4d5ba7fe66516624c5182276a278b9f3bd94459eb8bec0"
    )
    assert decision.digest() == (
        "sha256:c5668a26afece0b267e9aeb647c0f940c3fff6f912843df7eb0dd7dcf3224592"
    )


@pytest.mark.parametrize(
    ("record_type", "payload"),
    [
        (ProofClaim, _claim().to_dict()),
        (ModelRunEvidence, _model_run().to_dict()),
        (ProofTemplateSelection, _selection().to_dict()),
    ],
)
def test_from_dict_rejects_unknown_fields(
    record_type: type[Any], payload: dict[str, object]
) -> None:
    payload["unexpected"] = "must not be ignored"

    with pytest.raises(ValidationError, match="unknown|unexpected"):
        record_type.from_dict(payload)


def test_nested_records_reject_unknown_fields() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    payload = _plan(contract, attempt).to_dict()
    model_run = payload["model_run"]
    assert isinstance(model_run, dict)
    model_run["hidden_prompt"] = "must not be ignored"

    with pytest.raises(ValidationError, match="unknown|hidden_prompt"):
        ProofPlan.from_dict(payload)


def test_evidence_and_decision_from_dict_reject_unknown_fields() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    for record_type, payload in (
        (ProofEvidence, evidence.to_dict()),
        (ProofDecision, decision.to_dict()),
    ):
        payload["unexpected"] = "must not be ignored"
        with pytest.raises(ValidationError, match="unknown|unexpected"):
            record_type.from_dict(payload)


def test_plan_evidence_decision_and_policy_directly_reject_unknown_fields() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    for record_type, record in (
        (ProofPlan, plan),
        (ProofEvidence, evidence),
        (ProofDecision, decision),
        (ProofPolicy, policy),
    ):
        payload = record.to_dict()
        payload["unknown_top_level_field"] = "must not be ignored"
        with pytest.raises(ValidationError, match="unknown|unknown_top_level_field"):
            record_type.from_dict(payload)


def test_schema_constants_are_registered_without_changing_existing_golden_fixtures() -> None:
    expected = {
        schemas.PROOF_CLAIM,
        schemas.MODEL_RUN_EVIDENCE,
        schemas.PROOF_TEMPLATE_SELECTION,
        schemas.PROOF_PLAN,
        schemas.PROOF_EVIDENCE,
        schemas.PROOF_DECISION,
    }
    registry = protocol_schema_registry()

    for schema_id in expected:
        assert registry.validate(schema_id).compatible
    fixtures = load_golden_fixture_corpus("tests/fixtures/golden")
    assert validate_golden_fixture_corpus(fixtures) == []


def test_records_reject_wrong_schema_versions() -> None:
    payload = _claim().to_dict()
    payload["schema"] = "faber.proof_claim.v99"

    with pytest.raises(ProtocolVersionError):
        ProofClaim.from_dict(payload)


@pytest.mark.parametrize("mode", ["", "recorded", "LIVE", "re-play"])
def test_model_run_rejects_unknown_mode(mode: str) -> None:
    with pytest.raises(ValidationError, match="mode"):
        replace(_model_run(), mode=mode)


@pytest.mark.parametrize(
    "change",
    [
        {"request_digest": "not-a-digest"},
        {"structured_response_digest": "sha256:short"},
    ],
)
def test_model_run_rejects_malformed_digests(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="digest|sha256"):
        replace(_model_run(), **change)


@pytest.mark.parametrize("severity", ["", "urgent", "HIGH", "critical "])
def test_claim_rejects_unknown_or_noncanonical_severity(severity: str) -> None:
    with pytest.raises(ValidationError, match="severity"):
        _claim(severity=severity)


@pytest.mark.parametrize("severity", ["high", "critical"])
def test_high_and_critical_claims_always_require_executable_evidence(severity: str) -> None:
    with pytest.raises(ValidationError, match="evidence"):
        _claim(severity=severity, evidence_required=False)


@pytest.mark.parametrize("status", ["", "pass", "unknown", "PASSED"])
def test_evidence_rejects_unknown_or_noncanonical_status(status: str) -> None:
    contract, attempt, plan, _policy_record, run, receipt, _valid = _passing_fixture()
    del contract, attempt

    with pytest.raises(ValidationError, match="status"):
        _evidence(plan, plan.selections[0], run, receipt, status=status)


@pytest.mark.parametrize(
    "parameters",
    [
        {"Command": "pytest"},
        {"outer": [{"command-template": ["pytest"]}]},
        {"outer": {"Working Directory": "/tmp"}},
        {"outer": {"cWd": "/tmp"}},
        {"outer": {"p.a.t.h": "/tmp"}},
        {"outer": {"ｐａｔｈ": "/tmp"}},
        {"outer": {"file_path": "/tmp/file"}},
        {"outer": {"targetPath": "/tmp/file"}},
        {"outer": {"shellCommand": "pytest"}},
        {"outer": {"python_source": "print(1)"}},
        {"outer": {"Python": "print(1)"}},
        {"outer": {"script": "echo nope"}},
        {"outer": {"SOURCE": "payload"}},
    ],
)
def test_selection_rejects_normalized_executable_keys_recursively(
    parameters: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="executable|field|key"):
        _selection(parameters=parameters)


def test_advisory_authority_values_are_closed_and_cannot_be_promoted() -> None:
    selection = _selection()
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)

    with pytest.raises(ValidationError, match="authority"):
        replace(selection, authority="authoritative")
    with pytest.raises(ValidationError, match="authority"):
        replace(plan, authority="authoritative")


@dataclass
class _NotJson:
    value: str


@pytest.mark.parametrize(
    "value",
    [
        ("tuple",),
        {"set"},
        b"bytes",
        _NotJson("dataclass"),
        {1: "non-string-key"},
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_selection_rejects_non_json_or_non_finite_parameter_values(value: object) -> None:
    with pytest.raises(ValidationError, match="JSON|finite|string key"):
        _selection(parameters={"value": value})


def test_selection_rejects_excessively_deep_json() -> None:
    value: dict[str, object] = {"leaf": True}
    for index in range(20):
        value = {f"level_{index}": value}

    with pytest.raises(ValidationError, match="depth|deep|limit"):
        _selection(parameters=value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(10**20000, id="integer-over-runtime-digit-and-byte-limits"),
        pytest.param("\ud800", id="unpaired-surrogate"),
    ],
)
def test_bounded_json_serialization_errors_are_normalized(value: object) -> None:
    with pytest.raises(
        ValidationError,
        match="JSON|serializ|Unicode|UTF-8|encoded|bounded",
    ):
        _selection(parameters={"value": value})


@pytest.mark.parametrize(
    "change",
    [
        {"expected_summary": {"value": math.nan}},
        {"observed_summary": {"value": _NotJson("not-json")}},
        {"counterexample_summary": {1: "non-string-key"}},
        {"observed_summary": {"value": "x" * 1_000_000}},
    ],
)
def test_evidence_summaries_are_strict_bounded_json(change: dict[str, object]) -> None:
    _contract_record, _attempt_record, plan, _policy_record, run, receipt, _valid = (
        _passing_fixture()
    )

    with pytest.raises(ValidationError, match="JSON|finite|string key|size|limit|bounded"):
        replace(_evidence(plan, plan.selections[0], run, receipt), **change)


@pytest.mark.parametrize(
    "change",
    [
        {"failure_reason_codes": ("assertion_failed",)},
        {"counterexample_summary": {"failure": "concrete"}},
    ],
)
def test_passed_evidence_rejects_failure_only_fields(change: dict[str, object]) -> None:
    _contract_record, _attempt_record, plan, _policy_record, run, receipt, _valid = (
        _passing_fixture()
    )

    with pytest.raises(ValidationError, match="passed|failure|counterexample|inconsistent"):
        replace(_evidence(plan, plan.selections[0], run, receipt), **change)


def test_nested_values_and_sequences_are_defensively_immutable() -> None:
    refs = ["requirement:0"]
    nested_list: list[object] = [{"value": "original"}]
    parameters: dict[str, object] = {"cases": nested_list}
    claim = ProofClaim(
        id="claim.immutable",
        statement="Input values remain immutable.",
        severity="medium",
        requirement_refs=refs,
        evidence_required=True,
    )
    selection = _selection(claim.id, parameters=parameters)
    refs.append("requirement:forged")
    nested_list.append({"value": "forged"})
    cast_first = nested_list[0]
    assert isinstance(cast_first, dict)
    cast_first["value"] = "mutated"

    assert claim.to_dict()["requirement_refs"] == ["requirement:0"]
    assert selection.to_dict()["parameters"] == {"cases": [{"value": "original"}]}
    exported = selection.to_dict()
    exported_parameters = exported["parameters"]
    assert isinstance(exported_parameters, dict)
    exported_parameters["new"] = "does not leak back"
    assert "new" not in selection.to_dict()["parameters"]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        claim.statement = "forged"  # type: ignore[misc]


def test_proof_evidence_summaries_are_deeply_defensively_immutable() -> None:
    _contract_record, _attempt_record, plan, _policy_record, run, receipt, _valid = (
        _passing_fixture()
    )
    expected: dict[str, object] = {"nested": [{"value": "expected"}]}
    observed: dict[str, object] = {"nested": [{"value": "observed"}]}
    counterexample: dict[str, object] = {"nested": [{"value": "counterexample"}]}
    evidence = replace(
        _evidence(plan, plan.selections[0], run, receipt, status="failed"),
        expected_summary=expected,
        observed_summary=observed,
        counterexample_summary=counterexample,
    )
    for original in (expected, observed, counterexample):
        nested = original["nested"]
        assert isinstance(nested, list)
        first = nested[0]
        assert isinstance(first, dict)
        first["value"] = "forged"
        nested.append({"value": "also-forged"})
        original["extra"] = True

    assert evidence.to_dict()["expected_summary"] == {"nested": [{"value": "expected"}]}
    assert evidence.to_dict()["observed_summary"] == {"nested": [{"value": "observed"}]}
    assert evidence.to_dict()["counterexample_summary"] == {"nested": [{"value": "counterexample"}]}
    exported = evidence.to_dict()
    exported_expected = exported["expected_summary"]
    assert isinstance(exported_expected, dict)
    exported_expected["forged"] = True
    assert "forged" not in evidence.to_dict()["expected_summary"]


def test_plan_canonicalizes_order_and_copies_caller_owned_lists() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claim_a = _claim("claim.a", severity="medium")
    claim_b = _claim("claim.b", severity="medium")
    selection_a = _selection("claim.a", template_id="template.a")
    selection_b = _selection("claim.b", template_id="template.b")
    claims = [claim_b, claim_a]
    selections = [selection_b, selection_a]
    plan = _plan(
        contract,
        attempt,
        claims=claims,
        selections=selections,
        mandatory_claim_ids=["claim.b", "claim.a"],
        mandatory_template_ids=["template.b", "template.a"],
    )
    claims.clear()
    selections.clear()

    assert [claim.id for claim in plan.claims] == ["claim.a", "claim.b"]
    assert [selection.claim_id for selection in plan.selections] == ["claim.a", "claim.b"]
    assert plan.to_dict()["mandatory_claim_ids"] == ["claim.a", "claim.b"]
    assert plan.to_dict()["mandatory_template_ids"] == ["template.a", "template.b"]


def test_plan_digest_is_independent_of_input_order() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claims = [_claim("claim.a", severity="medium"), _claim("claim.b", severity="medium")]
    selections = [
        _selection("claim.a", template_id="template.a"),
        _selection("claim.b", template_id="template.b"),
    ]
    first = _plan(
        contract,
        attempt,
        claims=claims,
        selections=selections,
        mandatory_claim_ids=["claim.a", "claim.b"],
        mandatory_template_ids=["template.a", "template.b"],
    )
    second = _plan(
        contract,
        attempt,
        claims=list(reversed(claims)),
        selections=list(reversed(selections)),
        mandatory_claim_ids=["claim.b", "claim.a"],
        mandatory_template_ids=["template.b", "template.a"],
    )

    assert second.to_dict() == first.to_dict()
    assert second.digest() == first.digest()


def test_plan_rejects_duplicate_claim_ids() -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="duplicate.*claim"):
        _plan(contract, attempt, claims=[_claim(), _claim()])


def test_plan_rejects_unknown_selection_claim() -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="unknown.*claim"):
        _plan(contract, attempt, selections=[_selection("claim.unknown")])


def test_plan_rejects_duplicate_claim_template_pair() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    selection = _selection()

    with pytest.raises(ValidationError, match="duplicate.*selection|claim.*template"):
        _plan(contract, attempt, selections=[selection, selection])


def test_plan_rejects_duplicate_claim_template_pair_across_versions() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    selection = _selection()

    with pytest.raises(ValidationError, match="duplicate.*selection|claim.*template"):
        _plan(
            contract,
            attempt,
            selections=[selection, replace(selection, template_version="2")],
        )


def test_plan_rejects_unknown_uncovered_claim() -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="uncovered|unknown"):
        _plan(contract, attempt, uncovered_claim_ids=["claim.unknown"])


def test_plan_rejects_mandatory_claim_or_template_removal() -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="mandatory.*claim"):
        _plan(contract, attempt, mandatory_claim_ids=["claim.removed"])
    with pytest.raises(ValidationError, match="mandatory.*template"):
        _plan(contract, attempt, mandatory_template_ids=["template.removed"])


def test_plan_rejects_mismatched_prompt_versions() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    mismatched = replace(_model_run(), prompt_template_version="other.v1")

    with pytest.raises(ValidationError, match="prompt_template_version"):
        _plan(contract, attempt, model_run=mismatched)


@pytest.mark.parametrize(
    "change",
    [
        {"task_contract_digest": "not-a-digest"},
        {"attempt_digest": "sha256:short"},
        {"diff_digest": "sha512:" + "0" * 64},
        {"proof_catalog_digest": "sha256:" + "G" * 64},
    ],
)
def test_plan_rejects_malformed_binding_digests(change: dict[str, object]) -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="digest|sha256|hex"):
        replace(_plan(contract, attempt), **change)


def test_high_risk_uncovered_claim_produces_human_review() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claim = _claim()
    plan = _plan(
        contract,
        attempt,
        claims=[claim],
        selections=[],
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
        uncovered_claim_ids=[claim.id],
    )
    policy = _policy(
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
        mandatory_verifier_ids=[],
    )

    decision = _decide(plan, [], policy, contract, attempt)

    assert decision.verdict == "human_review"
    assert claim.id in decision.uncovered_claim_ids


def test_high_risk_claim_without_selection_must_be_explicitly_uncovered() -> None:
    contract = _contract()
    attempt = _attempt(contract)

    with pytest.raises(ValidationError, match="uncovered|selection|evidence"):
        _plan(
            contract,
            attempt,
            claims=[_claim()],
            selections=[],
            mandatory_claim_ids=[],
            mandatory_template_ids=[],
            uncovered_claim_ids=[],
        )


def test_valid_authoritative_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "pass"
    assert decision.passed_claim_ids == ("claim.empty-input",)
    assert decision.failed_claim_ids == ()
    assert decision.authoritative_receipt_digests == (receipt.digest(),)


def test_valid_authoritative_failure_blocks() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)
    evidence = _evidence(plan, plan.selections[0], run, receipt)

    decision = _decide(plan, [evidence], _policy(), contract, attempt, [run], [receipt])

    assert decision.verdict == "block"
    assert decision.failed_claim_ids == ("claim.empty-input",)


def test_demonstrated_failure_precedes_other_missing_evidence() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claims = [_claim("claim.a"), _claim("claim.b")]
    selections = [
        _selection("claim.a", template_id="template.a"),
        _selection("claim.b", template_id="template.b"),
    ]
    plan = _plan(
        contract,
        attempt,
        claims=claims,
        selections=selections,
        mandatory_claim_ids=["claim.a", "claim.b"],
        mandatory_template_ids=["template.a", "template.b"],
    )
    policy = _policy(
        mandatory_claim_ids=["claim.a", "claim.b"],
        mandatory_template_ids=["template.a", "template.b"],
    )
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)
    failed = _evidence(plan, selections[0], run, receipt)

    decision = _decide(plan, [failed], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "block"
    assert decision.failed_claim_ids == ("claim.a",)
    assert "claim.b" in decision.missing_claim_ids


def test_authoritative_failure_precedes_model_refusal() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt, model_run=_model_run(refusal="refused"))
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)
    evidence = _evidence(plan, plan.selections[0], run, receipt)

    decision = _decide(
        plan,
        [evidence],
        _policy(),
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "block"


@pytest.mark.parametrize("status", ["missing", "error"])
def test_missing_or_errored_required_evidence_produces_human_review(status: str) -> None:
    contract, attempt, plan, policy, _run_record, _receipt_record, _valid = _passing_fixture()
    incomplete = _evidence(plan, plan.selections[0], None, None, status=status)

    decision = _decide(plan, [incomplete], policy, contract, attempt)

    assert decision.verdict == "human_review"
    assert "claim.empty-input" in decision.missing_claim_ids


@pytest.mark.parametrize("status", ["missing", "error"])
def test_bound_authoritative_failure_blocks_even_if_evidence_claims_no_outcome(
    status: str,
) -> None:
    contract = _contract(verifier_ids=["verifier.contract-required"])
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    policy = _policy(
        approved_verifier_ids=[VERIFIER_ID, "verifier.contract-required"],
        mandatory_verifier_ids=[],
    )
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)
    disguised_failure = _evidence(
        plan,
        plan.selections[0],
        run,
        receipt,
        status=status,
    )

    decision = _decide(
        plan,
        [disguised_failure],
        policy,
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "block"


@pytest.mark.parametrize(
    "model_run",
    [
        pytest.param(_model_run(refusal="safety refusal"), id="refusal"),
        pytest.param(_model_run(error_code="timeout"), id="terminal-error"),
    ],
)
def test_model_refusal_or_terminal_error_produces_human_review(
    model_run: ModelRunEvidence,
) -> None:
    contract, attempt, _plan_record, policy, run, receipt, _evidence_record = _passing_fixture()
    plan = _plan(contract, attempt, model_run=model_run)
    evidence = _evidence(plan, plan.selections[0], run, receipt)

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "human_review"


def test_explicit_material_human_review_recommendation_cannot_pass() -> None:
    contract, attempt, _plan_record, policy, run, receipt, _evidence_record = _passing_fixture()
    plan = _plan(contract, attempt, human_review_recommended=True)
    evidence = _evidence(plan, plan.selections[0], run, receipt)

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "human_review"


def test_evidence_from_another_plan_cannot_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    wrong_plan_evidence = replace(evidence, proof_plan_digest=sha256_digest("another plan"))

    decision = _decide(
        plan,
        [wrong_plan_evidence],
        policy,
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


def test_duplicate_identical_evidence_cannot_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()

    decision = _decide(
        plan,
        [evidence, evidence],
        policy,
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


def test_duplicate_contradictory_evidence_cannot_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    contradictory = replace(evidence, status="failed", failure_reason_codes=("forged",))

    decision = _decide(
        plan,
        [evidence, contradictory],
        policy,
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


def test_partial_multi_selection_evidence_cannot_pass() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claim = _claim()
    first_selection = _selection(template_id="template.a")
    second_selection = _selection(template_id="template.b")
    plan = _plan(
        contract,
        attempt,
        claims=[claim],
        selections=[first_selection, second_selection],
        mandatory_template_ids=["template.a", "template.b"],
    )
    policy = _policy(mandatory_template_ids=["template.a", "template.b"])
    run = _run()
    receipt = _receipt(contract, attempt, run)
    evidence = _evidence(plan, first_selection, run, receipt)

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "human_review"


def test_mandatory_verifier_authoritative_failure_blocks_without_proof_evidence() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)

    decision = _decide(plan, [], _policy(), contract, attempt, [run], [receipt])

    assert decision.verdict == "block"


def test_mandatory_verifier_cross_scan_includes_bound_receipt_digest() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = _run()
    receipt = _receipt(contract, attempt, run)

    decision = _decide(plan, [], _policy(), contract, attempt, [run], [receipt])

    assert decision.verdict == "human_review"
    assert receipt.digest() in decision.authoritative_receipt_digests


def test_pass_shaped_evidence_without_receipt_cannot_pass() -> None:
    contract, attempt, plan, policy, run, _receipt_record, _evidence_record = _passing_fixture()
    evidence = _evidence(plan, plan.selections[0], run, None, status="passed")

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [])

    assert decision.verdict == "human_review"


def test_missing_actual_authority_records_cannot_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()

    no_contract = _decide(plan, [evidence], policy, None, attempt, [run], [receipt])
    no_attempt = _decide(plan, [evidence], policy, contract, None, [run], [receipt])
    no_run = _decide(plan, [evidence], policy, contract, attempt, [], [receipt])
    no_receipt = _decide(plan, [evidence], policy, contract, attempt, [run], [])

    assert {no_contract.verdict, no_attempt.verdict, no_run.verdict, no_receipt.verdict} == {
        "human_review"
    }


def test_valid_looking_but_unrelated_receipt_cannot_pass() -> None:
    contract, attempt, plan, policy, run, _receipt_record, _evidence_record = _passing_fixture()
    unrelated_contract = _contract(suffix="unrelated")
    unrelated_attempt = _attempt(unrelated_contract, suffix="unrelated")
    unrelated_receipt = _receipt(unrelated_contract, unrelated_attempt, run, suffix="unrelated")
    evidence = _evidence(plan, plan.selections[0], run, unrelated_receipt, status="passed")

    decision = _decide(
        plan,
        [evidence],
        policy,
        contract,
        attempt,
        [run],
        [unrelated_receipt],
    )

    assert decision.verdict == "human_review"


def test_unrelated_or_missing_receipt_does_not_create_authoritative_block() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    failed_run = _run(passed=False)
    unrelated_contract = _contract(suffix="unrelated")
    unrelated_attempt = _attempt(unrelated_contract, suffix="unrelated")
    unrelated_receipt = _receipt(
        unrelated_contract,
        unrelated_attempt,
        failed_run,
        suffix="unrelated",
    )
    forged_failure = _evidence(plan, plan.selections[0], failed_run, unrelated_receipt)

    with_unrelated = _decide(
        plan,
        [forged_failure],
        _policy(),
        contract,
        attempt,
        [failed_run],
        [unrelated_receipt],
    )
    without_receipt = _decide(
        plan,
        [replace(forged_failure, verification_receipt_digest=None)],
        _policy(),
        contract,
        attempt,
        [failed_run],
        [],
    )

    assert with_unrelated.verdict == "human_review"
    assert without_receipt.verdict == "human_review"


@pytest.mark.parametrize(
    "receipt_change",
    [
        {"task_contract_digest": sha256_digest("wrong contract")},
        {"attempt_id": "attempt_other"},
        {"worker_id": "worker.other"},
        {"base_revision": "base-other"},
        {"candidate_revision": "candidate-other"},
        {"verifier_id": "verifier.other"},
        {"verifier_digest": sha256_digest("wrong verifier")},
        {"result_digest": sha256_digest("wrong result")},
        {"metrics": {"tests": 999, "failures": 0}},
        {"failure_reasons": ["forged receipt narrative"]},
        {"accepted": False},
    ],
)
def test_forged_receipt_bindings_cannot_pass(receipt_change: dict[str, object]) -> None:
    contract, attempt, plan, policy, run, receipt, _valid = _passing_fixture()
    forged = replace(receipt, **receipt_change)
    evidence = _evidence(plan, plan.selections[0], run, forged, status="passed")

    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [forged])

    assert decision.verdict == "human_review"


def test_plan_must_resolve_to_exact_task_attempt_diff_and_revisions() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    wrong_contract = _contract(suffix="wrong")
    wrong_attempt = replace(attempt, patch_digest=sha256_digest("wrong patch"))

    wrong_contract_decision = _decide(
        plan,
        [evidence],
        policy,
        wrong_contract,
        attempt,
        [run],
        [receipt],
    )
    wrong_attempt_decision = _decide(
        plan,
        [evidence],
        policy,
        contract,
        wrong_attempt,
        [run],
        [receipt],
    )

    assert wrong_contract_decision.verdict == "human_review"
    assert wrong_attempt_decision.verdict == "human_review"


def test_run_and_receipt_result_must_resolve_exactly() -> None:
    contract, attempt, plan, policy, run, receipt, _valid = _passing_fixture()
    forged_run = replace(run, metrics={"tests": 999, "failures": 0})
    evidence = _evidence(plan, plan.selections[0], forged_run, receipt, status="passed")

    decision = _decide(
        plan,
        [evidence],
        policy,
        contract,
        attempt,
        [forged_run],
        [receipt],
    )

    assert decision.verdict == "human_review"


@pytest.mark.parametrize("truthy_non_bool", ["false", "true", 1, ["passed"]])
def test_truthy_non_boolean_authority_results_cannot_produce_pass(
    truthy_non_bool: object,
) -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = replace(_run(), passed=truthy_non_bool)  # type: ignore[arg-type]
    receipt = _receipt(contract, attempt, run)
    assert receipt.accepted == truthy_non_bool
    evidence = _evidence(plan, plan.selections[0], run, receipt, status="passed")

    decision = _decide(
        plan,
        [evidence],
        _policy(),
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


@pytest.mark.parametrize("failure_reason", ["assertion_failed", 1])
def test_passing_authority_with_failure_reasons_cannot_produce_pass(
    failure_reason: object,
) -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = replace(_run(), failure_reasons=[failure_reason])  # type: ignore[list-item]
    receipt = _receipt(contract, attempt, run)
    evidence = _evidence(plan, plan.selections[0], run, receipt, status="passed")

    decision = _decide(
        plan,
        [evidence],
        _policy(),
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


@pytest.mark.parametrize(
    "change",
    [
        {"verifier_id": "verifier.other"},
        {"verifier_version": "999"},
    ],
)
def test_evidence_verifier_identity_must_match_actual_run(change: dict[str, object]) -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    forged = replace(evidence, **change)

    decision = _decide(plan, [forged], policy, contract, attempt, [run], [receipt])

    assert decision.verdict == "human_review"


def test_authoritative_failure_blocks_even_if_evidence_lies_about_status() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    plan = _plan(contract, attempt)
    run = _run(passed=False)
    receipt = _receipt(contract, attempt, run)
    lying_evidence = _evidence(
        plan,
        plan.selections[0],
        run,
        receipt,
        status="passed",
    )

    decision = _decide(
        plan,
        [lying_evidence],
        _policy(),
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "block"


def test_verifier_must_be_approved_by_task_and_policy() -> None:
    contract, attempt, plan, _policy_record, run, receipt, evidence = _passing_fixture()
    unapproved_policy = _policy(approved_verifier_ids=["verifier.other"])
    unapproved_contract = replace(contract, verifier_ids=["verifier.other"])

    policy_decision = _decide(
        plan,
        [evidence],
        unapproved_policy,
        contract,
        attempt,
        [run],
        [receipt],
    )
    contract_decision = _decide(
        plan,
        [evidence],
        _policy(),
        unapproved_contract,
        attempt,
        [run],
        [receipt],
    )

    assert policy_decision.verdict == "human_review"
    assert contract_decision.verdict == "human_review"


def test_independent_policy_mandatory_sets_cannot_be_weakened_by_plan() -> None:
    contract, attempt, plan, _policy_record, run, receipt, evidence = _passing_fixture()
    independent_policy = _policy(
        mandatory_claim_ids=["claim.policy-only"],
        mandatory_template_ids=["template.policy-only"],
        mandatory_verifier_ids=["verifier.policy-only"],
        approved_verifier_ids=[VERIFIER_ID, "verifier.policy-only"],
    )

    decision = _decide(
        plan,
        [evidence],
        independent_policy,
        contract,
        attempt,
        [run],
        [receipt],
    )

    assert decision.verdict == "human_review"


@pytest.mark.parametrize("value", [True, False, 1.0, "1", 0])
def test_policy_minimum_authoritative_outcomes_requires_a_positive_integer(
    value: object,
) -> None:
    with pytest.raises(ValidationError, match="minimum_authoritative_outcomes|positive"):
        ProofPolicy(
            name="strict-policy",
            version="1",
            approved_verifier_ids=[VERIFIER_ID],
            minimum_authoritative_outcomes=value,  # type: ignore[arg-type]
        )


def test_no_vacuous_pass_when_plan_and_policy_have_no_obligations() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    low_claim = _claim("claim.informational", severity="low", evidence_required=False)
    plan = _plan(
        contract,
        attempt,
        claims=[low_claim],
        selections=[],
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
        uncovered_claim_ids=[low_claim.id],
    )
    policy = _policy(
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
        mandatory_verifier_ids=[],
        minimum_authoritative_outcomes=1,
    )
    assert policy.mandatory_claim_ids == ()
    assert policy.mandatory_template_ids == ()
    assert policy.mandatory_verifier_ids == ()

    decision = _decide(plan, [], policy, contract, attempt)

    assert decision.verdict == "human_review"


def test_every_selection_is_an_obligation_even_for_optional_low_claim() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claim = _claim("claim.optional", severity="low", evidence_required=False)
    selection = _selection(claim.id, template_id="template.optional")
    plan = _plan(
        contract,
        attempt,
        claims=[claim],
        selections=[selection],
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
    )
    policy = _policy(
        mandatory_claim_ids=[],
        mandatory_template_ids=[],
        mandatory_verifier_ids=[],
    )
    assert policy.mandatory_claim_ids == ()
    assert policy.mandatory_template_ids == ()
    assert policy.mandatory_verifier_ids == ()

    decision = _decide(plan, [], policy, contract, attempt)

    assert decision.verdict == "human_review"
    assert claim.id in decision.missing_claim_ids


def test_unknown_claim_or_selection_evidence_cannot_pass() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    unknown_claim = replace(evidence, claim_id="claim.unknown")
    unknown_selection = replace(evidence, selection_digest=sha256_digest("unknown selection"))

    for forged in (unknown_claim, unknown_selection):
        decision = _decide(
            plan,
            [forged],
            policy,
            contract,
            attempt,
            [run],
            [receipt],
        )
        assert decision.verdict == "human_review"


def test_decision_is_repeatable_sorted_and_has_no_generated_identity_or_time() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()

    first = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])
    second = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])

    assert second == first
    assert second.digest() == first.digest()
    assert list(first.reason_codes) == sorted(set(first.reason_codes))
    assert "id" not in first.to_dict()
    assert "created_at" not in first.to_dict()


def test_decision_is_invariant_under_evidence_and_authority_input_permutations() -> None:
    contract = _contract()
    attempt = _attempt(contract)
    claims = [_claim("claim.a"), _claim("claim.b")]
    selections = [
        _selection("claim.a", template_id="template.a"),
        _selection("claim.b", template_id="template.b"),
    ]
    plan = _plan(
        contract,
        attempt,
        claims=claims,
        selections=selections,
        mandatory_claim_ids=["claim.a", "claim.b"],
        mandatory_template_ids=["template.a", "template.b"],
    )
    policy = _policy(
        mandatory_claim_ids=["claim.a", "claim.b"],
        mandatory_template_ids=["template.a", "template.b"],
    )
    run_a = _run(suffix="a")
    run_b = _run(suffix="b")
    receipt_a = _receipt(contract, attempt, run_a, suffix="a")
    receipt_b = _receipt(contract, attempt, run_b, suffix="b")
    evidence_a = _evidence(plan, selections[0], run_a, receipt_a)
    evidence_b = _evidence(plan, selections[1], run_b, receipt_b)

    forward = _decide(
        plan,
        [evidence_a, evidence_b],
        policy,
        contract,
        attempt,
        [run_a, run_b],
        [receipt_a, receipt_b],
    )
    reverse = _decide(
        plan,
        [evidence_b, evidence_a],
        policy,
        contract,
        attempt,
        [run_b, run_a],
        [receipt_b, receipt_a],
    )

    assert reverse == forward
    assert reverse.digest() == forward.digest()
    assert forward.verdict == "pass"


def test_proof_decision_rejects_internally_inconsistent_pass_payload() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])
    forged_payload = decision.to_dict()
    forged_payload["failed_claim_ids"] = ["claim.empty-input"]

    with pytest.raises(ValidationError, match="pass|failed|inconsistent"):
        ProofDecision.from_dict(forged_payload)


@pytest.mark.parametrize(
    "reason_codes",
    [
        ["human_review_required"],
        ["authoritative_claim_failure"],
        ["proof_passed", "model_refusal"],
    ],
)
def test_proof_decision_rejects_forged_pass_reason_codes(
    reason_codes: list[str],
) -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    decision = _decide(plan, [evidence], policy, contract, attempt, [run], [receipt])
    forged_payload = decision.to_dict()
    forged_payload["reason_codes"] = reason_codes

    with pytest.raises(ValidationError, match="pass|proof_passed|reason"):
        ProofDecision.from_dict(forged_payload)


def test_decide_proof_does_not_mutate_any_input_or_caller_owned_nested_values() -> None:
    contract, attempt, plan, policy, run, receipt, evidence = _passing_fixture()
    evidence_input = [evidence]
    runs_input = [run]
    receipts_input = [receipt]
    before = (
        plan.to_dict(),
        evidence.to_dict(),
        policy.to_dict(),
        contract.to_dict(),
        attempt.to_dict(),
        run.to_dict(),
        receipt.to_dict(),
    )

    _decide(
        plan,
        evidence_input,
        policy,
        contract,
        attempt,
        runs_input,
        receipts_input,
    )

    assert evidence_input == [evidence]
    assert runs_input == [run]
    assert receipts_input == [receipt]
    assert before == (
        plan.to_dict(),
        evidence.to_dict(),
        policy.to_dict(),
        contract.to_dict(),
        attempt.to_dict(),
        run.to_dict(),
        receipt.to_dict(),
    )
