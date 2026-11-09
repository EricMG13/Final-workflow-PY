"""The financials coverage gate can cover SHC rows (CP1H-R20, T16).

Live runs 3 and 4 refused every financials submit with 215 "Uncovered extracted statement line"
issues whatever the model sent: `_statement` read only an upper-case heading (SHC's titles are
title-case), `_column_periods` was all-or-nothing, a printed nil dash was extracted as None while
the model wrote 0, and the refusal named only the row.

Answer key (read, never written): ``cases/statement-coverage/`` (the live submissions and the
payloads they stored) and ``cases/statement-rows/shc-earnings-update.json``. The replays rebuild
``_evidence_issues``'s inputs from an ``OwnerSubmission`` the way the live run's own audit does
(``owner_workflow._hist``, ``_fin`` and the submission's source evidence), on a tmp copy of the
run's ``execution/`` store; the run directory itself is never opened in place and the tests skip
when it is absent.
"""

import hashlib
import json
import re
import shutil
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.contracts import Span
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.execution import Execution
from deploy_vii.source_context import SourceContextReview
from deploy_workflow import financial_workflow as fw
from deploy_workflow import owner_workflow as ow
from deploy_workflow.statement_lines import LineTools, seen_tables

REPO = Path(__file__).resolve().parents[1]
KEY = REPO / "cases" / "statement-coverage"
ROWS_KEY = REPO / "cases" / "statement-rows" / "shc-earnings-update.json"
ARTIFACTS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/model-testing")
RUN3 = ARTIFACTS / "cp1h-live-3" / "pilot-sol-high-earnings_update-4"
RUN4 = ARTIFACTS / "cp1h-live-4" / "pilot-sol-medium-earnings_update-5"
Q10 = "SHC_2025-06-30_10-Q_0001822479-25-000044_shc-20250630"
K10 = "SHC_2024-12-31_10-K_0001822479-25-000015_shc-20241231"
PREFIX = "Uncovered extracted statement line: "
UNMEASURED = "Statement extraction is unmeasured"
NOT_EXTRACTED = "Financials must extract every located statement unit"


class Replay:
    """One key submission replayed through `_evidence_issues` on a tmp copy of its run's store."""

    def __init__(self, tmp_path: Path, run: Path, submission: str, stored: str | None) -> None:
        if not (run / "execution").is_dir():
            pytest.skip(f"live run store is absent: {run}")
        copy = tmp_path / "execution"
        shutil.copytree(run / "execution", copy, symlinks=True)
        self.store = Execution(copy)
        self.submission = ow.OwnerSubmission.model_validate_json(
            (KEY / submission).read_text(encoding="utf-8")
        )
        bound = self.submission.binding
        self.binding = bound.binding
        self.evidence = bound.source_evidence
        self.history = ow._hist(self.store, self.binding)
        if stored is None:
            self.payload = ow._raw(self.store, self.submission.stored_payload_sha256)
        else:
            data = (KEY / stored).read_bytes()
            assert hashlib.sha256(data).hexdigest() == self.submission.stored_payload_sha256
            self.payload = data.decode("utf-8")

    def issues(self, payload: str | None = None) -> tuple[str, ...]:
        return fw._evidence_issues(
            self.history, ow._fin(self.binding), payload or self.payload, self.evidence
        )

    def tables(self) -> list[Any]:
        attempt = next(
            a for a in self.history.read().attempts if a.ticket_id == self.binding.ticket_id
        )
        context = SourceContextReview.model_validate_json(
            self.history.payload(attempt.steps[0].payload_sha256)
        )
        ids = tuple(s.source_id for s in context.sources if s.classification == "financial")
        pack = self.history.pack()
        return list(seen_tables(LineTools(pack, sources=ids), self.evidence.seen(), context))


def _uncovered(issues: tuple[str, ...]) -> list[str]:
    return [i for i in issues if i.startswith(PREFIX)]


def _row(issues: tuple[str, ...], source_id: str, locator: str, line: int) -> list[str]:
    head = f"{PREFIX}{source_id} {locator} line {line}"
    return [i for i in issues if i == head or i.startswith(head + "; ")]


