"""Fixture-05 batch generator — 50-label demo batch.

Distribution (mix forces M-of-N anomaly + override paths):
- 30 clean spirits  -> pass
- 10 ABV out-of-tolerance -> fail (FR-400-abv-tolerance)
- 5 warning title-case -> fail (FR-200-government-warning)
- 5 borderline confidence -> needs_review

Idempotent at every write. Re-run is a no-op once labels exist.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path("fixtures/05-batch-of-50")
LABEL_COUNT = 50
BATCH_ID = "00000000-0000-4000-8000-00000000b005"
AGENT_ID = "session-batch-005"
SUBMITTED_AT = "2026-04-01T12:10:00.000Z"

WARN_OK = "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON"
WARN_OK_2 = "GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES"
WARN_OK_3 = "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS."
WARN_BAD = "Government Warning: (1) According to the Surgeon"
WARN_BAD_2 = "General, women should not drink alcoholic beverages"
WARN_BAD_3 = "during pregnancy because of the risk of birth defects."

BRANDS = ("ACME BOURBON", "STILLHOUSE BOURBON", "FRANKFORT SELECT", "BLUE RIDGE RYE", "RIVER MILL")


def _font() -> ImageFont.ImageFont:
    return ImageFont.load_default()


def _base(brand: str, abv_text: str, warning: tuple[str, str, str]) -> Image.Image:
    img = Image.new("RGB", (480, 480), color="white")
    draw = ImageDraw.Draw(img)
    font = _font()
    draw.text((10, 10), brand, fill="black", font=font)
    draw.text((10, 30), "BOURBON WHISKEY", fill="black", font=font)
    draw.text((10, 50), abv_text, fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    draw.text((10, 120), "Product of USA", fill="black", font=font)
    draw.text((10, 160), warning[0], fill="black", font=font)
    draw.text((10, 180), warning[1], fill="black", font=font)
    draw.text((10, 200), warning[2], fill="black", font=font)
    return img


def _clean_label(idx: int) -> Image.Image:
    return _base(BRANDS[idx % len(BRANDS)], "ALC. 40% BY VOL.", (WARN_OK, WARN_OK_2, WARN_OK_3))


def _abv_fail_label(idx: int) -> Image.Image:
    return _base(BRANDS[idx % len(BRANDS)], "ALC. 40% BY VOL.", (WARN_OK, WARN_OK_2, WARN_OK_3))


def _warning_fail_label(idx: int) -> Image.Image:
    return _base(BRANDS[idx % len(BRANDS)], "ALC. 40% BY VOL.", (WARN_BAD, WARN_BAD_2, WARN_BAD_3))


def _borderline_label(idx: int) -> Image.Image:
    img = _clean_label(idx)
    block = Image.new("RGB", (470, 80), color="white")
    wd = ImageDraw.Draw(block)
    font = _font()
    wd.text((0, 0), WARN_OK, fill="black", font=font)
    wd.text((0, 20), WARN_OK_2, fill="black", font=font)
    wd.text((0, 40), WARN_OK_3, fill="black", font=font)
    img.paste(block.filter(ImageFilter.GaussianBlur(radius=0.8)), (10, 160))
    return img


# index -> (kind, expected_disposition, expected_reason_code, abv_actual_pct)
def _plan() -> list[tuple[str, str, str | None, str]]:
    plan: list[tuple[str, str, str | None, str]] = []
    for _ in range(30):
        plan.append(("clean", "pass", None, "40.0"))
    for _ in range(10):
        plan.append(("abv", "fail", "FR-400-abv-tolerance", "42.5"))
    for _ in range(5):
        plan.append(("warning", "fail", "FR-200-government-warning", "40.0"))
    for _ in range(5):
        plan.append(("borderline", "needs_review", None, "40.0"))
    return plan


def _render(idx: int, kind: str) -> Image.Image:
    if kind == "clean":
        return _clean_label(idx)
    if kind == "abv":
        return _abv_fail_label(idx)
    if kind == "warning":
        return _warning_fail_label(idx)
    if kind == "borderline":
        return _borderline_label(idx)
    raise ValueError(f"unknown kind: {kind}")


def _expected_block(idx: int, kind: str, disposition: str, reason_code: str | None,
                    abv_actual: str) -> dict:
    label_ref = f"batch-005-item-{idx:03d}"
    brand = BRANDS[idx % len(BRANDS)]
    return {
        "label_ref": label_ref,
        "application_ref": f"app-batch-005-{idx:03d}",
        "expected_disposition": disposition,
        "expected_reason_code": reason_code,
        "kind": kind,
        "expected_values": [
            {"field_id": "brand_name", "value": brand, "aliases": [brand.split()[0]]},
            {"field_id": "class_type", "value": "BOURBON WHISKEY"},
            {"field_id": "alcohol_content",
             "abv_labeled_pct": "40.0", "abv_actual_pct": abv_actual},
            {"field_id": "net_contents", "container_volume_ml": "750"},
            {"field_id": "name_and_address",
             "value": "ACME DISTILLERIES, FRANKFORT, KY"},
            {"field_id": "country_of_origin", "value": "USA"},
            {"field_id": "government_warning",
             "value": "GOVERNMENT WARNING: (1) ACCORDING ..."},
        ],
    }


def _write_labels(plan: list[tuple[str, str, str | None, str]]) -> None:
    for i, (kind, _disp, _rc, _abv) in enumerate(plan, start=1):
        path = OUT_DIR / f"label_{i:03d}.png"
        if path.is_file():
            continue
        img = _render(i, kind)
        img.save(path, dpi=(300, 300))


def _write_expected(plan: list[tuple[str, str, str | None, str]]) -> None:
    path = OUT_DIR / "expected.json"
    if path.is_file():
        return
    blocks = [_expected_block(i, kind, disp, rc, abv)
              for i, (kind, disp, rc, abv) in enumerate(plan, start=1)]
    path.write_text(json.dumps(blocks, indent=2) + "\n")


def _write_envelope() -> None:
    path = OUT_DIR / "batch_envelope.json"
    if path.is_file():
        return
    items = [
        {"label_ref": f"batch-005-item-{i:03d}",
         "application_ref": f"app-batch-005-{i:03d}"}
        for i in range(1, LABEL_COUNT + 1)
    ]
    envelope = {
        "batch_id": BATCH_ID,
        "agent_id": AGENT_ID,
        "submitted_at": SUBMITTED_AT,
        "items": items,
    }
    path.write_text(json.dumps(envelope, indent=2) + "\n")


def _write_notes() -> None:
    path = OUT_DIR / "notes.md"
    if path.is_file():
        return
    path.write_text(
        "# Fixture 05 — Batch of 50\n\n"
        "**PRD §6.3 / §8.1 reference.** 50-label batch envelope — exercises "
        "`POST /batches`, lookahead SSE streaming, M-of-N anomaly advisory, "
        "and the three-keystroke override path (FR-803).\n\n"
        "**Distribution (forces anomaly + override).**\n"
        "- 30 clean spirits → `pass` (synthesized from 01-spirits-clean)\n"
        "- 10 ABV out-of-tolerance → `fail` / `FR-400-abv-tolerance` "
        "(synthesized from 06-abv-out-of-tolerance; same-reason cluster forces "
        "M-of-N anomaly advisory)\n"
        "- 5 warning title-case → `fail` / `FR-200-government-warning` "
        "(synthesized from 03-warning-title-case)\n"
        "- 5 borderline confidence → `needs_review` (mild blur on warning block, "
        "synthesized from 07-borderline-confidence)\n\n"
        "**Variant strategy.** 5-brand rotation (`ACME BOURBON`, `STILLHOUSE "
        "BOURBON`, `FRANKFORT SELECT`, `BLUE RIDGE RYE`, `RIVER MILL`) over 50 "
        "labels keeps OCR signal stable while giving the brand-match path "
        "non-trivial input. ABV cluster carries `abv_actual_pct=42.5` vs "
        "`abv_labeled_pct=40.0` (delta = 2.5% > 1% threshold).\n\n"
        "**Provenance.** synthetic — built by `scripts/build_fixture_05.py` "
        "from PIL primitives. Idempotent: re-running is a no-op once labels "
        "exist.\n\n"
        "**Class balance tag.** spirits.\n"
    )


def main() -> None:
    if all((OUT_DIR / f"label_{i:03d}.png").is_file()
           for i in range(1, LABEL_COUNT + 1)):
        print("[skip] fixture-05 labels exist")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = _plan()
    _write_labels(plan)
    _write_expected(plan)
    _write_envelope()
    _write_notes()
    print(f"[ok] fixture-05 generated ({LABEL_COUNT} labels + envelope + expected + notes)")


if __name__ == "__main__":
    main()
