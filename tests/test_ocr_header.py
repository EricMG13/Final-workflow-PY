"""An OCR unit composes only when its header verifies the model's map; the gate checks the OCR
rows a book line cites (CP1H-R23.23.2, T22 fix 3).

The pack: one financial source whose only page is an OCR'd balance sheet that balances (both
checks apply, pass and are not vacuous). The periods are FY ending 2024-09-30 and 2023-09-30.
"""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
from test_line_locators import FIN, _with_spans

from deploy_vii.contracts import Coverage, Span
from deploy_vii.live.tools import PackTools
from deploy_vii.preparation import OCR_MARK, PreparedPack
from deploy_vii.statement_extract import ExtractedTable, extract_statement_lines
from deploy_workflow import financial_workflow as fw
from deploy_workflow import statement_compose as sc
from deploy_workflow.unit_maps import UnitInputs, expand
from deploy_workflow.workflow import SourceEvidence

MARK = f"{OCR_MARK} (tesseract 5.5.2); verify against the original"
ROWS = [
    "Cash and cash equivalents               150          90",
    "Total assets                            150          90",
    "Total liabilities                        60          30",
    "Total equity                             90          60",
    "Total liabilities and equity            150          90",
]
ITEMS = [
    "cash_and_equivalents",
    sc.TOTAL_ASSETS,
    sc.TOTAL_LIABILITIES,
    sc.TOTAL_EQUITY,
    sc.TOTAL_LIABILITIES_AND_EQUITY,
]
HEADER = "                         September 30, 2024    September 30, 2023"
IDS = ["fy-2024", "fy-2023"]
GATE = (
    "Financials must extract",
    "Uncovered extracted",
    "Statement extraction is unmeasured",
    "No statement unit",
)
KEY = (FIN, "page:1")


def _text(header: str = HEADER) -> str:
    return "\n".join(["CONSOLIDATED BALANCE SHEETS", header, *ROWS])


def _period_dicts() -> list[dict[str, Any]]:
    return [
        {
            "period_id": f"fy-{year}",
            "fiscal_year": f"FY{year}",
            "fiscal_quarter": None,
            "period_type": "FY",
            "start_date": f"{year - 1}-10-01",
            "end_date": f"{year}-09-30",
        }
        for year in (2024, 2023)
    ]


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


def _pack(text: str, *, ocr: bool = True) -> PreparedPack:
    pack = _with_spans([Span(locator="page:1", text=text)])
    coverage = (Coverage(locator="page:1", status="retained", limitation=MARK if ocr else None),)
    return pack.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"coverage": coverage}) if s.source_id == FIN else s
                for s in pack.sources
            )
        }
    )


def _table(text: str | None = None) -> ExtractedTable:
    return extract_statement_lines(text or _text(), "page:1", FIN)


def _row_map(table: ExtractedTable) -> dict[int, sc.RowJudgment]:
    return {
        row.line_no: sc.RowJudgment(f"b{row.line_no}", ITEMS[i], "detail", "signed")
        for i, row in enumerate(table.lines)
    }


def _expanded(columns: list[str | None]) -> list[dict[str, Any]]:
    """The statement lines `expand` writes for the OCR unit, with the real `_ocr_header`."""
    table = _table()
    entries = [
        {
            "row": number,
            "line_id": j.line_id,
            "item_id": j.item_id,
            "line_kind": j.line_kind,
            "sign_convention": j.sign_convention,
        }
        for number, j in _row_map(table).items()
    ]
    unit = {
        "source_id": FIN,
        "locator": "page:1",
        "book_id": "b1",
        "statement": "BS",
        "columns": columns,
        "rows": entries,
    }
    book = {"book_id": "b1", "periods": _period_dicts(), "statement_lines": []}
    payload = json.dumps({"financial": {"books": [book]}, "unit_maps": [unit]})
    done = expand(
        payload,
        extracted={KEY},
        inputs=lambda: UnitInputs(
            [table],
            {FIN: "0" * 64},
            ocr_pages=frozenset({KEY}),
            ocr_header=fw._ocr_header,
            located=frozenset({KEY}),
        ),
    )
    lines: list[dict[str, Any]] = json.loads(done.payload)["financial"]["books"][0][
        "statement_lines"
    ]
    return lines


def test_an_ocr_unit_whose_header_maps_the_models_columns_composes() -> None:
    assert len(_expanded(IDS)) == 5 * 2


def test_an_ocr_unit_with_the_models_columns_swapped_composes_nothing() -> None:
    assert _expanded(["fy-2023", "fy-2024"]) == []


