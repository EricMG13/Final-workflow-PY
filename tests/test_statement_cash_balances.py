"""CFS opening/closing cash in statement history stay balances at every column shape:
LTM and quarter columns, zero and negative cash, absent and disagreeing same-date
observations (review of S12-vii-financial-engine-A01)."""

from datetime import date
from decimal import Decimal

import test_statement_quantities as quantity_fixtures
from test_statement_quantity_outputs import _bound_pack_review

from deploy_vii.financial_contracts import FinancialBook, FinancialPeriod, Observation
from deploy_vii.financial_periods import PeriodValue
from deploy_vii.statement_history import statement_history, validate_statement_history


def _period(pid: str, kind: str, quarter: int, start: date, end: date) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=pid,
        fiscal_year=f"FY{end.year}",
        fiscal_quarter=quarter,
        period_type=kind,  # type: ignore[arg-type]
        start_date=start,
        end_date=end,
        day_count=(end - start).days + 1,
        audit_status="unaudited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="US GAAP",
        entity_perimeter="Consolidated",
        citations=(quantity_fixtures.cite("period dates"),),
    )


# Two fiscal years of calendar interim periods; the Q2 24 and LTM Q2 24 columns derive.
PERIODS = (
    _period("FY23", "FY", 4, date(2023, 1, 1), date(2023, 12, 31)),
    _period("Q1_23", "QUARTER", 1, date(2023, 1, 1), date(2023, 3, 31)),
    _period("H1_23", "YTD", 2, date(2023, 1, 1), date(2023, 6, 30)),
    _period("Q1", "QUARTER", 1, date(2024, 1, 1), date(2024, 3, 31)),
    _period("H1", "YTD", 2, date(2024, 1, 1), date(2024, 6, 30)),
)


def _history(
    amounts: dict[tuple[str, str], int], periods: tuple[FinancialPeriod, ...] = PERIODS
) -> dict[tuple[str, str], PeriodValue]:
    lines = tuple(
        quantity_fixtures.line(f"{item}-{pid}", pid, item, priority=index).model_copy(
            update={
                "value": Observation(
                    observation_id=f"obs:{item}:{pid}",
                    status="known",
                    amount=Decimal(amount),
                    citations=(quantity_fixtures.cite(f"{item} {pid} {amount}"),),
                )
            }
        )
        for index, ((item, pid), amount) in enumerate(amounts.items(), start=1)
    )
    book: FinancialBook = quantity_fixtures.book(lines).model_copy(update={"periods": periods})
    pack, review = _bound_pack_review(book)
    report = statement_history(pack, review, book.book_id)
    assert validate_statement_history(pack, review, report) == ()
    labels = {c.construction_id: c.label for c in report.constructions}
    return {(labels[v.construction_id], v.item_id): v.value for v in report.values}


def test_cash_balances_at_quarter_and_ltm_columns() -> None:
    values = _history(
        {
            ("opening_cash", "FY23"): 300,
            ("closing_cash", "FY23"): 450,
            ("opening_cash", "Q1_23"): 300,
            ("closing_cash", "Q1_23"): 340,
            ("opening_cash", "H1_23"): 300,
            ("closing_cash", "H1_23"): 380,
            ("opening_cash", "Q1"): 450,
            ("closing_cash", "Q1"): 470,
            ("opening_cash", "H1"): 450,
            ("closing_cash", "H1"): 520,
        }
    )
    # Hand-derived (cash at the dates): Q2 23 runs 2023-03-31 (340) to 2023-06-30 (380);
    # Q2 24 runs 2024-03-31 (470) to 2024-06-30 (520); LTM Q2 24 runs 2023-06-30 (380,
    # the H1 23 close) to 2024-06-30 (520). None is a difference or sum of balances.
    got = {key: v.amount for key, v in values.items() if key[1] in {"opening_cash", "closing_cash"}}
    assert got == {
        ("Q2 23", "opening_cash"): Decimal(340),
        ("Q2 23", "closing_cash"): Decimal(380),
        ("Q2 24", "opening_cash"): Decimal(470),
        ("Q2 24", "closing_cash"): Decimal(520),
        ("LTM Q2 24", "opening_cash"): Decimal(380),
        ("LTM Q2 24", "closing_cash"): Decimal(520),
    }


def test_zero_and_negative_cash_balances_are_kept_not_missing() -> None:
    values = _history(
        {
            ("opening_cash", "Q1_23"): 9,
            ("closing_cash", "Q1_23"): 0,
            ("closing_cash", "H1_23"): -5,
            ("closing_cash", "Q1"): 0,
            ("closing_cash", "H1"): 0,
        }
    )
    # Hand-derived: cash at 2023-06-30 is the printed H1 23 -5 (an overdraft, sign kept);
    # at 2024-06-30 the printed H1 0 is a known zero; the Q1 closing 0 is the Q2 opening.
    assert values[("Q2 23", "closing_cash")].amount == Decimal(-5)
    assert values[("Q2 24", "closing_cash")].amount == Decimal(0)
    assert values[("Q2 24", "opening_cash")].amount == Decimal(0)
    assert values[("Q2 24", "opening_cash")].observation_ids == ("obs:closing_cash:Q1",)


def test_an_absent_closing_cash_is_missing_never_zero_or_a_difference() -> None:
    # Only Q1's closing cash 500 is printed; nothing states the cash at 2024-06-30.
    values = _history({("opening_cash", "FY23"): 1, ("closing_cash", "Q1"): 500})
    closing = values[("Q2 24", "closing_cash")]
    assert closing.amount is None
    assert closing.calculation_status != "Calculated"
    # The Q1 closing still opens Q2.
    assert values[("Q2 24", "opening_cash")].amount == Decimal(500)


def test_disagreeing_same_date_cash_balances_are_not_chosen_between() -> None:
    periods = (*PERIODS, _period("Q2", "QUARTER", 2, date(2024, 4, 1), date(2024, 6, 30)))
    values = _history(
        {("closing_cash", "Q1"): 500, ("closing_cash", "H1"): 520, ("closing_cash", "Q2"): 525},
        periods,
    )
    # Hand-derived: H1 (520) and Q2 (525) both end 2024-06-30 but disagree, so the LTM
    # Q2 24 closing cash has no single balance: missing, never the first of 520/525.
    closing = values[("LTM Q2 24", "closing_cash")]
    assert closing.amount is None
    assert set(closing.observation_ids) == {"obs:closing_cash:H1", "obs:closing_cash:Q2"}


def test_opening_cash_disagreeing_with_the_prior_closing_cash_is_not_chosen_between() -> None:
    periods = (*PERIODS, _period("Q3_23", "QUARTER", 3, date(2023, 7, 1), date(2023, 9, 30)))
    values = _history(
        {
            ("closing_cash", "H1_23"): 380,
            ("opening_cash", "Q3_23"): 381,
            ("closing_cash", "H1"): 520,
        },
        periods,
    )
    # Hand-derived: LTM Q2 24 opens on 2023-06-30; the H1 23 closing (380) and the Q3 23
    # opening (381) both state that day's cash and disagree: missing.
    assert values[("LTM Q2 24", "opening_cash")].amount is None
    assert values[("LTM Q2 24", "closing_cash")].amount == Decimal(520)
