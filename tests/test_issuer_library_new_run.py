"""New run, the cases P added to new-run.test.cjs (final-workflow dd3dfa18): stops, order, resume.

The Node suite drove views.js, actions.js and screen.js in jsdom with a stub fetch and timers. Here
the real New run screen opens (NewRun in test_issuer_library_app.py, which also holds the cases the
earlier port covered) and each reply is a synthetic API answer. Waits are on page conditions.
Synthetic data only; nothing reaches a server or a provider. Marked browser: real browser proof.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from issuer_library_browser import open_app, release, until
from test_issuer_library_app import (
    ID,
    ID2,
    IDENTITY,
    ROW_DONE,
    ROW_RUNNING,
    NewRun,
    review_reply,
)

pytestmark = pytest.mark.browser

SPACED = " "
ROW_STOPPED: dict[str, Any] = {
    "id": ID, "state": "stopped", "reason": "budget", "message": "CP-1 stopped.",
    "run_available": True, "issuer": "Northbridge Group", "pathway": "covenant_refinancing",
    "as_of": "2025-03-31", "spent_usd": "4.00", "modules": ["CP-0", "CP-1"],
    "module_details": [
        {"id": "CP-0", "title": "Source readiness"},
        {"id": "CP-1", "title": "Financial analysis"},
    ],
    "progress": {"module": "CP-1", "step": "stopped", "accepted": 1, "turn": 2, "max_turns": 32,
                 "spent_usd": "3.10", "held_usd": "1.60", "cap_usd": "10.00"},
}  # fmt: skip
HINT = (
    "This cap applies to the resumed run's own model calls; {}"
    "recorded for the stopped run is not counted against it."
)
WITH_SPEND = HINT.format("the USD 4.00 ")
WITHOUT_SPEND = HINT.format("spend ")
RESUMED = "Resumes run WEB-AAAAAAAA."
REFUSED = "The stopped run's inputs are no longer in the workspace"
# The frame is sandboxed, so it echoes what it receives and the page records the echo.
FRAME_ECHO = """
if(window!==top){addEventListener('message',e=>{if(e.source!==parent)return;
  if(e.data?.type==='cpos:names')parent.postMessage({type:'echo:names',names:e.data.names},'*');
  if(e.data?.type==='echo:flush')parent.postMessage({type:'echo:flushed'},'*');});}
else{window.__names=[];window.__flushed=0;addEventListener('message',e=>{
  if(e.data?.type==='echo:names')window.__names.push(e.data.names);
  if(e.data?.type==='echo:flushed')window.__flushed++;});}
