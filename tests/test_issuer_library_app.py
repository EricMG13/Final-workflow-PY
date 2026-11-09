"""The one app in a real browser: New run, Settings, the context form and the embedded reports.

Synthetic API replies only; no network, server or provider. Marked browser: real browser proof.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from issuer_library_browser import (
    CAPTURED_TIMERS,
    EMPTY_STORE,
    EMPTY_WORKSPACE,
    ORIGIN,
    ROOT,
    WEB,
    json_reply,
    open_app,
    pageerrors,
    serve,
    until,
)

pytestmark = pytest.mark.browser

ID = "web-" + "a" * 32
ID2 = "web-" + "c" * 32
ROW_RUNNING: dict[str, Any] = {
    "id": ID,
    "state": "running",
    "message": "Working",
    "run_available": True,
    "started_at": "2026-11-08T09:00:00Z",
    "issuer": "Northbridge Group",
    "pathway": "covenant_refinancing",
    "as_of": "2025-03-31",
    "modules": ["CP-0", "CP-1"],
    "module_details": [
        {"id": "CP-0", "title": "Source readiness"},
        {"id": "CP-1", "title": "Financial analysis"},
    ],
    "progress": {"module": "CP-1", "step": "started", "spent_usd": "0.10"},
}
ROW_DONE = {
    "id": "web-" + "b" * 32,
    "state": "complete",
    "message": "Done",
    "run_available": True,
    "started_at": "2026-11-07T08:00:00Z",
    "issuer": "Southport Holdings",
    "pathway": "credit_snapshot",
    "as_of": "2025-06-30",
    "spent_usd": "3.10",
}
IDENTITY = "Northbridge Group · Covenant Refinancing · as of 31 March 2025 · WEB-AAAAAAAA"
STARTED = {
    "state": "running",
    "message": "Working",
    "progress": {"module": "CP-1", "step": "started", "spent_usd": "0.10"},
    "run_available": True,
}
CONTEXT = json.loads((ROOT / "cases/context/research-minimal.json").read_text(encoding="utf-8"))
RUNNING = {
    "state": "running",
    "message": "Working",
    "progress": {"module": "CP-0", "step": "accepted", "spent_usd": "0.42"},
    "run_available": True,
}
# Written by hand from NORTHBRIDGE: one run with a delivered CP-0 and an unstructured CP-4A.
NORTHBRIDGE: dict[str, Any] = {
    "runs": {
        "web-1": {
            "folder": "web-1",
            "issuer": "Northbridge",
            "title": "Northbridge",
            "run": "WEB-1",
            "sector": "Industrials",
            "period": "As of 2025-03-31",
            "first": "CP-0",
            "modules": {
                "CP-0": {
                    "outputs": ["web-1/deliveries/abc/CP-0.md"],
                    "inputs": [],
                    "default": "web-1/deliveries/abc/CP-0.md",
                },
                "CP-4A": {"outputs": ["web-1/CP-4A.md"], "inputs": [], "default": "web-1/CP-4A.md"},
            },
        }
    },
    "outputs": {
        "web-1/deliveries/abc/CP-0.md": {
            "id": "web-1/deliveries/abc/CP-0.md",
            "run": "web-1",
            "module": "CP-0",
            "source": "deliveries/abc/CP-0.md",
            "file": "web-1--deliveries--abc--CP-0.md",
            "href": "/files/runs/web-1/deliveries/abc/CP-0.md?sha256=aa",
            "label": "CP-0",
            "sha256": "aa" * 32,
            "case": "Northbridge · WEB-1",
            "period": "As of 2025-03-31",
            "scope": "Retained module output",
            "firstHeading": None,
            "sections": [
                {
                    "heading": "Findings",
                    "level": 2,
                    "line": 3,
                    "blocks": [
                        {
                            "type": "table",
                            "line": 5,
                            "headers": ["Item", "Value"],
                            "rows": [{"line": 7, "cells": ["Revenue", "0"]}],
                        }
                    ],
                }
            ],
        },
        "web-1/CP-4A.md": {
            "id": "web-1/CP-4A.md",
            "run": "web-1",
            "module": "CP-4A",
            "source": "CP-4A.md",
            "file": "web-1--CP-4A.md",
            "href": "/files/runs/web-1/CP-4A.md?sha256=cc",
            "label": "CP-4A",
            "sha256": "cc" * 32,
            "case": "Northbridge · WEB-1",
            "period": "As of 2025-03-31",
            "scope": "Retained module output",
            "firstHeading": None,
            "parseError": "Body before first heading",
            "sections": [
                {
                    "heading": "Unstructured handoff",
                    "level": 1,
                    "line": 1,
                    "blocks": [{"type": "text", "line": 1, "end": 1, "text": "Body <b>raw</b>"}],
                }
            ],
        },
    },
    "inputs": {},
    "pins": {},
}
NORTHBRIDGE_REPORTS: dict[str, Any] = {
    "reports": [
        {
            "id": "abc",
            "build": None,
            "label": "Northbridge · as of 2025-03-31",
            "status": None,
            "issuer": "Northbridge",
            "sha256": "r",
            "scope": "s",
            "modelPublished": False,
            "href": "/files/runs/web-1/deliveries/abc/report.html?sha256=r&embedded=1",
            "download": "/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1",
            "files": [
                {
                    "name": "report.html",
                    "href": "/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1",
                }
            ],
            "builtFrom": [
                {
                    "module": "CP-0",
                    "sha256": "aa" * 32,
                    "run": "web-1",
                    "source": "web-1/deliveries/abc/CP-0.md",
                    "output": True,
                },
                {
                    "module": "CP-9",
                    "sha256": "bb" * 32,
                    "run": None,
                    "source": "CP-9.md",
                    "output": False,
                },
            ],
        },
        {
            "id": "orphan",
            "build": None,
            "label": "Gamma · as of 2024-01-31",
            "status": None,
            "issuer": "Gamma",
            "sha256": "o",
            "scope": "s",
            "modelPublished": False,
            "href": "/files/deliverables/orphan/report.html?sha256=o&embedded=1",
            "download": "/files/deliverables/orphan/report.html?sha256=o&download=1",
            "files": [],
            "builtFrom": [
                {
                    "module": "CP-1",
                    "sha256": "dd" * 32,
                    "run": None,
                    "source": "CP-1.md",
                    "output": False,
                }
            ],
        },
    ],
    "visuals": [],
}


def review_reply(ready: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "id": ID,
        "review_id": "b" * 64,
        "issuer": "Northbridge Group",
        "pathway": "covenant_refinancing",
        "as_of": "2025-03-31",
        "modules": ["CP-0", "CP-1"],
        "module_details": [
            {"id": "CP-0", "title": "Source readiness", "purpose": "Check issuer files"},
            {"id": "CP-1", "title": "Financial analysis", "purpose": "Read financial statements"},
        ],
        "config": "sol-medium",
        "provider": "openai",
        "model": "gpt-6.1-sol",
        "effort": "medium",
        "cap_usd": "10.00",
        "hold_usd": "1.86",
        "max_turns": 7,
        "prices_as_of": "2026-11-01",
        "provider_ready": ready,
        "provider_key": "OPENAI_API_KEY",
        "sources": [{"path": "filings/annual.txt", "sha256": "c" * 64}],
        "ignored": ["chart.png"],
        "report_sections": ["liquidity-runway"],
        "omitted": ["lme-chart"],
        "scope": "User-launched run; analytical accuracy has not been independently reviewed.",
    }


class NewRun:
    """The New run destination with synthetic replies; Start is counted, never executed."""

    def __init__(
        self,
        browser: Any,
        ready: bool = True,
        status: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
        route: str = "W-NewRun/run",
    ) -> None:
        self.starts = 0
        self.status = status or RUNNING
        self.rows = rows if rows is not None else []
        self.fail_list = False
        self.fail_start = False
        self.resume: dict[str, Any] = {
            **review_reply(ready),
            "id": ID2,
            "resume_of": ID,
            "retained_modules": ["CP-0"],
        }

        def listed(route: Any) -> None:
            if self.fail_list:
                self.fail_list = False
                route.abort()
            else:
                json_reply(self.rows)(route)

        def start(route: Any) -> None:
            self.starts += 1
            if self.fail_start:
                route.abort()
            else:
                json_reply({"state": "running", "id": ID})(route)

        self.screen = open_app(
            browser,
            route,
            api={
                "/api/runs/review": json_reply(review_reply(ready)),
                "/api/runs/resume": lambda reply: json_reply(self.resume)(reply),
                "/api/runs/start": start,
                "/api/runs/status": lambda route: json_reply(self.status)(route),
                "/api/runs/list": listed,
            },
            timers=CAPTURED_TIMERS,
        )
        self.page = self.screen.page
        self.settle()

    def settle(self) -> None:
        self.page.wait_for_timeout(50)

    def click(self, element_id: str) -> None:
        self.page.evaluate("i=>document.getElementById(i).click()", element_id)
        self.settle()

    def tick(self) -> None:
        """Fire every live interval once, as the page's own polling would."""
        self.page.evaluate("window.__tick()")
        self.settle()

    def revisit(self) -> None:
        self.page.evaluate("window.dispatchEvent(new Event('hashchange'))")
        self.settle()

    def launch(self) -> None:
        self.context()
        self.folder("N/annual.txt")
        self.click("review-run")
        self.confirm()
        self.click("start-run")

    def stages(self) -> list[dict[str, Any]]:
        value: list[dict[str, Any]] = self.page.evaluate(
            "[...document.querySelectorAll('#module-stages li')].map(li=>({"
            "name:li.querySelector('strong')?.textContent,status:li.dataset.status,"
            "current:li.getAttribute('aria-current'),stopped:li.hasAttribute('data-stopped'),"
            "note:li.querySelector('span:not(.step-marker)')?.textContent??null,title:li.title,"
            "marker:li.querySelector('.step-marker')?.textContent,"
            "tick:Boolean(li.querySelector('.step-marker img')),"
            "img:Boolean(li.querySelector('img'))}))"
        )
        return value

    def recent(self) -> list[dict[str, Any]]:
        value: list[dict[str, Any]] = self.page.evaluate(
            "[...document.querySelectorAll('#recent-jobs tbody tr')].map(tr=>({"
            "head:tr.querySelector('th').textContent,"
            "cells:[...tr.querySelectorAll('td')].map(td=>td.textContent),"
            "badges:[...tr.querySelectorAll('td')].map(td=>td.querySelector('.badge')?.className??null)}))"
        )
        return value

    def context(self, source_is_editor: bool = True) -> None:
        self.page.evaluate(
            "([ctx,editor])=>window.dispatchEvent(new MessageEvent('message',{source:editor?"
            "document.getElementById('context-editor').contentWindow:window,"
            "data:{type:'cpos:context',context:ctx,problems:[]}}))",
            [CONTEXT, source_is_editor],
        )

    def folder(self, *names: str) -> None:
        self.page.evaluate(
            "names=>{const input=document.getElementById('run-sources');"
            "const files=names.map(name=>{const file=new File(['x'],name.split('/').at(-1));"
            "Object.defineProperty(file,'webkitRelativePath',{value:name});return file;});"
            "Object.defineProperty(input,'files',{configurable:true,value:files});"
            "input.dispatchEvent(new Event('change'));}",
            list(names),
        )

    def confirm(self) -> None:
        self.page.evaluate(
            "()=>{const box=document.getElementById('run-confirm');box.checked=true;"
            "box.dispatchEvent(new Event('change'));}"
        )

    def review_body(self) -> dict[str, Any]:
        value: dict[str, Any] = self.page.evaluate(
            "()=>{const call=window.__calls.find(c=>c.url==='/api/runs/review');const b=call.options.body;"
            "return {paths:b.get('source_paths'),sources:b.getAll('sources').length,config:b.get('config'),"
            "cap:b.get('cap_usd'),modules:b.get('modules'),turns:b.get('max_turns'),context:b.get('context')};}"
        )
        return value

    def text(self, element_id: str) -> str:
        value: str = self.page.evaluate("i=>document.getElementById(i).textContent", element_id)
        return value

    def hidden(self, element_id: str) -> bool:
        return self.screen.hidden(element_id)

    def disabled(self, element_id: str) -> bool:
        value: bool = self.page.evaluate("i=>document.getElementById(i).disabled", element_id)
        return value

    def urls(self) -> list[str]:
        return [call["url"] for call in self.screen.calls()]

    def progress(self) -> list[str]:
        return self.screen.texts("#run-progress .summary-line")

    def posted(self, url: str) -> list[Any]:
        """The JSON bodies sent to a path, in order."""
        value: list[Any] = self.page.evaluate(
            "u=>window.__calls.filter(c=>c.url===u).map(c=>JSON.parse(c.options.body))", url
        )
        return value

    def close(self) -> None:
        assert self.screen.errors == []
        self.screen.close()


