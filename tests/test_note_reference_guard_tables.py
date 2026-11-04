"""The note-reference guard, per composed table (CP1H-R23, R23.24 and R23.24.1, T23 fix round 1).

Answer key (read, never written): the adversary's probes ``a3_glued_note_header.py``,
``a4_html_line_source.py``, ``a5_unlocated_unit_route.py`` and ``a6_m2_long_second_value.py`` of
``review-probes/t23-adv/`` (findings in ``work/build/cp1h/reviews/T23-adversary-1.md``). Each
probe input is rebuilt here as the probe builds it. Each unsafe row is left with
``note_reference_suspect`` and composes no line. Detection pins: VMO2Q3 p006, p007 and p009 are
note pages; no page of TDG, CZR, FUN or SIX22 is.
"""

import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_note_reference_guard import COLUMNS, SHA, _compose, _fixture, _written, printed

from deploy_vii.contracts import Span
from deploy_vii.statement_extract import FOOTNOTE_MARKER, ExtractedTable, extract_statement_lines
from deploy_workflow import financial_workflow as fw
from deploy_workflow import statement_compose as sc
from deploy_workflow.html_text import convert_html
from deploy_workflow.statement_lines import line_table
from deploy_workflow.unit_maps import UnitInputs, expand

PAGES = Path(__file__).resolve().parent / "fixtures" / "pdf_pages"
BELOW = (
    "the page prints a note-reference column and this row sits below a second header, so its "
    "dropped note may have been a value; Python writes no line for it"
)
EM_DASH = "—"
POUND = "£"


def _pack(source_id: str, spans: Sequence[Span]) -> SimpleNamespace:
    source = SimpleNamespace(source_id=source_id, status="ready", spans=list(spans), coverage=())
    return SimpleNamespace(sources=[source])


def _guarded(
    table: ExtractedTable, pack: SimpleNamespace, columns: Sequence[str | None] = COLUMNS
) -> sc.Composition:
    """The composition with the guard inputs `expand_unit_maps` derives from the pack."""
    ids = [table.source_id]
    key = (table.source_id, table.locator)
    return _compose(
        table,
        columns,
        note_page=key in fw._note_pages(pack, ids, [table]),
        note_rows=fw._note_rows(pack, ids, [table]).get(key, frozenset()),
    )


# ---- a6: a second table on a note page -----------------------------------------------------------


def _second_table_cases() -> list[Any]:
    top = _fixture("VMO2Q3", 4).rstrip("\n").split("\n")[:30]
    bare = " " * 150 + "2025" + " " * 16 + "2024" + " " * 16 + "2023"
    headers = {
        "group": " Group" + bare[6:],
        "pounds-m": " " + POUND + "m" + bare[3:],
        "dollars-m": " US$m" + bare[5:],
        "level": " " * 147 + "Level 1" + " " * 13 + "Level 2" + " " * 13 + "Level 3",
    }
    label = " Other financial assets"

    def row(a: str, b: str, c: str) -> str:
        pad = " " * (165 - len(label) - len(a))
        return label + pad + a + " " * (20 - len(b)) + b + " " * (20 - len(c)) + c

    values = [("12", "450", "670"), ("12", "1,245", "1,067"), ("8", "(1,500)", "900")]
    return [
        pytest.param("\n".join([*top, "", header, row(*triple)]), id=f"{name}-{'-'.join(triple)}")
        for name, header in headers.items()
        for triple in values
    ]


FIRST_TEXT = _second_table_cases()[0].values[0]


@pytest.mark.parametrize("text", _second_table_cases())
def test_a_footnote_marker_row_below_a_second_header_is_left_to_the_model(text: str) -> None:
    table = extract_statement_lines(text, "page:4", "doc")
    pack = _pack("doc", [Span(locator="page:4", text=text)])
    (row,) = [r for r in table.lines if r.label.startswith("Other financial assets")]
    assert row.label in _written(_compose(table)), "the row must be composable without the guard"
    guarded = _guarded(table, pack)
    assert row.label not in _written(guarded)
    left = [x for x in guarded.left_to_model if x.line_no == row.line_no]
    assert [(x.reason, x.detail) for x in left] == [(sc.NOTE_SUSPECT, BELOW)]


def test_note_rows_takes_only_footnote_marker_rows_below_the_first_second_header() -> None:
    text = FIRST_TEXT
    table = extract_statement_lines(text, "page:4", "doc")
    pack = _pack("doc", [Span(locator="page:4", text=text)])
    rows = fw._note_rows(pack, ["doc"], [table])[("doc", "page:4")]
    marked = {r.line_no for r in table.lines if FOOTNOTE_MARKER in r.flags}
    assert rows and rows <= marked
    assert min(rows) > min(r.line_no for r in table.lines)


