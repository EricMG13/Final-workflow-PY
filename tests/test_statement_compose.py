"""The statement composer writes the statement lines from a mapped unit (CP1H-R23, T21a).

Answer keys (read, never written):
- ``cases/statement-rows/shc-earnings-update.json``: the printed cells of every SHC row;
- ``cases/column-periods/SHC.json`` (F1): the oracle period of each unit column;
- ``cases/statement-coverage/``: the three live payloads whose declared periods and per-row
  judgment fields give the row maps, and the frozen line counts 240 / 369 / 280 (measured
  independently in preflight-d4 p5);
- ``cases/pdf-identities/<DOC>.json`` (F1) on ``tests/fixtures/pdf_pages``.

The composer's inputs are built here the way the model would send them: the column map matches
each oracle column to the payload's declared period with the same end and kind, the row map is
the payload's own judgment fields for a row it cites (a row it never cites gets a plain
`other:` mapping, as the model would be asked to give it).
"""

import json
import re
from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_cp1_coverage_gate as gate
from czr_runs import make_pack

from deploy_vii.contracts import Span
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.financial_contracts import StatementLine
from deploy_vii.statement_extract import (
    ExtractedLine,
    ExtractedTable,
    extract_statement_lines,
)
from deploy_workflow import financial_workflow as fw
from deploy_workflow import statement_compose as sc
from deploy_workflow.statement_lines import line_table

REPO = Path(__file__).resolve().parents[1]
ROWS = json.loads((REPO / "cases/statement-rows/shc-earnings-update.json").read_text("utf-8"))
ORACLE = json.loads((REPO / "cases/column-periods/SHC.json").read_text("utf-8"))
PAGES = REPO / "tests" / "fixtures" / "pdf_pages"
FLOW_TYPE = {"quarter": "QUARTER", "half": "YTD", "year": "FY"}
CASES = [  # one value per case: (run, submission, stored payload, frozen line count)
    pytest.param(
        (gate.RUN3, "shc-seq7-submission.json", "shc-seq7-stored.json", 236), id="run3-seq7"
    ),
    pytest.param((gate.RUN3, "shc-seq6-submission.json", None, 363), id="run3-seq6"),
    pytest.param(
        (gate.RUN4, "shc-run4-seq6-submission.json", "shc-run4-seq6-stored.json", 274),
        id="run4-seq6",
    ),
]


# ---- the keys, as composer inputs -----------------------------------------------------------


def _independent_amount(raw: str) -> Decimal:
    """The key cell read without the code's parser: a nil dash is 0, parentheses negate."""
    if raw in ("—", "–", "-"):
        return Decimal(0)
    sign = -1 if raw.startswith("(") else 1
    return sign * Decimal(raw.strip("()$").replace(",", ""))


def _units(tables: Sequence[ExtractedTable]) -> list[dict[str, Any]]:
    """Every key unit joined, by source and unit locator, to the extractor's real table of it
    (flags and all). The key stays the answer: `key_rows` holds its cells by row locator."""
    real = {(table.source_id, table.locator): table for table in tables}
    units = []
    for source in ROWS["sources"]:
        for unit in source["units"]:
            locator = f"{unit['start']}-{unit['end'].removeprefix('line:')}"
            oracle = ORACLE[f"{source['source_id']}|{unit['kind']}|{unit['start']}-{unit['end']}"]
            units.append(
                {
                    "source_id": source["source_id"],
                    "kind": unit["kind"],
                    "locator": locator,
                    "table": real[(source["source_id"], locator)],
                    "key_rows": {f"line:{row['line']}": row for row in unit["rows"]},
                    "columns": [c["period"] for c in oracle["columns"]],
                }
            )
    return units


def _book_columns(
    unit: dict[str, Any], periods: list[dict[str, Any]], own: set[str]
) -> list[str | None]:
    """The model's column map for one book: per oracle column the declared period with the same
    end and kind (a flow also the same start); a balance date shared by several periods takes
    PERIOD_END, else the period the payload's own lines of the unit use, else the first declared;
    None where none matches."""
    mapped: list[str | None] = []
    for period in unit["columns"]:
        found = [
            p
            for p in periods
            if p["end_date"] == period["end"]
            and (
                period["kind"] == "instant"
                or (
                    p["start_date"] == period["start"]
                    and p["period_type"] == FLOW_TYPE[period["kind"]]
                )
            )
        ]
        pick = (
            [p for p in found if p["period_type"] == "PERIOD_END"]
            or [p for p in found if p["period_id"] in own]
            or found
        )
        mapped.append(pick[0]["period_id"] if pick else None)
    return mapped


