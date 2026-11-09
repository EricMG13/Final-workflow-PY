"""Library credit and market screening, through the Library screen.

apps/issuer-library/web/screening-credit-dom.test.cjs at final-workflow d877d8ce (plan-4c) ran the
page's scripts in jsdom over a hand-written catalogue. Here the real page opens in Chromium with
the same catalogue served as /api/catalogue; the expected ids, counts and orders come from the
answer-key files under tests/fixtures/library-credit/ and every filter-cases.json row is its own
case. The jsdom stubs (scrollTo, fetch, the badInput shim) are not needed: the browser's own
behaviour is what runs. Synthetic data only.
Marked browser: real browser proof.
"""

from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from issuer_library_browser import WEB, Screen, json_reply, open_app, release, until

pytestmark = pytest.mark.browser

KEYS = Path(__file__).parent / "fixtures" / "library-credit"


def load(name: str) -> Any:
    return json.loads((KEYS / name).read_text(encoding="utf-8"))


CATALOGUE = load("screening-catalogue.json")
CASES = load("filter-cases.json")
SORT_CASES = load("sort-cases.json")
TOTAL = len(CATALOGUE["real"])


def squash(text: str) -> str:
    return " ".join(text.split())


def by_name(name: str) -> dict[str, Any]:
    return next(c for c in CASES if c["name"] == name)


def js_number(value: Any) -> float:
    """Number(value) for the plain decimal strings the key holds."""
    text = "" if value is None else str(value).strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return math.nan


class Library:
    """The Library screen of the real app, driven through the page's own controls."""

    def __init__(self, screen: Screen) -> None:
        self.screen = screen
        self.page = screen.page

    @property
    def hash(self) -> str:
        return self.screen.hash()

    def ids(self) -> list[str]:
        selector = "#library-results button[data-library-select]"
        return [i or "" for i in self.screen.attrs(selector, "data-library-select")]

    def text(self, element_id: str) -> str:
        return squash(self.screen.text(f"#{element_id}"))

    def value(self, element_id: str) -> str:
        value: str = self.page.evaluate("i=>document.getElementById(i).value", element_id)
        return value

    def detail(self) -> str:
        return self.text("run-detail")

    def set(self, element_id: str, value: str) -> None:
        # The key's unreadable number text is "abc". A person cannot enter letters into a
        # Chromium number box (typing them leaves '' with badInput false); the text it keeps as
        # unreadable is "e", for which the browser itself reports badInput. jsdom needed a
        # defineProperty shim for this; here the real keyboard and the real validity state run.
        unreadable: bool = self.page.evaluate(
            "([i,v])=>{const el=document.getElementById(i);"
            "return el.type==='number'&&v!==''&&!Number.isFinite(Number(v));}",
            [element_id, value],
        )
        if unreadable:
            # The box sits in a closed disclosure: a person opens it first.
            self.page.evaluate(
                "i=>{const el=document.getElementById(i);el.value='';"
                "const d=el.closest('details');if(d&&!d.open)d.querySelector('summary').click();}",
                element_id,
            )
            self.page.focus(f"#{element_id}")
            self.page.keyboard.type("e")
            bad: bool = self.page.evaluate(
                "i=>document.getElementById(i).validity.badInput", element_id
            )
            assert bad, f"{element_id}: the browser did not report badInput"
            return
        self.page.evaluate(
            "([id,v])=>{const el=document.getElementById(id);el.value=v;"
            "el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));}",
            [element_id, value],
        )

    def through(self, filters: dict[str, str]) -> None:
        for key, value in filters.items():
            self.set(f"library-{key}", value)

    def logic(self, code: str) -> Any:
        return self.page.evaluate(f"JSON.parse(JSON.stringify({code}))")

    def cell(self, run_id: str, column: str) -> str:
        value: str = self.page.evaluate(
            """([id,column])=>{const text=el=>el.textContent.replace(/\\s+/g,' ').trim();
            const heads=[...document.querySelectorAll('#library-results thead th')].map(text);
            const i=heads.findIndex(h=>h.startsWith(column));
            return text(document.querySelector(
              `#library-results tr:has([data-library-select="${id}"])`).children[i]);}""",
            [run_id, column],
        )
        return value

    def row(self, run_id: str) -> str:
        selector = f'#library-results tr:has([data-library-select="{run_id}"])'
        return squash(self.screen.text(selector))

    def lines(self) -> list[tuple[str, str]]:
        """Each coverage line as (group, text)."""
        selector = "#library-coverage [data-library-coverage]"
        groups = [g or "" for g in self.screen.attrs(selector, "data-library-coverage")]
        texts = [squash(t) for t in self.screen.texts(selector)]
        return list(zip(groups, texts, strict=True))

    def click(self, selector: str) -> None:
        self.screen.click(selector)

    def option_text(self, element_id: str) -> str:
        value: str = self.page.evaluate(
            "i=>document.getElementById(i).selectedOptions[0].textContent", element_id
        )
        return value

    def options(self, element_id: str) -> list[list[str]]:
        values: list[list[str]] = self.page.evaluate(
            "i=>[...document.getElementById(i).options].map(o=>[o.textContent,o.value])",
            element_id,
        )
        return values


