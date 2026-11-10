"""The report text live_check reads keeps cell boundaries: no number is made from two cells.

Marked browser: a real Chromium evaluates the script live_check runs on #view-root.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
spec = importlib.util.spec_from_file_location("live_check", DESIGNS / "live_check.py")
live_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_check)
import flow_check as flow

HTML = (
    '<div id="view-root"><table><tr><td>September 11, 2014</td><td>Rounded</td></tr>'
    "<tr><td>-83,297</td><td>Not calculable</td></tr></table>"
    "<p>Net sales</p><p>7,940</p><svg><text>99</text></svg></div>"
)
SEPARATED = "September 11, 2014\nRounded\n-83,297\nNot calculable\nNet sales\n7,940"


def test_report_text_separates_cells_and_drops_svg(browser: Any) -> None:
    page = browser.new_page()
    try:
        page.set_content(HTML)
        text = page.eval_on_selector("#view-root", live_check.REPORT_TEXT_JS)
    finally:
        page.close()
    assert flow.numbers(text) == flow.numbers(SEPARATED)
    assert "September 11, 2014" in " ".join(text.split())


def test_report_numbers_from_separate_cells_are_evidenced() -> None:
    assert flow.report_faults(SEPARATED, ["September 11, 2014 -83,297 7,940"]) == []
