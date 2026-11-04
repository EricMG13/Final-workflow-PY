"""The model's column map is checked, not trusted (CP1H-R23.27).

Answer key (read, never written): the reviewers' probes, ported as tests. Each reads the cause at
the surface where the probe saw it (the composed lines, the gate's issues, the expansion notes).
Real data: the SHC run-3 seq-7 store (``test_cp1_coverage_gate.Replay``); the tests skip when the
run is absent.

- R23.27.1: a text-layer unit composes only when its own printed header verifies the model's map
  (adversary P1, P1b, P1c, P2);
- R23.27.2: a null column's peer is a unit on another source, of the same kind, not OCR, whose own
  header maps the period (adversary P5, architect P1; architect P2 stays refused);
- R23.27.3: a map composes only a located statement unit (adversary P3).
"""

import copy
import dataclasses
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
import test_cp1_coverage_gate as gate
from test_line_locators import FIN, _with_spans

from deploy_vii.contracts import Span
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.live.tools import PackTools
from deploy_vii.statement_extract import extract_statement_lines
from deploy_vii.statement_validation import statement_issues
from deploy_workflow import financial_workflow as fw
from deploy_workflow import owner_workflow as ow
from deploy_workflow import statement_compose as sc
from deploy_workflow.workflow import SourceEvidence

UNIT = "line:33-81"


def _period(base: dict[str, Any], pid: str, start: str, end: str, days: int) -> dict[str, Any]:
    p = copy.deepcopy(base)
    p.update(period_id=pid, fiscal_year="2024", start_date=start, end_date=end)
    if "day_count" in p:
        p["day_count"] = days
    return p


def _with_2024_flows(replay: gate.Replay) -> None:
    """The 10-Q's two comparative flow periods declared (its income and cash-flow units print them)."""
    raw = json.loads(replay.payload)
    usd = next(b for b in raw["financial"]["books"] if b["book_id"] == gate.USD)
    q2 = next(p for p in usd["periods"] if p["period_id"] == "q2-2025")
    h1 = next(p for p in usd["periods"] if p["period_id"] == "h1-2025")
    usd["periods"] += [
        _period(q2, "q2-2024", "2024-04-01", "2024-06-30", 91),
        _period(h1, "h1-2024", "2024-01-01", "2024-06-30", 182),
    ]
    replay.payload = json.dumps(raw)


def _bs_table(replay: gate.Replay) -> Any:
    return next(t for t in replay.tables() if (t.source_id, t.locator) == (gate.Q10, UNIT))


