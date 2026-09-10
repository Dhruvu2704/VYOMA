import json
from pathlib import Path
import sys

# Ensure generators module is on sys.path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "generators")
)

from manifest_gen import generate_deliverable_manifest
from ai_agent.orchestrator.orchestrator import AgentOrchestrator

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA = ROOT / "sample-data"


def load_json(filename: str) -> dict:
    with open(SAMPLE_DATA / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def _build_fixture_for_scenario(scenario: dict, ptw_map: dict) -> dict:
    permit_ids = scenario["permit_ids"]
    primary_id = permit_ids[0]
    primary_ptw = ptw_map[primary_id]
    conflicting_ids = permit_ids[1:]

    rules_triggered = []
    if scenario.get("expected_conflict_rule"):
        rules_triggered.append(scenario["expected_conflict_rule"])

    explanation = scenario["description"]
    if conflicting_ids:
        explanation += f" Conflicting permits: {', '.join(conflicting_ids)}."

    # Ambiguous scenarios occur when the rule result is PASS (no explicit rule conflict)
    # but unresolved tags in the graph force reasoning to flag and require human review (REVIEW_REQUIRED).
    rule_result = scenario["expected_rule_result"]
    if scenario["expected_final_decision"] == "REVIEW_REQUIRED":
        rule_result = "PASS"

    return {
        "scenario": scenario["scenario_id"],
        "description": scenario["description"],
        "task_request": {
            "permit_id": primary_id,
            "task_type": "ptw_review",
            "document_refs": [f"sample-data:{primary_id}"],
            "context": {"source": "ground-truth-integration"},
        },
        "structured_ptw": {
            "permit_id": primary_id,
            "work_type": primary_ptw.get("work_type", "maintenance"),
            "scope": primary_ptw.get("description", scenario["description"]),
            "location": [primary_ptw.get("location", "Unit-01")],
            "start_time": primary_ptw.get("start_time", "2026-09-05T08:00:00Z"),
            "end_time": primary_ptw.get("end_time", "2026-09-05T17:00:00Z"),
            "issuer": primary_ptw.get("issuer", "Plant Safety Officer"),
            "raw_document_ref": f"sample-data:{primary_id}",
            "equipment_tags": primary_ptw.get("equipment_tags", []),
            "isolation_points": primary_ptw.get("isolation_points", []),
            "field_confidence": {
                "permit_id": 1.0,
                "work_type": 0.95,
                "scope": 0.90,
            },
            "low_confidence_fields": [],
        },
        "structured_pid": {
            "pid_id": "PID-UNIT-01",
            "source": "sample-data/pid-unit-01.pdf",
            "equipment_tags": primary_ptw.get("equipment_tags", []),
            "symbols": [],
            "connections": [],
            "unresolved_symbols": [],
            "field_confidence": {"equipment_tags": 0.95},
            "low_confidence_fields": [],
        },
        "graph_facts": {
            "permit_id": primary_id,
            "resolved_nodes": primary_ptw.get("equipment_tags", []),
            "unresolved_tags": ["G-101"] if scenario["expected_final_decision"] == "REVIEW_REQUIRED" else [],
            "connected_equipment": {},
            "active_isolations": primary_ptw.get("isolation_points", []),
            "overlap_check": {
                "overlapping_permits": conflicting_ids,
            },
        },
        "rule_verdict": {
            "permit_id": primary_id,
            "conflicting_permit_ids": conflicting_ids,
            "rules_triggered": rules_triggered,
            "rule_result": rule_result,
            "explanation": explanation,
            "confidence": scenario.get("confidence", "HIGH"),
        },
    }


def test_ground_truth_scenarios_pipeline_and_deliverables(tmp_path):
    ground_truth = load_json("ground-truth.json")
    ptw_data = load_json("ptws.json")

    ptw_map = {
        permit["permit_id"]: permit
        for permit in ptw_data["ptws"]
    }

    orchestrator = AgentOrchestrator()
    pid_file = SAMPLE_DATA / "pid-unit-01.pdf"

    for scenario in ground_truth["scenarios"]:
        scenario_id = scenario["scenario_id"]
        fixture = _build_fixture_for_scenario(scenario, ptw_map)

        result = orchestrator.run(fixture)
        final_verdict = result["final_verdict"]
        rule_verdict = fixture["rule_verdict"]

        assert final_verdict["final_decision"] == scenario["expected_final_decision"], (
            f"Scenario {scenario_id} expected decision {scenario['expected_final_decision']}, "
            f"got {final_verdict['final_decision']}"
        )

        manifest = generate_deliverable_manifest(
            final_verdict=final_verdict,
            rule_verdict=rule_verdict,
            pid_file=pid_file,
            output_dir=tmp_path / scenario_id,
        )

        assert manifest["permit_id"] == final_verdict["permit_id"]
        assert manifest["audit_ref"] == final_verdict["audit_ref"]
        assert len(manifest["deliverables"]) == 3

        for item in manifest["deliverables"]:
            assert Path(item["path"]).exists(), f"Missing file for {item['type']} in {scenario_id}"
