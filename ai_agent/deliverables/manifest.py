"""Deliverable manifest generator for KAVACH safety reviews.

Adapted from Role 6 data-testing/generators/manifest_gen.py.
Aggregates Word, Excel, and annotated P&ID PDF outputs into one manifest.
"""

from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_agent.deliverables.excel_matrix import generate_excel
from ai_agent.deliverables.pdf_annotator import annotate_pdf
from ai_agent.deliverables.word_memo import generate_word


def generate_deliverable_manifest(
    final_verdict: Mapping[str, Any],
    rule_verdict: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    pid_file: str | Path,
    output_dir: str | Path = "outputs",
) -> dict[str, Any]:
    """Generate the complete deliverable manifest for a permit safety review.

    Invokes the Word memo generator, Excel conflict matrix generator, and
    P&ID PDF annotator, aggregating their outputs into a single manifest.

    Args:
        final_verdict: FinalVerdict-shaped dictionary. Must include
            permit_id.
        rule_verdict: Single or sequence of rule-verdict mappings.
        pid_file: Path to the source P&ID PDF.
        output_dir: Directory to write the deliverables into.

    Returns:
        A dictionary with permit_id, generated_at, audit_ref, and the
        aggregated deliverables list.
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