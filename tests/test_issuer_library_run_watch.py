"""The app-wide run watcher: run-watch.test.cjs at final-workflow dd3dfa18.

The Node suite ran views.js, actions.js and screen.js in jsdom with fake timers, fetch and
Notification. Here the real app opens and its own boot runs the first watch; /api/runs/list is
answered from a job list the test changes between polls. The OS notice is a recording class set
in the page, so the test reads exactly what the page asked it to show. Pure functions are called
in the page itself. The page's own 30 s catalogue interval also runs, so the interval checks name
both timers. Synthetic job lists only; nothing reaches a server or a provider.
Marked browser: real browser proof.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from issuer_library_browser import (
    CAPTURED_TIMERS,
    EMPTY_STORE,
    Screen,
    json_reply,
    open_app,
    release,
    until,
)

pytestmark = pytest.mark.browser

ID = "web-" + "a" * 32
ID2 = "web-" + "d" * 32
KEY = "issuer-library.run-strip-dismissed"
MODULES = ["CP-0", "CP-1", "CP-2", "CP-3"]
RAIL = '.rail [data-place="Run activity"]'
ACTIVITY = ["View activity", f"#CP-OS/activity?c={ID}"]
BUDGET = (
    "Stopped: the next model call would pass the spending cap. "
    "Resuming keeps the accepted modules; the resumed run has its own cap."
)
CHECKER = "Stopped: a module's handoff did not pass its check within the allowed turns."
PROVIDER = "Stopped: the model provider returned an error or an unknown charge."
INTERRUPTED = "Stopped: the run was interrupted before a response was retained."
BOOTED = (
    "typeof runWatch!=='undefined'&&!runWatch.busy"
    "&&__calls.some(c=>c.url.startsWith('/api/runs/list'))"
)
OS_NOTICE = """
window.__built=[];
window.Notification=class{static permission=%r;static requestPermission=async()=>%r;
constructor(title,options){this.title=title;this.options=options;window.__built.push(this);}};
window.__warnings=[];const __warn=console.warn;
console.warn=(...args)=>{window.__warnings.push(String(args[0]));__warn.apply(console,args);};
"""
POLL_TIMES = (
    "window.__ms=new Map();const __set=window.setInterval;"
    "window.setInterval=(fn,ms)=>{const id=__set(fn,ms);window.__ms.set(id,ms);return id;};"
)
PARTS = (
    "()=>{const s=document.getElementById('run-strip');"
    "return{title:s.querySelector('.strip-title').textContent,"
    "lines:[...s.querySelectorAll('.strip-text')].map(n=>n.textContent),"
    "actions:[...s.querySelectorAll('.strip-actions a')]"
    ".map(a=>[a.textContent,a.getAttribute('href')])};}"
)
INTERCEPT = (
    "a=>{window.__reloads=0;window.__asked=0;window.reloadApp=()=>{window.__reloads++;};"
    "window.confirm=()=>{window.__asked++;return a;};}"
)


def job(**over: Any) -> dict[str, Any]:
    """A job as /api/runs/list sends it; a None field is left out, as undefined is in JSON."""
    base = {
        "id": ID, "state": "running", "message": "Working", "run_available": True,
        "issuer": "Northbridge Group", "pathway": "covenant_refinancing", "as_of": "2025-03-31",
        "modules": MODULES, "module_details": [{"id": m, "title": "Title " + m} for m in MODULES],
        "progress": {"module": "CP-2", "step": "running", "turn": 2, "max_turns": 24,
                     "spent_usd": "0.42", "held_usd": "1.86", "cap_usd": "10.00", "accepted": 2},
    }  # fmt: skip
    return {k: v for k, v in {**base, **over}.items() if v is not None}


def stopped(**over: Any) -> dict[str, Any]:
    return job(state="stopped", reason="budget", message="", **over)


class Watch:
    def __init__(self, screen: Screen, jobs: list[dict[str, Any]]) -> None:
        self.s = screen
        self.jobs = jobs

    def watch(self) -> None:
        self.s.eval("watchRuns()")

    def poll(self, *jobs: dict[str, Any]) -> None:
        self.jobs[:] = jobs
        self.watch()

    def mark(self) -> str:
        mark: str = self.s.eval("runMark")
        return mark

    def title(self) -> str:
        title: str = self.s.eval("document.title")
        return title

    def built(self) -> list[dict[str, Any]]:
        notices: list[dict[str, Any]] = self.s.eval(
            "__built.map(n=>({title:n.title,options:{...n.options}}))"
        )
        return notices

    def parts(self) -> dict[str, Any]:
        parts: dict[str, Any] = self.s.page.evaluate(PARTS)
        return parts

    def call(self, function: str, *args: Any) -> Any:
        return self.s.page.evaluate(f"a=>{function}(...a)", list(args))

    def stored(self) -> Any:
        return self.s.page.evaluate("k=>JSON.parse(localStorage.getItem(k))", KEY)

    def intercept(self, answer: bool = True, draft: bool = False) -> None:
        self.s.page.evaluate(INTERCEPT, answer)
        if draft:
            self.s.eval("document.body.dataset.draft='1'")

    def act(self, script: str, arg: Any = None) -> list[Any]:
        """Run a click, then read confirms asked, reloads and the hash in the same evaluate: the
        handler's own effects, before the hashchange it causes is routed."""
        outcome: list[Any] = self.s.page.evaluate(
            f"a=>{{{script};return [__asked,__reloads,location.hash];}}", arg
        )
        return outcome

    def link(self, label: str) -> list[Any]:
        return self.act(
            "[...document.querySelectorAll('#run-strip a')].find(l=>l.textContent===a).click()",
            label,
        )

    def notice(self) -> list[Any]:
        return self.act("__built[0].onclick()")

    def keep(self) -> None:
        self.s.eval("window.__kept=document.querySelector('.strip-title')")

    def kept(self) -> bool:
        kept: bool = self.s.eval("document.querySelector('.strip-title')===window.__kept")
        return kept

    def dismiss(self) -> None:
        self.s.click(".strip-close")

    def strip_hidden(self) -> bool:
        return self.s.hidden("run-strip")


