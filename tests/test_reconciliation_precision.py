"""The reporting-precision tolerance of a reconciliation and the kernel's
"differs from CP-1 stated" note come from the finest place among the figures
compared, never coarser than half a unit. A JSON number's trailing zeros are
dropped by the parse (`1234.0` reads as `Decimal('1234')`) and an exponent form
(`1.2E+3`) shows no printed place, so the reported figure's own exponent alone
would widen the tolerance tenfold or more (review of
S12-vii-financial-engine-A03)."""

from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
import test_cash_scope as cs

from deploy_vii.facility_fx import FacilityNormalization
from deploy_vii.financial_contracts import Observation
from deploy_vii.financial_reconciliation import ReconciliationTerm, _check, _term
from deploy_vii.live.schema import exact_json, json_object
from deploy_vii.model import history
from deploy_vii.model._cells import CONVERTED, DIFFERS, beyond_rounding, half_unit
from deploy_vii.model.frame import SourceRef
from deploy_vii.model.registers import AccountRow, Cp1Registers, FacilityRow, PeriodRow
from deploy_vii.model.statements import statement_frame
from deploy_vii.period_reconciliation import PeriodTerm, _compare

PERIOD = cs.flow(cs.book(), "fy-2025")


def _parsed(amount_text: str, name: str) -> Observation:
    """An observation through the live parse: JSON number -> exact_json -> Pydantic."""
    citation = f'{{"source_id":"k","source_sha256":"{cs.SHA}","locator":"page:1","quote":"q"}}'
    payload = (
        f'{{"observation_id":"{name}","status":"known","amount":{amount_text},'
        f'"citations":[{citation}]}}'
    )
    return Observation.model_validate_json(exact_json(json_object(payload)))


def _stored(amount: str, name: str) -> Observation:
    return Observation(
        observation_id=name, status="known", amount=D(amount), citations=(cs.cite("q"),)
    )


def _reconcile(total: Observation, *parts: Observation) -> tuple[D | None, D | None, str]:
    check = _check(
        PERIOD,
        "SOURCE_STATEMENT_IDENTITY",
        "x",
        _term("total", total),
        tuple(_term(p.observation_id, p) for p in parts),
        "sum",
    )
    return check.tolerance, check.difference, check.status


def test_parsed_trailing_zero_total_is_not_given_a_tenfold_tolerance() -> None:
    # Printed 1,234.0 = 1,000.0 + 233.6? The parse reads 1234 and 1000, but
    # 233.6 shows one decimal: tolerance 0.05; 1233.6 - 1234 = -0.4 -> BLOCK.
    total = _parsed("1234.0", "tot")
    assert total.amount == D(1234) and total.amount.as_tuple().exponent == 0
    tolerance, difference, status = _reconcile(total, _parsed("1000.0", "a"), _parsed("233.6", "b"))
    assert (tolerance, difference, status) == (D("0.05"), D("-0.4"), "BLOCK")


def test_exponent_form_total_is_held_to_at_most_half_a_unit() -> None:
    # "1.2E+3" alone would give 0.5E+2 = 50. Components 1000 + 200.3 = 1200.3:
    # finest place one decimal, tolerance 0.05, difference 0.3 -> BLOCK.
    tolerance, difference, status = _reconcile(
        _stored("1.2E+3", "tot"), _stored("1000", "a"), _stored("200.3", "b")
    )
    assert (tolerance, difference, status) == (D("0.05"), D("0.3"), "BLOCK")
    # Integer components 1000 + 201 = 1201: tolerance 0.5 (never 50), difference 1 -> BLOCK.
    tolerance, difference, status = _reconcile(
        _stored("1.2E+3", "tot"), _stored("1000", "a"), _stored("201", "b")
    )
    assert (tolerance, difference, status) == (D("0.5"), D(1), "BLOCK")
    # 1000 + 200 = 1200 exactly -> PASS at 0.5.
    tolerance, difference, status = _reconcile(
        _stored("1.2E+3", "tot"), _stored("1000", "a"), _stored("200", "b")
    )
    assert (tolerance, difference, status) == (D("0.5"), D(0), "PASS")


def test_same_precision_agreement_still_passes() -> None:
    # 1,000.0 + 233.6 = 1,233.6 printed as 1,233.6: difference 0 within 0.05.
    tolerance, difference, status = _reconcile(
        _parsed("1233.6", "tot"), _parsed("1000.0", "a"), _parsed("233.6", "b")
    )
    assert (tolerance, difference, status) == (D("0.05"), D(0), "PASS")


def test_missing_reported_value_has_no_tolerance() -> None:
    missing = Observation(
        observation_id="tot", status="missing", amount=None, citations=(), reason="not printed"
    )
    tolerance, difference, status = _reconcile(missing, _stored("1", "a"))
    assert (tolerance, difference, status) == (None, None, "BLOCK")


