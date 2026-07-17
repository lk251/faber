"""Owner-controlled proof harness for the original scheduler demonstration."""

from __future__ import annotations

from pathlib import Path
from types import FunctionType


def _candidate() -> FunctionType:
    source_path = Path(__file__).resolve().parent / "source" / "scheduler.py"
    namespace: dict[str, object] = {
        "__file__": str(source_path),
        "__name__": "faber_demo_candidate_scheduler",
    }
    source = source_path.read_text(encoding="utf-8")
    exec(compile(source, str(source_path), "exec"), namespace)
    function = namespace.get("run_conversation")
    if not isinstance(function, FunctionType):
        raise TypeError("candidate scheduler does not expose run_conversation")
    return function


def boundary_report(turn_budget_token: str, *responses: str) -> object:
    prefix = "turn_budget="
    if not turn_budget_token.startswith(prefix):
        raise ValueError("turn budget token is invalid")
    turn_budget = int(turn_budget_token.removeprefix(prefix))
    return _candidate()(list(responses), turn_budget)


def failure_paths() -> dict[str, str]:
    candidate = _candidate()
    incomplete = candidate(["NOTE: draft"], 2)
    cancelled = candidate(["CANCEL"], 2)
    return {
        "incomplete": str(incomplete.get("reason")),
        "cancelled": str(cancelled.get("reason")),
    }


def ordinary_regressions() -> dict[str, int]:
    candidate = _candidate()
    cases = (
        candidate(["FINAL: early"], 2) == {"status": "complete", "report": "early"},
        candidate(["NOTE: draft"], 3).get("status") == "failed",
        candidate(["CANCEL"], 2) == {"status": "failed", "reason": "cancelled"},
        candidate(["NOTE: premise", "FINAL: conclusion"], 3)
        == {"status": "complete", "report": "premise\nconclusion"},
    )
    return {"passed": sum(cases), "total": len(cases)}


def serialization_preview(turn_budget_token: str, *responses: str) -> dict[str, object]:
    """Plausible alternative that checks shape, not the boundary contract."""

    result = boundary_report(turn_budget_token, *responses)
    return {"json_compatible": isinstance(result, dict), "field_count": len(result)}
