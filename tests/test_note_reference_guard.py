"""The note-reference guard (CP1H-R23, ruling R23.24, T23).

Answer key (read, never written): the adversary's probes of ``work/build/cp1h/reviews/
T19-adversary-2.md`` (``b1_m2_outside_governed.py``, ``b2_note_until_escapes.py``,
``b3_two_note_cells.py``, ``b5_leader_exposes_m2.py``). Each probe input is rebuilt here from the
fixture pages exactly as the probe builds it. On a page that prints a note-reference column, a row
whose first value is a bare unsigned 1-2-digit number or ``n.n`` is left to the model with
``note_reference_suspect``; Python writes no line for it. The controls are TDG p105 (no Note
column) and VMO2Q3 p004 unedited (rows with a longer first value compose as without the guard).
"""

import json
import re
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.contracts import Span
from deploy_vii.statement_extract import ExtractedLine, ExtractedTable, extract_statement_lines
from deploy_workflow import financial_workflow as fw
from deploy_workflow import statement_compose as sc
from deploy_workflow.unit_maps import UnitInputs, expand

PAGES = Path(__file__).resolve().parent / "fixtures" / "pdf_pages"
SHA = "0" * 64
DETAIL = (
    "the page prints a note-reference column and this row's first value could be a note number; "
    "Python writes no line for it"
)
COLUMNS = ("p0", "p1")


def printed(_table: Any, _book: Any) -> tuple[frozenset[str], ...]:
    """The table's own printed header as ``UnitInputs.ocr_header`` reads it: one period per
    column (CP1H-R23.27.1 verifies every unit's map against it)."""
    return tuple(frozenset({c}) for c in COLUMNS)
NOTE_LOOKING = re.compile(r"\d{1,2}(?:\.\d{1,2})?")


def _fixture(doc: str, page: int) -> str:
    return (PAGES / doc / f"p{page:03d}.txt").read_text("utf-8")


def _blank_last(lines: Sequence[str], index: int, sign: str = "£") -> list[str]:
    """The lines with the last (2024) cell of one line blanked: cut at its last sign."""
    out = list(lines)
    out[index] = out[index][: out[index].rindex(sign)].rstrip()
    return out


def _vmed_cases() -> list[Any]:
    p172 = _fixture("VMED25", 172).split("\n")
    p107 = _fixture("VMED25", 107).rstrip("\n").split("\n")
    soci = _fixture("VMED25", 108).split("\n")
    for i, line in enumerate(soci):
        if "Defined benefit-related adjustments" in line:
            soci[i] = line[: line.index("(4.7)")] + "£ (4.7)"
    header = " " * 40 + "Note        2025        2024\n"
    return [
        pytest.param(
            "\n".join(_blank_last(p172, 11)), "Investments in subsidiaries", id="b1-p172-line-12"
        ),
        pytest.param(
            "\n".join(_blank_last(p172, 23)),
            "Creditors: amounts falling due after",
            id="b1-p172-line-24",
        ),
        pytest.param(
            "\n".join(p107 + soci), "Defined benefit-related adjustments", id="b1-p107-p108"
        ),
        pytest.param(
            "| | Note | 2025 | 2024 |\n| Revenue | 4 | £ 1,200 | |", "Revenue", id="b1-pipe-page"
        ),
        pytest.param(
            header + "Revenue" + " " * 32 + "4.1      € 1,200", "Revenue", id="b1-dotted-note"
        ),
        pytest.param(
            " " * 48
            + "2025        2024\n"
            + " " * 38
            + "Note      in millions\n"
            + "Revenue"
            + " " * 33
            + "4      £ 1,200",
            "Revenue",
            id="b1-note-cell-on-the-units-line",
        ),
        pytest.param(
            header + "Revenue" + " " * 30 + "4  5        1,200", "Revenue", id="b3-two-note-cells"
        ),
        pytest.param(
            header + "Revenue" + " " * 30 + "4  5      £ 1,200",
            "Revenue",
            id="b3-two-note-cells-gbp",
        ),
        pytest.param(
            header + "Revenue ................................ 4        1,200",
            "Revenue",
            id="b5-leader-one-space-before-note",
        ),
        pytest.param(
            header + "Revenue . . . . . . . . . . . . . . . . 4        1,200",
            "Revenue",
            id="b5-spaced-leader",
        ),
        pytest.param(
            header + "Revenue ..............................  4        1,200",
            "Revenue",
            id="b5-two-space-gap-after-leader",
        ),
    ]


def _vmo2_cases() -> list[Any]:
    top = _fixture("VMO2Q3", 4).rstrip("\n").split("\n")[:30]
    row = " Other financial assets" + " " * 140 + "12" + " " * 18 + "45" + " " * 18 + "67"
    bare = " " * 150 + "2025" + " " * 16 + "2024" + " " * 16 + "2023"
    headers = {
        "b2-group": " Group" + bare[6:],
        "b2-pounds-m": " £m" + bare[3:],
        "b2-dollars-m": " US$m" + bare[5:],
        "b2-level": " " * 147 + "Level 1" + " " * 13 + "Level 2" + " " * 13 + "Level 3",
    }
    return [
        pytest.param("\n".join([*top, "", header, row]), "Other financial assets", id=name)
        for name, header in headers.items()
    ]


