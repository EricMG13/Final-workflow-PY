"""Frame states, search scope, tab vocabulary, report rows, Settings requests, the service banner
and unsaved-run guards, in a real browser. Synthetic data only; no server or provider is reached.

Where the Node suite stubbed layout or timers, these checks use the browser's own: a frame that
must not load has its request held open, and waits are for a condition, not a fixed time.
Marked browser: real browser proof, not a layout or visual acceptance.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin, urlsplit

import pytest
from issuer_library_browser import (
    CAPTURED_TIMERS,
    DEFAULT_APP,
    EMPTY_STORE,
    EMPTY_WORKSPACE,
    ORIGIN,
    Screen,
    held,
    js,
    json_reply,
    norm,
    open_app,
)
from test_issuer_library_app import NewRun

pytestmark = pytest.mark.browser

SETTINGS_BUTTONS = ["save-workspace", "refresh-library", "quit-library"]
# Settings requests answer after 300 ms, so a check can see the state while one is pending.
SLOW_FETCH = (
    "fail=>{window.__urls=[];window.fetch=url=>{window.__urls.push(url);"
    "return new Promise((resolve,reject)=>setTimeout(()=>fail?reject(new Error('down'))"
    ":resolve({ok:true,json:async()=>({})}),300));};}"
)
CATALOGUE_CHECK = (
    "async()=>{for(const f of [...window.__timers.values()])"
    "if(String(f).includes('/api/catalogue'))await f();}"
)


def path_of(href: str) -> str:
    return urlsplit(urljoin(ORIGIN + "/index.html", href)).path


@pytest.fixture
def screens(browser: Any, design: tuple[dict[str, Any], dict[str, Any]]) -> Iterator[Any]:
    """Open the curated fixture, or another store, at a route; every page ends without errors."""
    opened: list[Screen] = []

    def factory(
        route: str,
        *,
        timeout: int | None = None,
        api: dict[str, Any] | None = None,
        timers: str | None = None,
        store: tuple[dict[str, Any], dict[str, Any]] | None = None,
        app: dict[str, Any] | None = None,
    ) -> Screen:
        init = f"window.DESIGN_FRAME_TIMEOUT_MS={timeout};" if timeout is not None else ""
        data, workspace = store or design
        screen = open_app(
            browser,
            route,
            data,
            workspace,
            app=app or DEFAULT_APP,
            api=api,
            init=init,
            **({"timers": timers} if timers else {}),
        )
        opened.append(screen)
        return screen

    yield factory
    for screen in opened:
        assert screen.errors == []
        screen.close()


def nav(screen: Screen, hash_route: str) -> None:
    """Change the hash as a link would, and return once the app's own handler has run."""
    screen.page.evaluate(
        "h=>new Promise(resolve=>{addEventListener('hashchange',()=>setTimeout(resolve,0),"
        "{once:true});location.hash=h;})",
        hash_route,
    )
    screen.page.wait_for_timeout(30)


def frame_status(screen: Screen, selector: str = ".frame-status") -> str:
    return norm(screen.text(selector))


def report_path(design: tuple[dict[str, Any], dict[str, Any]], index: int = 0) -> str:
    return path_of(design[1]["reports"][index]["href"])


def test_tab_and_rail_vocabulary_follows_the_approved_destinations(screens: Any) -> None:
    screen = screens("W-Overview/overview?c=tdg-002")
    assert screen.texts(".workspace-tabs a") == [
        "Overview",
        "Modules",
        "Calendar",
        "Reports",
        "Evidence",
    ]
    assert screen.exists('.rail a[aria-label="Reports"]')
    assert not screen.exists('.rail a[aria-label="Deliverables"]')
    assert str(screen.attr('.rail a[aria-label="Run activity"] img', "src")).endswith(
        "icons/activity.svg"
    )
    nav(screen, "W-Reports/list?c=tdg-002")
    assert screen.eval("document.title") == "Reports · Issuer Library"
    assert screen.text("#section-title") == "Reports"
    assert screen.text("h1") == screen.eval('contexts["tdg-002"].title')


