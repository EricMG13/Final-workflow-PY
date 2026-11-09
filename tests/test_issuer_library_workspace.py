"""Library and Reports screens over the workspace: library-workspace.test.cjs at dd3dfa18.

The Node suite started the real server on the repository, read /api/workspace and fed the
screens to jsdom. Here the real server code reads the repository in process (Application and
client_of), once per module, and each real page is served that store plus the pinned
2026-11-08 catalogue, then compared with the frozen answer keys. Forged cases change a deep
copy. No provider key is visible to the read and nothing reaches a provider.
Marked browser: real browser proof.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import quote

import pytest
from issuer_library_browser import (
    APP,
    ROOT,
    WEB,
    Screen,
    held,
    json_reply,
    open_app,
    release,
    until,
)
from issuer_library_support import HOST, Application, client_of, locations

pytestmark = pytest.mark.browser

PROVIDER_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")
KEY = json.loads((APP / "designs/library-answer-key.json").read_text(encoding="utf-8"))
PINNED = json.loads((WEB / "testdata/catalogue-2026-11-08.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((WEB / "testdata/library-screening-expected.json").read_text("utf-8"))
RUN_KEYS = (
    "[...document.querySelectorAll('#library-results a.run-link')]"
    ".map(a=>new URLSearchParams(a.getAttribute('href').split('?')[1]).get('c'))"
)
FORECAST = json.loads((APP / "designs/forecast-answer-key.json").read_text(encoding="utf-8"))
CASH = FORECAST["cashflow"]
SNAPSHOT = "tdg-fy2024-snapshot-7"
BAD = "<img src=x onerror=alert(1)>"
HOSTILE = 'x"><b id=pwn>Continue'
ROLE_WORDS = {
    "annual": "Annual handoff",
    "quarter": "Quarterly handoff",
    "forecast": "Forecast handoff",
    "forecast_exact": "Forecast calculations",
    "current_synthesis": "Current synthesis",
}
TEXT = (
    "const d=document,t=e=>e.textContent.replace(/\\s+/g,' ').trim();"
    "const q=s=>d.querySelector(s),qa=s=>[...d.querySelectorAll(s)];"
)
Opener = Callable[..., Screen]


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """What the browser would read from /api/workspace: the real server over this repository."""
    with pytest.MonkeyPatch.context() as patch:
        for name in PROVIDER_KEYS:
            patch.delenv(name, raising=False)
        app = Application(locations(tmp_path_factory.mktemp("library")), str(ROOT), HOST)
        reply = client_of(app).get("/api/workspace")
    assert reply.status_code == 200, f"/api/workspace: {reply.status_code} {reply.text}"
    store: dict[str, Any] = reply.json()
    return store


@pytest.fixture
def show(browser: Any, workspace: dict[str, Any]) -> Iterator[Opener]:
    opened: list[Screen] = []

    def open_at(
        hash_route: str,
        store: dict[str, Any] | None = None,
        catalogue: dict[str, Any] = PINNED,
        held_paths: tuple[str, ...] = (),
    ) -> Screen:
        api = {path: held for path in held_paths} | {
            "/api/catalogue": json_reply(catalogue),
            "/api/workspace": json_reply(workspace if store is None else store),
        }
        opened.append(open_app(browser, hash_route, api=api))
        return opened[-1]

    yield open_at
    release(opened)


def squash(text: str) -> str:
    return " ".join(text.split())


def row_ids(screen: Screen) -> list[str]:
    selector = "#library-results tbody button[data-library-select]"
    return [i or "" for i in screen.attrs(selector, "data-library-select")]


def search(screen: Screen, query: str) -> None:
    screen.set_value("#library-query", query)


def forecast_tab(show: Opener, store: dict[str, Any], run: str) -> Screen:
    """The Forecast tab, opened the way a reader opens it: from the run, through the tab."""
    screen = show(f"W-Overview/overview?c={run}", store)
    href = screen.eval(
        "(()=>{const a=[...document.querySelectorAll('.workspace-tabs a')]"
        ".find(a=>a.textContent.replace(/\\s+/g,' ').trim()==='Forecast');"
        "return a&&a.getAttribute('href');})()"
    )
    assert href, "no Forecast tab"
    screen.go(href[1:])
    return screen


LIST_ROWS = (
    "()=>Object.fromEntries([...document.querySelectorAll('.report-list li')].map(li=>"
    "[li.querySelector('.code').textContent,{text:li.textContent.replace(/\\s+/g,' ').trim(),"
    "badges:[...li.querySelectorAll('.badge')].map(b=>"
    "b.textContent.replace(/\\s+/g,' ').trim()+'|'+b.className)}]))"
)


def test_library_lists_every_catalogue_row_run_folders_open_overview_delivery_rows_open_report(
    show: Opener,
) -> None:
    screen = show("W-Library/cases")
    counts = f"{EXPECTED['row_count']['value']} of {EXPECTED['row_count']['value']} runs"
    assert (
        squash(screen.text("#library-count"))
        == f"{counts} · {EXPECTED['issuer_count']['value']} issuers"
    )
    folder_ids, delivery_ids = EXPECTED["run_folder_rows"]["ids"], EXPECTED["delivery_rows"]["ids"]
    assert sorted(row_ids(screen)) == sorted([*folder_ids, *delivery_ids])
    folders = screen.eval(f"{RUN_KEYS}.map(k=>contexts[k].folder)")
    assert sorted(folders) == sorted(folder_ids), "one Overview link per run folder"
    hrefs = screen.page.evaluate(
        "ids=>ids.map(id=>document.querySelector("
        '`#library-results tr:has([data-library-select="${id}"]) a.report-link`)'
        "?.getAttribute('href')||'')",
        delivery_ids,
    )
    for run_id, href in zip(delivery_ids, hrefs, strict=True):
        assert re.match(r"#W-(Reports|Forecast)/", href), f"{run_id}: {href!r}"


def test_library_search_finds_every_run_of_the_issuer_searched(show: Opener) -> None:
    screen = show("W-Library/cases")
    for query, want in KEY["library"]["search"].items():
        search(screen, query)
        assert sorted(screen.eval(RUN_KEYS)) == sorted(want), f'search "{query}"'
    # A search that keeps the served issuer apart from the recorded terms finds these.
    for query, run_id in [
        ("FROTO ford-otosan-2024-001", "ford-otosan-2024-001"),
        ("LMI lmi-2014-001", "lmi-2014-001"),
    ]:
        search(screen, query)
        assert row_ids(screen) == [run_id], f"a query spanning issuer and id: {query}"
    case = EXPECTED["filter_cases"]["c_search_issuer_name"]
    search(screen, case["filters"]["search"])
    assert row_ids(screen) == case["expected_ids"]


def test_a_metric_with_more_than_20_decimals_is_shown_as_served_and_does_not_blank_the_other_rows(
    show: Opener,
) -> None:
    forged, long = copy.deepcopy(PINNED), "1." + "0" * 100 + "1"
    next(r for r in forged["real"] if r["id"] == "tdg-002")["metrics"]["ebitda"]["value"] = long
    screen = show("W-Library/cases", catalogue=forged)
    assert len(row_ids(screen)) == len(forged["real"])
    screen.click('[data-library-select="tdg-002"]')
    assert long in squash(screen.text("#run-detail"))


def test_reports_for_a_run_list_the_same_issuer_by_identity_not_by_display_name(
    show: Opener,
) -> None:
    screen = show("W-Reports/list?c=tdg-002")
    want = KEY["reports"]["tdg-002"]
    for group, expected in [
        ("report-built", "built"),
        ("report-other", "sameIssuer"),
        ("report-rest", "otherIssuers"),
    ]:
        shown = screen.texts(f".{group} .report-list li .code")
        assert sorted(shown) == sorted(want[expected]), group


def test_every_report_row_shows_the_reports_declared_acceptance_state_and_qualification(
    show: Opener,
) -> None:
    screen = show("W-Reports/list?c=tdg-002")
    rows = screen.eval(LIST_ROWS)
    for report_id, expected in KEY["reports"]["byId"].items():
        assert report_id in rows, f"{report_id} has no row"
        shown = rows[report_id]["text"]
        assert expected["state"] in shown, (
            f"{report_id}: {expected['state']} missing from {shown!r}"
        )
        assert expected["qualification"] in shown, (
            f"{report_id}: {expected['qualification']} missing from {shown!r}"
        )


def test_the_reading_toolbar_shows_the_curated_status_with_the_acceptance_state(
    show: Opener,
) -> None:
    def toolbar(report_id: str) -> str:
        return squash(show(f"W-Reports/{report_id}?c=tdg-002").text(".report-tools"))

    latest, record = toolbar(SNAPSHOT), KEY["reports"]["byId"][SNAPSHOT]
    for part in [KEY["reports"]["status"][SNAPSHOT], record["state"], record["qualification"]]:
        assert part in latest, f"{part} missing from {latest!r}"
    assert KEY["reports"]["status"]["tdg-fy2024-snapshot"] in toolbar("tdg-fy2024-snapshot")


def test_the_reading_toolbar_separates_the_status_from_the_acceptance_badge(
    show: Opener,
) -> None:
    screen = show(f"W-Reports/{SNAPSHOT}?c=tdg-002")
    parts = screen.eval(
        "(()=>{const sep=document.querySelector('.report-tools .tool-sep');if(!sep)return null;"
        "const group=sep.nextElementSibling;"
        "return {before:sep.previousElementSibling.textContent,"
        "acceptance:group.classList.contains('acceptance'),"
        "badge:group.firstElementChild.classList.contains('badge'),"
        "muted:group.querySelector('.muted').textContent,hidden:sep.getAttribute('aria-hidden')};})()"
    )
    assert parts, "no separator"
    assert parts["before"] == KEY["reports"]["status"][SNAPSHOT]
    # The badge and its qualification text are one inline group, so they wrap as a unit.
    assert parts["acceptance"] and parts["badge"]
    assert parts["muted"].startswith("Analytical qualification")
    assert parts["hidden"] == "true"


def test_a_model_source_with_no_valid_path_or_hash_still_renders_flagged_with_no_hash(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    model = next(m for m in forged["models"] if m["id"] == "tdg-model-3")
    model["sources"][0].update(sha256=None, changed=None)
    screen = forecast_tab(show, forged, "tdg-002")
    cells = screen.eval(
        "[...document.querySelector('.forecast-built tbody tr').children].map(c=>c.textContent)"
    )
    assert cells[3] == ""
    assert squash(cells[4]) == "Invalid path or hash"


def test_each_deliverable_listed_on_the_run_overview_shows_its_reports_state(
    show: Opener,
) -> None:
    screen = show("W-Overview/overview?c=tdg-002")
    entries = screen.eval(
        "[...document.querySelectorAll('.summary-deliverables .deliverable')].map(e=>"
        "[e.querySelector('a').getAttribute('href').split('?')[0].split('/').at(-1),"
        "e.textContent.replace(/\\s+/g,' ').trim()])"
    )
    assert sorted(i for i, _ in entries) == sorted(KEY["reports"]["tdg-002"]["built"])
    for report_id, shown in entries:
        expected = KEY["reports"]["byId"].get(report_id)
        assert expected, f"{report_id} not in the answer key"
        assert expected["state"] in shown, (
            f"{report_id}: {expected['state']} missing from {shown!r}"
        )
        assert expected["qualification"] in shown, f"{report_id}: qualification missing"


def test_a_synthetic_delivery_shows_accepted_unrecorded_and_unknown_states_in_exact_words(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    issuer = next(r for r in forged["reports"] if r["id"] == SNAPSHOT)["issuerKey"]
    first, second, third, *_ = (r for r in forged["reports"] if r["issuerKey"] == issuer)
    first.update(mode="accepted", qualification="qualified")
    second.update(mode=None, qualification="mystery")
    third.update(mode="draft", qualification=None)
    screen = show("W-Reports/list?c=tdg-002", forged)
    rows = screen.eval(LIST_ROWS)
    assert re.search(r"Accepted.*Analytical qualification: qualified", rows[first["id"]]["text"])
    assert not re.search(r"not accepted|not recorded", rows[first["id"]]["text"])
    unrecorded = r"Acceptance not recorded.*Analytical qualification not recorded"
    assert re.search(unrecorded, rows[second["id"]]["text"])
    assert re.search(unrecorded, rows[third["id"]]["text"])
    assert "Accepted|badge badge-gray" in rows[first["id"]]["badges"], rows[first["id"]]["badges"]
    for row in (second, third):
        assert "Acceptance not recorded|badge badge-gray" in rows[row["id"]]["badges"], row["id"]
    candidate = screen.eval(
        "[...document.querySelectorAll('.report-list li .badge')]"
        ".find(b=>b.textContent.replace(/\\s+/g,' ').trim()==='Candidate · not accepted')"
        "?.classList.contains('badge-gray')"
    )
    assert candidate, "candidate state is a grey badge"
    assert not screen.exists(".report-list .badge-attention"), "no report row uses amber"


Store = dict[str, Any]
NM = "n.m.: not modelled in the calculation record"
UNRECORDED_CELL = {"exact": None, "display": "n.a.", "status": "na"}


@pytest.fixture
def forged(workspace: Store) -> Store:
    return copy.deepcopy(workspace)


def probe(screen: Screen, body: str, arg: Any = None) -> Any:
    """Run a function body in the page with d, t (collapsed text), q and qa (query helpers)."""
    return screen.page.evaluate("(a)=>{" + TEXT + body + "}", arg)


def choose(screen: Screen, model_id: str) -> None:
    screen.set_value("#model-select", model_id, "change")
    until(screen.page, f"current.section===({json.dumps(model_id)})")


def model_of(store: Store, model_id: str) -> Store:
    return next(m for m in store["models"] if m["id"] == model_id)


def rename(store: Store, old: str, new: str) -> Store:
    model_of(store, old)["id"] = new
    for other in store["models"]:
        if other.get("previous") == old:
            other["previous"] = new
    return store


CASHFLOW_READ = """
const s=q('.forecast-cashflow'),h2=s.querySelector('h2'),n=s.querySelector('.cashflow-notes');
const na=s.querySelector('.cashflow-na'),all=x=>[...s.querySelector('table').querySelectorAll(x)];
const heads=all('thead tr'),body=all('tbody tr'),band=tr=>tr.classList.contains('band-row');
const rows=body.filter(tr=>!band(tr)),tds=tr=>[...tr.querySelectorAll('td')];
const heads0=[...heads[0].querySelectorAll('th[colspan]')];
const heads1=[...heads[1].querySelectorAll('th')];
return {model:q('#model-select').value,h2:h2.textContent,caption:h2.nextElementSibling.textContent,
groups:heads0.map(t),spans:heads0.map(th=>Number(th.getAttribute('colspan'))),columns:heads1.map(t),
ytd:heads1.filter(th=>th.textContent.endsWith(' (YTD)'))
.map(th=>[th.querySelector('span.col-sub')?.textContent,th.querySelectorAll('*').length]),
bands:body.filter(band).map(t),labels:rows.map(tr=>t(tr.querySelector('th'))),
displays:rows.map(tr=>tds(tr).map(td=>td.textContent)),
beforeFirst:body.map((tr,i)=>band(tr)?[t(tr),t(body[i+1].querySelector('th'))]:null).filter(Boolean),
titles:rows.map(tr=>tds(tr).map(td=>td.getAttribute('title'))),
aria:rows.map(tr=>tds(tr).map(td=>td.getAttribute('aria-label'))),
notes:[...n.querySelectorAll('li')].map(li=>li.textContent),
place:[n.previousElementSibling===s.querySelector('.table-scroll'),n.nextElementSibling===na],
na:[...na.querySelectorAll('li')].map(t),
disclosure:[na.tagName,na.hasAttribute('open'),t(na.querySelector('summary'))],
dashes:all('tbody td').filter(td=>td.textContent==='—').length,
totals:rows.filter(tr=>tr.classList.contains('total-row')).map(tr=>t(tr.querySelector('th'))),
limits:qa('.forecast-limits li').map(t),limitsHeading:q('.forecast-limits h2').textContent};
"""
FORECAST_READ = """
const tools=q('.forecast-tools'),as=q('.forecast-assumptions'),built=q('.forecast-built');
const rows=[...built.querySelectorAll('tbody tr')].map(tr=>{
  const c=[...tr.querySelectorAll('td')],link=c[1].querySelector('a');
  const b=c[3].querySelector('.badge');
  return {role:tr.querySelector('th').textContent,run:c[0].querySelector('span.code')?.textContent,
  sha:c[2].textContent,status:t(c[3]),badge:b&&[...b.classList],link:link&&link.textContent,
  href:link&&link.getAttribute('href'),file:c[1].textContent,
  title:c[1].querySelector('[title]')?.getAttribute('title')};});
