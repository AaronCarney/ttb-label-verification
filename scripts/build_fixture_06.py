"""ABV value on label conflicts with application by > 1% — exercises FR-400
ABV-tolerance fail. Existing fixtures/06/expected.json carries
abv_labeled_pct=40.0 (label) and abv_actual_pct=42.5 (application);
the rule engine flags the > 1% delta. Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/06-abv-out-of-tolerance/label.png")


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
    # Label says 40%, application says 42.5% — delta = 2.5% > 1% threshold.
    draw.text((10, 50), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    draw.text((10, 120), "Product of USA", fill="black", font=font)
    draw.text((10, 160), "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON", fill="black", font=font)
    draw.text((10, 180), "GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES", fill="black", font=font)
    draw.text((10, 200), "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS.", fill="black", font=font)
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