LibraryOpener = Callable[..., Library]


@pytest.fixture
def library(browser: Any) -> Iterator[LibraryOpener]:
    opened: list[Screen] = []

    def open_library(
        hash_route: str = "W-Library/cases", data: dict[str, Any] = CATALOGUE
    ) -> Library:
        reply = {
            "workspace": "",
            "policy_locked": False,
            "issues": [],
            "real": copy.deepcopy(data["real"]),
            "sources": copy.deepcopy(data["sources"]),
        }
        app = {"workspace": "", "policy_locked": False, "issues": [], "problem": ""}
        screen = open_app(browser, hash_route, app=app, api={"/api/catalogue": json_reply(reply)})
        opened.append(screen)
        return Library(screen)

    yield open_library
    release(opened)


@pytest.mark.parametrize("case", CASES, ids=[f"{c['focus']}: {c['name']}" for c in CASES])
def test_filter_case_through_the_controls(library: LibraryOpener, case: dict[str, Any]) -> None:
    p = library()
    p.through(case["filters"])
    assert sorted(p.ids()) == case["expected_ids"]
    coverage = case.get("coverage") or {}
    lines = p.lines()
    assert sorted(group for group, _ in lines) == sorted(coverage), "one line per active group"
    for group, shown in lines:
        recorded, hidden = coverage[group]["recorded"], coverage[group]["hidden"]
        assert f"recorded for {recorded} of {TOTAL} runs" in shown, shown
        assert (f"· {hidden} hidden · Show them" in shown) == (hidden > 0), shown
        if hidden:
            p.click(f'#library-coverage [data-library-coverage="{group}"] button')
            assert len(p.ids()) == hidden, f"{group}: Show them lists the key's hidden count"
            assert re.match(r"Hidden by .+: (no figure|not) recorded", p.text("library-results"))
            p.click("#library-results [data-library-back]")
            assert sorted(p.ids()) == case["expected_ids"], (
                "Back to results restores the matching rows"
            )


def test_rf17_show_them_lists_rows_that_carry_no_net_leverage_figure_none_that_carry_one(
    library: LibraryOpener,
) -> None:
    p = library()
    p.through({"runs": "any", "netLeverageMax": "4"})
    p.click('[data-library-coverage="net_leverage"] button')
    assert p.text("library-results").startswith("Hidden by Net leverage: no figure recorded")
    key = by_name("RF17 net leverage max 4, any")
    assert len(p.ids()) == key["coverage"]["net_leverage"]["hidden"]
    for run_id in p.ids():
        run = next(r for r in CATALOGUE["real"] if r["id"] == run_id)
        raw = (run["metrics"].get("net_leverage") or {}).get("value")
        value = str(raw if raw is not None else "").strip()
        assert value == "" or not math.isfinite(js_number(value)) or js_number(value) < 0, (
            f"{run_id} carries a figure"
        )


