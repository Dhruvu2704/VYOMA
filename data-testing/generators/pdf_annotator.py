from pathlib import Path
from typing import Any, Mapping
import re

import fitz


def annotate_pdf(
    pid_file: str | Path,
    final_verdict: Mapping[str, Any],
    output_dir: str | Path = "outputs",
) -> dict[str, str]:
    """
    Annotate the original P&ID PDF using information from FinalVerdict.

    Equipment/isolation tags mentioned in the verdict explanation are
    highlighted on the original P&ID so the evidence can be reviewed
    visually.
    """

    pid_path = Path(pid_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    permit_id = final_verdict["permit_id"]
    output_file = output_path / f"{permit_id}_annotated_pid.pdf"

    document = fitz.open(pid_path)

    explanation = str(final_verdict.get("explanation", ""))

    # Find refinery-style equipment/isolation tags such as V-101, L-101.
    tags = sorted(set(re.findall(r"\b[A-Z]{1,4}-\d{3}\b", explanation)))

    highlighted_tags = []

    for page in document:
        for tag in tags:
            rectangles = page.search_for(tag)

            for rectangle in rectangles:
                annotation = page.add_highlight_annot(rectangle)
                annotation.update()
                highlighted_tags.append(tag)

    document.save(output_file)
    document.close()

    return {
        "type": "ANNOTATED_PDF",
        "path": str(output_file),
        "permit_id": permit_id,
        "highlighted_tags": ", ".join(sorted(set(highlighted_tags))),
    }