"""Review S03 (vii financial calculation): regressions for the confirmed review findings.

Expected values are literal: they come from the findings' failure scenarios, not from the code
under test. Each test names the finding it pins.
"""

import copy
import importlib
import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from deploy_vii.canonical_audit import absent_input_limitation
from deploy_vii.contracts import Citation, ModuleView, View
from deploy_vii.cp1_workflow import exact_review
from deploy_vii.distressed_figures import rating_trigger_figures
from deploy_vii.facility_fx import normalize_facilities
from deploy_vii.financial_adapter import _accounts, _facilities
from deploy_vii.financial_contracts import (
    Disclosure,
    FinancialBook,
    FinancialPeriod,
    Observation,
    StatementContribution,
    StatementDisclosure,
    StatementIdentity,
    StatementLine,
)
from deploy_vii.financial_periods import (
    HistoricalReport,
    PeriodConstruction,
    _id,
    contiguous,
    half_last_decimal,
    opening_date,
    stable_id,
)
from deploy_vii.financial_reconciliation import (
    Reconciliation,
    ReconciliationTerm,
    _check,
    _debt,
    _statement_check,
)
from deploy_vii.period_reconciliation import PeriodTerm, _cfo

fw: Any = importlib.import_module("test_financial_workflow")

SHA = "a" * 64
D = Decimal
PREFIX = "Absent input, stated as a limitation on a public filed pack (rulings item 82): "


def cite(quote: str) -> Citation:
    return Citation(source_id="k", source_sha256=SHA, locator="page:1", quote=quote)


def fy_period(pid: str = "fy") -> FinancialPeriod:
    return FinancialPeriod(
        period_id=pid,
        fiscal_year="FY2025",
        fiscal_quarter=None,
        period_type="FY",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        day_count=None,
        audit_status="audited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="US GAAP",
        entity_perimeter="Consolidated",
        citations=(cite("Year ended December 31, 2025"),),
        limitation=None,
    )


def undated(pid: str) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=pid,
        fiscal_year="FY2025",
        fiscal_quarter=None,
        period_type="PERIOD_END",
        start_date=None,
        end_date=None,
        day_count=None,
        audit_status="unaudited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="US GAAP",
        entity_perimeter="Consolidated",
        citations=(cite("Balance sheet (date not printed)"),),
        limitation="The balance sheet date is not printed",
    )


def empty_book(**fields: Any) -> FinancialBook:
    na = Disclosure(status="not_applicable", explanation="none", citations=(cite("none"),))
    base: dict[str, Any] = {
        "book_id": "b",
        "entity_perimeter": "Consolidated",
        "accounting_basis": "US GAAP",
        "currency": "USD",
        "unit": "MILLIONS",
        "periods": (),
        "accounts": (),
        "addbacks": (),
        "segments": (),
        "kpis": (),
        "facilities": (),
        "pro_forma": (),
        "statement_lines": (),
        "statement_identities": (),
        "statement_disclosures": (),
        "segment_allocation": (),
        "addback_disclosure": na,
        "segment_disclosure": na,
    }
    return FinancialBook(**(base | fields))


# --- cp1_workflow.py:126/232/272: retained payloads parse every JSON number exactly -------------


def _observation_text(number: str) -> str:
    citation = cite("Revenue 1,200.0").model_dump_json()
    return f'{{"observation_id":"o","status":"known","amount":{number},"citations":[{citation}]}}'


@pytest.mark.parametrize(
    ("sent", "exact"),
    [
        ("1200.0", "1200.0"),
        ("3624.10", "3624.10"),
        ("1234567890123456.7", "1234567890123456.7"),
        ("1.5e2", "150"),
        ("-0.0", "-0.0"),
    ],
)
def test_a_retained_json_number_keeps_its_printed_digits(sent: str, exact: str) -> None:
    amount = exact_review(Observation, _observation_text(sent)).amount
    assert amount is not None
    assert str(amount) == exact