def _compose_payload(
    payload: dict[str, Any], tables: Sequence[ExtractedTable]
) -> list[dict[str, Any]]:
    """Compose every unit in the book that owns it: the first book citing one of the unit's rows,
    else the first book with a column that maps. Returns, per composed unit, the book, the unit,
    the column map and the composition. `tables` are the extractor's own (`Replay.tables()`)."""
    books = payload["financial"]["books"]
    sha = {s["source_id"]: s["converted_sha256"] for s in ROWS["sources"]}
    cited = {
        book["book_id"]: {
            (c["source_id"], c["locator"]): line
            for line in reversed(book["statement_lines"])
            for c in line["value"]["citations"]
        }
        for book in books
    }
    out = []
    for unit in _units(tables):
        keys = [(unit["source_id"], row.locator) for row in unit["table"].lines]
        owner = next(
            (b for b in books if any(k in cited[b["book_id"]] for k in keys)),
            next((b for b in books if any(_book_columns(unit, b["periods"], set()))), None),
        )
        if owner is None:
            continue
        book_cited = cited[owner["book_id"]]
        own = {book_cited[k]["period_id"] for k in keys if k in book_cited}
        columns = _book_columns(unit, owner["periods"], own)
        row_map = {}
        for row in unit["table"].lines:
            line = book_cited.get((unit["source_id"], row.locator))
            row_map[row.line_no] = (
                sc.RowJudgment(
                    line["line_id"], line["item_id"], line["line_kind"], line["sign_convention"]
                )
                if line
                else sc.RowJudgment(f"r{row.line_no}", f"other:r{row.line_no}", "detail", "signed")
            )
        composition = sc.compose_unit(
            unit["table"],
            source_id=unit["source_id"],
            source_sha256=sha[unit["source_id"]],
            unit_locator=unit["locator"],
            kind=unit["kind"],
            column_periods=columns,
            row_map=row_map,
            declared_periods=[p["period_id"] for p in owner["periods"]],
        )
        out.append(
            {"book": owner, "unit": unit, "columns": columns, "composition": composition}
        )
    return out


def _payload(replay: gate.Replay) -> dict[str, Any]:
    return json.loads(replay.payload)  # type: ignore[no-any-return]


@pytest.fixture
def replay(tmp_path: Path, request: pytest.FixtureRequest) -> gate.Replay:
    run, submission, stored, _ = request.param
    return gate.Replay(tmp_path, run, submission, stored)


# ---- (a) line by line against the key -------------------------------------------------------


# The key rows the extractor flags `label_ends_numeric`; R23.3 leaves them to the model.
FLAGGED_ROWS = {
    (gate.Q10, "line:33-81", 74),
    (gate.Q10, "line:33-81", 75),
    (gate.K10, "line:217-266", 258),
    (gate.K10, "line:217-266", 259),
}
UNCOVERED = {  # by submission: the payload's own lines cover the four rows in seq 7 only
    "shc-seq7-submission.json": set(),
    "shc-seq6-submission.json": FLAGGED_ROWS,
    "shc-run4-seq6-submission.json": FLAGGED_ROWS,
}


@pytest.mark.parametrize("replay", CASES, indirect=True)
def test_every_composed_line_is_a_cell_of_the_key_under_its_oracle_period(
    replay: gate.Replay, request: pytest.FixtureRequest
) -> None:
    expected = request.node.callspec.params["replay"][3]
    composed = _compose_payload(_payload(replay), replay.tables())
    total = 0
    left = set()
    for item in composed:
        unit, columns, composition = item["unit"], item["columns"], item["composition"]
        assert composition.issues == ()
        assert {r.reason for r in composition.left_to_model} <= {sc.FLAGGED}
        left |= {(unit["source_id"], unit["locator"], r.line_no) for r in composition.left_to_model}
        periods = {p["period_id"]: p for p in item["book"]["periods"]}
        for line in composition.lines:
            total += 1
            (cite,) = line.value.citations
            row = unit["key_rows"][cite.locator]
            column = columns.index(line.period_id)  # the map names each period once
            oracle = unit["columns"][column]
            assert cite.source_id == unit["source_id"]
            assert cite.quote == row["label"]
            assert line.label == row["label"]
            assert line.statement == unit["kind"]
            assert line.value.amount == _independent_amount(row["raw_values"][column])
            assert periods[line.period_id]["end_date"] == oracle["end"]
            if oracle["kind"] != "instant":
                assert periods[line.period_id]["start_date"] == oracle["start"]
    assert total == expected
    assert left == FLAGGED_ROWS


# ---- (b) through the real gate --------------------------------------------------------------


@pytest.mark.parametrize("replay", CASES, indirect=True)
def test_only_the_rows_left_to_the_model_are_uncovered_through_the_real_gate(
    replay: gate.Replay, request: pytest.FixtureRequest
) -> None:
    payload = _payload(replay)
    composed = _compose_payload(payload, replay.tables())
    for book in payload["financial"]["books"]:
        own = [c for c in composed if c["book"]["book_id"] == book["book_id"]]
        left = {
            (c["unit"]["source_id"], r.locator)
            for c in own
            for r in c["composition"].left_to_model
        }
        kept = [
            line
            for line in book["statement_lines"]
            if any((c["source_id"], c["locator"]) in left for c in line["value"]["citations"])
        ]
        book["statement_lines"] = [
            *(line.model_dump(mode="json") for c in own for line in c["composition"].lines),
            *kept,
        ]
    text = json.dumps(payload)
    FinancialSubmission.model_validate_json(text)  # else the gate returns early
    issues = replay.issues(text)
    uncovered = set()
    for issue in gate._uncovered(issues):
        found = re.match(rf"{gate.PREFIX}(\S+) (\S+) line (\d+)", issue)
        assert found, issue
        uncovered.add((found[1], found[2], int(found[3])))
    submission = request.node.callspec.params["replay"][1]
    assert uncovered == UNCOVERED[submission]  # each is a left-to-model row (FLAGGED_ROWS)
    assert not [i for i in issues if gate.UNMEASURED in i or gate.NOT_EXTRACTED in i]


