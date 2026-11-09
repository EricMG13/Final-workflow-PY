"""Statement rows of HTML line sources (CP1H-R18 rows, T13).

`cases/statement-rows/*.json` is the frozen answer key: per statement unit of each golden HTML
filing, the rows DVII's extractor reads on a td/th-marked re-conversion (`line`, the row's own
`label`, `raw_values`). The key holds no headers. It is read, never written, here.
"""

import hashlib
import json
from decimal import Decimal
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from test_line_locators import FIN, make_pack

from deploy_vii.contracts import Span
from deploy_vii.live.tools import ToolError
from deploy_vii.preparation import PreparedPack
from deploy_vii.source_context import SourceContextReview
from deploy_workflow import financial_workflow as fw
from deploy_workflow.html_text import convert_html
from deploy_workflow.statement_lines import LineTools, line_table, respace, seen_tables
from deploy_workflow.tools.source import SourceTools

REPO = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
KEYS = sorted((REPO / "cases" / "statement-rows").glob("*.json"))
UNITS = 36
ROWS = 1130
SHC_10Q = "SHC_2025-06-30_10-Q_0001822479-25-000044_shc-20250630"
NATL_10Q = "natl-10q-2025-09-30"
LABEL_MERGES = 16


def _sources() -> Iterator[Any]:
    for key in KEYS:
        data = json.loads(key.read_text(encoding="utf-8"))
        for source in data["sources"]:
            yield pytest.param(source, id=f"{data['case']}/{source['source_id']}")


def _units() -> Iterator[Any]:
    for param in _sources():
        source = param.values[0]
        for unit in source["units"]:
            yield pytest.param(source, unit, id=f"{param.id}/{unit['kind']}")


def _lines(source: dict[str, Any]) -> list[str]:
    if not CORPUS.is_dir():
        pytest.skip("public corpus directory absent (artifacts/public-corpus/v1)")
    path = CORPUS / source["file"]
    if path.suffix.lower() not in {".htm", ".html"} or not path.is_file():
        pytest.skip(f"{source['file']} is not a converted corpus file")
    text = convert_html(path.read_bytes()).text
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == source["converted_sha256"]
    return text.splitlines()


@cache
def _cached_lines(file: str, sha: str) -> tuple[str, ...]:
    return tuple(_lines({"file": file, "converted_sha256": sha}))


def _converted(source: dict[str, Any]) -> list[str]:
    return list(_cached_lines(source["file"], source["converted_sha256"]))


def _pack(source_id: str, lines: list[str]) -> PreparedPack:
    """The shared test pack with its financial source made the line source `source_id`."""
    base: PreparedPack = make_pack()
    spans = tuple(Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1))
    return base.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"source_id": source_id, "spans": spans})
                if s.source_id == FIN
                else s
                for s in base.sources
            )
        }
    )


def _context(source_id: str) -> SourceContextReview:
    stand_in = SimpleNamespace(
        sources=[SimpleNamespace(source_id=source_id, classification="financial")]
    )
    return cast(SourceContextReview, stand_in)


def _locator(unit: dict[str, Any]) -> str:
    return f"line:{unit['start'].split(':')[1]}-{unit['end'].split(':')[1]}"


def _table(source: dict[str, Any], unit: dict[str, Any]) -> Any:
    """DW's extraction of one unit through the extract tool, then the validator's `seen_tables`."""
    source_id = source["source_id"]
    tools = LineTools(_pack(source_id, _converted(source)), sources=(source_id,))
    tools.extract_statements({"source_id": source_id, "locators": [_locator(unit)]})
    (table,) = seen_tables(tools, tools.seen(), _context(source_id))
    assert table.locator == _locator(unit)
    return table


def test_the_key_holds_every_unit_and_row() -> None:
    sources = [p.values[0] for p in _sources()]
    units = [u for s in sources for u in s["units"]]
    assert len(sources) == 12
    assert len(units) == UNITS
    assert sum(len(u["rows"]) for u in units) == ROWS


@pytest.mark.parametrize(("source", "unit"), _units())
def test_the_rows_of_a_unit_are_the_key_rows(source: dict[str, Any], unit: dict[str, Any]) -> None:
    table = _table(source, unit)
    got = [(row.line_no, row.label, list(row.raw_values)) for row in table.lines]
    want = [(row["line"], row["label"], row["raw_values"]) for row in unit["rows"]]
    assert got == want
    assert [row.locator for row in table.lines] == [f"line:{row['line']}" for row in unit["rows"]]