def test_fy_1200_0_against_quarters_summing_1200_3_blocks() -> None:
    """The printed one-decimal FY gives tolerance 0.05, so a 0.3 difference is unresolved."""
    obs = exact_review(Observation, _observation_text("1200.0"))
    reported = ReconciliationTerm(
        label="revenue",
        observation_id="o",
        original_amount=obs.amount,
        amount=obs.amount,
        citations=obs.citations,
    )
    quarters = tuple(
        ReconciliationTerm(
            label=f"q{i}", observation_id=None, original_amount=D(v), amount=D(v), citations=()
        )
        for i, v in enumerate(("300.1", "300.1", "300.0", "300.1"), 1)
    )
    check = _check(fy_period(), "FY_QUARTERS", "revenue", reported, quarters, "sum of quarters")
    assert (check.tolerance, check.difference, check.status) == (D("0.05"), D("0.3"), "BLOCK")


def test_exact_review_keeps_the_strict_shape_check() -> None:
    """A string field sent as a number is still refused, exactly as the strict JSON parse does."""
    from pydantic import ValidationError

    text = _observation_text("1").replace('"observation_id":"o"', '"observation_id":7')
    with pytest.raises(ValidationError):
        exact_review(Observation, text)


def test_e_notation_never_widens_the_tolerance_past_half_a_unit() -> None:
    assert half_last_decimal(D("1.2E+3")) == D("0.5")
    assert half_last_decimal(D("1200")) == D("0.5")
    assert half_last_decimal(D("1200.0")) == D("0.05")
    assert half_last_decimal(D("-3.125")) == D("0.0005")


# --- period_reconciliation.py:221: CFO converts an outflow magnitude to the target sign ---------


def _cfo_book() -> FinancialBook:
    quote = cite("Net cash used in operating activities 5")

    def line(lid: str, item: str, amount: int, *, outflow: bool = False) -> StatementLine:
        return StatementLine(
            line_id=lid,
            statement="CFS",
            item_id=item,
            label=lid,
            period_id="fy",
            display_priority={"cfo": 1, "loss": 2, "da": 3, "wc": 4}[lid],
            line_kind="subtotal" if lid == "cfo" else "detail",
            value=Observation(
                observation_id="obs-" + lid, status="known", amount=D(amount), citations=(quote,)
            ),
            sign_convention="outflow_magnitude" if outflow else "signed",
            sign_citations=(quote,) if outflow else (),
        )

    identity = StatementIdentity(
        identity_id="cfo-id",
        period_id="fy",
        target_line_id="cfo",
        components=(
            StatementContribution(line_id="loss", coefficient=1),
            StatementContribution(line_id="da", coefficient=-1),
            StatementContribution(line_id="wc", coefficient=-1),
        ),
        explanation="used = loss - D&A - WC",
        citations=(quote,),
    )
    complete = Disclosure(status="complete", explanation="all", citations=(quote,))
    return empty_book(
        periods=(fy_period(),),
        statement_lines=(
            line("cfo", "cfo_ncfo", 5, outflow=True),
            line("loss", "other:net-loss", 12),
            line("da", "other:d-and-a", 3),
            line("wc", "other:working-capital", 4),
        ),
        statement_identities=(identity,),
        statement_disclosures=(
            StatementDisclosure(statement="CFS", period_id="fy", disclosure=complete),
        ),
    )


