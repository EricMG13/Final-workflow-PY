"""T4.8 places each construction operand by its period role, not its sign (S13 C06).

Expected columns are read off the construction by hand: 0 Full-Year Component, 1 Current Stub,
2 Prior-Year Stub.
"""

from datetime import date

import pytest
import test_statement_quantity_outputs as outputs

import deploy_vii.statement_history as history_module
from deploy_vii.canonical_tables import COLUMNS, _constructed, _keys, _stub_column
from deploy_vii.model_interface import _Tables
from deploy_vii.statement_history import statement_history


@pytest.mark.parametrize(
    ("kind", "year", "own_year", "sign", "column"),
    [
        # Q4 2024 = FY2024 - 9M YTD 2024: the same-year YTD is the current stub.
        ("FY", 2024, 2024, 1, 0),
        ("YTD", 2024, 2024, -1, 1),
        # Q2 2024 = H1 2024 - Q1 2024: both stubs of the construction's own year.
        ("QUARTER", 2024, 2024, -1, 1),
        # LTM Q1 2024 = FY2023 + Q1 YTD 2024 - Q1 PYTD 2023.
        ("FY", 2023, 2024, 1, 0),
        ("YTD", 2024, 2024, 1, 1),
        ("PYTD", 2023, 2024, -1, 2),
        ("YTD", 2023, 2024, -1, 2),
        # Trailing four quarters to Q1 2024: Q2-Q4 2023 are prior-year stubs, Q1 2024 current.
        ("QUARTER", 2023, 2024, 1, 2),
        ("QUARTER", 2024, 2024, 1, 1),
        # A missing reference has no fiscal year: the sign decides, as before.
        (None, None, 2024, -1, 2),
        (None, None, 2024, 1, 1),
    ],
)
def test_stub_column(
    kind: str | None, year: int | None, own_year: int | None, sign: int, column: int
) -> None:
    assert _stub_column(kind, year, own_year, sign) == column


def test_a_same_year_ytd_subtracted_from_the_full_year_is_the_current_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The finding's case: the TDG fixture plus a 9M YTD FY2024 period; the Q4 24 construction
    # is FY2024 - YTD9M2024, both of fiscal year 2024.
    book = outputs._book()
    fy = next(p for p in book.periods if p.period_id == "FY2024")
    assert fy.start_date is not None and fy.end_date is not None
    end = date(fy.end_date.year, 6, 29)
    ytd = fy.model_copy(
        update={
            "period_id": "YTD9M2024",
            "period_type": "YTD",
            "fiscal_quarter": 3,
            "end_date": end,
            "day_count": (end - fy.start_date).days + 1,
        }
    )
    line = next(
        item
        for item in book.statement_lines
        if item.period_id == "FY2024" and item.quantity.kind == "monetary"
    )
    extra = line.model_copy(
        update={
            "line_id": line.line_id + ":ytd",
            "period_id": "YTD9M2024",
            "value": line.value.model_copy(
                update={"observation_id": line.value.observation_id + ":ytd"}
            ),
        }
    )
    book = book.model_copy(
        update={"periods": (*book.periods, ytd), "statement_lines": (*book.statement_lines, extra)}
    )
    pack, review = outputs._pack_and_review(book)
    report = outputs._report(book, pack, review)
    monkeypatch.setattr(history_module, "statement_report", lambda *_args: report)
    history = statement_history(pack, review, book.book_id)
    tables = _Tables(book, schemas={k: (t, None, _keys(k)) for k, (t, _) in COLUMNS.items()})
    _constructed(tables, history)

    rows: dict[str, dict[str, str | None]] = {}
    for fact in tables.facts:
        if fact.table_id == "T4.8":
            rows.setdefault(fact.row_id, {})[fact.field] = fact.text
    q4 = [r for r in rows.values() if r["field_1"] == "QUARTER" and r["field_2"]]
    assert q4
    for row in q4:
        assert (row["field_2"] or "").startswith("+1 * FY2024:")
        assert (row["field_3"] or "").startswith("-1 * YTD9M2024:")
        assert row["field_4"] is None