def test_converted_facility_uses_its_printed_amount_not_the_conversion() -> None:
    # Facility printed EUR 1,000 converted at 1.0857 -> USD 1085.7 (not printed).
    # Reported total 1,086 and the facility's printed place are integers:
    # tolerance 0.5; 1085.7 - 1086 = -0.3 -> PASS. The converted amount's
    # decimal place is the rate's, not the issuer's printing.
    normalization = FacilityNormalization(
        normalization_id="n1",
        facility_id="f1",
        period_id=PERIOD.period_id,
        field="carrying_value",
        facility_sha256=cs.SHA,
        conversion_id="c1",
        source_observation_id="obs-f1",
        input_observation_ids=("obs-f1",),
        original_amount=D(1000),
        source_currency="EUR",
        target_currency="USD",
        unit="MILLIONS",
        rate_date=date(2025, 12, 31),
        rate=D("1.0857"),
        amount=D("1085.7"),
        reason=None,
        citations=(cs.cite("EUR 1,000"),),
    )
    facility = ReconciliationTerm(
        label="f1",
        observation_id="obs-f1",
        original_amount=D(1000),
        amount=D("1085.7"),
        citations=(cs.cite("EUR 1,000"),),
        normalization=normalization,
    )
    total = _term("total", _stored("1086", "t"))
    check = _check(PERIOD, "DEBT_TOTAL_EX_LEASES", "total_debt", total, (facility,), "sum")
    assert (check.tolerance, check.difference, check.status) == (D("0.5"), D("-0.3"), "PASS")


def _period_term(amount: str | None) -> PeriodTerm:
    return PeriodTerm(
        label="t",
        value_id=None,
        amount=None if amount is None else D(amount),
        observation_ids=(),
        citations=(),
        reason=None if amount is not None else "absent",
    )


def test_period_check_takes_the_finest_place_among_its_parts() -> None:
    # Reported FY 1234 (parsed from 1,234.0); quarters 300.0 + 300.0 + 300.0 +
    # 333.6 read 300, 300, 300, 333.6 = 1233.6: tolerance 0.05, difference -0.4.
    node = SimpleNamespace(construction_id="fy")
    check = _compare(
        node,  # type: ignore[arg-type]
        "FY_QUARTERS",
        "revenue",
        _period_term("1234"),
        tuple(_period_term(a) for a in ("300", "300", "300", "333.6")),
        "sum",
    )
    assert (check.tolerance, check.difference, check.status) == (D("0.05"), D("-0.4"), "BLOCK")


@pytest.mark.parametrize(
    ("stated", "host", "differs"),
    [
        ("1234", "1233.6", True),  # parsed 1,234.0 vs 1,233.6: 0.4 > 0.05
        ("1.2E+3", "1200.4", True),  # 0.4 > 0.05, not within 50
        ("1.2E+3", "1201", True),  # 1 > 0.5
        ("1.2E+3", "1200", False),
        ("1233.6", "1234", True),  # 0.4 > 0.05, as before
        ("1234", "1234", False),
        ("1234.5", "1234.50", False),
        ("12.30", "12.34", True),  # 0.04 > 0.005 (two decimals)
    ],
)
def test_beyond_rounding_takes_the_finest_place_of_either_figure(
    stated: str, host: str, differs: bool
) -> None:
    assert beyond_rounding(D(stated), D(host)) is differs


def test_half_unit_is_never_coarser_than_half() -> None:
    # Hand-derived: exponents 2, 0 and -2 -> finest -2 -> 0.005; 2 alone -> 0.5.
    assert half_unit((D("1.2E+3"), D(7), D("0.25"))) == D("0.005")
    assert half_unit((D("1.2E+3"),)) == D("0.5")
    assert half_unit(()) == D("0.5")


def test_period_debt_check_ignores_a_converted_facility_place() -> None:
    # Reported total debt 1,586; facilities 500 (printed) and 1085.7 (EUR 1,000
    # converted, not printed): only 1586 and 500 set the place -> tolerance 0.5;
    # 500 + 1085.7 - 1586 = -0.3 -> PASS. Counting the conversion would give
    # 0.05 and a false BLOCK.
    node = SimpleNamespace(construction_id="fy")
    parts = (_period_term("500"), _period_term("1085.7"))
    check = _compare(
        node,  # type: ignore[arg-type]
        "DEBT_TOTAL_EX_LEASES",
        "total_debt",
        _period_term("1586"),
        parts,
        "sum",
        printed=(D(500), None),
    )
    assert (check.tolerance, check.difference, check.status) == (D("0.5"), D("-0.3"), "PASS")


