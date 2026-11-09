"""Library screening: screening.test.cjs and screening-dom.test.cjs at final-workflow dd3dfa18.

The Node suites evaluated screening.js in a bare vm context and simulated the Library screen in
jsdom. Here the real page loads screening.js and its LibraryLogic global is called with the same
synthetic rows; the real Library screen is opened over the pinned 2026-11-08 catalogue (served as
/api/catalogue) and compared with the hand-written key. Synthetic data only.
Marked browser: real browser proof.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from issuer_library_browser import WEB, Screen, js, json_reply, open_app

pytestmark = pytest.mark.browser


def row(run_id: str, **fields: Any) -> dict[str, Any]:
    return {"id": run_id, **fields}


ROWS = [
    row("missing", name="Zeta", issuer="Z", sector="Energy", workflow="Legal", date="2024-01-01",
        period_kind="Actual", completion=None, artifacts=[],
        metrics={"leverage": None, "coverage": None}),
    row("zero", name="Alpha", issuer="A", sector="Energy", workflow="Credit", date="2024-02-01",
        period_kind="Actual", completion=0, artifacts=[],
        metrics={"leverage": {"value": "0", "basis": "Gross"}, "coverage": {"value": "0"}}),
    row("gross", name="Beta", issuer="B", sector="Auto", workflow="Credit", date="2023-01-01",
        period_kind="Actual", completion=75, artifacts=[{"available": True, "state": "candidate"}],
        metrics={"leverage": {"value": "5.96", "basis": "Gross"}, "coverage": {"value": "3.60"}}),
    row("net", name="Gamma", issuer="G", sector="Auto", workflow="Credit", date="2022-01-01",
        period_kind="Forecast", completion=100, artifacts=[],
        metrics={"leverage": {"value": "2.2", "basis": "Net"}, "coverage": {"value": "4.5"}}),
]  # fmt: skip


@pytest.fixture
def screen(browser: Any) -> Iterator[Screen]:
    opened = open_app(browser, "W-Library/cases")
    yield opened
    assert opened.errors == []
    opened.close()


def logic(screen: Screen, call: str, *args: Any) -> Any:
    """LibraryLogic.<call>(ROWS, *args) in the page; the rows are passed in as plain data."""
    return screen.page.evaluate(
        "([call,rows,args])=>LibraryLogic[call](rows,...args)", [call, ROWS, list(args)]
    )


def ids(rows: list[dict[str, Any]]) -> list[str]:
    return [r["id"] for r in rows]


def test_missing_values_never_become_zero(screen: Screen) -> None:
    number_of = "v=>LibraryLogic.numberOf(v)"
    assert screen.page.evaluate(number_of, None) is None
    assert screen.page.evaluate(number_of, {"value": ""}) is None
    assert screen.page.evaluate(number_of, {"value": "NaN"}) is None
    assert screen.page.evaluate(number_of, {"value": "0"}) == 0
    assert ids(logic(screen, "filterRuns", {"leverageMax": "0"})) == ["zero"]


def test_combined_filters_retain_basis_and_period_identity(screen: Screen) -> None:
    combined = {
        "sector": "Auto",
        "basis": "Gross",
        "leverageMin": "4",
        "coverageMin": "3",
        "period": "Actual",
    }
    assert ids(logic(screen, "filterRuns", combined)) == ["gross"]
    net = {"sector": "Auto", "basis": "Net", "leverageMin": "4"}
    assert len(logic(screen, "filterRuns", net)) == 0


def test_unknown_completeness_zero_score_and_invalid_threshold_stay_distinct(
    screen: Screen,
) -> None:
    assert ids(logic(screen, "filterRuns", {"completion": "unassessed"})) == ["missing"]
    assert ids(logic(screen, "filterRuns", {"completion": "75"})) == ["gross", "net"]
    assert len(logic(screen, "filterRuns", {"leverageMin": "bad"})) == 0


def test_numeric_sort_keeps_missing_last_in_both_directions_without_mutating_input(
    screen: Screen,
) -> None:
    ascending = ids(logic(screen, "sortRuns", "leverage", "asc"))
    assert ascending == ["zero", "net", "gross", "missing"]
    descending = ids(logic(screen, "sortRuns", "leverage", "desc"))
    assert descending == ["gross", "net", "zero", "missing"]
    order = screen.page.evaluate(
        "rows=>{const before=rows.map(r=>r.id);LibraryLogic.sortRuns(rows,'leverage','asc');"
        "return [before,rows.map(r=>r.id)];}",
        ROWS,
    )
    assert order[0] == order[1] and order[1][0] == "missing"


def test_search_and_report_availability_are_conjunctive(screen: Screen) -> None:
    assert len(logic(screen, "filterRuns", {"search": "beta", "availability": "report"})) == 1
    assert len(logic(screen, "filterRuns", {"search": "alpha", "availability": "report"})) == 0


PINNED = json.loads((WEB / "testdata/catalogue-2026-11-08.json").read_text(encoding="utf-8"))
KEY = json.loads((WEB / "testdata/library-screening-expected.json").read_text(encoding="utf-8"))
ALL = [*KEY["run_folder_rows"]["ids"], *KEY["delivery_rows"]["ids"]]
METRIC_IDS = [r["id"] for r in KEY["with_metrics"]["rows"]]
SORT = "document.querySelector('[data-library-sort=\"{}\"]')"


def squash(text: str) -> str:
    return " ".join(text.split())


class Library:
    """The Library screen of the real app, driven through the page's own controls."""

    def __init__(self, screen: Screen) -> None:
        self.screen = screen

    def ids(self) -> list[str]:
        return [
            i or ""
            for i in self.screen.attrs(
                "#library-results button[data-library-select]", "data-library-select"
            )
        ]

    def set(self, element_id: str, value: str) -> None:
        self.screen.page.evaluate(
            "([id,v])=>{const el=document.getElementById(id);el.value=v;"
            "el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));}",
            [element_id, value],
        )

    def text(self, element_id: str) -> str:
        return squash(self.screen.text(f"#{element_id}"))

    def count(self) -> str:
        return self.text("library-count")

    def detail(self) -> str:
        return self.text("run-detail")

    def sort_click(self, name: str) -> None:
        self.screen.click(f'[data-library-sort="{name}"]')

    def aria_sort(self, name: str) -> str | None:
        return self.screen.attr(f'th:has([data-library-sort="{name}"])', "aria-sort")

    def select(self, run_id: str) -> None:
        self.screen.click(f'[data-library-select="{run_id}"]')

    def focused(self, name: str) -> tuple[str | None, str | None]:
        value: list[str | None] = self.screen.eval(
            f"(()=>{{const a=document.activeElement;"
            f"return [a.dataset.{name},a.getAttribute('aria-pressed')];}})()"
        )
        return value[0], value[1]