# ---- (c) the checks, on PDF pages ------------------------------------------------------------


def _page(doc: str, number: int) -> tuple[ExtractedTable, str]:
    manifest = json.loads((PAGES / doc / "manifest.json").read_text("utf-8"))
    text = (PAGES / doc / f"p{number:03d}.txt").read_text("utf-8")
    table = extract_statement_lines(text, f"page:{number}", manifest["source_name"])
    return table, manifest["source_sha256"]


def _identity(doc: str, name: str) -> dict[str, Any]:
    data = json.loads((REPO / "cases/pdf-identities" / f"{doc}.json").read_text("utf-8"))
    return next(i for i in data["identities"] if i["id"] == name)


def _row(table: ExtractedTable, member: dict[str, Any]) -> ExtractedLine:
    """The one row of the page that the identity member names, with its printed cells."""
    (row,) = [r for r in table.lines if r.label.rstrip(" .").strip() == member["label"]]
    assert list(row.raw_values) == member["printed"]
    return row


def _map(
    table: ExtractedTable, identity: dict[str, Any], items: Sequence[str]
) -> dict[int, sc.RowJudgment]:
    members = [*identity["lhs"], *identity["rhs"]]
    assert len(members) == len(items)
    return {
        _row(table, m).line_no: sc.RowJudgment(f"l{n}", item, "total", "signed")
        for n, (m, item) in enumerate(zip(members, items, strict=True))
    }


def _compose(
    table: ExtractedTable,
    sha: str,
    kind: sc.Kind,
    columns: list[str | None],
    row_map: dict[int, sc.RowJudgment],
) -> sc.Composition:
    return sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=sha,
        unit_locator=table.locator,
        kind=kind,
        column_periods=columns,
        row_map=row_map,
        declared_periods=["fy2024", "fy2023", "fy2022"],
    )


def _bumped(table: ExtractedTable, row: ExtractedLine, column: int) -> ExtractedTable:
    """A copy of the table with one printed cell of one row raised by 1."""
    values = list(row.values)
    values[column] = (values[column] or Decimal(0)) + 1
    raw = list(row.raw_values)
    raw[column] = str(values[column])
    changed = replace(row, values=tuple(values), raw_values=tuple(raw))
    return replace(table, lines=tuple(changed if r is row else r for r in table.lines))


TDG_CFS = (sc.OPERATING, sc.INVESTING, sc.FINANCING, sc.FX_EFFECT, sc.NET_CHANGE)
CZR_BS = (sc.TOTAL_ASSETS, sc.TOTAL_LIABILITIES, sc.TOTAL_EQUITY, sc.TOTAL_LIABILITIES_AND_EQUITY)


def _czr() -> tuple[ExtractedTable, str, dict[int, sc.RowJudgment]]:
    table, sha = _page("CZR", 56)
    one, two = _identity("CZR", "CZR-BS-1"), _identity("CZR", "CZR-BS-2")
    row_map = _map(table, one, CZR_BS[:3])
    row_map |= {
        _row(table, two["rhs"][0]).line_no: sc.RowJudgment("l9", CZR_BS[3], "total", "signed")
    }
    return table, sha, row_map


def test_a_balanced_balance_sheet_with_identified_totals_composes_and_both_checks_ran() -> None:
    table, sha, row_map = _czr()
    result = _compose(table, sha, "BS", ["fy2024", "fy2023"], row_map)
    assert result.issues == ()
    assert result.checks_applied == (sc.BS_LIABILITIES_PLUS_EQUITY, sc.BS_PRINTED_TOTAL)
    assert result.checks_not_applied == ()
    assert len(result.lines) == 4 * 2  # four mapped rows, two columns


@pytest.mark.parametrize("column", [0, 1])
def test_a_balance_sheet_total_changed_by_one_fails_both_checks_and_composes_nothing(
    column: int,
) -> None:
    table, sha, row_map = _czr()
    assets = next(r for r in table.lines if r.label == "Total assets")
    result = _compose(_bumped(table, assets, column), sha, "BS", ["fy2024", "fy2023"], row_map)
    assert result.lines == ()
    assert [i.check for i in result.issues] == [sc.BS_LIABILITIES_PLUS_EQUITY, sc.BS_PRINTED_TOTAL]
    for issue in result.issues:
        printed = assets.values[column]
        assert issue.column == column
        assert issue.period_id == ["fy2024", "fy2023"][column]
        assert issue.lhs == (printed or 0) + 1
        assert issue.rhs == printed
        assert issue.check in issue.message and f"column {column}" in issue.message
    failed = [r for r in result.left_to_model if r.reason == sc.UNIT_CHECK_FAILED]
    assert {r.line_no for r in failed} == set(row_map)  # every mapped row goes back
    assert {r.reason for r in result.left_to_model} == {sc.UNIT_CHECK_FAILED, sc.NOT_IN_ROW_MAP}