OpenWatch = Callable[..., Watch]


@pytest.fixture
def page(browser: Any) -> Iterator[OpenWatch]:
    opened: list[Screen] = []

    def open_watch(
        jobs: list[dict[str, Any]] | None = None,
        permission: str = "granted",
        stored: dict[str, str] | None = None,
        broken: tuple[str, ...] = (),
        runs: tuple[str, ...] = (),
    ) -> Watch:
        listed = list(jobs or [])
        init = OS_NOTICE % (permission, permission)
        if stored:
            init += (
                f"if(window===top)localStorage.setItem({KEY!r},{json.dumps(json.dumps(stored))});"
            )
        for method in broken:
            init += f"Storage.prototype.{method}=()=>{{throw new Error('storage unavailable');}};"
        known = {
            run: {"run": run, "title": "Northbridge Group", "period": "as of 31 March 2025",
                  "issuerKey": "id:nbg", "issuer": "Northbridge Group", "modules": {},
                  "first": None}
            for run in runs
        }  # fmt: skip
        screen = open_app(
            browser,
            "W-Library/cases",
            store={**EMPTY_STORE, "runs": known},
            api={"/api/runs/list": lambda route: json_reply(listed)(route)},
            timers=CAPTURED_TIMERS,
            init=POLL_TIMES + init,
        )
        opened.append(screen)
        until(screen.page, BOOTED)
        return Watch(screen, listed)

    yield open_watch
    release(opened)


def test_a_run_that_finishes_while_the_library_is_open_notifies_once_with_the_run_id_as_tag(
    page: OpenWatch,
) -> None:
    p = page([job()])
    assert p.built() == []
    p.poll(job(state="complete", message="Done", spent_usd="3.10"))
    p.watch()
    assert p.built() == [
        {
            "title": "Issuer Library",
            "options": {"body": "Northbridge Group run complete", "tag": ID},
        }
    ]
    p.intercept()
    assert p.notice() == [0, 1, f"#W-Reports/list?c={ID}"]