def _label_merges() -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Key rows whose line is preceded by a value-less line: DVII's merge would prefix it."""
    merged = []
    for param in _units():
        source, unit = param.values
        lines = _converted(source)
        for row in unit["rows"]:
            above = lines[row["line"] - 2]
            if above and not any(c.isdigit() for c in above) and not above.endswith(":"):
                merged.append((source, unit, row))
    return merged


def test_the_key_rows_that_a_merge_would_change_are_checked() -> None:
    assert len(_label_merges()) >= LABEL_MERGES


def test_a_label_is_its_own_line_never_merged_with_the_line_above() -> None:
    for source, unit, row in _label_merges():
        table = _table(source, unit)
        got = next(r for r in table.lines if r.line_no == row["line"])
        assert got.label == row["label"], (source["source_id"], row["line"])


def test_natl_10q_line_96_label_is_its_own_cell() -> None:
    key = json.loads((REPO / "cases/statement-rows/natl-portfolio-decision.json").read_text())
    source = next(s for s in key["sources"] if s["source_id"] == NATL_10Q)
    unit = next(u for u in source["units"] if any(r["line"] == 96 for r in u["rows"]))
    lines = _converted(source)
    assert lines[95].startswith("Cash and cash equivalents")
    row = next(r for r in _table(source, unit).lines if r.line_no == 96)
    assert row.label == "Cash and cash equivalents"
    assert "Assets" not in row.label


def test_the_tool_path_returns_the_shc_10q_balance_sheet_rows() -> None:
    key = json.loads((REPO / "cases/statement-rows/shc-earnings-update.json").read_text())
    source = next(s for s in key["sources"] if s["source_id"] == SHC_10Q)
    pack = _pack(SHC_10Q, _converted(source))
    tools = SourceTools(pack, [SHC_10Q], extraction=True)
    body, staged = tools.stage(
        "extract_statements", {"source_id": SHC_10Q, "locators": ["line:33-81"]}
    )
    assert "no statement lines extracted" not in body
    rows = [r.split(" | ") for r in body.splitlines() if r.split(" | ")[0].isdigit()]
    row = next(r for r in rows if r[0] == "38")
    assert row[1] == "Cash and cash equivalents"
    assert row[3] == "332,437 277,242"
    assert (SHC_10Q, "line:33-81") in staged.extracted
    tools.commit(staged)
    assert [SHC_10Q, "line:33-81"] in tools.evidence()["extracted"]


@pytest.mark.parametrize("source", _sources())
def test_respacing_changes_only_the_spacing_of_a_line(source: dict[str, Any]) -> None:
    lines = _converted(source)
    for x in lines:
        spaced = respace(x)
        assert " ".join(spaced.split()) == x
        assert "\n" not in spaced


def _shc_units() -> Iterator[Any]:
    for param in _units():
        source, unit = param.values
        if source["source_id"].startswith("SHC_"):
            yield pytest.param(source, unit, id=param.id)


def test_there_are_six_shc_units() -> None:
    assert len(list(_shc_units())) == 6


@pytest.mark.parametrize(("source", "unit"), _shc_units())
def test_the_shc_headers_map_to_the_columns_of_the_rows(
    source: dict[str, Any], unit: dict[str, Any]
) -> None:
    table = _table(source, unit)
    headers = tuple(table.headers)
    specs = [fw._spec_row(headers, i) for i in range(len(headers))]
    found = [s for s in specs if s is not None]
    assert found, headers
    widths = {len(row["raw_values"]) for row in unit["rows"]}
    assert widths == {len(found[0])}


# ---- S11-A03 / C02: HTML value cells beyond `$ 1,234` (synthetic lines, no corpus) ---------


def _spans(lines: list[str]) -> dict[int, Span]:
    return {i: Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1)}


