from pathlib import Path

from data_testing.generators.word_gen import generate_word


def test_generate_word(tmp_path):
    final_verdict = {
        "permit_id": "PTW-2026-014",
        "rule_result": "FLAGGED",
        "llm_result": "FLAGGED",
        "agreement": "AGREE",
        "final_decision": "FLAGGED_FOR_REVIEW",
        "explanation": (
            "Valve V-101 isolation overlaps with another permit "
            "during the same time window."
        ),
        "requires_human_review": True,
        "generated_at": "2026-09-05T09:43:00Z",
        "audit_ref": "AUD-PTW-2026-014",
    }

    result = generate_word(final_verdict, tmp_path)

    output_file = Path(result["path"])

    assert result["type"] == "WORD_MEMO"
    assert output_file.exists()
    assert output_file.name == "PTW-2026-014_memo.docx"