def test_the_title_carries_the_run_mark_on_every_route_and_clears_with_no_job(
    page: OpenWatch,
) -> None:
    p = page([job()])
    assert p.mark() == "● 2/4 · "
    for hash_route, name in (
        ("W-Library/cases", "Issuer library"),
        ("W-Settings/workspace", "Settings"),
        ("W-Help/help", "Help"),
    ):
        p.s.go(hash_route)
        assert p.title() == f"● 2/4 · {name} · Issuer Library", hash_route
    assert not p.s.hidden("run-mark")
    assert p.s.text("#run-mark") == "●"
    assert p.s.attr("#run-mark", "aria-hidden") == "true"
    assert p.s.attr("#run-mark", "role") is None
    assert p.s.attr("#run-mark", "aria-label") is None
    assert p.s.attr(RAIL, "aria-label") == "Run activity — run running"
    assert p.s.attr(RAIL, "href") == f"#CP-OS/activity?c={ID}"
    p.poll(job(state="stopped", reason="budget"))
    assert p.title() == "! Help · Issuer Library"
    assert p.s.attr(RAIL, "aria-label") == "Run activity — run stopped"
    p.poll(job(state="complete"))
    assert p.title() == "✓ Help · Issuer Library"
    p.poll()
    # a finished job leaves the list; the page keeps describing the run it saw finish
    assert p.mark() == "✓ "


def test_no_job_at_all_leaves_the_title_unmarked(page: OpenWatch) -> None:
    p = page([])
    p.s.go("W-Help/help")
    assert p.mark() == ""
    assert p.title() == "Help · Issuer Library"


def test_a_job_without_modules_shows_the_mark_without_a_count(page: OpenWatch) -> None:
    p = page([job(modules=None, module_details=None)])
    assert p.mark() == "● "
    assert p.s.attr(RAIL, "aria-label") == "Run activity — run running"


def test_no_notification_is_created_without_permission(page: OpenWatch) -> None:
    for permission in ("denied", "default"):
        p = page([job()], permission=permission)
        p.poll(job(state="failed", reason="provider"))
        assert p.built() == [], permission
        assert p.mark() == "! "


def test_polling_stops_when_no_run_is_active(page: OpenWatch) -> None:
    p = page([job()])
    assert p.s.eval("__started.map(id=>__ms.get(id))") == [30000, 5000]
    p.watch()
    assert p.s.eval("__timers.size") == 2
    p.jobs[:] = [job(state="complete")]
    p.s.eval("__tick()")
    until(p.s.page, "__cleared.length>0")
    assert p.s.eval("[__timers.size,__cleared.map(id=>__ms.get(id))]") == [1, [5000]]
    assert len(p.built()) == 1


def test_a_stopped_run_leads_with_the_sentence_for_its_reason(page: OpenWatch) -> None:
    rows = (
        ("budget", "stopped", BUDGET),
        ("checker", "stopped", CHECKER),
        ("provider", "stopped", PROVIDER),
        ("interrupted", "interrupted", INTERRUPTED),
        ("ruling", "failed", "Failed: a provider ruling or pause is in force."),
    )
    for reason, state, sentence in rows:
        p = page([job()])
        later = job(state=state, reason=reason, message="detail text")
        p.poll(later)
        assert p.built()[0]["options"]["body"] == f"Northbridge Group: {sentence}", reason
        assert p.call("stopText", later) == f"{sentence} detail text", reason
    p = page([job()])
    other = job(state="failed", reason="other", message="plain message")
    p.poll(other)
    assert p.built()[0]["options"]["body"] == "Northbridge Group run failed"
    assert p.call("stopText", other) == "Failed: plain message"


