"""T30: AC-FR-803 — three-keystroke override completes the canonical case."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = (
    ROOT / "tests" / "fixtures" / "envelopes" / "single" / "03-warning-title-case.json"
)


@pytest.mark.usefixtures("live_server", "pnpm_built_island")
def test_three_keystroke_override(page: Page, live_server_url: str) -> None:
    envelope = json.loads(FIXTURE.read_text())
    page.add_init_script(
        script=f"""
          window.addEventListener('DOMContentLoaded', () => {{
            const tag = document.createElement('script');
            tag.id = 'envelope';
            tag.type = 'application/json';
            tag.textContent = {json.dumps(json.dumps(envelope))};
            document.body.appendChild(tag);
          }});
        """
    )
    page.goto(f"{live_server_url}/")
    page.wait_for_selector('[data-mounted="true"]', timeout=5000)

    # Keystroke 1: 'O' → drawer opens, picker auto-focuses.
    page.keyboard.press("o")
    page.wait_for_selector('[role="dialog"]', timeout=2000)
    assert page.locator('[role="combobox"]').count() == 1

    # Keystroke 2: 'W' → unique prefix → ReasonCodePicker auto-selects WARNING.*.
    page.keyboard.type("w")

    # Keystroke 3: ENTER → submit.
    page.keyboard.press("Enter")

    # The LiveRegion announces the saved override; wait for the message.
    page.wait_for_selector(
        'text=/Override saved: WARNING\\.STYLE\\.HEADING_NOT_BOLD_CAPS/',
        timeout=2000,
    )


@pytest.mark.usefixtures("live_server", "pnpm_built_island")
def test_jk_navigation_does_not_steal_typing(page: Page, live_server_url: str) -> None:
    """J/K are reserved for batch navigation but must not fire while typing."""
    envelope = json.loads(FIXTURE.read_text())
    page.add_init_script(
        script=f"""
          window.addEventListener('DOMContentLoaded', () => {{
            const tag = document.createElement('script');
            tag.id = 'envelope';
            tag.type = 'application/json';
            tag.textContent = {json.dumps(json.dumps(envelope))};
            document.body.appendChild(tag);
          }});
        """
    )
    page.goto(f"{live_server_url}/")
    page.wait_for_selector('[data-mounted="true"]', timeout=5000)
    page.keyboard.press("o")
    page.wait_for_selector('[role="dialog"]', timeout=2000)
    page.keyboard.type("j")  # 'j' should land in the picker as text, not navigate.
    assert page.locator('[role="combobox"]').input_value().lower() == "j"
