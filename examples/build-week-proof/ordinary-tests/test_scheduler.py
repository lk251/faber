"""Ordinary tests intentionally omit the exact final-permitted-turn case."""

from __future__ import annotations

import unittest

from source.scheduler import run_conversation


class SchedulerTests(unittest.TestCase):
    def test_completes_before_budget_boundary(self) -> None:
        self.assertEqual(
            run_conversation(["FINAL: early"], 2),
            {"status": "complete", "report": "early"},
        )

    def test_incomplete_run_is_explicit_failure(self) -> None:
        self.assertEqual(run_conversation(["NOTE: draft"], 3)["status"], "failed")

    def test_cancellation_remains_a_rejection(self) -> None:
        self.assertEqual(
            run_conversation(["CANCEL"], 2),
            {"status": "failed", "reason": "cancelled"},
        )

    def test_report_composition_is_deterministic(self) -> None:
        self.assertEqual(
            run_conversation(["NOTE: premise", "FINAL: conclusion"], 3),
            {"status": "complete", "report": "premise\nconclusion"},
        )


if __name__ == "__main__":
    unittest.main()
