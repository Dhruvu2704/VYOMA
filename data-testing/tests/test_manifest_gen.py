from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "generators")
)

from manifest_gen import generate_deliverable_manifest


def test_generate_deliverable_manifest(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    pid_file = project_root / "sample-data" / "pid-unit-01.pdf"

    final_verdict = {
        "permit_id": "PTW-2026-014",
        "rule_result": "FLAGGED",
        "llm_result": "FLAGGED",
        "agreement": "AGREE",
        "final_decision": "FLAGGED_FOR_REVIEW",
        "explanation": (
            "Hot work near L-101 conflicts with the temporary "
            "reopening of V-101 isolation."
        ),
        "requires_human_review": True,
        "generated_at": "2026-09-05T09:43:00Z",
        "audit_ref": "AUD-PTW-2026-014",
    }

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
        }
    ]

    manifest = generate_deliverable_manifest(
        final_verdict=final_verdict,
        rule_verdict=rule_verdicts,
        pid_file=pid_file,
        output_dir=tmp_path,
    )

    assert manifest["permit_id"] == "PTW-2026-014"
    assert manifest["generated_at"] == "2026-09-05T09:43:00Z"
    assert manifest["audit_ref"] == "AUD-PTW-2026-014"

    deliverables = manifest["deliverables"]
    assert len(deliverables) == 3

    types = [item["type"] for item in deliverables]
    assert "WORD_MEMO" in types
    assert "EXCEL_CONFLICT_MATRIX" in types
    assert "ANNOTATED_PDF" in types

    for item in deliverables:
        assert Path(item["path"]).exists()