def test_a_cash_flow_statement_with_identified_sections_composes() -> None:
    table, sha = _page("TDG", 109)
    row_map = _map(table, _identity("TDG", "TDG-CFS-1"), TDG_CFS)
    result = _compose(table, sha, "CFS", ["fy2024", "fy2023", "fy2022"], row_map)
    assert result.issues == ()
    assert result.checks_applied == (sc.CFS_NET_CHANGE,)
    assert len(result.lines) == 5 * 3


@pytest.mark.parametrize("column", [0, 1, 2])
def test_a_net_change_raised_by_one_fails_the_cash_flow_check_naming_the_column(
    column: int,
) -> None:
    table, sha = _page("TDG", 109)
    row_map = _map(table, _identity("TDG", "TDG-CFS-1"), TDG_CFS)
    net = next(r for r in table.lines if r.label.startswith("NET INCREASE (DECREASE)"))
    columns: list[str | None] = ["fy2024", "fy2023", "fy2022"]
    result = _compose(_bumped(table, net, column), sha, "CFS", columns, row_map)
    assert result.lines == ()
    (issue,) = result.issues
    assert issue.check == sc.CFS_NET_CHANGE
    assert issue.column == column
    assert issue.period_id == columns[column]
    assert issue.lhs == net.values[column]
    assert issue.rhs == (net.values[column] or 0) + 1
    assert "column" in issue.message and sc.CFS_NET_CHANGE in issue.message


def test_a_none_column_is_not_checked_and_gets_no_line() -> None:
    table, sha = _page("TDG", 109)
    row_map = _map(table, _identity("TDG", "TDG-CFS-1"), TDG_CFS)
    net = next(r for r in table.lines if r.label.startswith("NET INCREASE (DECREASE)"))
    result = _compose(_bumped(table, net, 0), sha, "CFS", [None, "fy2023", "fy2022"], row_map)
    assert result.issues == ()
    assert len(result.lines) == 5 * 2
    assert {line.period_id for line in result.lines} == {"fy2023", "fy2022"}


def test_unidentified_totals_compose_and_the_unapplied_checks_are_named() -> None:
    table, sha = _page("CZR", 56)
    cash = next(r for r in table.lines if r.label == "Cash and cash equivalents")
    row_map = {cash.line_no: sc.RowJudgment("cash", "cash_and_equivalents", "detail", "signed")}
    result = _compose(table, sha, "BS", ["fy2024", "fy2023"], row_map)
    assert result.issues == () and result.checks_applied == ()
    assert [name for name, _ in result.checks_not_applied] == [
        sc.BS_LIABILITIES_PLUS_EQUITY,
        sc.BS_PRINTED_TOTAL,
    ]
    assert all("item_id" in why for _, why in result.checks_not_applied)
    assert len(result.lines) == 2


def test_a_total_named_by_two_rows_is_not_checked() -> None:
    table, sha, row_map = _czr()
    cash = next(r for r in table.lines if r.label == "Cash and cash equivalents")
    row_map[cash.line_no] = sc.RowJudgment("cash", sc.TOTAL_ASSETS, "total", "signed")
    result = _compose(table, sha, "BS", ["fy2024", "fy2023"], row_map)
    assert result.issues == ()
    assert {name for name, _ in result.checks_not_applied} == {
        sc.BS_LIABILITIES_PLUS_EQUITY,
        sc.BS_PRINTED_TOTAL,
    }
    assert all("more than one row" in why for _, why in result.checks_not_applied)


# ---- (d) what is left to the model, and the line fields ---------------------------------------


def _table() -> ExtractedTable:
    table, _ = _page("TDG", 109)
    return table


def _judge(row: ExtractedLine) -> sc.RowJudgment:
    return sc.RowJudgment(f"n{row.line_no}", f"other:n{row.line_no}", "detail", "signed")


def test_flagged_count_mismatch_unmapped_and_missing_rows_are_left_to_the_model() -> None:
    table = _table()
    first, second, third, fourth, *rest = table.lines
    flagged = replace(first, flags=("label_ends_numeric",))
    short = replace(second, raw_values=second.raw_values[:2], values=second.values[:2])
    table = replace(table, lines=(flagged, short, third, fourth, *rest))
    row_map = {r.line_no: _judge(r) for r in (flagged, short, third)}
    row_map[999] = _judge(first)
    result = _compose(table, "0" * 64, "CFS", ["fy2024", "fy2023", "fy2022"], row_map)
    left = {r.line_no: r for r in result.left_to_model}
    assert left[flagged.line_no].reason == sc.FLAGGED
    assert left[flagged.line_no].detail == "label_ends_numeric"
    assert left[short.line_no].reason == sc.VALUE_COUNT
    assert "2 values" in left[short.line_no].detail and "3 columns" in left[short.line_no].detail
    assert left[fourth.line_no].reason == sc.NOT_IN_ROW_MAP
    assert left[999].reason == sc.NO_SUCH_ROW and left[999].locator == ""
    assert {r.line_no for r in result.left_to_model if r.reason == sc.NOT_IN_ROW_MAP} == {
        r.line_no for r in (fourth, *rest)
    }
    composed = {line.value.citations[0].locator for line in result.lines}
    assert composed == {third.locator}
    assert len(result.lines) == 3