@pytest.fixture
def new_run(browser: Any) -> Any:
    opened: list[NewRun] = []

    def factory(**options: Any) -> NewRun:
        run = NewRun(browser, **options)
        opened.append(run)
        return run

    yield factory
    for run in opened:
        run.close()


def test_the_steps_follow_the_launcher_and_untrusted_messages_are_ignored(new_run: Any) -> None:
    run = new_run()
    assert run.screen.texts(".run-stages li") == [
        "Context",
        "Issuer folder & budget",
        "Review & start",
        "Progress",
    ]
    assert run.screen.attr("#run-sources", "webkitdirectory") is not None
    assert run.text("recent-jobs") == (
        "No runs started from this app are recorded in this workspace yet. "
        "Earlier runs are in the Issuer library."
    )
    assert run.screen.text("#recent-jobs a") == "Issuer library"
    assert run.screen.attr("#recent-jobs a", "href") == "#W-Library/cases"
    run.context(source_is_editor=False)
    assert run.hidden("source-step") is True
    run.context()
    assert run.hidden("source-step") is False
    assert run.page.evaluate("document.activeElement===document.querySelector('#source-step h2')")


def test_review_sends_the_folder_as_relative_paths_and_starts_nothing(new_run: Any) -> None:
    run = new_run()
    run.context()
    run.folder(
        "Northbridge/annual.txt",
        "Northbridge/filings/notes.md",
        "Northbridge/.DS_Store",
        "Northbridge/.git/config",
    )
    assert "2 files" in run.text("upload-list")
    run.screen.set_value("#run-model", "opus-medium", "change")
    run.screen.set_value("#run-budget", "25")
    run.screen.set_value("#run-modules", "CP-4")
    run.screen.set_value("#run-turns", "7")
    run.click("review-run")
    body = run.review_body()
    # Written by hand: the chosen folder's own name is dropped, dot paths are not uploaded.
    assert json.loads(body["paths"]) == ["annual.txt", "filings/notes.md"]
    assert body["sources"] == 2
    assert [body["config"], body["cap"], body["modules"], body["turns"]] == [
        "opus-medium",
        "25",
        "CP-4",
        "7",
    ]
    assert json.loads(body["context"]) == CONTEXT
    assert run.starts == 0 and run.hidden("review-step") is False
    assert run.page.evaluate("document.activeElement===document.querySelector('#review-step h2')")