@pytest.fixture
def seq7(tmp_path: Path) -> Replay:
    return Replay(tmp_path, RUN3, "shc-seq7-submission.json", "shc-seq7-stored.json")


# ---- 1. the key submissions ----------------------------------------------------------------


def test_seq7_leaves_exactly_the_25_income_rows_of_the_10q(seq7: Replay) -> None:
    issues = seq7.issues()
    got = _uncovered(issues)
    assert len(got) == 25
    assert all(i.startswith(f"{PREFIX}{Q10} line:82-114 line ") for i in got), got
    assert not [i for i in issues if UNMEASURED in i or NOT_EXTRACTED in i]
    assert all(len(i) < 200 for i in got)


def test_run3_seq6_stays_215_because_no_quote_holds_a_label(tmp_path: Path) -> None:
    replay = Replay(tmp_path, RUN3, "shc-seq6-submission.json", None)
    got = _uncovered(replay.issues())
    assert len(got) == 215
    assert all("; " in i for i in got)


def test_run4_seq6_leaves_177(tmp_path: Path) -> None:
    replay = Replay(
        tmp_path, RUN4, "shc-run4-seq6-submission.json", "shc-run4-seq6-stored.json"
    )
    issues = replay.issues()
    assert len(_uncovered(issues)) == 177
    assert not [i for i in issues if UNMEASURED in i or NOT_EXTRACTED in i]


# ---- 2. the gate can pass --------------------------------------------------------------------


def _amount(raw: str) -> int | float:
    text = raw.strip()
    if text in ("—", "–", "-"):
        return 0
    value = Decimal(text.strip("()$").replace(",", ""))
    value = -value if text.startswith("(") else value
    return int(value) if value == value.to_integral() else float(value)


# Each statement unit's header columns, read by hand from the source header lines (10-Q lines
# 34-35, 83-84, 116-117; 10-K lines 218-219, 268-269, 307-308): ("I", end) is a balance date,
# ("D", start, end) a flow period.
COLS = {
    (Q10, "BS"): [("I", "2025-06-30"), ("I", "2024-12-31")],
    (Q10, "IS"): [
        ("D", "2025-04-01", "2025-06-30"),
        ("D", "2024-04-01", "2024-06-30"),
        ("D", "2025-01-01", "2025-06-30"),
        ("D", "2024-01-01", "2024-06-30"),
    ],
    (Q10, "CFS"): [("D", "2025-01-01", "2025-06-30"), ("D", "2024-01-01", "2024-06-30")],
    (K10, "BS"): [("I", "2024-12-31"), ("I", "2023-12-31")],
    (K10, "IS"): [
        ("D", "2024-01-01", "2024-12-31"),
        ("D", "2023-01-01", "2023-12-31"),
        ("D", "2022-01-01", "2022-12-31"),
    ],
    (K10, "CFS"): [
        ("D", "2024-01-01", "2024-12-31"),
        ("D", "2023-01-01", "2023-12-31"),
        ("D", "2022-01-01", "2022-12-31"),
    ],
}


def _column_ids(spec: tuple[str, ...], periods: list[dict[str, Any]]) -> frozenset[str]:
    """The declared period ids one hand-read column matches by its dates."""
    if spec[0] == "I":
        return frozenset(p["period_id"] for p in periods if p["end_date"] == spec[1])
    return frozenset(
        p["period_id"] for p in periods if (p["start_date"], p["end_date"]) == spec[1:]
    )


