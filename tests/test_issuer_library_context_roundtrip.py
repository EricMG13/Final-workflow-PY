"""Answer key: a loaded context keeps every entered value (R-SB2 instrument defect).

context-form.html drew the deal-term `instrument` as a closed six-value <select>, so a loaded
"ABL revolver" or "6.00% senior secured notes due 2033" came out blank. The keys here are the
case files and a hand-written term list, never the form. The output is the `cpos:context`
message the app receives on #use-context, which it later posts to /api/runs/review.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from issuer_library_browser import ROOT, open_app

pytestmark = pytest.mark.browser

DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
_spec = importlib.util.spec_from_file_location("live_check", DESIGNS / "live_check.py")
live_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_check)

CAPTURE = (
    "if(window===window.top){window.__ctx=[];window.addEventListener('message',"
    "e=>{if(e.data&&e.data.type==='cpos:context')window.__ctx.push(e.data);});}"
)
C2 = ROOT / "cases/live-mattress-firm-2014/c2/context.json"
B_LIVE = ROOT / "cases/live-tdg-fy2024/b-live/context.json"
A_LIVE = ROOT / "cases/live-tdg-fy2024/a-live/context.json"
CASES = sorted(
    {*ROOT.glob("cases/*/*/context.json"), *ROOT.glob("cases/*/context.json"), C2, B_LIVE, A_LIVE}
)


def through_the_editor(browser: Any, path: Path) -> tuple[dict[str, Any], str]:
    """Load a context file as live_check.fill_form does, press Use, return (context, load note)."""
    screen = open_app(browser, "W-NewRun/run", init=CAPTURE)
    try:
        frame = screen.page.frame_locator("#context-editor")
        frame.locator("#load").wait_for(state="attached", timeout=15000)
        frame.locator("#load").set_input_files(str(path))
        frame.locator("#loadmsg").filter(has_text="Loaded").wait_for(timeout=15000)
        note = frame.locator("#loadmsg").inner_text()
        screen.page.click("#use-context")
        screen.page.wait_for_function("window.__ctx.length>0", timeout=15000)
        sent: dict[str, Any] = screen.page.evaluate("window.__ctx.at(-1)")
        assert screen.errors == []
        return sent["context"], note
    finally:
        screen.close()


def leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def test_c2_keeps_its_abl_revolver_instrument_and_the_second_term(browser: Any) -> None:
    sent, _ = through_the_editor(browser, C2)
    first, second = sent["deal_terms"][:2]
    assert len(sent["deal_terms"]) == 2
    key_first = {
        "facility_id": "abl-revolver",
        "instrument": "ABL revolver",
        "currency": "USD",
        "size_m": "125",
        "tenor_years": "5",
        "talk_spread_bps_low": "125",
        "talk_spread_bps_high": "175",
        "call_protection": "Prepayable at par",
        "as_of": "2014-09-11",
    }
    key_second = {
        "facility_id": "term-loan-b",
        "instrument": "Term loan B",
        "currency": "USD",
        "size_m": "720",
        "tenor_years": "7",
        "floor_pct": "1.00",
        "call_protection": "101 soft call, 6 months",
        "as_of": "2014-09-11",
    }
    assert {k: first.get(k) for k in key_first} == key_first
    assert {k: second.get(k) for k in key_second} == key_second


def test_a_free_text_instrument_is_kept_exactly(browser: Any) -> None:
    sent, note = through_the_editor(browser, B_LIVE)
    term = sent["deal_terms"][0]
    assert term["instrument"] == "6.00% senior secured notes due 2033"
    assert (term["facility_id"], term["size_m"], term["coupon_pct"], term["maturity"]) == (
        "tdg-6-00-secured-2033",
        "1500",
        "6.00",
        "2033-01-15",
    )
    assert "unknown value" not in note


@pytest.mark.parametrize(
    "case", CASES, ids=lambda p: p.relative_to(ROOT / "cases").parent.as_posix()
)
def test_every_entered_value_of_a_case_context_survives_the_editor(
    browser: Any, case: Path
) -> None:
    saved = json.loads(case.read_text("utf-8"))
    sent, note = through_the_editor(browser, case)
    out = dict(leaves(sent))
    lost = {
        path: (value, out.get(path, "<absent>"))
        for path, value in leaves(saved)
        if value not in ("", None, []) and out.get(path, "<absent>") != value
    }
    assert lost == {}, note


def test_fill_form_refuses_while_the_form_shows_an_unknown_value_note(
    browser: Any, tmp_path: Path
) -> None:
    """A closed-list loss must stop the walk before Start, not ride along as a silent note."""
    frame = (
        '<input id="load" type="file"><div id="loadmsg"></div><script>'
        "document.getElementById('load').onchange=()=>{document.getElementById('loadmsg')"
        ".textContent='Loaded context.json. 1 note(s): deal_terms[0].instrument: unknown value "
        '"ABL revolver", left blank\';};</script>'
    )
    shell = (
        '<button id="library-new-run">New</button><div id="context-readiness">'
        'Required fields complete</div><button id="use-context">Use</button>'
        f"<iframe id=\"context-editor\" srcdoc='{frame}'></iframe>"
    )
    context = tmp_path / "context.json"
    context.write_text("{}", encoding="utf-8")
    sources = tmp_path / "sources"
    sources.mkdir()
    page = browser.new_page()
    page.set_default_timeout(3000)
    page.route(
        "http://127.0.0.1:1/**",
        lambda route: route.fulfill(body=shell, content_type="text/html"),
    )
    args = SimpleNamespace(port=1, context=context, sources=sources)
    try:
        with pytest.raises(live_check.Refusal, match="unknown value"):
            live_check.fill_form(page, args)
    finally:
        page.close()