def test_the_review_shows_everything_the_launcher_decided(new_run: Any) -> None:
    run = new_run()
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    text = run.text("run-review")
    for expected in [
        "Northbridge Group",
        "Covenant Refinancing",
        "31 March 2025",
        "openai gpt-6.1-sol · medium",
        "USD 10.00",
        "USD 1.86",
        "Source readiness",
        "chart.png",
        "liquidity-runway",
        "lme-chart",
        "not been independently reviewed",
        "not an estimate of total cost",
        "filings/annual.txt",
    ]:
        assert expected in text, expected
    assert run.screen.count(".review-modules > li") == 2


def test_only_an_explicitly_confirmed_start_launches_once(new_run: Any) -> None:
    run = new_run()
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    assert run.disabled("start-run") is True
    run.click("start-run")
    assert run.starts == 0
    run.confirm()
    run.click("start-run")
    run.click("start-run")
    assert run.starts == 1 and run.hidden("progress-step") is False
    body = run.page.evaluate(
        "JSON.parse(window.__calls.find(c=>c.url==='/api/runs/start').options.body)"
    )
    assert body == {"id": ID, "review_id": "b" * 64, "confirm": True}
    assert run.text("run-identity") == IDENTITY
    assert run.progress() == ["Running", "Source readiness accepted\u00a0(1\u00a0of\u00a02)."]
    assert run.screen.attr("#run-identity .code", "title") == ID, "the full id stays in the badge"
    assert run.hidden("module-stages") is False
    stages = run.stages()
    assert [stage["name"] for stage in stages] == [
        "Source readiness",
        "Financial analysis",
        "Report delivery",
    ]
    assert stages[2]["status"] == "incomplete" and stages[2]["note"] is None
    assert not stages[2]["img"]
    assert stages[0]["current"] == "step" and stages[1]["current"] is None
    assert stages[0]["status"] == "complete" and stages[0]["note"] == "Accepted"
    assert stages[1]["status"] == "incomplete" and stages[1]["note"] is None
    reviewed = run.page.evaluate(
        "(()=>{const li=document.querySelector('#run-review ol li');"
        "return [li.textContent,li.title];})()"
    )
    assert reviewed == ["Source readiness", "CP-0: Check issuer files"], "no codes in the review"
    assert "USD 0.42" in run.text("run-spend")
    assert run.hidden("open-run") is True


def test_a_missing_provider_key_keeps_start_unavailable_and_names_the_variable(
    new_run: Any,
) -> None:
    run = new_run(ready=False)
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    run.confirm()
    assert run.disabled("start-run") is True
    assert "OPENAI_API_KEY is not set" in run.text("run-review")
    run.click("revise-run")
    assert run.hidden("source-step") is False
    assert run.page.evaluate("document.getElementById('run-confirm').checked") is False


def test_a_lost_start_response_reconnects_by_id_instead_of_launching_again(new_run: Any) -> None:
    run = new_run()
    run.fail_start = True
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    run.confirm()
    run.click("start-run")
    assert run.starts == 1 and run.hidden("progress-step") is False
    assert f"/api/runs/status?id={ID}" in run.urls()


@pytest.mark.parametrize(
    ("state", "label", "route"),
    [
        ("complete", "Open deliverables", f"W-Reports/list?c={ID}"),
        ("stopped", "Open run", f"W-Overview/overview?c={ID}"),
    ],
)
def test_a_finished_run_offers_its_deliverables_a_stopped_one_offers_the_run(
    new_run: Any, state: str, label: str, route: str
) -> None:
    status = {
        "state": state,
        "message": "Done",
        "spent_usd": "3.10",
        "run_available": True,
        "id": ID,
    }
    run = new_run(status=status)
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    run.confirm()
    run.click("start-run")
    assert run.hidden("open-run") is False and run.text("open-run") == label
    assert run.screen.attr("#open-run", "data-route") == route
    assert "USD 3.10" in run.text("run-spend") and run.hidden("another-run") is False
    assert run.text("run-progress").strip() == f"{state.capitalize()}: Done"
    stages = run.stages()
    if state == "complete":
        assert stages[-1]["current"] is not None
    else:
        assert all(stage["current"] is None for stage in stages)
    for stage in stages:
        assert stage["status"] == ("complete" if state == "complete" else "incomplete"), state
        if state == "stopped":
            assert stage["note"] is None


