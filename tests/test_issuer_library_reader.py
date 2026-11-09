"""The reader layer in a real browser: module names, the Summary, and reader sections.

The synthetic Northbridge store is written by hand in test_issuer_library_app.py. The reader
fixture is run through the library's own store, so these checks read what the app is given.
Marked browser: real browser proof, not a layout or visual acceptance.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from typing import Any

import pytest
from issuer_library_browser import ROOT, js, norm
from test_issuer_library_app import NORTHBRIDGE, NORTHBRIDGE_REPORTS, open_store

pytestmark = pytest.mark.browser

SPEC = importlib.util.spec_from_file_location(
    "library_store", ROOT / "apps/issuer-library/engine/store.py"
)
assert SPEC and SPEC.loader
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)
READER = ROOT / "apps/issuer-library/designs/reader-fixture/CP-1.md"
CODE = re.compile(r"\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])")
BOTTOM_LINE = "Total debt / EBITDA fell from 4.20x to 3.60x while liquidity held above 275."


def reader_output(before: str = "", after: str = "") -> dict[str, Any]:
    """The store's own reading of the reader fixture, optionally with one replacement."""
    text = READER.read_text(encoding="utf-8")
    if before:
        text = text.replace(before, after)
    sections = STORE.parse_source(text)
    value: dict[str, Any] = json.loads(
        json.dumps({"sections": sections, **STORE.reader_fields(sections)})
    )
    return value


def reader_store(fields: dict[str, Any] | None = None) -> dict[str, Any]:
    store = copy.deepcopy(NORTHBRIDGE)
    output_id = "web-1/CP-1.md"
    store["runs"]["web-1"]["modules"]["CP-1"] = {
        "outputs": [output_id],
        "inputs": [],
        "default": output_id,
    }
    base = {k: v for k, v in store["outputs"]["web-1/CP-4A.md"].items() if k != "parseError"}
    store["outputs"][output_id] = {
        **base,
        "id": output_id,
        "module": "CP-1",
        "source": "CP-1.md",
        "file": "web-1--CP-1.md",
        "label": "CP-1",
        "sha256": "dd" * 32,
        **(fields if fields is not None else reader_output()),
    }
    return store


@pytest.fixture
def northbridge(browser: Any) -> Any:
    opened: list[Any] = []

    def factory(route: str, store: dict[str, Any] | None = None) -> Any:
        screen = open_store(browser, route, store or NORTHBRIDGE, NORTHBRIDGE_REPORTS)
        opened.append(screen)
        return screen

    yield factory
    for screen in opened:
        assert screen.errors == []
        screen.close()


def test_module_codes_read_as_names_references_are_muted_and_evidence_stays_exact(
    fixture: Any,
) -> None:
    screen = fixture()
    facts = js(
        screen,
        "const named=text=>{const el=d.createElement('div');el.textContent=text;nameCodes(el);return el;};"
        "const refs=named('T4.3 normalization and C67');const refText=refs.textContent;"
        "const refList=[...refs.querySelectorAll('small.ref')].map(e=>e.textContent);"
        "nameCodes(refs);const nested=refs.querySelector('.ref .ref');"
        "const chart=d.createElement('div');chart.innerHTML='<svg><text>CP-2G</text></svg>';nameCodes(chart);"
        'return {possessive:named("CP-2G\'s assumed 20% earnings reduction").textContent,'
        "title:named('CP-2G').querySelector('abbr.module-ref').title,"
        "absorbed:named('CP-2F and CP-PARSE').textContent,unknown:named('CP-XYZ note').textContent,"
        "file:named('see CP-2-integrated.md').textContent,refText,refList,nested:nested===null,"
        "chart:chart.querySelector('text').textContent,abbr:chart.querySelector('abbr')===null};",
    )
    assert facts == {
        "possessive": "Forward credit model's assumed 20% earnings reduction",
        "title": "CP-2G",
        "absorbed": "Rates, FX & hedging and Source readiness",
        "unknown": "CP-XYZ note",
        "file": "see CP-2-integrated.md",
        "refText": "T4.3 normalization and C67",
        "refList": ["T4.3", "C67"],
        "nested": True,
        "chart": "Forward credit model",
        "abbr": True,
    }


