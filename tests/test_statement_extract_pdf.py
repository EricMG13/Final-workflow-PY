"""The statement extractor on real PDF pages (CP1H-R23 change 3, task T19).

The page texts are the exact product intake text of six real filings
(`tests/fixtures/pdf_pages/<DOC>/pNNN.txt`); the answer keys are frozen and are read, never copied:

- `cases/pdf-identities/<DOC>.json`: every named row holds the identity's expected values in column
  order, and the identity then holds in Decimal;
- `cases/pdf-units/<DOC>.json`: which pages hold which statement;
- `cases/statement-rows/tdg-credit-snapshot.json`, source K24: the rows the TDG 10-K must yield.

`tests/czr_pdf_before.json` is the CZR pages (p56, 57, 60, 61) read by the extractor as it was
before this change (7299a924); the before/after test names every difference.
"""

import json
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.statement_extract import (
    FOOTNOTE_MARKER,
    ExtractedLine,
    extract_statement_lines,
)

ROOT = Path(__file__).parent.parent
PAGES = ROOT / "tests" / "fixtures" / "pdf_pages"
DOCS = ("TDG", "CZR", "FUN", "SIX22", "VMO2Q3", "VMED25")
_LEADERS = re.compile(r"(?:[.…]\s*){2,}")


def _json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _rows(doc: str, page: int) -> tuple[ExtractedLine, ...]:
    text = (PAGES / doc / f"p{page:03d}.txt").read_text("utf-8")
    return extract_statement_lines(text, f"page:{page}").lines


def _norm(label: str) -> str:
    """A label with leader dots removed and whitespace normalised."""
    return " ".join(_LEADERS.sub(" ", label).split())


def _identity_cases() -> list[Any]:
    cases = []
    for doc in DOCS:
        for identity in _json(ROOT / "cases" / "pdf-identities" / f"{doc}.json")["identities"]:
            cases.append(pytest.param(doc, identity, id=identity["id"]))
    return cases


@pytest.mark.parametrize(("doc", "identity"), _identity_cases())
def test_identity_rows_hold_the_expected_values_and_the_identity_holds(
    doc: str, identity: dict[str, Any]
) -> None:
    columns = identity["columns"]
    sides: dict[str, list[list[Decimal | None]]] = {"lhs": [], "rhs": []}
    for side, rows in sides.items():
        for item in identity[side]:
            expected = [Decimal(column["values"][item["label"]]) for column in columns]
            name = _norm(item["label"])
            page = _rows(doc, item["page"])
            exact = [row for row in page if _norm(row.label) == name]
            # A printed trailing "(Note 9)" is part of the row label, not of the key's name; such
            # a prefix-only match counts only when it is the single prefix hit on the page.
            prefixed = [row for row in page if _norm(row.label).startswith(name)]
            hits = exact or (prefixed if len(prefixed) == 1 else [])
            found = [list(row.values) for row in hits if list(row.values) == expected]
            assert found, f"{identity['id']}: no row {item['label']!r} p{item['page']} = {expected}"
            rows.append(found[0])
    for index, column in enumerate(columns):
        lhs = sum((row[index] or Decimal(0) for row in sides["lhs"]), Decimal(0))
        rhs = sum((row[index] or Decimal(0) for row in sides["rhs"]), Decimal(0))
        assert lhs == rhs
        assert lhs == Decimal(column["lhs_sum"])
        assert rhs == Decimal(column["rhs_sum"])


def _tdg_unit_rows() -> list[tuple[str, list[ExtractedLine], list[dict[str, Any]]]]:
    units = {u["kind"]: u["pages"] for u in _json(ROOT / "cases/pdf-units/TDG.json")["units"]}
    keys = _json(ROOT / "cases/statement-rows/tdg-credit-snapshot.json")["sources"]
    k24 = next(s for s in keys if s["source_id"] == "K24")
    cases = []
    for unit in k24["units"]:
        extracted = [row for page in units[unit["kind"]] for row in _rows("TDG", page)]
        cases.append((unit["kind"], extracted, unit["rows"]))
    return cases