def test_a_repairing_module_shows_its_turn_and_the_rejected_draft(page: OpenWatch) -> None:
    p = page()
    rows = (
        ({"module": "CP-2", "step": "running", "turn": 2, "max_turns": 24},
         "running Title CP-2, turn 2 of 24"),
        ({"module": "CP-2", "step": "repairing", "turn": 3, "max_turns": 24},
         "repairing Title CP-2 after a rejected draft, turn 3 of 24"),
        ({"step": "delivering"}, "delivering the report"),
        ({"module": "CP-1", "step": "started"}, "running Title CP-1 (2 of 4)"),
        ({"module": "CP-1", "step": "accepted"}, "Title CP-1 accepted (2 of 4)"),
    )  # fmt: skip
    for progress, text in rows:
        described = p.s.page.evaluate(
            "([s,m])=>describeModule(s,m,id=>'Title '+id)",
            [{"state": "running", "progress": progress}, MODULES],
        )
        assert described == text


def test_a_finished_run_states_spend_against_a_known_cap_and_spend_alone_for_an_unknown_cap(
    page: OpenWatch,
) -> None:
    p = page()
    rows = (
        ({"state": "stopped", "spent_usd": "9.90", "progress": {"cap_usd": "10.00"}},
         "Recorded spend: USD 9.90 of a USD 10.00 cap"),
        ({"state": "failed", "progress": {"spent_usd": "9.90", "cap_usd": "10"}},
         "Recorded spend: USD 9.90 of a USD 10 cap"),
        ({"state": "stopped", "spent_usd": "9.90", "progress": {}}, "Recorded spend: USD 9.90"),
        ({"state": "stopped", "spent_usd": "unknown", "progress": {"cap_usd": "10"}},
         "Recorded spend could not be read; it may be above zero."),
    )  # fmt: skip
    for status, text in rows:
        assert p.call("spendText", status) == text


def test_the_spend_line_states_the_cap_and_the_held_amount_while_the_run_reports_them(
    page: OpenWatch,
) -> None:
    p = page()
    progress = {"spent_usd": "0.42", "held_usd": "1.86", "cap_usd": "10.00"}
    full = {"state": "running", "progress": progress}
    assert p.call("spendText", full) == (
        "Recorded spend: USD 0.42 of a USD 10.00 cap; the next call holds USD 1.86"
    )
    spent = {"state": "running", "progress": {"spent_usd": "0.42"}}
    assert p.call("spendText", spent) == "Recorded spend: USD 0.42"


def test_a_notification_click_with_a_run_draft_open_asks_before_leaving_it(
    page: OpenWatch,
) -> None:
    for answer, reloads, hash_route in (
        (True, 1, f"#W-Reports/list?c={ID}"),
        (False, 0, "#W-Library/cases"),
    ):
        p = page([job()])
        p.poll(job(state="complete"))
        p.intercept(answer, draft=True)
        assert p.notice() == [1, reloads, hash_route], answer


def test_the_run_list_request_says_whether_the_tab_can_show_the_browser_notice(
    page: OpenWatch,
) -> None:
    for permission, url in (
        ("granted", "/api/runs/list"),
        ("denied", "/api/runs/list?notify=0"),
        ("default", "/api/runs/list?notify=0"),
    ):
        p = page([job()], permission=permission)
        urls = [c["url"] for c in p.s.calls() if c["url"].startswith("/api/runs/list")]
        assert urls == [url], permission


def test_the_strip_is_the_polite_live_region_at_the_top_of_the_page_and_empty_with_nothing_to_show(
    page: OpenWatch,
) -> None:
    p = page([])
    assert p.strip_hidden()
    assert p.s.attr("#run-strip", "role") == "status"
    assert p.s.eval(
        "(s=>s.parentElement.querySelector('.issuer').previousElementSibling===s)"
        "(document.getElementById('run-strip'))"
    )


def test_a_running_run_shows_the_brand_strip_with_the_accepted_count_and_one_action(
    page: OpenWatch,
) -> None:
    p = page([job()])
    assert not p.strip_hidden()
    assert p.s.attr("#run-strip", "data-tone") == "brand"
    assert p.parts() == {
        "title": "Run running · Northbridge Group",
        "lines": ["2 of 4 modules accepted"],
        "actions": [ACTIVITY],
    }
    assert p.s.attr(".strip-icon", "data-icon") == "activity"
    assert p.s.attr(".strip-close", "aria-label") == "Dismiss run notice"
    assert p.s.attr(".strip-close", "title") == "Dismiss"