def _bs_map(rows: set[int], columns: list[str | None]) -> dict[str, Any]:
    return {
        "source_id": gate.Q10,
        "locator": UNIT,
        "book_id": gate.USD,
        "statement": "BS",
        "columns": columns,
        "rows": [
            {
                "row": n,
                "line_id": f"probe-bs-{n}",
                "item_id": f"other:probe-bs-{n}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for n in sorted(rows)
        ],
    }


def _composable(table: Any) -> set[int]:
    return {r.line_no for r in table.lines if not set(r.flags) - {"footnote_marker"}}


def _expanded(replay: gate.Replay, payload: dict[str, Any]) -> Any:
    return fw.expand_unit_maps(
        replay.history, ow._fin(replay.binding), json.dumps(payload), replay.evidence
    )


def _wrong_period_run(
    replay: gate.Replay, payload: dict[str, Any], columns: list[str | None]
) -> Any:
    """Expand a 10-Q BS map; return the expansion, the book, the lines holding the printed
    December 31, 2024 value under h1-2024 and the 10-Q BS rows the gate reports."""
    table = _bs_table(replay)
    rows = _composable(table)
    payload = copy.deepcopy(payload)
    book_payload = next(b for b in payload["financial"]["books"] if b["book_id"] == gate.USD)
    keep = [x for x in book_payload["statement_lines"] if not gate._cites(x, gate.Q10, rows)]
    book_payload["statement_lines"] = keep
    payload["unit_maps"] = [_bs_map(rows, columns)]
    expansion = _expanded(replay, payload)
    book = next(
        b
        for b in FinancialSubmission.model_validate_json(expansion.payload).financial.books
        if b.book_id == gate.USD
    )
    col1 = {r.locator: r.values[1] for r in table.lines if len(r.values) == 2}
    held = [
        line
        for line in book.statement_lines
        if line.period_id == "h1-2024"
        and line.value.citations[0].source_id == gate.Q10
        and line.value.citations[0].locator in col1
        and line.value.amount == (col1[line.value.citations[0].locator] or 0)
    ]
    reported = gate._reported(replay.issues(expansion.payload), gate.Q10, UNIT)
    return expansion, book, held, reported


@pytest.fixture
def shc(tmp_path: Path) -> gate.Replay:
    replay = gate.Replay(tmp_path, gate.RUN3, "shc-seq7-submission.json", "shc-seq7-stored.json")
    _with_2024_flows(replay)
    return replay


# ---- R23.27.1: the header check on every unit --------------------------------------------------


def test_a_text_layer_column_mapped_to_a_wrong_period_composes_nothing_and_is_reported(
    shc: gate.Replay,
) -> None:
    # adversary P1: the printed "December 31, 2024" column mapped to h1-2024 (ends 2024-06-30)
    expansion, _, held, reported = _wrong_period_run(
        shc, gate._one_book(shc), ["h1-2025", "h1-2024"]
    )
    assert held == []
    assert reported == _composable(_bs_table(shc))
    note = next(n for n in expansion.notes if "column 1" in n)
    assert "h1-2024" in note and UNIT in note and "nothing composed" in note


def test_a_text_layer_column_mapped_to_a_wrong_period_in_the_two_book_shape_is_not_written(
    shc: gate.Replay,
) -> None:
    # adversary P1b: the full two-book payload, the column maps no usd period (R20)
    payload = json.loads(gate._full_payload(shc))
    FinancialSubmission.model_validate_json(json.dumps(payload))
    _, _, held, reported = _wrong_period_run(shc, payload, ["h1-2025", "h1-2024"])
    assert held == []
    assert reported == _composable(_bs_table(shc))


def test_the_correct_map_still_composes_the_ten_q_balance_sheet(shc: gate.Replay) -> None:
    # positive control: [h1-2025, null] verifies against the printed header
    table = _bs_table(shc)
    expansion = _expanded(shc, _wrong_map_payload(shc, ["h1-2025", None]))
    book = next(
        b
        for b in FinancialSubmission.model_validate_json(expansion.payload).financial.books
        if b.book_id == gate.USD
    )
    made = [x for x in book.statement_lines if x.line_id.startswith("probe-bs-")]
    assert len(made) == len(_composable(table))
    assert {x.period_id for x in made} == {"h1-2025"}


def _wrong_map_payload(replay: gate.Replay, columns: list[str | None]) -> dict[str, Any]:
    payload = gate._one_book(replay)
    rows = _composable(_bs_table(replay))
    gate._drop(payload, gate.Q10, rows, None)
    payload["unit_maps"] = [_bs_map(rows, columns)]
    return payload


def test_wrong_period_map_is_refused_before_submission_and_composes_no_lines(
    tmp_path: Path,
) -> None:
    right_replay = _fresh(tmp_path / "right")
    _, _, right_held, right_reported = _wrong_period_run(
        right_replay, json.loads(right_replay.payload), ["h1-2025", None]
    )
    wrong_replay = _fresh(tmp_path / "wrong")
    expansion, _, held, reported = _wrong_period_run(
        wrong_replay, json.loads(wrong_replay.payload), ["h1-2025", "h1-2024"]
    )
    assert right_held == []
    assert right_reported == set()
    assert held == []
    assert reported == _composable(_bs_table(wrong_replay))
    note = next(n for n in expansion.notes if "column 1" in n)
    assert "h1-2024" in note and UNIT in note and "nothing composed" in note


def _fresh(path: Path) -> gate.Replay:
    path.mkdir()
    replay = gate.Replay(path, gate.RUN3, "shc-seq7-submission.json", "shc-seq7-stored.json")
    _with_2024_flows(replay)
    return replay


def test_a_short_or_long_column_map_composes_no_odd_row(
    shc: gate.Replay, monkeypatch: pytest.MonkeyPatch
) -> None:
    # adversary P2: the SHC 10-K income statement prints 3 columns; the unit's count is the
    # header's, not the map's
    unit = "line:267-305"
    key = (gate.K10, unit)
    table = next(t for t in shc.tables() if (t.source_id, t.locator) == key)
    usable = [r for r in table.lines if len(r.values) == 3 and not r.flags]
    short_src, long_src = usable[3], usable[4]
    short = _replace_row(short_src, short_src.values[1:], short_src.raw_values[1:])
    long_ = _replace_row(long_src, (sc.Decimal(4), *long_src.values), ("4", *long_src.raw_values))
    odd = _replace_lines(
        table, [short if r is short_src else long_ if r is long_src else r for r in table.lines]
    )
    real = fw.seen_tables
    monkeypatch.setattr(
        fw,
        "seen_tables",
        lambda *a, **k: [odd if (t.source_id, t.locator) == key else t for t in real(*a, **k)],
    )
    assert key in set(shc.evidence.extracted)
    payload = json.loads(gate._full_payload(shc))
    results: dict[str, list[str]] = {}
    for name, columns in (
        ("true", ["fy-2024", None, None]),
        ("short", ["fy-2024", None]),
        ("long", ["fy-2024", None, None, None]),
    ):
        sent = copy.deepcopy(payload)
        sent["unit_maps"] = [
            {
                "source_id": gate.K10,
                "locator": unit,
                "book_id": gate.ANNUAL,
                "statement": "IS",
                "columns": columns,
                "rows": [
                    {
                        "row": r.line_no,
                        "line_id": f"p2-{r.line_no}",
                        "item_id": f"other:p2_{r.line_no}",
                        "line_kind": "detail",
                        "sign_convention": "signed",
                    }
                    for r in odd.lines
                ],
            }
        ]
        done = _expanded(shc, sent)
        book = next(
            b for b in json.loads(done.payload)["financial"]["books"] if b["book_id"] == gate.ANNUAL
        )
        results[name] = [
            x["value"]["citations"][0]["locator"]
            for x in book["statement_lines"]
            if x["line_id"].startswith("p2-")
        ]
    assert results["true"], "control: the true map composes the unit's regular rows"
    assert short.locator not in results["true"] and long_.locator not in results["true"]
    assert results["short"] == [] and results["long"] == []


def _replace_row(row: Any, values: tuple[Any, ...], raw: tuple[str, ...]) -> Any:
    return dataclasses.replace(row, values=values, raw_values=raw)


def _replace_lines(table: Any, lines: list[Any]) -> Any:
    return dataclasses.replace(table, lines=tuple(lines))


# ---- R23.27.3: located units only --------------------------------------------------------------


def test_a_map_of_an_extracted_range_that_is_not_a_located_unit_composes_nothing(
    shc: gate.Replay,
) -> None:
    # adversary P3: line:33-211 is extracted (the live model read the whole 10-Q) but is not a
    # located statement unit; its cash-flow rows must not become BS lines
    rng = "line:33-211"
    assert (gate.Q10, rng) in set(shc.evidence.extracted)
    payload = json.loads(gate._full_payload(shc))
    table = next(t for t in shc.tables() if (t.source_id, t.locator) == (gate.Q10, rng))
    cfs = [r for r in table.lines if 115 <= r.line_no <= 162 and not r.flags]
    assert cfs
    payload["unit_maps"] = [
        {
            "source_id": gate.Q10,
            "locator": rng,
            "book_id": gate.USD,
            "statement": "BS",
            "columns": ["h1-2025", None],
            "rows": [
                {
                    "row": r.line_no,
                    "line_id": f"p3-{r.line_no}",
                    "item_id": f"other:p3_{r.line_no}",
                    "line_kind": "detail",
                    "sign_convention": "signed",
                }
                for r in cfs
            ],
        }
    ]
    expansion = _expanded(shc, payload)
    book = next(
        b
        for b in FinancialSubmission.model_validate_json(expansion.payload).financial.books
        if b.book_id == gate.USD
    )
    assert [x for x in book.statement_lines if x.line_id.startswith("p3-")] == []
    assert any("not a located statement unit; nothing composed" in n for n in expansion.notes)
    assert [i for i in statement_issues(book) if "p3-" in i] == []


# ---- R23.27.2: a null column's peer ------------------------------------------------------------

K_BS, K_CFS = "line:217-266", "line:306-357"


def test_one_cash_line_citing_the_cash_flow_unit_does_not_excuse_a_balance_sheet_column(
    shc: gate.Replay,
) -> None:
    # adversary P5: fy-2023 declared; the 10-K BS's December 31, 2023 lines dropped; ONE BS line
    # for fy-2023 cites the 10-K cash-flow unit's "beginning of period" row
    raw = json.loads(shc.payload)
    annual = next(b for b in raw["financial"]["books"] if b["book_id"] == gate.ANNUAL)
    fy24 = next(p for p in annual["periods"] if p["period_id"] == "fy-2024")
    fy23 = copy.deepcopy(fy24)
    fy23.update(
        period_id="fy-2023", fiscal_year="2023", start_date="2023-01-01", end_date="2023-12-31"
    )
    if "day_count" in fy23:
        fy23["day_count"] = 365
    annual["periods"].append(fy23)
    shc.payload = json.dumps(raw)
    payload = gate._one_book(shc)
    assert gate._uncovered(shc.issues(json.dumps(payload))) == []  # baseline: fy-2023 covered
    tables = {(t.source_id, t.locator): t for t in shc.tables()}
    bs, cfs = tables[(gate.K10, K_BS)], tables[(gate.K10, K_CFS)]
    begin = next(
        r for r in cfs.lines if "beginning" in r.label.lower() and "cash" in r.label.lower()
    )
    bs_rows = {r.line_no for r in bs.lines}
    gate._drop(payload, gate.K10, bs_rows, "fy-2023")
    book = payload["financial"]["books"][0]
    template = next(
        x
        for x in book["statement_lines"]
        if x["statement"] == "BS" and gate._cites(x, gate.K10, bs_rows)
    )
    extra = copy.deepcopy(template)
    extra.update(
        line_id="probe-cash-2023",
        item_id="other:probe_cash_2023",
        period_id="fy-2023",
        label="Cash and cash equivalents",
        display_priority=99999,
    )
    extra["value"].update(observation_id="probe-cash-2023-o", amount=int(begin.values[0]))
    extra["value"]["citations"] = [
        dict(extra["value"]["citations"][0], locator=begin.locator, quote=begin.label)
    ]
    book["statement_lines"].append(extra)
    text = json.dumps(payload)
    FinancialSubmission.model_validate_json(text)
    assert gate._reported(shc.issues(text), gate.K10, K_BS), "the fy-2023 BS rows are required"


HEADER = "                         September 30, 2024    September 30, 2023"
PAGE1 = f"CONSOLIDATED BALANCE SHEETS\n{HEADER}\nCash and cash equivalents               150          90\nReceivables                              50          40\nTotal assets                            200         130"
PAGE2 = f"{HEADER}\nPayables                                 60          30\nTotal liabilities                        60          30\nTotal equity                            140         100\nTotal liabilities and equity            200         130"
IDS = ["fy-2024", "fy-2023"]
PERIODS = [
    SimpleNamespace(
        period_id=f"fy-{year}",
        period_type="FY",
        fiscal_year=f"FY{year}",
        fiscal_quarter=None,
        start_date=date(year - 1, 10, 1),
        end_date=date(year, 9, 30),
    )
    for year in (2024, 2023)
]
GATE = ("Financials must extract", "Uncovered extracted", "Statement extraction", "No statement")


def _composed(locator: str, text: str, columns: list[str | None]) -> list[Any]:
    table = extract_statement_lines(text, locator, FIN)
    row_map = {
        row.line_no: sc.RowJudgment(
            f"{locator}-{row.line_no}",
            f"other:{locator}_{row.line_no}".replace(":", "_"),
            "detail",
            "signed",
        )
        for row in table.lines
    }
    done = sc.compose_unit(
        table,
        source_id=FIN,
        source_sha256="0" * 64,
        unit_locator=locator,
        kind="BS",
        column_periods=columns,
        row_map=row_map,
        declared_periods=IDS,
    )
    assert not done.issues, done.issues
    assert not done.left_to_model, done.left_to_model
    return list(done.lines)


def _page_gate(lines: list[Any]) -> list[str]:
    pack = _with_spans([Span(locator="page:1", text=PAGE1), Span(locator="page:2", text=PAGE2)])
    fin = next(s for s in pack.sources if s.source_id == FIN)
    units = fw._statement_units(fin.spans)
    assert set(units) == {"page:1", "page:2"}, set(units)
    tools = PackTools(pack, sources=(FIN,))
    for locator in units:
        tools.extract_statements({"source_id": FIN, "locators": [locator]})
    evidence = SourceEvidence(
        read=tuple(sorted(tools.read)), extracted=tuple(sorted(tools.extracted))
    )
    context = o2_case.payload_for("source_context")
    store = SimpleNamespace(
        read=lambda: SimpleNamespace(
            attempts=[SimpleNamespace(ticket_id="t", steps=[SimpleNamespace(payload_sha256="c")])]
        ),
        payload=lambda _sha: context,
        pack=lambda: pack,
    )
    book = SimpleNamespace(periods=PERIODS, statement_lines=lines)
    saved = fw.FinancialSubmission
    fw.FinancialSubmission = cast(
        Any,
        SimpleNamespace(
            model_validate_json=lambda _s: SimpleNamespace(financial=SimpleNamespace(books=[book]))
        ),
    )
    try:
        binding = SimpleNamespace(step_id="financials", ticket_id="t")
        found = fw._evidence_issues(cast(Any, store), cast(Any, binding), "x", evidence)
    finally:
        fw.FinancialSubmission = saved
    return [issue for issue in found if issue.startswith(GATE)]


def _page2_rows(issues: list[str]) -> list[str]:
    return [i for i in issues if f"{FIN} page:2 line " in i]


def test_a_sibling_page_of_the_same_source_does_not_excuse_a_null_column() -> None:
    # architect P1: page 2's fy-2023 column null, page 1 (same source, same kind) gives fy-2023
    page1 = _composed("page:1", PAGE1, IDS)
    assert _page_gate(page1 + _composed("page:2", PAGE2, IDS)) == []  # control A
    assert len(_page2_rows(_page_gate(page1))) == 4  # control B (R23.19)
    partial = _page_gate(page1 + _composed("page:2", PAGE2, ["fy-2024", None]))
    assert len(_page2_rows(partial)) == 4, partial


def test_a_swap_plus_a_null_column_is_still_refused_on_the_amounts() -> None:
    # architect P2 (stays at exit 0)
    page1 = _composed("page:1", PAGE1, IDS)
    swapped = _composed("page:2", PAGE2, ["fy-2023", None])
    issues = _page2_rows(_page_gate(page1 + swapped))
    assert len(issues) == 4, issues
    assert _page2_rows(_page_gate(page1 + _composed("page:2", PAGE2, IDS))) == []
