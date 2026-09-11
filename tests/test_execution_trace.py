"""The agent execution trace is real orchestrator output.

Every completed run must record one entry per pipeline stage with a status and
a timestamp, and the same trace must surface identically in the audit
snapshot. Tests guard against a fabricated/placeholder stage list.
"""

import unittest
from datetime import datetime
from pathlib import Path

from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.plant_safety_integration import evaluate_plant_safety

REPO = Path(__file__).resolve().parent.parent
CONFLICT_FIXTURE = REPO / "ai_agent" / "fixtures" / "conflict_case.json"


class ExecutionTraceTest(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        self.result = self.orchestrator.run(load_fixture(CONFLICT_FIXTURE))

    def test_result_exposes_one_entry_per_pipeline_stage(self):
        self.assertEqual(
            AgentOrchestrator.PIPELINE_STAGES,
            [entry["stage"] for entry in self.result["execution_trace"]],
        )

    def test_every_entry_has_status_and_iso_timestamp(self):
        for entry in self.result["execution_trace"]:
            self.assertEqual(sorted(entry.keys()), ["stage", "status", "timestamp"])
            self.assertIn(entry["status"], ("completed", "failed", "running"))
            parsed = datetime.fromisoformat(entry["timestamp"])
            self.assertIsNotNone(parsed)

    def test_completed_run_marks_all_stages_completed(self):
        self.assertNotIn(
            "failed",
            {entry["status"] for entry in self.result["execution_trace"]},
        )

    def test_trace_surfaces_identically_in_audit_snapshot(self):
        self.assertEqual(
            self.result["audit"]["stages"]["execution_trace"],
            self.result["execution_trace"],
        )