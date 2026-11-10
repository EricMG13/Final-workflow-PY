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
from issuer_library_browser import json_reply, open_app, release, until
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


# PR1 answer key (R-SB2-7): the Review step lists the expected outcomes and, when items are
# counted, asks for acceptance before Start. Expected values come from Plan 2 Task 7, its
# "Outcome semantics" and the lead's rulings; the replies below are written by hand.
CAPTION = (
    "Expected from your declarations, files and context; CP-0 confirms during the run; "
    "the model may still find less."
)
ROW_KEYS = (
    "id",
    "scope",
    "outcome",
    "reason",
    "fix",
    "basis",
    "evidence",
    "counted",
    "inherited_from",
)
START = "/api/runs/start"


def expectation(row_id: str, outcome: str, counted: bool, **fields: Any) -> dict[str, Any]:
    scope = fields.pop("scope", row_id.split(":")[0])
    row = {
        "id": row_id, "scope": scope, "outcome": outcome, "counted": counted,
        "reason": f"reason of {row_id}", "fix": f"fix of {row_id}", "basis": f"basis of {row_id}",
        "evidence": "per method", "inherited_from": [],
    }  # fmt: skip
    return {**row, **fields}


# Scrambled on purpose: the page, not the server, puts "This run" first, then modules in order,
# and an inherited row under its producer (CP-0) rather than with its own scope (CP-1).
MIXED = [
    expectation("CP-1:check", "check", True, evidence="observed offline"),
    expectation("CP-1:ok", "ready", False),
    expectation("CP-1:from:CP-0", "information", False, inherited_from=["CP-0"]),
    expectation("CP-1:warn", "limited", True, evidence="observed live"),
    expectation("run:legal", "gap", True),
    expectation("CP-1:info", "information", False),
    expectation("CP-0:z", "will_refuse", True),
]
MIXED_COUNTED = ["run:legal", "CP-0:z", "CP-1:check", "CP-1:warn"]
INFORMATION_ONLY = [expectation("run:what-changed", "information", False)]
OUTCOME_NAMES = {
    "CP-0:z": "Returns Blocked", "run:legal": "Gap", "CP-1:warn": "Limited",
    "CP-1:check": "Check", "CP-1:info": "Information", "CP-1:ok": "Ready",
}  # fmt: skip
EVIDENCE_LABELS = {"CP-1:check": "observed offline", "CP-1:warn": "observed live"}
ROWS = "#expected-outcomes tr[data-id]"
ROW_TEXT = (
    "id=>{const tr=[...document.querySelectorAll('#expected-outcomes tr[data-id]')]"
    ".find(r=>r.dataset.id===id);return {text:tr.textContent,"
    "details:[...tr.querySelectorAll('details')].map(d=>({summary:d.querySelector('summary')"
    "?.textContent,text:d.textContent}))};}"
)
BOX = "(()=>{const b=document.getElementById('run-accept');return b?"
BOX_STATE = (
    BOX + "{checked:b.checked,type:b.type,disabled:b.disabled,"
    "label:b.closest('label')?.textContent.trim()}:null})()"
)


def with_expectations(rows: list[dict[str, Any]], counted: list[str]) -> dict[str, Any]:
    return {**review_reply(True), "expectations": rows, "counted": counted}


def prepared(new_run: Any, review: dict[str, Any], **options: Any) -> tuple[NewRun, list[Any]]:
    """A New run whose Review reply is `review`; every Start body is recorded at the route."""
    run: NewRun = new_run(**options)
    bodies: list[Any] = []

    def start(route: Any) -> None:
        bodies.append(json.loads(route.request.post_data))
        json_reply({"state": "running", "id": ID})(route)

    run.page.route("**/api/runs/review", json_reply(review))
    run.page.route(f"**{START}", start)
    return run, bodies


def reviewing(new_run: Any, review: dict[str, Any], **options: Any) -> tuple[NewRun, list[Any]]:
    run, bodies = prepared(new_run, review, **options)
    review_it(run)
    return run, bodies


