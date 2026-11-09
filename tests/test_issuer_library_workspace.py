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
from urllib.parse import parse_qs, quote

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
TEXT = "const t=e=>e.textContent.replace(/\\s+/g,' ').trim();"
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


def probe(screen: Screen, body: str, arg: Any = None) -> Any:
    """Run a function body in the page with `d` and `t` (whitespace-collapsed text) defined."""
    return screen.page.evaluate("(a)=>{" + TEXT + "const d=document;" + body + "}", arg)


def choose(screen: Screen, model_id: str) -> None:
    screen.set_value("#model-select", model_id, "change")
    until(screen.page, f"current.section===({json.dumps(model_id)})")


def model_of(store: dict[str, Any], model_id: str) -> dict[str, Any]:
    return next(m for m in store["models"] if m["id"] == model_id)


def renamed(store: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    forged = copy.deepcopy(store)
    model_of(forged, old)["id"] = new
    for other in forged["models"]:
        if other.get("previous") == old:
            other["previous"] = new
    return forged


CASHFLOW_READ = """
const s=d.querySelector('.forecast-cashflow'),table=s.querySelector('table');
const heads=[...table.querySelectorAll('thead tr')],body=[...table.querySelectorAll('tbody tr')];
const band=tr=>tr.classList.contains('band-row'),rows=body.filter(tr=>!band(tr));
const tds=tr=>[...tr.querySelectorAll('td')],notes=s.querySelector('.cashflow-notes');
const na=s.querySelector('.cashflow-na'),h2=s.querySelector('h2');
return {model:d.querySelector('#model-select').value,h2:h2.textContent,
caption:h2.nextElementSibling.textContent,
groups:[...heads[0].querySelectorAll('th[colspan]')].map(t),
spans:[...heads[0].querySelectorAll('th[colspan]')].map(th=>Number(th.getAttribute('colspan'))),
columns:[...heads[1].querySelectorAll('th')].map(t),
ytd:[...heads[1].querySelectorAll('th')].filter(th=>th.textContent.endsWith(' (YTD)'))
.map(th=>[th.querySelector('span.col-sub')?.textContent,th.querySelectorAll('*').length]),
bands:body.filter(band).map(t),labels:rows.map(tr=>t(tr.querySelector('th'))),
displays:rows.map(tr=>tds(tr).map(td=>td.textContent)),
beforeFirst:body.map((tr,i)=>band(tr)?[t(tr),t(body[i+1].querySelector('th'))]:null).filter(Boolean),
titles:rows.map(tr=>tds(tr).map(td=>td.getAttribute('title'))),
aria:rows.map(tr=>tds(tr).map(td=>td.getAttribute('aria-label'))),
notes:[...s.querySelectorAll('.cashflow-notes li')].map(li=>li.textContent),
notesPlace:[notes.previousElementSibling===s.querySelector('.table-scroll'),
notes.nextElementSibling===na],
na:[...s.querySelectorAll('.cashflow-na li')].map(t),
naDisclosure:[na.tagName,na.hasAttribute('open'),t(na.querySelector('summary'))],
dashes:[...s.querySelectorAll('tbody td')].filter(td=>td.textContent==='—').length,
totals:rows.filter(tr=>tr.classList.contains('total-row')).map(tr=>t(tr.querySelector('th'))),
limits:[...d.querySelectorAll('.forecast-limits li')].map(t),
limitsHeading:d.querySelector('.forecast-limits h2').textContent};
"""


FORECAST_READ = """
const tools=d.querySelector('.forecast-tools'),as=d.querySelector('.forecast-assumptions');
const frame=d.getElementById('model-preview'),built=d.querySelector('.forecast-built');
const rows=[...built.querySelectorAll('tbody tr')].map(tr=>{
  const cells=[...tr.querySelectorAll('td')],link=cells[1].querySelector('a');
  const run=cells[0].querySelector('span.code');
  const badge=cells[3].querySelector('.badge');
  return {role:tr.querySelector('th').textContent,run:run&&run.textContent,sha:cells[2].textContent,
  status:t(cells[3]),badge:badge&&[...badge.classList],link:link&&link.textContent,
  href:link&&link.getAttribute('href'),file:cells[1].textContent,
  title:cells[1].querySelector('[title]')?.getAttribute('title')};});
return {options:[...d.querySelectorAll('#model-select option')].map(o=>o.textContent),
selected:[...d.querySelectorAll('#model-select option')].filter(o=>o.selected)
.map(o=>o.textContent),
badges:[...tools.querySelectorAll('.badge')].map(b=>b.textContent),
muted:[...tools.querySelectorAll('.muted')].map(b=>b.textContent),
download:t(tools.querySelector('a[download]')),scope:d.querySelector('.forecast-scope').textContent,
input:d.querySelector('.forecast-input').textContent,revision:d.querySelector('.forecast-revision').textContent,
headings:[...d.querySelectorAll('.forecast > section > h2')].map(t),
registerHeading:as.querySelector('h3').textContent,intro:t(as.querySelector('.register-intro')),
register:[...as.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(c=>c.textContent)),
registerHref:as.querySelector('a.text-action').getAttribute('href'),
registerLink:t(as.querySelector('a.text-action')),
builtHeads:[...built.querySelectorAll('thead th')].map(t),rows,
attempts:t(built.querySelector('.forecast-attempts')),
attemptsAfterTable:built.querySelector('.table-scroll').nextElementSibling===built.querySelector('.forecast-attempts'),
sandbox:frame.getAttribute('sandbox'),src:frame.getAttribute('src'),dataSrc:frame.dataset.src};
"""


@pytest.mark.parametrize("run", [r for r, e in FORECAST["runs"].items() if e["models"]])
def test_forecast_for_run_shows_its_models_their_state_why_built_and_what_they_were_built_from(
    show: Opener, workspace: dict[str, Any], run: str
) -> None:
    expected = FORECAST["runs"][run]
    screen = forecast_tab(show, workspace, run)
    got = probe(screen, FORECAST_READ)
    assert got["options"] == expected["options"]
    assert got["selected"] == [expected["selected"]]
    assert got["badges"] == [expected["state"]]
    assert got["muted"] == [expected["qualification"]]
    assert got["download"] == "Download original HTML"
    assert got["scope"] == expected["scope"]
    assert got["input"] == expected["inputContract"]
    assert got["revision"] == expected["revisionNote"]
    assert got["headings"] == [
        "Cash flow model",
        "Assumptions and their rationale",
        "Model limitations",
        "Why this model was built",
        "Built from",
    ]
    assert got["registerHeading"] == expected["registerHeading"]
    assert got["intro"] == expected["registerIntro"]
    assert [r[0] for r in got["register"]] == expected["registerIds"]
    assert got["register"] == expected["registerRows"]
    assert got["builtHeads"] == ["Role", "Run", "Source", "SHA-256 prefix", "Status"]
    assert [r["role"] for r in got["rows"]] == [
        ROLE_WORDS[b["role"]] for b in expected["builtFrom"]
    ]
    for row, b in zip(got["rows"], expected["builtFrom"], strict=True):
        role = b["role"]
        assert row["run"] == b["path"].split("/")[1], role
        assert row["sha"] == b["sha256Prefix"], role
        assert row["status"] == (
            "Changed since publication" if b["changed"] else "Matches publication"
        )
        assert (
            row["badge"] and ("badge-attention" if b["changed"] else "badge-gray") in row["badge"]
        ), role
        if b["output"] is None:
            assert row["link"] is None, f"{role} must not link"
            assert row["file"] == b["path"].split("/")[-1], role
            assert row["title"] == b["path"], f"{role} keeps the full path in a title"
        else:
            assert row["link"] == b["output"].split("/")[-1], role
    # The sources come from different attempts, and the note says which files, as a fact.
    assert got["attempts"] == (
        "These files come from different attempts: CP-1-attempt-2.md (attempt 2), "
        "CP-2G-attempt-2.md (attempt 2), CP-2G-attempt-1-calculations.json (attempt 1)"
    )
    assert got["attemptsAfterTable"] is True
    assert got["sandbox"] == "allow-scripts allow-downloads"
    assert got["src"] is None, "the frame has no address until the disclosure is opened"
    assert re.fullmatch(
        r"/files/deliverables/tdg-model-3/model\.html\?sha256=[0-9a-f]{64}&embedded=1",
        got["dataSrc"],
    )
    assert f"sha256={expected['modelSha256']}" in got["dataSrc"]
    # Each link opens the output it names, in the run that holds it.
    links = [(got["registerHref"], expected["registerLinkOutput"])]
    links += [
        (r["href"], b["output"])
        for r, b in zip(got["rows"], expected["builtFrom"], strict=True)
        if b["output"]
    ]
    assert got["registerLink"] == "Open the full forward credit model output"
    for href, output in links:
        screen.go(href[1:])
        assert screen.eval("current.output") == output
        screen.go(f"W-Forecast/forecast?c={run}")


def test_forecast_for_tdg_002_lays_the_calculation_record_out_as_a_cash_flow_model(
    show: Opener, workspace: dict[str, Any]
) -> None:
    got = probe(forecast_tab(show, workspace, "tdg-002"), CASHFLOW_READ)
    assert got["model"] == CASH["model"]
    assert (got["h2"], got["caption"]) == ("Cash flow model", CASH["caption"])
    assert got["groups"] == CASH["groups"]
    assert got["spans"] == [2, 3, 3, 3]
    assert got["columns"] == CASH["columns"]
    # A year-to-date header puts "(YTD)" in its own span; the header text is unchanged.
    assert got["ytd"] == [["(YTD)", 1], ["(YTD)", 1]]
    assert got["bands"] == CASH["bands"]
    assert got["labels"] == [r["label"] for r in CASH["rows"]]
    for label, shown, row in zip(got["labels"], got["displays"], CASH["rows"], strict=True):
        assert shown == row["display"], label
    # Each band heading sits directly before its first row.
    for band, first in got["beforeFirst"]:
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
    assert got["notes"] == CASH["notes"]
    assert got["notesPlace"] == [True, True]
    assert got["na"] == CASH["notAvailable"]
    count = len(CASH["notAvailable"])
    assert got["naDisclosure"] == ["DETAILS", False, f"Why cells show n.a. ({count} lines)"]
    assert got["dashes"] == 0, "no cell shows a dash"
    assert got["totals"] == CASH["totals"]
    nm = "n.m.: not modelled in the calculation record"
    for i, row in enumerate(CASH["rows"]):
        for j, shown in enumerate(row["display"]):
            at = f"{row['label']} / {CASH['columns'][j]}"
            want = {"n.a.": f"n.a.: {got['titles'][i][j]}", "n.m.": nm}.get(shown)
            assert got["aria"][i][j] == want, at
    assert any(nm in line for line in got["aria"]), "some cell is n.m."
    assert got["limits"] == CASH["limits"]
    assert got["limitsHeading"] == "Model limitations"


@pytest.mark.parametrize("run", ["tdg-model-001", "tdg-003"])
def test_forecast_for_run_shows_the_same_models_cash_flow_caption_and_first_row(
    show: Opener, workspace: dict[str, Any], run: str
) -> None:
    got = probe(
        forecast_tab(show, workspace, run),
        "const f=d.querySelector('.forecast-cashflow tbody tr:not(.band-row)');"
        "return {model:d.querySelector('#model-select').value,"
        "caption:d.querySelector('.forecast-cashflow h2').nextElementSibling.textContent,"
        "label:t(f.querySelector('th')),cells:[...f.querySelectorAll('td')].map(td=>td.textContent)};",
    )
    first = CASH["rows"][0]
    assert got == {
        "model": CASH["model"],
        "caption": CASH["caption"],
        "label": first["label"],
        "cells": first["display"],
    }


def test_a_model_with_no_calculation_record_says_so_in_place_of_the_table_hostile_text_stays_text(
    show: Opener, workspace: dict[str, Any]
) -> None:
    quoted = 'x" onmouseover="alert(1)'
    forged = copy.deepcopy(workspace)
    first, second = model_of(forged, "tdg-model-3"), model_of(forged, "tdg-model-2")
    second["cashflow"] = None
    flow = first["cashflow"]
    flow["limits"] = flow["notes"] = [BAD]
    flow["rows"][0]["cells"][1] = {"exact": None, "display": "n.a.", "reason": BAD, "status": "na"}
    flow["rows"][0]["cells"][2] = {
        "exact": None,
        "display": "n.a.",
        "reason": quoted,
        "status": "na",
    }
    flow["units"] = None
    screen = forecast_tab(show, forged, "tdg-002")
    got = probe(
        screen,
        "const q=d.querySelectorAll('.cashflow td')[2];"
        "return {caption:d.querySelector('.forecast-cashflow h2').nextElementSibling.textContent,"
        "limit:d.querySelector('.forecast-limits li').textContent,"
        "notes:[...d.querySelectorAll('.cashflow-notes li')].map(li=>li.textContent),"
        "na:[...d.querySelectorAll('.cashflow-na li')].map(li=>li.textContent).slice(0,1),"
        "aria:d.querySelectorAll('.cashflow td')[1].getAttribute('aria-label'),"
        "quoted:q.getAttribute('aria-label'),onmouseover:q.hasAttribute('onmouseover'),"
        "names:[...q.attributes].map(x=>x.name).sort(),"
        "expected:['aria-label','class','title'].filter(n=>q.hasAttribute(n)).sort(),"
        "img:d.querySelector('.forecast-cashflow img,.forecast-limits img')!==null,"
        "onerror:d.querySelector('[onerror]')!==null};",
    )
    assert got["caption"] == (
        "Units not recorded · Q1 FY2024 (YTD) to FY2027E · history as retained in the handoffs; "
        "forecasts are conditional illustrations from the calculation record"
    )
    assert got["limit"] == BAD
    assert got["notes"] == [BAD]
    assert got["na"] == [f"Not available: Power & Control — {CASH['columns'][1]}: {BAD}"]
    assert got["aria"] == f"n.a.: {BAD}"
    # A quote in a reason must stay inside the one aria-label attribute.
    assert got["quoted"] == f"n.a.: {quoted}"
    assert got["onmouseover"] is False
    assert got["names"] == got["expected"]
    assert (got["img"], got["onerror"]) == (False, False)
    choose(screen, "tdg-model-2")
    after = probe(
        screen,
        "return {table:d.querySelector('.forecast-cashflow table')!==null,"
        "p:d.querySelector('.forecast-cashflow p').textContent,"
        "limits:d.querySelector('.forecast-limits')!==null};",
    )
    assert after == {
        "table": False,
        "p": "This model has no readable calculation record.",
        "limits": False,
    }


def test_choosing_another_model_in_the_forecast_tab_shows_that_model(
    show: Opener, workspace: dict[str, Any]
) -> None:
    screen = forecast_tab(show, workspace, "tdg-002")
    choose(screen, "tdg-model-1")
    got = probe(
        screen,
        "return [d.getElementById('model-select').selectedOptions[0].textContent,"
        "d.getElementById('model-preview').dataset.src];",
    )
    assert got[0] == FORECAST["runs"]["tdg-002"]["options"][2]
    assert re.search(r"tdg-model-1/model\.html", got[1]), got[1]


@pytest.mark.parametrize("run", [r for r, e in FORECAST["runs"].items() if not e["models"]])
def test_forecast_for_run_says_no_model_was_published_from_its_files_and_lists_other_models(
    show: Opener, workspace: dict[str, Any], run: str
) -> None:
    expected = FORECAST["runs"][run]
    got = probe(
        forecast_tab(show, workspace, run),
        "const o=d.querySelector('.forecast-other');"
        "return {heading:d.querySelector('#content .missing-state h2')?.textContent,"
        "select:d.getElementById('model-select')!==null,"
        "frame:d.getElementById('model-preview')!==null,"
        "otherHeading:o&&o.querySelector('h2').textContent,"
        "others:o&&[...o.querySelectorAll('li > a, li > span:first-child')]"
        ".map(e=>e.textContent)};",
    )
    assert got["heading"] == FORECAST["emptyHeading"]
    assert (got["select"], got["frame"]) == (False, False)
    assert got["otherHeading"] == expected["otherHeading"]
    if expected["otherHeading"] is not None:
        assert got["others"] == expected["others"]


def test_ratio_titles_show_four_decimals_with_the_approximation_sign_only_where_rounding_changed_it(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    rows = model_of(forged, "tdg-model-3")["cashflow"]["rows"]
    pick = {k: next(r for r in rows if r["kind"] == k) for k in ("percent", "multiple", "money")}
    cases = [
        ("percent", "0.5", "50.0000%"),
        ("percent", "0.123456789", "≈ 12.3457%"),
        ("percent", "-0.12345", "-12.3450%"),
        ("percent", "-0.0000000001", "≈ 0.0000%"),
        ("percent", "1E-4", "0.0100%"),
        ("multiple", "4.79755", "≈ 4.7976x"),
        ("multiple", "3", "3.0000x"),
        ("money", "1221.04741248", "1221.04741248"),
    ]
    for i, (kind, exact, _) in enumerate(cases):
        pick[kind]["cells"][i] = {
            "exact": exact,
            "display": "shown",
            "reason": None,
            "status": "value",
        }
    titles = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return Object.fromEntries([...d.querySelectorAll('.cashflow tbody tr:not(.band-row)')]"
        ".map(tr=>[t(tr.querySelector('th')),[...tr.querySelectorAll('td')].map(td=>td.getAttribute('title'))]));",
    )
    for i, (kind, exact, title) in enumerate(cases):
        assert titles[pick[kind]["label"]][i] == title, f"{pick[kind]['label']} {exact}"


def test_built_from_names_an_unknown_role_by_its_token_and_adds_no_note_when_files_share_an_attempt(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    sources = model_of(forged, "tdg-model-3")["sources"]
    sources[0]["role"] = "<b>mystery</b>"
    for source in sources:
        if source.get("path"):
            source["path"] = re.sub(r"-attempt-\d+", "-attempt-2", source["path"], count=1)
    got = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return [d.querySelector('.forecast-built tbody th').textContent,"
        "d.querySelector('.forecast-built tbody th b')!==null,"
        "d.querySelector('.forecast-attempts')!==null];",
    )
    assert got == ["<b>mystery</b>", False, False]


def test_a_report_whose_qualification_is_unrun_reads_not_run_and_no_acceptance_badge_is_amber(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    report = next((r for r in forged["reports"] if r["qualification"] == "unrun"), None)
    assert report, "the workspace holds an unrun report"
    screen = show("W-Reports/list?c=tdg-002", forged)
    shown = screen.eval(LIST_ROWS)[report["id"]]["text"]
    assert re.search(r"Analytical qualification: not run", shown)
    assert not re.search(r"unrun", shown)
    assert not screen.exists(".badge-attention")


def test_model_text_from_a_workspace_stays_text_and_a_source_that_changed_says_so(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    model = model_of(forged, "tdg-model-3")
    model.update(scope=BAD, revisionNote=BAD)
    model["register"]["rows"][0][1] = BAD
    model["sources"][0]["changed"] = True
    got = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return {scope:d.querySelector('.forecast-scope').textContent,"
        "revision:d.querySelector('.forecast-revision').textContent,"
        "cell:d.querySelector('.forecast-assumptions tbody tr').children[1].textContent,"
        "img:d.querySelector('#content img[src=\"x\"]')!==null,"
        "onerror:d.querySelector('#content [onerror]')!==null,"
        "status:[...d.querySelectorAll('.forecast-built tbody tr')].map(tr=>t(tr.children[4]))};",
    )
    assert got["scope"] == BAD
    assert got["revision"] == f"Revision note: {BAD}"
    assert got["cell"] == BAD
    assert (got["img"], got["onerror"]) == (False, False)
    assert got["status"][0] == "Changed since publication"
    assert got["status"][1:] == ["Matches publication"] * 4


def test_the_model_frame_is_not_loaded_or_watched_until_its_disclosure_is_opened(
    show: Opener,
) -> None:
    # The model file is never answered, so the frame cannot load and the watch must time out.
    held_model = ("/files/deliverables/tdg-model-3/model.html",)
    screen = show("W-Overview/overview?c=tdg-002", held_paths=held_model)
    screen.eval("window.DESIGN_FRAME_TIMEOUT_MS=20")
    screen.go("W-Forecast/forecast?c=tdg-002")
    page = screen.page
    parts = (
        "const x=d.querySelector('details.model-original'),f=d.getElementById('model-preview');"
        "const s=x.querySelector('.frame-status');"
    )
    got = probe(
        screen,
        parts + "return {open:x.open,summary:t(x.querySelector('summary')),"
        "inside:f.closest('details')===x,src:f.getAttribute('src')};",
    )
    assert got == {
        "open": False,
        "summary": "Published model (original HTML)",
        "inside": True,
        "src": None,
    }
    # Longer than the 20 ms watch the page would start; a started watch un-hides the status.
    page.wait_for_timeout(80)
    assert probe(screen, parts + "return [s.hidden,t(s)];") == [True, ""], "no watch has started"
    probe(screen, parts + "x.open=true;")
    until(page, "!!document.getElementById('model-preview').getAttribute('src')")
    until(page, "/did not load/.test(document.querySelector('.frame-status').textContent)")
    got = probe(
        screen,
        parts + "return {same:f.getAttribute('src')===f.dataset.src,text:t(s),"
        "href:s.querySelector('a').getAttribute('href')};",
    )
    assert got["same"] is True
    assert re.fullmatch(r"The model did not load\. Download original HTML Retry", got["text"])
    assert re.search(r"model\.html\?sha256=[0-9a-f]{64}&download=1$", got["href"])
    assert probe(screen, parts + "f.dispatchEvent(new Event('load'));return s.hidden;") is True
    # Closing and opening again does not start a second watch or reset the address.
    src = screen.attr("#model-preview", "src")
    probe(screen, parts + "x.open=false;")
    page.wait_for_timeout(30)
    probe(screen, parts + "x.open=true;")
    page.wait_for_timeout(30)
    assert screen.attr("#model-preview", "src") == src
    assert probe(screen, parts + "return s.hidden;") is True, "no second watch started"


def test_a_model_id_with_markup_in_it_renders_no_element_of_its_own_on_four_screens_and_the_tab(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = renamed(workspace, "tdg-model-3", HOSTILE)
    for hash_route in [
        "W-Overview/overview?c=tdg-002",
        "W-Forecast/forecast?c=tdg-002",
        "W-Library/cases",
        "W-Settings/workspace",
    ]:
        assert not show(hash_route, forged).exists("[id^=pwn]"), hash_route
    screen = forecast_tab(show, forged, "tdg-002")
    assert not screen.exists("[id^=pwn]"), "Forecast tab"
    # The id is one encoded section.
    section = quote(HOSTILE, safe="-_.!~*'()")
    hrefs = [h or "" for h in screen.attrs("a", "href")]
    assert any(h.startswith(f"#W-Forecast/{section}") for h in hrefs), (
        "the id is one encoded section"
    )


def test_catalogue_text_with_markup_in_it_renders_no_element_of_its_own_in_rows_or_selected_run(
    show: Opener,
) -> None:
    forged = copy.deepcopy(PINNED)
    run = next(r for r in forged["real"] if r["id"] == "tdg-002")
    for field in ["name", "title", "issuer", "sector", "workflow", "summary", "period"]:
        run[field] = HOSTILE
    run["gaps"] = [HOSTILE]
    run["ratings"] = [{"label": HOSTILE, "date": HOSTILE, "source": ""}]
    run["artifacts"][0].update(label=HOSTILE, issue=HOSTILE)
    run["metrics"]["leverage"].update(basis=HOSTILE, source='s"><b id=pwn2>')
    forged["sources"] = {
        's"><b id=pwn2>': {"path": HOSTILE, "line": 1, "quote": HOSTILE, "href": HOSTILE}
    }
    screen = show("W-Library/cases", catalogue=forged)
    screen.click('[data-library-select="tdg-002"]')
    assert not screen.exists("[id^=pwn]")
    assert HOSTILE in squash(screen.text("#run-detail")), "shown as text"


def test_a_report_id_with_markup_in_it_renders_no_element_of_its_own(
    show: Opener, workspace: dict[str, Any]
) -> None:
    forged = copy.deepcopy(workspace)
    forged["reports"][0]["id"] = HOSTILE
    for hash_route in [
        "W-Library/cases",
        "W-Reports/list?c=tdg-002",
        "W-Overview/overview?c=tdg-002",
    ]:
        assert not show(hash_route, forged).exists("[id^=pwn]"), hash_route


@pytest.mark.parametrize("model_id", ["m é 1", "a%20b", "Société modèle", "a/b?c=1#x"])
def test_a_model_id_chosen_in_the_model_select_shows_that_model(
    show: Opener, workspace: dict[str, Any], model_id: str
) -> None:
    forged = renamed(workspace, "tdg-model-1", model_id)
    want = model_of(forged, model_id)
    screen = forecast_tab(show, forged, "tdg-002")
    choose(screen, model_id)
    got = probe(
        screen,
        "return {value:d.getElementById('model-select').value,"
        "src:d.getElementById('model-preview').dataset.src,"
        "scope:d.querySelector('.forecast-scope')?.textContent??null,section:parseRoute().section};",
    )
    assert got["value"] == model_id
    assert want["href"].split("?")[0] in got["src"]
    assert got["scope"] == want["scope"]
    assert got["section"] == model_id


def test_a_malformed_escape_in_the_section_is_an_unknown_section_never_an_error(
    show: Opener,
) -> None:
    screen = show("W-Overview/overview?c=tdg-002")
    route = probe(
        screen,
        "location.hash='#W-Forecast/%E0%A4%A?c=tdg-002';const r=parseRoute();"
        "return [r.module,r.section];",
    )
    assert route[0] == "W-Forecast"
    assert route[1] != "%E0%A4%A"
    until(screen.page, "current.module==='W-Forecast'")


def test_the_forecast_tab_opens_the_default_model_not_superseded_preferring_one_with_a_predecessor(
    show: Opener, workspace: dict[str, Any]
) -> None:
    # tdg-model-2 records tdg-model-1; the latest folder, tdg-model-3, records none.
    forged = copy.deepcopy(workspace)
    model_of(forged, "tdg-model-3")["previous"] = None
    model_of(forged, "tdg-model-2")["previous"] = "tdg-model-1"
    model_of(forged, "tdg-model-1")["previous"] = None
    got = probe(
        forecast_tab(show, forged, "tdg-002"),
        "return [d.getElementById('model-select').value,"
        "[...d.querySelectorAll('#model-select option')].map(o=>o.value)];",
    )
    assert got[0] == "tdg-model-2"
    assert got[1] == ["tdg-model-2", "tdg-model-3", "tdg-model-1"]


HYDRATE_DATA = (
    "const x=[{heading:'A',level:1,line:1,blocks:[]}],y=[{heading:'B',level:1,line:1,blocks:[]}];"
    "const data={runs:{},inputs:{},pins:{},handoffs:{aa:x,bb:y},outputs:{"
    "'r1/CP-1.md':{id:'r1/CP-1.md',sha256:'aa'},'r2/CP-1.md':{id:'r2/CP-1.md',sha256:'aa'},"
    "'r2/CP-2.md':{id:'r2/CP-2.md',sha256:'bb'}}};"
)


def test_hydrate_gives_every_output_the_sections_of_its_own_hash(show: Opener) -> None:
    got = probe(
        show("W-Library/cases"),
        HYDRATE_DATA + "const o=data.outputs;return [hydrate(data)===data,"
        "o['r1/CP-1.md'].sections[0].heading,o['r2/CP-1.md'].sections[0].heading,"
        "o['r2/CP-2.md'].sections[0].heading];",
    )
    assert got == [True, "A", "A", "B"]


def test_hydrate_refuses_an_output_whose_handoff_was_not_sent(show: Opener) -> None:
    refused = probe(
        show("W-Library/cases"),
        "try{hydrate({outputs:{'r1/CP-1.md':{id:'r1/CP-1.md',sha256:'zz'}},handoffs:{}});}"
        "catch(error){return error.message;}return null;",
    )
    assert refused is not None, "hydrate did not throw"
    assert re.search(r"r1/CP-1\.md", refused), refused


def test_the_cash_flow_table_is_a_labelled_scroll_region_with_ruled_groups_and_quiet_scenarios(
    show: Opener, workspace: dict[str, Any]
) -> None:
    got = probe(
        forecast_tab(show, workspace, "tdg-002"),
        "const r=d.querySelector('.forecast-cashflow .table-scroll');"
        "const h=d.querySelector('.forecast-cashflow h2');"
        "const f=d.querySelector('.cashflow tbody tr:not(.band-row)');"
        "const c=[...f.querySelectorAll('td')];"
        "const g=c.find(x=>x.classList.contains('group-start'));"
        "const sc=c.find(x=>x.classList.contains('scenario'));"
        "const q=c.find(x=>!x.classList.contains('scenario')),cs=x=>getComputedStyle(x);"
        "return {role:r.getAttribute('role'),tab:r.getAttribute('tabindex'),"
        "labelled:r.getAttribute('aria-labelledby'),id:h.id,cells:c.length,"
        "starts:c.map(x=>x.classList.contains('group-start')),"
        "scenario:c.map(x=>x.classList.contains('scenario')),height:cs(c[0]).height,"
        "minWidth:cs(f.querySelector('th')).minWidth,"
        "root:parseFloat(cs(document.documentElement).fontSize),border:cs(g).borderLeft,"
        "padding:cs(g).paddingTop,quiet:cs(sc).backgroundColor,plain:cs(q).backgroundColor};",
    )
    assert got["role"] == "region"
    assert got["tab"] == "0"
    assert got["id"], "the heading has an id"
    assert got["labelled"] == got["id"]
    assert got["cells"] == len(CASH["columns"])
    assert got["starts"].count(True) == len(CASH["groups"]), "one ruled first column per group"
    assert got["starts"][0] is True
    assert True in got["scenario"] and False in got["scenario"], "scenario and plain columns"
    assert got["height"] == "32px"
    # The key reads 12rem; a real browser reports the resolved length.
    assert float(got["minWidth"].removesuffix("px")) == 12 * got["root"]
    assert re.match(r"^1px solid (rgb\(221, 225, 234\)|#dde1ea)$", got["border"]), got["border"]
    assert got["padding"] == "5px"
    assert got["quiet"] == "rgb(246, 247, 250)"
    assert got["plain"] == "rgba(0, 0, 0, 0)"


def test_the_section_pager_names_models_on_forecast_and_reports_on_reports_sections_elsewhere(
    show: Opener, workspace: dict[str, Any]
) -> None:
    screen = forecast_tab(show, workspace, "tdg-002")
    labels = (
        "['previous-section','next-section']"
        ".map(id=>document.getElementById(id).getAttribute('aria-label'))"
    )
    assert screen.eval(labels) == ["Previous model", "Next model"]
    screen.go("W-Reports/list?c=tdg-002")
    assert screen.eval(labels) == ["Previous report", "Next report"]
    # An analytical module with several sections keeps the default labels.
    screen.go("CP-1/summary?c=tdg-002")
    assert screen.eval(labels) == ["Previous section", "Next section"]


def test_help_explains_run_notices_resuming_a_stopped_run_and_na_and_nm_in_the_cash_flow_model(
    show: Opener,
) -> None:
    names = ["Run notices", "Resuming a stopped run", "n.a. and n.m. in the cash flow model"]
    got = probe(
        show("W-Help/help"),
        "const hs=[...d.querySelectorAll('.help-copy h2')];"
        "const body=n=>{const h=hs.find(x=>t(x)===n);"
        "return h&&t(h.nextElementSibling);};return {heads:hs.map(t),bodies:a.map(body)};",
        names,
    )
    for name in names:
        assert name in got["heads"], name
    notices, resuming, na = got["bodies"]
    for state in ["running", "complete", "stopped", "failed", "interrupted"]:
        assert re.search(state, notices), state
    assert re.search(r"Dismiss", notices)
    assert re.search(
        r"Resume appears on stopped, failed or interrupted notices, "
        r"except a run stopped by a provider ruling\.",
        notices,
    )
    assert resuming == (
        "A run started from New run that stopped, failed or was interrupted can be resumed from "
        "its "
        "notice, from Run activity or from Recent runs. The resumed run is a new run: it keeps the "
        "accepted modules without a new model call and has its own spending cap, and what the "
        "stopped "
        "run spent is not counted against it. A run stopped by a provider ruling cannot be resumed."
    )
    for pattern in [
        r"n\.a\. means not available",
        r"Why cells show n\.a\.",
        r"never zero",
        r"n\.m\. means not modelled",
    ]:
        assert re.search(pattern, na), pattern


def test_an_other_models_row_opens_the_model_under_the_run_it_was_published_for(
    show: Opener, workspace: dict[str, Any]
) -> None:
    screen = forecast_tab(show, workspace, "tdg-run-comparison")
    owner = screen.eval(
        "(()=>{const issuer=contexts['tdg-run-comparison'].issuerKey;"
        "const same=Object.keys(contexts)"
        ".filter(k=>contexts[k].issuerKey===issuer&&k!=='tdg-run-comparison');"
        "const supplier=same[0],owner=same.at(-1);"
        "if(supplier===owner)throw new Error('one run only');"
        "const base=JSON.parse(JSON.stringify(window.DESIGN_WORKSPACE.models[0]));"
        "base.id='zz-owned-model';base.issuerKey=issuer;base.runId=contexts[owner].folder;"
        "base.sources=[{...base.sources[0],run:supplier}];"
        "window.DESIGN_WORKSPACE.models.splice(0,window.DESIGN_WORKSPACE.models.length,base);"
        "return owner;})()"
    )
    screen.go("W-Library/cases")
    screen.go("W-Forecast/forecast?c=tdg-run-comparison")
    href = screen.attr(".forecast-other li a", "href")
    assert href, "the row links"
    assert parse_qs(href.split("?")[1])["c"] == [owner]