def test_search_is_cleared_when_leaving_the_modules_and_can_be_cleared_in_place(
    screens: Any,
) -> None:
    screen = screens("CP-1/performance?c=tdg-002")
    tools = "document.getElementById('workbench').classList.contains('tools-workspace')"
    results = "document.getElementById('search-results').children.length"
    screen.set_value("#module-search", "liquidity")
    assert screen.eval(results) > 0 and screen.hidden("module-search-clear") is False
    nav(screen, "W-Calendar/events?c=tdg-002")
    assert screen.eval("document.getElementById('module-search').value") == ""
    assert screen.eval(results) == 0 and screen.eval(tools) is True
    nav(screen, "CP-2/assessment?c=tdg-002")
    assert screen.eval(tools) is False
    screen.set_value("#module-search", "liquidity")
    screen.click("#module-search-clear")
    assert screen.eval("document.getElementById('module-search').value") == ""
    assert screen.eval(results) == 0 and screen.active() == "module-search"
    assert screen.hidden("module-search-clear") is True


def test_the_navigator_is_resident_on_overview_and_modules_only(screens: Any) -> None:
    screen = screens("W-Overview/overview?c=tdg-002")
    tools = "document.getElementById('workbench').classList.contains('tools-workspace')"
    assert screen.eval(tools) is False
    nav(screen, "CP-1/performance?c=tdg-002")
    assert screen.eval(tools) is False
    for route in ["W-Reports/list", "W-Evidence/sources", "CP-OS/activity"]:
        nav(screen, f"{route}?c=tdg-002")
        assert screen.eval(tools) is True, route


