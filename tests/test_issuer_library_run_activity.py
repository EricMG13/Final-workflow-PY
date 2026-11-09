"""The Run activity page for an app run: run-activity.test.cjs at final-workflow dd3dfa18.

The Node suite loaded the screens into jsdom with a fetch mock. Here the real app opens
#CP-OS/activity?c=<run> and /api/runs/status and /api/runs/events are answered by synthetic
replies; the run reaches the page through the store, as DESIGN_DATA. Nothing reaches a server
or a provider.
Marked browser: real browser proof.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple

import pytest
from issuer_library_browser import (
    EMPTY_WORKSPACE,
    Reply,
    Screen,
    json_reply,
    open_app,
    release,
    text_reply,
    until,
)

pytestmark = pytest.mark.browser

ID = "web-" + "b" * 32
MODULES = ["CP-0", "CP-1"]
DONE = "!document.getElementById('content').textContent.includes('Loading run activity')"
RETAINED = "No live progress is recorded for this run in this workspace."


class Failure(NamedTuple):
    message: str
    status: int


def status(**over: Any) -> dict[str, Any]:
    base = {
        "id": ID,
        "state": "running",
        "message": "Working",
        "run_available": True,
        "modules": MODULES,
        "module_details": [{"id": m, "title": "Title " + m} for m in MODULES],
        "spent_usd": "0.00",
        "progress": {"module": "CP-1", "step": "running", "turn": 1, "max_turns": 24,
                     "spent_usd": "0.00", "held_usd": "5.73", "cap_usd": "10", "accepted": 1},
    }  # fmt: skip
    return {**base, **over}


EVENTS = [
    {"at": "2026-11-08T09:00:00Z", "event": "module_started", "module": "CP-0"},
    {"at": "2026-11-08T09:00:01Z", "event": "turn", "module": "CP-0", "turn": 1, "max_turns": 24,
     "spent_usd": "0.00", "held_usd": "5.73", "cap_usd": "10"},
    {"at": "2026-11-08T09:00:02Z", "event": "draft_rejected", "module": "CP-0", "writes_left": 2},
    {"at": "2026-11-08T09:00:03Z", "event": "module_accepted", "module": "CP-0"},
    {"at": "2026-11-08T09:00:04Z", "event": "delivery_started"},
    {"at": "2026-11-08T09:00:05Z", "event": "delivered"},
]  # fmt: skip


def log(events: list[dict[str, Any]], complete: bool = True) -> dict[str, Any]:
    return {"events": events, "complete": complete}


def answer(value: Any) -> Reply:
    if isinstance(value, Failure):
        return text_reply(value.message, value.status)
    return json_reply(value)


def run_store(key: str, modules: dict[str, Any]) -> dict[str, Any]:
    run = {"run": key, "title": "Northbridge Group", "period": "as of 31 March 2025",
           "issuerKey": "id:nbg", "issuer": "Northbridge Group", "modules": modules,
           "first": None}  # fmt: skip
    return {"runs": {key: run}, "outputs": {}, "inputs": {}, "pins": {}}


OpenRun = Callable[..., Screen]


@pytest.fixture
def activity(browser: Any) -> Iterator[OpenRun]:
    opened: list[Screen] = []

    def open_activity(
        key: str = ID,
        live: Any = None,
        events: Any = None,
        modules: dict[str, Any] | None = None,
        reports: list[dict[str, Any]] | None = None,
    ) -> Screen:
        api = {
            "/api/runs/status": answer(status() if live is None else live),
            "/api/runs/events": answer(log(EVENTS) if events is None else events),
        }
        screen = open_app(
            browser,
            f"CP-OS/activity?c={key}",
            store=run_store(key, modules or {}),
            workspace={**EMPTY_WORKSPACE, "reports": reports or []},
            api=api,
        )
        opened.append(screen)
        until(screen.page, DONE)
        return screen

    yield open_activity
    release(opened)


def rows(screen: Screen) -> list[str]:
    return [t.strip() for t in screen.texts(".activity-log tbody tr")]


def test_the_run_activity_page_lists_each_event_in_order_with_its_text(activity: OpenRun) -> None:
    p = activity()
    assert rows(p) == [
        "8 November 2026 · 09:00:00Started Title CP-0",
        "09:00:01Turn 1 of 24 · spend USD 0.00 of USD 10; this call holds USD 5.73",
        "09:00:02Draft of Title CP-0 rejected · 2 writes left",
        "09:00:03Accepted Title CP-0",
        "09:00:04Delivery started",
        "09:00:05Report delivered",
    ]
    lines = [t.strip() for t in p.texts(".activity-summary .summary-line")]
    assert lines == ["Running", "Running Title CP-1, turn 1 of 24."]
    assert p.text("#run-activity h2").strip() == "Run record · " + ID
    assert p.text(".activity-log caption").strip() == "Events (UTC)"
    assert p.exists(".activity-flow")
    assert not p.exists("#run-activity .caution")


def test_one_write_left_reads_in_the_singular_and_an_unknown_event_is_shown_as_written(
    activity: OpenRun,
) -> None:
    events = [
        {"at": "2026-11-08T09:00:02Z", "event": "draft_rejected", "module": "CP-1",
         "writes_left": 1},
        {"at": "2026-11-08T09:00:03Z", "event": "<b>odd</b>"},
        {"at": "2026-11-08T09:00:04Z", "event": "stopped", "reason": "other"},
    ]  # fmt: skip
    p = activity(events=log(events))
    assert rows(p) == [
        "8 November 2026 · 09:00:02Draft of Title CP-1 rejected · 1 write left",
        "09:00:03<b>odd</b>",
        "09:00:04Stopped (other)",
    ]
    assert not p.exists(".activity-log b")


def test_a_stopped_run_leads_with_its_stop_sentence(activity: OpenRun) -> None:
    stopped = status(state="stopped", reason="budget", message="cap reached", spent_usd="9.90")
    stop = {"at": "2026-11-08T09:00:00Z", "event": "stopped", "reason": "budget"}
    p = activity(live=stopped, events=log([stop]))
    budget = p.eval("STOP_COPY.budget")
    paragraphs = [t.strip() for t in p.texts("#run-activity p")]
    assert paragraphs[0].startswith(budget), paragraphs[0]
    assert rows(p) == ["8 November 2026 · 09:00:00" + budget]
    assert paragraphs[1] == "Recorded spend: USD 9.90 of a USD 10 cap"


def test_an_incomplete_log_says_so(activity: OpenRun) -> None:
    p = activity(events=log(EVENTS[:2], complete=False))
    assert len(rows(p)) == 2
    assert p.text("#run-activity .caution").strip() == (
        "The record is incomplete: the log was cut or stopped mid-write."
    )


def test_a_run_without_a_log_shows_the_no_events_line(activity: OpenRun) -> None:
    p = activity(events=log([]))
    assert not p.exists(".activity-log")
    assert p.text("#run-activity .hint").strip() == "No events were recorded for this run."


def test_a_failed_fetch_says_the_record_could_not_be_loaded_and_keeps_the_raw_detail_closed(
    activity: OpenRun,
) -> None:
    p = activity(events=Failure("boom", 500))
    lines = p.eval(
        "(()=>{const note=document.querySelector('#run-activity .caution'),"
        "details=document.querySelector('#run-activity details');"
        "return {first:(note.querySelector('p')||note.firstChild).textContent.trim(),"
        "open:details.open,summary:details.querySelector('summary').textContent.trim(),"
        "detail:details.textContent,outside:note.textContent.replace(details.textContent,'')};})()"
    )
    assert (
        lines["first"] == "Could not load this run's live record. Reload the library to try again."
    )
    assert lines["open"] is False and lines["summary"] == "Technical detail"
    assert re.search(r"boom", lines["detail"])
    assert not re.search(r"boom", lines["outside"])
    assert not p.exists(".activity-log")


def test_a_404_for_the_live_record_shows_the_retained_record_view_never_the_raw_404_text(
    activity: OpenRun,
) -> None:
    p = activity(live=Failure("404 page not found\n", 404), events=log([]))
    text = p.content()
    assert re.search(r"Retained record · ", text)
    assert re.search(re.escape(RETAINED), text)
    assert not re.search(r"404|page not found|Could not load", text)
    assert not p.exists("#run-activity")
    assert p.exists(".activity-flow"), "the flow stays"


def test_a_404_status_with_a_recorded_event_log_shows_the_retained_heading_the_log_and_last_spend(
    activity: OpenRun,
) -> None:
    turn = {"at": "2026-11-08T09:10:00Z", "event": "turn", "module": "CP-0", "turn": 2,
            "max_turns": 24,
            "spent_usd": "2.40", "held_usd": "1.00", "cap_usd": "10"}  # fmt: skip
    missing = Failure("404 page not found\n", 404)
    p = activity(live=missing, events=log([EVENTS[0], EVENTS[1], turn]))
    text = p.content()
    assert re.search(r"Retained record · ", text)
    assert not re.search(re.escape(RETAINED), text)
    assert p.count(".activity-log tbody tr") == 3
    assert p.exists("#content .table-scroll .activity-log")
    assert re.search(r"Last recorded spend: USD 2\.40", text)
    assert not re.search(r"404|page not found", text)
    none = activity(live=Failure("404", 404), events=log([]))
    assert re.search(re.escape(RETAINED), none.content())
    lost = activity(live=Failure("404", 404), events=Failure("boom", 500))
    assert re.search(re.escape(RETAINED), lost.content())


def test_a_404_landing_after_the_reader_left_run_activity_neither_throws_nor_writes_on_new_page(
    browser: Any,
) -> None:
    pending: list[Any] = []
    answered = (
        "const f=window.fetch;window.__answered=0;window.fetch=(u,o)=>{const p=f(u,o);"
        "if(String(u).startsWith('/api/runs/'))p.then(r=>r.clone().text())"
        ".then(()=>setTimeout(()=>{window.__answered++},0));return p;};"
    )
    screen = open_app(
        browser,
        f"CP-OS/activity?c={ID}",
        api={"/api/runs/status": pending.append, "/api/runs/events": answer(log([]))},
        store=run_store(ID, {}),
        init=answered,
    )
    events = "window.__calls.filter(c=>c.url.startsWith('/api/runs/events')).length"
    after = "new Promise(resolve=>setTimeout(resolve,0))"
    try:
        for _ in range(250):
            if pending:
                break
            screen.page.wait_for_timeout(20)
        else:
            raise AssertionError("the status request was never made")
        screen.page.evaluate("location.hash='#W-Library/cases'")
        until(screen.page, "current.module==='W-Library'")
        pending[0].fulfill(status=404, body="404 page not found", content_type="text/plain")
        until(screen.page, "window.__answered>0")
        screen.page.evaluate(after)
        if screen.page.evaluate(events):
            until(screen.page, "window.__answered>1")
        screen.page.evaluate(after)
        assert screen.errors == []
        assert "Live progress and spend are recorded only" not in screen.content()
    finally:
        screen.close()


def test_a_404_on_the_events_request_alone_is_also_the_retained_record(activity: OpenRun) -> None:
    p = activity(events=Failure("404 page not found", 404))
    assert re.search(re.escape(RETAINED), p.content())
    assert not re.search(r"404", p.content())


def test_the_log_sits_in_the_bordered_content_table_card_and_only_the_summary_line_is_live(
    activity: OpenRun,
) -> None:
    p = activity()
    assert p.exists("#run-activity .table-scroll table.activity-log"), "the log is inside the card"
    assert p.eval("document.querySelector('#run-activity .table-scroll').tabIndex") == 0
    assert p.eval("document.getElementById('run-activity').hasAttribute('aria-live')") is False
    assert p.attr(".activity-summary", "aria-live") == "polite"
    assert p.count("#run-activity [aria-live]") == 1
    assert p.text(".activity-log td").strip() == "8 November 2026 · 09:00:00"


def test_a_stopped_app_run_offers_resume_this_run_through_new_runs_resume_route_other_runs_do_not(
    activity: OpenRun,
) -> None:
    def stopped(**over: Any) -> dict[str, Any]:
        return status(**{"state": "stopped", "reason": "budget", "spent_usd": "9.90", **over})

    p = activity(live=stopped(), events=log(EVENTS[:1]))
    links = p.eval(
        "[...document.querySelectorAll('#run-activity a')]"
        ".filter(a=>a.textContent.trim()==='Resume this run').map(a=>a.getAttribute('href'))"
    )
    assert links == [f"#W-NewRun/run?resume={ID}"]
    for over in [
        {"reason": "ruling", "state": "failed"},
        {"state": "running"},
        {"state": "complete"},
    ]:
        q = activity(live=stopped(**over), events=log(EVENTS[:1]))
        assert not any("Resume" in t for t in q.texts("#run-activity a")), over


def test_a_retained_run_keeps_the_retained_record_text(activity: OpenRun) -> None:
    p = activity(key="tdg-002")
    assert re.search(re.escape(RETAINED), p.content())
    assert not p.exists("#run-activity")
    boot = ["/api/catalogue", "/api/runs/list?notify=0", "/api/workspace"]
    assert sorted(c["url"] for c in p.calls()) == boot, "the page asks for nothing but boot's reads"


def test_final_2_the_retained_record_sentence_makes_no_claim_about_cost(activity: OpenRun) -> None:
    missing = Failure("404 page not found", 404)
    p = activity(live=missing, events=missing)
    assert re.search(re.escape(RETAINED), p.content())
    assert not re.search(r"No live progress or cost", p.content())


def test_final_4_the_activity_log_card_is_a_named_region(activity: OpenRun) -> None:
    p = activity()
    assert p.attr("#run-activity .table-scroll", "role") == "region"
    assert p.attr("#run-activity .table-scroll", "aria-label") == "Run events"


def test_the_date_shows_on_the_first_row_and_again_when_it_changes_a_missing_time_stays_a_dash(
    activity: OpenRun,
) -> None:
    events = [
        {"at": "2026-11-08T23:59:58Z", "event": "module_started", "module": "CP-0"},
        {"at": "2026-11-08T23:59:59Z", "event": "delivery_started"},
        {"event": "delivered"},
        {"at": "2026-11-09T00:00:01Z", "event": "delivered"},
        {"at": "2026-11-09T00:00:02Z", "event": "delivered"},
    ]
    p = activity(events=log(events))
    times = [t.strip() for t in p.texts(".activity-log tbody td:first-child")]
    assert times == [
        "8 November 2026 · 23:59:58",
        "23:59:59",
        "—",
        "9 November 2026 · 00:00:01",
        "00:00:02",
    ]


def test_empty_counts_carry_no_link_to_an_empty_view(activity: OpenRun) -> None:
    p = activity()
    flow = p.text(".activity-flow").strip()
    assert re.search(r"0 saved outputs", flow)
    assert re.search(r"No report was built from this run’s files\.", flow)
    assert p.count(".activity-flow a") == 0


def test_a_run_with_saved_outputs_and_a_report_keeps_both_links(activity: OpenRun) -> None:
    report = {"id": "r1", "label": "Credit report", "builtFrom": [{"run": ID}]}
    p = activity(modules={"CP-0": {"outputs": ["o1", "o2"]}}, reports=[report])
    assert [t.strip() for t in p.texts(".activity-flow a")] == [
        "Inspect retained outputs",
        "View reports",
    ]
    assert re.search(
        r"2 saved outputs.*1 report built from this run’s files\.", p.text(".activity-flow").strip()
    )
