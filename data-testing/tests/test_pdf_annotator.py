from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "generators")
)

from pdf_annotator import annotate_pdf


def test_annotate_pdf(tmp_path):
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

    result = annotate_pdf(
        pid_file,
        final_verdict,
        tmp_path,
    )

    output_file = Path(result["path"])

    assert result["type"] == "ANNOTATED_PDF"
    assert output_file.exists()
    assert output_file.name == "PTW-2026-014_annotated_pid.pdf"
    assert "L-101" in result["highlighted_tags"]
    assert "V-101" in result["highlighted_tags"]