def test_an_ocr_unit_composes_a_null_column_as_the_header_allows() -> None:
    assert len(_expanded([None, "fy-2023"])) == 5


@pytest.mark.parametrize(
    "mapped",
    [None, (frozenset({"fy-2024"}),), (frozenset(), frozenset({"fy-2023"}))],
    ids=["no header", "wrong length", "column maps nothing"],
)
def test_an_ocr_unit_whose_header_does_not_verify_leaves_every_row_to_the_model(
    mapped: Any,
) -> None:
    table = _table()
    row_map = _row_map(table)
    unit = {
        "source_id": FIN,
        "locator": "page:1",
        "book_id": "b1",
        "statement": "BS",
        "columns": IDS,
        "rows": [
            {
                "row": n,
                "line_id": j.line_id,
                "item_id": j.item_id,
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for n, j in row_map.items()
        ],
    }
    book = {"book_id": "b1", "periods": _period_dicts(), "statement_lines": []}
    done = expand(
        json.dumps({"financial": {"books": [book]}, "unit_maps": [unit]}),
        extracted={KEY},
        inputs=lambda: UnitInputs(
            [table],
            {FIN: "0" * 64},
            ocr_pages=frozenset({KEY}),
            ocr_header=lambda t, b: mapped,
            located=frozenset({KEY}),
        ),
    )
    assert json.loads(done.payload)["financial"]["books"][0]["statement_lines"] == []
    assert sum("ocr_unchecked" in note for note in done.notes) >= 1


def test_a_header_that_is_lost_never_verifies() -> None:
    table = _table(_text("                                        2024          2023"))
    assert fw._ocr_header(table, {"periods": _period_dicts()}) is None


def test_the_header_of_a_book_with_no_period_fields_does_not_verify() -> None:
    assert fw._ocr_header(_table(), {"periods": [{"period_id": "fy-2024"}]}) is None
    assert fw._ocr_header(_table(), {"periods": "x"}) is None


# ---- the gate ---------------------------------------------------------------------------------


def _composed(table: ExtractedTable) -> list[Any]:
    done = sc.compose_unit(
        table,
        source_id=FIN,
        source_sha256="0" * 64,
        unit_locator="page:1",
        kind="BS",
        column_periods=IDS,
        row_map=_row_map(table),
        declared_periods=IDS,
        ocr=True,
    )
    return list(done.lines)


def _gate(monkeypatch: pytest.MonkeyPatch, pack: PreparedPack, lines: list[Any]) -> list[str]:
    """The gate's own issues for a book of `lines`, every located unit extracted."""
    fin = next(s for s in pack.sources if s.source_id == FIN)
    tools = PackTools(pack, sources=(FIN,))
    for locator in fw._statement_units(fin.spans):
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
    monkeypatch.setattr(
        fw,
        "FinancialSubmission",
        SimpleNamespace(
            model_validate_json=lambda _s: SimpleNamespace(financial=SimpleNamespace(books=[book]))
        ),
    )
    binding = SimpleNamespace(step_id="financials", ticket_id="t")
    found = fw._evidence_issues(cast(Any, store), cast(Any, binding), "x", evidence)
    return [issue for issue in found if issue.startswith(GATE)]


def test_the_gate_raises_nothing_for_correctly_composed_ocr_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = _composed(_table())
    assert len(lines) == 5 * 2
    assert _gate(monkeypatch, _pack(_text()), lines) == []


def test_the_gate_asks_nothing_of_a_line_citing_an_ocr_row_with_another_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = _composed(_table())
    cash = next(i for i, x in enumerate(lines) if x.item_id == "cash_and_equivalents")
    lines[cash] = lines[cash].model_copy(
        update={"value": lines[cash].value.model_copy(update={"amount": Decimal(1)})}
    )
    # R23.23.1: an OCR unit's rows are not required, and on a page source a citation names only
    # the page, so the gate cannot tell a checked row from a misread one; it raises nothing
    assert _gate(monkeypatch, _pack(_text()), lines) == []


def test_the_gate_raises_nothing_for_an_ocr_page_no_line_cites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # on a page source a row's locator is the page, so an uncited page has no cited row
    assert _gate(monkeypatch, _pack(_text()), []) == []


# ---- "no statement unit" (L-c) ----------------------------------------------------------------


def test_a_pack_whose_only_units_are_on_ocr_pages_raises_no_missing_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert not [i for i in _gate(monkeypatch, _pack(_text()), []) if "No statement unit" in i]


def test_a_pack_with_no_located_unit_still_raises_no_statement_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pack = _pack("\n".join([HEADER, *ROWS]))
    assert "No statement unit is located in the financial sources" in _gate(monkeypatch, pack, [])