def _match_in_order(
    extracted: list[ExtractedLine], key: list[dict[str, Any]]
) -> list[ExtractedLine | None]:
    """For each key row, the next extracted row (in page order) with the same value list."""
    matched: list[ExtractedLine | None] = []
    at = 0
    for row in key:
        hit = next(
            (
                i
                for i in range(at, len(extracted))
                if list(extracted[i].raw_values) == row["raw_values"]
            ),
            None,
        )
        matched.append(None if hit is None else extracted[hit])
        if hit is not None:
            at = hit + 1
    return matched


def test_tdg_10k_values_equal_the_statement_rows_key() -> None:
    cells = 0
    for kind, extracted, key in _tdg_unit_rows():
        for row, hit in zip(key, _match_in_order(extracted, key), strict=True):
            assert hit is not None, f"{kind} line {row['line']} {row['label']!r}: no row"
            cells += len(row["raw_values"])
    assert cells == 256


def test_tdg_10k_labels_equal_the_statement_rows_key_but_for_wrapped_labels() -> None:
    total = same = 0
    for _, extracted, key in _tdg_unit_rows():
        for row, hit in zip(key, _match_in_order(extracted, key), strict=True):
            assert hit is not None
            total += 1
            same += _norm(hit.label) == _norm(row["label"])
    assert total == 95
    assert same >= 90


_SNAPSHOT = _json(ROOT / "tests" / "czr_pdf_before.json")


@pytest.mark.parametrize("page", sorted(_SNAPSHOT))
def test_czr_pages_extract_with_their_values_unchanged(page: str) -> None:
    after = [
        {
            "line_no": row.line_no,
            "label": row.label,
            "raw_values": list(row.raw_values),
            "flags": list(row.flags),
        }
        for row in _rows("CZR", int(page[1:]))
    ]
    assert after == _SNAPSHOT[page]


def test_czr_page_61_keeps_every_value() -> None:
    before = {row["line_no"]: row["raw_values"] for row in _SNAPSHOT["p061"]}
    assert {row.line_no: list(row.raw_values) for row in _rows("CZR", 61)} == before


def _one(text: str) -> ExtractedLine:
    (line,) = extract_statement_lines(text, "page:1").lines
    return line


HEAD = "                                        Note        2025        2024\n"


@pytest.mark.parametrize("sign", ["£", "€", "$"])
def test_a_currency_sign_is_folded_like_a_dollar(sign: str) -> None:
    line = _one(f"Intangible assets       {sign}      16,423.4    {sign}     16,101.4")
    assert (line.label, line.raw_values) == ("Intangible assets", ("16,423.4", "16,101.4"))
    assert line.values == (Decimal("16423.4"), Decimal("16101.4"))


def test_a_currency_sign_attached_to_a_value_is_folded() -> None:
    line = _one("Total assets    £46,576.8   £ 46,625.8")
    assert line.raw_values == ("46,576.8", "46,625.8")


def test_a_bare_note_reference_left_of_the_values_is_dropped() -> None:
    line = _one(HEAD + "Intangible assets            6           16,423.4    16,101.4")
    assert (line.label, line.raw_values) == ("Intangible assets", ("16,423.4", "16,101.4"))
    assert line.flags == (FOOTNOTE_MARKER,)


@pytest.mark.parametrize("ref", ["7 and 9", "8, 9, 11 and 16", "5, 6"])
def test_a_multi_note_reference_is_dropped_from_label_and_values(ref: str) -> None:
    line = _one(HEAD + f"Property, plant and equipment      {ref}      10,026.6    10,006.9")
    assert (line.label, line.raw_values) == (
        "Property, plant and equipment",
        ("10,026.6", "10,006.9"),
    )


def test_a_small_first_value_is_kept_when_the_row_has_no_extra_value() -> None:
    # Guard (b): two values under two year columns; the 6 is a value (CZR p61 in the pre-flight).
    line = _one(HEAD + "Treasury shares              6           12")
    assert line.raw_values == ("6", "12")
    assert line.flags == ()


def test_a_small_first_value_is_kept_when_it_lies_right_of_the_first_year() -> None:
    # Guard (a): three values but the 6 starts under the year columns.
    line = _one(HEAD + "Item" + " " * 50 + "6        100      200")
    assert line.raw_values == ("6", "100", "200")


def test_a_multi_note_label_is_kept_when_the_row_has_no_extra_value() -> None:
    line = _one(HEAD + "Notes payable 7 and 9              100       200")
    assert (line.label, line.raw_values) == ("Notes payable 7 and 9", ("100", "200"))


