"""A run being prepared is never cleared by a reload without asking: draft-guard.test.cjs at
final-workflow dd3dfa18.

The Node suite ran boot.js, installSettings and watchFrame in a vm context with stub elements and a
stubbed location.reload. Here the real page does each of them: the user's answer to confirm is set
in the page, and a reload is observed as the page's own beforeunload, counted in sessionStorage so
the count survives the reload. A click's handlers run before it returns, so a count read in the
same evaluate shows whether a reload began. Synthetic state only; no server or provider.
Marked browser: real browser proof.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from issuer_library_browser import Screen, json_reply, open_app, text_reply

pytestmark = pytest.mark.browser

INIT = """
if(window===top){
window.__bump=k=>sessionStorage.setItem(k,String(+(sessionStorage.getItem(k)||0)+1));
addEventListener('beforeunload',()=>__bump('unloads'));
const __wrapped=window.fetch;
window.fetch=(url,options)=>{
  if(/^\\/api\\/(settings|refresh)$/.test(String(url))){
    const sent=JSON.parse(sessionStorage.getItem('requests')||'[]');
    sent.push(String(url));sessionStorage.setItem('requests',JSON.stringify(sent));
  }
  return __wrapped(url,options);
};
}
"""
ASK = (
    "([draft,answer])=>{if(draft)document.body.dataset.draft='1';"
    "window.confirm=()=>{__bump('confirms');return answer;};}"
)
STATE = (
    "()=>({confirm:+(sessionStorage.getItem('confirms')||0),"
    "reload:+(sessionStorage.getItem('unloads')||0),"
    "requests:JSON.parse(sessionStorage.getItem('requests')||'[]')})"
)
CLICK = "id=>{document.getElementById(id).click();}"
CLICK_IN = "s=>{document.querySelector(s).click();}"


@pytest.fixture
def opened(browser: Any) -> Iterator[Any]:
    screens: list[Screen] = []

    def factory(route: str, **options: Any) -> Screen:
        screen = open_app(browser, route, init=INIT, **options)
        screens.append(screen)
        return screen

    yield factory
    for screen in screens:
        assert screen.errors == []
        screen.close()


def press(screen: Screen, script: str, target: str, reloads: bool) -> dict[str, Any]:
    """Click with the answer already set. A reload is awaited; no reload is read at once."""
    if reloads:
        with screen.page.expect_navigation():
            screen.page.evaluate(script, target)
    else:
        screen.page.evaluate(script, target)
    state: dict[str, Any] = screen.page.evaluate(STATE)
    return state


def counts(state: dict[str, Any]) -> dict[str, int]:
    return {"confirm": state["confirm"], "reload": state["reload"]}


def test_reload_asks_before_clearing_a_prepared_run_while_another_screen_is_shown(
    opened: Any,
) -> None:
    for new_run_hidden in (True, False):
        for button in ("reload-workspace", "reload-service"):
            screen = opened("W-Library/cases")
            screen.page.evaluate(ASK, [True, False])
            screen.page.evaluate(
                "h=>{document.getElementById('new-run').hidden=h;}", new_run_hidden
            )
            state = press(screen, CLICK, button, reloads=False)
            assert counts(state) == {"confirm": 1, "reload": 0}, f"{button} hidden={new_run_hidden}"
    accepted = opened("W-Library/cases")
    accepted.page.evaluate(ASK, [True, True])
    assert counts(press(accepted, CLICK, "reload-workspace", reloads=True)) == {
        "confirm": 1,
        "reload": 1,
    }
    none = opened("W-Library/cases")
    none.page.evaluate(ASK, [False, False])
    assert counts(press(none, CLICK, "reload-workspace", reloads=True)) == {
        "confirm": 0,
        "reload": 1,
    }


def test_settings_save_and_refresh_ask_before_clearing_a_prepared_run_and_send_nothing_on_cancel(
    opened: Any,
) -> None:
    for button, url in (("save-workspace", "/api/settings"), ("refresh-library", "/api/refresh")):
        api = {url: json_reply({})}
        kept = opened("W-Settings/workspace", api=api)
        kept.page.evaluate(ASK, [True, False])
        assert press(kept, CLICK, button, reloads=False) == {
            "confirm": 1,
            "reload": 0,
            "requests": [],
        }, button
        cleared = opened("W-Settings/workspace", api=api)
        cleared.page.evaluate(ASK, [True, True])
        assert press(cleared, CLICK, button, reloads=True) == {
            "confirm": 1,
            "reload": 1,
            "requests": [url],
        }, button
        plain = opened("W-Settings/workspace", api=api)
        plain.page.evaluate(ASK, [False, False])
        assert press(plain, CLICK, button, reloads=True) == {
            "confirm": 0,
            "reload": 1,
            "requests": [url],
        }, button


def test_the_reload_offered_for_a_deliverable_that_has_gone_asks_before_clearing_a_prepared_run(
    opened: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    report = design[1]["reports"][0]
    path = "/" + report["href"].split("?")[0].lstrip("/")
    for draft, answer, expected in (
        (True, False, {"confirm": 1, "reload": 0}),
        (True, True, {"confirm": 1, "reload": 1}),
        (False, False, {"confirm": 0, "reload": 1}),
    ):
        screen = opened(
            f"W-Reports/{report['id']}?c=tdg-002",
            store=design[0],
            workspace=design[1],
            api={path: text_reply("gone", 404)},
        )
        screen.page.wait_for_function(
            "document.querySelectorAll('.frame-status button').length===1"
        )
        screen.page.evaluate(ASK, [draft, answer])
        state = press(screen, CLICK_IN, ".frame-status button", reloads=expected["reload"] == 1)
        assert counts(state) == expected, f"draft={draft} answer={answer}"