def test_a_line_carries_the_printed_cell_the_row_locator_and_the_row_order() -> None:
    table, sha = _page("TDG", 109)
    discontinued = next(r for r in table.lines if r.label.startswith("Income from discontinued"))
    judgment = sc.RowJudgment("disc", "other:discontinued", "detail", "signed")
    result = sc.compose_unit(
        table,
        source_id="tdg",
        source_sha256=sha,
        unit_locator="page:109",
        kind="CFS",
        column_periods=["fy2024", None, "fy2022"],
        row_map={discontinued.line_no: judgment},
        declared_periods=["fy2024", "fy2023", "fy2022"],
        priority_offset=100,
    )
    first, last = result.lines
    assert isinstance(first, StatementLine)
    assert (first.period_id, first.value.amount) == ("fy2024", Decimal(0))  # a nil dash
    assert (last.period_id, last.value.amount) == ("fy2022", Decimal(-1))
    position = table.lines.index(discontinued) + 1
    assert first.display_priority == last.display_priority == 100 + position
    assert first.statement == "CFS" and first.label == discontinued.label
    assert (first.line_id, first.item_id) == ("disc", "other:discontinued")
    assert first.value.observation_id == "disc.fy2024"
    assert last.value.observation_id == "disc.fy2022"
    (cite,) = first.value.citations
    assert (cite.source_id, cite.locator, cite.quote) == ("tdg", "page:109", discontinued.label)
    assert cite.source_sha256 == sha


def test_an_outflow_magnitude_row_cites_itself_for_the_sign() -> None:
    table, sha = _page("TDG", 109)
    capex = next(r for r in table.lines if r.label.startswith("Capital expenditures"))
    row_map = {capex.line_no: sc.RowJudgment("capex", "capex_total", "detail", "outflow_magnitude")}
    result = _compose(table, sha, "CFS", ["fy2024", "fy2023", "fy2022"], row_map)
    assert len(result.lines) == 3
    for line in result.lines:
        assert line.sign_citations == line.value.citations != ()


def _magnitude_cfs(lines: Sequence[str], signs: Sequence[str]) -> sc.Composition:
    """A two-year CFS page whose rows 3-6 are operating, investing, financing and net change,
    mapped as totals with the given sign conventions (S11 C05)."""
    page = ["CONSOLIDATED STATEMENTS OF CASH FLOWS", "2024 2023", *lines]
    spans = {i: Span(locator=f"line:{i}", text=text) for i, text in enumerate(page, 1)}
    table = line_table(spans, f"line:1-{len(page)}", "s")
    items = (sc.OPERATING, sc.INVESTING, sc.FINANCING, sc.NET_CHANGE)
    row_map = {
        row.line_no: sc.RowJudgment(f"l{row.line_no}", item, "total", sign)
        for row, item, sign in zip(table.lines, items, signs, strict=True)
    }
    return _compose(table, "0" * 64, "CFS", ["fy2024", "fy2023"], row_map)


MAGNITUDES = (
    "Net cash provided by operating activities 400 300",
    "Net cash used in investing activities 250 200",
    "Net cash used in financing activities 100 50",
    "Net increase in cash 50 50",
)


@pytest.mark.parametrize(
    "lines,signs",
    [
        # By hand: 400 - 250 - 100 = 50 and 300 - 200 - 50 = 50, the printed net change.
        (MAGNITUDES, ("signed", "outflow_magnitude", "outflow_magnitude", "signed")),
        # A printed (250) under outflow_magnitude is still read as -abs: 400 - 250 - 100 = 50.
        (
            (MAGNITUDES[0], "Net cash used in investing activities (250) (200)", *MAGNITUDES[2:]),
            ("signed", "outflow_magnitude", "outflow_magnitude", "signed"),
        ),
        # A net decrease printed as a magnitude: 100 - 250 + 100 = -50 = -abs(50); 300 - 200
        # - 150 = -50.
        (
            (
                "Net cash provided by operating activities 100 300",
                MAGNITUDES[1],
                "Net cash provided by financing activities 100 (150)",
                "Net decrease in cash 50 50",
            ),
            ("signed", "outflow_magnitude", "signed", "outflow_magnitude"),
        ),
    ],
)
def test_the_cash_flow_check_reads_outflow_magnitudes_as_negative(lines, signs) -> None:
    result = _magnitude_cfs(lines, signs)
    assert result.issues == ()
    assert result.checks_applied == (sc.CFS_NET_CHANGE,)
    assert len(result.lines) == 8
    # The lines keep the printed cell; only the check reads it as -abs.
    investing = [line.value.amount for line in result.lines if line.item_id == sc.INVESTING]
    assert [abs(a) for a in investing] == [Decimal(250), Decimal(200)]