@pytest.mark.parametrize("symbol", ["€", "£"])
def test_euro_and_pound_value_cells_are_respaced_and_extracted(symbol: str) -> None:
    """By hand: three data rows, Revenue 1,234 and 1,100, Cost of sales (800) and (700), and
    Operating profit 434 and 400; the symbol marks the first and third rows' cells."""
    lines = [
        "CONSOLIDATED INCOME STATEMENT",
        "2024 2023",
        f"Revenue {symbol} 1,234 {symbol} 1,100",
        "Cost of sales (800) (700)",
        f"Operating profit {symbol} 434 {symbol} 400",
    ]
    assert respace(lines[2]) == f"Revenue  {symbol} 1,234  {symbol} 1,100"
    assert " ".join(respace(lines[2]).split()) == lines[2]
    table = line_table(_spans(lines), "line:1-5", "fin")
    assert [(row.label, row.values, row.currency_values) for row in table.lines] == [
        ("Revenue", (Decimal(1234), Decimal(1100)), (True, True)),
        ("Cost of sales", (Decimal(-800), Decimal(-700)), (False, False)),
        ("Operating profit", (Decimal(434), Decimal(400)), (True, True)),
    ]


@pytest.mark.parametrize(
    "line,spaced",
    [
        ("Operating loss $ (250 ) $ (10 )", "Operating loss  $ (250 )  $ (10 )"),
        ("Other expense −45 −30", "Other expense  −45  −30"),
        ("Capex (1,234 ) (1,100 )", "Capex  (1,234 )  (1,100 )"),
    ],
)
def test_split_parenthesis_and_unicode_minus_cells_are_cells_not_label(
    line: str, spaced: str
) -> None:
    assert respace(line) == spaced
    assert " ".join(spaced.split()) == line


def test_a_row_the_extractor_cannot_read_refuses_the_range_instead_of_vanishing() -> None:
    """EDGAR prints `<td>(250</td><td>)</td>`, converted to `(250 )`, and a Unicode minus `−45`;
    the extractor reads neither. The range is refused naming the line and its cells, so the
    operating loss cannot silently disappear from the extraction and the coverage gate."""
    html = (
        b"<html><body><table>"
        b"<tr><td></td><td>2024</td><td>2023</td></tr>"
        b"<tr><td>Revenue</td><td>$</td><td>1,234</td><td>$</td><td>1,100</td></tr>"
        b"<tr><td>Operating loss</td><td>$</td><td>(250</td><td>)</td>"
        b"<td>$</td><td>(10</td><td>)</td></tr>"
        b"<tr><td>Other expense</td><td>&#8722;45</td><td>&#8722;30</td></tr>"
        b"<tr><td>Net loss</td><td>$</td><td>(300)</td><td>$</td><td>(40)</td></tr>"
        b"</table></body></html>"
    )
    lines = convert_html(html).text.splitlines()
    assert lines[2] == "Operating loss $ (250 ) $ (10 )"
    with pytest.raises(ToolError, match=r"line:3 of fin holds value cells Python cannot read"):
        line_table(_spans(lines), "line:1-5", "fin")
    with pytest.raises(ToolError, match=r"line:4 of fin .*'−45', '−30'"):
        line_table(_spans(lines), "line:4-5", "fin")
    one_column = _spans(["2024", "Operating loss $ (250 )"])
    with pytest.raises(ToolError, match=r"line:2 of fin .*'\$ \(250 \)'"):
        line_table(one_column, "line:1-2", "fin")
    # The readable rows of a range without those lines extract as before (hand-read values).
    table = line_table(_spans(lines), "line:1-2", "fin")
    assert [(row.label, row.values) for row in table.lines] == [
        ("Revenue", (Decimal(1234), Decimal(1100)))
    ]


def test_a_bare_closing_parenthesis_or_minus_in_a_label_is_not_a_value_cell() -> None:
    """A label ending in `)` (`Tax (note 4)` is a footnote, not a split number) and a label with
    a minus sign are left to the extractor as today; only a `(N` `)` pair or a `−N` cell counts."""
    assert respace("Income tax (benefit) 12 10") == "Income tax (benefit)  12  10"
    assert respace("Other ) 12 10") == "Other )  12  10"
    assert respace("Non−operating items 12 10") == "Non−operating items  12  10"
    table = line_table(_spans(["2024 2023", "Income tax (benefit) 12 10"]), "line:1-2", "fin")
    assert [(row.label, row.values) for row in table.lines] == [
        ("Income tax (benefit)", (Decimal(12), Decimal(10)))
    ]