def test_default_latest_view_shows_the_key_rows_tags_what_latest_does_not_screen_and_says_how_many(
    library: LibraryOpener,
) -> None:
    p = library()
    key = by_name("default filters, latest")
    assert sorted(p.ids()) == key["expected_ids"]
    tagged = sorted(
        p.logic(
            "LibraryLogic.screened(window.DESIGN_CATALOGUE.real,{})"
            ".filter(e=>e.notScreened).map(e=>e.run.id)"
        )
    )
    assert sorted(i for i in p.ids() if "No report · not screened" in p.row(i)) == tagged
    assert "aldermoor-2025-001" in tagged, "the stopped run is tagged"
    left = len(by_name("runs any, no other filter")["expected_ids"]) - len(key["expected_ids"])
    assert re.search(f"{left} runs not screened.*Any run", p.text("library-coverage"))
    p.set("library-runs", "any")
    assert sorted(p.ids()) == by_name("runs any, no other filter")["expected_ids"]
    assert p.option_text("library-runs") == "Any run"
    assert not re.search("not screened", p.text("library-coverage"))


def test_rf18_leverage_reads_only_metrics_leverage_a_net_leverage_only_run_shows_a_dash(
    library: LibraryOpener,
) -> None:
    p = library()
    p.set("library-runs", "any")
    assert p.cell("fairholt-001", "Leverage").startswith("—")
    assert "×" in p.cell("fairholt-001", "Net leverage")
    assert p.options("library-basis")[0][0] == "All bases · definitions differ"


def test_rf20_the_rating_column_shows_the_lowest_rating_as_entered_with_agency_scope_and_date(
    library: LibraryOpener,
) -> None:
    p = library()
    p.set("library-runs", "any")
    assert p.cell("hartley-001", "Rating").startswith("(P)B2"), p.cell("hartley-001", "Rating")
    assert re.search("S&P|Fitch|Moody", p.cell("hartley-001", "Rating"))
    assert p.cell("kestrel-001", "Rating").startswith("—"), (
        "a scope-less rating is not counted under issuer scope"
    )
    assert p.option_text("library-ratingBelow") == "Any"
    assert ["BB+ / Ba1", "BB+/Ba1"] in p.options("library-ratingBelow")
    p.through(by_name("RF20 rating below B/B2, issuer scope, any runs")["filters"])
    issuer = p.ids()
    p.through({"ratingScope": "any"})
    assert sorted(p.ids()) == by_name("RF20 rating below B/B2, any scope, any runs")["expected_ids"]
    issuer_key = by_name("RF20 rating below B/B2, issuer scope, any runs")
    assert sorted(issuer) == issuer_key["expected_ids"]


def test_rf23_the_private_side_run_carries_a_private_side_label_in_its_row_and_its_detail(
    library: LibraryOpener,
) -> None:
    p = library()
    run_id = "brackenfell-hy-001"
    assert "Private-side" in p.row(run_id) and "High yield" in p.row(run_id)
    assert "Private-side" not in p.row("dunmore-001")
    p.click(f'[data-library-select="{run_id}"]')
    detail = p.detail()
    for shown in [
        "Private-side",
        "Classification",
        "High yield",
        "Currency",
        "USD",
        "Net leverage",
        "Undrawn facilities",
        "TLB",
        "Spread talk, low",
        "325",
        "bps",
        "Entered by the user · shown as entered",
        "Facilities & quotes as entered",
        "B · S&P",
    ]:
        assert shown in detail, shown
    source = '#run-detail [data-library-source="brackenfell-hy-001.TLB-talk_spread_bps_low"]'
    assert p.screen.exists(source), "a facility figure has View source"


def test_the_new_sort_buttons_are_native_buttons_and_sort_to_the_key_order_both_ways(
    library: LibraryOpener,
) -> None:
    for case in SORT_CASES:
        p = library()
        p.through(case["filters"])
        selector = f'[data-library-sort="{case["key"]}"]'
        shape = p.page.evaluate(
            "s=>{const b=document.querySelector(s);return [b.tagName,b.type];}", selector
        )
        assert shape == ["BUTTON", "button"]
        p.click(selector)
        if case["direction"] == "desc":
            p.click(selector)
        assert p.ids() == case["expected_ids"], case["name"]
        active: str = p.page.evaluate("document.activeElement.dataset.librarySort")
        assert active == case["key"]


