"""Local runner skeleton."""

from __future__ import annotations

from dataclasses import dataclass

from faber.verifiers import VerifierRun


@dataclass(frozen=True)
class LocalVerifierSpec:
    verifier_id: str
    name: str
    version: str
    command: list[str]

    def record_result(
        self,
        *,
        passed: bool,
        metrics: dict[str, object] | None = None,
        failure_reasons: list[str] | None = None,
        logs_digest: str | None = None,
    ) -> VerifierRun:
        return VerifierRun(
            verifier_id=self.verifier_id,
            name=self.name,
            version=self.version,
            command=self.command,
            passed=passed,
            metrics=metrics or {},
            failure_reasons=failure_reasons or [],
            logs_digest=logs_digest,
        )