def sent(run: NewRun, bodies: list[Any]) -> list[Any]:
    """The Start bodies the route has seen, once one has arrived."""
    for _ in range(100):
        if bodies:
            break
        run.page.wait_for_timeout(20)
    return bodies


def review_it(run: NewRun) -> None:
    """From the source step: context and folder given, Validate and review, wait for the step."""
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    until(run.page, "!document.getElementById('review-step').hidden")


def row_ids(run: NewRun) -> list[str | None]:
    return run.screen.attrs(ROWS, "data-id")


def accept_box(run: NewRun) -> dict[str, Any] | None:
    state: dict[str, Any] | None = run.page.evaluate(BOX_STATE)
    return state


def start_enabled(run: NewRun) -> bool:
    return not run.disabled("start-run")


def test_expected_outcomes_open_the_review_step_with_the_caption(new_run: Any) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    page = run.page
    assert page.evaluate("!!document.querySelector('#run-review #expected-outcomes')")
    before_summary = (
        "document.querySelector('#expected-outcomes').compareDocumentPosition("
        "document.querySelector('#run-review .review-summary'))&Node.DOCUMENT_POSITION_FOLLOWING"
    )
    assert page.evaluate(before_summary), "the table does not come before the existing summary"
    text = run.text("expected-outcomes") if run.screen.exists("#expected-outcomes") else ""
    assert CAPTION in " ".join(text.split())
    assert "Expected outcomes" in page.evaluate("document.getElementById('run-review').textContent")


def test_this_run_rows_come_first_then_modules_in_order_and_inherited_under_the_producer(
    new_run: Any,
) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    ids = row_ids(run)
    assert ids[:3] == ["run:legal", "CP-0:z", "CP-1:from:CP-0"], ids
    assert sorted(ids[3:]) == ["CP-1:check", "CP-1:info", "CP-1:ok", "CP-1:warn"], ids


def test_each_row_shows_outcome_name_reason_fix_and_the_why_disclosure(new_run: Any) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    for row_id, name in OUTCOME_NAMES.items():
        row = run.page.evaluate(ROW_TEXT, row_id)
        for shown in (name, f"reason of {row_id}", f"fix of {row_id}"):
            assert shown in row["text"], f"{row_id}: {shown!r} not shown"
        (why,) = row["details"]
        assert why["summary"] == "Why we expect this", row_id
        assert f"basis of {row_id}" in why["text"], row_id
        label = EVIDENCE_LABELS.get(row_id, "per method")
        assert label in why["text"], f"{row_id}: evidence label {label!r}"
    assert "Source readiness" in run.page.evaluate(ROW_TEXT, "CP-0:z")["text"], "module title"
    assert "Will refuse" not in run.text("expected-outcomes"), "R-ALIVE wording: Returns Blocked"


def test_information_and_inherited_rows_say_not_counted_and_counted_rows_do_not(
    new_run: Any,
) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    for row in MIXED:
        text = run.page.evaluate(ROW_TEXT, row["id"])["text"]
        assert ("Not counted" in text) == (not row["counted"]), f"{row['id']}: {text!r}"


def test_the_acceptance_box_counts_the_items_and_start_needs_both_ticks(new_run: Any) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    box = accept_box(run)
    assert box == {"checked": False, "type": "checkbox", "disabled": False,
                   "label": "I accept these 4 items"}  # fmt: skip
    assert not start_enabled(run)
    run.click("run-confirm")
    assert not start_enabled(run), "Start enabled with only the approval ticked"
    run.click("run-confirm")
    run.click("run-accept")
    assert not start_enabled(run), "Start enabled with only the acceptance ticked"
    run.click("run-confirm")
    assert start_enabled(run)


def test_start_carries_accept_limitations_true_after_both_ticks(new_run: Any) -> None:
    run, bodies = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    run.click("run-confirm")
    run.click("run-accept")
    run.click("start-run")
    assert sent(run, bodies) == [
        {"id": ID, "review_id": "b" * 64, "confirm": True, "accept_limitations": True}
    ]


