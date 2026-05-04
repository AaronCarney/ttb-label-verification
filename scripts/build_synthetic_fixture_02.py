"""Deterministic synthetic fixture-02 (STONE'S THROW BOURBON). Mirrors E3-T5 shape.

200x200 white PNG with embedded "STONE'S THROW BOURBON" text + EXIF DPI=300.
Used by E4 orchestrator brand-disambig recordings.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/02-bourbon-stones-throw/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "STONE'S THROW", fill="black", font=font)
    draw.text((10, 30), "BOURBON", fill="black", font=font)
    draw.text((10, 50), "ALC. 45% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "GOVERNMENT WARNING:", fill="black", font=font)
    draw.text((10, 90), "(1) ACCORDING TO THE", fill="black", font=font)
    draw.text((10, 105), "SURGEON GENERAL...", fill="black", font=font)
    draw.text((10, 130), "750 ML", fill="black", font=font)
    draw.text((10, 150), "DISTILLED IN KENTUCKY", fill="black", font=font)
    img.save(OUT, "PNG", dpi=(300, 300))


if __name__ == "__main__":
    main()