def _full_payload(replay: Replay) -> str:
    """The seq-7 payload with one line per row and mapped column of the rows key: the label as
    the quote, the raw amount (0 for a dash)."""
    payload = json.loads(replay.payload)
    books = payload["financial"]["books"]
    template = books[0]["statement_lines"][0]
    sha = {
        c["source_id"]: c["source_sha256"]
        for book in books
        for line in book["statement_lines"]
        for c in line["value"]["citations"]
    }
    for book in books:
        book["statement_lines"] = []
    rows = json.loads(ROWS_KEY.read_text(encoding="utf-8"))
    count = 0
    for source in rows["sources"]:
        for unit in source["units"]:
            columns = COLS[(source["source_id"], unit["kind"])]
            for row in unit["rows"]:
                for book in books:
                    mapped = [_column_ids(spec, book["periods"]) for spec in columns]
                    if not any(mapped):
                        continue
                    count += 1
                    for pids, raw in zip(mapped, row["raw_values"], strict=True):
                        if not pids:
                            continue
                        line = json.loads(json.dumps(template))
                        line.update(
                            line_id=f"t16-{count}",
                            statement=unit["kind"],
                            item_id=f"other:t16-{count}",
                            label=row["label"],
                            period_id=min(pids),
                            display_priority=count,
                        )
                        line["value"].update(
                            observation_id=f"t16-o{count}-{min(pids)}",
                            amount=_amount(raw),
                            citations=[
                                {
                                    "source_id": source["source_id"],
                                    "source_sha256": sha[source["source_id"]],
                                    "locator": f"line:{row['line']}",
                                    "quote": row["label"],
                                }
                            ],
                        )
                        book["statement_lines"].append(line)
                    break  # the first book that maps the row covers it
    return json.dumps(payload)


def test_a_payload_with_every_mapped_column_of_every_row_has_no_uncovered_row(
    seq7: Replay,
) -> None:
    payload = _full_payload(seq7)
    submission = FinancialSubmission.model_validate_json(payload)  # else the gate returns early
    assert sum(len(b.statement_lines) for b in submission.financial.books) > 215
    issues = seq7.issues(payload)
    assert _uncovered(issues) == []
    assert not [i for i in issues if UNMEASURED in i or NOT_EXTRACTED in i]


# ---- 3. units ---------------------------------------------------------------------------------


def _spans(lines: list[str]) -> list[Span]:
    return [Span(locator=f"line:{n}", text=text) for n, text in enumerate(lines, 1)]


def test_a_title_case_line_unit_has_its_located_kind() -> None:
    spans = _spans(
        [
            "Condensed Consolidated Balance Sheets (Unaudited)",
            "Cash and cash equivalents $ 1 $ 2",
            "Condensed Consolidated Statements of Operations",
            "Revenues $ 1 $ 2",
            "Condensed Consolidated Statements of Cash Flows",
            "Net income $ 1 $ 2",
        ]
    )
    assert fw._statement_kinds(spans) == {"line:1-2": "BS", "line:3-4": "IS", "line:5-6": "CFS"}
    text = fw._statement_units(spans)["line:3-4"]
    assert fw._statement(None, text, "IS") == "IS"
    assert fw._statement("Revenues", text, "BS") == "BS"


def test_a_comprehensive_income_unit_counts_as_income_where_no_income_title_stands() -> None:
    spans = _spans(["Consolidated Statements of Comprehensive Income", "Net income $ 1 $ 2"])
    assert fw._statement_kinds(spans) == {"line:1-2": "IS"}


def test_a_page_source_with_no_heading_still_has_no_statement() -> None:
    page = [Span(locator="page:1", text="CONSOLIDATED BALANCE SHEETS\nCash 1")]
    assert fw._statement_kinds(page) == {}
    assert fw._statement("ASSETS", "no heading here") is None
    assert fw._statement("ASSETS", "no heading here", None) is None


def test_a_nil_dash_matches_zero_and_none() -> None:
    assert fw._amount_matches(0, None)
    assert fw._amount_matches(None, None)
    assert not fw._amount_matches(5, None)
    assert fw._amount_matches(Decimal(332437), Decimal(332437))
    assert not fw._amount_matches(None, Decimal(0))
    assert not fw._amount_matches(0, Decimal(5))


def test_seq7_covers_the_dash_rows_with_the_amount_zero(seq7: Replay) -> None:
    issues = seq7.issues()
    for source_id, locator, line in (
        (Q10, "line:33-81", 75),
        (Q10, "line:115-162", 138),
        (Q10, "line:115-162", 148),
        (K10, "line:217-266", 259),
        (K10, "line:267-305", 286),
    ):
        assert not _row(issues, source_id, locator, line), (locator, line)


def _mutated(seq7: Replay, change: Any) -> tuple[str, ...]:
    payload = json.loads(seq7.payload)
    change(payload)
    return seq7.issues(json.dumps(payload))