LibraryOpener = Callable[..., Library]


@pytest.fixture
def library(browser: Any) -> Iterator[LibraryOpener]:
    opened: list[Screen] = []

    def open_library(catalogue: dict[str, Any] = PINNED, problem: str = "") -> Library:
        reply = {"workspace": "", "policy_locked": False, "issues": []}
        reply.update(real=catalogue["real"], sources=catalogue["sources"])
        app = {"workspace": "", "policy_locked": False, "issues": [], "problem": problem}
        screen = open_app(
            browser,
            "W-Library/cases",
            workspace={"reports": [], "models": [], "visuals": []},
            app=app,
            api={"/api/catalogue": json_reply(reply)},
        )
        opened.append(screen)
        return Library(screen)

    try:
        yield open_library
    finally:
        try:
            for screen in opened:
                assert screen.errors == []
        finally:
            for screen in opened:
                screen.close()


def test_the_screen_lists_the_59_served_rows_in_served_order_under_7_issuers(
    library: LibraryOpener,
) -> None:
    p = library()
    assert p.count() == "59 of 59 runs · 7 issuers"
    assert p.ids() == KEY["default_sort"]["served_order"]
    assert sorted(p.ids()) == sorted(ALL)
    nav = js(
        p.screen,
        "return Object.fromEntries([...d.querySelectorAll('[data-library-issuer]')]"
        ".map(b=>[b.dataset.libraryIssuer,norm(b.querySelector('.count').textContent)]));",
    )
    assert nav == {k: str(v) for k, v in KEY["issuer_count"]["rows_per_issuer"].items()}
    assert p.screen.count("a.run-link") == 0, "no row links to an Overview"


def test_missing_is_never_shown_as_zero_a_row_without_metrics_shows_a_dash_and_not_assessed(
    library: LibraryOpener,
) -> None:
    p = library()
    cells = [squash(c) for c in p.screen.texts('tr:has([data-library-select="tdg-001"]) td')]
    assert cells[3].startswith("—") and cells[4].startswith("—"), " | ".join(cells)
    assert cells[5].startswith("Not assessed")
    assert not re.search(r"\b0(\.0+)?×", " ".join(cells))