def test_constructed_cfo_outflow_magnitude_agrees_after_target_sign_conversion() -> None:
    """Printed 'used in operating activities 5' = 12 - 3 - 4; the kernel holds CFO -5."""
    book = _cfo_book()
    source = _statement_check(book, book.periods[0], "CFS", "cfo_ncfo", "CFO_IDENTITY")
    assert (source.status, source.reported_value, source.calculated_value) == ("PASS", 5, 5)
    kernel = next(r for r in _accounts(book) if r.metric_id == "cfo_ncfo")
    assert kernel.value == D(-5)
    node = PeriodConstruction(
        construction_id="period:fy",
        column_key="FY:fy",
        label="FY25",
        kind="FY",
        fiscal_year="FY2025",
        fiscal_quarter=None,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        days=365,
        own_period_id="fy",
        stated_period_id=None,
        terms=(),
        formula="reported",
        limitation=None,
    )
    report = HistoricalReport.model_construct(constructions=(node,), periods=book.periods)
    reported = PeriodTerm(
        label="cfo_ncfo",
        value_id="hv",
        amount=D(-5),
        observation_ids=("obs-cfo",),
        citations=(),
        reason=None,
    )
    check = _cfo(book, report, node, reported)
    assert (check.calculated_value, check.difference, check.status) == (D(-5), D(0), "PASS")
    assert [(t.label, t.amount, t.coefficient) for t in check.components] == [
        ("loss", D(12), -1),
        ("da", D(3), 1),
        ("wc", D(4), 1),
    ]


# --- financial_reconciliation.py:339: a facility not yet issued is a sourced zero ---------------


def _issued_later_book(fixed_rate: str | None = None) -> FinancialBook:
    """The synthetic financial case plus New Notes issued 2025-07-01 (rows from q3-2025)."""
    doc = fw.financials(fw.make_pack())
    book = doc["financial"]["books"][0]
    for pid in ("q3-2025", "q4-2025", "fy-2025"):
        base = next(f for f in book["facilities"] if f["period_id"] == pid)
        row = copy.deepcopy(base)
        row.update(
            facility_id="new-notes",
            facility_name="New Notes",
            issued_on="2025-07-01",
            issuance_citations=base["terms_citations"],
        )
        for field in (
            "carrying_value",
            "principal",
            "drawn_amount",
            "commitment",
            "spread_bps",
            "floor_bps",
            "fixed_rate",
            "annual_amortisation",
        ):
            row[field]["observation_id"] = "new-" + row[field]["observation_id"]
        if fixed_rate is not None:
            row.update(rate_type="FIXED", reference_rate="NONE")
            row["spread_bps"].update(status="not_applicable", amount=None, reason="Fixed coupon")
            row["fixed_rate"].update(status="known", amount=fixed_rate, reason=None)
        book["facilities"].append(row)
    dims = {
        "currency": "USD",
        "unit": "MILLIONS",
        "accounting_basis": "IFRS",
        "entity_perimeter": "consolidated group",
    }
    book.update(dims)
    for period in book["periods"]:
        period.update(dims)
    return FinancialBook.model_validate_json(json.dumps(book))


def test_debt_before_a_later_issuance_counts_the_facility_as_a_cited_zero() -> None:
    book = _issued_later_book()
    q2 = next(p for p in book.periods if p.period_id == "q2-2025")
    check = _debt(book, q2, {})
    notes = next(t for t in check.components if t.label == "new-notes")
    issuance = {c for f in book.facilities if f.issued_on for c in f.issuance_citations}
    assert (notes.amount, notes.original_amount, notes.observation_id) == (D(0), D(0), None)
    assert notes.reason is None and notes.citations and set(notes.citations) <= issuance
    assert check.status == "PASS"
    adapter = next(
        r for r in _facilities(book) if r.period_id == "q2-2025" and r.facility_id == "new-notes"
    )
    assert adapter.carrying_value == notes.amount


def test_debt_still_blocks_an_issued_facility_with_no_row() -> None:
    book = _issued_later_book()
    # q4-2025 and fy-2025 share the 2025-12-31 end date: drop both rows.
    rows = tuple(
        f
        for f in book.facilities
        if not (f.facility_id == "new-notes" and f.period_id in {"q4-2025", "fy-2025"})
    )
    book = book.model_copy(update={"facilities": rows})
    q4 = next(p for p in book.periods if p.period_id == "q4-2025")
    notes = next(t for t in _debt(book, q4, {}).components if t.label == "new-notes")
    assert (notes.amount, notes.reason) == (None, "Not supplied")


