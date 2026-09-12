"""Generate a synthetic PTW-like image for local, offline OCR testing.

SYNTHETIC TEST FIXTURE ONLY

This image is rendered purely for tests of
``ai_agent.vision.ptw_ocr.extract_text_from_image``. It is NOT a real
production document and must NEVER be treated, shipped, or exported as
reference/example data. It renders known text with Pillow so a genuine OCR
pass can be proven against real image bytes with no cloud OCR service.

Usage:
    python scripts/make_synthetic_ptw_image.py --out path/to/output.png
"""

import argparse
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

SYNTHETIC_PTW_LINES = [
    "Permit ID: MR-TEST-001",
    "Work Type: HOT WORK",
    "Scope: DISCHARGE LINE REPLACEMENT",
    "Location: UNIT-7, AREA-03",
    "Start Time: 2026-09-12 08:00",
    "End Time: 2026-09-12 17:00",
    "Issuer: JOHN SMITH",
    "Equipment Tags: P-701, V-702",
    "Isolation Points: ISO-07, ISO-08",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for font_path in (
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if Path(font_path).is_file():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default(size=size)


def render_synthetic_ptw_image(
    dest: Union[str, Path],
    *,
    width: int = 1300,
    height: int = 760,
    font_size: int = 44,
) -> Path:
    """Render known PTW-like text onto a blank image and save it as PNG.

    The service image renders all nine fields ptw_parser field patterns
    expect (Permit ID, Work Type, Scope, Location, Start Time, End Time,
    Issuer, Equipment Tags, Isolation Points). The canvas is sized so every
    line fits: Tesseract must be able to read all of them cleanly.
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    font = _load_font(font_size)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    margin = 60
    line_height = int(font_size * 1.6)
    y = margin
    for line in SYNTHETIC_PTW_LINES:
        draw.text((margin, y), line, fill="black", font=font)
        y += line_height

    draw.rectangle([20, 20, width - 20, height - 20], outline="black", width=3)
    image.save(dest_path, format="PNG")
    return dest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="synthetic_ptw_test_image.png",
        help="where to write the generated PNG",
    )
    args = parser.parse_args()
    path = render_synthetic_ptw_image(args.out)
    print(f"wrote synthetic PTW test image: {path}")


if __name__ == "__main__":
    main()