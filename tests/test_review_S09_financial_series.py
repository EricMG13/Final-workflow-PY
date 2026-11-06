"""S09 review regressions for the CP-1 chart producer (`financial_series`).

A register consistently in one non-USD currency is charted in that currency; a register stating
several currencies, or a facility stated in another currency, is an explicit unsupported reason;
four trailing quarters that are not Q1-Q4 of one fiscal year are a reason, not an exception.
Expected amounts are literals (the same frozen oracle values `test_financial_series` reads).
"""

from decimal import Decimal

import pytest
from test_financial_series import amounts, change, fixture

from deploy_workflow.financial_series import cp1_chart_series

S3_AMOUNTS = [
    Decimal(v)
    for v in ("16.25", "17.5", "18.75", "20", "0", "0", "0", "0", "16.25", "17.5", "18.75", "20")
]


def _recurrency(module, currency, *, rows=None):
    """Every USD money fact and T4.14/T4.18 currency text of `rows` (all rows: None) restated."""
    facts = []
    for fact in module.facts:
        if rows is not None and fact.row_id not in rows:
            facts.append(fact)
            continue
        updates = {}
        if fact.currency == "USD":
            updates["currency"] = currency
        if fact.text == "USD":
            updates["text"] = currency
        facts.append(fact.model_copy(update=updates) if updates else fact)
    return module.model_copy(update={"facts": tuple(facts)})


def test_a_consistent_eur_register_is_charted_in_eur():
    module = _recurrency(fixture(), "EUR")
    figures = cp1_chart_series(module)
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert [f.unit for f in figures] == ["x", "x", "EUR m", "EUR m", "EUR m"]
    assert all(f.reason is None for f in figures)
    assert amounts(module, figures[2]) == S3_AMOUNTS
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert figures[3].series == ("Northbridge Term Loan (term-loan)",)
    facts = {f.fact_id: f for f in module.facts}
    assert {facts[p.fact_id].currency for f in (figures[2], figures[4]) for p in f.points} == {
        "EUR"
    }


def test_the_usd_register_keeps_its_pinned_unit_spelling():
    assert [f.unit for f in cp1_chart_series(fixture())] == ["x", "x", "US$m", "US$m", "US$m"]


def test_a_eur_fact_in_a_usd_register_still_fails_closed():
    module = change(fixture(), table="T4.10", row="T4.10.cash_closing", currency="EUR")
    with pytest.raises(ValueError, match="Incompatible chart dimensions"):
        cp1_chart_series(module)


def test_a_register_stating_two_currencies_gives_money_figures_a_reason():
    module = _recurrency(fixture(), "GBP", rows={"T4.14.q1-2025"})
    figures = {f.fig_id: f for f in cp1_chart_series(module)}
    for fig_id in ("S.3", "S.4", "S.5"):
        figure = figures[fig_id]
        assert figure.points == ()
        assert figure.reason is not None and "more than one currency (GBP, USD)" in figure.reason
    # The multiples carry no currency: they are still charted from the register.
    assert amounts(module, figures["S.2"]) == [None, None, None, Decimal(6)]
    assert figures["S.1"].reason is None and figures["S.2"].reason is None


def test_a_facility_in_another_currency_is_a_reason_not_a_conversion():
    module = change(fixture(), table="T4.18", row="T4.18.q4-2025", field="currency", text="GBP")
    figure = cp1_chart_series(module)[3]
    assert figure.points == () and figure.series == ()
    assert figure.reason == (
        "Facility term-loan is stated in GBP, not the register currency USD; "
        "no amount is converted."
    )


def test_a_currency_that_is_not_an_iso_code_fails_closed():
    module = change(fixture(), table="T4.14", field="currency", text="usd")
    with pytest.raises(ValueError, match="Unsupported chart currency"):
        cp1_chart_series(module)


def _relabel(module, labels):
    """Set (fiscal_year, fiscal_quarter) of the T4.14 quarter rows named in `labels`."""
    texts = {}
    for row_id, (year, quarter) in labels.items():
        texts[f"T4.14.{row_id}.fiscal_year"] = year
        texts[f"T4.14.{row_id}.fiscal_quarter"] = quarter
    return module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": texts[f.fact_id]}) if f.fact_id in texts else f
                for f in module.facts
            )
        }
    )


def test_trailing_quarters_across_two_fiscal_years_are_a_reason():
    # A July-June fiscal year: the four contiguous quarters are Q3/Q4 FY2024, Q1/Q2 FY2025.
    module = _relabel(fixture(), {"q1-2025": ("2024", "3"), "q2-2025": ("2024", "4")})
    module = _relabel(module, {"q3-2025": ("2025", "1"), "q4-2025": ("2025", "2")})
    figures = cp1_chart_series(module)
    expected = (
        "Charts require Q1 to Q4 of one fiscal year; the four reported QUARTER periods are "
        "Q3 2024, Q4 2024, Q1 2025, Q2 2025; no periods were fabricated."
    )
    for figure in (*figures[:3], figures[4]):
        assert figure.points == () and figure.reason == expected
    # The facility snapshot does not depend on the quarter labels.
    assert amounts(module, figures[3]) == [Decimal(50)]


def test_one_fiscal_year_with_a_date_gap_still_raises():
    module = change(
        fixture(), table="T4.14", row="T4.14.q3-2025", field="start_date", text="2025-07-02"
    )
    with pytest.raises(ValueError, match="noncontiguous"):
        cp1_chart_series(module)


def test_overlapping_quarters_still_raise():
    module = change(
        fixture(), table="T4.14", row="T4.14.q3-2025", field="start_date", text="2025-06-15"
    )
    with pytest.raises(ValueError, match="overlapping"):
        cp1_chart_series(module)
