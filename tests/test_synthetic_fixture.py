from pathlib import Path

from PIL import Image

FIXTURE = Path("fixtures/01-spirits-clean/label.png")


def test_fixture_exists():
    assert FIXTURE.exists()


def test_fixture_is_png_with_dpi():
    with Image.open(FIXTURE) as img:
        assert img.format == "PNG"
        assert img.size == (200, 200)
        # PIL exposes DPI via info["dpi"] when pHYs is present.
        # PNG pHYs stores pixels-per-meter as int, so 300 dpi round-trips
        # as ~299.9994 due to lossy meter<->inch conversion (inherent to PIL).
        dpi = img.info.get("dpi")
        assert dpi is not None
        assert round(dpi[0]) == 300 and round(dpi[1]) == 300
