from pathlib import Path

from PIL import Image

FIXTURE = Path("fixtures/02-bourbon-stones-throw/label.png")


def test_fixture_exists():
    assert FIXTURE.exists()


def test_fixture_is_png_with_dpi():
    with Image.open(FIXTURE) as img:
        assert img.format == "PNG"
        assert img.size == (200, 200)
        dpi = img.info.get("dpi")
        # PNG pHYs round-trip is lossy via integer pixels-per-meter — accept ±1.
        assert dpi is not None
        assert int(round(dpi[0])) == 300