def test_every_new_control_is_labelled_ids_are_unique_disclosures_report_their_active_count(
    library: LibraryOpener,
) -> None:
    p = library()
    need = [
        "runs", "classification", "currency", "ratingBelow", "ratingAbove", "ratingScope",
        "netLeverageMin", "netLeverageMax", "cashMin", "cashMax", "undrawnMin", "undrawnMax",
        "talkMin", "talkMax", "marginMin", "marginMax", "couponMin", "couponMax",
        "priceMin", "priceMax", "yieldMin", "yieldMax", "limitation",
    ]  # fmt: skip
    for key in need:
        info = p.page.evaluate(
            """k=>{const el=document.getElementById(`library-${k}`);
            if(!el)return null;
            const label=el.labels.length?el.labels[0].textContent.replace(/\\s+/g,' ').trim():'';
            return {label,number:el.type==='number'&&el.step==='any'};}""",
            key,
        )
        assert info is not None, key
        assert info["label"], f"{key} has a label"
        if re.search("(Min|Max)$", key):
            assert info["number"] is True, key
    ids: list[str] = p.page.evaluate("[...document.querySelectorAll('[id]')].map(x=>x.id)")
    assert len(ids) == len(set(ids))
    assert re.search("not screened", p.text("library-coverage"))
    assert p.screen.attr("#library-coverage", "role") == "status"
    p.set("library-currency", "EUR")
    p.set("library-talkMin", "300")
    summaries = [squash(s) for s in p.screen.texts("#library-filters details > summary")]
    joined = "|".join(summaries)
    assert any(
        s.startswith("Classification, rating & currency") and s.endswith("· 1 active")
        for s in summaries
    ), joined
    assert any(
        s.startswith("Facilities & quotes") and s.endswith("· 1 active") for s in summaries
    ), joined
    currencies = [value for _, value in p.options("library-currency")]
    assert currencies == ["", "EUR", "GBP", "USD"]
    assert "Matched within one facility" in p.text("library-filters")


def test_hostile_facility_id_and_limitation_text_render_as_text_and_create_no_element(
    library: LibraryOpener,
) -> None:
    bad = "<img src=x onerror=alert(1)>"
    data = copy.deepcopy(CATALOGUE)
    run = next(r for r in data["real"] if r["id"] == "brackenfell-hy-001")
    run["facilities"][0]["facility_id"] = bad
    run["gaps"] = [bad]
    p = library("W-Library/cases", data)
    p.click('[data-library-select="brackenfell-hy-001"]')
    assert bad in p.detail()
    assert p.screen.count('.library-screen img[src="x"],.library-screen [onerror]') == 0
    assert [bad, bad] in [[o[0], o[1]] for o in p.options("library-limitation")]
    p.set("library-limitation", bad)
    assert p.ids() == ["brackenfell-hy-001"]