def test_a_running_run_without_counts_falls_back_to_the_module_text_or_to_no_text(
    page: OpenWatch,
) -> None:
    progress = {"module": "CP-2", "step": "running", "turn": 2, "max_turns": 24}
    p = page([job(progress=progress)])
    assert p.parts()["lines"] == ["running Title CP-2, turn 2 of 24"]
    p.poll(job(modules=None, module_details=None, progress={}))
    assert p.parts()["lines"] == []


def test_a_stopped_failed_or_interrupted_run_shows_the_amber_strip_with_sentence_spend_and_resume(
    page: OpenWatch,
) -> None:
    rows = (
        ("stopped", "budget", "Stopped", BUDGET),
        ("failed", "provider", "Failed", PROVIDER),
        ("interrupted", "interrupted", "Interrupted", INTERRUPTED),
    )
    for state, reason, word, sentence in rows:
        p = page([job(state=state, reason=reason, message="", spent_usd="0.42")])
        assert p.s.attr("#run-strip", "data-tone") == "amber", state
        assert p.s.attr(".strip-icon", "data-icon") == "triangle-alert", state
        assert p.parts() == {
            "title": f"Run {word.lower()} · Northbridge Group",
            "lines": [sentence, "Recorded spend: USD 0.42 of a USD 10.00 cap"],
            "actions": [ACTIVITY, ["Resume", f"#W-NewRun/run?resume={ID}"]],
        }, state


def test_a_stop_with_module_codes_in_its_engine_message_never_puts_them_in_the_browser_notice(
    page: OpenWatch,
) -> None:
    p = page([job()])
    p.poll(job(state="failed", reason="checker", message="CP-3 handoff rejected; CP-OS stopped"))
    body = p.built()[0]["options"]["body"]
    assert body == f"Northbridge Group: {CHECKER}"
    assert "CP-" not in body
    q = page([job()])
    q.poll(job(state="stopped", reason="budget", issuer=None))
    assert q.built()[0]["options"]["body"] == BUDGET
    r = page([job(issuer=None)])
    r.poll(job(state="complete", issuer=None))
    assert r.built()[0]["options"]["body"] == "The run complete"


def test_a_ruling_stop_is_not_resumable_anywhere_the_strip_offers_activity_only(
    page: OpenWatch,
) -> None:
    p = page([job(state="failed", reason="ruling", message="")])
    assert p.parts()["actions"] == [ACTIVITY]
    assert p.call("resumable", {"state": "failed", "reason": "ruling"}) is False
    assert p.call("resumable", {"state": "failed", "reason": "provider"}) is True
    for state in ("reviewed", "complete", "running", "weird", None):
        status = {} if state is None else {"state": state}
        assert p.call("resumable", status) is False, str(state)
    for state in ("stopped", "failed", "interrupted"):
        assert p.call("resumable", {"state": state}) is True, state


def test_a_complete_run_shows_the_grey_strip_with_a_tick_and_view_reports_only(
    page: OpenWatch,
) -> None:
    p = page([job(state="complete")])
    assert p.s.attr("#run-strip", "data-tone") == "grey"
    assert p.s.attr(".strip-icon", "data-icon") == "circle-check"
    assert p.parts() == {
        "title": "Run complete · Northbridge Group",
        "lines": [],
        "actions": [["View reports", f"#W-Reports/list?c={ID}"]],
    }


def test_at_load_the_active_job_wins_else_the_newest_not_running_and_clicks_do_not_clear_it(
    page: OpenWatch,
) -> None:
    older = stopped(id=ID2)
    done = job(state="complete")
    p = page([older, done])
    assert p.parts()["title"] == "Run stopped · Northbridge Group"
    assert p.mark() == "! "
    assert p.parts()["actions"][0][1] == f"#CP-OS/activity?c={ID2}"
    p = page([done, job(id=ID2)])
    assert p.parts()["title"] == "Run running · Northbridge Group"
    assert p.mark() == "● 2/4 · "
    p = page([done])
    assert not p.strip_hidden()
    assert p.mark() == "✓ "
    assert not p.s.hidden("run-mark")
    assert p.built() == []
    # a notification click for a finished run leaves the notice in place
    p = page([job()])
    p.poll(done)
    p.intercept()
    p.notice()
    until(p.s.page, "current.module==='W-Reports'")
    assert not p.strip_hidden()