def _cash_line(payload: dict[str, Any]) -> dict[str, Any]:
    book = next(b for b in payload["financial"]["books"] if b["book_id"] == "shc_usd")
    return next(
        line
        for line in book["statement_lines"]
        if line["value"]["citations"][0]["locator"] == "line:38"
    )


def _cash_reason(issues: tuple[str, ...]) -> str:
    (issue,) = _row(issues, Q10, "line:33-81", 38)
    assert issue.startswith(f"{PREFIX}{Q10} line:33-81 line 38; ")
    assert len(issue) < 200
    return issue


def test_reason_period_names_the_mapped_period_with_no_line(seq7: Replay) -> None:
    issues = [i for i in seq7.issues() if i.startswith(f"{PREFIX}{Q10} line:82-114 line ")]
    assert len(issues) == 25
    assert all(
        "; period: no IS line " in i and i.endswith(" for h1-2025") for i in issues
    ), issues[0]


def test_a_row_whose_label_only_names_lines_citing_other_rows_names_the_period(
    seq7: Replay,
) -> None:
    # 10-Q line 95 (amortisation of intangibles) has CFS lines of that label for h1-2025 that
    # cite other rows; there is no IS line for h1-2025
    (issue,) = _row(seq7.issues(), Q10, "line:82-114", 95)
    assert "; period: no IS line " in issue
    assert issue.endswith(" for h1-2025")