def test_the_library_query_carries_the_filter_state_and_is_read_back_unknown_parts_are_dropped(
    library: LibraryOpener,
) -> None:
    p = library()
    p.through({"runs": "any", "netLeverageMax": "4"})
    p.click('[data-library-sort="net_leverage"]')
    assert p.hash == "#W-Library/cases?runs=any&netLeverageMax=4&sort=net_leverage&dir=asc"
    p.set("library-netLeverageMax", "")
    p.set("library-runs", "latest")
    assert p.hash == "#W-Library/cases?sort=net_leverage&dir=asc", "defaults are not written"
    key = by_name("RF17 net leverage max 4, any")
    q = library(
        "W-Library/cases?runs=any&netLeverageMax=4&ratingBelow=BB%2B%2FBa1&classification=high_yield"
    )
    assert q.value("library-netLeverageMax") == "4"
    assert q.value("library-runs") == "any"
    assert q.value("library-ratingBelow") == "BB+/Ba1"
    assert all(i in key["expected_ids"] for i in q.ids())
    r = library("W-Library/cases?runs=any&netLeverageMax=4&sort=net_leverage&dir=desc")
    assert sorted(r.ids()) == key["expected_ids"]
    descending = next(c for c in SORT_CASES if c["name"] == "net leverage descending, any")
    assert r.ids() == [i for i in descending["expected_ids"] if i in key["expected_ids"]]
    junk = library(
        "W-Library/cases?bogus=1&classification=nope&netLeverageMax=abc&runs=any&sort=nothing"
        f"&search={'x' * 300}"
    )
    values = [junk.value(f"library-{k}") for k in ["classification", "netLeverageMax", "query"]]
    assert values == ["", "", ""]
    assert junk.value("library-runs") == "any", "a valid part beside invalid ones is kept"
    assert len(junk.ids()) == TOTAL
    later = library()
    later.page.evaluate("location.hash='#W-Library/cases?runs=any&classification=high_yield'")
    until(later.page, "document.getElementById('library-classification').value==='high_yield'")
    assert later.value("library-classification") == "high_yield"
    assert sorted(later.ids()) == by_name("RF23 high yield, any")["expected_ids"]


def test_narrow_screens_stack_the_panel_table_and_detail() -> None:
    css = (WEB / "screen.css").read_text(encoding="utf-8")

    def block(width: int) -> str:
        found = []
        for m in re.finditer(rf"@media\(max-width:{width}px\)\{{", css):
            depth, i = 1, m.end()
            start = i
            while depth and i < len(css):
                depth += 1 if css[i] == "{" else -1 if css[i] == "}" else 0
                i += 1
            found.append(css[start : i - 1])
        return "".join(found)

    assert re.search(r"\.library-screen\{grid-template-columns:minmax\(0,1fr\)\}", block(900))
    assert re.search(
        r"\.library-filters,\.metric-grid,\.detail-layout\{grid-template-columns:minmax\(0,1fr\)\}",
        block(720),
    )


def test_rating_sort_follows_the_rating_scope_the_column_shows(library: LibraryOpener) -> None:
    p = library("W-Library/cases?runs=any&ratingScope=any&sort=rating&dir=asc")
    shown = [p.cell(i, "Rating").startswith("—") for i in p.ids()]
    assert False in shown and True in shown
    last_rated = len(shown) - 1 - shown[::-1].index(False)
    assert last_rated < shown.index(True), "rated rows sort before unrated rows"


def test_cash_and_undrawn_sort_as_metrics_missing_last(library: LibraryOpener) -> None:
    p = library()
    rows = CATALOGUE["real"]

    def fig(run_id: str, key: str) -> float | None:
        metric = next(r for r in rows if r["id"] == run_id)["metrics"].get(key)
        if not metric:
            return None
        raw = metric.get("value")
        if str("null" if raw is None else raw).strip() == "":
            return None
        value = js_number(raw)
        return value if value >= 0 else None

    for key in ["cash", "undrawn"]:
        out = p.logic(
            f"LibraryLogic.sortRuns(window.DESIGN_CATALOGUE.real,'{key}','desc').map(r=>r.id)"
        )
        have = [v for v in (fig(i, key) for i in out) if v is not None]
        assert have == sorted(have, reverse=True), key
        missing = [fig(i, key) is None for i in out]
        first_missing = missing.index(True) if True in missing else -1
        assert first_missing in (-1, len(have)), f"{key}: missing last"


def test_a_change_event_after_the_input_event_rebuilds_nothing_so_the_click_that_blurred_lands(
    library: LibraryOpener,
) -> None:
    p = library()
    p.through({"runs": "any"})
    connected: bool = p.page.evaluate(
        """()=>{const box=document.getElementById('library-netLeverageMax');
        box.value='4';box.dispatchEvent(new Event('input',{bubbles:true}));
        const button=document.querySelector('[data-library-hidden="net_leverage"]');
        box.dispatchEvent(new Event('change',{bubbles:true}));
        return button.isConnected;}"""
    )
    assert connected is True