def test_magnitudes_mapped_as_signed_still_fail_the_cash_flow_check() -> None:
    # By hand: 400 + 250 + 100 = 750 != 50 in fy2024 (300 + 200 + 50 = 550 != 50 in fy2023).
    result = _magnitude_cfs(MAGNITUDES, ("signed",) * 4)
    assert [(i.check, i.period_id, i.lhs, i.rhs) for i in result.issues] == [
        (sc.CFS_NET_CHANGE, "fy2024", Decimal(750), Decimal(50)),
        (sc.CFS_NET_CHANGE, "fy2023", Decimal(550), Decimal(50)),
    ]
    assert result.lines == ()


def test_a_balance_sheet_outflow_magnitude_and_a_malformed_entry_are_refused_per_row() -> None:
    table, sha = _page("CZR", 56)
    cash, restricted = table.lines[0], table.lines[1]
    row_map = {
        cash.line_no: sc.RowJudgment("cash", "cash_and_equivalents", "detail", "outflow_magnitude"),
        restricted.line_no: sc.RowJudgment("bad id", "restricted_cash", "detail", "signed"),
    }
    result = _compose(table, sha, "BS", ["fy2024", "fy2023"], row_map)
    assert result.lines == ()
    assert {r.reason for r in result.left_to_model if r.line_no in row_map} == {sc.REFUSED}


def test_a_column_mapped_to_an_undeclared_period_gets_no_line_and_is_reported() -> None:
    table, sha = _page("CZR", 56)
    cash = table.lines[0]
    result = _compose(table, sha, "BS", ["fy2024", "fy2099"], {cash.line_no: _judge(cash)})
    assert result.undeclared == ((1, "fy2099"),)
    assert [line.period_id for line in result.lines] == ["fy2024"]


def test_a_column_map_that_repeats_a_period_composes_nothing() -> None:
    table, sha = _page("CZR", 56)
    cash = table.lines[0]
    result = _compose(table, sha, "BS", ["fy2024", "fy2024"], {cash.line_no: _judge(cash)})
    assert result.lines == ()
    (issue,) = result.issues
    assert issue.check == sc.COLUMN_MAP_DISTINCT and issue.period_id == "fy2024"
    assert {r.reason for r in result.left_to_model} == {sc.UNIT_CHECK_FAILED}


def test_a_row_map_entry_without_four_fields_stays_with_the_model_and_raises_nothing() -> None:
    table, sha = _page("CZR", 56)
    cash, restricted = table.lines[0], table.lines[1]
    short = ("cash", "cash_and_equivalents", "detail")  # three fields, not four
    row_map: dict[int, Any] = {cash.line_no: short, restricted.line_no: _judge(restricted)}
    result = _compose(table, sha, "BS", ["fy2024", "fy2023"], row_map)
    (bad,) = [r for r in result.left_to_model if r.line_no == cash.line_no]
    assert bad.reason == sc.BAD_ENTRY
    assert "missing 1 required positional argument: 'sign_convention'" in bad.detail
    assert {line.value.citations[0].locator for line in result.lines} == {restricted.locator}
    assert len(result.lines) == 2


# ---- (d) rows whose caption names another statement (CP1H-R23.22) ----------------------------


def test_a_row_under_another_statements_caption_is_left_and_the_rest_compose() -> None:
    table = _table()
    first, second, *rest = table.lines
    result = sc.compose_unit(
        table,
        source_id="doc",
        source_sha256="0" * 64,
        unit_locator=table.locator,
        kind="CFS",
        column_periods=["fy2024", "fy2023", "fy2022"],
        row_map={r.line_no: _judge(r) for r in table.lines},
        declared_periods=["fy2024", "fy2023", "fy2022"],
        other_rows={first.line_no: "BS"},
    )
    (left,) = result.left_to_model
    assert (left.line_no, left.reason) == (first.line_no, sc.OTHER_STATEMENT)
    assert left.detail == (
        "its caption names BS, not this unit's CFS; "
        "Python writes no line for it and coverage does not require it"
    )
    composed = {line.value.citations[0].locator for line in result.lines}
    assert composed == {r.locator for r in (second, *rest)}


def test_the_cash_reconciliation_rows_of_a_cash_flow_page_are_found_as_balance_sheet_rows() -> None:
    pack = make_pack()
    tenk, tenq = "czr-fy2025-10k", "czr-q2-2026-10q"
    spans = {(s.source_id, sp.locator): sp.text for s in pack.sources for sp in s.spans}
    tables = [
        extract_statement_lines(spans[(source, f"page:{page}")], f"page:{page}", source)
        for source, page in ((tenk, 61), (tenq, 10))
    ]
    found = fw._other_statement_rows(pack, (tenk, tenq), tables)
    assert found == {
        (tenk, "page:61"): {4: "BS", 5: "BS", 6: "BS", 7: "BS"},
        (tenq, "page:10"): {4: "BS", 5: "BS", 6: "BS", 7: "BS"},
    }