"""
HOLD_STATUS = """()=>{window.__held=[];window.__asked=[];window.__read=false;
const inner=window.fetch;window.fetch=(url,options)=>{
if(!String(url).startsWith('/api/runs/status'))return inner(url,options);
window.__asked.push(decodeURIComponent(String(url).split('id=')[1]));
return new Promise(resolve=>window.__held.push(()=>resolve({ok:true,json:async()=>{
window.__read=true;return{state:'complete',message:'Done A',run_available:true,
progress:{module:'CP-1',step:'accepted'}};}})));};}"""
OPEN_ROW = (
    "id=>{const b=[...document.querySelectorAll('#recent-jobs tbody th button')];"
    "(id?b.find(x=>x.title===id):b[0]).click();}"
)
CAP = "document.getElementById('resume-budget').value"
NOTE = "document.getElementById('new-run-message').textContent"


@pytest.fixture
def new_run(browser: Any) -> Iterator[Callable[..., NewRun]]:
    opened_runs: list[NewRun] = []

    def factory(**options: Any) -> NewRun:
        opened_runs.append(NewRun(browser, **options))
        return opened_runs[-1]

    yield factory
    release([run.screen for run in opened_runs])


def drop(row: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in keys}


def launched(new_run: Any, status: dict[str, Any]) -> NewRun:
    """Launch, then wait for the first status reply to be drawn: the list and lines it reads."""
    run: NewRun = new_run(status=status)
    run.launch()
    until(run.page, "document.querySelectorAll('#run-progress .summary-line').length>0")
    until(run.page, "document.querySelectorAll('#module-stages li').length>0")
    return run


def open_row(run: NewRun, run_id: str | None = None) -> None:
    """Click a recent-runs row once the list has drawn it (the list is fetched after the visit)."""
    want = json.dumps(run_id)
    shown = "[...document.querySelectorAll('#recent-jobs tbody th button')]"
    until(run.page, f"{shown}.some(b=>{want}===null||b.title==={want})")
    run.page.evaluate(OPEN_ROW, run_id)
    run.settle()


def opened(new_run: Any, row: dict[str, Any], reply: dict[str, Any] | None = None) -> NewRun:
    run: NewRun = new_run(rows=[row], status=row)
    run.resume = reply or run.resume
    run.revisit()
    open_row(run)
    return run


def resume(run: NewRun, cap: str) -> None:
    """Enter a cap, ask to resume, and wait until the reply is a review or a refusal message."""
    run.screen.set_value("#resume-budget", cap)
    run.click("resume-run")
    until(run.page, "window.__calls.some(c=>c.url==='/api/runs/resume')")
    until(
        run.page,
        f"!document.getElementById('review-step').hidden||({NOTE}!==''&&!{NOTE}.startsWith('Checking'))",
    )


def notes(run: NewRun) -> list[str]:
    return run.screen.texts("#run-review .matrix-note")


def test_opening_a_row_waits_for_a_list_reply_that_is_still_in_flight(new_run: Any) -> None:
    """The failing CI case, forced: the list answers after the helper's old 50 ms settle."""
    run = new_run(rows=[])

    def slowly(route: Any) -> None:
        run.page.wait_for_timeout(400)
        route.fallback()

    run.page.route("**/api/runs/list*", slowly)
    run.rows = [ROW_STOPPED]
    run.page.evaluate("location.hash='#W-Library/cases'")
    run.page.evaluate("location.hash='#W-NewRun/run'")
    run.settle()
    assert run.screen.attrs("#recent-jobs tbody th button", "title") == []
    open_row(run)
    assert run.hidden("progress-step") is False
    assert run.text("resume-hint") == WITH_SPEND


def test_a_stop_between_modules_keeps_the_accepted_module_ticked(new_run: Any) -> None:
    progress = {"step": "stopped", "stopped_during": "accepted", "module": "CP-0", "accepted": 1}
    run = launched(
        new_run,
        {"state": "failed", "reason": "provider", "message": "handoff refused",
         "progress": progress, "run_available": True, "id": ID},
    )  # fmt: skip
    until(run.page, "document.querySelectorAll('#run-progress .summary-line').length>1")
    assert run.progress()[1] == f"Stopped after Source readiness{SPACED}(1{SPACED}of{SPACED}2)."
    stages = run.stages()
    assert [s["status"] for s in stages] == ["complete", "incomplete", "incomplete"]
    assert stages[0]["note"] == "Accepted" and stages[0]["img"]
    assert [s["stopped"] for s in stages] == [False, False, False]


def test_a_budget_stop_names_the_module_it_stopped_in(new_run: Any) -> None:
    progress = {"step": "stopped", "stopped_during": "running", "module": "CP-1", "accepted": 1,
                "turn": 2, "max_turns": 32, "spent_usd": "8.90", "held_usd": "1.60",
                "cap_usd": "10"}  # fmt: skip
    run = launched(
        new_run,
        {"state": "stopped", "reason": "budget", "message": "next call over cap",
         "started_at": "2026-11-08T09:00:00Z", "spent_usd": "8.90", "progress": progress,
         "run_available": True, "id": ID},
    )  # fmt: skip
    first, second, last = run.stages()
    assert first["status"] == "complete" and first["note"] == "Accepted"
    assert second["status"] == "current" and second["stopped"] and second["note"] == "Stopped here"
    assert second["current"] == "step"
    assert last["status"] == "incomplete" and not last["stopped"] and last["current"] is None


def test_a_stop_in_delivery_marks_no_module_stopped(new_run: Any) -> None:
    progress = {"module": "CP-1", "step": "stopped", "stopped_during": "delivering",
                "accepted": 2, "spent_usd": "0.42"}  # fmt: skip
    run = launched(
        new_run,
        {"state": "failed", "message": "delivery refused", "progress": progress,
         "run_available": True, "id": ID},
    )  # fmt: skip
    assert run.progress() == [
        "Failed: delivery refused",
        "Stopped while delivering the report.",
    ]
    stages = run.stages()
    assert [s["status"] for s in stages] == ["complete", "complete", "incomplete"]
    assert not any(s["stopped"] for s in stages[:2])
    assert stages[2]["stopped"] and stages[2]["note"] == "Stopped" and not stages[2]["img"]