def test_a_failed_run_offers_nothing_to_open(new_run: Any) -> None:
    run = new_run(
        status={"state": "failed", "message": "Refused", "run_available": False, "id": ID}
    )
    run.context()
    run.folder("N/annual.txt")
    run.click("review-run")
    run.confirm()
    run.click("start-run")
    assert run.hidden("open-run") is True


def test_context_height_messages_are_source_checked_and_bounded(new_run: Any) -> None:
    run = new_run()

    def send(editor: bool, height: float) -> str:
        value: str = run.page.evaluate(
            "([editor,height])=>{const frame=document.getElementById('context-editor');"
            "window.dispatchEvent(new MessageEvent('message',{source:editor?frame.contentWindow:window,"
            "data:{type:'cpos:height',height}}));return frame.style.height;}",
            [editor, height],
        )
        return value

    assert send(False, 1800) == ""
    assert send(True, 1800) == "1800px"
    assert send(True, float("inf")) == "1800px"
    assert send(True, 50001) == "1800px"


def test_an_issuer_folder_is_required_before_review(new_run: Any) -> None:
    run = new_run()
    run.context()
    run.click("review-run")
    assert "Choose the issuer folder" in run.text("new-run-message")
    assert "/api/runs/review" not in run.urls()


# ---- One app: navigation across destinations and deliverables, over any workspace. ----


def test_a_module_that_has_started_is_shown_as_running(new_run: Any) -> None:
    run = new_run(status={**STARTED, "progress": {**STARTED["progress"], "spent_usd": "0.42"}})
    run.launch()
    assert run.progress() == ["Running", "Running Financial analysis\u00a0(2\u00a0of\u00a02)."]
    first, second, _ = run.stages()
    assert second["current"] is not None and first["current"] is None
    assert first["status"] == "complete" and first["note"] == "Accepted"
    assert first["tick"], "a tick, not a number"
    assert second["status"] == "current" and second["note"] == "Running" and not second["stopped"]
    assert first["title"] == "CP-0" and second["marker"] == "2"


def test_a_stopped_run_does_not_claim_its_rejected_module_is_still_running(new_run: Any) -> None:
    run = new_run(status={**STARTED, "state": "stopped", "message": "CP-1 rejected.", "id": ID})
    run.launch()
    assert run.progress() == [
        "Stopped: CP-1 rejected.",
        "Stopped during Financial analysis\u00a0(2\u00a0of\u00a02).",
    ]
    second = run.stages()[1]
    assert second["current"] == "step" and second["status"] == "current"
    assert second["stopped"] and second["note"] == "Stopped here"
    assert run.hidden("open-run") is False and run.text("open-run") == "Open run"


def test_recent_runs_are_a_table_active_first_and_a_row_reopens_its_run(new_run: Any) -> None:
    run = new_run(rows=[ROW_DONE, ROW_RUNNING], status=STARTED)
    run.revisit()
    assert run.screen.texts("#recent-jobs .table-scroll table thead th") == [
        "Issuer",
        "Workflow",
        "Module",
        "State",
        "Spend (USD)",
    ]
    rows = run.recent()
    assert len(rows) == 2
    button = run.page.evaluate(
        "(()=>{const b=document.querySelector("
        "'#recent-jobs tbody tr th[scope=\"row\"] button.text-button');"
        "return b&&[b.textContent,b.title];})()"
    )
    assert button == ["Northbridge Group · WEB-AAAAAAAA · 8 November 2026", ID]
    assert rows[0]["cells"] == [
        "Covenant Refinancing",
        "running Financial analysis (2 of 2)",
        "running",
        "0.10",
    ]
    assert "badge-blue" in rows[0]["badges"][0] and "badge-blue" in rows[0]["badges"][2]
    assert rows[1]["head"] == "Southport Holdings · WEB-BBBBBBBB · 7 November 2026"
    assert rows[1]["cells"][1:] == ["—", "complete", "3.10"]
    assert "badge-navy" in rows[1]["badges"][2]
    assert run.page.evaluate("document.querySelector('.recent-runs').open") is True
    run.page.evaluate("document.querySelector('#recent-jobs tbody th button').click()")
    run.settle()
    assert run.hidden("progress-step") is False and run.text("run-identity") == IDENTITY
    assert run.hidden("module-stages") is False
    stages = run.stages()
    assert len(stages) == 3 and stages[1]["current"] == "step"
    assert run.progress() == ["Running", "Running Financial analysis\u00a0(2\u00a0of\u00a02)."]


def test_a_list_refresh_keeps_the_focused_row(new_run: Any) -> None:
    rows = [dict(ROW_RUNNING)]
    run = new_run(rows=rows)
    run.revisit()
    focused = run.page.evaluate(
        "(()=>{window.__table=document.querySelector('#recent-jobs table');"
        "document.querySelector('#recent-jobs tbody th button').focus();"
        "return document.activeElement.title;})()"
    )
    assert focused == ID
    run.tick()
    assert run.page.evaluate("document.querySelector('#recent-jobs table')===window.__table"), (
        "an identical list keeps the same table node"
    )
    assert run.page.evaluate("document.activeElement.title") == ID
    rows[0] = {**ROW_RUNNING, "state": "complete"}
    run.tick()
    after = run.page.evaluate(
        "(()=>{const t=document.querySelector('#recent-jobs table');"
        "return {rebuilt:t!==window.__table,"
        "focus:document.activeElement===t.querySelector('tbody th button'),"
        "title:document.activeElement.title};})()"
    )
    assert after == {"rebuilt": True, "focus": True, "title": ID}


def test_a_run_without_a_saved_review_still_lists_and_opens_by_id(new_run: Any) -> None:
    row = {"id": ID, "state": "stopped", "message": "Halted", "run_available": True}
    run = new_run(rows=[{**row, "progress": STARTED["progress"]}])
    run.revisit()
    (listed,) = run.recent()
    assert listed["head"] == "WEB-AAAAAAAA", "no start time is recorded, so no date is shown"
    assert run.screen.attr("#recent-jobs tbody tr button", "title") == ID
    assert listed["cells"][:2] == ["—", "stopped during CP-1"]
    assert run.page.evaluate("document.querySelector('.recent-runs').open") is False
    run.page.evaluate("document.querySelector('#recent-jobs tbody tr button').click()")
    run.settle()
    assert run.text("run-identity") == "WEB-AAAAAAAA"
    assert run.screen.attr("#run-identity .code", "title") == ID
    assert run.hidden("module-stages") is True
    assert run.progress() == ["Stopped: Halted", "Stopped during CP-1."]


