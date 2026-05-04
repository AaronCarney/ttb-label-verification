"""Low-resolution / glare degradation — exercises legibility short-circuit
(Evaluator routes to needs_review when assess_quality returns
needs_better_photo). Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

OUT = Path("fixtures/04-low-res-blurry/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Tiny canvas + blur + glare; quality assessor should flag.
    img = Image.new("RGB", (160, 160), color="white")
    draw = ImageDraw.Draw(img)
    f = ImageFont.load_default()
    draw.text((4, 4), "ACME", fill="black", font=f)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=3.0))
    # Glare hotspot
    hotspot = Image.new("RGBA", blurred.size, (255, 255, 255, 0))
    d2 = ImageDraw.Draw(hotspot)
    d2.ellipse((20, 20, 80, 80), fill=(255, 255, 255, 140))
    composite = Image.alpha_composite(blurred.convert("RGBA"), hotspot).convert("RGB")
    composite.save(OUT, dpi=(72, 72))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