def test_recent_runs_are_newest_started_first_whatever_their_state(new_run: Any) -> None:
    older = {**ROW_RUNNING, "id": "web-" + "1" * 32, "started_at": "2026-11-06T09:00:00Z"}
    newest = {**ROW_DONE, "id": "web-" + "2" * 32, "started_at": "2026-11-09T09:00:00Z"}
    undated = drop({**ROW_DONE, "id": "web-" + "3" * 32, "issuer": "Undated Co"}, "started_at")
    run = new_run(rows=[older, undated, ROW_DONE, newest])
    run.revisit()
    until(run.page, "document.querySelectorAll('#recent-jobs tbody th button').length==4")
    assert run.screen.attrs("#recent-jobs tbody th button", "title") == [
        newest["id"], ROW_DONE["id"], older["id"], undated["id"],
    ]  # fmt: skip
    labels = run.screen.texts("#recent-jobs tbody th button")
    assert labels[0] == "Southport Holdings · WEB-22222222 · 9 November 2026"
    assert labels[-1] == "Undated Co · WEB-33333333"


def test_the_context_form_is_sent_the_module_names_when_it_reports_ready(
    browser: Any,
) -> None:
    screen = open_app(browser, "W-NewRun/run", init=FRAME_ECHO)
    page = screen.page
    flushed = 0

    def say(from_form: bool) -> list[dict[str, Any]]:
        nonlocal flushed
        page.evaluate(
            "from=>{const f=document.getElementById('context-editor').contentWindow;"
            "window.dispatchEvent(new MessageEvent('message',{source:from?f:window,"
            "data:{type:'cpos:ready',ready:!from}}));f.postMessage({type:'echo:flush'},'*');}",
            from_form,
        )
        flushed += 1
        until(page, f"window.__flushed=={flushed}")
        names: list[dict[str, Any]] = page.evaluate("window.__names")
        return names

    try:
        until(page, "window.__names.length>0")
        say(False)
        page.evaluate("window.__names.length=0")  # the form's own ready, already answered
        assert say(False) == []
        (names,) = say(True)
        assert names["CP-0"] == "Source readiness"
        assert all(isinstance(value, str) for value in names.values())
    finally:
        release([screen])


def test_a_status_reply_for_a_run_the_reader_has_left_changes_nothing(new_run: Any) -> None:
    other = "web-" + "c" * 32
    run = new_run(rows=[ROW_RUNNING, {**ROW_RUNNING, "id": other, "issuer": "Eastgate Plc"}])
    run.revisit()
    run.page.evaluate(HOLD_STATUS)
    open_row(run, ID)
    until(run.page, "window.__asked.length>0")
    assert run.page.evaluate("window.__asked.at(-1)") == ID
    open_row(run, other)
    run.page.evaluate("window.__held.shift()()")
    until(run.page, "window.__read")
    assert "Done A" not in run.text("run-progress")
    before = run.page.evaluate("window.__asked.length")
    run.tick()
    until(run.page, f"window.__asked.slice({before}).includes({other!r})")


def test_after_a_budget_stop_the_cap_starts_at_the_previous_cap(new_run: Any) -> None:
    run = opened(new_run, ROW_STOPPED)
    assert run.screen.eval(CAP) == "10.00"
    assert run.disabled("resume-run") is False
    assert run.text("resume-hint") == WITH_SPEND and run.hidden("resume-hint") is False
    assert run.screen.attr("#resume-budget", "aria-describedby") == "resume-hint"
    for value, enabled in [("", False), ("0", False), ("0.00", False), ("-5", False),
                           ("1e1", False), ("abc", False), ("3", True), ("4.00", True),
                           ("0.01", True), ("12.50", True)]:  # fmt: skip
        run.screen.set_value("#resume-budget", value)
        assert run.disabled("resume-run") is not enabled, f"value {value!r}"
    resume(run, "3")
    assert run.posted("/api/runs/resume")[0]["cap_usd"] == "3"


@pytest.mark.parametrize(
    "row", [{**ROW_STOPPED, "spent_usd": "unknown"}, drop(ROW_STOPPED, "spent_usd")]
)
def test_the_hint_says_so_when_the_recorded_spend_cannot_be_read(
    new_run: Any, row: dict[str, Any]
) -> None:
    run = opened(new_run, row)
    assert run.text("resume-hint") == WITHOUT_SPEND
    assert run.disabled("resume-run") is False