# The kernel: "differs from CP-1 stated" on a recomputed line.
FY = PeriodRow("FY25", "FY2025", None, "FY", "2025-01-01", "2025-12-31", 365, "USD", "MILLIONS", ())
REF = SourceRef("s1", "financial-observation", "x")


def _kernel(accounts: tuple[AccountRow, ...], facilities: tuple[FacilityRow, ...] = ()) -> dict:
    regs = Cp1Registers((FY,), accounts, (), (), (), facilities, (), "USD", "MILLIONS")
    columns = history.historical_columns(regs)
    return statement_frame(history.account_frame(regs, columns), columns, regs)["FY:FY25"]


def _account(metric: str, amount: str) -> AccountRow:
    return AccountRow(metric, "FY25", D(amount), "VERIFIED", REF)


def test_kernel_notes_a_parsed_trailing_zero_stated_figure_that_differs() -> None:
    # CP-1 printed gross profit 1,234.0 (parsed 1234); 1500.0 - 266.4 = 1233.6.
    # The cogs place (one decimal) gives 0.05; |1234 - 1233.6| = 0.4 -> differs.
    cells = _kernel(
        (_account("revenue", "1500"), _account("cogs", "-266.4"), _account("gross_profit", "1234"))
    )
    gross = cells["gross_profit"]
    assert (gross.value, gross.stated, gross.note) == (D("1233.6"), D(1234), DIFFERS)


def _facility(facility_id: str, amount: str, source: SourceRef) -> FacilityRow:
    return FacilityRow(
        facility_id, facility_id, "FY25", "Term loan", "USD", D(amount), None, None,
        "Unsecured", "Senior", "NONE", None, "Not stated", "Fixed", "None",
        None, None, None, None, source,
    )  # fmt: skip


def test_kernel_debt_total_ignores_the_places_of_a_converted_facility() -> None:
    # CP-1 total debt 1,586; facilities 500 (USD, printed) and 1085.7 (EUR 1,000
    # converted, places of the rate): tolerance 0.5 from 1586 and 500;
    # |1586 - 1585.7| = 0.3 -> no note. Counting 1085.7 would note it (0.05).
    converted = SourceRef("n1", CONVERTED, "1085.7")
    facilities = (_facility("a", "500", REF), _facility("b", "1085.7", converted))
    total = _kernel((_account("total_debt", "1586"),), facilities)["total_debt"]
    assert (total.value, total.stated, total.note) == (D("1585.7"), D(1586), None)
    # The same 1085.7 printed (not converted) sets the place: 0.3 > 0.05 -> noted.
    printed = (_facility("a", "500", REF), _facility("b", "1085.7", REF))
    total = _kernel((_account("total_debt", "1586"),), printed)["total_debt"]
    assert total.note == DIFFERS


def test_negative_parsed_trailing_zero_total_is_held_to_the_finest_place() -> None:
    # Printed (1,234.0) = (1,000.0) + (233.6)? Parsed -1234, -1000, -233.6:
    # tolerance 0.05; -1233.6 - (-1234) = 0.4 -> BLOCK.
    tolerance, difference, status = _reconcile(
        _parsed("-1234.0", "tot"), _parsed("-1000.0", "a"), _parsed("-233.6", "b")
    )
    assert (tolerance, difference, status) == (D("0.05"), D("0.4"), "BLOCK")


def test_half_unit_keeps_a_stored_trailing_zero_place() -> None:
    # Hand-derived: D("1.50") is written to two decimals -> 0.005; D("1.5") to one -> 0.05.
    assert half_unit((D("1.50"),)) == D("0.005")
    assert half_unit((D("1.5"), D(7))) == D("0.05")


def test_beyond_rounding_printed_figures_replace_the_hosts_own_places() -> None:
    # Host 1585.70 is a sum of 500 and 1085.7 (EUR conversion, not printed): the
    # printed 500 sets the place with the stated 1586 -> 0.5; |1586 - 1585.70| = 0.3.
    assert beyond_rounding(D(1586), D("1585.70"), [D(500)]) is False
    # No printed figures left (every part converted): the stated figure's place alone.
    assert beyond_rounding(D(1586), D("1585.70"), []) is False
    # Defaulting to the host would read its conversion places: 0.005 -> differs.
    assert beyond_rounding(D(1586), D("1585.70")) is True


def test_check_with_a_derived_three_decimal_part_set_by_integer_peers_stays_exact() -> None:
    # 33.333 + 33.333 + 33.334 = 100.000 against a printed 100.000: PASS at 0.0005.
    total, parts = (
        _stored("100.000", "t"),
        [_stored(p, f"p{i}") for i, p in enumerate(("33.333", "33.333", "33.334"))],
    )
    assert _reconcile(total, *parts) == (D("0.0005"), D("0.000"), "PASS")