def test_reason_statement_names_the_expected_kind(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        book = next(b for b in payload["financial"]["books"] if b["book_id"] == "shc_usd")
        for line in book["statement_lines"]:
            if line["statement"] == "BS":
                line["statement"] = "IS"

    reason = _cash_reason(_mutated(seq7, change))
    assert "; statement: one of h1-2025, q2-2025 cites this row as IS, expected BS" in reason


def test_reason_label(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        _cash_line(payload)["label"] = "Cash"

    reason = _cash_reason(_mutated(seq7, change))
    assert '; label: one of h1-2025, q2-2025 cites this row with label "Cash"' in reason


def test_reason_amount_names_the_extracted_value(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        _cash_line(payload)["value"]["amount"] += 1

    reason = _cash_reason(_mutated(seq7, change))
    assert "; amount: one of h1-2025, q2-2025 expects 332437" in reason


def test_reason_quote(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        _cash_line(payload)["value"]["citations"][0]["quote"] = "332,437"

    reason = _cash_reason(_mutated(seq7, change))
    assert "; quote: one of h1-2025, q2-2025 has no citation of line:38 quoting the label" in reason


def test_a_row_line_tagged_with_the_wrong_statement_names_the_statement(seq7: Replay) -> None:
    reason = _cash_reason(_mutated(seq7, lambda p: _cash_line(p).update(statement="IS")))
    assert "; statement: one of h1-2025, q2-2025 cites this row as IS, expected BS" in reason


def test_a_row_line_with_an_undeclared_period_names_the_period(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        _cash_line(payload)["period_id"] = "zz-undeclared"

    reason = _cash_reason(_mutated(seq7, change))
    expected = '; period: no BS line "Cash and cash equivalents" for one of h1-2025, q2-2025'
    assert expected in reason


def test_run4_line_40_names_the_missing_fy2024_line_not_a_label(tmp_path: Path) -> None:
    replay = Replay(
        tmp_path, RUN4, "shc-run4-seq6-submission.json", "shc-run4-seq6-stored.json"
    )
    (issue,) = _row(replay.issues(), Q10, "line:33-81", 40)
    assert "; period: no BS line " in issue
    assert issue.endswith(" for FY2024")


def test_reason_no_column_maps_a_declared_period(seq7: Replay) -> None:
    def change(payload: dict[str, Any]) -> None:
        payload["financial"]["books"] = [
            b for b in payload["financial"]["books"] if b["book_id"] == "shc_usd"
        ]
        payload["binding"]["books"] = [
            b for b in payload["binding"]["books"] if b["book_id"] == "shc_usd"
        ]

    issues = _mutated(seq7, change)
    tenk = [i for i in issues if i.startswith(f"{PREFIX}{K10} ")]
    assert len(tenk) == 111
    assert all(i.endswith("; no column maps a declared period") for i in tenk), tenk[0]
    assert len(_uncovered(issues)) == 111 + 25


# ---- 6. fix round 3: the reason finds a row's lines by citation, not by label ----------------


def test_a_shared_label_row_missing_its_own_line_names_the_period(seq7: Replay) -> None:
    # 10-Q IS "Service" is line 86 (revenue) and line 90 (cost): with row 90's q2-2025 line gone,
    # row 86's correct line of the same label must not stand in for it
    def change(payload: dict[str, Any]) -> None:
        book = next(b for b in payload["financial"]["books"] if b["book_id"] == "shc_usd")
        book["statement_lines"] = [
            line
            for line in book["statement_lines"]
            if not (
                line["period_id"] == "q2-2025"
                and "line:90" in [c["locator"] for c in line["value"]["citations"]]
            )
        ]

    issues = _mutated(seq7, change)
    assert _row(issues, Q10, "line:82-114", 90) == [
        f'{PREFIX}{Q10} line:82-114 line 90; period: no IS line "Service" for q2-2025'
    ]
    (row86,) = _row(issues, Q10, "line:82-114", 86)
    assert row86.endswith(" for h1-2025")


def test_a_mislabelled_own_line_beside_a_same_label_line_of_another_row_names_the_label(
    seq7: Replay,
) -> None:
    def change(payload: dict[str, Any]) -> None:
        book = next(b for b in payload["financial"]["books"] if b["book_id"] == "shc_usd")
        line = _cash_line(payload)
        decoy = deepcopy(line)
        decoy["line_id"] += "-decoy"
        decoy["item_id"] = "other:decoy"
        decoy["value"]["observation_id"] += "-decoy"
        decoy["value"]["amount"] += 1
        decoy["value"]["citations"][0]["locator"] = "line:39"
        line["label"] = "Cash"
        book["statement_lines"].append(decoy)

    reason = _cash_reason(_mutated(seq7, change))
    assert '; label: one of h1-2025, q2-2025 cites this row with label "Cash"' in reason


def test_a_row_with_a_matching_line_that_cites_another_source_names_the_quote(
    tmp_path: Path,
) -> None:
    replay = Replay(tmp_path, RUN3, "shc-seq6-submission.json", None)
    (issue,) = _row(replay.issues(), K10, "line:217-266", 222)
    assert issue.endswith("; quote: fy-2024 has no citation of line:222 quoting the label")


def test_an_ambiguous_flow_column_fails_closed() -> None:
    headers = (
        "Three Months Ended June 30,  Six Months Ended June 30,",
        "2025  2024  2025  2024",
    )

    def per(period_id: str, kind: str, start: date, end: date, quarter: int) -> SimpleNamespace:
        return SimpleNamespace(
            period_id=period_id,
            period_type=kind,
            start_date=start,
            end_date=end,
            fiscal_quarter=quarter,
            fiscal_year="2025",
            day_count=(end - start).days + 1,
        )

    q2 = per("q2", "QUARTER", date(2025, 4, 1), date(2025, 6, 30), 2)
    q2x = per("q2x", "QUARTER", date(2025, 4, 1), date(2025, 6, 30), 3)
    h1 = per("h1", "YTD", date(2025, 1, 1), date(2025, 6, 30), 2)
    assert fw._mapped_columns(headers, [q2, h1]) == (
        frozenset({"q2"}),
        frozenset(),
        frozenset({"h1"}),
        frozenset(),
    )
    assert fw._mapped_columns(headers, [q2, q2x, h1]) is None


def test_a_dated_header_maps_no_flow_column_of_an_income_or_cash_flow_unit() -> None:
    """S11-A01: a 52/53-week 10-K prints "Fiscal Year Ended" over "December 28, 2024 | December
    30, 2023". The book declares fy-2024 and q4-2024, both ending 2024-12-28. A bare date is an
    instant: it cannot tell the full year from Q4, so for an IS/CI/CFS unit it maps no period and
    the model's map to q4-2024 (or to fy-2024) is not verified. A balance sheet keeps the balance
    rule: every non-LTM period ending on the date (hand-read from the declared periods below)."""
    headers = ("Fiscal Year Ended", "December 28, 2024  December 30, 2023")

    def per(period_id: str, kind: str, start: date | None, end: date, quarter: int | None):
        return SimpleNamespace(
            period_id=period_id,
            period_type=kind,
            start_date=start,
            end_date=end,
            fiscal_quarter=quarter,
            fiscal_year=str(end.year),
        )

    periods = [
        per("fy-2024", "FY", date(2023, 12, 31), date(2024, 12, 28), None),
        per("q4-2024", "QUARTER", date(2024, 9, 29), date(2024, 12, 28), 4),
        per("fy-2023", "FY", date(2023, 1, 1), date(2023, 12, 30), None),
    ]
    for kind in ("IS", "CI", "CFS"):
        assert fw._mapped_columns(headers, periods, kind) is None
        book = {"periods": [vars(p) for p in periods]}
        table = SimpleNamespace(headers=headers, source_id="fin", locator="line:3-6")
        assert fw._header_columns(table, book, statement=kind) is None
    assert fw._mapped_columns(headers, periods, "BS") == (
        frozenset({"fy-2024", "q4-2024"}),
        frozenset({"fy-2023"}),
    )
    # a flow span over the same dates still maps exactly one period per column
    spanned = ("Years Ended December 28,", "2024")
    assert fw._mapped_columns(spanned, periods[:2], "IS") == (frozenset({"fy-2024"}),)

    # a PDF page located only by its heading has no located kind: the page's own heading gives it
    table = SimpleNamespace(headers=headers, source_id="fin", locator="page:3")
    book = {"periods": [vars(p) for p in periods]}
    income = "CONSOLIDATED STATEMENTS OF OPERATIONS\nFiscal Year Ended\nNet sales 1,234 1,100"
    assert fw._header_columns(table, book, page_text=income) is None
    balance = "CONSOLIDATED BALANCE SHEETS\nFiscal Year Ended\nCash 1,234 1,100"
    assert fw._header_columns(table, book, page_text=balance) == (
        frozenset({"fy-2024", "q4-2024"}),
        frozenset({"fy-2023"}),
    )


# ---- 7. null columns (CP1H-R23.16, R23.19) ----------------------------------------------------

Q10_BS = "line:33-81"
USD, ANNUAL = "shc_usd", "shc_annual"


def _unit_rows(source_id: str, kind: str) -> set[int]:
    rows = json.loads(ROWS_KEY.read_text(encoding="utf-8"))
    return {
        row["line"]
        for source in rows["sources"]
        if source["source_id"] == source_id
        for unit in source["units"]
        if unit["kind"] == kind
        for row in unit["rows"]
    }


def _one_book(replay: Replay) -> dict[str, Any]:
    """The full payload with its two books made one: the 10-Q book declares the 10-K's FY2024
    period and holds the 10-K lines. The 10-Q balance sheet's 2024-12-31 column then maps to
    fy-2024 and no line of the 10-Q unit cites it (a null column); the 10-K balance sheet gives
    that period."""
    payload = json.loads(_full_payload(replay))
    usd, annual = payload["financial"]["books"]
    assert (usd["book_id"], annual["book_id"]) == (USD, ANNUAL)
    usd["periods"] += annual["periods"]
    usd["statement_lines"] += annual["statement_lines"]
    payload["financial"]["books"] = [usd]
    payload["binding"]["books"] = [b for b in payload["binding"]["books"] if b["book_id"] == USD]
    return payload


def _cites(line: dict[str, Any], source_id: str, rows: set[int]) -> bool:
    wanted = {f"line:{n}" for n in rows}
    return any(
        c["source_id"] == source_id and c["locator"] in wanted for c in line["value"]["citations"]
    )


def _drop(payload: dict[str, Any], source_id: str, rows: set[int], period_id: str | None) -> None:
    """Remove the book's lines citing a row of `rows` of the source (under one period, or all)."""
    (book,) = payload["financial"]["books"]
    book["statement_lines"] = [
        line
        for line in book["statement_lines"]
        if not (period_id in (None, line["period_id"]) and _cites(line, source_id, rows))
    ]


def _reported(issues: tuple[str, ...], source_id: str, locator: str) -> set[int]:
    head = re.escape(f"{PREFIX}{source_id} {locator} line ")
    found = (re.match(rf"{head}(\d+)(?:;|$)", issue) for issue in _uncovered(issues))
    return {int(m[1]) for m in found if m}


def test_a_null_column_with_another_covered_column_and_a_peer_unit_is_not_reported(
    seq7: Replay,
) -> None:
    payload = _one_book(seq7)
    FinancialSubmission.model_validate_json(json.dumps(payload))  # else the gate returns early
    issues = seq7.issues(json.dumps(payload))
    assert _uncovered(issues) == []
    assert not [i for i in issues if UNMEASURED in i or NOT_EXTRACTED in i]


def test_a_null_column_whose_period_no_other_unit_gives_is_reported(seq7: Replay) -> None:
    payload = _one_book(seq7)
    _drop(payload, K10, _unit_rows(K10, "BS"), "fy-2024")
    issues = seq7.issues(json.dumps(payload))
    assert _reported(issues, Q10, Q10_BS) == _unit_rows(Q10, "BS")
    (one,) = _row(issues, Q10, Q10_BS, min(_unit_rows(Q10, "BS")))
    assert "; period: no BS line " in one and one.endswith(" for fy-2024")


def test_a_unit_with_every_column_empty_is_reported(seq7: Replay) -> None:
    payload = _one_book(seq7)
    _drop(payload, Q10, _unit_rows(Q10, "BS"), None)
    issues = seq7.issues(json.dumps(payload))
    assert _reported(issues, Q10, Q10_BS) == _unit_rows(Q10, "BS")
    assert not _reported(issues, K10, "line:217-266")


def test_a_null_column_whose_peer_lines_are_another_statement_is_reported(seq7: Replay) -> None:
    # the 10-K balance sheet's lines are the 10-Q unit's only peers for fy-2024: tag them as IS
    # lines and the periods are no longer given by a balance sheet unit
    payload = _one_book(seq7)
    (book,) = payload["financial"]["books"]
    rows = _unit_rows(K10, "BS")
    for line in book["statement_lines"]:
        if _cites(line, K10, rows):
            line["statement"] = "IS"
    issues = seq7.issues(json.dumps(payload))
    assert _reported(issues, Q10, Q10_BS) == _unit_rows(Q10, "BS")


def test_a_column_some_line_of_the_unit_cites_under_is_required(seq7: Replay) -> None:
    # condition (a) of _null_column (R23.16): the 10-Q balance sheet's 2024-12-31 column maps to
    # fy-2024 and is null, and the 10-K balance sheet gives fy-2024. One extra line citing a 10-Q
    # BS row under fy-2024 (an other: item, so no duplicate) makes that column the unit's own:
    # it is required, so every 10-Q BS row is reported for fy-2024.
    payload = _one_book(seq7)
    (book,) = payload["financial"]["books"]
    rows = _unit_rows(Q10, "BS")
    source = next(line for line in book["statement_lines"] if _cites(line, Q10, rows))
    extra = deepcopy(source)
    extra["period_id"] = "fy-2024"
    extra["line_id"] = "probe-extra-1"
    extra["item_id"] = "other:probe_extra_1"
    book["statement_lines"].append(extra)
    text = json.dumps(payload)
    FinancialSubmission.model_validate_json(text)  # else the gate returns early
    assert len(rows) == 40
    assert _reported(seq7.issues(text), Q10, Q10_BS) == rows


# ---- 8. rows under another statement's caption (CP1H-R23.22) ---------------------------------


def test_a_located_units_row_whose_caption_names_another_statement_is_not_reported(
    seq7: Replay, monkeypatch: pytest.MonkeyPatch
) -> None:
    income = "line:82-114"
    before = _reported(seq7.issues(), Q10, income)
    assert len(before) == 25
    rows = {n: "BS" for n in sorted(before)[:3]}
    monkeypatch.setattr(fw, "_other_statement_rows", lambda *a, **k: {(Q10, income): rows})
    assert _reported(seq7.issues(), Q10, income) == before - set(rows)