def test_only_module_codes_change_on_any_reader_section_and_every_retained_character_restores(
    fixture: Any,
) -> None:
    screen = fixture()
    result = js(
        screen,
        "const pages=Object.entries(data).filter(([id])=>data[id].source)"
        ".flatMap(([id])=>modules[id].sections.map(s=>[id,s[0]])).filter(([,s])=>s!=='audit');"
        "const failures=[];"
        "for(const [id,section] of pages){const el=d.createElement('div');"
        "el.innerHTML=renderContent(id,section);const before=el.textContent;nameCodes(el);"
        "const left=el.textContent.match(/\\bCP-[A-Z0-9]+\\b(?![-.][A-Za-z0-9])/g);"
        "if(left)failures.push(id+'/'+section+' still shows '+left);"
        "el.querySelectorAll('abbr.module-ref').forEach(a=>a.replaceWith(a.title));"
        "if(el.textContent!==before)failures.push(id+'/'+section+' changed text');}"
        "return {pages:pages.length,failures};",
    )
    assert result["pages"] > 50
    assert result["failures"] == []


def test_the_route_names_codes_on_reader_pages_and_leaves_the_audit_and_inspector_exact(
    fixture: Any,
) -> None:
    screen = fixture("CP-2/assessment?c=tdg-002")
    assert not re.search(r"\bCP-\d", screen.content())
    screen.go("CP-2/audit?c=tdg-002")
    assert re.search(r"\bCP-\d", screen.content()), "the technical audit keeps codes"
    key = screen.eval(
        "[...evidence.entries()].find(([k,v])=>v.run==='tdg-002'&&v.fields.some(f=>/CP-\\d/.test(f[1])))[0]"
    )
    screen.page.evaluate("k=>showInspector(k)", key)
    assert re.search(r"\bCP-\d", screen.text("#inspector")), "the inspector keeps codes"


def test_the_app_is_organised_by_credit_question_and_its_chrome_shows_names_not_codes(
    fixture: Any,
) -> None:
    screen = fixture("CP-2G?c=tdg-003")
    assert screen.texts(".workspace-tabs a") == [
        "Overview",
        "Modules",
        "Calendar",
        "Forecast",
        "Reports",
        "Evidence",
    ]
    assert norm(screen.text(".module-title h2")) == "Forward credit model"
    assert screen.attr(".module-title h2", "title") == "CP-2G"
    assert not re.search(r"CP-", screen.eval("document.title"))
    assert screen.texts(".nav-group summary")[:7] == [
        "Business and evidence",
        "Financial performance",
        "Liquidity and refinancing",
        "Outlook and downside",
        "Capital structure and legal",
        "Relative value",
        "Decision and review",
    ]
    assert not re.search(r"\bCP-\d", screen.text("#module-list"))
    assert screen.attr(".module-item[aria-current]", "title") == "CP-2G"
    screen.eval(
        "()=>{document.getElementById('module-search').value='cp-2g';renderNavigator(current.module);}"
    )
    assert any("Forward credit model" in text for text in screen.texts(".module-item"))
    assert not re.search(r"\bCP-\d", screen.text("#search-results"))
    assert screen.exists(".module-title h2")
    screen.go("CP-2G/overview?c=tdg-003")
    assert screen.eval("current.module") == "CP-2G", "the code still works as a link"


