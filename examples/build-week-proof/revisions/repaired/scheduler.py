"""Narrow repair that preserves a complete report at the exact budget boundary."""

from __future__ import annotations

from collections.abc import Sequence


def run_conversation(responses: Sequence[str], turn_budget: int) -> dict[str, str]:
    """Compose notes and distinguish exhaustion from an incomplete response stream."""

    if turn_budget < 1:
        return {"status": "failed", "reason": "invalid_budget"}
    notes: list[str] = []
    for turn_number, response in enumerate(responses[:turn_budget], start=1):
        if response == "CANCEL":
            return {"status": "failed", "reason": "cancelled"}
        if response.startswith("NOTE: "):
            notes.append(response.removeprefix("NOTE: "))
            continue
        if response.startswith("FINAL: "):
            final = response.removeprefix("FINAL: ")
            report = "\n".join([*notes, final])
            return {"status": "complete", "report": report}
        if turn_number == turn_budget:
            return {"status": "failed", "reason": "budget_exhausted"}
    return {"status": "failed", "reason": "incomplete"}