def check_leverage_filters(p: Library) -> None:
    cases = KEY["filter_cases"]
    p.set("library-leverageMin", cases["a_leverage_min"]["filters"]["leverageMin"])
    assert sorted(p.ids()) == sorted(cases["a_leverage_min"]["expected_ids"])
    p.set("library-leverageMin", "1.61")
    assert p.ids() == ["tdg-002"], "a minimum is inclusive and the smaller leverage falls out"
    p.set("library-leverageMin", "")
    p.set("library-leverageMax", "1.59")
    assert p.ids() == [], "a maximum below every leverage"
    p.set("library-leverageMax", "100")
    assert sorted(p.ids()) == ["ford-otosan-2024-001", "tdg-002"], (
        "a set bound never matches a missing leverage"
    )
    p.set("library-leverageMax", "")
    assert len(p.ids()) == 59, "a blank bound ignores the filter"
    p.set("library-coverageMin", "3.6")
    assert sorted(p.ids()) == ["ford-otosan-2024-001", "tdg-002"]
    p.set("library-coverageMin", "3.61")
    assert p.ids() == ["ford-otosan-2024-001"]
    p.set("library-coverageMin", "")
    p.set("library-coverageMax", "3.6")
    assert p.ids() == ["tdg-002"]
    p.set("library-coverageMax", "")


def test_each_filter_selects_the_key_rows_a_blank_bound_is_ignored_a_set_one_misses_a_missing_value(
    library: LibraryOpener,
) -> None:
    p = library()
    cases = KEY["filter_cases"]
    check_leverage_filters(p)
    p.set("library-basis", cases["b_leverage_basis"]["filters"]["basis"])
    assert p.ids() == cases["b_leverage_basis"]["expected_ids"]
    p.set("library-basis", "")
    p.set("library-query", cases["c_search_issuer_name"]["filters"]["search"])
    assert p.ids() == cases["c_search_issuer_name"]["expected_ids"]
    p.set("library-query", "")
    p.set("library-period", "Quarterly actual")
    assert [i for i in p.ids() if i in METRIC_IDS] == ["tdg-003"]
    p.set("library-period", "")
    p.set("library-completion", "unassessed")
    assert len(p.ids()) == 59, "no served run has a completeness"
    p.set("library-completion", "50")
    assert p.ids() == [], "a completeness bound never matches a missing one"
    p.set("library-completion", "")
    p.set("library-availability", "handoff")
    none = len(p.ids())
    p.set("library-availability", "report")
    assert none + len(p.ids()) == 59, "every row has a report or has none"


def test_combined_filters_narrow_together_and_count_the_metric_filters_in_use(
    library: LibraryOpener,
) -> None:
    p = library()
    p.set("library-sector", "Aerospace & defense")
    p.set("library-leverageMin", "5")
    assert p.ids() == ["tdg-002"]
    assert p.screen.text("#metric-filter-count") == "· 1 active"
    p.set("library-leverageMin", "")
    for run_id in ["tdg-002", "tdg-003", "tdg-guidance-001"]:
        assert run_id in p.ids(), run_id
    assert p.screen.text("#metric-filter-count") == ""


def test_sorting_missing_last_descending_after_ascending_the_key_order_the_header_says_which_way(
    library: LibraryOpener,
) -> None:
    p = library()
    assert p.aria_sort("leverage") == "none"
    p.sort_click("leverage")
    assert p.aria_sort("leverage") == "ascending"
    assert p.ids()[:2] == ["ford-otosan-2024-001", "tdg-002"]
    p.sort_click("leverage")
    assert p.aria_sort("leverage") == "descending"
    assert p.ids()[:4] == KEY["sort_leverage_desc_missing_last"]["first_4_ids"]
    assert len(p.ids()) == 59
    p.sort_click("coverage")
    assert p.ids()[:2] == ["tdg-002", "ford-otosan-2024-001"], "3.60 before 8.2"
    assert p.screen.eval(f"document.activeElement==={SORT.format('coverage')}"), (
        "the sort button keeps focus"
    )


