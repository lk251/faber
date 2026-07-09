# 0057 — Verifier calibration and oracle comparison

## Goal

Measure verifier quality, not just solver quality.

## Scope

Add calibration objects and fixtures:

- `VerifierCalibrationSet`
- `OracleOutcome`
- `VerifierPrediction`
- `CalibrationReport`
- `AgreementMetric`
- `FalseAcceptRisk`
- `FalseRejectRisk`

## Requirements

- Use local fixtures only.
- Compare advisory/probabilistic scores to hard verifier outcomes and human review fixtures.
- Track verifier cost, latency, uncertainty, tie rate, and agreement.
- Support task-family-specific calibration.
- Do not use real model APIs.

## Tests

- perfect verifier fixture scores high
- noisy verifier fixture scores lower
- false accept and false reject rates are calculated
- cost-adjusted verifier value is calculated using integer money
- calibration report exports stable JSON

## Acceptance criteria

Faber can decide which verifier is worth using for which task family and budget.