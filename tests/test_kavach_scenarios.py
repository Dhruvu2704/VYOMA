"""KAVACH nine-scenario coverage through the PRODUCTION integrated pipeline.

Each of the nine required demo cases is exercised through ``execute_fixture``
- the exact ``DEFAULT_ENTRYPOINT`` the backend uses
(``build_provider_orchestrator(..., plant_safety=True)``). The asserted
outcome tuple is::

    (deterministic_rule_result, llm_result, agreement,
     final_decision, requires_human_review)

plus an explicit ``failed_stage`` assertion (None for any completed run).

Scenarios covered:
 1. SAFE                       -> PASS / PASS / AGREE / PASS / False
 2. HOT-WORK CONFLICT          -> FLAGGED / FLAGGED / AGREE / FLAGGED_FOR_REVIEW / True
 3. ISOLATION CONFLICT         -> FLAGGED / FLAGGED / AGREE / FLAGGED_FOR_REVIEW / True
 4. MULTIPLE CONFLICTS         -> FLAGGED / FLAGGED / AGREE / FLAGGED_FOR_REVIEW / True
 5. UNKNOWN TAG                -> FLAGGED / FLAGGED / AGREE / FLAGGED_FOR_REVIEW / True
 6. AMBIGUOUS                  -> FLAGGED / FLAGGED / AGREE / FLAGGED_FOR_REVIEW / True
 7. LLM/DETERMINISTIC DISAGREE -> PASS / FLAGGED / DISAGREE / REVIEW_REQUIRED / True
 8. INVALID INPUT              -> blocked at use_tool, no verdict
 9. OLLAMA UNAVAILABLE         -> blocked at reason, no verdict

All output is deterministic and grounded in structured evidence; the LLM
verdict is never authoritative and provider text is only a non-authoritative
note. No Ollama server is required (stub transport is injected).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_agent.config import OllamaConfig
from ai_agent.orchestrator.fixture_run import execute_fixture
from ai_agent.orchestrator.orchestrator import load_fixture

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"


def _stub_transport(status: int, body: bytes):
    def transport(url, data, headers, timeout):
        return status, body

    return transport


def _ok_body(content: str = "local model reasoning note") -> bytes:
    return json.dumps(
        {
            "model": "llama3",
            "message": {"role": "assistant", "content": content},
            "done": True,
        }
    ).encode("utf-8")


def _load(filename: str) -> dict:
    return load_fixture(FIXTURES_DIR / filename)


def _production_run(fixture: dict) -> dict:
    return execute_fixture(
        fixture,
        config=OllamaConfig(base_url="http://127.0.0.1:11434"),
        transport=_stub_transport(200, _ok_body("reasoning note")),
    )


def _outcome(result: dict):
    stages = (result.get("audit") or {}).get("stages") or {}
    rule_verdict = stages.get("rule_verdict") or {}
    final_verdict = result.get("final_verdict") or {}
    return (
        rule_verdict.get("rule_result"),
        (result.get("llm_reasoning") or {}).get("llm_result"),
        (result.get("verification") or {}).get("agreement"),
        final_verdict.get("final_decision"),
        final_verdict.get("requires_human_review"),
    )


class SafeScenarioTests(unittest.TestCase):
    """1. SAFE: clean permit, fully resolved tags, no overlap."""

    def test_safe_outcome_tuple(self) -> None:
        result = _production_run(_load("safe_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("PASS", "PASS", "AGREE", "PASS", False),
        )


class HotWorkConflictScenarioTests(unittest.TestCase):
    """2. HOT-WORK CONFLICT: overlapping hot work in the same area."""

    def test_hot_work_conflict_outcome_tuple(self) -> None:
        result = _production_run(_load("conflict_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("FLAGGED", "FLAGGED", "AGREE", "FLAGGED_FOR_REVIEW", True),
        )


class IsolationConflictScenarioTests(unittest.TestCase):
    """3. ISOLATION CONFLICT: non-hot-work permit whose live isolation
    overlaps another active permit in the same store."""

    def test_isolation_conflict_outcome_tuple(self) -> None:
        result = _production_run(_load("isolation_conflict_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("FLAGGED", "FLAGGED", "AGREE", "FLAGGED_FOR_REVIEW", True),
        )

    def test_isolated_rule_triggers(self) -> None:
        result = _production_run(_load("isolation_conflict_case.json"))
        rule_verdict = (result["audit"]["stages"].get("rule_verdict") or {})
        self.assertEqual(
            sorted(rule_verdict["rules_triggered"]),
            ["isolation-overlap-time-window", "permit-conflict"],
        )
        self.assertNotIn("hot-work-overlap", rule_verdict["rules_triggered"])
        self.assertEqual(
            rule_verdict["conflicting_permit_ids"], ["MR-0014-ISO"]
        )


class MultipleConflictsScenarioTests(unittest.TestCase):
    """4. MULTIPLE CONFLICTS: hot work overlapping TWO active permits plus
    a live isolation."""

    def test_multiple_conflicts_outcome_tuple(self) -> None:
        result = _production_run(_load("multiple_conflicts_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("FLAGGED", "FLAGGED", "AGREE", "FLAGGED_FOR_REVIEW", True),
        )

    def test_all_three_conflict_rules_triggered(self) -> None:
        result = _production_run(_load("multiple_conflicts_case.json"))
        rule_verdict = (result["audit"]["stages"].get("rule_verdict") or {})
        self.assertEqual(
            sorted(rule_verdict["rules_triggered"]),
            [
                "hot-work-overlap",
                "isolation-overlap-time-window",
                "permit-conflict",
            ],
        )
        self.assertEqual(
            len(rule_verdict["conflicting_permit_ids"]),
            2,
            rule_verdict["conflicting_permit_ids"],
        )


class UnknownTagScenarioTests(unittest.TestCase):
    """5. UNKNOWN TAG: a permit-cited equipment tag resolves nowhere."""

    def test_unknown_tag_outcome_tuple(self) -> None:
        result = _production_run(_load("unknown_tag_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("FLAGGED", "FLAGGED", "AGREE", "FLAGGED_FOR_REVIEW", True),
        )

    def test_unresolved_tag_rule(self) -> None:
        result = _production_run(_load("unknown_tag_case.json"))
        rule_verdict = (result["audit"]["stages"].get("rule_verdict") or {})
        self.assertEqual(rule_verdict["rules_triggered"], ["unresolved-tags"])
        self.assertEqual(rule_verdict["conflicting_permit_ids"], [])


class AmbiguousScenarioTests(unittest.TestCase):
    """6. AMBIGUOUS: conflicting field signals force human review."""

    def test_ambiguous_outcome_tuple(self) -> None:
        result = _production_run(_load("ambiguous_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("FLAGGED", "FLAGGED", "AGREE", "FLAGGED_FOR_REVIEW", True),
        )


class DisagreementScenarioTests(unittest.TestCase):
    """7. LLM/DETERMINISTIC DISAGREEMENT through the production pipeline:
    rules pass (tags resolved, no overlap) while the declared live isolation
    keeps the LLM-side verdict FLAGGED -> DISAGREE / REVIEW_REQUIRED."""

    def test_production_disagreement_outcome_tuple(self) -> None:
        result = _production_run(_load("llm_rule_disagreement_case.json"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(
            _outcome(result),
            ("PASS", "FLAGGED", "DISAGREE", "REVIEW_REQUIRED", True),
        )

    def test_rule_side_truly_passes(self) -> None:
        result = _production_run(_load("llm_rule_disagreement_case.json"))
        rule_verdict = (result["audit"]["stages"].get("rule_verdict") or {})
        self.assertEqual(rule_verdict["rule_result"], "PASS")
        self.assertEqual(
            sorted(rule_verdict["rules_triggered"]),
            ["no-conflict", "tags-resolved"],
        )

    def test_llm_side_flags_active_isolation(self) -> None:
        result = _production_run(_load("llm_rule_disagreement_case.json"))
        self.assertEqual(
            result["llm_reasoning"]["llm_result"],
            "FLAGGED",
        )


class InvalidInputScenarioTests(unittest.TestCase):
    """8. INVALID INPUT: malformed PID (dangling connection) blocks the
    pipeline with no verdict; nothing is ever declared PASS."""

    def test_invalid_input_blocks_with_no_verdict(self) -> None:
        result = _production_run(_load("invalid_input_case.json"))
        self.assertEqual(result.get("failed_stage"), "use_tool")
        self.assertIsNone(result.get("final_verdict"))
        self.assertIsNone((result.get("verification") or {}).get("agreement"))
        self.assertTrue(result["errors"])
        error = result["errors"][0]
        self.assertEqual(error.get("error_type"), "StageFailure")
        self.assertIn(
            "Plant-safety evaluation failed: TopologyError",
            error.get("message", ""),
        )


class OllamaUnavailableScenarioTests(unittest.TestCase):
    """9. OLLAMA UNAVAILABLE: the reason stage cannot reach Ollama (real
    connection refused on an unbound local port) and the run blocks with no
    verdict instead of guessing."""

    def test_ollama_unavailable_blocks_with_no_verdict(self) -> None:
        result = execute_fixture(
            _load("conflict_case.json"),
            config=OllamaConfig(
                base_url="http://127.0.0.1:59977",
                timeout=5,
            ),
        )
        self.assertEqual(result.get("failed_stage"), "reason")
        self.assertIsNone(result.get("final_verdict"))
        self.assertIsNone((result.get("verification") or {}).get("agreement"))
        self.assertTrue(result["errors"])
        error = result["errors"][0]
        self.assertEqual(error.get("error_type"), "ReasoningError")
        self.assertIn("Could not connect to Ollama", error.get("message", ""))

    def test_rule_layer_still_ran_before_block(self) -> None:
        result = execute_fixture(
            _load("conflict_case.json"),
            config=OllamaConfig(
                base_url="http://127.0.0.1:59977",
                timeout=5,
            ),
        )
        stages = (result.get("audit") or {}).get("stages") or {}
        self.assertTrue(stages.get("deterministic_safety_evaluated"))
        self.assertEqual(
            (stages.get("rule_verdict") or {}).get("rule_result"),
            "FLAGGED",
        )


class NewFixtureIntegrityTests(unittest.TestCase):
    """Internal-consistency guarantees for the newly added fixtures: valid
    JSON, matching permit IDs across contract sections, and every equipment
    tag resolvable within the fixture's own PID data (except the one tag the
    UNKNOWN-TAG scenario deliberately leaves unresolved)."""

    NEW_FIXTURES = [
        "isolation_conflict_case.json",
        "multiple_conflicts_case.json",
        "unknown_tag_case.json",
        "llm_rule_disagreement_case.json",
        "invalid_input_case.json",
    ]

    def test_new_fixture_ids_consistent(self) -> None:
        for filename in self.NEW_FIXTURES:
            with self.subTest(fixture=filename):
                fixture = _load(filename)
                permit_id = fixture["task_request"]["permit_id"]
                self.assertEqual(
                    permit_id, fixture["structured_ptw"]["permit_id"]
                )
                if fixture["scenario"] != "invalid-input":
                    self.assertEqual(
                        permit_id, fixture["graph_facts"]["permit_id"]
                    )
                    self.assertEqual(
                        permit_id, fixture["rule_verdict"]["permit_id"]
                    )

    def test_new_fixture_tags_resolve_or_are_deliberate(self) -> None:
        for filename in self.NEW_FIXTURES:
            with self.subTest(fixture=filename):
                fixture = _load(filename)
                symbols = {
                    s["symbol_id"]
                    for s in fixture["structured_pid"].get("symbols", [])
                }
                declared_unresolved = set(
                    (fixture.get("graph_facts") or {}).get(
                        "unresolved_tags", []
                    )
                )
                for tag in fixture["structured_ptw"]["equipment_tags"]:
                    if tag in declared_unresolved:
                        self.assertEqual(
                            filename, "unknown_tag_case.json",
                        )
                    else:
                        self.assertIn(tag, symbols, filename)

    def test_new_fixture_overlap_permits_referenced(self) -> None:
        for filename in self.NEW_FIXTURES:
            with self.subTest(fixture=filename):
                fixture = _load(filename)
                overlap = fixture.get("graph_facts", {}).get("overlap_check")
                if overlap is None or overlap["overlapping_permits"] == []:
                    continue
                conflicting = fixture.get("rule_verdict", {}).get(
                    "conflicting_permit_ids", []
                )
                self.assertEqual(
                    sorted(overlap["overlapping_permits"]),
                    sorted(conflicting),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)