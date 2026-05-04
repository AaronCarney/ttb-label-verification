"""Borderline-confidence fixture — mid-confidence band on at least one field.
Pillow output is deterministic given pinned dependencies. Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

OUT = Path("fixtures/07-borderline-confidence/label.png")


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
    # Light blur in the warning region — should land confidence in mid-band.
    warning_block = Image.new("RGB", (470, 80), color="white")
    wd = ImageDraw.Draw(warning_block)
    wd.text((0, 0), "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON", fill="black", font=font)
    wd.text((0, 20), "GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES", fill="black", font=font)
    wd.text((0, 40), "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS.", fill="black", font=font)
    blurred = warning_block.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.paste(blurred, (10, 160))
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