def test_the_cap_starts_at_the_stopped_runs_recorded_cap(new_run: Any) -> None:
    progress = {**ROW_STOPPED["progress"], "cap_usd": "25.00", "max_turns": 12}
    row = {**ROW_STOPPED, "progress": progress}
    run = new_run(rows=[row], status=row)
    run.screen.set_value("#run-budget", "3.00")
    run.screen.set_value("#run-turns", "40")
    run.revisit()
    open_row(run)
    assert run.screen.eval(CAP) == "25.00"
    run.click("resume-run")
    until(run.page, "window.__calls.some(c=>c.url==='/api/runs/resume')")
    assert run.posted("/api/runs/resume") == [{"id": ID, "cap_usd": "25.00", "max_turns": 12}]
    bare = {**ROW_STOPPED, "progress": {"module": "CP-1", "step": "stopped", "accepted": 1}}
    other = new_run(rows=[bare], status=bare)
    other.screen.set_value("#run-budget", "3.00")
    other.revisit()
    open_row(other)
    assert other.screen.eval(CAP) == ""
    assert other.disabled("resume-run") is True, "Review waits for a cap the analyst enters"
    other.screen.set_value("#resume-budget", "7")
    assert other.disabled("resume-run") is False


def test_reopening_a_stopped_run_after_another_run_shows_its_field(new_run: Any) -> None:
    run = new_run(rows=[ROW_STOPPED, ROW_DONE], status=ROW_STOPPED)
    run.revisit()
    open_row(run, ID)
    assert run.hidden("resume-hint") is False
    assert run.screen.eval("document.getElementById('resume-hint').closest('label')") is None
    run.status = ROW_DONE
    open_row(run, ROW_DONE["id"])
    assert run.hidden("resume-field") is True and run.hidden("resume-hint") is True
    run.status = ROW_STOPPED
    open_row(run, ID)
    assert run.hidden("resume-field") is False and run.hidden("resume-hint") is False
    assert run.text("resume-hint") == WITH_SPEND
    assert run.screen.attr("#resume-budget", "aria-describedby") == "resume-hint"


def test_a_resume_request_while_a_run_is_in_progress_is_said(new_run: Any) -> None:
    run = new_run(rows=[ROW_RUNNING, ROW_STOPPED], status=ROW_RUNNING)
    run.revisit()
    open_row(run)
    run.page.evaluate("id=>{location.hash='#W-NewRun/run?resume='+id;}", ID)
    until(run.page, f"{NOTE}!==''&&location.hash==='#W-NewRun/run'")
    assert run.text("new-run-message") == (
        "Another run is in progress. Resume this run after it finishes."
    )


@pytest.mark.parametrize("reason", ["checker", "provider", "interrupted", None])
def test_a_stop_for_another_reason_starts_at_the_previous_cap_with_the_same_hint(
    new_run: Any, reason: str | None
) -> None:
    row = {
        **drop(ROW_STOPPED, "reason"),
        "state": "failed",
        **({"reason": reason} if reason else {}),
    }
    run = opened(new_run, row)
    assert run.screen.eval(CAP) == "10.00"
    assert run.disabled("resume-run") is False and run.text("resume-hint") == WITH_SPEND
    for value, disabled in (("0", True), ("", True), ("2.50", False)):
        run.screen.set_value("#resume-budget", value)
        assert run.disabled("resume-run") is disabled, value


def test_resume_is_not_offered_after_a_ruling_stop(new_run: Any) -> None:
    run = opened(new_run, {**ROW_STOPPED, "state": "failed", "reason": "ruling"})
    assert [run.hidden(i) for i in ("resume-run", "resume-field", "resume-hint")] == [True] * 3


def test_a_stopped_run_offers_a_resume_that_goes_through_review(new_run: Any) -> None:
    run = opened(new_run, ROW_STOPPED)
    assert run.hidden("resume-run") is False
    assert run.screen.eval(CAP) == "10.00"
    run.screen.set_value("#resume-budget", "12.50")
    assert run.disabled("resume-run") is False
    resume(run, "12.50")
    assert run.posted("/api/runs/resume") == [{"id": ID, "cap_usd": "12.50", "max_turns": 32}]
    assert run.hidden("review-step") is False
    assert f"{RESUMED} Retained without a new model call: Source readiness." in notes(run)
    assert run.starts == 0 and run.disabled("start-run") is True
    run.confirm()
    assert run.disabled("start-run") is False
    run.click("start-run")
    assert run.starts == 1
    assert run.posted("/api/runs/start") == [{"id": ID2, "review_id": "b" * 64, "confirm": True}]


