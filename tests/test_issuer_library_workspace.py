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

import pytest
from issuer_library_browser import APP, ROOT, WEB, Screen, json_reply, open_app, release
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
SNAPSHOT = "tdg-fy2024-snapshot-7"
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
    ) -> Screen:
        api = {
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
