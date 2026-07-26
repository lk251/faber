"""Deterministic verifier calibration against local oracle fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.validation import require_non_empty_string, require_schema


@dataclass(frozen=True)
class OracleOutcome:
    sample_id: str
    task_family: str
    accepted: bool
    oracle_source: str

    def __post_init__(self) -> None:
        require_non_empty_string(self.sample_id, "sample_id")
        require_non_empty_string(self.task_family, "task_family")
        if not isinstance(self.accepted, bool):
            raise ValidationError("accepted must be a boolean")
        require_non_empty_string(self.oracle_source, "oracle_source")

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "task_family": self.task_family,
            "accepted": self.accepted,
            "oracle_source": self.oracle_source,
        }


@dataclass(frozen=True)
class VerifierPrediction:
    sample_id: str
    verifier_id: str
    task_family: str
    score_milli: int
    predicted_accept: bool
    uncertainty_milli: int
    cost: Money
    latency_ms: int
    tie: bool = False

    def __post_init__(self) -> None:
        require_non_empty_string(self.sample_id, "sample_id")
        require_non_empty_string(self.verifier_id, "verifier_id")
        require_non_empty_string(self.task_family, "task_family")
        _require_milli(self.score_milli, "score_milli")
        if not isinstance(self.predicted_accept, bool):
            raise ValidationError("predicted_accept must be a boolean")
        _require_milli(self.uncertainty_milli, "uncertainty_milli")
        if not isinstance(self.cost, Money):
            raise ValidationError("cost must be Money")
        _require_non_negative_int(self.latency_ms, "latency_ms")
        if not isinstance(self.tie, bool):
            raise ValidationError("tie must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "verifier_id": self.verifier_id,
            "task_family": self.task_family,
            "score_milli": self.score_milli,
            "predicted_accept": self.predicted_accept,
            "uncertainty_milli": self.uncertainty_milli,
            "cost": self.cost.to_dict(),
            "latency_ms": self.latency_ms,
            "tie": self.tie,
        }


@dataclass(frozen=True)
class VerifierCalibrationSet:
    name: str
    task_family: str
    outcomes: list[OracleOutcome]
    predictions: list[VerifierPrediction]
    id: str = field(default_factory=lambda: new_id("verifier-calibration-set"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.VERIFIER_CALIBRATION_SET

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.VERIFIER_CALIBRATION_SET)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.task_family, "task_family")
        if not self.outcomes:
            raise ValidationError("outcomes must contain at least one oracle outcome")
        if not self.predictions:
            raise ValidationError("predictions must contain at least one verifier prediction")
        outcome_ids = {outcome.sample_id for outcome in self.outcomes}
        if len(outcome_ids) != len(self.outcomes):
            raise ValidationError("oracle outcome sample ids must be unique")
        for outcome in self.outcomes:
            if outcome.task_family != self.task_family:
                raise ValidationError("oracle outcome task_family must match calibration set")
        for prediction in self.predictions:
            if prediction.sample_id not in outcome_ids:
                raise ValidationError("prediction sample_id must reference an oracle outcome")
            if prediction.task_family != self.task_family:
                raise ValidationError("prediction task_family must match calibration set")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "name": self.name,
            "task_family": self.task_family,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "predictions": [prediction.to_dict() for prediction in self.predictions],
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class AgreementMetric:
    correct: int
    total: int
    agreement_milli: int

    def to_dict(self) -> dict[str, int]:
        return {
            "correct": self.correct,
            "total": self.total,
            "agreement_milli": self.agreement_milli,
        }


@dataclass(frozen=True)
class FalseAcceptRisk:
    false_accepts: int
    actual_rejects: int
    risk_milli: int

    def to_dict(self) -> dict[str, int]:
        return {
            "false_accepts": self.false_accepts,
            "actual_rejects": self.actual_rejects,
            "risk_milli": self.risk_milli,
        }


@dataclass(frozen=True)
class FalseRejectRisk:
    false_rejects: int
    actual_accepts: int
    risk_milli: int

    def to_dict(self) -> dict[str, int]:
        return {
            "false_rejects": self.false_rejects,
            "actual_accepts": self.actual_accepts,
            "risk_milli": self.risk_milli,
        }


@dataclass(frozen=True)
class CalibrationReport:
    calibration_set_id: str
    calibration_set_digest: str
    verifier_id: str
    task_family: str
    agreement: AgreementMetric
    false_accept_risk: FalseAcceptRisk
    false_reject_risk: FalseRejectRisk
    total_cost: Money
    average_latency_ms: int
    average_uncertainty_milli: int
    tie_rate_milli: int
    cost_adjusted_value_milli: int
    id: str = field(default_factory=lambda: new_id("calibration-report"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.CALIBRATION_REPORT

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "calibration_set_id": self.calibration_set_id,
            "calibration_set_digest": self.calibration_set_digest,
            "verifier_id": self.verifier_id,
            "task_family": self.task_family,
            "agreement": self.agreement.to_dict(),
            "false_accept_risk": self.false_accept_risk.to_dict(),
            "false_reject_risk": self.false_reject_risk.to_dict(),
            "total_cost": self.total_cost.to_dict(),
            "average_latency_ms": self.average_latency_ms,
            "average_uncertainty_milli": self.average_uncertainty_milli,
            "tie_rate_milli": self.tie_rate_milli,
            "cost_adjusted_value_milli": self.cost_adjusted_value_milli,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


def calibrate_verifier(
    calibration_set: VerifierCalibrationSet,
    verifier_id: str,
    *,
    report_id: str | None = None,
    created_at: str | None = None,
) -> CalibrationReport:
    require_non_empty_string(verifier_id, "verifier_id")
    predictions = [
        prediction
        for prediction in calibration_set.predictions
        if prediction.verifier_id == verifier_id
    ]
    if not predictions:
        raise ValidationError("calibration set has no predictions for verifier_id")
    outcomes = {outcome.sample_id: outcome for outcome in calibration_set.outcomes}
    prediction_ids = {prediction.sample_id for prediction in predictions}
    if prediction_ids != set(outcomes):
        raise ValidationError("verifier predictions must cover every oracle outcome exactly once")
    if len(prediction_ids) != len(predictions):
        raise ValidationError("verifier predictions contain duplicate sample ids")
    currencies = {prediction.cost.currency for prediction in predictions}
    if len(currencies) != 1:
        raise ValidationError("verifier prediction costs must use one currency")
    correct = sum(
        prediction.predicted_accept == outcomes[prediction.sample_id].accepted
        for prediction in predictions
    )
    actual_rejects = sum(not outcome.accepted for outcome in outcomes.values())
    actual_accepts = sum(outcome.accepted for outcome in outcomes.values())
    false_accepts = sum(
        prediction.predicted_accept and not outcomes[prediction.sample_id].accepted
        for prediction in predictions
    )
    false_rejects = sum(
        not prediction.predicted_accept and outcomes[prediction.sample_id].accepted
        for prediction in predictions
    )
    total = len(predictions)
    agreement_milli = _ratio_milli(correct, total)
    total_cost_minor_units = sum(prediction.cost.minor_units for prediction in predictions)
    total_cost = Money(next(iter(currencies)), total_cost_minor_units)
    return CalibrationReport(
        id=report_id or new_id("calibration-report"),
        created_at=created_at or utc_now(),
        calibration_set_id=calibration_set.id,
        calibration_set_digest=calibration_set.digest(),
        verifier_id=verifier_id,
        task_family=calibration_set.task_family,
        agreement=AgreementMetric(
            correct=correct,
            total=total,
            agreement_milli=agreement_milli,
        ),
        false_accept_risk=FalseAcceptRisk(
            false_accepts=false_accepts,
            actual_rejects=actual_rejects,
            risk_milli=_ratio_milli(false_accepts, actual_rejects),
        ),
        false_reject_risk=FalseRejectRisk(
            false_rejects=false_rejects,
            actual_accepts=actual_accepts,
            risk_milli=_ratio_milli(false_rejects, actual_accepts),
        ),
        total_cost=total_cost,
        average_latency_ms=sum(item.latency_ms for item in predictions) // total,
        average_uncertainty_milli=(sum(item.uncertainty_milli for item in predictions) // total),
        tie_rate_milli=_ratio_milli(
            sum(item.tie or item.score_milli == 500 for item in predictions),
            total,
        ),
        cost_adjusted_value_milli=(agreement_milli * 1000 // max(total_cost_minor_units, 1)),
    )


def _ratio_milli(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return numerator * 1000 // denominator


def _require_milli(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 1000:
        raise ValidationError(f"{field_name} must be an integer from 0 to 1000")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")