def test_sort_buttons_and_issuer_choices_are_native_buttons_tabbable_named_and_keep_focus(
    library: LibraryOpener,
) -> None:
    p = library()
    controls = p.screen.eval(
        "[...document.querySelectorAll('[data-library-sort],[data-library-issuer],"
        "[data-library-nav],[data-library-select]')].map(b=>({tag:b.tagName,type:b.type,"
        "tabindex:b.getAttribute('tabindex'),named:!!(b.textContent.trim()||b.getAttribute('aria-label'))}))"
    )
    assert controls
    for control in controls:
        assert control["tag"] == "BUTTON" and control["type"] == "button"
        assert control["tabindex"] != "-1" and control["named"], control
    tdg = '[data-library-issuer="TDG"]'
    assert p.screen.attr(tdg, "aria-pressed") == "false"
    p.screen.click(tdg)
    assert p.focused("libraryIssuer") == ("TDG", "true")
    assert p.count() == "13 of 59 runs · 1 issuer"
    p.screen.click(tdg)
    assert len(p.ids()) == 59, "a second choice releases the issuer"
    p.screen.click('[data-library-nav="reports"]')
    assert p.focused("libraryNav") == ("reports", "true")
    p.screen.click('[data-library-nav="all"]')
    assert len(p.ids()) == 59


def test_selecting_a_row_opens_its_detail_with_the_key_values_and_bases_one_run_at_a_time(
    library: LibraryOpener,
) -> None:
    p = library()
    assert not p.screen.hidden("run-detail"), "the first row is selected on load"
    for row in KEY["with_metrics"]["rows"]:
        p.select(row["id"])
        detail = p.detail()
        assert row["id"] in detail, row["id"]
        for name, m in row["metrics_present"].items():
            assert m["basis"] in detail, f"{row['id']} {name} basis"
            shown = (
                f"{m['value']}×"
                if m["unit"] == "x"
                else p.screen.page.evaluate("v=>Number(v).toLocaleString('en-GB')", m["value"])
            )
            assert shown in detail, f"{row['id']} {name}: {shown}"
        assert "Not assessed" in detail
    p.select("tdg-003")
    assert "Not established for this case." in p.detail(), "tdg-003 has no leverage"
    assert p.screen.count("#library-results tr.selected") == 1


def test_view_source_moves_to_the_source_block_reset_returns_filters_sort_and_selection(
    library: LibraryOpener,
) -> None:
    p = library()
    p.select("tdg-002")
    p.screen.click('[data-library-source="tdg-002.tdg-base"]')
    assert p.screen.eval("document.getElementById('metric-sources').open") is True
    assert p.screen.active() == "source-tdg-002.tdg-base"
    p.set("library-leverageMin", "5")
    p.sort_click("leverage")
    p.screen.click('[data-library-issuer="TDG"]')
    assert p.ids() == ["tdg-002"]
    p.screen.click("#library-clear")
    assert p.ids() == KEY["default_sort"]["served_order"]
    values = p.screen.eval(
        "[...document.querySelectorAll('#library-filters [data-library-filter]')]"
        ".map(e=>[e.id,e.value])"
    )
    assert values
    assert [v for v in values if v[1] != ""] == []
    assert p.aria_sort("leverage") == "none"
    assert p.screen.active() == "library-query"


def test_no_match_shows_a_reset_that_works_an_empty_workspace_and_an_unreadable_one_each_say_so(
    library: LibraryOpener,
) -> None:
    p = library()
    p.set("library-query", "no such issuer anywhere")
    assert p.count() == "0 of 59 runs · 0 issuers"
    assert "No runs match these filters" in p.text("library-results")
    assert p.screen.hidden("run-detail")
    p.screen.click("#library-empty-reset")
    assert len(p.ids()) == 59
    none = library({"real": [], "sources": {}})
    assert "No runs in this workspace yet" in none.text("library-results")
    bad = library({"real": [], "sources": {}}, "503")
    assert "The library could not read this workspace" in bad.text("library-results")
    assert bad.screen.attr("#library-results a", "href") == "#W-Settings/workspace"


def test_every_control_is_labelled_ids_are_unique_and_the_count_is_announced(
    library: LibraryOpener,
) -> None:
    s = library().screen
    ids = s.attrs("[id]", "id")
    assert len(ids) == len(set(ids))
    unlabelled = js(
        s,
        "return [...d.querySelectorAll('#library-filters input,#library-filters select')]"
        ".filter(c=>!(c.labels.length&&c.labels[0].textContent.trim())).map(c=>c.id);",
    )
    assert unlabelled == []
    assert s.attr("#library-count", "role") == "status"
    assert s.attr("#library-count", "aria-live") == "polite"
    assert s.exists("#library-results table caption")
    assert set(s.attrs("#library-results thead th", "scope")) == {"col"}


BAD, QUOTE = "<img src=x onerror=alert(1)>", 'x" onmouseover="alert(1)'


