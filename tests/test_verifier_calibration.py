from faber.calibration import (
    OracleOutcome,
    VerifierCalibrationSet,
    VerifierPrediction,
    calibrate_verifier,
)
from faber.money import Money

CREATED_AT = "2026-01-01T00:00:00Z"


def _outcomes() -> list[OracleOutcome]:
    return [
        OracleOutcome(
            sample_id=f"sample-{index}",
            task_family="python-bugfix",
            accepted=accepted,
            oracle_source="hard_verifier",
        )
        for index, accepted in enumerate([True, True, False, False])
    ]


def _predictions(
    decisions: list[bool],
    *,
    verifier_id: str,
    cost: int = 10,
) -> list[VerifierPrediction]:
    return [
        VerifierPrediction(
            sample_id=f"sample-{index}",
            verifier_id=verifier_id,
            task_family="python-bugfix",
            score_milli=900 if decision else 100,
            predicted_accept=decision,
            uncertainty_milli=50,
            cost=Money("EUR", cost),
            latency_ms=100,
        )
        for index, decision in enumerate(decisions)
    ]


def _set(predictions: list[VerifierPrediction]) -> VerifierCalibrationSet:
    return VerifierCalibrationSet(
        id="verifier-calibration-set_fixture",
        created_at=CREATED_AT,
        name="Python bugfix calibration",
        task_family="python-bugfix",
        outcomes=_outcomes(),
        predictions=predictions,
    )


def test_perfect_verifier_fixture_scores_high() -> None:
    report = calibrate_verifier(
        _set(_predictions([True, True, False, False], verifier_id="verifier.perfect")),
        "verifier.perfect",
        report_id="calibration-report_perfect",
        created_at=CREATED_AT,
    )

    assert report.agreement.agreement_milli == 1000
    assert report.false_accept_risk.risk_milli == 0
    assert report.false_reject_risk.risk_milli == 0


def test_noisy_verifier_fixture_scores_lower() -> None:
    perfect = calibrate_verifier(
        _set(_predictions([True, True, False, False], verifier_id="verifier.perfect")),
        "verifier.perfect",
        report_id="calibration-report_perfect",
        created_at=CREATED_AT,
    )
    noisy = calibrate_verifier(
        _set(_predictions([True, False, True, False], verifier_id="verifier.noisy")),
        "verifier.noisy",
        report_id="calibration-report_noisy",
        created_at=CREATED_AT,
    )

    assert noisy.agreement.agreement_milli == 500
    assert noisy.agreement.agreement_milli < perfect.agreement.agreement_milli


def test_false_accept_and_false_reject_rates_are_calculated() -> None:
    report = calibrate_verifier(
        _set(_predictions([True, False, True, False], verifier_id="verifier.noisy")),
        "verifier.noisy",
        report_id="calibration-report_risks",
        created_at=CREATED_AT,
    )

    assert report.false_accept_risk.false_accepts == 1
    assert report.false_accept_risk.actual_rejects == 2
    assert report.false_accept_risk.risk_milli == 500
    assert report.false_reject_risk.false_rejects == 1
    assert report.false_reject_risk.risk_milli == 500


def test_cost_adjusted_verifier_value_uses_integer_money() -> None:
    cheap = calibrate_verifier(
        _set(_predictions([True, True, False, False], verifier_id="verifier.cheap", cost=10)),
        "verifier.cheap",
        report_id="calibration-report_cheap",
        created_at=CREATED_AT,
    )
    expensive = calibrate_verifier(
        _set(
            _predictions(
                [True, True, False, False],
                verifier_id="verifier.expensive",
                cost=100,
            )
        ),
        "verifier.expensive",
        report_id="calibration-report_expensive",
        created_at=CREATED_AT,
    )

    assert isinstance(cheap.total_cost.minor_units, int)
    assert cheap.cost_adjusted_value_milli > expensive.cost_adjusted_value_milli


def test_calibration_report_exports_stable_json() -> None:
    calibration_set = _set(_predictions([True, True, False, False], verifier_id="verifier.stable"))
    left = calibrate_verifier(
        calibration_set,
        "verifier.stable",
        report_id="calibration-report_stable",
        created_at=CREATED_AT,
    )
    right = calibrate_verifier(
        calibration_set,
        "verifier.stable",
        report_id="calibration-report_stable",
        created_at=CREATED_AT,
    )

    assert left.to_dict() == right.to_dict()
    assert left.digest() == right.digest()
    assert left.task_family == "python-bugfix"