def test_a_malformed_row_degrades_to_a_dash_and_does_not_hide_the_others(new_run: Any) -> None:
    bad = {**ROW_RUNNING, "module_details": "bad", "modules": "CP-0 CP-1"}
    run = new_run(rows=[bad, ROW_DONE])
    run.revisit()
    rows = run.recent()
    assert len(rows) == 2
    assert rows[0]["cells"][1] == "running CP-1", "raw id, no ordinal, from the malformed row"
    assert rows[1]["cells"][3] == "3.10"
    assert "Could not load" not in run.text("recent-jobs")
    run.status = dict(ROW_RUNNING)
    run.page.evaluate("document.querySelector('#recent-jobs tbody tr button').click()")
    run.settle()
    assert run.hidden("module-stages") is True
    assert run.progress() == ["Running", "Running CP-1."]


def test_a_failed_render_is_retried_on_the_next_refresh(new_run: Any) -> None:
    rows = [ROW_RUNNING]
    run = new_run(rows=rows)
    rows[0] = {**ROW_RUNNING, "message": "Still working"}
    run.page.evaluate(
        "()=>{const real=document.createElement.bind(document);window.__thrown=false;"
        "document.createElement=(tag,...rest)=>{if(tag==='table'&&!window.__thrown){"
        "window.__thrown=true;throw new Error('render fault');}return real(tag,...rest);};}"
    )
    run.tick()
    assert run.page.evaluate("window.__thrown") is True
    assert run.text("recent-jobs").startswith("Could not load")
    run.tick()
    assert run.screen.exists("#recent-jobs table")


def test_polling_stops_while_new_run_is_hidden_and_resumes_on_return(new_run: Any) -> None:
    # boot.js also keeps a workspace check; only New run's own poll is followed here.
    polls = "[...window.__timers.entries()].filter(([,f])=>f.name==='poll').map(([id])=>id)"
    run = new_run(rows=[ROW_RUNNING])
    run.revisit()
    (poll,) = run.page.evaluate(polls)
    started = len(run.page.evaluate("window.__started"))
    run.page.evaluate("document.getElementById('new-run').hidden=true")
    run.tick()
    assert run.page.evaluate("window.__cleared") == [poll]
    assert run.page.evaluate(polls) == []
    assert len(run.page.evaluate("window.__started")) == started
    run.page.evaluate("location.hash='#W-Reports/list'")
    run.settle()
    run.page.evaluate("location.hash='#W-NewRun/run'")
    run.settle()
    assert run.hidden("new-run") is False
    assert len(run.page.evaluate("window.__started")) == started + 1
    assert len(run.page.evaluate(polls)) == 1


def test_a_failed_list_fetch_is_retried_and_its_error_does_not_stick(new_run: Any) -> None:
    run = new_run(rows=[ROW_RUNNING])
    run.fail_list = True
    run.tick()
    assert run.text("recent-jobs").startswith("Could not load")
    run.tick()
    assert run.screen.exists("#recent-jobs table")


def test_a_null_module_detail_does_not_break_the_row(new_run: Any) -> None:
    details = [None, {"id": "CP-1", "title": "Financial analysis"}]
    run = new_run(rows=[{**ROW_RUNNING, "module_details": details}])
    assert run.recent()[0]["cells"][1] == "running Financial analysis (2 of 2)"