@pytest.mark.parametrize("row", [{**ROW_STOPPED, "state": "complete"}, ROW_RUNNING])
def test_a_complete_or_running_run_offers_no_resume(new_run: Any, row: dict[str, Any]) -> None:
    run = opened(new_run, row)
    assert run.hidden("resume-run") is True and run.hidden("resume-field") is True


def test_a_resume_with_nothing_accepted_says_every_module_runs_again(new_run: Any) -> None:
    reply = {**review_reply(True), "id": ID2, "resume_of": ID, "retained_modules": []}
    run = opened(new_run, ROW_STOPPED, reply)
    resume(run, "12.50")
    assert f"{RESUMED} No module of it was accepted; every module runs again." in notes(run)


def test_a_refused_resume_shows_its_problems_and_stays_on_progress(new_run: Any) -> None:
    run = opened(new_run, ROW_STOPPED, {"ok": False, "problems": [REFUSED]})
    resume(run, "12.50")
    assert run.text("new-run-message") == REFUSED
    assert run.hidden("progress-step") is False and run.hidden("review-step") is True


def test_a_resume_that_stops_its_retained_work_early_says_why(new_run: Any) -> None:
    note = (
        "Retained work stops before Financial analysis: "
        "its instructions changed since the stopped run."
    )
    reply = {**review_reply(True), "id": ID2, "resume_of": ID, "retained_modules": ["CP-0"],
             "retained_note": note}  # fmt: skip
    run = opened(new_run, ROW_STOPPED, reply)
    resume(run, "12.50")
    assert f"{RESUMED} Retained without a new model call: Source readiness. {note}" in notes(run)


def test_a_resume_that_keeps_nothing_says_why(new_run: Any) -> None:
    note = (
        "Retained work stops before Source readiness: "
        "its sources or context changed since the stopped run."
    )
    reply = {**review_reply(True), "id": ID2, "resume_of": ID, "retained_modules": [],
             "retained_note": note}  # fmt: skip
    run = opened(new_run, ROW_STOPPED, reply)
    resume(run, "12.50")
    assert f"{RESUMED} {note} Every module runs again." in notes(run)


def test_the_page_list_poll_never_speaks_for_a_tab_that_can_notify(new_run: Any) -> None:
    run = new_run(rows=[ROW_RUNNING], status=ROW_RUNNING)
    until(run.page, "[...window.__timers.values()].some(fn=>fn.name==='poll')")
    # Only the page's own poll runs: the app-wide watcher legitimately asks with notice enabled.
    run.page.evaluate(
        "()=>{window.Notification=class{static permission='granted';"
        "static requestPermission=async()=>'granted';};window.__calls.length=0;"
        "for(const fn of [...window.__timers.values()])if(fn.name==='poll')fn();}"
    )
    until(run.page, "window.__calls.some(c=>c.url.startsWith('/api/runs/list'))")
    lists = {u for u in run.urls() if u.split("?")[0] == "/api/runs/list"}
    assert lists == {"/api/runs/list?notify=0"}


@pytest.mark.parametrize(
    ("status", "want"),
    [
        ({"state": "running", "message": "Working", "run_available": True,
          "progress": {"module": "CP-1", "step": "running"}},
         ("incomplete", None, False, False)),
        ({"state": "running", "message": "Working", "run_available": True,
          "progress": {"step": "delivering", "accepted": 2}},
         ("current", "Delivering", False, False)),
        ({"state": "complete", "message": "Done", "run_available": True, "id": ID,
          "progress": {"step": "delivered", "accepted": 2}},
         ("complete", "Delivered", True, False)),
        ({"state": "failed", "message": "refused", "run_available": True, "id": ID,
          "progress": {"module": "CP-1", "step": "stopped", "stopped_during": "delivering",
                       "accepted": 2}},
         ("incomplete", "Stopped", False, True)),
    ],
    ids=["ahead", "delivering", "delivered", "stopped"],
)  # fmt: skip
def test_the_report_delivery_step_is_grey_ahead_blue_delivering_ticked_delivered_amber_stopped(
    new_run: Any, status: dict[str, Any], want: tuple[str, str | None, bool, bool]
) -> None:
    run = launched(new_run, status)
    until(run.page, "document.querySelectorAll('#module-stages li').length>0")
    stages = run.stages()
    step = stages[-1]
    assert step["name"] == "Report delivery"
    assert (step["status"], step["note"], step["img"], step["stopped"]) == want
    ahead = status["progress"].get("step") == "running"
    assert [s["status"] for s in stages[:2]] == ["complete", "current" if ahead else "complete"]
    if not ahead:
        assert step["current"] == "step"