# --- financial_adapter.py:176: terms_out_of_range only where a row is supplied ------------------


def test_terms_out_of_range_belongs_only_to_periods_with_a_supplied_row() -> None:
    book = _issued_later_book(fixed_rate="0.065")
    flags = {
        r.period_id: r.terms_out_of_range for r in _facilities(book) if r.facility_id == "new-notes"
    }
    assert flags["q2-2025"] is False
    assert flags["q3-2025"] is True


# --- financial_adapter.py:48/98, facility_fx.py:140: undated periods share no date --------------


def _conflicting(oid: str) -> Observation:
    return Observation.model_validate(
        {
            "observation_id": oid,
            "status": "conflicting",
            "amount": None,
            "reason": "Two printed values",
            "citations": (cite("Cash 110 / 115"),),
            "alternatives": (
                {"amount": D(110), "citations": (cite("Cash 110"),), "explanation": "note 4"},
                {"amount": D(115), "citations": (cite("Cash 115"),), "explanation": "page 2"},
            ),
        }
    )


def _known(oid: str, amount: int) -> Observation:
    return Observation(
        observation_id=oid, status="known", amount=D(amount), citations=(cite(f"Cash {amount}"),)
    )


def test_an_undated_conflict_does_not_null_another_undated_balance() -> None:
    from deploy_vii.financial_contracts import AccountObservation

    book = empty_book(
        periods=(undated("pe-a"), undated("pe-b")),
        accounts=(
            AccountObservation(
                metric_id="cash_and_equivalents", period_id="pe-a", value=_conflicting("c-a")
            ),
            AccountObservation(
                metric_id="cash_and_equivalents", period_id="pe-b", value=_known("c-b", 120)
            ),
        ),
    )
    cash = {r.period_id: r.value for r in _accounts(book) if r.metric_id == "cash_and_equivalents"}
    assert cash == {"pe-a": None, "pe-b": D(120)}


def _facility_rows(currency: str) -> tuple[Any, ...]:
    template = next(f for f in _issued_later_book().facilities if f.facility_id != "new-notes")
    rows = []
    for pid, carrying in (("pe-a", _conflicting("f-a")), ("pe-b", _known("f-b", 50))):
        update = {"period_id": pid, "currency": currency, "carrying_value": carrying}
        for field in (
            "principal",
            "drawn_amount",
            "commitment",
            "spread_bps",
            "floor_bps",
            "fixed_rate",
            "annual_amortisation",
        ):
            value = getattr(template, field)
            update[field] = value.model_copy(update={"observation_id": f"{pid}-{field}"})
        rows.append(template.model_copy(update=update))
    return tuple(rows)


def test_an_undated_facility_conflict_does_not_null_another_undated_carrying_value() -> None:
    book = empty_book(periods=(undated("pe-a"), undated("pe-b")), facilities=_facility_rows("USD"))
    carrying = {r.period_id: r.carrying_value for r in _facilities(book)}
    assert carrying == {"pe-a": None, "pe-b": D(50)}


def test_an_undated_foreign_facility_conflict_stays_in_its_own_period() -> None:
    book = empty_book(periods=(undated("pe-a"), undated("pe-b")), facilities=_facility_rows("EUR"))
    reasons = {
        n.period_id: n.reason for n in normalize_facilities(book) if n.field == "carrying_value"
    }
    assert reasons == {
        "pe-a": "Same-date source amount is conflicting",
        "pe-b": "No explicit source-bound FX conversion",
    }


# --- canonical_audit.py:524: soften only an actually absent input -------------------------------


def _term(label: str, amount: str | None) -> ReconciliationTerm:
    return ReconciliationTerm(
        label=label,
        observation_id=None,
        original_amount=None if amount is None else D(amount),
        amount=None if amount is None else D(amount),
        reason="Not supplied" if amount is None else None,
        citations=(),
    )


