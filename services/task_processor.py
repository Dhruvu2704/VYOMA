from pathlib import Path

from services.pdf_processor import extract_text_from_pdf
from services.ptw_parser import parse_ptw


def process_document(file_path: str) -> dict:
    """
    Process an uploaded document and return structured PTW data.
    """

    # Check whether the file exists
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError("Uploaded file not found")

    # Extract text from PDF
    extracted_text = extract_text_from_pdf(str(path))

    if not extracted_text.strip():
        raise ValueError("No readable text found in PDF")

    # Convert extracted text into structured PTW
    structured_ptw = parse_ptw(extracted_text)

    # Return the structured result
    return structured_ptw