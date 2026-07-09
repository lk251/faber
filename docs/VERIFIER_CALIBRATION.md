# Verifier Calibration

Faber measures verifier quality against local `OracleOutcome` fixtures from hard
verifiers or human review. A `VerifierCalibrationSet` is scoped to one task
family and can contain predictions from several verifier candidates.

`CalibrationReport` records agreement, false-accept risk, false-reject risk,
uncertainty, tie rate, latency, total integer-minor-unit cost, and a deterministic
cost-adjusted value score. Reports are stable canonical records suitable for
audit and later router features.

Calibration is task-family specific. A verifier that works well for a Python
bugfix is not assumed to work equally well for documentation, security, or
product-fit review. Current fixtures are local and deterministic; no model API is
called. Future verifier routing should compare quality, risk, latency, and cost
rather than treating solver verification as free or infallible.