def test_the_rail_mark_takes_its_colour_state_and_glyph_from_the_run_and_is_not_announced(
    page: OpenWatch,
) -> None:
    rows = (
        ({}, "●", "running"),
        ({"state": "complete"}, "✓", "complete"),
        ({"state": "stopped", "reason": "budget"}, "!", "stopped"),
        ({"state": "failed", "reason": "provider"}, "!", "stopped"),
        ({"state": "interrupted", "reason": "interrupted"}, "!", "stopped"),
    )
    for over, glyph, state in rows:
        p = page([job(**over)])
        shown = [
            p.s.text("#run-mark"),
            p.s.attr("#run-mark", "data-state"),
            p.s.attr("#run-mark", "aria-hidden"),
            p.s.attr("#run-mark", "role") is not None,
            p.s.hidden("run-mark"),
        ]
        assert shown == [glyph, state, "true", False, False], json.dumps(over)
        word = over.get("state", "running")
        assert p.s.attr(RAIL, "aria-label") == f"Run activity — run {word}"


def test_a_poll_that_only_moves_the_count_does_not_rebuild_the_strip_a_change_of_state_does(
    page: OpenWatch,
) -> None:
    p = page([job()])
    p.keep()
    p.poll(job(progress={"module": "CP-3", "step": "running", "accepted": 3}))
    assert p.kept()
    assert p.parts()["lines"] == ["3 of 4 modules accepted"]
    p.poll(stopped())
    assert not p.kept()
    assert p.s.attr("#run-strip", "data-tone") == "amber"


def test_dismissing_hides_only_that_jobs_strip_until_its_state_changes_and_is_stored_per_viewer(
    page: OpenWatch,
) -> None:
    p = page([stopped()])
    p.dismiss()
    assert p.strip_hidden()
    assert not p.s.hidden("run-mark"), "the rail mark is not affected by Dismiss"
    assert p.mark() != ""
    assert p.stored() == {ID: "stopped"}
    p.watch()
    assert p.strip_hidden()
    p.poll(job(state="failed", reason="provider", message=""))
    assert not p.strip_hidden(), "a changed state shows the notice again"


def test_a_stored_dismissal_is_read_at_load(page: OpenWatch) -> None:
    assert page([stopped()], stored={ID: "stopped"}).strip_hidden()
    assert not page([stopped()], stored={ID: "running"}).strip_hidden()


def test_without_usable_storage_a_dismissal_holds_for_the_page_and_is_warned_about(
    page: OpenWatch,
) -> None:
    p = page([stopped()], broken=("getItem", "setItem"))
    assert not p.strip_hidden(), "unreadable storage shows the notice"
    p.dismiss()
    assert p.strip_hidden()
    p.watch()
    assert p.strip_hidden()
    warnings: list[str] = p.s.eval("__warnings")
    assert any("could not be read" in w or "could not be saved" in w for w in warnings)


def test_the_strip_links_go_to_that_job_and_ask_before_leaving_a_run_draft(
    page: OpenWatch,
) -> None:
    p = page([stopped()])
    p.intercept()
    assert p.link("View activity") == [0, 1, f"#CP-OS/activity?c={ID}"]
    resume = p.link("Resume")
    assert resume == [0, 1, f"#W-NewRun/run?resume={ID}"], "Resume reads the live status"
    for answer, hash_route, count in (
        (False, "#W-Library/cases", 0),
        (True, f"#CP-OS/activity?c={ID}", 1),
    ):
        q = page([stopped()])
        q.intercept(answer, draft=True)
        assert q.link("View activity") == [1, count, hash_route]