def test_summary_leads_with_the_stored_call_and_never_promotes_a_finding(fixture: Any) -> None:
    screen = fixture("W-Overview/overview?c=tdg-002")
    band = norm(screen.text(".summary-lead"))
    assert (
        "Overall, TransDigm presents an established but not fully assessable business profile"
        in band
    )
    assert "Fundamental credit" in band
    assert screen.exists('.summary-lead [data-evidence$=":132"]'), "the band links its source line"
    assert (
        "Control rights, economic interest, shareholder concentration and private-equity sponsor"
        " status are therefore unestablished"
    ) in norm(screen.text('[data-module="CP-1A"]'))
    assert screen.eval("document.querySelector('.summary-lead').closest('.summary-text')") is None
    screen.eval(
        "()=>{document.querySelector('.summary-lead [data-evidence$=\":132\"]').click();renderRoute();}"
    )
    assert screen.hidden("inspector") is False, "its source opens from the Summary"
    assert screen.eval("current.module") == "W-Overview"


def test_a_one_section_page_does_not_repeat_its_heading_or_show_a_pager(fixture: Any) -> None:
    screen = fixture("W-Overview/overview?c=tdg-002")
    assert screen.eval("document.getElementById('section-title').classList.contains('sr-only')")
    assert not screen.exists("#next-section")


def test_every_card_on_a_summary_quotes_its_own_handoff(fixture: Any) -> None:
    screen = fixture()
    checked = 0
    for run in screen.eval("Object.keys(contexts)"):
        screen.go(f"W-Overview/overview?c={run}")
        assert screen.exists(".summary-lead"), run
        cards = js(
            screen,
            "return [...d.querySelectorAll('#content [data-output]')].flatMap(card=>{"
            "const text=card.querySelector('.summary-text');if(!text)return [];"
            "const copy=text.cloneNode(true);"
            "copy.querySelectorAll('abbr.module-ref').forEach(a=>a.replaceWith(a.title));"
            "return [{output:card.dataset.output,text:norm(copy.textContent)}];});",
        )
        for card in cards:
            raw = norm(
                (ROOT / "runs" / card["output"]).read_text(encoding="utf-8").replace("\n", " ")
            )
            assert card["text"] in raw, f"{card['output']}: {card['text'][:60]}"
            checked += 1
    assert checked >= 10, f"checked {checked}"


def test_a_run_in_the_library_opens_on_its_summary(fixture: Any) -> None:
    screen = fixture("W-Library/cases")
    hrefs = [str(h) for h in screen.attrs("#library-results a.run-link", "href")]
    link = next(h for h in hrefs if "c=tdg-002" in h)
    assert link.startswith("#W-Overview/overview?")


def test_a_run_with_no_stored_call_says_so_and_shows_its_findings_without_a_bottom_line(
    northbridge: Any,
) -> None:
    screen = northbridge("W-Overview?c=web-1")
    assert (
        norm(screen.text(".summary-lead"))
        == "No bottom line is stored for this run. Read the findings below."
    )
    assert not screen.exists(".call-quote")
    assert screen.exists("[data-module]"), "each module with an output still has a card"


def test_a_legal_sub_module_sits_with_the_legal_work_under_its_own_name(northbridge: Any) -> None:
    screen = northbridge("W-Overview?c=web-1")
    facts = js(
        screen,
        "const link=d.querySelector('.module-item[title=\"CP-4A\"]');"
        "return {label:norm(link.querySelector('.module-label').textContent),"
        "group:link.closest('.nav-group').dataset.group,"
        "other:[...d.querySelectorAll('.nav-group summary')].some(s=>s.textContent==='Other modules'),"
        "own:moduleLabel('CP-4A'),absorbed:moduleLabel('CP-2F')};",
    )
    assert facts == {
        "label": "Covenant capacity",
        "group": "Capital structure and legal",
        "other": False,
        "own": "Covenant capacity",
        "absorbed": "Rates, FX & hedging",
    }