def hostile_catalogue() -> tuple[dict[str, Any], dict[str, Any]]:
    bad, quote, evil = BAD, QUOTE, "javascript:alert(1)"
    base = copy.deepcopy(next(r for r in PINNED["real"] if r["id"] == "tdg-002"))

    def metric(name: str) -> dict[str, str]:
        return {
            "value": "12.5",
            "unit": bad,
            "period": bad,
            "basis": quote + name,
            "source": f's{name}"><i>',
        }

    def artifact(
        folder: str, available: bool, href: str, issue: str, kind: str = "report"
    ) -> dict[str, Any]:
        return {"folder": folder, "kind": kind, "label": bad, "state": "candidate",
                "relationship": "direct" if kind == "report" else "related",
                "available": available, "href": href, "issue": issue}  # fmt: skip

    run = {**base, "id": f"{quote}-1", "issuer": bad, "name": bad, "title": quote, "sector": bad,
           "workflow": quote, "date": bad, "period": bad, "period_kind": bad, "summary": bad,
           "gaps": [bad], "ratings": [{"label": bad, "date": bad, "source": 'r"><i>'}],
           "identity_source": bad, "sector_source": quote, "handoff_href": evil, "completion": None,
           "metrics": {"revenue": metric("r"), "ebitda": metric("e"),
                       "leverage": {**metric("l"), "unit": "x"}, "coverage": metric("c"),
                       "cash": metric("h"), "cashflow": metric("f")},
           "artifacts": [artifact("f", True, evil, ""), artifact("g", False, "/files/x", bad),
                         artifact("h", True, "//evil.example/x", "", "model")]}  # fmt: skip
    ids = [bad, quote, 'r"><i>', *(f's{n}"><i>' for n in "relchf")]
    sources = {
        i: {"path": bad, "sha256": "0", "line": quote, "href": evil,
            "quote": f"{bad}</blockquote><script>alert(1)</script>"}
        for i in ids
    }  # fmt: skip
    plain = {**base, "id": "plain-1", "issuer": quote, "artifacts": [], "handoff_href": evil}
    return {"real": [run, plain], "sources": sources}, run


SCREEN_SAFE = """()=>{
  const screen=document.querySelector('.library-screen');
  const handlers=[];
  for(const el of [screen,...screen.querySelectorAll('*')])for(const a of el.attributes)
    if(/^on/i.test(a.name))handlers.push(el.tagName+' '+a.name);
  const links=[...screen.querySelectorAll('a')].filter(a=>
    /^\\s*(javascript|data):/i.test(a.getAttribute('href'))
    ||a.getAttribute('href').startsWith('//')).length;
  return {handlers,injected:screen.querySelectorAll('script,i,b,img[src="x"]').length,links};
}"""


def check_safe(p: Library) -> None:
    safe = p.screen.page.evaluate(SCREEN_SAFE)
    assert safe == {"handlers": [], "injected": 0, "links": 0}, safe


def test_hostile_record_text_is_rendered_as_text_no_markup_handler_or_script_link_comes_of_it(
    library: LibraryOpener,
) -> None:
    catalogue, run = hostile_catalogue()
    p = library(catalogue)
    assert p.ids() == [run["id"], "plain-1"]
    check_safe(p)
    assert BAD in p.text("library-results"), "the markup shows as text"
    p.screen.click("[data-library-select]")
    check_safe(p)
    for shown in [BAD, QUOTE, "Unavailable"]:
        assert shown in p.detail(), shown
    assert p.screen.count(".artifact-list li") == 3
    gone = js(
        p.screen,
        "return [...d.querySelectorAll('.artifact-list li')]"
        ".filter(li=>li.textContent.includes('Unavailable')).map(li=>li.querySelector('a')===null);",
    )
    assert gone == [True], "the unavailable artifact is text, not a link"
    p.select("plain-1")
    check_safe(p)
    assert "No final deliverable has been indexed" in p.detail()
    p.set("library-period", BAD)
    assert p.ids() == [run["id"]], "the period kind selects as text"
    check_safe(p)


def test_a_number_box_holding_unreadable_text_does_not_leave_an_invisible_filter_after_the_rebuild(
    library: LibraryOpener,
) -> None:
    p = library()
    p.screen.eval(
        "(()=>{const box=document.getElementById('library-leverageMin');"
        "Object.defineProperty(box,'validity',{value:{badInput:true}});"
        "box.dispatchEvent(new Event('input',{bubbles:true}));})()"
    )
    assert p.ids() == [], "unreadable text excludes every run while it is shown"
    p.screen.click('[data-library-nav="reports"]')
    assert p.screen.eval("document.getElementById('library-leverageMin').value") == ""
    assert len(p.ids()) > 0, "the report rows are listed under the empty box"