@pytest.mark.parametrize("dots", ["........", ". . . . . .", "………", ".."])
def test_leader_dots_between_label_and_values_are_stripped(dots: str) -> None:
    line = _one(f"Cash and cash equivalents {dots} $ 6,261    $  3,472")
    assert (line.label, line.raw_values) == ("Cash and cash equivalents", ("6,261", "3,472"))


def test_a_decimal_point_is_not_a_leader() -> None:
    line = _one("Earnings per share          2.42        1.5")
    assert line.raw_values == ("2.42", "1.5")


@pytest.mark.parametrize(
    ("text", "raw"),
    [
        ("Net loss per share      $ (4.99) $ (5.12)", ("(4.99)", "(5.12)")),
        ("Revenue        1,200 $ 1,100", ("1,200", "1,100")),
        ("Revenue        1.5$ 1.4", ("1.5", "1.4")),
    ],
)
def test_a_dollar_stuck_after_a_digit_a_parenthesis_or_a_dot_is_split(
    text: str, raw: tuple[str, ...]
) -> None:
    assert _one(text).raw_values == raw


def test_a_dollar_after_a_word_stays_in_the_label() -> None:
    line = _one("Notes of $84 and $108       100       200")
    assert (line.label, line.raw_values) == ("Notes of $84 and $108", ("100", "200"))


def test_a_bare_small_first_value_is_kept_when_no_header_names_a_note_column() -> None:
    # CZR 10-K notes table: two columns under one year, "Net income | 21 | 15" (LINQ, Rio).
    page = "Year Ended December 31, 2023\nNet income | 21 | 15"
    (line,) = extract_statement_lines(page, "page:1").lines
    assert line.raw_values == ("21", "15")
    assert line.flags == ("more_values_than_header_years",)


def test_a_header_word_notes_right_of_the_years_is_not_a_note_column() -> None:
    page = "2026 Notes     2028 Notes\nSenior debt       5       100      200"
    (line,) = extract_statement_lines(page, "page:1").lines
    assert line.raw_values == ("5", "100", "200")


def test_leader_dots_inside_a_label_are_kept() -> None:
    line = _one("Gains... net      100      200")
    assert (line.label, line.raw_values) == ("Gains... net", ("100", "200"))


def test_a_leader_inside_a_label_is_kept_when_a_leader_precedes_the_values() -> None:
    line = _one("Gains... net ........ $ 100    $  200")
    assert (line.label, line.raw_values) == ("Gains... net", ("100", "200"))


def test_dots_between_values_are_left_as_base_read_them() -> None:
    # A nil-dots cell between values is not a leader: the row reads as it did before the change.
    assert extract_statement_lines("Other      100      ...      200", "page:1").lines == ()
    line = _one("Other      100      ...      200      300")
    assert (line.label, line.raw_values) == ("Other      100      ...", ("200", "300"))


_H2 = " " * 44 + "2025        2024\n"
_H3 = " " * 40 + "2025      2024      2023\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            _H2 + "Cash dividends declared per share ........ .25          —",
            [],
            id="dividends .25 then nil, one-space leader",
        ),
        pytest.param(
            _H2 + "Dividends per share . . . . . . . . . .25         1.00",
            [],
            id="dividends .25 then 1.00, spaced leader",
        ),
        pytest.param(
            _H2 + "Dividends per share..........25          0.20",
            [],
            id="no-space leader ..........25",
        ),
        pytest.param(
            _H3 + "Diluted earnings per share ....... .52      -       -",
            [("Diluted earnings per share ....... .52", ("-", "-"), (None, None), ())],
            id="3-year, .52 then nils",
        ),
        pytest.param(
            _H2 + "Dividends per share \u2026\u2026 .30        0.25",
            [],
            id="ellipsis char",
        ),
    ],
)
def test_a_dot_before_a_digit_is_a_decimal_point_not_a_leader(
    text: str, expected: list[Any]
) -> None:
    lines = extract_statement_lines(text, "p").lines
    assert [(x.label, x.raw_values, x.values, x.flags) for x in lines] == expected


