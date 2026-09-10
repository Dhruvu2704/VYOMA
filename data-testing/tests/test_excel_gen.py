from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "generators")
)

from excel_gen import generate_excel


def test_generate_excel(tmp_path):
    rule_verdicts = [
        {
            "permit_id": "PTW-2026-014",
            "conflicting_permit_ids": ["PTW-2026-009"],
            "rules_triggered": ["ISOLATION_OVERLAP_TIME_WINDOW"],
            "rule_result": "FLAGGED",
            "explanation": (
                "V-101 isolation overlaps with another permit "
                "during the same time window."
            ),
            "confidence": "HIGH",
        },
        {
            "permit_id": "PTW-2026-001",
            "conflicting_permit_ids": [],
            "rules_triggered": [],
            "rule_result": "PASS",
            "explanation": "No conflicting permit was detected.",
            "confidence": "HIGH",
        },
    ]

    result = generate_excel(rule_verdicts, tmp_path)

    output_file = Path(result["path"])

    assert result["type"] == "EXCEL_CONFLICT_MATRIX"
    assert output_file.exists()
    assert output_file.name == "permit_conflict_matrix.xlsx"