def test_note_rows_leaves_a_row_that_is_flagged_otherwise_with_its_own_reason() -> None:
    text = FIRST_TEXT
    table = extract_statement_lines(text, "page:4", "doc")
    (row,) = [r for r in table.lines if r.label.startswith("Other financial assets")]
    flagged = replace(row, flags=("label_ends_numeric",))
    table = replace(table, lines=tuple(flagged if r is row else r for r in table.lines))
    result = _compose(table, note_page=True, note_rows=frozenset({row.line_no}))
    left = [x for x in result.left_to_model if x.line_no == row.line_no]
    assert [x.reason for x in left] == [sc.FLAGGED]


def test_a_row_outside_note_rows_composes_as_before() -> None:
    table = extract_statement_lines("Fee  1,200  900\n", "p")
    assert _written(_compose(table, note_rows=frozenset({99}))) == {"Fee"}


# ---- a3: the Note header glued to the last year ---------------------------------------------


def _blank_last(text: str, label: str, last: str) -> str:
    out = []
    for line in text.split("\n"):
        if label in line:
            assert line.rstrip().endswith(last), line
            line = line.rstrip()[: -len(last)].rstrip()
        out.append(line)
    return "\n".join(out)


@pytest.mark.parametrize(
    ("page", "label", "last", "columns"),
    [
        pytest.param(9, "Cash received from O2 Daisy Transaction", EM_DASH, 2, id="p009-line-43"),
        pytest.param(6, "Finance costs", "(1,365.7)", 4, id="p006-finance-costs"),
    ],
)
def test_a_note_number_beside_a_blank_cell_on_a_glued_header_page_is_left(
    page: int, label: str, last: str, columns: int
) -> None:
    text = _blank_last(_fixture("VMO2Q3", page), label, last)
    locator = f"page:{page}"
    table = extract_statement_lines(text, locator, "vmo2")
    pack = _pack("vmo2", [Span(locator=locator, text=text)])
    names = tuple(f"p{i}" for i in range(columns))
    (row, *_) = [r for r in table.lines if r.label.startswith(label)]
    assert fw._has_note_column(text)
    guarded = _guarded(table, pack, names)
    assert row.label not in _written(guarded)
    left = [x for x in guarded.left_to_model if x.line_no == row.line_no]
    assert [x.reason for x in left] == [sc.NOTE_SUSPECT]


@pytest.mark.parametrize("page", [6, 7, 9])
def test_the_glued_header_pages_of_vmo2q3_are_note_pages(page: int) -> None:
    assert fw._has_note_column(_fixture("VMO2Q3", page))


@pytest.mark.parametrize("doc", ["TDG", "CZR", "FUN", "SIX22"])
def test_no_page_of_the_other_documents_is_a_note_page(doc: str) -> None:
    pages = sorted((PAGES / doc).glob("p*.txt"))
    assert pages
    assert [p.name for p in pages if fw._has_note_column(p.read_text("utf-8"))] == []


@pytest.mark.parametrize(
    "line",
    [
        " " * 40 + "2025        2024Note",
        "Revenue" + " " * 20 + "in millionsReferences",
        "Revenue" + " " * 20 + "in millionsNote",
        "                References       2025",
        "  references  ",
        " " * 20 + "30 September 2025Notes",
    ],
)
def test_the_glued_and_bare_references_forms_are_note_columns(line: str) -> None:
    assert fw._has_note_column(line)


@pytest.mark.parametrize(
    "line",
    [
        "Revenue from salesNote      4",
        "Footnotes to the 2025 summary",
        "See References",
        "Revenue      in millions      2025",
    ],
)
def test_a_glued_word_needs_a_year_or_unit_line_and_a_note_word_of_its_own(line: str) -> None:
    assert not fw._has_note_column(line)


# ---- a5 and a4: any extracted table, and a line source respaced -----------------------------


def test_a_page_that_is_not_a_located_unit_is_a_note_page_through_its_table() -> None:
    p172 = _fixture("VMED25", 172).split("\n")
    p172[11] = p172[11][: p172[11].rindex(POUND)].rstrip()
    text = "\n".join(p172)
    pack = _pack("vmed", [Span(locator="page:172", text=text)])
    table = extract_statement_lines(text, "page:172", "vmed")
    assert ("vmed", "page:172") not in fw._note_pages(pack, ["vmed"])
    assert ("vmed", "page:172") in fw._note_pages(pack, ["vmed"], [table])


