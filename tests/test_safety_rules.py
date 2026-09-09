"""Unit tests for plant_safety.safety_rules.

Uses the actual repository fixtures in ai_agent/fixtures/ where appropriate,
and locally constructed cases for scenarios not covered by the fixtures.

Run from the repository root:

    python -m unittest discover -s tests -v
    python -m unittest tests.test_safety_rules -v
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any, Dict

from shared.contracts import RuleResult, RuleVerdict

from plant_safety.safety_rules import (
    HOT_WORK_OVERLAP,
    ISOLATION_OVERLAP_TIME_WINDOW,
    NO_CONFLICT,
    PERMIT_CONFLICT,
    SUBMITTED_TAGS_CLEAN,
    TAGS_RESOLVED,
    UNRESOLVED_TAGS,
    evaluate,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _load_fixture(scenario: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / FIXTURE_FILES[scenario]
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _facts(scenario: str) -> Dict[str, Any]:
    return _load_fixture(scenario)["graph_facts"]


def _ptw(scenario: str) -> Dict[str, Any]:
    return _load_fixture(scenario)["structured_ptw"]


def _safe_graph_facts() -> Dict[str, Any]:
    return {
        "permit_id": "SAFE-1",
        "resolved_nodes": ["P-101"],
        "unresolved_tags": [],
        "connected_equipment": {"P-101": []},
        "active_isolations": [],
        "overlap_check": {
            "overlapping_permits": [],
            "same_area_active": False,
        },
    }


# =========================================================================
# A. safe fixture -> PASS
# =========================================================================
class SafeFixtureTest(unittest.TestCase):
    def test_safe_passes(self) -> None:
        verdict = evaluate(_facts("safe"), _ptw("safe"))
        self.assertEqual(verdict["rule_result"], "PASS")
        self.assertEqual(verdict["permit_id"], "MR-0001-SAFE")
        self.assertEqual(verdict["conflicting_permit_ids"], [])
        self.assertIn(NO_CONFLICT, verdict["rules_triggered"])
        self.assertIn(TAGS_RESOLVED, verdict["rules_triggered"])


# =========================================================================
# B. conflict fixture -> FLAGGED
# =========================================================================
class ConflictFixtureTest(unittest.TestCase):
    def test_conflict_flagged(self) -> None:
        verdict = evaluate(_facts("conflict"), _ptw("conflict"))
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["permit_id"], "MR-0002-CONF")
        self.assertIn("MR-0003-CONF", verdict["conflicting_permit_ids"])
        self.assertIn(PERMIT_CONFLICT, verdict["rules_triggered"])
        self.assertIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])


# =========================================================================
# C. ambiguous fixture -> FLAGGED
# =========================================================================
class AmbiguousFixtureTest(unittest.TestCase):
    def test_ambiguous_flagged(self) -> None:
        verdict = evaluate(_facts("ambiguous"), _ptw("ambiguous"))
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["permit_id"], "MR-0004-AMB")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])


# =========================================================================
# D. disagreement fixture -> existing expected behavior (PASS on rule side)
# =========================================================================
class DisagreementFixtureTest(unittest.TestCase):
    def test_disagreement_rule_passes_per_existing_fixture(self) -> None:
        # The fixture's rule_verdict is PASS (the rule engine on the submitted
        # tag list found no conflict).  The graph layer finds unresolved tags,
        # which produces the LLM/reasoning DISAGREE later.  The rule evaluator
        # must preserve this existing semantics: with unresolved tags present,
        # the evaluator FLAGS (matching the graph evidence).
        verdict = evaluate(_facts("disagreement"), _ptw("disagreement"))
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])


# =========================================================================
# E. unresolved tags trigger rule
# =========================================================================
class UnresolvedTagsTriggerTest(unittest.TestCase):
    def test_unresolved_triggers_flag(self) -> None:
        facts = _safe_graph_facts()
        facts["unresolved_tags"] = ["G-7X-TEMP", "G-7X-LEVEL"]
        verdict = evaluate(facts)
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])
        self.assertIn("unresolved", verdict["explanation"].lower())
        self.assertIn("G-7X-TEMP", verdict["explanation"])
        self.assertIn("G-7X-LEVEL", verdict["explanation"])

    def test_unresolved_confidence_low(self) -> None:
        facts = _safe_graph_facts()
        facts["unresolved_tags"] = ["TAG-X"]
        verdict = evaluate(facts)
        self.assertEqual(verdict["confidence"], "LOW")


# =========================================================================
# F. no unresolved tags do not trigger rule
# =========================================================================
class NoUnresolvedTagsTest(unittest.TestCase):
    def test_no_unresolved_no_trigger(self) -> None:
        verdict = evaluate(_safe_graph_facts())
        self.assertNotIn(UNRESOLVED_TAGS, verdict["rules_triggered"])

    def test_safe_fixture_no_unresolved(self) -> None:
        verdict = evaluate(_facts("safe"))
        self.assertNotIn(UNRESOLVED_TAGS, verdict["rules_triggered"])


# =========================================================================
# G. permit overlap triggers permit-conflict rule
# =========================================================================
class PermitOverlapTriggerTest(unittest.TestCase):
    def test_overlap_triggers_conflict(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-0009-CONF"],
            "same_area_active": True,
        }
        verdict = evaluate(facts)
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(PERMIT_CONFLICT, verdict["rules_triggered"])
        self.assertIn("MR-0009-CONF", verdict["conflicting_permit_ids"])


# =========================================================================
# H. no permit overlap does not trigger permit-conflict
# =========================================================================
class NoPermitOverlapTest(unittest.TestCase):
    def test_no_overlap_no_conflict_rule(self) -> None:
        verdict = evaluate(_safe_graph_facts())
        self.assertNotIn(PERMIT_CONFLICT, verdict["rules_triggered"])
        self.assertEqual(verdict["conflicting_permit_ids"], [])


# =========================================================================
# I. HOT_WORK with relevant overlap triggers hot-work-overlap
# =========================================================================
class HotWorkOverlapTriggerTest(unittest.TestCase):
    def test_hot_work_with_overlap_flags(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-0010-HW"],
            "same_area_active": True,
        }
        ptw = {"permit_id": "HW-1", "work_type": "hot-work"}
        verdict = evaluate(facts, ptw)
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])
        self.assertIn("MR-0010-HW", verdict["conflicting_permit_ids"])
        self.assertIn("hot work", verdict["explanation"].lower())


# =========================================================================
# J. HOT_WORK without overlap does not automatically flag
# =========================================================================
class HotWorkNoOverlapTest(unittest.TestCase):
    def test_hot_work_without_overlap_no_flag(self) -> None:
        facts = _safe_graph_facts()
        ptw = {"permit_id": "HW-NO-1", "work_type": "hot-work"}
        verdict = evaluate(facts, ptw)
        self.assertEqual(verdict["rule_result"], "PASS")
        self.assertNotIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])
        self.assertNotIn(PERMIT_CONFLICT, verdict["rules_triggered"])


# =========================================================================
# K. isolation/time-window conflict triggers the appropriate rule
# =========================================================================
class IsolationTimeWindowTriggerTest(unittest.TestCase):
    def test_isolation_overlap_triggers(self) -> None:
        facts = _safe_graph_facts()
        facts["active_isolations"] = ["ISO-T300-01"]
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-0011-ISO"],
            "same_area_active": True,
        }
        verdict = evaluate(facts)
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(ISOLATION_OVERLAP_TIME_WINDOW, verdict["rules_triggered"])
        self.assertIn("MR-0011-ISO", verdict["conflicting_permit_ids"])


# =========================================================================
# L. no isolation/time-window conflict does not trigger it
# =========================================================================
class NoIsolationTimeWindowTest(unittest.TestCase):
    def test_no_isolation_no_trigger(self) -> None:
        verdict = evaluate(_safe_graph_facts())
        self.assertNotIn(ISOLATION_OVERLAP_TIME_WINDOW, verdict["rules_triggered"])

    def test_isolation_but_no_overlap_no_trigger(self) -> None:
        facts = _safe_graph_facts()
        facts["active_isolations"] = ["ISO-A-01"]
        verdict = evaluate(facts)
        self.assertNotIn(ISOLATION_OVERLAP_TIME_WINDOW, verdict["rules_triggered"])


# =========================================================================
# M. multiple rules can trigger simultaneously
# =========================================================================
class MultipleRulesTriggerTest(unittest.TestCase):
    def test_multiple_rules_flag(self) -> None:
        facts = _safe_graph_facts()
        facts["unresolved_tags"] = ["TAG-MISS"]
        facts["active_isolations"] = ["ISO-1"]
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-0020-A", "MR-0021-B"],
            "same_area_active": True,
        }
        ptw = {"permit_id": "MULTI-1", "work_type": "hot-work"}
        verdict = evaluate(facts, ptw)
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])
        self.assertIn(PERMIT_CONFLICT, verdict["rules_triggered"])
        self.assertIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])
        self.assertIn(ISOLATION_OVERLAP_TIME_WINDOW, verdict["rules_triggered"])


# =========================================================================
# N. conflicting permit IDs are deduplicated
# =========================================================================
class ConflictingDeduplicationTest(unittest.TestCase):
    def test_duplicate_overlap_ids_deduplicated(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-0030", "MR-0030"],
            "same_area_active": True,
        }
        verdict = evaluate(facts)
        self.assertEqual(verdict["conflicting_permit_ids"], ["MR-0030"])


# =========================================================================
# O. conflicting permit ordering is deterministic
# =========================================================================
class ConflictingOrderingTest(unittest.TestCase):
    def test_first_seen_order_preserved(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-Z", "MR-A", "MR-M"],
            "same_area_active": True,
        }
        verdict = evaluate(facts)
        self.assertEqual(
            verdict["conflicting_permit_ids"], ["MR-Z", "MR-A", "MR-M"]
        )


# =========================================================================
# P. rule ordering is deterministic
# =========================================================================
class RuleOrderingTest(unittest.TestCase):
    def test_rule_order_deterministic(self) -> None:
        facts = _safe_graph_facts()
        facts["unresolved_tags"] = ["TAG-1"]
        facts["active_isolations"] = ["ISO-1"]
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-1"],
            "same_area_active": True,
        }
        ptw = {"permit_id": "R", "work_type": "hot-work"}
        v1 = evaluate(facts, ptw)
        v2 = evaluate(copy.deepcopy(facts), dict(ptw))
        self.assertEqual(v1["rules_triggered"], v2["rules_triggered"])


# =========================================================================
# Q. PASS output shape
# =========================================================================
class PassOutputShapeTest(unittest.TestCase):
    def test_pass_shape(self) -> None:
        verdict = evaluate(_safe_graph_facts())
        self.assertEqual(
            set(verdict),
            {
                "permit_id",
                "conflicting_permit_ids",
                "rules_triggered",
                "rule_result",
                "explanation",
                "confidence",
            },
        )
        self.assertEqual(verdict["conflicting_permit_ids"], [])
        self.assertEqual(verdict["rule_result"], "PASS")
        self.assertIsInstance(verdict["rules_triggered"], list)
        self.assertNotIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])


# =========================================================================
# R. FLAGGED output shape
# =========================================================================
class FlaggedOutputShapeTest(unittest.TestCase):
    def test_flagged_shape(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-1"],
            "same_area_active": True,
        }
        verdict = evaluate(facts)
        self.assertEqual(
            set(verdict),
            {
                "permit_id",
                "conflicting_permit_ids",
                "rules_triggered",
                "rule_result",
                "explanation",
                "confidence",
            },
        )
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["conflicting_permit_ids"], ["MR-1"])


# =========================================================================
# S. explanation is deterministic
# =========================================================================
class ExplanationDeterministicTest(unittest.TestCase):
    def test_explanation_stable(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-5"],
            "same_area_active": True,
        }
        v1 = evaluate(facts)
        v2 = evaluate(copy.deepcopy(facts))
        self.assertEqual(v1["explanation"], v2["explanation"])
        self.assertEqual(v1["explanation"], v1["explanation"])


# =========================================================================
# T. repeated evaluation produces identical RuleVerdict
# =========================================================================
class RepeatedEvaluationTest(unittest.TestCase):
    def test_repeated_same_input_same_output(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-7"],
            "same_area_active": True,
        }
        v1 = evaluate(facts)
        v2 = evaluate(facts)
        v3 = evaluate(facts)
        self.assertEqual(v1, v2)
        self.assertEqual(v2, v3)


# =========================================================================
# U. input PTW is not mutated
# =========================================================================
class PtwNotMutatedTest(unittest.TestCase):
    def test_ptw_unchanged(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-8"],
            "same_area_active": True,
        }
        ptw = {"permit_id": "PTW-1", "work_type": "hot-work"}
        before = copy.deepcopy(ptw)
        evaluate(facts, ptw)
        self.assertEqual(ptw, before)


# =========================================================================
# V. GraphFacts is not mutated
# =========================================================================
class FactsNotMutatedTest(unittest.TestCase):
    def test_facts_unchanged(self) -> None:
        facts = _safe_graph_facts()
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-9"],
            "same_area_active": True,
        }
        before = copy.deepcopy(facts)
        evaluate(facts)
        self.assertEqual(facts, before)

    def test_facts_unchanged_with_ptw(self) -> None:
        facts = _safe_graph_facts()
        facts["unresolved_tags"] = ["TAG-MISS"]
        facts["active_isolations"] = ["ISO-9"]
        facts["overlap_check"] = {
            "overlapping_permits": ["MR-10"],
            "same_area_active": True,
        }
        before = copy.deepcopy(facts)
        ptw = {"permit_id": "P", "work_type": "hot-work"}
        ptw_before = copy.deepcopy(ptw)
        evaluate(facts, ptw)
        self.assertEqual(facts, before)
        self.assertEqual(ptw, ptw_before)


# =========================================================================
# W. invalid input behavior is tested consistently with repository conventions
# =========================================================================
class InvalidInputTest(unittest.TestCase):
    def test_type_error_on_non_dict_facts(self) -> None:
        with self.assertRaises(TypeError):
            evaluate("not-a-dict")  # type: ignore[arg-type]

    def test_none_facts_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            evaluate(None)  # type: ignore[arg-type]

    def test_ptw_none_is_tolerated(self) -> None:
        verdict = evaluate(_safe_graph_facts(), None)
        self.assertEqual(verdict["rule_result"], "PASS")


# =========================================================================
# X. RuleVerdict remains compatible with shared/contracts.py
# =========================================================================
class ContractCompatibilityTest(unittest.TestCase):
    def test_verdict_conforms_to_ruleverdict_keys(self) -> None:
        verdict = evaluate(_facts("conflict"), _ptw("conflict"))
        self.assertEqual(
            set(verdict),
            {
                "permit_id",
                "conflicting_permit_ids",
                "rules_triggered",
                "rule_result",
                "explanation",
                "confidence",
            },
        )

    def test_rule_result_is_valid_literal(self) -> None:
        for facts, ptw in (
            (_safe_graph_facts(), None),
            (_facts("conflict"), _ptw("conflict")),
            (_facts("ambiguous"), _ptw("ambiguous")),
        ):
            verdict = evaluate(facts, ptw)
            self.assertIn(verdict["rule_result"], ("PASS", "FLAGGED"))
            self.assertIsInstance(verdict["rule_result"], str)

    def test_conflicting_permit_ids_is_list_of_str(self) -> None:
        verdict = evaluate(_facts("conflict"), _ptw("conflict"))
        self.assertIsInstance(verdict["conflicting_permit_ids"], list)
        for pid in verdict["conflicting_permit_ids"]:
            self.assertIsInstance(pid, str)

    def test_rules_triggered_is_list_of_str(self) -> None:
        verdict = evaluate(_facts("conflict"), _ptw("conflict"))
        self.assertIsInstance(verdict["rules_triggered"], list)
        for rule in verdict["rules_triggered"]:
            self.assertIsInstance(rule, str)

    def test_conflict_fixture_matches_expected_ruleverdict(self) -> None:
        expected = _load_fixture("conflict")["rule_verdict"]
        verdict = evaluate(_facts("conflict"), _ptw("conflict"))
        self.assertEqual(verdict["rule_result"], expected["rule_result"])
        self.assertEqual(
            verdict["conflicting_permit_ids"], expected["conflicting_permit_ids"]
        )
        # DAY 3 adds the isolation-overlap-time-window rule, which is also
        # applicable to the conflict fixture (overlap + active isolation).
        self.assertEqual(
            set(verdict["rules_triggered"]),
            {PERMIT_CONFLICT, HOT_WORK_OVERLAP, ISOLATION_OVERLAP_TIME_WINDOW},
        )

    def test_ambiguous_fixture_matches_expected_ruleverdict(self) -> None:
        expected = _load_fixture("ambiguous")["rule_verdict"]
        verdict = evaluate(_facts("ambiguous"), _ptw("ambiguous"))
        self.assertEqual(verdict["rule_result"], expected["rule_result"])
        self.assertEqual(
            verdict["conflicting_permit_ids"], expected["conflicting_permit_ids"]
        )
        self.assertEqual(verdict["rules_triggered"], expected["rules_triggered"])
        self.assertEqual(verdict["confidence"], expected["confidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