return {options:qa('#model-select option').map(o=>o.textContent),
selected:qa('#model-select option').filter(o=>o.selected).map(o=>o.textContent),
badges:[...tools.querySelectorAll('.badge')].map(b=>b.textContent),
muted:[...tools.querySelectorAll('.muted')].map(b=>b.textContent),
download:t(tools.querySelector('a[download]')),scope:q('.forecast-scope').textContent,
input:q('.forecast-input').textContent,revision:q('.forecast-revision').textContent,
headings:qa('.forecast > section > h2').map(t),registerHeading:as.querySelector('h3').textContent,
intro:t(as.querySelector('.register-intro')),
register:[...as.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(c=>c.textContent)),
registerHref:as.querySelector('a.text-action').getAttribute('href'),
registerLink:t(as.querySelector('a.text-action')),
builtHeads:[...built.querySelectorAll('thead th')].map(t),rows,
attempts:t(built.querySelector('.forecast-attempts')),
attemptsAfterTable:built.querySelector('.table-scroll').nextElementSibling
===built.querySelector('.forecast-attempts'),
sandbox:q('#model-preview').getAttribute('sandbox'),src:q('#model-preview').getAttribute('src'),
dataSrc:q('#model-preview').dataset.src};
"""
# Sets the disclosure's open state and resolves on the toggle event the browser fires for it.
GIVE_UP = "new Promise((_,j)=>setTimeout(()=>j(new Error(%r)),2000))"
TOGGLE = (
    "async o=>{const x=document.querySelector('details.model-original');"
    "const seen=new Promise(r=>x.addEventListener('toggle',()=>r(x.open),{once:true}));"
    f"x.open=o;return await Promise.race([seen,{GIVE_UP % 'toggle never fired'}]);}}"
)
# Fires after any watch timer armed at render (4x the watch timeout); bounded like `until`.
SENTINEL = (
    "()=>Promise.race([new Promise(r=>setTimeout(r,4*window.DESIGN_FRAME_TIMEOUT_MS)),"
    f"{GIVE_UP % 'sentinel timer never fired'}])"
)
BUILT_HEADS = ["Role", "Run", "Source", "SHA-256 prefix", "Status"]
HEADINGS = [
    "Cash flow model",
    "Assumptions and their rationale",
    "Model limitations",
    "Why this model was built",
    "Built from",
]
ATTEMPTS = (
    "These files come from different attempts: CP-1-attempt-2.md (attempt 2), "
    "CP-2G-attempt-2.md (attempt 2), CP-2G-attempt-1-calculations.json (attempt 1)"
)
MODEL_URL = r"/files/deliverables/tdg-model-3/model\.html\?sha256=[0-9a-f]{64}&embedded=1"


@pytest.mark.parametrize("run", [r for r, e in FORECAST["runs"].items() if e["models"]])
def test_forecast_for_run_shows_its_models_state_reason_and_sources(
    show: Opener, workspace: Store, run: str
) -> None:
    want, screen = FORECAST["runs"][run], forecast_tab(show, workspace, run)
    got = probe(screen, FORECAST_READ)
    assert got["options"] == want["options"]
    assert got["selected"] == [want["selected"]]
    assert (got["badges"], got["muted"]) == ([want["state"]], [want["qualification"]])
    assert got["download"] == "Download original HTML"
    assert (got["scope"], got["input"]) == (want["scope"], want["inputContract"])
    assert got["revision"] == want["revisionNote"]
    assert got["headings"] == HEADINGS
    assert (got["registerHeading"], got["intro"]) == (
        want["registerHeading"],
        want["registerIntro"],
    )
    assert [r[0] for r in got["register"]] == want["registerIds"]
    assert got["register"] == want["registerRows"]
    assert got["builtHeads"] == BUILT_HEADS
    assert [r["role"] for r in got["rows"]] == [ROLE_WORDS[b["role"]] for b in want["builtFrom"]]
    for row, b in zip(got["rows"], want["builtFrom"], strict=True):
        changed = "Changed since publication" if b["changed"] else "Matches publication"
        assert (row["run"], row["sha"], row["status"]) == (
            b["path"].split("/")[1],
            b["sha256Prefix"],
            changed,
        ), b["role"]
        assert ("badge-attention" if b["changed"] else "badge-gray") in (row["badge"] or []), b[
            "role"
        ]
        if b["output"] is None:
            assert row["link"] is None, f"{b['role']} must not link"
            assert row["file"] == b["path"].split("/")[-1], b["role"]
            assert row["title"] == b["path"], f"{b['role']} keeps the full path in a title"
        else:
            assert row["link"] == b["output"].split("/")[-1], b["role"]
    assert got["attempts"] == ATTEMPTS
    assert got["attemptsAfterTable"] is True
    assert got["sandbox"] == "allow-scripts allow-downloads"
    assert got["src"] is None, "the frame has no address until the disclosure is opened"
    assert re.fullmatch(MODEL_URL, got["dataSrc"])
    assert f"sha256={want['modelSha256']}" in got["dataSrc"]
    assert got["registerLink"] == "Open the full forward credit model output"
    links = [(got["registerHref"], want["registerLinkOutput"])]
    links += [
        (r["href"], b["output"])
        for r, b in zip(got["rows"], want["builtFrom"], strict=True)
        if b["output"]
    ]
    for href, output in links:  # Each link opens the output it names, in the run that holds it.
        screen.go(href[1:])
        assert screen.eval("current.output") == output
        screen.go(f"W-Forecast/forecast?c={run}")


def test_forecast_for_tdg_002_lays_out_the_cash_flow_model(show: Opener, workspace: Store) -> None:
    got = probe(forecast_tab(show, workspace, "tdg-002"), CASHFLOW_READ)
    assert got["model"] == CASH["model"]
    assert (got["h2"], got["caption"]) == ("Cash flow model", CASH["caption"])
    assert (got["groups"], got["spans"]) == (CASH["groups"], [2, 3, 3, 3])
    assert got["columns"] == CASH["columns"]
    assert got["ytd"] == [["(YTD)", 1], ["(YTD)", 1]]  # "(YTD)" sits in its own span
    assert got["bands"] == CASH["bands"]
    assert got["labels"] == [r["label"] for r in CASH["rows"]]
    for label, shown, row in zip(got["labels"], got["displays"], CASH["rows"], strict=True):
        assert shown == row["display"], label
    for band, first in got["beforeFirst"]:  # Each band heading sits directly before its first row.
        assert first == next(r["label"] for r in CASH["rows"] if r["band"] == band)
    for name, exact in CASH["titles"].items():
        label, column, *group = name.split("|")
        at = [
            i
            for i, c in enumerate(CASH["columns"])
            if c == column and (not group or CASH["columnGroups"][i] == group[0])
        ]
        assert len(at) == 1, f"{name} must name exactly one column"
        assert got["titles"][got["labels"].index(label)][at[0]] == exact, name
    assert (got["notes"], got["place"]) == (CASH["notes"], [True, True])
    assert got["na"] == CASH["notAvailable"]
    count = len(CASH["notAvailable"])
    assert got["disclosure"] == ["DETAILS", False, f"Why cells show n.a. ({count} lines)"]
    assert (got["dashes"], got["totals"]) == (0, CASH["totals"])
    for i, row in enumerate(CASH["rows"]):
        for j, shown in enumerate(row["display"]):
            want = {"n.a.": f"n.a.: {got['titles'][i][j]}", "n.m.": NM}.get(shown)
            assert got["aria"][i][j] == want, f"{row['label']} / {CASH['columns'][j]}"
    assert any(NM in line for line in got["aria"]), "some cell is n.m."
    assert (got["limits"], got["limitsHeading"]) == (CASH["limits"], "Model limitations")


@pytest.mark.parametrize("run", ["tdg-model-001", "tdg-003"])
def test_forecast_for_run_shows_the_same_models_caption_and_first_row(
    show: Opener, workspace: Store, run: str
) -> None:
    got = probe(
        forecast_tab(show, workspace, run),
        "const f=q('.forecast-cashflow tbody tr:not(.band-row)');"
        "return {model:q('#model-select').value,"
        "caption:q('.forecast-cashflow h2').nextElementSibling.textContent,"
        "label:t(f.querySelector('th')),cells:[...f.querySelectorAll('td')].map(td=>td.textContent)};",
    )
    first = CASH["rows"][0]
    want = {"model": CASH["model"], "caption": CASH["caption"]}
    assert got == want | {"label": first["label"], "cells": first["display"]}


def test_a_model_with_no_calculation_record_says_so_hostile_text_stays_text(
    show: Opener, forged: Store
) -> None:
    quoted = 'x" onmouseover="alert(1)'
    model_of(forged, "tdg-model-2")["cashflow"] = None
    flow = model_of(forged, "tdg-model-3")["cashflow"]
    flow["limits"] = flow["notes"] = [BAD]
    flow["rows"][0]["cells"][1] = UNRECORDED_CELL | {"reason": BAD}
    flow["rows"][0]["cells"][2] = UNRECORDED_CELL | {"reason": quoted}
    flow["units"] = None
    screen = forecast_tab(show, forged, "tdg-002")
    got = probe(
        screen,
        "const c=qa('.cashflow td'),x=c[2];"
        "return {caption:q('.forecast-cashflow h2').nextElementSibling.textContent,"
        "limit:q('.forecast-limits li').textContent,"
        "notes:qa('.cashflow-notes li').map(li=>li.textContent),"
        "na:qa('.cashflow-na li').map(li=>li.textContent).slice(0,1),"
        "aria:c[1].getAttribute('aria-label'),quoted:x.getAttribute('aria-label'),"
        "onmouseover:x.hasAttribute('onmouseover'),names:[...x.attributes].map(a=>a.name).sort(),"
        "allowed:['aria-label','class','title'].filter(n=>x.hasAttribute(n)).sort(),"
        "img:!!q('.forecast-cashflow img,.forecast-limits img'),onerror:!!q('[onerror]')};",
    )
    assert got["caption"] == (
        "Units not recorded · Q1 FY2024 (YTD) to FY2027E · history as retained in the handoffs; "
        "forecasts are conditional illustrations from the calculation record"
    )
    assert (got["limit"], got["notes"]) == (BAD, [BAD])
    assert got["na"] == [f"Not available: Power & Control — {CASH['columns'][1]}: {BAD}"]
    assert got["aria"] == f"n.a.: {BAD}"
    # A quote in a reason must stay inside the one aria-label attribute.
    assert (got["quoted"], got["onmouseover"]) == (f"n.a.: {quoted}", False)
    assert got["names"] == got["allowed"]
    assert (got["img"], got["onerror"]) == (False, False)
    choose(screen, "tdg-model-2")
    after = probe(
        screen,
        "return {table:!!q('.forecast-cashflow table'),p:q('.forecast-cashflow p').textContent,"
        "limits:!!q('.forecast-limits')};",
    )
    assert after == {
        "table": False,
        "p": "This model has no readable calculation record.",
        "limits": False,
    }


def test_choosing_another_model_in_the_forecast_tab_shows_that_model(
    show: Opener, workspace: Store
) -> None:
    screen = forecast_tab(show, workspace, "tdg-002")
    choose(screen, "tdg-model-1")
    shown, src = probe(
        screen,
        "return [q('#model-select').selectedOptions[0].textContent,"
        "q('#model-preview').dataset.src];",
    )
    assert shown == FORECAST["runs"]["tdg-002"]["options"][2]
    assert re.search(r"tdg-model-1/model\.html", src), src


@pytest.mark.parametrize("run", [r for r, e in FORECAST["runs"].items() if not e["models"]])
def test_forecast_for_run_says_no_model_was_published_and_lists_other_models(
    show: Opener, workspace: Store, run: str
) -> None:
    want = FORECAST["runs"][run]
    got = probe(
        forecast_tab(show, workspace, run),
        "const o=q('.forecast-other');"
        "return {heading:q('#content .missing-state h2')?.textContent,"
        "present:[!!q('#model-select'),!!q('#model-preview')],"
        "otherHeading:o&&o.querySelector('h2').textContent,"
        "others:o&&[...o.querySelectorAll('li > a, li > span:first-child')]"
        ".map(e=>e.textContent)};",
    )
    assert got["heading"] == FORECAST["emptyHeading"]
    assert got["present"] == [False, False]
    assert got["otherHeading"] == want["otherHeading"]
    if want["otherHeading"] is not None:
        assert got["others"] == want["others"]


RATIOS = [
    ("percent", "0.5", "50.0000%"),
    ("percent", "0.123456789", "≈ 12.3457%"),
    ("percent", "-0.12345", "-12.3450%"),
    ("percent", "-0.0000000001", "≈ 0.0000%"),
    ("percent", "1E-4", "0.0100%"),
    ("multiple", "4.79755", "≈ 4.7976x"),
    ("multiple", "3", "3.0000x"),
    ("money", "1221.04741248", "1221.04741248"),
]


def test_ratio_titles_show_four_decimals_with_the_sign_only_where_rounding_changed_it(
    show: Opener, forged: Store
) -> None:
    rows = model_of(forged, "tdg-model-3")["cashflow"]["rows"]
    pick = {k: next(r for r in rows if r["kind"] == k) for k in ("percent", "multiple", "money")}
    for i, (kind, exact, _) in enumerate(RATIOS):
        pick[kind]["cells"][i] = {
            "exact": exact,
            "display": "shown",
            "reason": None,
            "status": "value",
        }
    titles = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return Object.fromEntries(qa('.cashflow tbody tr:not(.band-row)').map(tr=>"
        "[t(tr.querySelector('th')),[...tr.querySelectorAll('td')].map(td=>td.getAttribute('title'))]));",
    )
    for i, (kind, exact, title) in enumerate(RATIOS):
        assert titles[pick[kind]["label"]][i] == title, f"{pick[kind]['label']} {exact}"


def test_built_from_names_an_unknown_role_by_its_token_and_adds_no_note_for_one_attempt(
    show: Opener, forged: Store
) -> None:
    sources = model_of(forged, "tdg-model-3")["sources"]
    sources[0]["role"] = "<b>mystery</b>"
    for source in sources:
        if source.get("path"):
            source["path"] = re.sub(r"-attempt-\d+", "-attempt-2", source["path"], count=1)
    got = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return [q('.forecast-built tbody th').textContent,!!q('.forecast-built tbody th b'),"
        "!!q('.forecast-attempts')];",
    )
    assert got == ["<b>mystery</b>", False, False]


def test_a_report_whose_qualification_is_unrun_reads_not_run_and_no_badge_is_amber(
    show: Opener, forged: Store
) -> None:
    report = next((r for r in forged["reports"] if r["qualification"] == "unrun"), None)
    assert report, "the workspace holds an unrun report"
    screen = show("W-Reports/list?c=tdg-002", forged)
    shown = screen.eval(LIST_ROWS)[report["id"]]["text"]
    assert re.search(r"Analytical qualification: not run", shown)
    assert not re.search(r"unrun", shown)
    assert not screen.exists(".badge-attention")


def test_model_text_from_a_workspace_stays_text_and_a_changed_source_says_so(
    show: Opener, forged: Store
) -> None:
    model = model_of(forged, "tdg-model-3")
    model.update(scope=BAD, revisionNote=BAD)
    model["register"]["rows"][0][1] = BAD
    model["sources"][0]["changed"] = True
    got = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return {scope:q('.forecast-scope').textContent,"
        "revision:q('.forecast-revision').textContent,"
        "cell:q('.forecast-assumptions tbody tr').children[1].textContent,"
        "bad:[!!q('#content img[src=\"x\"]'),!!q('#content [onerror]')],"
        "status:qa('.forecast-built tbody tr').map(tr=>t(tr.children[4]))};",
    )
    assert (got["scope"], got["cell"]) == (BAD, BAD)
    assert got["revision"] == f"Revision note: {BAD}"
    assert got["bad"] == [False, False]
    assert got["status"] == ["Changed since publication", *["Matches publication"] * 4]


def test_the_model_frame_is_not_loaded_or_watched_until_its_disclosure_is_opened(
    show: Opener,
) -> None:
    # The model file is never answered, so the frame cannot load and the watch must time out.
    screen = show(
        "W-Overview/overview?c=tdg-002", held_paths=("/files/deliverables/tdg-model-3/model.html",)
    )
    screen.eval("window.DESIGN_FRAME_TIMEOUT_MS=20")
    screen.go("W-Forecast/forecast?c=tdg-002")
    parts = (
        "const x=q('details.model-original'),f=q('#model-preview');"
        "const s=x.querySelector('.frame-status');"
    )
    state = (
        "return {open:x.open,summary:t(x.querySelector('summary')),inside:f.closest('details')===x,"
    )
    got = probe(screen, parts + state + "src:f.getAttribute('src')};")
    assert got == {
        "open": False,
        "summary": "Published model (original HTML)",
        "inside": True,
        "src": None,
    }
    screen.page.evaluate(SENTINEL)
    assert probe(screen, parts + "return [s.hidden,t(s)];") == [True, ""], "no watch has started"
    assert screen.page.evaluate(TOGGLE, True) is True
    until(screen.page, "!!document.getElementById('model-preview').getAttribute('src')")
    until(screen.page, "/did not load/.test(document.querySelector('.frame-status').textContent)")
    got = probe(
        screen,
        parts + "return {same:f.getAttribute('src')===f.dataset.src,text:t(s),"
        "href:s.querySelector('a').getAttribute('href')};",
    )
    assert got["same"] is True
    assert got["text"] == "The model did not load. Download original HTML Retry"
    assert re.search(r"model\.html\?sha256=[0-9a-f]{64}&download=1$", got["href"])
    assert probe(screen, parts + "f.dispatchEvent(new Event('load'));return s.hidden;") is True
    src = screen.attr("#model-preview", "src")  # Reopening starts no second watch.
    assert screen.page.evaluate(TOGGLE, False) is False
    assert screen.page.evaluate(TOGGLE, True) is True
    assert screen.attr("#model-preview", "src") == src
    assert probe(screen, parts + "return s.hidden;") is True, "no second watch started"


def test_a_model_id_with_markup_renders_no_element_of_its_own(show: Opener, forged: Store) -> None:
    rename(forged, "tdg-model-3", HOSTILE)
    for hash_route in [
        "W-Overview/overview?c=tdg-002",
        "W-Forecast/forecast?c=tdg-002",
        "W-Library/cases",
        "W-Settings/workspace",
    ]:
        assert not show(hash_route, forged).exists("[id^=pwn]"), hash_route
    screen = forecast_tab(show, forged, "tdg-002")
    assert not screen.exists("[id^=pwn]"), "Forecast tab"
    section = quote(HOSTILE, safe="-_.!~*'()")
    hrefs = [h or "" for h in screen.attrs("a", "href")]
    assert any(h.startswith(f"#W-Forecast/{section}") for h in hrefs), "one encoded section"


def test_catalogue_text_with_markup_renders_no_element_of_its_own(show: Opener) -> None:
    catalogue = copy.deepcopy(PINNED)
    run = next(r for r in catalogue["real"] if r["id"] == "tdg-002")
    for field in ["name", "title", "issuer", "sector", "workflow", "summary", "period"]:
        run[field] = HOSTILE
    run["gaps"] = [HOSTILE]
    run["ratings"] = [{"label": HOSTILE, "date": HOSTILE, "source": ""}]
    run["artifacts"][0].update(label=HOSTILE, issue=HOSTILE)
    run["metrics"]["leverage"].update(basis=HOSTILE, source='s"><b id=pwn2>')
    quote_row = {"path": HOSTILE, "line": 1, "quote": HOSTILE, "href": HOSTILE}
    catalogue["sources"] = {'s"><b id=pwn2>': quote_row}
    screen = show("W-Library/cases", catalogue=catalogue)
    screen.click('[data-library-select="tdg-002"]')
    assert not screen.exists("[id^=pwn]")
    assert HOSTILE in squash(screen.text("#run-detail")), "shown as text"


def test_a_report_id_with_markup_renders_no_element_of_its_own(show: Opener, forged: Store) -> None:
    forged["reports"][0]["id"] = HOSTILE
    for hash_route in [
        "W-Library/cases",
        "W-Reports/list?c=tdg-002",
        "W-Overview/overview?c=tdg-002",
    ]:
        assert not show(hash_route, forged).exists("[id^=pwn]"), hash_route


@pytest.mark.parametrize("model_id", ["m é 1", "a%20b", "Société modèle", "a/b?c=1#x"])
def test_a_model_id_chosen_in_the_model_select_shows_that_model(
    show: Opener, forged: Store, model_id: str
) -> None:
    want = model_of(rename(forged, "tdg-model-1", model_id), model_id)
    screen = forecast_tab(show, forged, "tdg-002")
    choose(screen, model_id)
    got = probe(
        screen,
        "return {value:q('#model-select').value,src:q('#model-preview').dataset.src,"
        "scope:q('.forecast-scope')?.textContent??null,section:parseRoute().section};",
    )
    assert got["value"] == model_id
    assert want["href"].split("?")[0] in got["src"]
    assert (got["scope"], got["section"]) == (want["scope"], model_id)
