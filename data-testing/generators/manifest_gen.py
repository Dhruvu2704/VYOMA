from pathlib import Path
from typing import Any, Mapping, Sequence

from excel_gen import generate_excel
from pdf_annotator import annotate_pdf
from word_gen import generate_word


def generate_deliverable_manifest(
    final_verdict: Mapping[str, Any],
    rule_verdict: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    pid_file: str | Path,
    output_dir: str | Path = "outputs",
) -> dict[str, Any]:
    """
    Generate the complete deliverable manifest for a permit safety review.

    Invokes the Word memo generator, Excel conflict matrix generator, and
    P&ID PDF annotator, aggregating their outputs into a single manifest dict.
    """

    word_result = generate_word(final_verdict, output_dir=output_dir)
    excel_result = generate_excel(rule_verdict, output_dir=output_dir)
    pdf_result = annotate_pdf(pid_file, final_verdict, output_dir=output_dir)

    permit_id = final_verdict["permit_id"]
    generated_at = final_verdict.get("generated_at", "")
    audit_ref = final_verdict.get("audit_ref")

    return {
        "permit_id": permit_id,
        "generated_at": generated_at,
        "audit_ref": audit_ref,
        "deliverables": [
            word_result,
            excel_result,
            pdf_result,
        ],
    }
