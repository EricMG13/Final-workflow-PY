"""Chart renderers escape handoff values and output ids: escape-sinks.test.cjs at dd3dfa18.

The Node suite lifted functions into a bare vm context. Here a synthetic workspace holding the
hostile values is served to the real page, and its own globals (trendChart, comparisonChart,
routeHref, parseRoute) are called on it. A real browser percent-encodes location.hash, so routes
are set with history.replaceState and read by the page's own parseRoute. Synthetic markup only.
Marked browser: real browser proof.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import pytest
from issuer_library_browser import WEB, open_app

pytestmark = pytest.mark.browser

MARK = "<img src=q onerror=1>"
ENTITY = "&lt;5"
CHART_ID = 'x"><b>'
ROW_ID = 'shared-run/CP-1"><img src=x onerror=1>.md'
CELLS_ID = "r/CP-1.md"
NOT_NUMBERS = ["5", "Not supplied: reported in EUR m", "Not supplied:", "", "(5.0%)"]
NOT_NUMBERS += ["<b>x</b> & y", "—"]
REPORT_IDS = [
    'r"><img src=q onerror=1>',
    "TDG report 2024",
    "a?b#c&d'",
    "100% build",
    "list",
    "a/b",
    "a%2Fb",
    "a?c=1",
    "../..",
    "%E0%A4%A",
]


def section(
    heading: str, headers: list[str], rows: list[list[str]], line: int, row_line: int
) -> dict[str, Any]:
    table = {
        "type": "table",
        "line": line,
        "headers": headers,
        "rows": [{"line": row_line, "cells": cells} for cells in rows],
    }
    return {"heading": heading, "level": 2, "line": line - 1, "blocks": [table]}


def output(output_id: str, sha: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": output_id,
        "run": "acme-001",
        "module": "CP-1",
        "source": output_id,
        "file": output_id.replace("/", "--"),
        "href": "/files/none",
        "label": "CP-1",
        "sha256": sha * 64,
        "case": "Acme · ACME-001",
        "period": "FY2024",
        "scope": "Retained module output",
        "firstHeading": None,
        "basis": {"unit": "USD m"},
        "sections": sections,
    }


def report(report_id: str) -> dict[str, Any]:
    return {
        "id": report_id,
        "build": None,
        "label": "Acme · as of 2024-12-31",
        "status": None,
        "issuer": "Acme",
        "sha256": "r",
        "scope": "s",
        "modelPublished": False,
        "href": "/files/none",
        "download": "/files/none",
        "files": [],
        "builtFrom": [
            {"module": "CP-1", "sha256": "a" * 64, "run": "acme-001", "source": "x", "output": True}
        ],
    }


def store() -> dict[str, Any]:
    chart = [
        section(
            "T4.10 Net sales",
            ["", f"{MARK}A", f"{MARK}B", ENTITY, ""],
            [["Net sales", f"{MARK}1", "2", ENTITY, "note"]],
            5,
            7,
        )
    ]
    row = [section("Findings", ["Item", "Value"], [["Revenue", "5"]], 1, 9)]
    header = ["Item", *(f"c{i}" for i in range(len(NOT_NUMBERS))), "c7"]
    cells = [section("Findings", header, [["Revenue", *NOT_NUMBERS]], 1, 3)]
    outputs = {
        CHART_ID: output(CHART_ID, "a", chart),
        ROW_ID: output(ROW_ID, "b", row),
        CELLS_ID: output(CELLS_ID, "c", cells),
    }
    run = {
        "folder": "acme-001",
        "issuer": "Acme",
        "title": "Acme",
        "run": "ACME-001",
        "sector": "Industrials",
        "period": "FY2024",
        "first": "CP-1",
        "modules": {},
    }
    return {
        "runs": {"acme-001": run},
        "outputs": outputs,
        "handoffs": {out["sha256"]: out["sections"] for out in outputs.values()},
        "inputs": {},
        "pins": {},
    }


@pytest.fixture
def page(browser: Any) -> Iterator[Any]:
    screen = open_app(
        browser,
        "W-Library/cases",
        store(),
        {"reports": [report(i) for i in REPORT_IDS], "models": [], "visuals": []},
    )
    yield screen.page
    assert screen.errors == []
    screen.close()


def test_the_pinned_cp_1_bar_chart_escapes_the_cell_value_the_period_label_and_the_evidence_key(
    page: Any,
) -> None:
    html: str = page.evaluate("id=>trendChart(id,'Net sales')", CHART_ID)
    # The source footer's own icon is the one <img> the page draws, not the injected one.
    assert "<img src=q" not in html, html
    assert re.findall(r"<img[^>]*>", html) == ['<img src="icons/file-text.svg" alt="">']
    assert '"><b>' not in html, html
    assert re.search(r'<span class="bar-value">&amp;lt;5</span>', html)
    assert re.search(r'<span class="bar-period">&amp;lt;5</span>', html)


def test_a_chart_row_built_on_an_output_id_with_markup_in_its_file_name_stays_one_attribute(
    page: Any,
) -> None:
    html: str = page.evaluate(
        "id=>comparisonChart(id,{kind:'bars',title:'T',table:1,column:1})", ROW_ID
    )
    assert "<img" not in html, html
    assert re.search(
        r'data-evidence="shared-run/CP-1&quot;&gt;&lt;img src=x onerror=1&gt;\.md:9"', html
    )


def test_no_web_script_writes_an_evidence_key_into_an_attribute_without_escaping_it() -> None:
    for name in ("screen.js", "views.js", "actions.js"):
        text = (WEB / name).read_text(encoding="utf-8")
        raw = re.findall(r'data-evidence="\$\{(?!esc\()', text)
        assert len(raw) == 0, f"{name} has {len(raw)} unescaped data-evidence"


def route(page: Any, section_id: str, as_typed: str | None = None) -> dict[str, Any]:
    """The href routeHref builds for a report id, and what parseRoute reads back from it after
    the browser has stored it in location.hash (or from the hash exactly as typed)."""
    value: dict[str, Any] = page.evaluate(
        """([id,typed])=>{
          const href=typed??routeHref('W-Reports',id,null,'acme-001');
          history.replaceState(null,'',href);
          const parsed=parseRoute();
          return {href,module:parsed.module,section:parsed.section};
        }""",
        [section_id, as_typed],
    )
    return value


def test_a_report_id_from_a_folder_name_stays_inside_its_href_and_routes_back_to_the_same_report(
    page: Any,
) -> None:
    cases = {
        'r"><img src=q onerror=1>': (
            "#W-Reports/r%22%3E%3Cimg%20src%3Dq%20onerror%3D1%3E?c=acme-001"
        ),
        "TDG report 2024": "#W-Reports/TDG%20report%202024?c=acme-001",
        "a?b#c&d'": "#W-Reports/a%3Fb%23c%26d'?c=acme-001",
        "100% build": "#W-Reports/100%25%20build?c=acme-001",
    }
    for report_id, expected in cases.items():
        found = route(page, report_id)
        assert found["href"] == expected
        assert not re.search(r'["<>&]', found["href"]), found["href"]
        assert (found["module"], found["section"]) == ("W-Reports", report_id)


def test_a_hand_typed_malformed_section_escape_names_no_section_and_is_not_thrown(
    page: Any,
) -> None:
    default = route(page, "list")
    found = route(page, "", "#W-Reports/%E0%A4%A")
    assert (found["module"], found["section"]) == ("W-Reports", default["section"])
    assert found["section"] == "list"
    assert "%E0%A4%A" in [r["id"] for r in page.evaluate("DESIGN_WORKSPACE.reports")]


def test_a_chart_cell_that_is_not_a_number_shows_its_retained_text_escaped_and_draws_no_bar(
    page: Any,
) -> None:
    html: str = page.evaluate(
        "id=>comparisonChart(id,{kind:'bars',title:'T',table:1,columns:[1,2,3,4,5,6,7,8]})",
        CELLS_ID,
    )
    shown = re.findall(r"<strong>(.*?)</strong>", html)
    assert shown == [
        "5",
        "Not supplied: reported in EUR m",
        "Not supplied:",
        "Not available",
        "(5.0%)",
        "&lt;b&gt;x&lt;/b&gt; &amp; y",
        "Not available",
        "Not available",
    ]
    tracks = re.findall(r'<span class="track ([^"]*)">', html)
    assert tracks == [
        "",
        "missing",
        "missing",
        "missing",
        "missing",
        "missing",
        "missing",
        "missing",
    ]
    assert re.search(r'<i class="series-0" style="width:100%">', html)


def test_an_escaped_slash_a_doubled_escape_or_a_path_like_id_cannot_make_a_second_route_segment(
    page: Any,
) -> None:
    def parse(hash_route: str) -> tuple[str, str]:
        found = route(page, "", hash_route)
        return found["module"], found["section"]

    assert parse("#W-Reports/a%2Fb") == ("W-Reports", "a/b")
    assert parse("#W-Reports/a%252Fb") == ("W-Reports", "a%2Fb")
    assert parse("#W-Reports%2Flist") == ("W-Library", "cases")
    assert parse("#W-Reports/a%3Fc=1") == ("W-Reports", "a?c=1")
    assert parse("#W-Reports/..%2F..") == ("W-Reports", "../..")
