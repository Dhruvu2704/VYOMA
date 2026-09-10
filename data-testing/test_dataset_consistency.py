import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA = ROOT / "sample-data"


def load_json(filename):
    with open(SAMPLE_DATA / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def test_ptw_equipment_consistency():
    equipment_data = load_json("equipment.json")
    ptw_data = load_json("ptws.json")

    equipment_tags = {
        item["tag"]
        for item in equipment_data["equipment"]
    }

    for permit in ptw_data["ptws"]:
        for tag in permit["equipment_tags"]:
            assert tag in equipment_tags, (
                f"{tag} from {permit['permit_id']} "
                "does not exist in equipment.json"
            )


def test_isolation_points_exist_in_equipment():
    equipment_data = load_json("equipment.json")
    ptw_data = load_json("ptws.json")

    equipment_by_tag = {
        item["tag"]: item
        for item in equipment_data["equipment"]
    }

    for permit in ptw_data["ptws"]:
        for tag in permit["isolation_points"]:
            assert tag in equipment_by_tag, (
                f"{tag} from {permit['permit_id']} "
                "does not exist in equipment.json"
            )

            assert equipment_by_tag[tag]["isolation_capable"] is True, (
                f"{tag} is used as an isolation point but is not "
                "marked isolation_capable"
            )


def test_pipes_reference_existing_equipment():
    equipment_data = load_json("equipment.json")
    pipes_data = load_json("pipes.json")

    equipment_tags = {
        item["tag"]
        for item in equipment_data["equipment"]
    }

    for connection in pipes_data["connections"]:
        assert connection["source"] in equipment_tags
        assert connection["target"] in equipment_tags
        assert connection["line_ref"] in equipment_tags


def test_pid_matches_equipment_and_pipes():
    equipment_data = load_json("equipment.json")
    pipes_data = load_json("pipes.json")

    equipment_tags = {
        item["tag"]
        for item in equipment_data["equipment"]
    }

    expected_connections = {
        (
            connection["source"],
            connection["target"],
            connection["line_ref"],
        )
        for connection in pipes_data["connections"]
    }

    pdf_path = SAMPLE_DATA / "pid-unit-01.pdf"

    document = fitz.open(pdf_path)

    pdf_text = "\n".join(
        page.get_text()
        for page in document
    )

    document.close()

    for tag in equipment_tags:
        assert tag in pdf_text, (
            f"Equipment tag {tag} is missing from the P&ID"
        )

    for source, target, line_ref in expected_connections:
        assert source in pdf_text
        assert target in pdf_text
        assert line_ref in pdf_text


def test_permit_register_matches_ptws():
    ptw_data = load_json("ptws.json")
    register_data = load_json("permit-register.json")

    ptw_by_id = {
        permit["permit_id"]: permit
        for permit in ptw_data["ptws"]
    }

    for registered_permit in register_data["active_permits"]:
        permit_id = registered_permit["permit_id"]

        assert permit_id in ptw_by_id, (
            f"{permit_id} in permit-register.json "
            "does not exist in ptws.json"
        )

        ptw = ptw_by_id[permit_id]

        assert registered_permit["start_time"] == ptw["start_time"]
        assert registered_permit["end_time"] == ptw["end_time"]


def test_ground_truth_references_existing_ptws():
    ptw_data = load_json("ptws.json")
    ground_truth = load_json("ground-truth.json")

    ptw_ids = {
        permit["permit_id"]
        for permit in ptw_data["ptws"]
    }

    for scenario in ground_truth["scenarios"]:
        for permit_id in scenario["permit_ids"]:
            assert permit_id in ptw_ids, (
                f"{permit_id} from {scenario['scenario_id']} "
                "does not exist in ptws.json"
            )


def test_ground_truth_has_expected_scenario_coverage():
    ground_truth = load_json("ground-truth.json")

    scenarios = ground_truth["scenarios"]

    expected_decisions = {
        scenario["expected_final_decision"]
        for scenario in scenarios
    }

    assert "PASS" in expected_decisions
    assert "FLAGGED_FOR_REVIEW" in expected_decisions
    assert "REVIEW_REQUIRED" in expected_decisions

    assert len(scenarios) >= 5


def test_planted_conflicts_have_isolation_overlap():
    ptw_data = load_json("ptws.json")
    ground_truth = load_json("ground-truth.json")

    ptws = {
        permit["permit_id"]: permit
        for permit in ptw_data["ptws"]
    }

    conflict_scenarios = [
        scenario
        for scenario in ground_truth["scenarios"]
        if scenario["expected_final_decision"] == "FLAGGED_FOR_REVIEW"
    ]

    for scenario in conflict_scenarios:
        permit_a = ptws[scenario["permit_ids"][0]]
        permit_b = ptws[scenario["permit_ids"][1]]

        shared_isolations = (
            set(permit_a["isolation_points"])
            & set(permit_b["isolation_points"])
        )

        assert shared_isolations, (
            f"{scenario['scenario_id']} has no shared "
            "isolation point"
        )

        assert (
            permit_a["start_time"] < permit_b["end_time"]
            and permit_b["start_time"] < permit_a["end_time"]
        ), (
            "{scenario['scenario_id']} does not have "
            "an overlapping time window"
        )