UNSAFE = [*_vmed_cases(), *_vmo2_cases()]


def _row_map(table: ExtractedTable) -> dict[int, sc.RowJudgment]:
    """Every extracted row mapped to its own `other:` item, as a detail, signed."""
    return {
        r.line_no: sc.RowJudgment(f"l{r.line_no}", f"other:r{r.line_no}", "detail", "signed")
        for r in table.lines
    }


def _compose(
    table: ExtractedTable,
    columns: Sequence[str | None] = COLUMNS,
    **keywords: Any,
) -> sc.Composition:
    return sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=SHA,
        unit_locator=table.locator,
        kind="IS",
        column_periods=columns,
        row_map=_row_map(table),
        declared_periods=[p for p in columns if p is not None],
        **keywords,
    )


def _written(composition: sc.Composition) -> set[str]:
    """The labels of the rows the composition wrote lines for (a page's rows share one locator)."""
    return {line.label for line in composition.lines}


def _the_row(table: ExtractedTable, label: str) -> ExtractedLine:
    (row,) = [r for r in table.lines if r.label.startswith(label)]
    return row


# ---- detection ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "label"), UNSAFE)
def test_each_probe_page_is_detected_as_a_note_page(text: str, label: str) -> None:
    assert fw._has_note_column(text)


@pytest.mark.parametrize(
    "line",
    [
        "Revenue      Note      2025      2024",
        "                  Notes        2025",
        "      Note References       in millions",
        "| | Note | 2025 | 2024 |",
        "   note        2025",
        "  NOTES  ",
        "Note\n",
    ],
)
def test_a_cell_that_is_exactly_note_notes_or_note_references_is_a_note_column(line: str) -> None:
    assert fw._has_note_column(line)


@pytest.mark.parametrize(
    "line",
    [
        "Revenue (Note 9)      1,200",
        "Notes to the financial statements",
        "Footnote      2025",
        "See Note 4 for details",
        "Net income      21      15",
        "| Revenue | Notes to accounts |",
        "",
    ],
)
def test_a_line_without_a_note_cell_is_not_a_note_column(line: str) -> None:
    assert not fw._has_note_column(line)


def test_the_note_cell_counts_anywhere_on_the_page_not_only_in_the_header_block() -> None:
    text = "Revenue    1,200    1,000\n" * 40 + "Total      Note      x"
    assert fw._has_note_column(text)


def test_the_note_pages_are_the_located_financial_units_that_print_a_note_column() -> None:
    def source(source_id: str, status: str, pages: dict[str, str]) -> SimpleNamespace:
        spans = [Span(locator=loc, text=text) for loc, text in pages.items()]
        return SimpleNamespace(source_id=source_id, status=status, spans=spans)

    title = "CONSOLIDATED STATEMENTS OF INCOME\n" + " " * 30
    plain = title + "2025        2024\nRevenue  1,200  1,000"
    noted = title + "Note        2025        2024\nRevenue       4      1,200  1,000"
    pack = SimpleNamespace(
        sources=[
            source("fin", "ready", {"page:1": plain, "page:2": noted}),
            source("other", "ready", {"page:1": noted}),
        ]
    )
    assert fw._note_pages(pack, ("fin",)) == {("fin", "page:2")}


# ---- the rule ----------------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "label"), UNSAFE)
def test_the_unsafe_row_of_each_probe_is_left_to_the_model_with_no_line(
    text: str, label: str
) -> None:
    table = extract_statement_lines(text, "page:1")
    row = _the_row(table, label)
    plain = _compose(table)
    assert row.label in _written(plain), "the probe row must be composable without the guard"
    guarded = _compose(table, note_page=True)
    assert row.label not in _written(guarded)
    left = [x for x in guarded.left_to_model if x.line_no == row.line_no]
    assert [(x.reason, x.detail) for x in left] == [(sc.NOTE_SUSPECT, DETAIL)]
    assert sc.NOTE_SUSPECT == "note_reference_suspect"


def test_a_bare_short_or_dotted_first_value_is_suspect_and_a_longer_one_is_not() -> None:
    table = extract_statement_lines("Revenue  4  5\nCost  12  3\nTax  1.5  2\nFee  100  2\n", "p")
    guarded = _compose(table, note_page=True)
    reasons = {x.label: x.reason for x in guarded.left_to_model}
    assert reasons == {
        "Revenue": sc.NOTE_SUSPECT,
        "Cost": sc.NOTE_SUSPECT,
        "Tax": sc.NOTE_SUSPECT,
    }
    assert {line.label for line in guarded.lines} == {"Fee"}


def test_a_first_value_with_a_thousands_separator_a_sign_or_three_digits_composes() -> None:
    table = extract_statement_lines("Gross  1,200  2\nNet  (5)  2\nOther  123  2\n", "p")
    guarded = _compose(table, note_page=True)
    assert guarded.left_to_model == ()
    assert {line.label for line in guarded.lines} == {"Gross", "Net", "Other"}


