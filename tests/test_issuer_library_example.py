"""The static Issuer Library example page in a real browser; no network, server or provider.

Marked browser: real browser proof of the generated page, not a layout acceptance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest
from issuer_library_browser import ROOT, pageerrors

pytestmark = pytest.mark.browser

EXAMPLE = ROOT / "examples/issuer-library"
ROWS = [
    {
        "id": "missing",
        "name": "Zeta",
        "issuer": "Z",
        "sector": "Energy",
        "workflow": "Legal",
        "date": "2024-01-01",
        "period_kind": "Actual",
        "completion": None,
        "artifacts": [],
        "metrics": {"leverage": None, "coverage": None},
    },
    {
        "id": "zero",
        "name": "Alpha",
        "issuer": "A",
        "sector": "Energy",
        "workflow": "Credit",
        "date": "2024-02-01",
        "period_kind": "Actual",
        "completion": 0,
        "artifacts": [],
        "metrics": {"leverage": {"value": "0", "basis": "Gross"}, "coverage": {"value": "0"}},
    },
    {
        "id": "gross",
        "name": "Beta",
        "issuer": "B",
        "sector": "Auto",
        "workflow": "Credit",
        "date": "2023-01-01",
        "period_kind": "Actual",
        "completion": 75,
        "artifacts": [{"available": True, "state": "candidate"}],
        "metrics": {"leverage": {"value": "5.96", "basis": "Gross"}, "coverage": {"value": "3.60"}},
    },
    {
        "id": "net",
        "name": "Gamma",
        "issuer": "G",
        "sector": "Auto",
        "workflow": "Credit",
        "date": "2022-01-01",
        "period_kind": "Forecast",
        "completion": 100,
        "artifacts": [],
        "metrics": {"leverage": {"value": "2.2", "basis": "Net"}, "coverage": {"value": "4.5"}},
    },
]


@pytest.fixture
def logic(browser: Any) -> Any:
    """The pure screening operations, loaded alone on a blank page."""
    page = browser.new_context().new_page()
    page.add_script_tag(path=str(EXAMPLE / "logic.js"))
    page.evaluate("rows=>{window.rows=rows;}", ROWS)
    yield page
    page.context.close()


def ids(page: Any, expression: str) -> list[str]:
    values: list[str] = page.evaluate(f"Array.from({expression},r=>r.id)")
    return values


def test_missing_values_never_become_zero(logic: Any) -> None:
    assert logic.evaluate("LibraryLogic.numberOf(null)") is None
    assert logic.evaluate("LibraryLogic.numberOf({value:''})") is None
    assert logic.evaluate("LibraryLogic.numberOf({value:'NaN'})") is None
    assert logic.evaluate("LibraryLogic.numberOf({value:'0'})") == 0
    assert ids(logic, "LibraryLogic.filterRuns(rows,{leverageMax:'0'})") == ["zero"]


def test_combined_filters_retain_basis_and_period_identity(logic: Any) -> None:
    filters = "{sector:'Auto',basis:'Gross',leverageMin:'4',coverageMin:'3',period:'Actual'}"
    assert ids(logic, f"LibraryLogic.filterRuns(rows,{filters})") == ["gross"]
    assert (
        logic.evaluate(
            "LibraryLogic.filterRuns(rows,{sector:'Auto',basis:'Net',leverageMin:'4'}).length"
        )
        == 0
    )


def test_unknown_completeness_zero_score_and_invalid_threshold_stay_distinct(logic: Any) -> None:
    assert ids(logic, "LibraryLogic.filterRuns(rows,{completion:'unassessed'})") == ["missing"]
    assert ids(logic, "LibraryLogic.filterRuns(rows,{completion:'75'})") == ["gross", "net"]
    assert logic.evaluate("LibraryLogic.filterRuns(rows,{leverageMin:'bad'}).length") == 0


def test_numeric_sort_keeps_missing_last_in_both_directions_without_mutating_input(
    logic: Any,
) -> None:
    assert ids(logic, "LibraryLogic.sortRuns(rows,'leverage','asc')") == [
        "zero",
        "net",
        "gross",
        "missing",
    ]
    assert ids(logic, "LibraryLogic.sortRuns(rows,'leverage','desc')") == [
        "gross",
        "net",
        "zero",
        "missing",
    ]
    assert logic.evaluate("rows[0].id") == "missing"


def test_search_and_report_availability_are_conjunctive(logic: Any) -> None:
    assert (
        logic.evaluate("LibraryLogic.filterRuns(rows,{search:'beta',availability:'report'}).length")
        == 1
    )
    assert (
        logic.evaluate(
            "LibraryLogic.filterRuns(rows,{search:'alpha',availability:'report'}).length"
        )
        == 0
    )


class Example:
    """The generated index.html opened from the repository folder, as a reader would."""

    def __init__(self, browser: Any) -> None:
        self.page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
        self.errors = pageerrors(self.page)
        self.page.goto((EXAMPLE / "index.html").as_uri())
        self.page.wait_for_selector("#run-rows tr")

    def set(self, element_id: str, value: str) -> None:
        self.page.evaluate(
            "([i,v])=>{const el=document.getElementById(i);el.value=v;"
            "el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));}",
            [element_id, value],
        )

    def click(self, element_id: str) -> None:
        self.page.evaluate("i=>document.getElementById(i).click()", element_id)

    def rows(self) -> list[str]:
        values: list[str] = self.page.evaluate(
            "[...document.querySelectorAll('#run-rows tr')].map(r=>r.textContent)"
        )
        return values

    def text(self, element_id: str) -> str:
        value: str = self.page.evaluate("i=>document.getElementById(i).textContent", element_id)
        return value

    def hidden(self, element_id: str) -> bool:
        value: bool = self.page.evaluate("i=>document.getElementById(i).hidden", element_id)
        return value

    def close(self) -> None:
        assert self.errors == []
        self.page.context.close()


@pytest.fixture
def example(browser: Any) -> Any:
    opened = Example(browser)
    yield opened
    opened.close()


def local_target(href: str) -> Path:
    return (EXAMPLE / unquote(href)).resolve()


def test_initial_real_dataset_has_seven_runs_and_correct_selected_source_values(
    example: Example,
) -> None:
    assert len(example.rows()) == 7
    detail = example.text("run-detail")
    assert (
        re.search(r"5.96×", detail) and re.search(r"3.60×", detail) and re.search(r"1,880", detail)
    )
    assert re.search(r"Workflow completeness · Not assessed", detail)
    assert (
        example.page.evaluate("document.querySelectorAll('#run-rows .progress-fill').length") == 0
    )


def test_combining_sector_basis_and_leverage_selects_only_the_annual_tdg_run(
    example: Example,
) -> None:
    example.set("sector", "Aerospace & defense")
    example.set("basis", "Total carrying debt / EBITDA As Defined")
    example.set("leverageMin", "5")
    rows = example.rows()
    assert len(rows) == 1 and re.search(r"Annual credit review", rows[0])
    assert re.search(r"2 active", example.text("metric-filter-count"))


def test_unassessed_real_completeness_is_not_treated_as_a_high_score(example: Example) -> None:
    example.set("completion", "75")
    assert example.rows() == [] and example.hidden("empty-state") is False
    assert example.hidden("run-detail") is True
    example.click("empty-reset")
    assert len(example.rows()) == 7


def test_fictional_dataset_stays_separated_and_completion_filters_work(example: Example) -> None:
    example.click("demo-data")
    assert len(example.rows()) == 6
    assert re.search(r"Fictional examples", example.text("dataset-note"))
    example.set("completion", "75")
    assert len(example.rows()) == 3
    assert example.page.evaluate("document.querySelectorAll('#run-rows a').length") == 0
    example.click("real-data")
    assert len(example.rows()) == 7
    assert example.page.evaluate("document.getElementById('completion').value") == ""


def test_report_only_view_includes_direct_and_explicitly_related_annual_reports(
    example: Example,
) -> None:
    example.click("reports-only")
    rows = example.rows()
    assert len(rows) == 2 and re.search(r"Related report", rows[1])
    anchors: list[dict[str, str]] = example.page.evaluate(
        "[...document.querySelectorAll('#run-rows a')].map(a=>({href:a.getAttribute('href'),target:a.target,rel:a.rel}))"
    )
    for anchor in anchors:
        assert local_target(anchor["href"]).exists(), anchor["href"]
        assert (anchor["target"], anchor["rel"]) == ("_blank", "noopener")


def test_source_details_preserve_an_exact_quoted_row_and_a_working_local_target(
    example: Example,
) -> None:
    example.page.evaluate("document.querySelector('.metric-item .source-link').click()")
    assert example.page.evaluate("document.getElementById('metric-sources').open") is True
    assert re.search(
        r"Net sales \| 7,940", example.page.evaluate("document.activeElement.textContent")
    )
    href = example.page.evaluate("document.activeElement.querySelector('a').getAttribute('href')")
    assert local_target(href).exists()


def test_keyboard_shortcut_selected_detail_focus_and_sort_state_work(example: Example) -> None:
    example.page.evaluate(
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true}))"
    )
    assert example.page.evaluate("document.activeElement.id") == "search"
    example.page.evaluate("document.querySelector('[data-sort=\"leverage\"] button').click()")
    assert (
        example.page.evaluate(
            "document.querySelector('[data-sort=\"leverage\"]').getAttribute('aria-sort')"
        )
        == "ascending"
    )
    assert re.search(r"Ford Otosan", example.rows()[0])
    example.page.evaluate("document.querySelector('#run-rows tr button').click()")
    assert example.page.evaluate("document.activeElement.id") == "run-detail"
    assert re.search(r"TRY m", example.text("run-detail"))


def test_template_has_no_unresolved_tokens_duplicate_ids_or_unlabeled_filters(
    example: Example,
) -> None:
    html = (EXAMPLE / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"/\*(DATA|APP|LOGIC|STYLE|FONTS)\*/", html)
    identifiers: list[str] = example.page.evaluate(
        "[...document.querySelectorAll('[id]')].map(x=>x.id)"
    )
    assert len(identifiers) == len(set(identifiers))
    unlabeled: list[str] = example.page.evaluate(
        "[...document.querySelectorAll('input,select')].filter(c=>!c.labels.length).map(c=>c.id)"
    )
    assert unlabeled == []
    assert (
        example.page.evaluate(
            'document.querySelectorAll(\'script[src],link[rel="stylesheet"],img[src^="http"]\').length'
        )
        == 0
    )


def test_all_seven_run_detail_views_retain_existing_local_evidence_and_delivery_links(
    example: Example,
) -> None:
    labels: list[str] = example.page.evaluate(
        "[...document.querySelectorAll('#run-rows .issuer-title')].map(el=>el.getAttribute('aria-label'))"
    )
    links = 0
    for label in labels:
        example.page.evaluate(
            "label=>[...document.querySelectorAll('#run-rows .issuer-title')].find(el=>el.getAttribute('aria-label')===label).click()",
            label,
        )
        for href in example.page.evaluate(
            "[...document.querySelectorAll('#run-detail a')].map(a=>a.getAttribute('href'))"
        ):
            target = local_target(href)
            assert target.is_relative_to(ROOT), href
            assert target.exists(), href
            links += 1
    assert links >= 30