def test_with_nothing_counted_there_is_no_acceptance_box_and_start_needs_one_tick(
    new_run: Any,
) -> None:
    run, bodies = reviewing(new_run, with_expectations(INFORMATION_ONLY, []))
    assert accept_box(run) is None and run.screen.count("#run-accept") == 0
    assert run.screen.count(ROWS) == 1 and "Not counted" in run.text("expected-outcomes")
    assert not start_enabled(run)
    run.click("run-confirm")
    assert start_enabled(run)
    run.click("start-run")
    assert sent(run, bodies) == [
        {"id": ID, "review_id": "b" * 64, "confirm": True, "accept_limitations": False}
    ]


def tick_both(run: NewRun) -> None:
    run.click("run-confirm")
    run.click("run-accept")
    assert start_enabled(run)


def assert_both_cleared(run: NewRun) -> None:
    assert accept_box(run) is not None and not accept_box(run)["checked"]  # type: ignore[index]
    assert not run.page.evaluate("document.getElementById('run-confirm').checked")
    run.click("run-confirm")
    assert not start_enabled(run), "a stale acceptance tick survived"


def test_editing_the_folder_and_reviewing_again_clears_the_acceptance_tick(new_run: Any) -> None:
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED))
    tick_both(run)
    run.click("revise-run")
    review_it(run)
    assert_both_cleared(run)


def test_a_resumed_review_clears_the_acceptance_tick(new_run: Any) -> None:
    review = with_expectations(MIXED, MIXED_COUNTED)
    run, _ = prepared(new_run, review, rows=[ROW_STOPPED], status=ROW_STOPPED)
    run.page.route("**/api/runs/resume", json_reply({**review, "id": ID2, "resume_of": ID}))
    review_it(run)
    tick_both(run)
    run.click("revise-run")
    run.revisit()
    open_row(run)
    resume(run, "10.00")
    assert_both_cleared(run)


def test_another_run_clears_the_acceptance_tick(new_run: Any) -> None:
    done = {"state": "complete", "message": "Done", "run_available": True,
            "progress": {"module": "CP-1", "step": "delivered"}}  # fmt: skip
    run, _ = reviewing(new_run, with_expectations(MIXED, MIXED_COUNTED), status=done)
    tick_both(run)
    run.click("start-run")
    until(run.page, "!document.getElementById('another-run').hidden")
    run.click("another-run")
    review_it(run)
    assert_both_cleared(run)


HOSTILE_IMG = "<img src=x onerror=window.__pwned=1>"
HOSTILE_CELL = "</td><script>window.__pwned=1</script>"


def test_hostile_review_text_renders_as_literal_text(new_run: Any) -> None:
    rows = [
        expectation(
            f"CP-1:{HOSTILE_IMG}", "gap", True, scope=f"CP-1{HOSTILE_CELL}",
            reason=f"{HOSTILE_IMG} reason {HOSTILE_CELL}", fix=f"fix {HOSTILE_IMG}{HOSTILE_CELL}",
            basis=f"basis {HOSTILE_CELL} {HOSTILE_IMG}",
        ),
        expectation(f"run:{HOSTILE_CELL}", "check", True, reason=HOSTILE_IMG, fix=HOSTILE_CELL,
                    basis=HOSTILE_IMG, scope=HOSTILE_IMG),
    ]  # fmt: skip
    run, _ = reviewing(new_run, with_expectations(rows, [rows[0]["id"], rows[1]["id"]]))
    page = run.page
    assert (
        page.evaluate("document.querySelectorAll('#run-review img,#run-review script').length") == 0
    )
    assert page.evaluate("window.__pwned") is None
    assert run.screen.count(ROWS) == 2, "an injected cell or row changed the table"
    assert sorted(row_ids(run)) == sorted(str(r["id"]) for r in rows)  # type: ignore[type-var]
    shown = page.evaluate("document.getElementById('expected-outcomes').textContent")
    assert HOSTILE_IMG in shown and HOSTILE_CELL in shown
    assert "I accept these 2 items" in page.evaluate(
        "document.getElementById('run-accept').closest('label').textContent"
    )