def _expand(pack: SimpleNamespace, table: ExtractedTable, statement: str, label: str) -> list[Any]:
    """The lines of `label` that `expand` composes, with `UnitInputs` as `inputs()` builds them."""
    ids = [table.source_id]
    inputs = UnitInputs(
        [table],
        {table.source_id: SHA},
        fw._other_statement_rows(pack, ids, [table]),
        fw._ocr_pages(pack, ids),
        fw._note_pages(pack, ids, [table]),
        fw._note_rows(pack, ids, [table]),
        ocr_header=printed,
        located=frozenset({(table.source_id, table.locator)}),
    )
    book = {"book_id": "b1", "periods": [{"period_id": p} for p in COLUMNS], "statement_lines": []}
    unit = {
        "source_id": table.source_id,
        "locator": table.locator,
        "book_id": "b1",
        "statement": statement,
        "columns": list(COLUMNS),
        "rows": [
            {
                "row": r.line_no,
                "line_id": f"l{r.line_no}",
                "item_id": f"other:r{r.line_no}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for r in table.lines
        ],
    }
    document = json.dumps({"financial": {"books": [book]}, "unit_maps": [unit]})
    result = expand(document, extracted={(table.source_id, table.locator)}, inputs=lambda: inputs)
    lines = json.loads(result.payload)["financial"]["books"][0]["statement_lines"]
    assert lines, "the control rows must compose"
    return [x for x in lines if x["label"].startswith(label)]


def test_expand_leaves_the_note_row_of_an_unlocated_note_page() -> None:
    p172 = _fixture("VMED25", 172).split("\n")
    p172[11] = p172[11][: p172[11].rindex(POUND)].rstrip()
    text = "\n".join(p172)
    pack = _pack("vmed", [Span(locator="page:172", text=text)])
    table = extract_statement_lines(text, "page:172", "vmed")
    assert _expand(pack, table, "BS", "Investments in subsidiaries") == []


HTML = (
    b"<html><body><p>Consolidated Statement of Financial Position</p><table>"
    b"<tr><td>Note</td><td>2025</td><td>2024</td></tr>"
    b"<tr><td>Trade receivables</td><td>4</td><td>350.0</td><td></td></tr>"
    b"<tr><td>Total assets</td><td></td><td>2,050.0</td><td>1,500.0</td></tr>"
    b"</table></body></html>"
)


def _html_table(locator: str) -> tuple[SimpleNamespace, ExtractedTable]:
    lines = convert_html(HTML).text.splitlines()
    spans = [Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1)]
    numbered = dict(enumerate(spans, 1))
    return _pack("html", spans), line_table(numbered, locator, "html")


def test_expand_leaves_the_note_row_of_a_line_unit_mapped_under_another_range() -> None:
    pack, table = _html_table("line:2-4")
    assert _expand(pack, table, "BS", "Trade receivables") == []


def test_a_line_source_note_cell_is_found_after_the_respacing_of_its_lines() -> None:
    pack, table = _html_table("line:2-4")
    assert ("html", "line:2-4") in fw._note_pages(pack, ["html"], [table])
    (row,) = [r for r in table.lines if r.label == "Trade receivables"]
    guarded = _guarded(table, pack)
    assert row.label not in _written(guarded)


def test_the_raw_single_spaced_line_of_a_line_unit_holds_no_note_cell() -> None:
    pack, table = _html_table("line:2-4")
    raw = "\n".join(s.text for s in pack.sources[0].spans[1:4])
    assert not fw._has_note_column(raw), "the raw single-spaced line holds no Note cell"
    assert ("html", "line:2-4") in fw._note_pages(pack, ["html"], [table])


# ---- wiring ---------------------------------------------------------------------------------


def test_the_expansion_passes_the_rows_below_a_second_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = extract_statement_lines("Revenue  1,200  900\n", "page:1", "doc")
    key = (table.source_id, table.locator)
    asked: list[Any] = []
    real = sc.compose_unit

    def spy(*args: Any, **kwargs: Any) -> sc.Composition:
        asked.append(kwargs.get("note_rows"))
        return real(*args, **kwargs)

    monkeypatch.setattr(sc, "compose_unit", spy)
    unit = {
        "source_id": table.source_id,
        "locator": table.locator,
        "book_id": "b1",
        "statement": "IS",
        "columns": list(COLUMNS),
        "rows": [],
    }
    book = {"book_id": "b1", "periods": [{"period_id": p} for p in COLUMNS], "statement_lines": []}
    document = json.dumps({"financial": {"books": [book]}, "unit_maps": [unit]})
    rows = frozenset({3, 4})
    expand(
        document,
        extracted={key},
        inputs=lambda: UnitInputs(
            [table],
            {table.source_id: SHA},
            note_rows={key: rows},
            ocr_header=printed,
            located=frozenset({key}),
        ),
    )
    assert asked == [rows]