def _reconciliation(explanation: str, *components: ReconciliationTerm) -> Reconciliation:
    return Reconciliation.model_construct(
        check_id="recon:x",
        period_id="fy-2024",
        reported=_term("revenue", "100"),
        components=components,
        difference=None,
        status="BLOCK",
        explanation=explanation,
    )


NONE: frozenset[str] = frozenset()


def _soften(check: Reconciliation) -> str | None:
    return absent_input_limitation(check, public=True, conflicting=NONE)


def test_a_structural_blocker_with_every_term_present_stays_blocked() -> None:
    quarters = tuple(_term(f"q{i}", "25") for i in range(1, 5))
    check = _reconciliation("Four dated discrete quarters do not span the reported FY", *quarters)
    assert _soften(check) is None
    unknown = _reconciliation("Expense presentation is unknown", _term("cogs", "40"))
    assert _soften(unknown) is None


def test_an_absent_term_or_a_quoted_absent_input_is_still_a_limitation() -> None:
    absent = _soften(_reconciliation("Expense presentation is unknown", _term("cogs", None)))
    assert absent == (PREFIX + "Expense presentation is unknown; absent: cogs (Not supplied)")
    no_components = _reconciliation("Missing reported value or complete independent components")
    assert _soften(no_components) == (
        PREFIX + "Missing reported value or complete independent components"
    )
    partial = _reconciliation("Disclosed segment schedule is partial", _term("operations", "60"))
    assert _soften(partial) == PREFIX + "Disclosed segment schedule is partial"
    child = "cfs-ncfo: Missing reported value or complete independent components"
    assert _soften(_reconciliation(child, _term("cfo", "5"))) == PREFIX + child


# --- distressed_figures.py:161: a real agency source renders DR.6 without raising ---------------


def _cp2h_view(limitations: tuple[str, ...]) -> View:
    module = ModuleView.model_construct(
        module_id="CP-2H", status="accepted", limitations=limitations, facts=()
    )
    return View.model_construct(modules=(module,))


def test_dr6_frame_of_a_real_agency_source_does_not_claim_it_is_synthetic() -> None:
    real = (
        (
            "Agency ratings and outlooks are user-supplied in the context file; trigger terms "
            "are read from the attached agency source."
        ),
    )
    (figure,) = rating_trigger_figures("rating-triggers", _cp2h_view(real), {})
    assert figure.chart.reason is not None
    assert "synthetic" not in figure.chart.reason
    assert figure.chart.reason == (
        "headroom is stated in the rating trigger tables; no headroom chart is drawn"
    )


def test_dr6_frame_of_the_synthetic_source_keeps_the_oracle_text() -> None:
    synthetic = (
        (
            "Agency ratings, outlooks, scale mappings and trigger terms are read from one "
            "synthetic source naming fictional agencies; no real agency report is an input."
        ),
    )
    (figure,) = rating_trigger_figures("rating-triggers", _cp2h_view(synthetic), {})
    assert figure.chart.reason == (
        "agency source is synthetic; a headroom chart waits for a real agency report"
    )


# --- shared helpers (financial_periods) ---------------------------------------------------------


def test_stable_id_keeps_the_former_private_name() -> None:
    assert _id is stable_id
    assert stable_id("k", "a", "b") == stable_id("k", "a", "b") != stable_id("k", "ab")


def test_opening_date_and_contiguity() -> None:
    assert opening_date(date(2025, 1, 1)) == date(2024, 12, 31)
    assert opening_date(None) is None
    assert opening_date(date.min) is None
    assert contiguous(date(2025, 3, 31), date(2025, 4, 1))
    assert not contiguous(date(2025, 3, 31), date(2025, 4, 2))
    assert not contiguous(None, date(2025, 4, 1))
    assert not contiguous(date.max, date.max)  # no OverflowError at the calendar's end
