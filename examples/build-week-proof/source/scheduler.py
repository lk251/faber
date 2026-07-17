"""Baseline scheduler before the requested explicit budget-exhaustion behavior."""

from __future__ import annotations

from collections.abc import Sequence


def run_conversation(responses: Sequence[str], turn_budget: int) -> dict[str, str]:
    """Compose notes and return a final report when the conversation completes."""

    if turn_budget < 1:
        return {"status": "failed", "reason": "invalid_budget"}
    notes: list[str] = []
    for response in responses[:turn_budget]:
        if response == "CANCEL":
            return {"status": "failed", "reason": "cancelled"}
        if response.startswith("NOTE: "):
            notes.append(response.removeprefix("NOTE: "))
            continue
        if response.startswith("FINAL: "):
            final = response.removeprefix("FINAL: ")
            report = "\n".join([*notes, final])
            return {"status": "complete", "report": report}
    return {"status": "failed", "reason": "incomplete"}
