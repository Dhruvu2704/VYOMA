"""Contract compatibility tests for the VYOMA cross-role shared contracts.

Verifies the corrected shared/contracts.py shapes against the authoritative
Role 2 / Role 3 / Role 4 interfaces, and that the Role 1 pipeline still
behaves correctly with the corrected contracts and fixtures.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from shared.contracts import (
    ActivePermit,
    ActivePermits,
    AuditEvent,
    AuditLogger,
    FinalVerdict,
    RuleResult,
    RuleVerdict,
    StructuredPID,
    StructuredPTW,
    VerificationResult,
)

from ai_agent.audit import InMemoryAuditLogger
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.verification import VerificationEngine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _is_list_of_str(annotation: object) -> bool:
    return get_origin(annotation) is list and get_args(annotation) == (str,)


def _is_dict_str_float(annotation: object) -> bool:
    return (
        get_origin(annotation) is dict
        and get_args(annotation) == (str, float)
    )


class StructuredPTWContractTests(unittest.TestCase):
    def test_contains_all_role2_required_fields(self) -> None:
        hints = get_type_hints(StructuredPTW)
        required = {
            "permit_id",
            "work_type",
            "scope",
            "location",
            "start_time",
            "end_time",
            "issuer",
            "raw_document_ref",
            "equipment_tags",
            "isolation_points",
            "field_confidence",
            "low_confidence_fields",
        }
        self.assertEqual(set(hints), required)

    def test_permit_type_no_longer_exists(self) -> None:
        hints = get_type_hints(StructuredPTW)
        self.assertNotIn("permit_type", hints)

    def test_new_field_types(self) -> None:
        hints = get_type_hints(StructuredPTW)
        self.assertEqual(hints["work_type"], str)
        self.assertTrue(_is_list_of_str(hints["equipment_tags"]))
        self.assertTrue(_is_list_of_str(hints["isolation_points"]))
        self.assertTrue(_is_dict_str_float(hints["field_confidence"]))
        self.assertTrue(_is_list_of_str(hints["low_confidence_fields"]))


class StructuredPIDContractTests(unittest.TestCase):
    def test_contains_role2_pid_fields(self) -> None:
        hints = get_type_hints(StructuredPID)
        required = {
            "pid_id",
            "source",
            "equipment_tags",
            "symbols",
            "connections",
            "unresolved_symbols",
            "field_confidence",
            "low_confidence_fields",
        }
        self.assertEqual(set(hints), required)

    def test_topology_structure_is_preserved(self) -> None:
        hints = get_type_hints(StructuredPID)
        self.assertIs(get_origin(hints["symbols"]), list)
        self.assertIs(get_origin(hints["connections"]), list)
        self.assertTrue(_is_list_of_str(hints["unresolved_symbols"]))
        self.assertTrue(_is_dict_str_float(hints["field_confidence"]))

    def test_pid_symbol_and_connection_subcontracts(self) -> None:
        hints = get_type_hints(StructuredPID)
        (symbol_type,) = get_args(hints["symbols"])
        self.assertEqual(
            set(get_type_hints(symbol_type)),
            {"symbol_id", "symbol_type", "properties", "connections"},
        )
        (connection_type,) = get_args(hints["connections"])
        self.assertEqual(
            set(get_type_hints(connection_type)),
            {"source", "target", "line_ref"},
        )


class RuleVerdictConfidenceTests(unittest.TestCase):
    def test_confidence_accepts_arbitrary_strings(self) -> None:
        hints = get_type_hints(RuleVerdict)
        self.assertEqual(hints["confidence"], str)

        engine = VerificationEngine()
        for arbitrary in ("0.83", "medium", "VERY-LOW", "uncertain", "0.62"):
            verification = engine.verify(
                RuleVerdict(
                    permit_id="P1",
                    conflicting_permit_ids=[],
                    rules_triggered=[],
                    rule_result="FLAGGED",
                    explanation="x",
                    confidence=arbitrary,
                ),
                {
                    "permit_id": "P1",
                    "llm_result": "FLAGGED",
                    "explanation": "x",
                    "confidence": "MEDIUM",
                },
            )
            self.assertEqual(verification["agreement"], "AGREE")
            self.assertTrue(verification["requires_human_review"])

    def test_other_verdict_fields_unchanged(self) -> None:
        hints = get_type_hints(RuleVerdict)
        self.assertEqual(hints["rule_result"], RuleResult)
        self.assertTrue(_is_list_of_str(hints["conflicting_permit_ids"]))
        self.assertTrue(_is_list_of_str(hints["rules_triggered"]))


class AuditEventContractTests(unittest.TestCase):
    def test_contains_timestamp(self) -> None:
        hints = get_type_hints(AuditEvent)
        self.assertIn("timestamp", hints)
        self.assertEqual(hints["timestamp"], str)

    def test_retains_required_fields(self) -> None:
        hints = get_type_hints(AuditEvent)
        self.assertEqual(
            set(hints),
            {"audit_ref", "permit_id", "timestamp", "pipeline", "stages", "sequence"},
        )

    def test_orchestrator_audit_event_has_timestamp(self) -> None:
        result = AgentOrchestrator().run(
            load_fixture(FIXTURES_DIR / FIXTURE_FILES["safe"])
        )
        self.assertIsInstance(result["audit"]["timestamp"], str)
        self.assertTrue(result["audit"]["timestamp"])


class AuditLoggerInterfaceTests(unittest.TestCase):
    def test_interface_exists_with_log_operation(self) -> None:
        self.assertTrue(callable(AuditLogger.log))
        # Structural check: the minimal operation appends and returns audit_ref.
        event = AuditEvent(
            audit_ref="AUD-ABC",
            permit_id="MR-X",
            timestamp="2026-01-01T00:00:00+00:00",
            pipeline=["log"],
            stages={},
            sequence=[],
        )
        confirm = InMemoryAuditLogger().log(event)
        self.assertEqual(confirm, "AUD-ABC")

    def test_in_memory_logger_implements_interface(self) -> None:
        logger = InMemoryAuditLogger()
        self.assertIsInstance(logger, AuditLogger)
        logger.log(
            AuditEvent(
                audit_ref="AUD-1",
                permit_id="MR-1",
                timestamp="t",
                pipeline=["log"],
                stages={},
                sequence=[],
            )
        )
        self.assertEqual(logger.last_audit_ref, "AUD-1")
        self.assertEqual(len(logger.events), 1)

    def test_orchestrator_depends_on_interface(self) -> None:
        logger = InMemoryAuditLogger()
        orchestrator = AgentOrchestrator(audit_logger=logger)
        result = orchestrator.run(load_fixture(FIXTURES_DIR / FIXTURE_FILES["conflict"]))
        self.assertEqual(len(logger.events), 1)
        self.assertEqual(logger.last_audit_ref, result["audit"]["audit_ref"])
        self.assertEqual(result["final_verdict"]["audit_ref"], result["audit"]["audit_ref"])


class ActivePermitsContractTests(unittest.TestCase):
    def test_active_permit_record_fields(self) -> None:
        hints = get_type_hints(ActivePermit)
        self.assertEqual(
            set(hints), {"permit_id", "location", "start_time", "end_time", "status"}
        )
        self.assertTrue(_is_list_of_str(hints["location"]))
        self.assertEqual(hints["status"], str)

    def test_active_permits_collection_type(self) -> None:
        self.assertIs(get_origin(ActivePermits), list)
        (item,) = get_args(ActivePermits)
        self.assertIs(item, ActivePermit)

    def test_no_database_specific_fields(self) -> None:
        hints = get_type_hints(ActivePermit)
        for forbidden in ("id", "rowid", "created_at", "updated_at", "system_id"):
            self.assertNotIn(forbidden, hints)


class ContractFixtureConformanceTests(unittest.TestCase):
    """Fixture JSON must conform to the corrected contracts."""

    def test_fixtures_conform_to_structured_ptw(self) -> None:
        required = {
            "permit_id",
            "work_type",
            "scope",
            "location",
            "start_time",
            "end_time",
            "issuer",
            "raw_document_ref",
            "equipment_tags",
            "isolation_points",
            "field_confidence",
            "low_confidence_fields",
        }
        for scenario in FIXTURE_FILES:
            fixture = load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])
            ptw = fixture["structured_ptw"]
            self.assertEqual(set(ptw.keys()), required, scenario)
            self.assertNotIn("permit_type", ptw, scenario)

    def test_fixtures_include_structured_pid(self) -> None:
        for scenario in FIXTURE_FILES:
            fixture = load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])
            pid = fixture["structured_pid"]
            for key in (
                "pid_id",
                "source",
                "equipment_tags",
                "symbols",
                "connections",
                "unresolved_symbols",
                "field_confidence",
                "low_confidence_fields",
            ):
                self.assertIn(key, pid, f"{scenario}: missing {key}")
            self.assertIsInstance(pid["unresolved_symbols"], list, scenario)


class Milestone1RegressionTests(unittest.TestCase):
    """Existing Milestone 1 behavior must be unchanged."""

    def test_fixture_expectations_still_hold(self) -> None:
        expectations = {
            "safe": ("AGREE", "PASS", False),
            "conflict": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "ambiguous": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "disagreement": ("DISAGREE", "REVIEW_REQUIRED", True),
        }
        for scenario, (agreement, decision, review) in expectations.items():
            result = AgentOrchestrator().run(
                load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])
            )
            self.assertEqual(result["verification"]["agreement"], agreement, scenario)
            self.assertEqual(result["final_verdict"]["final_decision"], decision, scenario)
            self.assertEqual(
                result["final_verdict"]["requires_human_review"], review, scenario
            )

    def test_verdict_shapes_unchanged(self) -> None:
        result = AgentOrchestrator().run(load_fixture(FIXTURES_DIR / FIXTURE_FILES["safe"]))
        self.assertEqual(
            set(result["verification"]),
            {
                "permit_id",
                "rule_result",
                "llm_result",
                "agreement",
                "final_decision",
                "requires_human_review",
                "explanation",
            },
        )
        self.assertEqual(
            set(result["final_verdict"]),
            {
                "permit_id",
                "rule_result",
                "llm_result",
                "agreement",
                "final_decision",
                "explanation",
                "requires_human_review",
                "generated_at",
                "audit_ref",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)