def test_a_module_the_groups_do_not_know_stays_under_its_code_in_its_own_group(
    northbridge: Any,
) -> None:
    store = copy.deepcopy(NORTHBRIDGE)
    output = store["outputs"]["web-1/CP-4A.md"]
    store["runs"]["web-1"]["modules"]["CP-99"] = {
        "outputs": ["web-1/CP-99.md"],
        "inputs": [],
        "default": "web-1/CP-99.md",
    }
    store["outputs"]["web-1/CP-99.md"] = {
        **output,
        "id": "web-1/CP-99.md",
        "module": "CP-99",
        "source": "CP-99.md",
        "file": "web-1--CP-99.md",
        "label": "CP-99",
    }
    screen = northbridge("W-Overview?c=web-1", store)
    facts = js(
        screen,
        "const link=d.querySelector('.module-item[title=\"CP-99\"]');"
        "return {group:link.closest('.nav-group').dataset.group,"
        "label:norm(link.querySelector('.module-label').textContent)};",
    )
    assert facts == {"group": "Other modules", "label": "CP-99"}


def test_a_card_quotes_only_the_findings_section_never_a_later_section(northbridge: Any) -> None:
    store = copy.deepcopy(NORTHBRIDGE)
    store["outputs"]["web-1/deliveries/abc/CP-0.md"]["sections"][1:] = [
        {
            "heading": "Gaps",
            "level": 2,
            "line": 9,
            "blocks": [{"type": "text", "line": 9, "end": 9, "text": "A stated gap."}],
        }
    ]
    screen = northbridge("W-Overview?c=web-1", store)
    card = screen.text('.summary-card[data-module="CP-0"]')
    assert "A stated gap." not in card and "No written findings" in card


def test_a_card_quotes_a_finding_written_under_a_findings_subsection(northbridge: Any) -> None:
    store = copy.deepcopy(NORTHBRIDGE)
    store["outputs"]["web-1/deliveries/abc/CP-0.md"]["sections"][1:] = [
        {
            "heading": "Liquidity",
            "level": 3,
            "line": 8,
            "blocks": [{"type": "text", "line": 9, "end": 9, "text": "A located finding."}],
        }
    ]
    screen = northbridge("W-Overview?c=web-1", store)
    assert "A located finding." in screen.text('.summary-card[data-module="CP-0"]')


def test_summary_leads_with_the_reader_section_bottom_line_confidence_and_limitation(
    northbridge: Any,
) -> None:
    screen = northbridge("W-Overview?c=web-1", reader_store())
    lead = js(
        screen,
        "const lead=d.querySelector('.summary-lead');"
        "return {quote:norm(lead.querySelector('.call-quote').textContent),text:norm(lead.textContent),"
        "evidence:lead.querySelector('.source-link').dataset.evidence};",
    )
    assert lead["quote"] == BOTTOM_LINE
    assert re.search(r"Confidence\s*Medium", lead["text"])
    assert re.search(
        r"Main limitation\s*The maturity schedule has no FY2027 figure\.", lead["text"]
    )
    assert lead["evidence"] == "web-1/CP-1.md:17"


def test_summary_draws_chart_tables_with_their_exact_values_and_shows_a_gap_with_its_stated_reason(
    northbridge: Any,
) -> None:
    screen = northbridge("W-Overview?c=web-1", reader_store())
    charts = js(
        screen,
        "return [...d.querySelectorAll('.summary-chart')]"
        ".map(c=>({title:norm(c.querySelector('h2').textContent),"
        "rows:[...c.querySelectorAll('.chart-row')].map(r=>[norm(r.querySelector('.chart-label').textContent),"
        "norm(r.querySelector('strong').textContent)])}));",
    )
    assert [chart["title"] for chart in charts] == [
        "Leverage",
        "Interest cover",
        "Liquidity",
        "Debt maturities",
    ]
    assert charts[0]["rows"] == [
        ["FY2023Total debt / EBITDA", "4.20"],
        ["FY2023Net debt / EBITDA", "3.85"],
        ["FY2024Total debt / EBITDA", "3.60"],
        ["FY2024Net debt / EBITDA", "3.25"],
    ]
    assert charts[3]["rows"] == [
        ["FY2026Debt maturing", "500"],
        ["FY2027Debt maturing", "Not supplied: the schedule stops here"],
        ["FY2028Debt maturing", "1,250"],
    ]