def strip_row(state: str, reason: str, progress: dict[str, Any]) -> dict[str, Any]:
    return {**ROW_RUNNING, "state": state, "reason": reason, "message": "", "progress": progress}


def test_the_strip_resume_link_opens_that_runs_progress_panel_once(new_run: Any) -> None:
    progress = {"module": "CP-1", "step": "stopped", "accepted": 1, "spent_usd": "0.42"}
    row = strip_row("stopped", "budget", progress)
    run = new_run(rows=[row], status=row, route=f"W-NewRun/run?resume={ID}")
    until(run.page, "!document.getElementById('progress-step').hidden")
    assert run.text("run-identity") == IDENTITY
    assert run.hidden("resume-run") is False, "the same resumable rule as the recent-runs click"
    assert run.screen.hash() == "#W-NewRun/run"
    unknown = new_run(rows=[row], route=f"W-NewRun/run?resume=web-{'f' * 32}")
    until(unknown.page, f"{NOTE}!==''")
    assert unknown.hidden("progress-step") is True
    assert "no longer in the recent list" in unknown.text("new-run-message")


def test_the_strip_resume_link_works_while_new_run_is_already_open(new_run: Any) -> None:
    row = strip_row("failed", "provider", {"module": "CP-1", "step": "stopped", "accepted": 1})
    run = new_run(rows=[row], status=row)
    run.page.evaluate("id=>{location.hash='#W-NewRun/run?resume='+id;}", ID)
    until(run.page, "!document.getElementById('progress-step').hidden")
    until(run.page, "location.hash==='#W-NewRun/run'")


def test_a_resumable_run_has_one_primary_action_resume(new_run: Any) -> None:
    progress = {"step": "stopped", "stopped_during": "running", "module": "CP-1", "accepted": 1,
                "spent_usd": "8.90", "held_usd": "1.60", "cap_usd": "10"}  # fmt: skip
    row = strip_row("stopped", "budget", progress)
    run = new_run(rows=[row], status=row, route=f"W-NewRun/run?resume={ID}")
    until(run.page, "!document.getElementById('progress-step').hidden")
    until(run.page, "!runWatch.busy&&runWatch.jobs.length>0")
    run.page.evaluate("watchRuns()")
    primary = run.screen.eval(
        "[...document.querySelectorAll('#progress-step .primary-action')]"
        ".filter(b=>!b.hidden).map(b=>b.id)"
    )
    assert primary == ["resume-run"], "one primary: Resume"
    assert run.screen.attr("#open-run", "class") == "secondary-action"
    assert run.hidden("run-strip") is True, "the panel already says why the run stopped"
    run.click("another-run")
    until(run.page, "!document.getElementById('run-strip').hidden")


def test_a_finished_run_that_cannot_resume_keeps_open_run_primary(new_run: Any) -> None:
    progress = {"module": "CP-0", "step": "accepted", "accepted": 1}
    run = launched(
        new_run,
        {"state": "stopped", "reason": "ruling", "message": "paused", "progress": progress,
         "run_available": True, "id": ID},
    )  # fmt: skip
    assert run.screen.attr("#open-run", "class") == "primary-action"
    assert run.screen.attr("#resume-run", "class") == "secondary-action"


def test_fix_3_a_stop_after_the_last_module_was_accepted(new_run: Any) -> None:
    progress = {"module": "CP-1", "step": "accepted", "accepted": 2}
    run = launched(
        new_run,
        {"state": "interrupted", "message": "cut", "progress": progress, "run_available": True,
         "id": ID},
    )  # fmt: skip
    stages = run.stages()
    assert [s["status"] for s in stages[:2]] == ["complete", "complete"]
    assert stages[2]["stopped"] and stages[2]["note"] == "Stopped" and not stages[2]["img"]