# ---- (e) a unit read by OCR composes only when its arithmetic check passed (CP1H-R23.23) ------

OCR_DETAIL = (
    "the page was read by OCR and Python could not verify this unit (its arithmetic checks or "
    "its period header); Python writes no line for it and coverage does not require it"
)


def _ocr(
    table: ExtractedTable,
    sha: str,
    kind: sc.Kind,
    columns: list[str | None],
    row_map: dict[int, sc.RowJudgment],
    *,
    ocr: bool,
) -> sc.Composition:
    return sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=sha,
        unit_locator=table.locator,
        kind=kind,
        column_periods=columns,
        row_map=row_map,
        declared_periods=["fy2024", "fy2023", "fy2022"],
        ocr=ocr,
    )


def test_an_ocr_income_unit_has_no_check_and_leaves_every_mapped_row_to_the_model() -> None:
    table, sha = _page("TDG", 109)
    columns: list[str | None] = ["fy2024", "fy2023", "fy2022"]
    row_map = {r.line_no: _judge(r) for r in table.lines[:6]}
    plain = _ocr(table, sha, "IS", columns, row_map, ocr=False)
    assert plain.lines and plain.checks_applied == ()  # an IS unit has no check
    result = _ocr(table, sha, "IS", columns, row_map, ocr=True)
    assert result.lines == ()
    composed = set(row_map) - {item.line_no for item in plain.left_to_model}
    assert composed
    held = {item.line_no: item for item in result.left_to_model}
    for number in composed:
        assert (held[number].reason, held[number].detail) == (sc.OCR_UNCHECKED, OCR_DETAIL)
    assert sc.OCR_UNCHECKED == "ocr_unchecked"
    for item in plain.left_to_model:  # rows already left keep their own reason
        assert held[item.line_no] == item
    assert len(result.left_to_model) == len(plain.left_to_model) + len(composed)
    assert result.issues == plain.issues


def test_an_ocr_balance_sheet_that_passed_its_check_composes_as_without_ocr() -> None:
    table, sha, row_map = _czr()
    columns: list[str | None] = ["fy2024", "fy2023"]
    plain = _ocr(table, sha, "BS", columns, row_map, ocr=False)
    assert plain.checks_applied and plain.lines
    result = _ocr(table, sha, "BS", columns, row_map, ocr=True)
    assert result.lines == plain.lines
    assert result.left_to_model == plain.left_to_model
    assert result.checks_applied == plain.checks_applied


def test_an_ocr_balance_sheet_whose_header_does_not_verify_the_map_composes_nothing() -> None:
    table, sha, row_map = _czr()
    columns: list[str | None] = ["fy2024", "fy2023"]
    kept = sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=sha,
        unit_locator=table.locator,
        kind="BS",
        column_periods=columns,
        row_map=row_map,
        declared_periods=["fy2024", "fy2023"],
        ocr=True,
        ocr_verified=True,
    )
    assert kept.lines
    result = sc.compose_unit(
        table,
        source_id="doc",
        source_sha256=sha,
        unit_locator=table.locator,
        kind="BS",
        column_periods=columns,
        row_map=row_map,
        declared_periods=["fy2024", "fy2023"],
        ocr=True,
        ocr_verified=False,
    )
    assert result.lines == ()
    held = {i.line_no: i for i in result.left_to_model if i.reason == sc.OCR_UNCHECKED}
    assert set(held) == set(row_map)
    assert {i.detail for i in held.values()} == {OCR_DETAIL}


def test_an_ocr_unit_with_a_check_not_applied_leaves_its_rows_to_the_model() -> None:
    table, sha = _page("CZR", 56)
    cash = next(r for r in table.lines if r.label == "Cash and cash equivalents")
    row_map = {cash.line_no: sc.RowJudgment("cash", "cash_and_equivalents", "detail", "signed")}
    columns: list[str | None] = ["fy2024", "fy2023"]
    assert _ocr(table, sha, "BS", columns, row_map, ocr=False).lines
    result = _ocr(table, sha, "BS", columns, row_map, ocr=True)
    assert result.lines == ()
    held = {item.line_no: item for item in result.left_to_model}
    assert (held[cash.line_no].reason, held[cash.line_no].detail) == (sc.OCR_UNCHECKED, OCR_DETAIL)