def test_the_guard_is_off_unless_the_page_prints_a_note_column() -> None:
    table = extract_statement_lines("Revenue  4  5\n", "p")
    assert _written(_compose(table)) == _written(_compose(table, note_page=False)) == {"Revenue"}
    assert _compose(table, note_page=False).left_to_model == ()


def test_a_row_already_flagged_keeps_its_own_reason_and_the_other_rows_compose() -> None:
    table = extract_statement_lines("Revenue  4  5\nCost  7  8\nFee  1,200  900\n", "p")
    flagged = replace(table.lines[0], flags=("label_ends_numeric",))
    table = replace(table, lines=(flagged, *table.lines[1:]))
    guarded = _compose(table, note_page=True)
    assert {x.label: x.reason for x in guarded.left_to_model} == {
        "Revenue": sc.FLAGGED,
        "Cost": sc.NOTE_SUSPECT,
    }
    assert {line.label for line in guarded.lines} == {"Fee"}


def test_a_suspect_row_is_left_out_of_the_unit_checks_like_every_other_left_row() -> None:
    text = "Operating  500  100\nInvesting  -  (40)\nFinancing  -  (10)\nNet change  3  50\n"
    table = extract_statement_lines(text, "p")
    items = {
        "Operating": sc.OPERATING,
        "Investing": sc.INVESTING,
        "Financing": sc.FINANCING,
        "Net change": sc.NET_CHANGE,
    }
    row_map = {
        r.line_no: sc.RowJudgment(f"l{r.line_no}", items[r.label], "total", "signed")
        for r in table.lines
    }
    result = sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=SHA,
        unit_locator="p",
        kind="CFS",
        column_periods=COLUMNS,
        row_map=row_map,
        declared_periods=COLUMNS,
        note_page=True,
    )
    suspects = {x.label for x in result.left_to_model if x.reason == sc.NOTE_SUSPECT}
    assert suspects == {"Net change"}
    assert result.issues == ()
    assert [check for check, _ in result.checks_not_applied] == [sc.CFS_NET_CHANGE]
    assert {line.label for line in result.lines} == {"Operating", "Investing", "Financing"}
    off = sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=SHA,
        unit_locator="p",
        kind="CFS",
        column_periods=COLUMNS,
        row_map=row_map,
        declared_periods=COLUMNS,
    )
    assert [i.check for i in off.issues] == [sc.CFS_NET_CHANGE]  # column 0: 500 against 3


# ---- controls ----------------------------------------------------------------------------------


def test_tdg_p105_has_no_note_column_and_composes_as_without_the_guard() -> None:
    text = _fixture("TDG", 105)
    note = fw._has_note_column(text)
    assert not note
    table = extract_statement_lines(text, "page:105")
    without = _compose(table)
    assert without.lines, "the control must compose lines"
    assert _compose(table, note_page=note).lines == without.lines


def test_vmo2q3_p004_rows_with_a_longer_first_value_compose_as_without_the_guard() -> None:
    text = _fixture("VMO2Q3", 4)
    assert fw._has_note_column(text)
    table = extract_statement_lines(text, "page:4")
    without = _compose(table)
    guarded = _compose(table, note_page=True)
    looking = {
        r.label for r in table.lines if r.raw_values and NOTE_LOOKING.fullmatch(r.raw_values[0])
    }
    safe = {r.label for r in table.lines} - looking
    assert safe & _written(without), "the control must compose rows"
    keep = [x for x in without.lines if x.label in safe]
    assert [x for x in guarded.lines if x.label in safe] == keep
    new = {x.reason for x in guarded.left_to_model} - {x.reason for x in without.left_to_model}
    assert new <= {sc.NOTE_SUSPECT}


# ---- wiring ------------------------------------------------------------------------------------


@pytest.mark.parametrize("on_note_page", [True, False])
def test_the_expansion_passes_note_page_for_a_unit_on_a_note_page_only(
    monkeypatch: pytest.MonkeyPatch, on_note_page: bool
) -> None:
    table = extract_statement_lines("Revenue  4  5\n", "page:1", "doc")
    key = (table.source_id, table.locator)
    asked: list[Any] = []
    real = sc.compose_unit

    def spy(*args: Any, **kwargs: Any) -> sc.Composition:
        asked.append(kwargs.get("note_page"))
        return real(*args, **kwargs)

    monkeypatch.setattr(sc, "compose_unit", spy)
    pages = frozenset({key}) if on_note_page else frozenset({("other-source", "page:1")})
    unit = {
        "source_id": table.source_id,
        "locator": table.locator,
        "book_id": "b1",
        "statement": "IS",
        "columns": COLUMNS,
        "rows": [],
    }
    book = {"book_id": "b1", "periods": [{"period_id": p} for p in COLUMNS], "statement_lines": []}
    document = json.dumps({"financial": {"books": [book]}, "unit_maps": [unit]})
    expand(
        document,
        extracted={key},
        inputs=lambda: UnitInputs(
            [table],
            {table.source_id: SHA},
            note_pages=pages,
            ocr_header=printed,
            located=frozenset({key}),
        ),
    )
    assert asked == [on_note_page]