def _note_ref_cases() -> list[Any]:
    vmo2 = (PAGES / "VMO2Q3" / "p004.txt").read_text("utf-8").rstrip("\n").split("\n")[:30]
    second = [
        "",
        " " * 150 + "2025" + " " * 16 + "2024" + " " * 16 + "2023",
        " Other financial assets" + " " * 140 + "12" + " " * 18 + "45" + " " * 18 + "67",
    ]
    flag = ("more_values_than_header_years",)
    return [
        pytest.param(
            "\n".join(vmo2 + second),
            "Other financial assets",
            (("12", "45", "67"), flag),
            id="second table below a Note statement",
        ),
        pytest.param(
            "Notes to Consolidated Financial Statements                "
            "Year Ended December 31, 2023\nNet income | 21 | 15",
            "Net income",
            (("21", "15"), flag),
            id="Notes to Consolidated title",
        ),
        pytest.param(
            "Notes payable and other borrowings outstanding as of December 31, 2025\n"
            + " " * 30
            + "Principal   Interest\nBank A"
            + " " * 28
            + "12"
            + " " * 10
            + "3",
            "Bank A",
            (("12", "3"), flag),
            id="Notes payable title",
        ),
    ]


@pytest.mark.parametrize(("text", "label", "expected"), _note_ref_cases())
def test_the_note_word_must_be_its_own_header_cell_above_the_rows(
    text: str, label: str, expected: tuple[Any, ...]
) -> None:
    rows = [x for x in extract_statement_lines(text, "p").lines if x.label.startswith(label)]
    assert [(x.raw_values, x.flags) for x in rows] == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            _H3 + "Dividends declared per share U.S.$0.25    1.00      0.80",
            [("Dividends declared per share U.S.$0.25", ("1.00", "0.80"), ())],
            id="U.S.$ label amount",
        ),
        pytest.param(
            _H3 + "Senior notes (5.5%)$500      480       460",
            [("Senior notes (5.5%)$500", ("480", "460"), ())],
            id="(rate)$ label amount",
        ),
    ],
)
def test_a_sign_after_a_label_word_or_a_non_digit_paren_is_not_split(
    text: str, expected: list[Any]
) -> None:
    lines = extract_statement_lines(text, "p").lines
    assert [(x.label, x.raw_values, x.flags) for x in lines] == expected


def test_a_line_of_many_leader_runs_is_read_in_linear_time() -> None:
    text = _H2 + "Label " + "a .. " * 16000 + "  100  200"
    start = time.perf_counter()
    extract_statement_lines(text, "p")
    assert time.perf_counter() - start < 2


_NOTE_H = " " * 40 + "Note        2025        2024\n"


def _m2_cases() -> list[Any]:
    p4 = (PAGES / "VMO2Q3" / "p004.txt").read_text("utf-8").split("\n")
    row = p4[13]
    p4[13] = row[: row.rindex("\u00a3")].rstrip()
    revenue = "Revenue" + " " * 33
    signed = ("Revenue 4", ("1,200",), ("label_ends_numeric",))
    return [
        pytest.param(_NOTE_H + revenue + "4      \u00a3 1,200", "Revenue", signed, id="GBP"),
        pytest.param(_NOTE_H + revenue + "4      \u20ac 1,200", "Revenue", signed, id="EUR"),
        pytest.param(_NOTE_H + revenue + "4      $ 1,200", "Revenue", signed, id="USD"),
        pytest.param(
            _NOTE_H + revenue + "4        1,200",
            "Revenue",
            ("Revenue", ("4", "1,200"), ()),
            id="unsigned",
        ),
        pytest.param(
            "\n".join(p4),
            "Intangible assets",
            ("Intangible assets 6", ("16,423.4",), ("label_ends_numeric",)),
            id="VMO2 p004 blank 2024",
        ),
        pytest.param(
            _NOTE_H + "Treasury shares              6           12",
            "Treasury shares",
            ("Treasury shares", ("6", "12"), ()),
            id="two unsigned values",
        ),
    ]


@pytest.mark.parametrize(("text", "label", "expected"), _m2_cases())
def test_a_note_number_before_a_signed_value_stays_in_the_label(
    text: str, label: str, expected: tuple[Any, ...]
) -> None:
    rows = [x for x in extract_statement_lines(text, "p").lines if x.label.startswith(label)]
    assert [(x.label, x.raw_values, x.flags) for x in rows] == [expected]