def test_an_ocr_balance_sheet_with_a_check_applied_and_one_not_applied_composes_nothing() -> None:
    printed = [
        "CONSOLIDATED BALANCE SHEETS",
        "                                        2024        2023",
        "Cash                                     100          90",
        "Total assets                             100          90",
        "Accounts payable                          40          30",
        "Total liabilities and equity             100          90",
    ]
    page = "\n".join(printed)
    table = extract_statement_lines(page, "page:2", "doc")
    items = {
        "Cash": "cash_and_equivalents",
        "Total assets": "total_assets",
        "Accounts payable": "accounts_payable",
        "Total liabilities and equity": sc.TOTAL_LIABILITIES_AND_EQUITY,
    }
    row_map = {
        r.line_no: sc.RowJudgment(f"n{r.line_no}", items[r.label], "detail", "signed")
        for r in table.lines
    }
    columns: list[str | None] = ["fy2024", "fy2023"]
    plain = _ocr(table, "0" * 64, "BS", columns, row_map, ocr=False)
    assert plain.lines and plain.checks_applied and plain.checks_not_applied
    result = _ocr(table, "0" * 64, "BS", columns, row_map, ocr=True)
    assert result.lines == ()
    unchecked = {i.line_no for i in result.left_to_model if i.reason == sc.OCR_UNCHECKED}
    assert unchecked == set(row_map)


def test_an_ocr_unit_whose_checked_totals_are_all_nil_in_a_column_composes_nothing() -> None:
    table, sha, row_map = _czr()
    totals = (
        sc.TOTAL_ASSETS,
        sc.TOTAL_LIABILITIES,
        sc.TOTAL_EQUITY,
        sc.TOTAL_LIABILITIES_AND_EQUITY,
    )
    nil = table
    for number, judgment in row_map.items():
        if judgment.item_id in totals:
            row = next(r for r in nil.lines if r.line_no == number)
            changed = replace(
                row, values=(row.values[0], None), raw_values=(row.raw_values[0], "—")
            )
            nil = replace(nil, lines=tuple(changed if r is row else r for r in nil.lines))
    columns: list[str | None] = ["fy2024", "fy2023"]
    plain = _ocr(nil, sha, "BS", columns, row_map, ocr=False)
    assert plain.issues == () and {line.period_id for line in plain.lines} == set(columns)
    result = _ocr(nil, sha, "BS", columns, row_map, ocr=True)
    assert result.lines == ()
    assert {i.reason for i in result.left_to_model if i.line_no in row_map} >= {sc.OCR_UNCHECKED}


def test_a_zero_outflow_magnitude_row_adds_nothing_to_a_failing_check() -> None:
    # S11-C05 adversarial. By hand: 400 + (-0) - 100 = 300 != 50 and 300 + 0 - 50 = 250 != 50.
    lines = (MAGNITUDES[0], "Net cash used in investing activities 0 0", *MAGNITUDES[2:])
    result = _magnitude_cfs(lines, ("signed", "outflow_magnitude", "outflow_magnitude", "signed"))
    assert [(i.period_id, i.lhs, i.rhs) for i in result.issues] == [
        ("fy2024", Decimal(300), Decimal(50)),
        ("fy2023", Decimal(250), Decimal(50)),
    ]
    assert result.lines == ()


@pytest.mark.parametrize(
    "book,text,expected",
    [
        # By hand: "US$" states USD, "C$"/"CA$" CAD, "A$" AUD; a bare "$" names no currency, so
        # with nothing else stated it verifies a USD book only (a CAD book's "$" could be US$).
        ("EUR", "(in millions of us$)", False),
        ("USD", "(in millions of us$)", True),
        ("EUR", "(in c$ millions)", False),
        ("CAD", "(in ca$ millions)", True),
        ("EUR", "(in a$ thousands)", False),
        ("AUD", "(in a$ thousands)", True),
        ("EUR", "cash $ 1,000", False),
        ("GBP", "(in $ millions)", False),
        ("USD", "(in $ millions)", True),
        ("CAD", "(in $ millions)", False),
        ("AUD", "cash $ 1,000", False),
        ("HKD", "(in $ millions)", False),
        ("CAD", "(in millions of canadian dollars) revenue $ 10", True),
        ("CAD", "(in millions of united states dollars)", False),
        ("USD", "(in millions of united states dollars) revenue $ 10", True),
        ("EUR", "(in millions)", True),
        ("EUR", "(in r$ millions)", True),
    ],
)
def test_currency_symbols_state_a_currency(book, text, expected):
    # S11-A06.
    assert sc._currency_matches(book, text) is expected


def test_page_units_extracts_each_page_once_across_the_inputs_helpers(monkeypatch):
    # S11-C09. By hand: one balance-sheet page; the five helpers of inputs() read it, and the
    # extractor runs once for it, not once per helper, with the same units each time.
    calls = []
    real = fw.extract_statement_lines
    monkeypatch.setattr(fw, "extract_statement_lines", lambda *a: calls.append(a) or real(*a))
    fw._units_of_pages.cache_clear()
    spans = (
        Span(
            locator="page:1",
            text="CONSOLIDATED BALANCE SHEETS\n2025  2024\nCash  10  9\nTotal assets  10  9",
        ),
    )
    first = fw._page_units(spans)
    assert first == {"page:1": "BS"}
    first["page:1"] = "IS"  # a caller's edit does not reach the cache
    assert fw._page_units(spans) == {"page:1": "BS"}
    assert fw._statement_kinds(spans) == {"page:1": "BS"}
    assert list(fw._statement_units(spans)) == ["page:1"]
    assert len(calls) == 1
