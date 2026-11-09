"""Per-cell statement dimensions through the independent CP1 TDG output oracle."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_statement_quantities as quantity_fixtures

import deploy_vii.statement_history as history_module
from deploy_vii.canonical_audit import _positions
from deploy_vii.canonical_tables import COLUMNS, _calculations, _constructed, _keys
from deploy_vii.contracts import Citation, Fact, Run, Source, Span
from deploy_vii.financial_contracts import (
    Disclosure,
    FinancialBook,
    FinancialPeriod,
    FinancialReview,
    Observation,
    StatementLine,
    StatementQuantity,
)
from deploy_vii.financial_periods import PeriodValue, _id
from deploy_vii.financial_validation import records, validate_financial_review
from deploy_vii.model_interface import SCHEMAS, _Cell, _Tables
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _scale_of, figure_unit
from deploy_vii.statement_history import statement_history, validate_statement_history
from deploy_vii.statement_output import StatementReport, _cells
from deploy_vii.statement_view import statement_view

REPO = Path(__file__).resolve().parents[1]
CASE = REPO / "cases" / "cp1-chain"
EXPECTED_SHA256 = "b31b0fc8c3828097087d88873526eaf2d5853d3a8577daf77b3add742e595b2b"
SOURCE_ID = "TDG-FY2024-10K"
EXPECTED = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))


def _citation(locator: str, quote: str) -> Citation:
    return Citation(
        source_id=SOURCE_ID,
        source_sha256=EXPECTED["source"]["source_sha256"],
        locator=locator,
        quote=quote,
    )


def _periods() -> tuple[FinancialPeriod, ...]:
    policy = EXPECTED["fiscal_policy"]
    policy_citation = _citation(policy["citation"]["locator"], policy["source_lines"][0])
    periods = []
    for row in policy["periods"]["duration"]:
        start = date.fromisoformat(row["start_date"])
        end = date.fromisoformat(row["end_date"])
        periods.append(
            FinancialPeriod(
                period_id=row["period_id"],
                fiscal_year=f"FY{row['fiscal_year']}",
                fiscal_quarter=None,
                period_type="FY",
                start_date=start,
                end_date=end,
                day_count=(end - start).days + 1,
                audit_status="audited",
                currency="USD",
                unit="MILLIONS",
                accounting_basis="US GAAP",
                entity_perimeter="TD Group consolidated",
                citations=(policy_citation,),
            )
        )
    for row in policy["periods"]["BS"]:
        end = date.fromisoformat(row["end_date"])
        periods.append(
            FinancialPeriod(
                period_id=row["period_id"],
                fiscal_year=f"FY{row['fiscal_year']}",
                fiscal_quarter=None,
                period_type="PERIOD_END",
                start_date=None,
                end_date=end,
                day_count=None,
                audit_status="audited",
                currency="USD",
                unit="MILLIONS",
                accounting_basis="US GAAP",
                entity_perimeter="TD Group consolidated",
                citations=(policy_citation,),
                limitation="Balance-sheet observation is an instant; no start date is supplied",
            )
        )
    return tuple(periods)


def _book() -> FinancialBook:
    lines = []
    priority: Counter[str] = Counter()
    for row in EXPECTED["financial_rows"]:
        source_statement = row["statement"]
        statement = "IS" if source_statement == "CI" else source_statement
        prefix = "ci" if source_statement == "CI" else source_statement.casefold().replace("-", "_")
        item_id = f"other:{prefix}_{row['row_id'].split('-')[1]}"
        priority[statement] += 1
        for cell in row["cells"]:
            amount_position = row["amount_position"]
            value_citation = _citation(
                amount_position["locator"], amount_position["raw_source_line"]
            )
            quantity_citations = tuple(
                _citation(item["locator"], item["quote"])
                for item in cell["quantity"]["unit_context_citations"]
            )
            observation = Observation(
                observation_id=f"obs:{row['row_id']}:{cell['period_id']}",
                status="known",
                amount=Decimal(cell["normalized_value"]),
                citations=(value_citation,),
            )
            lines.append(
                StatementLine(
                    line_id=f"line:{row['row_id']}:{cell['period_id']}",
                    statement=statement,
                    item_id=item_id,
                    label=row["label"],
                    period_id=cell["period_id"],
                    display_priority=priority[statement],
                    line_kind="detail",
                    value=observation,
                    quantity=StatementQuantity(
                        kind=cell["quantity"]["kind"],
                        scale=cell["quantity"]["scale"],
                        citations=quantity_citations,
                    ),
                )
            )
    not_applicable = Disclosure(
        status="not_applicable",
        explanation="No add-back or segment data is in this statement projection fixture",
        citations=(_citation("page:3", EXPECTED["fiscal_policy"]["source_lines"][0]),),
    )
    return FinancialBook(
        book_id="tdg-fy2024",
        entity_perimeter="TD Group consolidated",
        accounting_basis="US GAAP",
        currency="USD",
        unit="MILLIONS",
        periods=_periods(),
        accounts=(),
        addbacks=(),
        segments=(),
        kpis=(),
        facilities=(),
        pro_forma=(),
        statement_lines=tuple(lines),
        segment_allocation=(),
        addback_disclosure=not_applicable,
        segment_disclosure=not_applicable,
    )


def _pack_and_review(book: FinancialBook) -> tuple[PreparedPack, FinancialReview]:
    run = Run(
        run_id="cp1-quantity-output-test",
        issuer_id="transdigm",
        issuer_name="TransDigm Group Incorporated",
        as_of=max(
            (period.end_date for period in book.periods if period.end_date),
            default=date(2024, 9, 30),
        ),
        case_kind="public",
    )
    pack = PreparedPack(run=run, sources=())
    review = FinancialReview(
        pack_sha256=pack.content_hash(),
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        books=(book,),
        analysis=(),
    )
    return pack, review


def _report(book: FinancialBook, pack: PreparedPack, review: FinancialReview) -> StatementReport:
    return StatementReport(
        run_id=review.run_id,
        issuer_id=review.issuer_id,
        as_of=review.as_of,
        pack_sha256=pack.content_hash(),
        review_sha256=review.content_hash(),
        book_id=book.book_id,
        currency=book.currency,
        unit=book.unit,
        entity_perimeter=book.entity_perimeter,
        accounting_basis=book.accounting_basis,
        cells=_cells(book),
        limitations=("Independent statement-projection component case",),
    )


def _bound_pack_review(book: FinancialBook) -> tuple[PreparedPack, FinancialReview]:
    pack, review = _pack_and_review(book)
    by_source: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for citation in records(review, Citation):
        by_source[citation.source_id, citation.source_sha256][citation.locator].append(
            citation.quote
        )
    sources = tuple(
        Source(
            source_id=source_id,
            name=source_id,
            status="ready",
            sha256=source_sha256,
            media_type="application/pdf",
            spans=tuple(
                Span(locator=locator, text="\n".join(dict.fromkeys(quotes)))
                for locator, quotes in locators.items()
            ),
        )
        for (source_id, source_sha256), locators in by_source.items()
    )
    pack = PreparedPack(run=pack.run, sources=sources)
    review = review.model_copy(update={"pack_sha256": pack.content_hash()})
    assert validate_financial_review(pack, review) == ()
    return pack, review


def test_frozen_source_oracle_still_matches_its_independent_hash() -> None:
    assert hashlib.sha256((CASE / "expected.json").read_bytes()).hexdigest() == EXPECTED_SHA256
    assert (CASE / "manifest.json").read_text(encoding="utf-8").find(EXPECTED_SHA256) >= 0


def test_all_oracle_families_retain_dimensions_and_ci_transport_identity() -> None:
    book = _book()
    cells = _cells(book)
    reported = tuple(cell for cell in cells if cell.observation_id is not None)

    assert len(reported) == EXPECTED["unit_totals"]["total_cells"] == 280
    assert len({(cell.table_id, cell.item_id, cell.period_id) for cell in reported}) == 280
    assert Counter(cell.table_id for cell in reported) == {
        "T4.4": 90,
        "T4.5": 132,
        "T4.6": 58,
    }

    ci = tuple(cell for cell in reported if cell.item_id.startswith("other:ci_"))
    assert len(ci) == 24
    assert {cell.table_id for cell in ci} == {"T4.4"}
    assert {cell.statement for cell in ci} == {"IS"}
    assert all(any(citation.locator == "page:107" for citation in cell.citations) for cell in ci)
    assert len({cell.item_id for cell in ci}) == 8

    eps = {cell.period_id: cell for cell in reported if cell.item_id == "other:is_18"}
    assert {period: cell.normalized_amount for period, cell in eps.items()} == {
        "FY2024": Decimal("25.62"),
        "FY2023": Decimal("22.03"),
        "FY2022": Decimal("13.38"),
    }
    assert all(
        (cell.quantity_kind, cell.quantity_unit, cell.currency, cell.scale, cell.factor)
        == ("currency_per_share", "USD/share", "USD", "UNITS", Decimal(1))
        for cell in eps.values()
    )
    assert all(
        any(citation.locator == "page:106" for citation in cell.quantity_citations)
        for cell in eps.values()
    )

    shares = {cell.period_id: cell for cell in reported if cell.item_id == "other:is_22"}
    assert {period: cell.normalized_amount for period, cell in shares.items()} == {
        "FY2024": Decimal("57.8"),
        "FY2023": Decimal("57.2"),
        "FY2022": Decimal("58.2"),
    }
    assert all(
        (cell.quantity_kind, cell.quantity_unit, cell.currency, cell.scale, cell.factor)
        == ("shares", "million shares", None, "MILLIONS", Decimal(1_000_000))
        for cell in shares.values()
    )

    cash = {cell.period_id: cell for cell in reported if cell.item_id == "other:bs_01"}
    assert {period: cell.normalized_amount for period, cell in cash.items()} == {
        "FY2024_END": Decimal(6261),
        "FY2023_END": Decimal(3472),
    }
    assert all(cell.period_id.endswith("_END") for cell in cash.values())

    nil_keys = {
        (
            "T4.4"
            if row["statement"] in {"IS", "CI"}
            else "T4.5"
            if row["statement"] == "CFS"
            else "T4.6",
            "other:"
            + ("ci" if row["statement"] == "CI" else row["statement"].casefold())
            + "_"
            + row["row_id"].split("-")[1],
            cell["period_id"],
        )
        for row in EXPECTED["financial_rows"]
        for cell in row["cells"]
        if cell["raw_value"] == "—"
    }
    assert (
        len(nil_keys)
        == EXPECTED["unit_totals"]["existing_financial_reference"]["printed_nil_cells"]
    )
    nil_cells = tuple(
        cell for cell in reported if (cell.table_id, cell.item_id, cell.period_id) in nil_keys
    )
    assert len(nil_cells) == 21
    assert all(
        cell.status == "known"
        and cell.source_amount == cell.normalized_amount == Decimal(0)
        and any("—" in citation.quote for citation in cell.citations)
        for cell in nil_cells
    )


def test_full_statement_view_exposes_units_ci_origin_and_no_nonmonetary_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    book = _book()
    pack, review = _pack_and_review(book)
    report = _report(book, pack, review)
    monkeypatch.setattr(history_module, "statement_report", lambda *_args: report)

    history = statement_history(pack, review, book.book_id)
    assert validate_statement_history(pack, review, history) == ()
    by_computation = {item.computation_id: item for item in history.computations}
    nonmonetary = tuple(value for value in history.values if value.quantity_kind != "monetary")
    assert nonmonetary
    assert all(value.operands == () for value in nonmonetary)
    assert all(
        by_computation[value.computation_id].operation in {"input", "unavailable"}
        and by_computation[value.computation_id].operands == ()
        for value in nonmonetary
    )
    constructions = {item.construction_id: item for item in history.constructions}
    source_by_observation = {
        cell.observation_id: cell for cell in report.cells if cell.observation_id
    }
    for value in nonmonetary:
        if value.value.amount is not None:
            construction = constructions[value.construction_id]
            assert construction.own_period_id is not None
            assert len(value.value.observation_ids) == 1
            assert source_by_observation[value.value.observation_ids[0]].period_id == (
                construction.own_period_id
            )
        else:
            assert value.value.reason or value.value.note

    eps_history = next(
        value
        for value in history.values
        if value.item_id == "other:is_18" and value.quantity_kind == "currency_per_share"
    )
    assert any(citation.locator == "page:106" for citation in eps_history.quantity_citations)
    assert any(citation.locator == "page:106" for citation in eps_history.value.citations)

    view = statement_view(pack, review, book.book_id)
    module = next(item for item in view.modules if item.module_id == "CP-1")
    source_facts = tuple(
        fact
        for fact in module.facts
        if fact.field in {period.period_id for period in book.periods}
        and fact.status == "known"
        and fact.citations
    )
    assert len(source_facts) == 280
    ci_facts = tuple(fact for fact in source_facts if fact.row_id.startswith("other:ci_"))
    assert len(ci_facts) == 24
    assert all(fact.label.startswith("CI · ") for fact in ci_facts)
    eps = next(
        fact for fact in source_facts if fact.row_id == "other:is_18" and fact.field == "FY2024"
    )
    assert (eps.amount, eps.unit, eps.currency, eps.scale) == (
        Decimal("25.62"),
        "USD/share",
        "USD",
        Decimal(1),
    )
    assert any(citation.locator == "page:106" for citation in eps.citations)
    shares = next(
        fact for fact in source_facts if fact.row_id == "other:is_22" and fact.field == "FY2024"
    )
    assert (shares.amount, shares.unit, shares.currency, shares.scale) == (
        Decimal("57.8"),
        "million shares",
        None,
        Decimal(1_000_000),
    )
    assert any(citation.locator == "page:106" for citation in shares.citations)


def test_canonical_and_prose_currency_scale_comes_from_fact_scale() -> None:
    million = Fact(
        fact_id="tdg.cash",
        label="Cash",
        table_id="T4.5",
        row_id="cash",
        field="FY2024",
        amount=Decimal(6261),
        unit="currency",
        currency="USD",
        scale=Decimal(1_000_000),
        period="FY2024",
    )
    thousand = Fact(
        fact_id="tdg.cash.thousands",
        label="Cash",
        table_id="T4.5",
        row_id="cash",
        field="FY2024",
        amount=Decimal(6261000),
        unit="currency",
        currency="USD",
        scale=Decimal(1000),
        period="FY2024",
    )
    share_price = Fact(
        fact_id="tdg.eps",
        label="EPS",
        table_id="T4.4",
        row_id="eps",
        field="FY2024",
        amount=Decimal("25.62"),
        unit="USD/share",
        currency="USD",
        scale=Decimal(1),
        period="FY2024",
    )
    assert figure_unit(million) == "US$ m"
    assert figure_unit(thousand) == "US$ 000"
    assert figure_unit(share_price) == "USD/share"
    assert _scale_of("T4.5", ("FY2024",), [[million]]) == "US$ m"
    with pytest.raises(ValueError, match="mixes amount units"):
        _scale_of("T4.5", ("FY2024", "FY2023"), [[million, thousand]])
    with pytest.raises(ValueError, match="unsupported scale"):
        figure_unit(million.model_copy(update={"scale": Decimal(10)}))


def _scale_fact(unit: str, currency: str | None, scale: int, name: str) -> Fact:
    return Fact(
        fact_id=f"tdg.{name}",
        label=name,
        table_id="T4.9",
        row_id=name,
        field="FY2024",
        amount=Decimal(1),
        unit=unit,
        currency=currency,
        scale=Decimal(scale),
        period="FY2024",
        status="known",
    )


def test_scale_of_treats_equivalent_currency_and_amount_unit_spellings_as_one_scale() -> None:
    cur_m = _scale_fact("currency", "USD", 1_000_000, "cur_m")
    cur_m2 = _scale_fact("currency", "USD", 1_000_000, "cur_m2")
    mil = _scale_fact("MILLIONS", "USD", 1, "mil")
    mil2 = _scale_fact("MILLIONS", "USD", 1, "mil2")
    cur_k = _scale_fact("currency", "USD", 1_000, "cur_k")
    thou = _scale_fact("THOUSANDS", "USD", 1, "thou")
    for row in (
        [cur_m, mil],
        [mil, cur_m],
        [cur_m, cur_m2, mil],  # currency spelling dominant
        [mil, mil2, cur_m],  # MILLIONS spelling dominant
    ):
        assert _scale_of("T4.9", ("A",) * 3, [row]) == "US$ m"
    assert _scale_of("T4.9", ("A", "B"), [[cur_k, thou]]) == "US$ 000"
    assert _scale_of("T4.9", ("A", "B"), [[thou, cur_k]]) == "US$ 000"


@pytest.mark.parametrize(
    "left, right",
    [
        (("currency", "USD", 1_000), ("MILLIONS", "USD", 1)),
        (("MILLIONS", "USD", 1), ("THOUSANDS", "USD", 1)),
        (("MILLIONS", "USD", 1), ("MILLIONS", "EUR", 1)),
        (("MILLIONS", None, 1), ("MILLIONS", "USD", 1)),
        (("currency", "USD", 1_000_000), ("currency", "EUR", 1_000_000)),
    ],
)
def test_scale_of_still_refuses_genuinely_different_scales(
    left: tuple[str, str | None, int], right: tuple[str, str | None, int]
) -> None:
    a = _scale_fact(*left, "a")
    b = _scale_fact(*right, "b")
    for row in ([a, b], [b, a]):
        with pytest.raises(ValueError, match="mixes amount units"):
            _scale_of("T4.9", ("A", "B"), [row])


def test_model_interface_prefers_explicit_cell_scale_and_keeps_legacy_fallback() -> None:
    book = _book()
    tables = _Tables(book)
    columns = SCHEMAS["T4.15"][2]
    fields = {name: None for name in columns}
    fields.update(
        {
            "metric_id": "cash",
            "period_id": "FY2024",
            "value": _Cell(
                Decimal(6261),
                unit="currency",
                currency="USD",
                scale=Decimal(1_000_000),
            ),
        }
    )
    tables.row("T4.15", ("cash",), "FY2024", fields)
    explicit = next(fact for fact in tables.facts if fact.field == "value")
    assert (explicit.unit, explicit.currency, explicit.scale) == (
        "currency",
        "USD",
        Decimal(1_000_000),
    )

    legacy = _Tables(book)
    fields["value"] = _Cell(Decimal(6261), unit="MILLIONS", currency="USD")
    legacy.row("T4.15", ("cash",), "FY2024", fields)
    fallback = next(fact for fact in legacy.facts if fact.field == "value")
    assert fallback.scale == Decimal(1_000_000)


def test_canonical_constructed_projection_keeps_typed_dimensions_and_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    book = _book()
    pack, review = _pack_and_review(book)
    report = _report(book, pack, review)
    monkeypatch.setattr(history_module, "statement_report", lambda *_args: report)
    history = statement_history(pack, review, book.book_id)
    schemas = {key: (title, None, _keys(key)) for key, (title, _) in COLUMNS.items()}
    tables = _Tables(book, schemas=schemas)
    _constructed(tables, history)

    for item_id, unit, currency, factor in (
        ("other:is_18", "USD/share", "USD", Decimal(1)),
        ("other:is_22", "million shares", None, Decimal(1_000_000)),
    ):
        value = next(value for value in history.values if value.item_id == item_id)
        row_id = _id("interface-row", "T4.8", value.value_id)
        projected = next(
            fact for fact in tables.facts if fact.row_id == row_id and fact.unit == unit
        )
        assert (projected.currency, projected.scale) == (currency, factor)
        assert projected.amount is None
        assert projected.limitation
        assert any(citation.locator == "page:106" for citation in projected.citations)


def _quarter_history_book() -> FinancialBook:
    period_citation = quantity_fixtures.cite("interim period date")
    periods = (
        FinancialPeriod(
            period_id="Q1",
            fiscal_year="FY2024",
            fiscal_quarter=1,
            period_type="QUARTER",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            day_count=91,
            audit_status="unaudited",
            currency="USD",
            unit="MILLIONS",
            accounting_basis="US GAAP",
            entity_perimeter="Consolidated",
            citations=(period_citation,),
        ),
        FinancialPeriod(
            period_id="H1",
            fiscal_year="FY2024",
            fiscal_quarter=2,
            period_type="YTD",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            day_count=182,
            audit_status="unaudited",
            currency="USD",
            unit="MILLIONS",
            accounting_basis="US GAAP",
            entity_perimeter="Consolidated",
            citations=(period_citation,),
        ),
    )
    lines = []
    for period_id, amount, name in (("Q1", 10, "Q1"), ("H1", 30, "H1")):
        source = Observation(
            observation_id=f"obs:money:{period_id}",
            status="known",
            amount=Decimal(amount),
            citations=(quantity_fixtures.cite(f"{name} monetary amount {amount}"),),
        )
        lines.append(
            quantity_fixtures.line(
                f"money-{period_id}",
                period_id,
                "other:money_series",
                statement="IS",
                priority=1 if period_id == "Q1" else 3,
            ).model_copy(update={"value": source})
        )
        share_source = Observation(
            observation_id=f"obs:eps:{period_id}",
            status="known",
            amount=Decimal("2.5" if period_id == "Q1" else "3.0"),
            citations=(quantity_fixtures.cite(f"{name} EPS amount"),),
        )
        lines.append(
            quantity_fixtures.line(
                f"eps-{period_id}",
                period_id,
                "other:eps_series",
                statement="IS",
                kind="currency_per_share",
                scale="UNITS",
                priority=2 if period_id == "Q1" else 4,
            ).model_copy(update={"value": share_source})
        )
    return quantity_fixtures.book(tuple(lines)).model_copy(update={"periods": periods})


def _fy_eps_with_quarters_book() -> FinancialBook:
    rows = (
        ("Q1", "QUARTER", 1, date(2025, 1, 1), date(2025, 3, 31), 90),
        ("Q2", "QUARTER", 2, date(2025, 4, 1), date(2025, 6, 30), 91),
        ("Q3", "QUARTER", 3, date(2025, 7, 1), date(2025, 9, 30), 92),
        ("Q4", "QUARTER", 4, date(2025, 10, 1), date(2025, 12, 31), 92),
        ("FY2025", "FY", None, date(2025, 1, 1), date(2025, 12, 31), 365),
    )
    period_citation = quantity_fixtures.cite("FY2025 quarter schedule")
    periods = tuple(
        FinancialPeriod(
            period_id=period_id,
            fiscal_year="FY2025",
            fiscal_quarter=quarter,
            period_type=period_type,
            start_date=start,
            end_date=end,
            day_count=days,
            audit_status="unaudited" if period_type == "QUARTER" else "audited",
            currency="USD",
            unit="MILLIONS",
            accounting_basis="US GAAP",
            entity_perimeter="Consolidated",
            citations=(period_citation,),
            component_period_ids=("Q1", "Q2", "Q3", "Q4") if period_id == "FY2025" else (),
        )
        for period_id, period_type, quarter, start, end, days in rows
    )
    amounts = {"Q1": "0.5", "Q2": "0.7", "Q3": "0.6", "Q4": "0.7", "FY2025": "2.5"}
    lines = tuple(
        quantity_fixtures.line(
            f"eps-{period_id}",
            period_id,
            "other:eps_fy",
            statement="IS",
            kind="currency_per_share",
            scale="UNITS",
            priority=index,
        ).model_copy(
            update={
                "value": Observation(
                    observation_id=f"obs:eps-fy:{period_id}",
                    status="known",
                    amount=Decimal(amounts[period_id]),
                    citations=(quantity_fixtures.cite(f"{period_id} EPS amount"),),
                )
            }
        )
        for index, period_id in enumerate(amounts, start=1)
    )
    return quantity_fixtures.book(lines).model_copy(update={"periods": periods})


def test_fix_round_one_history_formula_evidence_and_canonical_dimensions() -> None:
    book = _quarter_history_book()
    pack, review = _bound_pack_review(book)
    history = statement_history(pack, review, book.book_id)
    assert validate_statement_history(pack, review, history) == ()
    constructions = {item.construction_id: item for item in history.constructions}
    q2_money = next(
        item
        for item in history.values
        if item.item_id == "other:money_series"
        and constructions[item.construction_id].label.startswith("Q2")
    )
    assert q2_money.value.amount == Decimal(20)
    assert len(q2_money.operands) == 2

    q2_eps = next(
        item
        for item in history.values
        if item.item_id == "other:eps_series"
        and constructions[item.construction_id].label.startswith("Q2")
    )
    assert q2_eps.value.amount is None
    assert q2_eps.operands == ()
    assert set(q2_eps.value.observation_ids) == {"obs:eps:Q1", "obs:eps:H1"}
    assert {citation.quote for citation in q2_eps.value.citations} >= {
        "Q1 EPS amount",
        "H1 EPS amount",
        "unit context",
    }
    assert {citation.quote for citation in q2_eps.quantity_citations} >= {"unit context"}
    assert (q2_eps.quantity_unit, q2_eps.currency, q2_eps.factor) == (
        "USD/share",
        "USD",
        Decimal(1),
    )

    view = statement_view(pack, review, book.book_id)
    module = next(module for module in view.modules if module.module_id == "CP-1")
    q2_fact = next(
        fact
        for fact in module.facts
        if fact.row_id == "other:money_series"
        and fact.field == _id("statement-column", q2_money.construction_id)
    )
    assert q2_fact.amount == Decimal(20)
    assert "Q1: 10" in (q2_fact.formula or "") and "H1: 30" in (q2_fact.formula or "")
    assert "nonmonetary" not in (q2_fact.formula or "")
    q2_eps_fact = next(
        fact
        for fact in module.facts
        if fact.row_id == "other:eps_series"
        and fact.field == _id("statement-column", q2_eps.construction_id)
    )
    assert q2_eps_fact.amount is None
    assert {citation.quote for citation in q2_eps_fact.citations} >= {
        "Q1 EPS amount",
        "H1 EPS amount",
        "unit context",
    }

    tables = _Tables(
        book, schemas={key: (title, None, _keys(key)) for key, (title, _) in COLUMNS.items()}
    )
    _constructed(tables, history)
    q2_eps_t48 = next(
        fact
        for fact in tables.facts
        if fact.table_id == "T4.8"
        and fact.unit == "USD/share"
        and fact.calculation_id == q2_eps.computation_id
    )
    assert q2_eps_t48.amount is None
    assert {citation.quote for citation in q2_eps_t48.citations} >= {
        "Q1 EPS amount",
        "H1 EPS amount",
        "unit context",
    }
    downstream = SimpleNamespace(
        inputs=SimpleNamespace(
            narrative=SimpleNamespace(inputs=SimpleNamespace(ledger=SimpleNamespace(kpis=None)))
        )
    )
    _calculations(tables, downstream, history)
    q2_eps_t49 = next(
        fact
        for fact in tables.facts
        if fact.table_id == "T4.9" and fact.calculation_id == q2_eps.computation_id
    )
    assert (q2_eps_t49.unit, q2_eps_t49.currency, q2_eps_t49.scale) == (
        "USD/share",
        "USD",
        Decimal(1),
    )
    assert q2_eps_t49.amount is None
    assert {citation.quote for citation in q2_eps_t49.citations} >= {
        "Q1 EPS amount",
        "H1 EPS amount",
        "unit context",
    }
    q2_money_t49 = next(
        fact
        for fact in tables.facts
        if fact.table_id == "T4.9" and fact.calculation_id == q2_money.computation_id
    )
    assert (q2_money_t49.amount, q2_money_t49.unit, q2_money_t49.currency, q2_money_t49.scale) == (
        Decimal(20),
        "currency",
        "USD",
        Decimal(1_000_000),
    )
    q2_money_computation_ids = {
        q2_money.computation_id,
        *(operand.computation_id for operand in q2_money.operands),
    }
    q2_money_graph_facts = tuple(
        fact
        for fact in tables.facts
        if fact.table_id == "T4.9" and fact.calculation_id in q2_money_computation_ids
    )
    assert {fact.calculation_id for fact in q2_money_graph_facts} == q2_money_computation_ids
    assert all(
        (fact.unit, fact.currency, fact.scale) == ("currency", "USD", Decimal(1_000_000))
        for fact in q2_money_graph_facts
    )


def test_fix_round_one_preserves_all_180_accepted_legacy_balance_sheet_durations() -> None:
    periods = ("FY2024",)
    legacy_lines = tuple(
        StatementLine(
            line_id=f"legacy-bs-{index}-{period_id}",
            statement="BS",
            item_id=f"other:legacy_bs_{index:02d}",
            label=f"Legacy balance observation {index:02d}",
            period_id=period_id,
            display_priority=index + 1,
            line_kind="detail",
            value=Observation(
                observation_id=f"obs:legacy-bs-{index}:{period_id}",
                status="known",
                amount=Decimal(index),
                citations=(quantity_fixtures.cite(f"legacy FY balance {index} {period_id}"),),
            ),
        )
        for index in range(180)
        for period_id in periods
    )
    book = quantity_fixtures.book(legacy_lines)
    pack, review = _bound_pack_review(book)
    cells = _cells(book)
    legacy_cells = tuple(
        cell
        for cell in cells
        if cell.table_id == "T4.6" and cell.item_id.startswith("other:legacy_bs_")
    )
    assert len(legacy_cells) == 180
    view = statement_view(pack, review, book.book_id)
    module = next(module for module in view.modules if module.module_id == "CP-1")
    legacy_facts = tuple(
        fact
        for fact in module.facts
        if fact.table_id == "T4.6"
        and fact.row_id.startswith("other:legacy_bs_")
        and fact.field in periods
    )
    assert len(legacy_facts) == 180
    assert all(
        (fact.status, fact.unit, fact.currency, fact.scale)
        == ("known", "currency", "USD", Decimal(1_000_000))
        for fact in legacy_facts
    )


def test_fix_round_one_t49_direct_fy_eps_keeps_per_share_dimensions() -> None:
    book = _fy_eps_with_quarters_book()
    pack, review = _bound_pack_review(book)
    history = statement_history(pack, review, book.book_id)
    fy_eps = next(
        value
        for value in history.values
        if value.item_id == "other:eps_fy" and value.value.amount == Decimal("2.5")
    )
    schemas = {key: (title, None, _keys(key)) for key, (title, _) in COLUMNS.items()}
    tables = _Tables(book, schemas=schemas)
    downstream = SimpleNamespace(
        inputs=SimpleNamespace(
            narrative=SimpleNamespace(inputs=SimpleNamespace(ledger=SimpleNamespace(kpis=None)))
        )
    )
    _calculations(tables, downstream, history)
    projected = next(
        fact
        for fact in tables.facts
        if fact.table_id == "T4.9" and fact.calculation_id == fy_eps.computation_id
    )
    assert (projected.amount, projected.unit, projected.currency, projected.scale) == (
        Decimal("2.5"),
        "USD/share",
        "USD",
        Decimal(1),
    )
    assert all(
        fact.unit == "USD/share" and fact.currency == "USD" and fact.scale == Decimal(1)
        for fact in tables.facts
        if fact.table_id == "T4.9"
        and fact.row_id == projected.row_id
        and fact.calculation_id is not None
    )


def test_canonical_audit_source_positions_retain_statement_dimensions_and_unit_citations() -> None:
    positions = _positions(_book())
    source_positions = tuple(
        position for position in positions if position.register_id == "statement_lines"
    )
    assert len(source_positions) == 280
    eps = next(position for position in source_positions if position.row_id == "line:IS-18:FY2024")
    assert (eps.quantity_kind, eps.currency, eps.scale, eps.factor, eps.unit) == (
        "currency_per_share",
        "USD",
        "UNITS",
        Decimal(1),
        "USD/share",
    )
    assert any(citation.locator == "page:106" for citation in eps.quantity_citations)
    shares = next(
        position for position in source_positions if position.row_id == "line:IS-22:FY2024"
    )
    assert (shares.quantity_kind, shares.currency, shares.scale, shares.factor, shares.unit) == (
        "shares",
        None,
        "MILLIONS",
        Decimal(1_000_000),
        "million shares",
    )


def _cfs_cash_history_book(amounts: dict[tuple[str, str], int]) -> FinancialBook:
    periods = _quarter_history_book().periods  # Q1 (Jan-Mar 2024) and H1 (Jan-Jun 2024)
    lines = tuple(
        quantity_fixtures.line(f"{item}-{period_id}", period_id, item, priority=index).model_copy(
            update={
                "value": Observation(
                    observation_id=f"obs:{item}:{period_id}",
                    status="known",
                    amount=Decimal(amount),
                    citations=(quantity_fixtures.cite(f"{item} {period_id} {amount}"),),
                )
            }
        )
        for index, ((item, period_id), amount) in enumerate(amounts.items(), start=1)
    )
    return quantity_fixtures.book(lines).model_copy(update={"periods": periods})


def _history_by_label(book: FinancialBook) -> dict[tuple[str, str], PeriodValue]:
    pack, review = _bound_pack_review(book)
    history = statement_history(pack, review, book.book_id)
    assert validate_statement_history(pack, review, history) == ()
    labels = {item.construction_id: item.label for item in history.constructions}
    return {(labels[item.construction_id], item.item_id): item.value for item in history.values}


def test_cfs_opening_and_closing_cash_are_balances_not_flows() -> None:
    # A 10-Q CFS printed YTD only: Q1 cash 480 -> 500, H1 cash 480 -> 520.
    values = _history_by_label(
        _cfs_cash_history_book(
            {
                ("opening_cash", "Q1"): 480,
                ("opening_cash", "H1"): 480,
                ("closing_cash", "Q1"): 500,
                ("closing_cash", "H1"): 520,
                ("net_cash_change", "Q1"): 20,
                ("net_cash_change", "H1"): 40,
            }
        )
    )
    # Hand-derived: Q2 24 closing cash is the cash at 2024-06-30, H1's printed 520
    # (never 520 - 500 = 20); LTM Q2 24 ends the same day, so it is 520 too.
    for label in ("Q2 24", "LTM Q2 24"):
        closing = values[(label, "closing_cash")]
        assert closing.amount == Decimal(520)
        assert closing.observation_ids == ("obs:closing_cash:H1",)
    # Q2 24 opening cash is the cash at 2024-03-31: no opening-cash line starts on
    # 2024-04-01, so it is Q1's printed closing cash 500 (never 480 - 480 = 0).
    opening = values[("Q2 24", "opening_cash")]
    assert opening.amount == Decimal(500)
    assert opening.observation_ids == ("obs:closing_cash:Q1",)
    assert "CFS closing cash at 2024-03-31" in (opening.note or "")
    # No balance is stated at 2023-06-30, the day before LTM Q2 24 starts.
    assert values[("LTM Q2 24", "opening_cash")].amount is None
    # Net cash change is still a flow: 40 - 20 = 20.
    assert values[("Q2 24", "net_cash_change")].amount == Decimal(20)


def test_cfs_opening_cash_without_a_balance_at_its_date_stays_missing() -> None:
    # Only YTD opening cash (at 2023-12-31) is printed; nothing states 2024-03-31.
    values = _history_by_label(
        _cfs_cash_history_book({("opening_cash", "Q1"): 480, ("opening_cash", "H1"): 480})
    )
    opening = values[("Q2 24", "opening_cash")]
    assert opening.amount is None  # never 480 - 480 = 0
    assert opening.calculation_status != "Calculated"


@pytest.mark.parametrize(
    ("raw", "shown", "value_class"),
    [
        # S15-C03: an outflow is shown negative, but a source zero keeps its lexeme (never "-0"),
        # so it stays an unchanged source value. Expected by hand.
        ("0", "0", "source"),
        ("0.00", "0.00", "source"),
        ("-0", "-0", "source"),  # the source's own lexeme
        ("-0.00", "-0.00", "source"),
        ("12.5", "-12.5", "normalized"),
        ("-12.5", "-12.5", "source"),
    ],
)
def test_an_outflow_zero_keeps_its_source_lexeme(raw: str, shown: str, value_class: str) -> None:
    from deploy_vii.model_interface import _observed

    cite = Citation(source_id="s", source_sha256="a" * 64, locator="page:1", quote="Dividends 0")
    amount = Decimal(raw)
    observed = Observation(observation_id="o", status="known", amount=amount, citations=(cite,))
    book = SimpleNamespace(unit="MILLIONS", currency="USD")
    cell = _observed(observed, book, outflow=True)  # type: ignore[arg-type]
    assert (str(cell.value), cell.value_class, str(cell.source_amount)) == (shown, value_class, raw)
