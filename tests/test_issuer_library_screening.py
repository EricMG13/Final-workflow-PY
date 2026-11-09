"""Library screening operations: screening.test.cjs at final-workflow dd3dfa18.

The Node suite evaluated screening.js in a bare vm context. Here the real page loads it
and its LibraryLogic global is called with the same synthetic rows.
Marked browser: real browser proof.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from issuer_library_browser import Screen, open_app

pytestmark = pytest.mark.browser


def run(
    run_id: str,
    name: str,
    issuer: str,
    sector: str,
    workflow: str,
    date: str,
    period_kind: str,
    completion: int | None,
    artifacts: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": run_id,
        "name": name,
        "issuer": issuer,
        "sector": sector,
        "workflow": workflow,
        "date": date,
        "period_kind": period_kind,
        "completion": completion,
        "artifacts": artifacts,
        "metrics": metrics,
    }


ROWS = [
    run("missing", "Zeta", "Z", "Energy", "Legal", "2024-01-01", "Actual", None, [],
        {"leverage": None, "coverage": None}),
    run("zero", "Alpha", "A", "Energy", "Credit", "2024-02-01", "Actual", 0, [],
        {"leverage": {"value": "0", "basis": "Gross"}, "coverage": {"value": "0"}}),
    run("gross", "Beta", "B", "Auto", "Credit", "2023-01-01", "Actual", 75,
        [{"available": True, "state": "candidate"}],
        {"leverage": {"value": "5.96", "basis": "Gross"}, "coverage": {"value": "3.60"}}),
    run("net", "Gamma", "G", "Auto", "Credit", "2022-01-01", "Forecast", 100, [],
        {"leverage": {"value": "2.2", "basis": "Net"}, "coverage": {"value": "4.5"}}),
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
