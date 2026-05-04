"""Deterministic synthetic label fixture for E3 tests.

200x200 white PNG with embedded "ACME BOURBON" + "ALC. 40% BY VOL." +
GOVERNMENT WARNING block; PIL pHYs DPI=300. ~5 KB.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/01-spirits-clean/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 50), "GOVERNMENT WARNING:", fill="black", font=font)
    draw.text((10, 70), "(1) ACCORDING TO THE", fill="black", font=font)
    draw.text((10, 85), "SURGEON GENERAL...", fill="black", font=font)
    draw.text((10, 110), "750 ML", fill="black", font=font)
    draw.text((10, 130), "DISTILLED IN KENTUCKY", fill="black", font=font)
    img.save(OUT, "PNG", dpi=(300, 300))


if __name__ == "__main__":
    main()
