"""Title-case GOVERNMENT WARNING — exercises FR-200-style case-sensitivity rule.

Idempotent: skips if label.png already exists.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/03-warning-title-case/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (480, 480), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "BOURBON WHISKEY", fill="black", font=font)
    draw.text((10, 50), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    draw.text((10, 120), "Product of USA", fill="black", font=font)
    # FR-200 violation: title-case (Government Warning), not ALL CAPS.
    draw.text((10, 160), "Government Warning: (1) According to the Surgeon", fill="black", font=font)
    draw.text((10, 180), "General, women should not drink alcoholic beverages", fill="black", font=font)
    draw.text((10, 200), "during pregnancy because of the risk of birth defects.", fill="black", font=font)
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