def test_plain_state_words_replace_raw_states_and_bare_module_codes_are_named(
    page: OpenWatch,
) -> None:
    p = page()
    named = [{"id": "CP-1", "title": "Financial analysis"}]

    def text(state: str, message: str, **extra: str) -> dict[str, Any]:
        return {"state": state, "message": message, "module_details": named, **extra}

    running = {"state": "running", "message": "Working"}
    cases: list[tuple[list[Any], str]] = [
        ([text("failed", "boom")], "Failed: boom"),
        ([text("complete", "Done")], "Complete: Done"),
        ([text("interrupted", "")], "Interrupted"),
        ([text("stopped", "halt")], "Stopped: halt"),
        ([text("weird", "x")], "Not running: x"),
        ([running, True], "Running"),
        ([running], "Running: Working"),
        ([text("failed", "CP-1 rejected; CP-OS stopped; CP-9 unknown")],
         "Failed: Financial analysis (CP-1) rejected; CP-OS stopped; CP-9 unknown"),
        ([text("failed", "Financial analysis (CP-1) rejected")],
         "Failed: Financial analysis (CP-1) rejected"),
        ([text("stopped", "x", reason="budget")], f"{BUDGET} x"),
    ]  # fmt: skip
    for args, expected in cases:
        assert p.call("stopText", *args) == expected


def test_fix_1_dismissing_a_running_strip_hides_only_the_strip_until_the_run_changes_state(
    page: OpenWatch,
) -> None:
    p = page([job()])
    p.dismiss()
    assert p.strip_hidden()
    assert p.stored() == {ID: "running"}
    p.poll(job(progress={"module": "CP-3", "step": "running", "accepted": 3}))
    assert p.strip_hidden(), "a poll in the same state keeps it hidden"
    p.poll(stopped())
    assert not p.strip_hidden(), "the stop shows it again"


def test_fix_1_a_running_job_left_dismissed_does_not_hide_a_newer_state_of_another_job(
    page: OpenWatch,
) -> None:
    p = page([job()], stored={ID: "running"})
    assert p.strip_hidden()
    p.poll(job(id=ID2))
    assert not p.strip_hidden()


def test_fix_2_an_unchanged_state_with_no_supporting_text_updates_in_place_and_does_not_rebuild(
    page: OpenWatch,
) -> None:
    p = page([job(modules=None, module_details=None, progress={})])
    p.keep()
    p.watch()
    p.watch()
    assert p.kept()


def test_final_1_dismissing_the_strip_keeps_the_rail_mark_and_the_title_prefix_of_the_active_run(
    page: OpenWatch,
) -> None:
    p = page([job()])
    p.dismiss()
    assert p.strip_hidden()
    assert not p.s.hidden("run-mark")
    assert p.mark() == "● 2/4 · "


def test_final_1_with_the_newest_stopped_run_dismissed_the_mark_follows_it_and_no_fallback(
    page: OpenWatch,
) -> None:
    older = job(id=ID2, state="failed", message="x")
    p = page([stopped(), older])
    p.dismiss()
    assert p.strip_hidden()
    assert not p.s.hidden("run-mark")
    assert ID in (p.s.attr(RAIL, "href") or "")


def test_final_5_a_poll_adding_the_first_supporting_line_keeps_the_strip_nodes(
    page: OpenWatch,
) -> None:
    p = page([job(modules=[], progress={})])
    p.keep()
    p.poll(job())
    assert p.kept()
    assert "2 of 4 modules accepted" in p.s.text(".strip-text")
    assert p.s.exists(".strip-actions")


def test_the_strip_is_hidden_on_the_run_activity_page_of_its_own_job_and_returns_elsewhere(
    page: OpenWatch,
) -> None:
    p = page([job(state="stopped", reason="budget")], runs=(ID,))
    assert not p.strip_hidden()
    p.s.go(f"CP-OS/activity?c={ID}")
    assert p.strip_hidden()
    assert not p.s.hidden("run-mark"), "the rail mark stays"
    assert p.title().startswith("! "), "the title prefix stays"
    p.s.go("W-Help/help")
    assert not p.strip_hidden()