def test_the_report_frame_shows_loading_failure_with_retry_and_loaded(
    screens: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    report = design[1]["reports"][0]
    screen = screens("W-Calendar/events?c=tdg-002", timeout=1000, api={report_path(design): held})
    nav(screen, f"W-Reports/{report['id']}")
    assert frame_status(screen).startswith("Loading report")
    screen.page.wait_for_function(
        "/did not load/.test(document.querySelector('.frame-status').textContent)"
    )
    assert screen.attr(".frame-status a", "href") == report["download"]
    src = screen.attr("#report-preview", "src")
    screen.click(".frame-status .frame-retry")
    assert frame_status(screen) == "Loading report…"
    assert screen.attr("#report-preview", "src") == src
    screen.eval("document.getElementById('report-preview').dispatchEvent(new Event('load'))")
    assert screen.eval("document.querySelector('.frame-status').hidden") is True
    screen.page.wait_for_timeout(1200)
    assert screen.eval("document.querySelector('.frame-status').hidden") is True


def test_the_run_context_frame_shows_loading_failure_with_retry_and_ready(screens: Any) -> None:
    screen = screens(
        "W-NewRun/run",
        timeout=1000,
        api={"/context-form.html": held},
        store=(EMPTY_STORE, EMPTY_WORKSPACE),
    )
    status = "#context-step .frame-status"
    assert frame_status(screen, status).startswith("Loading run context form")
    screen.page.wait_for_function(
        "/did not load/.test(document.querySelector('#context-step .frame-status').textContent)"
    )
    screen.click(f"{status} .frame-retry")
    assert frame_status(screen, status).startswith("Loading run context form")
    screen.eval(
        "window.dispatchEvent(new MessageEvent('message',{source:"
        "document.getElementById('context-editor').contentWindow,"
        "data:{type:'cpos:height',height:500}}))"
    )
    assert screen.eval(f"document.querySelector('{status}').hidden") is True


def rest_rows(screen: Screen, context: str, required: bool) -> None:
    reports = {r["id"]: r for r in screen.eval("window.DESIGN_WORKSPACE.reports")}
    issuer = screen.eval(f'contexts["{context}"].issuer')
    rows = js(
        screen,
        "return [...d.querySelectorAll('.report-rest .report-list li')].map(li=>({"
        "code:norm(li.querySelector('.code').textContent),text:norm(li.textContent),"
        "prefix:Boolean(li.querySelector('.report-issuer'))}));",
    )
    if required:
        assert rows, f"no rows under .report-rest for {context}"
    for row in rows:
        report = reports[row["code"]]
        led = report["label"].strip().startswith(report["issuer"])
        if report["issuer"] != issuer and not led:
            assert row["text"].startswith(report["issuer"]), row["text"]
        if led:
            assert report["label"].strip() in row["text"], row["text"]
        shown = row["text"].replace(row["code"], "", 1)
        assert shown.count(report["issuer"]) == 1, f"issuer repeated: {row['text']}"
        assert row["prefix"] is not led, row["text"]


def test_report_rows_carry_the_id_sort_by_build_and_prefix_other_issuers(screens: Any) -> None:
    screen = screens("W-Reports/list?c=tdg-002")
    ids = {r["id"] for r in screen.eval("window.DESIGN_WORKSPACE.reports")}
    built = screen.texts(".report-built .report-list li")
    assert built
    builds = [int(m.group(1)) if (m := re.search(r"Build (\d+)", t)) else 0 for t in built]
    assert builds == sorted(builds, reverse=True), builds
    for row in js(
        screen,
        "return [...d.querySelectorAll('.report-list li')].map(li=>({"
        "code:li.querySelector('.code')?.textContent,text:li.textContent}));",
    ):
        assert row["code"] in ids, row["text"]
        assert "  " not in row["text"], repr(row["text"])
    rest_rows(screen, "tdg-002", False)
    # The engine's default label for an uncurated report starts with its issuer; curated ones do not.
    screen.eval(
        "window.DESIGN_WORKSPACE.reports[0].label="
        "window.DESIGN_WORKSPACE.reports[0].issuer+' · as of 2025-05-31'"
    )
    nav(screen, "W-Reports/list?c=ford-otosan-2024")
    assert screen.exists(".report-rest .report-list li .code")
    assert any(
        "TransDigm Group · as of 2025-05-31" in norm(t)
        for t in screen.texts(".report-rest .report-list li a")
    ), "issuer-led label case missing"
    rest_rows(screen, "ford-otosan-2024", True)


def test_the_report_selector_lists_builds_in_the_list_page_order(screens: Any) -> None:
    screen = screens("W-Reports/list?c=tdg-002")
    report = screen.eval(
        'window.DESIGN_WORKSPACE.reports.filter(r=>r.issuer===contexts["tdg-002"].issuer)[0].id'
    )
    nav(screen, f"W-Reports/{report}?c=tdg-002")
    options = screen.texts("#report-select option")
    assert len(options) > 1
    builds = [int(m.group(1)) if (m := re.match(r"Build (\d+)", o)) else 0 for o in options]
    assert builds == sorted(builds, reverse=True), builds


def test_help_names_reports_not_deliverables(screens: Any) -> None:
    help_text = norm(screens("W-Help/help?c=tdg-002").content())
    assert "Reports lists" in help_text and "Deliverables lists" not in help_text


def test_settings_lists_issues_as_path_and_message_and_quits_as_a_tertiary_action(
    screens: Any,
) -> None:
    issues = ["deliverables/x: Delivery manifest requires report.html: and view.json", "plain note"]
    screen = screens(
        "W-Settings/workspace",
        store=(EMPTY_STORE, EMPTY_WORKSPACE),
        app={**DEFAULT_APP, "issues": issues},
    )
    quit_button = js(
        screen,
        "const q=d.getElementById('quit-library');return {tertiary:q.classList.contains('tertiary-action'),"
        "last:q.parentElement.lastElementChild===q,"
        "actions:q.parentElement.classList.contains('step-actions')};",
    )
    assert quit_button == {"tertiary": True, "last": True, "actions": True}
    items = js(
        screen,
        "return [...d.querySelectorAll('.issue-list li')].map(li=>({"
        "code:li.querySelector('.code')?.textContent??null,message:li.children[1]?.textContent}));",
    )
    assert len(items) == 2
    assert items[0] == {
        "code": "deliverables/x",
        "message": "Delivery manifest requires report.html: and view.json",
    }
    assert items[1]["code"] is None


def settings(screens: Any, fail: bool) -> Screen:
    screen: Screen = screens("W-Settings/workspace", store=(EMPTY_STORE, EMPTY_WORKSPACE))
    screen.page.evaluate(SLOW_FETCH, fail)
    return screen


def disabled(screen: Screen) -> list[bool]:
    return [screen.eval(f"document.getElementById('{b}').disabled") for b in SETTINGS_BUTTONS]


def test_h1_settings_sends_one_request_at_a_time_and_shows_what_is_happening(
    screens: Any,
) -> None:
    screen = settings(screens, False)
    screen.click("#refresh-library")
    screen.click("#refresh-library")
    assert disabled(screen) == [True, True, True]
    assert screen.text("#settings-status").startswith("Refreshing")
    # Read while the request is pending: a successful refresh reloads the page.
    assert screen.eval("window.__urls.filter(u=>u==='/api/refresh').length") == 1
    with screen.page.expect_navigation():
        pass


def test_h1_a_failed_settings_request_re_enables_the_buttons_and_says_why(screens: Any) -> None:
    screen = settings(screens, True)
    screen.click("#save-workspace")
    screen.page.wait_for_function(
        "document.getElementById('settings-status').textContent.startsWith('Could not update')",
        timeout=5000,
    )
    assert disabled(screen) == [False, False, False]
    assert screen.text("#settings-status").startswith("Could not update the library")


def test_h1_quit_locks_the_buttons_and_is_ignored_during_another_request(screens: Any) -> None:
    screen = settings(screens, False)
    screen.click("#quit-library")
    assert disabled(screen) == [True, True, True]
    screen.page.wait_for_function("document.body.dataset.quit==='1'", timeout=5000)
    other = settings(screens, False)
    other.click("#refresh-library")
    other.eval("()=>{const q=document.getElementById('quit-library');q.disabled=false;q.click();}")
    assert other.eval("window.__urls") == ["/api/refresh"]
    with other.page.expect_navigation():
        pass


def test_h2_quit_marks_the_library_stopped(screens: Any) -> None:
    screen = settings(screens, False)
    screen.click("#quit-library")
    screen.page.wait_for_function("document.body.dataset.quit==='1'", timeout=5000)


def banner_page(screens: Any, state: dict[str, bool]) -> Screen:
    catalogue = {"workspace": "/research", "policy_locked": False, "issues": [], "real": []}

    def reply(route: Any) -> None:
        if state["down"]:
            route.abort()
        else:
            json_reply(catalogue)(route)

    screen: Screen = screens(
        "W-Library/cases",
        store=(EMPTY_STORE, EMPTY_WORKSPACE),
        api={"/api/catalogue": reply},
        timers=CAPTURED_TIMERS,
    )
    return screen


def check(screen: Screen) -> bool:
    """Run boot.js's workspace check once and say whether the banner is still hidden."""
    screen.page.evaluate(CATALOGUE_CHECK)
    return screen.hidden("service-down")


def test_h2_the_service_banner_appears_after_two_failed_checks_and_clears_on_success(
    screens: Any,
) -> None:
    state = {"down": False}
    screen = banner_page(screens, state)
    state["down"] = True
    assert check(screen) is True
    assert check(screen) is False
    state["down"] = False
    assert check(screen) is True
    state["down"] = True
    screen.eval("document.body.dataset.quit='1'")
    assert [check(screen) for _ in range(3)] == [True, True, True]


def test_h2_a_success_between_failures_resets_the_count(screens: Any) -> None:
    state = {"down": True}
    screen = banner_page(screens, state)
    check(screen)
    state["down"] = False
    check(screen)
    state["down"] = True
    assert check(screen) is True


def reloads(screen: Screen, button: str, confirm: bool) -> bool:
    """Click a reload button with confirm answering as given; say whether the page reloaded."""
    screen.page.evaluate(
        "c=>{window.__alive=1;window.confirm=()=>c;document.body.dataset.draft='1';}", confirm
    )
    if not confirm:
        screen.click(button)
        screen.page.wait_for_timeout(100)
        return screen.eval("window.__alive") != 1
    with screen.page.expect_navigation():
        screen.click(button)
    return screen.eval("window.__alive") != 1


def test_h3_reload_honours_the_unsaved_run_confirm(browser: Any) -> None:
    run = NewRun(browser)
    assert reloads(run.screen, "#reload-service", confirm=False) is False
    assert reloads(run.screen, "#reload-workspace", confirm=False) is False
    assert reloads(run.screen, "#reload-workspace", confirm=True) is True
    run.close()


def test_h3_start_clears_the_unsaved_run_flag(browser: Any) -> None:
    run = NewRun(browser)
    draft = "document.body.dataset.draft??null"
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    assert run.page.evaluate(draft) == "1"
    run.confirm()
    run.click("start-run")
    assert run.page.evaluate(draft) is None
    run.close()


def test_h3_preparing_a_run_sets_the_flag_and_another_run_clears_it(browser: Any) -> None:
    run = NewRun(browser)
    draft = "document.body.dataset.draft??null"
    run.context()
    assert run.page.evaluate(draft) == "1"
    run.page.evaluate(
        "()=>{const b=document.getElementById('another-run');b.hidden=false;b.click();}"
    )
    assert run.page.evaluate(draft) is None
    run.close()


def missing_page(screens: Any, design: tuple[dict[str, Any], dict[str, Any]], fetch: str) -> Screen:
    screen: Screen = screens(
        "W-Calendar/events?c=tdg-002", timeout=5000, api={report_path(design): held}
    )
    screen.page.evaluate(fetch)
    nav(screen, f"W-Reports/{design[1]['reports'][0]['id']}")
    return screen


def test_h4_a_report_whose_file_has_gone_says_so_at_once_with_reload(
    screens: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    screen = missing_page(
        screens,
        design,
        "()=>{window.__heads=[];window.fetch=async(url,o)=>{window.__heads.push(o?.method);"
        "return {ok:false,status:404};};}",
    )
    assert "could not be found" in frame_status(screen)
    assert screen.exists(".frame-status button") and not screen.exists(".frame-status .frame-retry")
    assert screen.eval("window.__heads[0]") == "HEAD"


def test_h4_a_404_page_loading_after_the_missing_answer_does_not_hide_it(
    screens: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    screen = missing_page(screens, design, "()=>{window.fetch=async()=>({ok:false,status:404});}")
    screen.eval("document.getElementById('report-preview').dispatchEvent(new Event('load'))")
    assert screen.eval("document.querySelector('.frame-status').hidden") is False
    assert "could not be found" in frame_status(screen)


def test_h4_a_failed_request_for_the_file_also_says_it_could_not_be_found(
    screens: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    screen = missing_page(
        screens, design, "()=>{window.fetch=async()=>{throw new Error('down');};}"
    )
    assert "could not be found" in frame_status(screen)


def test_h4_a_present_file_keeps_the_loading_state_until_the_frame_loads(
    screens: Any, design: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    screen = missing_page(screens, design, "()=>{window.fetch=async()=>({ok:true,status:200});}")
    assert frame_status(screen) == "Loading report…"


def test_h5_an_evidence_tab_with_no_retained_files_says_so(screens: Any) -> None:
    screen = screens("W-Overview/overview?c=tdg-002")
    screen.eval('contexts["tdg-002"].modules={}')
    nav(screen, "W-Evidence/sources?c=tdg-002")
    assert "No retained files for this run" in norm(screen.content())
    assert screen.exists('#content a[href="#W-Library/cases"]')


def test_layout_toggle_label_issuer_title_library_band_offset_and_row_labels(
    screens: Any,
) -> None:
    screen = screens("W-Reports/list?c=tdg-002")
    assert norm(screen.text("#module-toggle")) == "Browse modules"
    nav(screen, "W-Overview/overview?c=tdg-002")
    title = screen.attr(".issuer h1", "title")
    assert title and title == screen.text(".issuer h1")
    nav(screen, "W-Library/cases")
    # jsdom has no layout, so the Node suite saw -8px; here the band has a real height. The app
    # measures it on render and on resize, so a resize first makes the comparison independent of
    # when layout settled.
    band = js(
        screen,
        "window.dispatchEvent(new Event('resize'));return {set:d.querySelector('.library-workspace').style.getPropertyValue('--band-h'),"
        "want:`${d.querySelector('.library-discovery').offsetHeight-8}px`};",
    )
    assert band["set"] == band["want"] and band["set"] != "-8px", band
    nav(screen, "W-Overview/overview?c=tdg-002")
    assert "--band-h" not in screen.eval("document.getElementById('workbench').style.cssText")
    nav(screen, "W-Library/cases")
    labels = screen.eval(
        "[...document.querySelectorAll('.run-row td:not(:first-child):not(.row-open), "
        ".issuer-row td:not(.row-open)')].map(c=>c.dataset.label??null)"
    )
    assert labels and None not in labels
    assert sorted(set(labels)) == ["Period", "Reports", "Run", "Workflow"]