def test_query_numbers_the_number_box_would_blank_are_dropped(library: LibraryOpener) -> None:
    p = library("W-Library/cases?runs=any&netLeverageMax=%2B4&cashMin=4.&undrawnMax=.5")
    values = [p.value(f"library-{k}") for k in ["netLeverageMax", "cashMin", "undrawnMax"]]
    assert values == ["", "", ".5"]


def test_the_latest_line_counts_what_any_run_adds_under_the_active_filters_from_the_key(
    library: LibraryOpener,
) -> None:
    p = library()
    latest = by_name("RF17 net leverage max 4, latest")
    any_run = by_name("RF17 net leverage max 4, any")
    p.through({"netLeverageMax": "4"})
    added = len(any_run["expected_ids"]) - len(latest["expected_ids"])
    assert re.search(
        f"{added} runs not screened by the Latest run rule", p.text("library-coverage")
    )


def test_the_private_side_detail_row_appears_only_for_a_private_side_run(
    library: LibraryOpener,
) -> None:
    p = library()
    p.click('[data-library-select="brackenfell-hy-001"]')
    assert "Private-side · Yes" in p.detail()
    p.click('[data-library-select="dunmore-001"]')
    assert "Private-side" not in p.detail()


def test_issuers_differing_only_in_case_are_one_nav_entry_and_one_issuer_in_the_count(
    library: LibraryOpener,
) -> None:
    key = load("issuer-case-cases.json")
    p = library("W-Library/cases", {"real": key["runs"], "sources": {}})
    p.set("library-runs", "any")
    entries = p.page.evaluate(
        """()=>{const text=el=>el.textContent.replace(/\\s+/g,' ').trim();
        return [...document.querySelectorAll('#library-nav [data-library-issuer]')].map(b=>({
          label:text(b.querySelector('span:not(.monogram):not(.count)')),
          count:Number(text(b.querySelector('.count'))),
          monogram:text(b.querySelector('.monogram')),
          issuer:b.dataset.libraryIssuer}));}"""
    )
    issuers = key["nav"]["issuers"]
    assert [{"label": e["label"], "count": e["count"]} for e in entries] == [
        {"label": i["label"], "count": i["count"]} for i in issuers
    ]
    assert [e["monogram"] for e in entries] == [i["monogram_from"][:3] for i in issuers]
    assert re.search(f"· {key['nav']['count_line_issuers']} issuers$", p.text("library-count"))
    p.click("#library-nav [data-library-issuer]")
    assert entries[0]["issuer"] == "TDG"
    assert sorted(p.ids()) == sorted(r["id"] for r in key["runs"] if r["issuer"].lower() == "tdg")


def test_an_address_issuer_matching_a_recorded_issuer_in_another_case_still_filters(
    library: LibraryOpener,
) -> None:
    key = load("issuer-case-cases.json")
    p = library("W-Library/cases?issuer=tdg&runs=any", {"real": key["runs"], "sources": {}})
    assert sorted(p.ids()) == sorted(r["id"] for r in key["runs"] if r["issuer"].lower() == "tdg")
    assert re.search("issuer=tdg", p.hash), "stored as given"


def test_the_nav_entry_of_a_case_folded_issuer_is_active_and_toggles_the_filter_off(
    library: LibraryOpener,
) -> None:
    key = load("issuer-case-cases.json")
    p = library("W-Library/cases?issuer=tdg&runs=any", {"real": key["runs"], "sources": {}})
    entry = '#library-nav [data-library-issuer="TDG"]'
    state = (
        "s=>{const e=document.querySelector(s);"
        "return [e.classList.contains('active'),e.getAttribute('aria-pressed')];}"
    )
    assert p.page.evaluate(state, entry) == [True, "true"]
    p.click(entry)
    assert len(p.ids()) == len(key["runs"]), "filter cleared: every run under Any"
    assert p.page.evaluate(state, entry)[0] is False
