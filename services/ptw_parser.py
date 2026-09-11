def parse_ptw(text: str) -> dict:
    """
    Convert extracted PTW text into a basic structured format.
    """

    if not text.strip():
        raise ValueError("Empty document text")

    structured_ptw = {
        "permit_type": None,
        "location": None,
        "work_description": None,
        "hazards": [],
        "ppe_required": [],
        "raw_text": text
    }

    text_lower = text.lower()

    # Basic permit type detection
    if "hot work" in text_lower:
        structured_ptw["permit_type"] = "HOT_WORK"

    elif "cold work" in text_lower:
        structured_ptw["permit_type"] = "COLD_WORK"

    elif "confined space" in text_lower:
        structured_ptw["permit_type"] = "CONFINED_SPACE"

    # Basic hazard detection
    if "fire" in text_lower:
        structured_ptw["hazards"].append("FIRE")

    if "gas" in text_lower:
        structured_ptw["hazards"].append("GAS")

    if "electric" in text_lower:
        structured_ptw["hazards"].append("ELECTRICAL")

    if "height" in text_lower:
        structured_ptw["hazards"].append("WORK_AT_HEIGHT")

    # Basic PPE detection
    if "helmet" in text_lower:
        structured_ptw["ppe_required"].append("HELMET")

    if "gloves" in text_lower:
        structured_ptw["ppe_required"].append("GLOVES")

    if "safety shoes" in text_lower:
        structured_ptw["ppe_required"].append("SAFETY_SHOES")

    return structured_ptw