def test_new_run_lives_inside_the_app_and_keeps_what_you_entered(browser: Any) -> None:
    screen = open_app(browser, "W-Library/cases", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    assert screen.hidden("new-run") is True
    assert screen.attr("#context-editor", "src") is None
    assert screen.attr("#library-new-run", "href") == "#W-NewRun/run"
    screen.go("W-NewRun/run")
    assert screen.hidden("new-run") is False and screen.hidden("content") is True
    assert screen.attr("#context-editor", "src") == "context-form.html"
    assert screen.text(".issuer h1") == "New run"
    screen.set_value("#run-budget", "37.50")
    screen.go("W-Reports/list?c=web-1")
    assert screen.hidden("new-run") is True and screen.hidden("content") is False
    screen.go("W-NewRun/run")
    assert screen.eval("document.getElementById('run-budget').value") == "37.50"
    assert screen.eval("document.activeElement===document.querySelector('#context-step h2')")
    assert screen.errors == []
    screen.close()


def test_deliverables_and_module_outputs_link_to_each_other_in_both_directions(
    browser: Any,
) -> None:
    screen = open_app(browser, "W-Reports/list", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    assert screen.texts(".report-built .report-row a") == ["Northbridge · as of 2025-03-31"]
    assert screen.texts(".report-rest .report-row a") == ["Gamma · as of 2024-01-31"]
    screen.go("W-Reports/abc")
    assert (
        screen.attr("#report-preview", "src")
        == "/files/runs/web-1/deliveries/abc/report.html?sha256=r&embedded=1"
    )
    assert screen.attr("#report-preview", "sandbox") == "allow-scripts allow-downloads"
    assert (
        screen.attr(".report-tools a[download]", "href")
        == "/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1"
    )
    assert screen.eval("document.querySelector('.rail').hidden") is False
    rows = screen.texts(".built-from tbody tr")
    assert re.search(r"CP-9No matching run file", rows[1])
    assert re.search(
        r"2 handoffs · 1 with no matching run file", screen.text(".built-from summary")
    )
    to_module = screen.attr(".built-from tbody a", "href")
    assert to_module is not None and to_module.startswith("#CP-0/")
    screen.go(to_module[1:])
    assert screen.eval("current.output") == "web-1/deliveries/abc/CP-0.md"
    back = screen.eval(
        "[...document.querySelectorAll('#module-head a')].find(a=>a.textContent.startsWith('Used in'))"
        ".getAttribute('href')"
    )
    assert (
        screen.eval(
            "[...document.querySelectorAll('#module-head a')].find(a=>a.textContent.startsWith('Used in'))"
            ".textContent"
        )
        == "Used in Northbridge · as of 2025-03-31"
    )
    screen.go(back[1:])
    assert screen.exists("#report-preview")
    assert screen.errors == []
    screen.close()


def test_a_deliverable_with_no_matching_run_still_opens_under_no_run(browser: Any) -> None:
    screen = open_app(browser, "W-Reports/orphan?c=web-1", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    assert screen.eval("current.context") is None
    assert (
        screen.attr("#report-preview", "src")
        == "/files/deliverables/orphan/report.html?sha256=o&embedded=1"
    )
    assert screen.eval("document.querySelector('.workspace-tabs').hidden") is True
    assert re.search(r"No matching run", screen.text(".report-tools"))
    assert not screen.exists(".built-from tbody a")
    screen.click("#rail-search")
    assert screen.eval("current.module") == "W-Library"
    assert screen.active() == "library-query"
    screen.close()


def test_an_uncurated_workspace_works_unnamed_modules_unstructured_handoffs_no_calendar(
    browser: Any,
) -> None:
    screen = open_app(browser, "CP-4A?c=web-1", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    assert screen.eval("current.module") == "CP-4A"
    body = screen.text("body")
    assert not re.search(r"Historical evidence|not current issuer", body)
    assert re.sub(r"\s+", " ", screen.text(".issuer .scope")).strip() == "As of 2025-03-31"
    assert re.search(r"Shown unstructured: Body before first heading", screen.text("#module-head"))
    assert "Body <b>raw</b>" in screen.content(), "raw text is shown, escaped"
    assert not screen.exists("#content b")
    screen.go("CP-0?c=web-1")
    assert "Revenue" in screen.content()
    assert screen.text("#content .record-field div") == "0", "zero stays a zero"
    screen.go("W-Calendar?c=web-1")
    assert re.search(r"No calendar retained for this run", screen.content())
    screen.go("CP-1?c=web-1")
    assert re.search(r"No output found", screen.content())
    assert screen.errors == []
    screen.close()


def test_a_module_with_several_unranked_outputs_does_not_break_the_published_model_page(
    browser: Any,
) -> None:
    store = json.loads(json.dumps(NORTHBRIDGE))
    first = store["outputs"]["web-1/deliveries/abc/CP-0.md"]
    store["outputs"]["web-1/CP-1.md"] = {
        **first,
        "id": "web-1/CP-1.md",
        "module": "CP-1",
        "source": "CP-1.md",
        "label": "CP-1",
    }
    store["outputs"]["web-1/CP-1-v2.md"] = {
        **first,
        "id": "web-1/CP-1-v2.md",
        "module": "CP-1",
        "source": "CP-1-v2.md",
        "label": "V2",
    }
    store["runs"]["web-1"]["modules"]["CP-1"] = {
        "outputs": ["web-1/CP-1.md", "web-1/CP-1-v2.md"],
        "inputs": [],
        "default": None,
    }
    screen = open_app(browser, "W-Library/cases", store, NORTHBRIDGE_REPORTS)
    screen.go("CP-MODEL/publication?c=web-1")
    assert screen.eval("current.module") == "CP-MODEL"
    assert re.search(r"No published model available", screen.content())
    assert screen.errors == []
    screen.close()


def test_names_from_a_workspace_stay_text_on_every_destination(browser: Any) -> None:
    bad = '"><img src=x onerror=alert(1)>'
    store = json.loads(json.dumps(NORTHBRIDGE))
    workspace = json.loads(json.dumps(NORTHBRIDGE_REPORTS))
    for key in ["issuer", "title", "run", "sector", "period"]:
        store["runs"]["web-1"][key] = bad + key
    for output in store["outputs"].values():
        for key in ["label", "source", "case", "period", "scope", "parseError"]:
            if key in output:
                output[key] = bad + key
    for report in workspace["reports"]:
        for key in ["label", "status", "scope"]:
            report[key] = bad + key
        report["files"] = [{"name": bad, "href": "/files/x"}]
        for row in report["builtFrom"]:
            row["source"] = bad
    app = {"workspace": bad, "policy_locked": False, "issues": [bad], "problem": bad}
    screen = open_app(browser, "W-Library/cases", store, workspace, app)
    for route in [
        "W-Library/cases",
        "W-Overview?c=web-1",
        "CP-0?c=web-1",
        "CP-4A?c=web-1",
        "W-Evidence?c=web-1",
        "W-Calendar?c=web-1",
        "CP-OS?c=web-1",
        "W-Reports/list?c=web-1",
        "W-Reports/abc?c=web-1",
        "W-Reports/orphan",
        "W-Settings/workspace",
        "W-Help/help",
        "W-NewRun/run",
    ]:
        screen.go(route)
        assert not screen.exists('img[src="x"]'), route
    screen.close()


def test_an_empty_workspace_opens_on_the_library_with_only_what_can_work(browser: Any) -> None:
    screen = open_app(browser, "CP-1/performance", EMPTY_STORE, EMPTY_WORKSPACE)
    assert screen.eval("current.module") == "W-Library"
    assert re.search(r"No runs in this workspace yet", screen.content())
    assert screen.attr("#library-new-run", "href") == "#W-NewRun/run"
    for label in ["Research workspace", "Run activity", "Reports"]:
        assert screen.eval(f"document.querySelector('.rail a[aria-label=\"{label}\"]').hidden"), (
            label
        )
    for label in ["Issuer library", "New run", "Settings", "Help"]:
        assert not screen.eval(f"document.querySelector('.rail a[aria-label=\"{label}\"]').hidden")
    for route in [
        "W-Overview/overview",
        "W-Calendar",
        "W-Evidence/sources",
        "CP-OS/activity",
        "CP-1",
    ]:
        screen.go(route)
        assert screen.eval("current.module") == "W-Library", route
    screen.go("W-Reports/list")
    assert re.search(r"No deliverables yet", screen.content())
    for route in ["W-NewRun/run", "W-Settings/workspace", "W-Help/help", "W-Help/visuals"]:
        screen.go(route)
    assert screen.errors == []
    screen.close()


def test_settings_shows_the_workspace_and_its_issues_and_respects_the_policy_lock(
    browser: Any,
) -> None:
    app = {
        "workspace": '/research "main"',
        "policy_locked": True,
        "issues": ["runs/x: <b>changed</b>"],
        "problem": "",
    }
    quits: list[dict[str, str]] = []

    def quit_reply(route: Any) -> None:
        quits.append(dict(route.request.headers))
        json_reply({"stopped": True})(route)

    screen = open_app(
        browser,
        "W-Settings/workspace",
        NORTHBRIDGE,
        NORTHBRIDGE_REPORTS,
        app,
        api={"/api/quit": quit_reply},
    )
    assert screen.eval("document.getElementById('workspace-path').value") == '/research "main"'
    assert screen.eval("document.getElementById('workspace-path').disabled") is True
    assert screen.eval("document.getElementById('save-workspace').disabled") is True
    assert re.search(r"managed by your IT configuration", screen.text(".settings"))
    assert not screen.exists(".settings ul b")
    assert "<b>changed</b>" in screen.text(".settings ul")
    screen.click("#quit-library")
    screen.page.wait_for_function("document.getElementById('settings-status').textContent!==''")
    assert len(quits) == 1 and quits[0].get("x-issuer-library") == "1"
    assert re.search(r"Library stopped", screen.text("#settings-status"))
    screen.close()


def test_a_workspace_that_cannot_be_read_says_so_and_the_app_still_opens(browser: Any) -> None:
    app = {
        "workspace": "",
        "policy_locked": False,
        "issues": [],
        "problem": "CP-OS runtime is unavailable",
    }
    screen = open_app(browser, "W-Library/cases", EMPTY_STORE, EMPTY_WORKSPACE, app)
    assert screen.hidden("app-problem") is False
    assert re.search(r"CP-OS runtime is unavailable", screen.text("#app-problem"))
    screen.close()


def test_search_from_an_app_destination_goes_to_the_library_search(browser: Any) -> None:
    screen = open_app(browser, "W-Settings/workspace", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    screen.click("#rail-search")
    assert screen.eval("current.module") == "W-Library" and screen.active() == "library-query"
    screen.close()


def test_the_shell_loads_only_files_the_server_packages() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for relative in re.findall(r'(?:src|href)="([^"#]+)"', html):
        assert (WEB / relative).is_file(), relative
    boot = (WEB / "boot.js").read_text(encoding="utf-8")
    for name in ["views.js", "actions.js", "screen.js"]:
        assert f"'{name}'" in boot and (WEB / name).is_file(), name


# ---- The existing context form with the embedded presentation. ----


class ContextForm:
    def __init__(self, browser: Any) -> None:
        self.page = browser.new_context().new_page()
        self.errors = pageerrors(self.page)
        self.page.add_init_script(
            "window.__messages=[];window.postMessage=v=>{window.__messages.push(v)};"
        )
        serve(self.page, {})
        self.page.goto(f"{ORIGIN}/context-form.html")
        self.page.wait_for_function("typeof update==='function'")

    def set(self, element_id: str, value: str) -> None:
        self.page.evaluate(
            "([i,v])=>{const f=document.getElementById(i);f.value=v;"
            "f.dispatchEvent(new Event('input',{bubbles:true}));}",
            [element_id, value],
        )

    def pick(self, element_id: str) -> None:
        self.page.evaluate(
            "i=>{const c=document.getElementById(i);c.checked=true;"
            "c.dispatchEvent(new Event('change',{bubbles:true}));}",
            element_id,
        )

    def declare(self) -> None:
        self.pick("issue_classification-high_yield")
        self.pick("legal_documents-executed")

    def submit(self) -> dict[str, Any]:
        value: dict[str, Any] = self.page.evaluate(
            "()=>{window.dispatchEvent(new MessageEvent('message',{source:window,data:{type:'cpos:get-context'}}));"
            "return window.__messages.filter(m=>m.type==='cpos:context').at(-1);}"
        )
        return value

    def load(self, folder: Path, text: str) -> None:
        """Choose a saved context file and wait until the form reports it loaded."""
        saved = folder / "context.json"
        saved.write_text(text, encoding="utf-8")
        self.page.set_input_files("#load", saved)
        self.page.wait_for_function(
            "document.getElementById('loadmsg').textContent.startsWith('Loaded')"
        )

    def close(self) -> None:
        assert self.errors == []
        self.page.context.close()


@pytest.fixture
def form(browser: Any) -> Any:
    opened = ContextForm(browser)
    yield opened
    opened.close()


def test_one_required_context_path_retains_all_original_optional_fields(form: ContextForm) -> None:
    for element_id in ["sec1", "sec2", "sec3"]:
        assert form.page.evaluate(f"document.getElementById('{element_id}').hidden") is False
    assert (
        form.page.evaluate("getComputedStyle(document.querySelector('.stepnav')).display") == "none"
    )
    assert form.page.evaluate("document.querySelector('#sec2 details').open") is False
    assert form.page.evaluate("Boolean(document.getElementById('s2-guarantors'))")
    assert len(form.submit()["problems"]) == 4
    assert form.page.evaluate("document.activeElement.id") == "s2-issuer_name"
    form.set("s2-issuer_name", "Synthetic Émetteur")
    form.set("s3-reporting_currency", "EUR")
    form.declare()
    result = form.submit()
    assert result["problems"] == []
    assert result["context"]["identity"]["issuer_name"] == "Synthetic Émetteur"
    assert result["context"]["run"]["reporting_currency"] == "EUR"
    assert result["context"]["identity"]["issue_classification"] == "high_yield"
    assert result["context"]["attachments"]["legal_documents"] == "executed"


def test_context_destinations_use_visible_disclosure_names_instead_of_numbering(
    form: ContextForm,
) -> None:
    labels = form.page.evaluate("[...document.querySelectorAll('summary')].map(n=>n.textContent)")
    for label in ["Deal terms", "Quotes", "Valuation"]:
        assert label in labels
    assert not re.search(
        r"section [457]", form.page.evaluate("document.body.textContent"), re.IGNORECASE
    )
    section_one = form.page.evaluate("document.getElementById('sec1').textContent")
    assert "Shows “Deal terms”" in section_one and "Shows “Quotes”" in section_one
    assert "market cap and net debt in “Valuation”" in form.page.evaluate(
        "document.getElementById('sec2').textContent"
    )


def test_earnings_requirements_and_optional_section_errors_keep_native_validation(
    form: ContextForm,
) -> None:
    form.set("s2-issuer_name", "Synthetic earnings")
    form.declare()
    form.page.evaluate(
        "()=>{const c=document.getElementById('run_type-earnings');c.checked=true;"
        "c.dispatchEvent(new Event('change',{bubbles:true}));}"
    )
    assert any("Current period" in problem for problem in form.submit()["problems"])
    form.set("s3-current_period", "q3-2026")
    form.set("s3-prior_period", "q2-2026")
    assert form.submit()["problems"] == []


def test_loading_a_context_from_before_the_classification_existed_asks_for_it(
    form: ContextForm, tmp_path: Path
) -> None:
    raw = (ROOT / "cases/context/research-minimal.json").read_text(encoding="utf-8")
    saved = json.loads(raw)
    assert "issue_classification" not in saved["identity"]
    form.load(tmp_path, raw)
    message = form.page.evaluate("document.getElementById('loadmsg').textContent")
    assert "Loaded context.json" in message
    assert "issue_classification: not stated in this file" in message
    assert form.page.evaluate("document.activeElement.closest('section').id") == "sec2"
    assert (
        form.page.evaluate(
            "document.querySelectorAll('input[name=\"issue_classification\"]:checked').length"
        )
        == 0
    )
    assert form.submit()["problems"] == ["Issue classification: required."]
    assert (
        form.page.evaluate("document.getElementById('classf').querySelector('.err').textContent")
        == "required."
    )
    form.pick("issue_classification-investment_grade")
    result = form.submit()
    assert result["problems"] == []
    assert result["context"]["identity"]["issuer_name"] == "Northbridge Group"
    assert result["context"]["run"]["as_of"] == "2026-10-31"
    assert (
        result["context"]["attachments"]["legal_documents"]
        == saved["attachments"]["legal_documents"]
    )
    assert result["context"]["identity"]["issue_classification"] == "investment_grade"


# ---- Retained report renderers inside the sandboxed frame contract. ----

DELIVERIES = ROOT / "deliverables"
RETAINED = sorted(path.parent.name for path in DELIVERIES.glob("*/report.html"))


def open_report(browser: Any, folder: str, query: str = "?embedded=1") -> tuple[Any, list[str]]:
    page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
    errors = pageerrors(page)
    serve(page, {})
    page.goto(f"{ORIGIN}/files/deliverables/{folder}/report.html{query}")
    page.wait_for_load_state("load")
    return page, errors


def open_destination(page: Any, destination: str) -> None:
    """Click a report destination and resolve after the report's own hashchange handler ran."""
    page.evaluate(
        "d=>new Promise(resolve=>{window.addEventListener('hashchange',resolve,{once:true});"
        'document.querySelector(`#rail-dests [data-dest="${d}"]`).click();})',
        destination,
    )


@pytest.mark.parametrize("folder", RETAINED)
def test_retained_native_sections_and_evidence_inspector_remain_functional(
    browser: Any, folder: str
) -> None:
    page, errors = open_report(browser, folder)
    issuer = json.loads((DELIVERIES / folder / "view.json").read_text(encoding="utf-8"))["run"][
        "issuer_name"
    ]
    assert issuer in page.evaluate("document.getElementById('nav-issuer').textContent")
    assert page.evaluate("document.querySelectorAll('#rail-dests a').length") == 6
    open_destination(page, "model")
    figure = page.evaluate("Boolean(document.querySelector('.fact-value'))")
    # Only these reports carry a financial model; the others have no figures to inspect.
    assert figure == bool(re.match(r"^(tdg-fy2024-snapshot|erste-source-intake)", folder))
    if figure:
        page.evaluate("document.querySelector('.fact-value').click()")
        assert re.search(
            r"SHA-256", page.evaluate("document.getElementById('inspector-content').textContent")
        )
    open_destination(page, "evidence")
    assert re.search(
        r"Source|Evidence", page.evaluate("document.getElementById('view-root').textContent")
    )
    assert errors == []
    page.context.close()


def test_embedded_presentation_opens_evidence_on_demand_and_restores_the_trigger(
    browser: Any,
) -> None:
    page, errors = open_report(browser, "tdg-fy2024-snapshot-2", "")
    page.add_script_tag(path=str(WEB / "report-adapter.js"))
    evidence_open = "document.body.classList.contains('evidence-open')"
    assert page.evaluate("document.title") == "Issuer report"
    assert page.evaluate("document.querySelector('.brand-mark').textContent") == ""
    assert page.evaluate("document.querySelector('.logo-block')") is None
    assert page.evaluate(evidence_open) is False
    assert page.evaluate("Boolean(document.querySelector('.fig.narrative'))")
    cite = "[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')==='Key findings: C65 (cited C65)')"
    page.evaluate(f"{cite}.click()")
    until(page, evidence_open)
    assert page.evaluate("document.activeElement.id") == "inspector-content"
    page.evaluate("document.querySelector('.inspector-dismiss').click()")
    assert page.evaluate(evidence_open) is False
    assert page.evaluate(f"document.activeElement==={cite}")
    page.evaluate(f"{cite}.click()")
    until(page, evidence_open)
    page.evaluate(
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"
    )
    assert page.evaluate(evidence_open) is False
    assert page.evaluate(f"document.activeElement==={cite}")
    open_destination(page, "model")
    assert page.evaluate(evidence_open) is False
    assert page.evaluate("document.querySelector('.page-head>.eyebrow')") is None
    assert not re.search(
        r"DEPLOY VII|State Street Investment Management",
        page.evaluate("document.getElementById('view-root').textContent"),
    )
    page.evaluate("document.querySelector('.fact-value').click()")
    until(page, evidence_open)
    page.evaluate("document.querySelector('button[aria-label=\"Close inspector\"]').click()")
    until(page, f"!{evidence_open}")
    assert errors == []
    page.context.close()


MODULE_CODE = re.compile(r"\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])")


def test_the_report_preview_shows_module_names_keeps_figures_and_leaves_the_inspector_and_original_exact(
    browser: Any,
) -> None:
    original = DELIVERIES / "tdg-fy2024-snapshot-7" / "report.html"
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    page, errors = open_report(browser, "tdg-fy2024-snapshot-7", "")
    root = "document.getElementById('view-root').textContent"
    assert re.search(r"\bCP-\d", page.evaluate(root)), "the retained report does name modules"
    page.add_script_tag(path=str(WEB / "report-adapter.js"))
    text = page.evaluate(root)
    assert not MODULE_CODE.search(text)
    assert not MODULE_CODE.search(page.evaluate("document.querySelector('.navigator').textContent"))
    assert "Business & governance" in text and "3.14x" in text
    assert "Analyst Interpretation" in text
    open_destination(page, "model")
    assert not MODULE_CODE.search(page.evaluate(root)), "a later destination is named too"
    page.evaluate("document.querySelector('.fact-value').click()")
    until(
        page,
        "/CP-1 \\/ evidence-trace/.test(document.getElementById('inspector-content').textContent)",
    )
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    assert errors == []
    page.context.close()


def test_the_preview_names_every_module_the_app_names_including_absorbed_codes(
    browser: Any,
) -> None:
    adapter = (WEB / "report-adapter.js").read_text(encoding="utf-8")
    match = re.search(r"const MODULE_NAMES=(\{[^}]*\});", adapter)
    assert match
    names: dict[str, str] = json.loads(match.group(1))
    screen = open_app(browser, "W-Library/cases", NORTHBRIDGE, NORTHBRIDGE_REPORTS)
    app: dict[str, str] = screen.eval("Object.fromEntries(groups.flatMap(group=>group[1]))")
    screen.close()
    for code, name in app.items():
        assert names[code] == name, code
    rows = (ROOT / "docs/visualisations/catalogue.csv").read_text(encoding="utf-8").split("\n")[1:]
    for row in filter(None, rows):
        found = re.match(r'^[^,]*,([^,]*),(?:"([^"]*)"|([^,]*))', row)
        assert found
        module, quoted, bare = found.groups()
        for alias in filter(None, re.split(r"[;,\s]+", quoted if quoted is not None else bare)):
            assert names[alias] == app.get(alias, app.get(module)), alias