def test_a_handoff_with_a_reader_section_opens_on_it_and_hostile_text_stays_text(
    northbridge: Any,
) -> None:
    screen = northbridge("CP-1?c=web-1", reader_store())
    facts = js(
        screen,
        "const c=d.getElementById('content');"
        "return {quote:norm(d.querySelector('.analysis-call .call-quote').textContent),"
        "call:norm(d.querySelector('.analysis-call').textContent),image:c.querySelector('img[src=\"x\"]')===null,"
        "text:c.textContent,records:c.querySelectorAll('.record h3').length};",
    )
    assert facts["quote"] == BOTTOM_LINE
    assert re.search(r"Main limitation\s*The maturity schedule", facts["call"])
    assert facts["image"]
    assert "<img src=x onerror=alert(document.domain)>" in facts["text"]
    assert "More debt capacity before a covenant test." in facts["text"]
    assert facts["records"] == 2, (
        "the band holds the bottom line row; only findings stay as records"
    )


def test_a_chart_section_is_named_for_its_measure_and_draws_its_table_above_the_exact_rows(
    northbridge: Any,
) -> None:
    output = reader_output()
    line = next(s["line"] for s in output["sections"] if s["heading"] == "Chart data: leverage")
    screen = northbridge(f"CP-1/s{line}?c=web-1", reader_store(output))
    assert norm(screen.text("#section-title")) == "Leverage"
    assert screen.count("#content .chart-row") == 4
    assert "Synthetic." in screen.content(), "the exact table stays below the chart"


def test_a_malformed_reader_section_is_named_and_the_handoff_still_renders_with_no_bottom_line(
    northbridge: Any,
) -> None:
    fields = reader_output("| Bottom line |", "| Conclusion |")
    assert re.search(r"Reader summary", fields["issue"])
    assert fields["summary"] is None
    screen = northbridge("W-Overview?c=web-1", reader_store(fields))
    assert re.search(r"No bottom line is stored", screen.text(".summary-lead"))
    assert screen.exists('.summary-card[data-module="CP-1"]')
    screen.go("CP-1?c=web-1")
    assert "Total debt / EBITDA fell" in screen.content(), "its rows stay readable"


def test_a_stopped_run_holding_only_one_module_shows_it_as_the_lead_and_no_card(
    northbridge: Any,
) -> None:
    store = reader_store()
    del store["runs"]["web-1"]["modules"]["CP-4A"]
    del store["runs"]["web-1"]["modules"]["CP-0"]
    del store["outputs"]["web-1/CP-4A.md"]
    del store["outputs"]["web-1/deliveries/abc/CP-0.md"]
    screen = northbridge("W-Overview?c=web-1", store)
    assert screen.exists(".summary-lead .call-quote"), "its bottom line leads"
    assert screen.attrs(".summary-card", "data-module") == [], "the lead module repeats no card"
    assert screen.count(".question-map>section") == 0, "a group left with no card is omitted"


def test_a_reader_section_opens_first_even_when_the_catalogue_names_another_heading(
    northbridge: Any,
) -> None:
    store = reader_store()
    store["outputs"]["web-1/CP-1.md"]["firstHeading"] = "Chart data: liquidity"
    screen = northbridge("CP-1?c=web-1", store)
    assert norm(screen.text("#section-title")) == "Reader summary"
    assert screen.exists(".analysis-call .summary-facts")


def test_a_catalogue_first_heading_with_no_body_of_its_own_still_opens_a_real_section(
    northbridge: Any,
) -> None:
    store = reader_store(reader_output("| Bottom line |", "| Conclusion |"))
    store["outputs"]["web-1/CP-1.md"]["firstHeading"] = "Findings"
    screen = northbridge("CP-1?c=web-1", store)
    assert "Total debt / EBITDA fell" in screen.content()
