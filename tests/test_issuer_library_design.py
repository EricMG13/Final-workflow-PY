"""The curated retained runs in a real browser; answer keys are written here by hand.

The fixture is built strictly by designs/build.py, so a stale curated pin fails here.
Marked browser: real browser proof, not a layout or visual acceptance.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from issuer_library_browser import FIXTURE, ROOT, WEB, Screen, design_store, open_app

pytestmark = pytest.mark.browser

PIN = {
    "CP-1": "tdg-002/CP-1-attempt-2.md",
    "CP-1A": "tdg-002/CP-1A-attempt-3.md",
    "CP-2": "tdg-002/CP-2-attempt-2.md",
    "CP-1C": "tdg-peers-2024-001/CP-1C-attempt-2.md",
    "CP-6": "ford-otosan-2024-001/CP-6-attempt-1.md",
    "CP-8": "tdg-run-comparison-001/CP-8.md",
}
KEY_A: dict[str, dict[str, Any]] = {
    "tdg-002": {
        "folder": "tdg-002",
        "outputs": {
            "CP-1": ["CP-1-attempt-1.md", "CP-1-attempt-2.md"],
            "CP-1A": ["CP-1A-attempt-1.md", "CP-1A-attempt-2.md", "CP-1A-attempt-3.md"],
            "CP-2": ["CP-2-attempt-1.md", "CP-2-attempt-2.md"],
            "CP-2A": ["CP-2A-attempt-1.md"],
            "CP-2D": ["CP-2D-attempt-1.md"],
        },
        "inputs": [],
    },
    "tdg-003": {
        "folder": "tdg-003",
        "outputs": {
            "CP-0": ["CP-0.md"],
            "CP-1": ["CP-1-attempt-1.md", "CP-1-attempt-2.md"],
            "CP-1B": ["CP-1B-attempt-1.md"],
            "CP-1D": ["CP-1D-attempt-1.md"],
            "CP-2": ["CP-2-integrated.md", "CP-2-macro-update.md", "CP-2-quality-update.md"],
            "CP-2A": ["CP-2A-calendar-attempt-1.md"],
            "CP-2D": ["CP-2D-attempt-1.md", "CP-2D-calendar-consumer.md"],
            "CP-2E": ["CP-2E-attempt-1.md", "CP-2E-attempt-2.md"],
            "CP-2G": ["CP-2G-attempt-1.md", "CP-2G-attempt-2.md"],
            "CP-2H": ["CP-2H-evidence-check.md"],
        },
        "inputs": [],
    },
    "tdg-004": {
        "folder": "tdg-004",
        "outputs": {
            "CP-0": ["CP-0.md"],
            "CP-3C": ["CP-3C-legal-consumer.md"],
            "CP-4": ["CP-4-attempt-1.md", "CP-4-attempt-2.md"],
        },
        "inputs": [],
    },
    "tdg-guidance": {
        "folder": "tdg-guidance-001",
        "outputs": {"CP-DR": ["CP-DR-attempt-1.md"]},
        "inputs": [],
    },
    "tdg-peers-2024": {
        "folder": "tdg-peers-2024-001",
        "outputs": {
            "CP-0": ["CP-0.md"],
            "CP-1C": ["CP-1C-attempt-1.md", "CP-1C-attempt-2.md"],
            "CP-2": ["CP-2-peer-consumer.md"],
        },
        "inputs": [
            "CP-1-peer-inputs-attempt-2.md",
            "CP-1-peer-inputs.md",
            "CP-2-delivery-input-attempt-2.md",
            "CP-2-delivery-input-final.md",
            "CP-2-delivery-input.md",
        ],
    },
    "ford-otosan-2024": {
        "folder": "ford-otosan-2024-001",
        "outputs": {
            "CP-0": ["CP-0.md"],
            "CP-2G": ["CP-2G-published-forecast.md"],
            "CP-2H": ["CP-2H-attempt-1.md", "CP-2H-attempt-2.md"],
            "CP-3C": ["CP-3C-consumer.md"],
            "CP-5": ["CP-5-attempt-1.md"],
            "CP-6": ["CP-6-attempt-1.md"],
        },
        "inputs": ["CP-1-selected-input.md"],
    },
    "frontier-2020": {
        "folder": "frontier-2020-001",
        "outputs": {
            "CP-0": ["CP-0.md"],
            "CP-3": ["CP-3-recovery-consumer.md"],
            "CP-4C": ["CP-4C-attempt-1.md"],
        },
        "inputs": [],
    },
    "tdg-run-comparison": {
        "folder": "tdg-run-comparison-001",
        "outputs": {"CP-2": ["CP-2-consumer.md"], "CP-8": ["CP-8-recheck.md", "CP-8.md"]},
        "inputs": ["CP-2-delivery.md"],
    },
}
KEY_B = {
    "CP-0": ["tdg-003", "tdg-004", "tdg-peers-2024", "ford-otosan-2024", "frontier-2020"],
    "CP-1": ["tdg-002", "tdg-003"],
    "CP-1A": ["tdg-002"],
    "CP-1B": ["tdg-003"],
    "CP-1C": ["tdg-peers-2024"],
    "CP-1D": ["tdg-003"],
    "CP-2": ["tdg-002", "tdg-003", "tdg-peers-2024", "tdg-run-comparison"],
    "CP-2A": ["tdg-002", "tdg-003"],
    "CP-2D": ["tdg-002", "tdg-003"],
    "CP-2E": ["tdg-003"],
    "CP-2G": ["tdg-003", "ford-otosan-2024"],
    "CP-2H": ["tdg-003", "ford-otosan-2024"],
    "CP-3": ["frontier-2020"],
    "CP-3C": ["tdg-004", "ford-otosan-2024"],
    "CP-4": ["tdg-004"],
    "CP-4C": ["frontier-2020"],
    "CP-5": ["ford-otosan-2024"],
    "CP-6": ["ford-otosan-2024"],
    "CP-8": ["tdg-run-comparison"],
    "CP-DR": ["tdg-guidance"],
}
KEY_C = [
    (
        "tdg-fy2024-snapshot",
        "Initial snapshot · failed date presentation",
        "tdg-002/CP-2-attempt-2.md",
        "249d0cbdf1ba",
        "38eac27cebeb",
        "Superseded",
    ),
    (
        "tdg-fy2024-snapshot-2",
        "Annual snapshot · reviewed",
        "tdg-002/CP-2-attempt-2.md",
        "249d0cbdf1ba",
        "324952b09a08",
        None,
    ),
    (
        "tdg-fy2024-snapshot-3",
        "Integrated · macro/ESG and conditional forecast",
        "tdg-003/CP-2-integrated.md",
        "828e78d47cbb",
        "00186b0f4bdd",
        None,
    ),
    (
        "tdg-fy2024-snapshot-4",
        "Peer comparison · first delivery, gap rows dropped",
        "tdg-peers-2024-001/CP-2-delivery-input.md",
        "b88d1dfce706",
        "084e27e00b1d",
        None,
    ),
    (
        "tdg-fy2024-snapshot-5",
        "Peer comparison · gap boundary repaired",
        "tdg-peers-2024-001/CP-2-delivery-input-attempt-2.md",
        "54247baa99d3",
        "5ba26c11e2ee",
        None,
    ),
    (
        "tdg-fy2024-snapshot-6",
        "Peer comparison · exact fiscal dates added",
        "tdg-peers-2024-001/CP-2-delivery-input-final.md",
        "ba312d7faa8a",
        "6bc718146295",
        None,
    ),
    (
        "tdg-fy2024-snapshot-7",
        "CP-8 repairs applied",
        "tdg-run-comparison-001/CP-2-delivery.md",
        "22edd045e3d6",
        "c7c4156e7c2a",
        "Latest",
    ),
]
REPORTS_BY_RUN = {
    "tdg-002": [1, 2, 3, 4, 5, 6, 7],
    "tdg-003": [3],
    "tdg-004": [],
    "tdg-guidance": [],
    "tdg-peers-2024": [4, 5, 6],
    "ford-otosan-2024": [],
    "frontier-2020": [],
    "tdg-run-comparison": [7],
}
KEY_D = [
    ("CP-2", 12, "Not classified"),
    ("CP-2", 35, "Analyst Interpretation"),
    ("CP-2", 132, "Analyst Interpretation"),
    ("CP-2", 39, "Documentary Fact"),
    ("CP-2", 45, "Insufficient Information · Documentary Fact"),
    ("CP-2", 84, "Analyst Interpretation"),
    ("CP-2", 85, "Analyst Interpretation"),
    ("CP-1A", 44, "Documentary Fact"),
    ("CP-1A", 46, "Analyst Interpretation"),
    ("CP-1A", 70, "Documentary Fact"),
    ("CP-6", 88, "Not classified"),
    ("CP-6", 143, "Not classified"),
    ("CP-1", 246, "Not classified"),
]
NORM = "s=>s.replace(/\\*\\*|`/g,'').replace(/\\s+/g,' ').trim()"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def design() -> tuple[dict[str, Any], dict[str, Any]]:
    return design_store()


@pytest.fixture
def fixture(browser: Any, design: tuple[dict[str, Any], dict[str, Any]]) -> Any:
    opened: list[Screen] = []

    def factory(
        hash_route: str = "CP-1/performance", viewport: tuple[int, int] = (1280, 600)
    ) -> Screen:
        screen = open_app(browser, hash_route, design[0], design[1], viewport=viewport)
        opened.append(screen)
        return screen

    yield factory
    for screen in opened:
        assert screen.errors == []
        screen.close()


def search_groups(screen: Screen) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = screen.eval(
        "[...document.querySelectorAll('#search-results .search-group')].map(g=>({title:g.querySelector('p')"
        ".textContent,hits:[...g.querySelectorAll('a.search-hit')].map(a=>({href:a.getAttribute('href'),"
        "label:a.getAttribute('aria-label'),text:a.textContent}))}))"
    )
    return groups


def context_of(href: str) -> str | None:
    from urllib.parse import parse_qs

    query = href.split("?", 1)[1] if "?" in href else ""
    return parse_qs(query).get("c", [None])[0]


def test_every_retained_body_block_is_reachable_in_exactly_one_named_section(fixture: Any) -> None:
    screen = fixture()
    result = screen.eval(
        f"""()=>{{const norm={NORM};const failures=[];let covered=0;
        for(const [id,out] of Object.entries(data)){{
          for(const s of out.sections.filter(s=>s.blocks.length)){{
            const count=modules[id].sections.filter(d=>d[2].some(p=>matchesHeading(s.heading,p))).length;
            if(count!==1)failures.push(`${{id}}: ${{s.heading}} in ${{count}} sections`);}}
          for(const s of modules[id].sections){{
            const text=norm(window.__fragment(renderContent(id,s[0])));
            for(const block of sectionData(id,s[0]).flatMap(x=>x.blocks)){{
              const values=block.type==='text'?[block.text]:block.rows.flatMap(r=>r.cells);
              for(const value of values)if(!text.includes(norm(value)))failures.push(`${{id}}/${{s[0]}} line ${{block.line}}: ${{value.slice(0,70)}}`);
              covered++;}}}}}}
        return {{failures,covered}};}}"""
    )
    assert result["failures"] == []
    assert result["covered"] > 100


def test_financial_chart_uses_retained_periods_and_values_and_exact_rows(fixture: Any) -> None:
    screen = fixture()
    assert screen.texts(".bar-period") == ["FY2022", "FY2023", "FY2024"]
    assert screen.texts(".bar-value") == ["5,429", "6,585", "7,940"]
    statements = norm(
        screen.fragment_text(screen.eval(f"renderContent('{PIN['CP-1']}','statements')"))
    )
    assert "2,923" in statements and "(1)" in statements and "—" in statements
    assert "2,992" not in statements


def test_inspector_retains_unknown_classification_units_and_exact_row(fixture: Any) -> None:
    screen = fixture()
    trigger = f'[data-evidence="{PIN["CP-1"]}:246"]'
    screen.eval("document.getElementById('content').scrollTop=343")
    screen.eval(f"()=>{{document.querySelector('{trigger}').click();renderRoute();}}")
    assert screen.active() == "back-analysis"
    assert screen.hidden("inspector") is False
    text = screen.text("#inspector")
    for value in ["Not classified", "USD millions", "7,940", "6,585", "5,429", "Reported, PDF 106"]:
        assert value in text, value
    screen.eval("document.getElementById('content').scrollTop=777")
    screen.eval(
        "()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));renderRoute();}"
    )
    assert screen.hidden("inspector") is True
    assert screen.eval(f"document.activeElement===document.querySelector('{trigger}')")
    assert screen.eval("document.getElementById('content').scrollTop") == 343


def test_timeline_keeps_all_nine_events_and_never_assigns_days_to_fiscal_dates(
    fixture: Any,
) -> None:
    screen = fixture("CP-1A/events")
    assert screen.count(".timeline li") == 9
    assert screen.count(".timeline:not(.periods) li") == 5
    assert screen.count(".periods li") == 4
    october = screen.eval(
        "[...document.querySelectorAll('.timeline li')].find(e=>e.querySelector('strong').textContent"
        "==='October 2024').textContent"
    )
    assert "Month only" in october


def test_six_factor_assessment_preserves_producer_grades(fixture: Any) -> None:
    screen = fixture("CP-2/assessment")
    assert screen.texts(".grade") == [
        "Average",
        "Not Assessable",
        "Not Assessable",
        "Not Assessable",
        "Average",
        "Weak",
    ]
    assert screen.count(".grade.adverse") == 1
    assert "confidence Medium" in screen.content()


def test_section_navigation_topic_search_invalid_links_and_skip_link(fixture: Any) -> None:
    screen = fixture("CP-1A/ownership")
    screen.click(".skip")
    assert screen.hash().startswith("#CP-1A/ownership") and screen.active() == "analysis"
    screen.set_value("#module-search", "cash generation")
    assert screen.attr("a.module-item", "href") == "#CP-1/cash?c=tdg-002"
    screen.go("CP-2/no-such-section?e=99999")
    assert "Fundamental credit" in screen.text("#module-head")
    assert screen.text("#section-title") == "Integrated assessment"
    assert screen.hidden("inspector") is True


def test_retained_text_is_escaped_before_formatting_and_nothing_is_remote(fixture: Any) -> None:
    screen = fixture()
    assert (
        screen.eval("rich('<img src=x onerror=alert(1)>')") == "&lt;img src=x onerror=alert(1)&gt;"
    )
    references: list[str] = screen.eval(
        "[...document.querySelectorAll('script[src],link[rel=stylesheet],img[src]')]"
        ".map(e=>e.getAttribute('src')||e.getAttribute('href'))"
    )
    for relative in references:
        assert not re.match(r"^https?:", relative), relative
        name = relative.split("?")[0]
        assert any((folder / name).exists() for folder in (WEB, FIXTURE)), relative


def test_every_module_primary_view_renders_without_fictitious_values(fixture: Any) -> None:
    screen = fixture()
    ids: list[str] = screen.eval("groups.flatMap(g=>g[1].map(m=>m[0]))")
    assert len(ids) == 22
    for module in ids:
        screen.go(module)
        assert len(screen.content()) > 200, module
        assert "NaN" not in screen.inner_html("#content"), module
        assert "undefined" not in screen.text("#module-head"), module
    for module, issuer in [
        ("CP-2H", "Ford Otosan"),
        ("CP-4C", "Frontier"),
        ("CP-2G", "TransDigm Group"),
    ]:
        screen.go(module)
        assert screen.text(".issuer h1") == issuer
    for module in ["CP-L10", "CP-3D"]:
        screen.go(module)
        assert screen.exists(".missing-state")
        assert screen.count("#content svg,.chart-row") == 0


def test_numeric_parsing_and_peer_comparison_preserve_absence_and_precision(fixture: Any) -> None:
    screen = fixture("CP-1C")
    parsed = screen.eval(
        "['—','','not available','1,234.50','(12.5)','0','86.5398%','Infinity','around 2x'].map(chartNumber)"
    )
    assert parsed == [None, None, None, 1234.5, -12.5, 0, 86.5398, None, None]
    screen.set_value("#chart-metric", "1", "change")
    assert screen.active() == "chart-metric"
    rows = screen.texts(".chart-row")
    assert len(rows) == 4 and "Not available" in rows[3] and "44.47" in rows[0]
    assert screen.exists(".chart-row:nth-of-type(4) .missing") or screen.eval(
        "Boolean([...document.querySelectorAll('.chart-row')][3].querySelector('.missing'))"
    )
    screen.go("CP-3C")
    assert screen.count(".negative") == 2
    assert "TRY billions" in screen.text(".section-heading")


def test_conditional_path_cash_bridge_and_recovery_graphics_use_retained_values(
    fixture: Any,
) -> None:
    screen = fixture("CP-2G")
    assert screen.texts(".path-readout strong") == ["6,036.61", "2,652.78", "6,594.60"]
    assert screen.count("polyline") == 3
    screen.go("CP-2D")
    assert screen.count(".vector-chart rect") == 6
    chart = screen.text(".vector-chart")
    assert "(2,441)" in chart and "4,972" not in chart
    screen.go("CP-4C")
    assert screen.texts(".chart-row strong") == [
        "86.5398%",
        "100.0000%",
        "9.5291%",
        "74.9657%",
        "9.5291%",
        "13.8421%",
    ]


def test_calendar_source_inspection_keeps_owning_module_and_returns(fixture: Any) -> None:
    screen = fixture("W-Calendar/hedges")
    base = float(
        screen.eval("parseFloat(document.querySelectorAll('.hedge-axis span')[1].style.left)")
    )
    assert 33 < base < 34
    assert screen.count(".hedge-span.future") == 4 and screen.count(".hedge-span:not(.future)") == 4
    screen.eval("()=>{document.querySelector('.hedge-row').click();renderRoute();}")
    assert "CP-2E" in screen.text("#inspector")
    assert screen.hash().startswith("#W-Calendar/hedges?c=tdg-003&e=tdg-003%2FCP-2E-attempt-2.md")
    screen.eval("()=>{document.getElementById('back-analysis').click();renderRoute();}")
    assert screen.hash() == "#W-Calendar/hedges?c=tdg-003"


def test_evidence_cases_are_isolated_and_report_selection_changes_preview_and_original(
    fixture: Any,
) -> None:
    screen = fixture("W-Evidence/sources?c=ford-otosan-2024")
    assert screen.count(".source-inventory>section") == 8 and "TDG-002" not in screen.content()
    screen.go("W-Evidence/sources?c=tdg-002")
    assert "Ford Otosan" not in screen.content() and "Frontier" not in screen.content()
    screen.go("W-Reports/tdg-fy2024-snapshot-6")
    assert screen.attr("#report-preview", "src") == "reports/tdg-fy2024-snapshot-6/preview.html"
    assert (
        screen.attr(".report-tools a[download]", "href")
        == "reports/tdg-fy2024-snapshot-6/original.html"
    )
    assert screen.attr("#report-preview", "sandbox") == "allow-scripts allow-downloads"
    screen.go("W-Library/cases")
    assert screen.count(".case-list>section") == 3


def test_malformed_and_inherited_object_route_keys_cannot_break_navigation(fixture: Any) -> None:
    screen = fixture()
    for hash_route in ["toString/x", "__proto__/x", "constructor/x"]:
        screen.go(hash_route)
        assert screen.eval("current.module") == "W-Library", hash_route
    screen.go("CP-2H/s31?e=CP-1:246")
    assert screen.hidden("inspector") is True


def test_an_analytical_verdict_is_not_promoted_to_a_provenance_classification(fixture: Any) -> None:
    screen = fixture("CP-6")
    last = screen.eval("document.querySelectorAll('.debate')[2].textContent")
    assert "Insufficient Information" in last
    assert (
        screen.eval(
            "document.querySelectorAll('.debate')[2].querySelector('.source-footer .tag').textContent"
        )
        == "Not classified"
    )
    assert (
        screen.eval(
            "classification({fields:[['Evidence classification','Insufficient Information']]})"
        )
        == "Insufficient Information"
    )
    screen.go("CP-1D")
    assert screen.count(".vector-chart rect") == 6 and "4,173" in screen.text(".vector-chart")


def test_workspace_tabs_preserve_issuer_and_run_and_never_substitute_another_case(
    fixture: Any,
) -> None:
    screen = fixture("CP-2H")
    for name in ["Calendar", "Deliverables", "Evidence", "Overview", "Modules"]:
        href = screen.eval(
            f"[...document.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent==='{name}').getAttribute('href')"
        )
        screen.go(href[1:])
        assert screen.text(".issuer h1") == "Ford Otosan", name
        assert screen.eval("current.context") == "ford-otosan-2024", name
        assert not screen.exists("#content iframe"), name
        if name in ("Calendar", "Deliverables"):
            assert "remains selected" in screen.content()
    screen.go("CP-1/performance?c=ford-otosan-2024")
    assert screen.exists(".missing-state") and screen.count(".bar-column") == 0
    assert "Inputs only" in screen.text(".missing-state")
    assert "CP-1-selected-input.md" in screen.content() and not screen.exists(".available-case a")
    screen.go("CP-1/performance?c=ford-otosan-2024&e=CP-1:246")
    assert screen.hidden("inspector") is True


def test_tdg_runs_and_delivery_collection_are_distinct_and_survive_a_fresh_deep_link(
    fixture: Any,
) -> None:
    screen = fixture("CP-2G")
    calendar = screen.eval(
        "[...document.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent==='Calendar').hash"
    )
    screen.go(calendar[1:])
    assert screen.count(".hedge-row") == 9 and screen.count(".timeline li") == 0
    screen.go("W-Reports/unavailable?c=tdg-003")
    assert not screen.exists("#content iframe")
    assert "Build 3" in screen.content() and "tdg-deliveries" not in screen.inner_html("#content")
    screen.go("W-Evidence/sources?c=tdg-003")
    assert screen.count(".source-inventory>section") == 16 and "TDG-002" not in screen.content()
    cold = fixture("W-Reports/unavailable?c=ford-otosan-2024")
    assert cold.text(".issuer h1") == "Ford Otosan" and not cold.exists("#content iframe")


def test_narrative_claims_expose_exact_retained_evidence_without_hard_wrapping(
    fixture: Any,
) -> None:
    screen = fixture("CP-4/s75")
    assert screen.count(".finding") == 3 and screen.count(".finding br") == 0
    screen.eval(
        "()=>{const b=document.querySelector('.finding .source-link');b.focus();b.click();renderRoute();}"
    )
    assert "2.0" in screen.text("#inspector")
    assert "Not classified" in screen.text(".finding .tag")
    screen.eval("()=>{document.getElementById('back-analysis').click();renderRoute();}")
    assert screen.eval("document.activeElement===document.querySelector('.finding .source-link')")


def test_grouped_outline_has_unique_labels_absorbed_aliases_and_persistent_disclosures(
    fixture: Any,
) -> None:
    screen = fixture("CP-2E")
    assert screen.count(".outline-group") >= 4 and screen.count(".section-item") == 21
    key = screen.eval(
        "()=>{const d=document.querySelector('.outline-group');d.querySelector('summary').click();return d.dataset.group;}"
    )
    screen.eval(
        "()=>{const n=document.getElementById('next-section');n.focus();n.click();renderRoute();}"
    )
    assert screen.active() == "next-section"
    assert (
        screen.eval(
            f"[...document.querySelectorAll('.outline-group')].find(e=>e.dataset.group==='{key}').open"
        )
        is False
    )
    screen.set_value("#module-search", "CP-2F")
    assert screen.count(".module-item") == 1
    assert "CP-2E" in screen.eval("document.querySelector('.module-item').href")
    screen.go("CP-4/s75")
    screen.eval(
        "()=>{document.getElementById('module-search').value='';renderNavigator(current.module);}"
    )
    labels = screen.texts(".section-item")
    assert len(set(labels)) == len(labels)
    screen.go("CP-2F")
    assert screen.eval("current.module") == "CP-2E"


def test_every_conditional_point_and_bridge_movement_has_keyboard_evidence(fixture: Any) -> None:
    screen = fixture("CP-2G")
    assert screen.count(".plot-point") == 9
    assert "2026" in screen.eval(
        "document.querySelectorAll('.plot-point')[1].getAttribute('aria-label')"
    )
    screen.eval(
        "()=>{const p=document.querySelectorAll('.plot-point')[1];p.focus();"
        "p.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));renderRoute();}"
    )
    assert "2026" in screen.text("#inspector") and screen.active() == "back-analysis"
    screen.eval("()=>{document.getElementById('back-analysis').click();renderRoute();}")
    assert screen.eval("document.activeElement===document.querySelectorAll('.plot-point')[1]")
    screen.go("CP-2D")
    assert screen.count(".plot-point") == 6


def test_remembered_section_reading_positions_are_isolated_by_run_and_destination(
    fixture: Any,
) -> None:
    screen = fixture("CP-4/s75", viewport=(1280, 400))
    screen.eval("document.getElementById('content').scrollTop=270")
    assert screen.eval("document.getElementById('content').scrollTop") == 270, (
        "content is scrollable"
    )
    screen.go("CP-4/s100?c=tdg-004")
    assert screen.eval("document.getElementById('content').scrollTop") == 0
    screen.go("CP-4/s75?c=tdg-004")
    assert screen.eval("document.getElementById('content').scrollTop") == 270
    screen.go("CP-4/s75?c=ford-otosan-2024")
    assert screen.eval("document.getElementById('content').scrollTop") == 0


def test_legacy_evidence_routes_reject_inherited_object_names(fixture: Any) -> None:
    for section in ["constructor", "__proto__", "toString"]:
        assert fixture(f"W-Evidence/{section}").text(".issuer h1") == "TransDigm Group"


def test_navigation_focus_targets_remain_visible_on_a_narrow_screen(fixture: Any) -> None:
    screen = fixture("CP-2G", viewport=(640, 800))
    screen.eval(
        "()=>{const s=[...document.querySelectorAll('.section-item')].find(a=>a.textContent==='Assumption register');"
        "s.focus();location.hash=s.hash;renderRoute();}"
    )
    assert screen.active() == "section-title"
    assert (
        screen.eval("document.getElementById('navigator').classList.contains('mobile-open')")
        is False
    )
    screen.go("W-Reports/tdg-fy2024-snapshot?c=tdg-002")
    assert screen.active() == "report-select"
    screen.go("W-Library/cases")
    assert screen.active() == "analysis"


def test_library_filters_combine_search_sector_content_and_module(fixture: Any) -> None:
    screen = fixture("W-Library/cases")
    assert screen.text("#library-count") == "3 issuers · 8 runs · 7 reports"
    screen.focus("#library-query")
    screen.set_value("#library-query", "  FORD   2024 ")
    assert screen.count(".run-list a") == 1 and screen.text(".case-list h2") == "Ford Otosan"
    assert screen.active() == "library-query"
    screen.set_value('[data-library-filter="sector"]', "Telecommunications", "change")
    assert screen.exists(".library-empty") and screen.count(".run-list a") == 0
    screen.click("#library-clear")
    assert screen.count(".run-list a") == 8 and screen.active() == "library-query"
    screen.set_value('[data-library-filter="content"]', "reports", "change")
    assert screen.text("#library-count") == "1 issuer · 4 runs · 7 reports"
    assert not any("c=tdg-deliveries" in href for href in screen.attrs(".run-list a", "href"))
    screen.set_value('[data-library-filter="module"]', "CP-2G", "change")
    assert screen.count(".run-list a") == 1
    assert "c=tdg-003" in str(screen.attr(".run-list a", "href"))
    screen.set_value('[data-library-filter="content"]', "modules", "change")
    contexts = sorted(context_of(str(href)) or "" for href in screen.attrs(".run-list a", "href"))
    assert contexts == ["ford-otosan-2024", "tdg-003"]


def test_library_return_restores_filters_and_clear_resets_without_changing_context(
    fixture: Any,
) -> None:
    screen = fixture("W-Library/cases")
    screen.set_value("#library-query", "Ford")
    screen.go(str(screen.attr(".run-list a", "href"))[1:])
    assert screen.text(".issuer h1") == "Ford Otosan"
    screen.go("W-Library/cases")
    assert screen.eval("document.getElementById('library-query').value") == "Ford"
    assert screen.count(".run-list a") == 1
    screen.click("#library-clear")
    assert screen.eval("document.getElementById('library-query').value") == ""
    assert screen.count(".run-list a") == 8 and screen.eval("current.context") == "ford-otosan-2024"
    screen.focus("#analysis")
    screen.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true}))")
    assert screen.active() == "library-query"
    prevented = screen.eval(
        "()=>{const e=new Event('submit',{bubbles:true,cancelable:true});"
        "document.getElementById('library-filters').dispatchEvent(e);return e.defaultPrevented;}"
    )
    assert prevented is True


def test_literal_search_text_is_escaped_and_short_ids_include_the_delivery_collection(
    fixture: Any,
) -> None:
    screen = fixture("W-Library/cases")
    screen.set_value("#library-query", "TDG")
    assert screen.count(".run-list a") == 6
    bad = '"><img src=x onerror=alert(1)>'
    screen.set_value("#library-query", bad)
    screen.go("CP-1")
    screen.go("W-Library/cases")
    assert screen.eval("document.getElementById('library-query').value") == bad
    assert not screen.exists("[onerror]") and screen.exists(".library-empty")


def test_workspace_round_trips_do_not_persist_automatically_opened_catalogue_states(
    fixture: Any,
) -> None:
    screen = fixture("CP-2H")
    opened = "document.querySelector('.module-catalogue').open"
    screen.page.wait_for_timeout(20)
    assert screen.eval(opened) is False
    screen.go("W-Reports/unavailable?c=ford-otosan-2024")
    screen.page.wait_for_timeout(20)
    screen.go("CP-2H/s31?c=ford-otosan-2024")
    screen.page.wait_for_timeout(20)
    assert screen.eval(opened) is False
    screen.click(".module-catalogue>summary")
    screen.page.wait_for_timeout(20)
    screen.go("W-Evidence/sources?c=ford-otosan-2024")
    screen.page.wait_for_timeout(20)
    screen.go("CP-2H/s31?c=ford-otosan-2024")
    screen.page.wait_for_timeout(20)
    assert screen.eval(opened) is True


def test_key_a_every_run_lists_exactly_its_saved_outputs_and_inputs(fixture: Any) -> None:
    screen = fixture()
    runs = screen.eval("JSON.parse(JSON.stringify(contexts))")
    assert sorted(runs) == sorted(KEY_A)
    for key, expected in KEY_A.items():
        run = runs[key]
        prefix = len(expected["folder"]) + 1
        assert run["folder"] == expected["folder"]
        outputs = {
            module: sorted(item[prefix:] for item in details["outputs"])
            for module, details in run["modules"].items()
            if details["outputs"]
        }
        assert outputs == {
            module: sorted(files) for module, files in expected["outputs"].items()
        }, key
        inputs = sorted(
            item[prefix:] for details in run["modules"].values() for item in details["inputs"]
        )
        assert inputs == sorted(expected["inputs"]), key
        for file in [
            *(f for files in expected["outputs"].values() for f in files),
            *expected["inputs"],
        ]:
            copied = FIXTURE / "sources" / f"{expected['folder']}--{file}"
            assert sha256(copied) == sha256(ROOT / "runs" / expected["folder"] / file), file


def test_key_b_the_contains_module_filter_returns_every_run_with_an_output(fixture: Any) -> None:
    screen = fixture("W-Library/cases")
    options = screen.eval(
        "[...document.querySelector('[data-library-filter=\"module\"]').options].map(o=>o.value).filter(v=>v!=='all')"
    )
    assert sorted(options) == sorted(KEY_B)
    for module, runs in KEY_B.items():
        screen.set_value('[data-library-filter="module"]', module, "change")
        found = sorted(context_of(str(href)) or "" for href in screen.attrs(".run-list a", "href"))
        assert found == sorted(runs), module


def test_availability_uses_only_the_recorded_labels(fixture: Any) -> None:
    screen = fixture("CP-1?c=tdg-003")
    assert not screen.exists(".missing-state") and "Attempt 2 of 2" in screen.text("#module-head")
    assert screen.eval(
        "[...document.querySelectorAll('#output-select option')].map(o=>o.value)"
    ) == [
        "CP-1-attempt-1.md",
        "CP-1-attempt-2.md",
    ]
    assert screen.eval("document.querySelector('#output-select').value") == "CP-1-attempt-2.md"
    assert screen.count(".bar-column") == 0
    screen.go("CP-1?c=ford-otosan-2024")
    content = screen.content()
    assert "Inputs only" in content and "CP-1-selected-input.md" in content
    assert "Output available" not in content
    screen.go("CP-1?c=tdg-002")
    screen.eval("document.querySelector('.module-catalogue').open=true")
    labels = screen.texts(".module-code>span")
    assert "Output available" in labels and "No output found" in labels
    for label in labels:
        assert label in ("Output available", "Inputs only", "No output found", "Run record"), label
    for route in ["CP-L10?c=tdg-002", "CP-2H?c=tdg-002", "W-Reports/list?c=ford-otosan-2024"]:
        screen.go(route)
        assert not re.search(
            r"No output in this run|is available in this gallery", screen.content()
        ), route


def test_a_module_with_no_output_shows_no_other_case_and_offers_only_the_same_issuer(
    fixture: Any,
) -> None:
    screen = fixture("CP-2H?c=tdg-002")
    assert "No output found" in screen.text("#content .missing-state")
    screen.eval("document.querySelector('#content .visual-plan').remove()")
    combined = (
        screen.content() + " " + screen.text("#module-list") + " " + screen.text("#section-nav")
    )
    assert not re.search(r"dated rating posture|agency divergence|Ford", combined, re.IGNORECASE)
    assert not screen.exists("#next-section") and not screen.exists(".section-outline")
    assert [context_of(str(h)) for h in screen.attrs("#content .available-case a", "href")] == [
        "tdg-003"
    ]
    screen.go("CP-1A?c=ford-otosan-2024")
    assert not screen.exists("#content .available-case a")
    assert "c=tdg-" not in screen.inner_html("#content")


def test_several_unnumbered_outputs_show_a_chooser_and_pick_none(fixture: Any) -> None:
    screen = fixture("CP-2?c=tdg-003")
    assert [t.strip() for t in screen.texts("#content .output-choices a")] == [
        "Integrated",
        "Macro-update",
        "Quality-update",
    ]
    assert screen.eval("current.output") is None
    assert not screen.exists(".finding") and not screen.exists("#next-section")
    screen.go(str(screen.eval("document.querySelector('#content .output-choices a').hash"))[1:])
    assert screen.eval("current.output") == "tdg-003/CP-2-integrated.md"
    assert (
        screen.eval("new URLSearchParams(location.hash.split('?')[1]).get('o')")
        == "CP-2-integrated.md"
    )
    screen.eval("()=>{document.getElementById('next-section').click();renderRoute();}")
    assert screen.eval("current.output") == "tdg-003/CP-2-integrated.md"


def test_curated_views_apply_only_to_the_exact_file_they_were_built_for(fixture: Any) -> None:
    screen = fixture("CP-2?c=tdg-002")
    assert screen.count(".factor") == 6
    assert screen.eval("document.getElementById('output-select').value") == "CP-2-attempt-2.md"
    screen.eval(
        "()=>{const s=document.getElementById('output-select');s.focus();s.value='CP-2-attempt-1.md';"
        "s.dispatchEvent(new Event('change',{bubbles:true}));renderRoute();}"
    )
    assert screen.count(".factor") == 0
    assert screen.eval("current.output") == "tdg-002/CP-2-attempt-1.md"
    assert screen.active() == "output-select"
    assert (
        screen.eval("new URLSearchParams(location.hash.split('?')[1]).get('o')")
        == "CP-2-attempt-1.md"
    )
    screen.go("CP-1?c=tdg-003")
    assert screen.count(".bar-column") == 0


def test_a_render_failure_names_the_new_module_and_shows_an_explicit_gap(fixture: Any) -> None:
    screen = fixture("CP-1")
    screen.eval(
        "()=>{window.__logged=0;console.error=()=>{window.__logged++;};renderContent=()=>{throw new Error('forced')};}"
    )
    screen.go("CP-2G")
    assert "Couldn’t present this output" in screen.content()
    assert screen.count(".bar-column") == 0
    assert "Forward credit model" in screen.text("#module-head")
    assert "CP-2G" in screen.eval("document.title")
    assert "CP-2G" in str(screen.attr("#content a[download]", "href"))
    assert screen.eval("window.__logged") == 1


def test_key_c_reports_trace_to_their_source_files_by_hash(fixture: Any) -> None:
    screen = fixture("W-Reports/list?c=tdg-002")
    reports = screen.eval("JSON.parse(JSON.stringify(window.DESIGN_WORKSPACE.reports))")
    assert len(reports) == 7
    for position, (report_id, label, cp2, cp2_hash, report_hash, status) in enumerate(KEY_C):
        report = reports[position]
        assert (report["id"], report["label"], report["status"]) == (report_id, label, status)
        assert report["sha256"].startswith(report_hash), report_id
        assert sha256(ROOT / "deliverables" / report_id / "report.html") == report["sha256"]
        assert sha256(FIXTURE / "reports" / report_id / "original.html") == report["sha256"]
        source = {row["module"]: row for row in report["builtFrom"]}
        assert source["CP-1"]["source"] == "tdg-002/CP-1-attempt-2.md"
        assert source["CP-1"]["sha256"].startswith("301af0eeed2d")
        assert source["CP-1A"]["source"] == "tdg-002/CP-1A-attempt-3.md"
        assert source["CP-1A"]["sha256"].startswith("6f63963177c2")
        assert source["CP-2"]["source"] == cp2 and source["CP-2"]["sha256"].startswith(cp2_hash), (
            report_id
        )
    for run, builds in REPORTS_BY_RUN.items():
        traced = [
            position + 1
            for position, report in enumerate(reports)
            if any(row["run"] == run for row in report["builtFrom"])
        ]
        assert traced == builds, run
        screen.go(f"W-Reports/list?c={run}")
        built = screen.texts("#content .report-built .report-row a")
        numbers = sorted(int(re.search(r"Build (\d)", text).group(1)) for text in built)  # type: ignore[union-attr]
        assert numbers == builds, run
        if not builds:
            assert (
                "No report was built from this run’s files (checked by SHA-256)" in screen.content()
            ), run
    for route in [
        "W-Reports/list?c=tdg-002",
        "W-Reports/tdg-fy2024-snapshot-3?c=tdg-002",
        "W-Library/cases",
        "W-Overview?c=tdg-002",
        "CP-OS?c=tdg-003",
        "W-Help/help",
    ]:
        screen.go(route)
        assert not re.search(
            r"source-run linkage|No report linked|Revision order unverified|Saved build|tdg-deliveries",
            screen.inner_html("#content"),
        ), route


def test_opening_a_report_keeps_the_run_pinned_and_built_from_reaches_each_source_run(
    fixture: Any,
) -> None:
    screen = fixture("W-Reports/list?c=tdg-002")
    assert screen.text(".issuer .code") == "TDG-002"
    row = screen.eval(
        "[...document.querySelectorAll('.report-row a')].find(a=>a.textContent.includes('Build 3')).hash"
    )
    screen.go(row[1:])
    assert screen.eval("current.context") == "tdg-002" and screen.text(".issuer .code") == "TDG-002"
    assert screen.attr("#report-preview", "src") == "reports/tdg-fy2024-snapshot-3/preview.html"
    links = [str(href) for href in screen.attrs(".built-from a", "href")]
    assert any("c=tdg-003" in href and "o=CP-2-integrated.md" in href for href in links)
    assert any("c=tdg-002" in href for href in links)
    assert not re.search(r"accepted|verified", screen.text(".built-from"), re.IGNORECASE)
    screen.go("W-Reports/tdg-fy2024-snapshot-6?c=tdg-002")
    assert any(
        "c=tdg-peers-2024" in str(href) for href in screen.attrs("#content .built-from a", "href")
    )
    screen.go("W-Reports/list?c=tdg-004")
    assert screen.count("#content .report-other .report-row") == 7
    assert screen.eval("current.context") == "tdg-004"


def handoff_rows(lines: list[str], heading: str) -> list[str]:
    start = lines.index(f"### {heading}")
    rows: list[str] = []
    for position, line in enumerate(lines[start:]):
        if any(earlier.startswith("## ") for earlier in lines[start : start + position]):
            break
        if line.startswith("|"):
            rows.append(line)
    return [row for row in rows[2:] if not re.fullmatch(r"\|[\s:|-]+\|", row)]


def test_cp8_is_the_deliverable_comparison_with_all_retained_rows(fixture: Any) -> None:
    screen = fixture("CP-8")
    assert screen.eval("current.context") == "tdg-run-comparison"
    assert screen.eval("current.output") == PIN["CP-8"]
    assert "Deliverable comparison" in screen.text("#module-head")
    assert screen.eval("document.getElementById('output-select').value") == "CP-8.md"
    text = norm(screen.content())
    lines = (ROOT / "runs" / PIN["CP-8"]).read_text(encoding="utf-8").split("\n")
    sections = handoff_rows(lines, "All five report sections")[:5]
    material = handoff_rows(lines, "Material analytical changes")[:9]
    regressions = handoff_rows(lines, "Unresolved regressions to repair")[:3]
    assert sections[0].startswith("| Key findings") and sections[4].startswith(
        "| Transaction summary"
    )
    assert material[0].startswith("| Annual financial base") and material[8].startswith(
        "| Output scope"
    )
    assert regressions[2].startswith("| RC-3")
    for line in [*sections, *material, *regressions]:
        for cell in line.split("|")[1:-1]:
            assert norm(cell) in text, cell[:60]
    assert screen.texts("#content .change-row .grade") == [
        "Revised",
        "Unchanged",
        "Revised",
        "Unchanged",
        "Unchanged",
    ]
    hrefs = [str(href or "") for href in screen.attrs("#content a", "href")]
    for report_id in ["tdg-fy2024-snapshot-2", "tdg-fy2024-snapshot-6", "tdg-fy2024-snapshot-7"]:
        assert any(
            href.startswith(f"#W-Reports/{report_id}?") and "c=tdg-run-comparison" in href
            for href in hrefs
        ), report_id
    assert "RC-1/2/3 are closed for this delivery revision." in text
    assert (
        "“Current” means the selected latest local report, not current2026 issuer information."
        in text
    )
    grades = screen.texts("#content .regression-row .grade")
    assert len(grades) == 3 and all(grade == "Closed" for grade in grades)
    screen.go("CP-8/gaps")
    assert "Native integration and assurance" in screen.content()
    old = re.compile(r"decision review|attribution|calibration|hit-rate|post-mortem", re.IGNORECASE)
    plan = screen.eval("visualPlan('CP-8')")
    assert not old.search(text) and not old.search(screen.text("#module-head"))
    assert not old.search(screen.text("#module-list")) and not old.search(plan)
    assert screen.page.evaluate("h=>window.__fragment(h,'section').length", plan) == 3
    assert screen.eval("window.DESIGN_WORKSPACE.visuals.length") == 91
    screen.go("CP-8?c=tdg-run-comparison&o=CP-8-recheck.md")
    assert "RC-3 Critical labels" in screen.content() and screen.count("#content .change-row") == 0


def test_every_band_reading_caution_and_note_quotes_its_own_handoff(fixture: Any) -> None:
    allow = [
        "Select a plotted row to inspect its exact source fields.",
        "Missing values have no bar.",
        "Solid: active at the historical base.",
        "Outlined: starts after the base.",
        "“Not Assessable” is an evidence limitation, not an adverse grade.",
    ]
    for legend in allow:
        assert not re.search(r"\d", legend), legend
    screen = fixture()
    files: list[str] = screen.eval(
        "Object.keys(data).filter(id=>id.includes('/')).map(id=>data[id].file)"
    )
    handoffs = {
        name: norm((FIXTURE / "sources" / name).read_text(encoding="utf-8")) for name in files
    }
    result = screen.page.evaluate(
        f"""([handoffs,allow])=>{{const norm={NORM};const failures=[];let bands=0,checked=0;
        for(const id of Object.keys(data).filter(id=>id.includes('/'))){{
          const out=data[id],first=modules[id].first,handoff=handoffs[out.file];let firstBands=0,anyBand=false;
          for(const s of modules[id].sections){{
            const html=renderContent(id,s[0]);const t=document.createElement('template');t.innerHTML=html;
            for(const el of t.content.querySelectorAll('.analysis-call,.chart-reading,.caution,.matrix-note,.downside')){{
              for(const sentence of norm(el.textContent).split(/(?<=[.!?])\\s+/).filter(Boolean)){{
                checked++;if(!(handoff.includes(sentence)||allow.includes(sentence)))failures.push(`${{id}}/${{s[0]}}: ${{sentence}}`);}}}}
            for(const band of t.content.querySelectorAll('.analysis-call')){{
              bands++;anyBand=true;if(s[0]===first)firstBands++;else failures.push(`${{id}}: band outside first view ${{s[0]}}`);
              const source=band.nextElementSibling?.querySelector('[data-evidence]');
              if(!source)failures.push(`${{id}} band has no source action`);
              else if(!evidence.has(source.dataset.evidence))failures.push(`${{id}}: unknown evidence ${{source.dataset.evidence}}`);}}}}
          if(out.call){{if(firstBands!==1)failures.push(`${{id}}: ${{firstBands}} bands on first view`);}}
          else if(anyBand)failures.push(`${{id}}: band without a call`);}}
        return {{failures,bands,checked}};}}""",
        [handoffs, allow],
    )
    assert result["failures"] == []
    assert result["bands"] >= 18 and result["checked"] >= result["bands"]


def test_key_d_provenance_comes_only_from_labels_the_handoff_declares(fixture: Any) -> None:
    screen = fixture()
    for module, line, expected in KEY_D:
        key = json.dumps(f"{PIN[module]}:{line}")
        assert screen.eval(f"classification(evidence.get({key}))") == expected, f"{module}:{line}"
    assert (
        screen.eval(
            "classification({fields:[['Note','Mentions Management Language and Documentary Fact in passing.']]})"
        )
        == "Not classified"
    )
    assert (
        screen.eval("classification({fields:[['Category','Documentary Fact']]})")
        == "Documentary Fact"
    )


def test_navigation_links_keep_module_identity_and_tabs_keep_the_selected_output(
    fixture: Any,
) -> None:
    screen = fixture("CP-1?c=tdg-002")
    href = screen.eval(
        "[...document.querySelectorAll('a.module-item')].find(a=>a.getAttribute('href').startsWith('#CP-1A/')).getAttribute('href')"
    )
    assert href == "#CP-1A/events?c=tdg-002"
    screen.go("CP-OS?c=tdg-002")
    assert screen.attrs(".section-item", "href") == [
        "#CP-OS/activity?c=tdg-002",
        "#CP-OS/delivery?c=tdg-002",
    ]
    section = screen.eval(
        "modules['tdg-003/CP-1-attempt-1.md'].sections.map(s=>s[0]).find(id=>!modules['tdg-003/CP-1-attempt-2.md']"
        ".sections.some(s=>s[0]===id))"
    )
    assert section
    screen.go(f"CP-1/{section}?c=tdg-003&o=CP-1-attempt-1.md")
    screen.go("W-Evidence/sources?c=tdg-003")
    modules_href = screen.eval(
        "[...document.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent==='Modules').getAttribute('href')"
    )
    assert modules_href.startswith(f"#CP-1/{section}?") and "o=CP-1-attempt-1.md" in modules_href


def test_run_periods_and_bounded_case_limits_stay_accurate_outside_the_pinned_output(
    fixture: Any,
) -> None:
    screen = fixture("CP-0?c=ford-otosan-2024")
    scope = screen.text(".scope")
    assert "agency publications" not in scope and "11 April 2024" in scope
    screen.go("W-Evidence/sources?c=frontier-2020")
    assert "Bounded recovery consumer · not full security selection" in screen.content()
    screen.go("W-Evidence/sources?c=ford-otosan-2024")
    assert "Bounded funding-plan consumer · not full refinancing / LME" in screen.content()


def test_the_slash_key_opens_search_unless_typing_or_modified(fixture: Any) -> None:
    screen = fixture("CP-1/performance?c=tdg-002")
    assert screen.attr("#module-search", "placeholder") == "Find a module, figure or source"
    assert screen.attr("#module-search", "aria-keyshortcuts") == "/"
    assert screen.text(".search kbd") == "/" and screen.attr(".search kbd", "aria-hidden") == "true"
    screen.focus("#analysis")
    for modifier in ["metaKey", "ctrlKey", "altKey"]:
        assert screen.press("#analysis", "/", **{modifier: True}) is False, modifier
        assert screen.active() == "analysis", modifier
    assert screen.press("#analysis", "/") is True and screen.active() == "module-search"
    assert screen.eval("document.getElementById('navigator').classList.contains('mobile-open')")
    assert screen.attr("#module-toggle", "aria-expanded") == "true"
    assert screen.press("#module-search", "/") is False
    screen.focus("#analysis")
    assert screen.exists('.rail button[aria-label="Search (/)"]')
    screen.click('.rail button[aria-label="Search (/)"]')
    assert screen.active() == "module-search"
    screen.go("W-Library/cases")
    screen.click('.rail button[aria-label="Search (/)"]')
    assert screen.active() == "library-query"


def test_escape_steps_back_one_layer_at_a_time(fixture: Any) -> None:
    # Narrow: the module toggle that takes focus back is only shown on a narrow screen.
    screen = fixture("CP-1/performance?c=tdg-002", viewport=(640, 800))
    screen.press("#analysis", "/")
    screen.set_value("#module-search", "net sales")
    assert screen.exists("#search-results a.search-hit")
    screen.press("#module-search", "Escape")
    assert screen.eval("document.getElementById('module-search').value") == ""
    assert screen.eval("document.getElementById('search-results').children.length") == 0
    assert screen.active() == "module-search"
    assert screen.eval("document.getElementById('navigator').classList.contains('mobile-open')")
    screen.press("#module-search", "Escape")
    assert not screen.eval("document.getElementById('navigator').classList.contains('mobile-open')")
    assert screen.active() == "module-toggle"
    assert screen.attr("#module-toggle", "aria-expanded") == "false"
    screen.go("W-Library/cases")
    screen.focus("#library-query")
    screen.set_value("#library-query", "zzz")
    assert re.search(r"No matching issuers or runs", screen.content())
    screen.press("#library-query", "Escape")
    assert screen.eval("document.getElementById('library-query').value") == ""
    assert not re.search(r"No matching issuers or runs", screen.content())


def test_arrow_keys_walk_chart_marks_without_wrapping(fixture: Any) -> None:
    screen = fixture("CP-1/performance?c=tdg-002")
    bars = ".bars .bar-column"
    assert screen.count(bars) == 3
    screen.eval(f"document.querySelectorAll('{bars}')[0].focus()")
    active = f"[...document.querySelectorAll('{bars}')].indexOf(document.activeElement)"
    assert screen.press("", "ArrowRight") is True and screen.eval(active) == 1
    screen.press("", "ArrowDown")
    assert screen.eval(active) == 2
    assert screen.press("", "ArrowRight") is False and screen.eval(active) == 2
    screen.press("", "ArrowLeft")
    assert screen.eval(active) == 1
    screen.press("", "ArrowUp")
    assert screen.eval(active) == 0
    assert screen.press("", "ArrowRight", altKey=True) is False and screen.eval(active) == 0
    screen.focus("#content .source-link")
    assert screen.press("", "ArrowDown") is False
    result = screen.page.evaluate(
        """()=>{const containers='.bars,.mix-bars,.horizontal-chart,.hedge-chart,.vector-chart';
        const seen=new Set(),failures=[];
        const press=(t,k)=>{const e=new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true});t.dispatchEvent(e);};
        for(const id of Object.values(pins))for(const section of modules[id].sections.map(s=>s[0])){
          const module=id.split('/')[1].match(/CP-[A-Z0-9]+/)[0],context=data[id].run;
          location.hash=`${module}/${section}?c=${context}`;renderRoute();const content=document.getElementById('content');
          for(const mark of content.querySelectorAll('.bar-column,.chart-row,.hedge-row,.plot-point,.mix-bars button'))
            if(!mark.closest(containers))failures.push(`${id}/${section}: ${mark.className}`);
          for(const chart of content.querySelectorAll(containers)){
            seen.add(chart.className.baseVal??chart.className.split(' ')[0]);
            const marks=[...chart.querySelectorAll('[data-evidence]')];if(marks.length<2)continue;
            marks[0].focus();press(marks[0],'ArrowRight');
            if(document.activeElement!==marks[1])failures.push(`${id}/${section}: arrow did not move`);}}
        return {seen:[...seen].sort(),failures};}"""
    )
    assert result["failures"] == []
    assert result["seen"] == ["bars", "hedge-chart", "horizontal-chart", "mix-bars", "vector-chart"]


def follow(screen: Screen, href: str) -> None:
    """Open a search hit the way a reader does: its click handler runs, then the route renders."""
    screen.page.evaluate(
        "href=>{const a=[...document.querySelectorAll('a.search-hit')].find(a=>a.getAttribute('href')===href);"
        "a.click();location.hash=href;renderRoute();}",
        href,
    )


def test_search_finds_figures_and_sources_of_this_run_and_opens_them(fixture: Any) -> None:
    screen = fixture("CP-2?c=tdg-002")
    assert screen.attr("#search-results", "aria-live") == "polite"
    screen.set_value("#module-search", "source-supported dashboard")
    groups = search_groups(screen)
    assert groups[0]["title"] == "Figures"
    assert groups[0]["hits"][0]["href"] == "#CP-1/performance?c=tdg-002"
    assert (
        groups[0]["hits"][0]["label"]
        == "Figure: CP-1 · Attempt 2 of 2 T4.10 — Source-supported dashboard"
    )
    assert "o=CP-1-attempt-1.md" in groups[0]["hits"][1]["href"]
    screen.go(groups[0]["hits"][0]["href"][1:])
    assert "7,940" in screen.content()
    screen.set_value("#module-search", "Quarterly comparison")
    assert search_groups(screen) == [], "visual of another run"
    screen.set_value("#module-search", "Pretax continuing income")
    sources = next(g for g in search_groups(screen) if g["title"].startswith("Sources"))
    row = next(h for h in sources["hits"] if "CP-1-attempt-2.md%3A249" in h["href"])
    assert row["href"].startswith("#CP-1/performance?c=tdg-002&e="), row["href"]
    follow(screen, row["href"])
    assert screen.hidden("inspector") is False
    inspector = screen.text("#inspector")
    for exact in ["Pretax continuing income", "2,215", "1,716", "1,127", "Reported, PDF 106"]:
        assert exact in inspector, exact
    assert screen.active() == "back-analysis"
    screen.eval(
        "()=>{document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,"
        "cancelable:true}));renderRoute();}"
    )
    assert screen.hidden("inspector") is True and screen.active() == "module-search"
    assert (
        screen.eval("document.getElementById('module-search').value") == "Pretax continuing income"
    )
    screen.set_value("#module-search", "CP-1-attempt-1.md")
    file_hit = search_groups(screen)[0]["hits"][0]
    assert file_hit["href"].startswith("#CP-1/") and file_hit["href"].endswith(
        "?c=tdg-002&o=CP-1-attempt-1.md"
    )
    follow(screen, file_hit["href"])
    assert screen.eval("document.getElementById('output-select').value") == "CP-1-attempt-1.md"
    screen.set_value("#module-search", "CP-1-instructions.md")
    assert search_groups(screen) == [], "instructions are not shown"
    screen.set_value("#module-search", "PDF 106")
    sources = next(g for g in search_groups(screen) if g["title"].startswith("Sources"))
    assert re.fullmatch(r"Sources · 4 of \d+", sources["title"]) and len(sources["hits"]) == 4
    assert int(sources["title"].split(" of ")[1]) > 4
    screen.set_value("#module-search", "Otosan")
    assert search_groups(screen) == [], "another issuer"
    screen.set_value("#module-search", "&")
    for group in search_groups(screen):
        for hit in group["hits"]:
            assert "&amp;" not in hit["text"], hit["text"]
    screen.set_value("#module-search", "no output found")
    assert any("CP-2H" in text for text in screen.texts(".module-item")), "status word"
    screen.go("CP-1?c=ford-otosan-2024")
    screen.set_value("#module-search", "Source-supported dashboard")
    assert search_groups(screen) == [], "another run"
    screen.set_value("#module-search", "CP-1-selected-input.md")
    assert search_groups(screen)[0]["hits"][0]["href"] == "#W-Evidence/sources?c=ford-otosan-2024"
    screen.go("CP-1?c=tdg-003")
    screen.set_value("#module-search", "net sales")
    sources = next(g for g in search_groups(screen) if g["title"].startswith("Sources"))
    assert any(
        h["label"] == "Reference: CP-1 · Attempt 2 of 2 3 · NET SALES" for h in sources["hits"]
    )
    screen.go("CP-1B?c=tdg-003")
    screen.set_value("#module-search", "Quarterly comparison")
    plotted = search_groups(screen)[0]["hits"][0]
    assert (
        plotted["label"].startswith("Figure: CP-1B") and "Quarterly comparison" in plotted["text"]
    )
    screen.go(plotted["href"][1:])
    assert screen.exists("#content #module-visual")
    for context in screen.eval("Object.keys(contexts)"):
        screen.go(f"W-Evidence/sources?c={context}")
        for text in ["t", "a", ".md"]:
            screen.set_value("#module-search", text)
            for href in screen.attrs("a.search-hit", "href"):
                assert "undefined" not in str(href), f"{context} {href}"


def test_chart_labels_and_basis_text_come_from_the_retained_handoff(fixture: Any) -> None:
    screen = fixture("CP-1/performance?c=tdg-002")
    assert screen.text(".chart-head span") == "USD millions · Reported, PDF 106"
    assert "USD millions" in str(screen.attr(".bar-column", "aria-label"))
    screen.eval("()=>{document.querySelector('.bar-column').click();renderRoute();}")
    basis = screen.text("#inspector .evidence-basis")
    assert "Monetary unit USD millions; statement parentheses retained as negative" in basis, basis
    assert "period-end balances" not in basis, basis
    screen.go("CP-1A/business?c=tdg-002")
    assert screen.text("#content .section-heading span") == "FY2024 · approximate"


def test_the_rail_reaches_every_destination_marks_where_you_are_and_keeps_the_run(
    fixture: Any,
) -> None:
    screen = fixture("CP-2H?c=ford-otosan-2024")
    for label in [
        "Issuer library",
        "Research workspace",
        "Deliverables",
        "Run activity",
        "New run",
        "Settings",
        "Help",
    ]:
        assert screen.exists(f'.rail a[aria-label="{label}"]'), label
    assert (
        screen.attr('.rail a[aria-label="Deliverables"]', "href")
        == "#W-Reports/list?c=ford-otosan-2024"
    )
    assert (
        screen.attr('.rail a[aria-label="Run activity"]', "href")
        == "#CP-OS/activity?c=ford-otosan-2024"
    )
    assert screen.attr('.rail a[aria-label="Research workspace"]', "aria-current") == "page"
    for route, label in [
        ("W-Library/cases", "Issuer library"),
        ("W-NewRun/run", "New run"),
        ("W-Settings/workspace", "Settings"),
        ("W-Help/help", "Help"),
        ("W-Reports/list", "Deliverables"),
        ("CP-OS/activity", "Run activity"),
    ]:
        screen.go(route)
        assert screen.attrs(".rail a[aria-current]", "aria-label") == [label], route


def test_no_destination_still_calls_itself_a_gallery_or_a_prototype(fixture: Any) -> None:
    screen = fixture("W-Library/cases")
    for route in [
        "W-Library/cases",
        "W-Overview/overview?c=tdg-002",
        "W-Reports/list?c=tdg-002",
        "W-Evidence/sources?c=tdg-002",
        "CP-OS/activity?c=tdg-002",
        "CP-MODEL/publication?c=tdg-002",
        "W-NewRun/run",
        "W-Settings/workspace",
        "W-Help/help",
        "CP-1/audit?c=tdg-002",
    ]:
        screen.go(route)
        combined = screen.text("body") + screen.eval("document.title")
        assert not re.search(
            r"screen.design|prototype|gallery|working app", combined, re.IGNORECASE
        ), route
