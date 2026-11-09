"""A facility issued after a balance date holds zero there in the source debt check,
as the kernel adapter reads it (S12-vii-financial-engine-C01)."""

from datetime import date
from decimal import Decimal

from test_cash_scope import book, cite, observation

from deploy_vii.financial_adapter import _facilities
from deploy_vii.financial_contracts import (
    AccountObservation,
    FacilityObservation,
    FinancialBook,
    Observation,
)
from deploy_vii.financial_reconciliation import _debt


def _nil(name: str) -> Observation:
    return Observation(
        observation_id=name, status="missing", amount=None, citations=(), reason="n/a"
    )


def _facility(fid: str, pid: str, amount: int, issued: date | None = None) -> FacilityObservation:
    citation = cite(f"{fid} {amount}", "page:70")
    return FacilityObservation(
        facility_id=fid,
        facility_name=fid,
        period_id=pid,
        facility_type="TERM_LOAN",
        currency="USD",
        carrying_value=observation(f"cv-{fid}-{pid}", amount, citation),
        principal=_nil(f"p-{fid}-{pid}"),
        drawn_amount=_nil(f"d-{fid}-{pid}"),
        commitment=_nil(f"c-{fid}-{pid}"),
        secured_status="SECURED",
        seniority="SENIOR",
        lease_classification="NOT_LEASE",
        margin_or_coupon="Not stated",
        maturity_date=date(2030, 1, 1),
        maturity_limitation=None,
        rate_type="NOT_STATED",
        reference_rate="NOT_STATED",
        spread_bps=_nil(f"s-{fid}-{pid}"),
        floor_bps=_nil(f"f-{fid}-{pid}"),
        fixed_rate=_nil(f"x-{fid}-{pid}"),
        annual_amortisation=_nil(f"a-{fid}-{pid}"),
        terms_citations=(citation,),
        issued_on=issued,
        issuance_citations=(cite("TL-B issued", "page:71"),) if issued else (),
    )


def _debt_book(issued: date) -> FinancialBook:
    """TL-A 100 at every balance date; TL-B 50 with rows only at 2025-12-31 and 2026-06-30;
    reported total debt 100 at 2024-12-31 and 2025-06-30."""
    base = book()
    pids = [p.period_id for p in base.periods if p.period_type == "PERIOD_END"]
    assert pids == ["bs-2024-12-31", "bs-2025-06-30", "bs-2025-12-31", "bs-2026-06-30"]
    facilities = (
        *(_facility("tl-a", pid, 100) for pid in pids),
        *(_facility("tl-b", pid, 50, issued) for pid in pids[2:]),
    )
    accounts = tuple(
        AccountObservation(
            metric_id="total_debt",
            period_id=pid,
            value=observation(f"td-{pid}", 100, cite(f"Total debt 100 {pid}", "page:61")),
        )
        for pid in pids[:2]
    )
    return base.model_copy(update={"facilities": facilities, "accounts": accounts})


def test_debt_check_reads_a_facility_issued_after_the_date_as_zero() -> None:
    b = _debt_book(date(2025, 10, 1))
    period = next(p for p in b.periods if p.period_id == "bs-2025-06-30")
    check = _debt(b, period, {})
    # Hand-derived: TL-A 100 + TL-B 0 (issued 2025-10-01, after 2025-06-30) = 100,
    # equal to the reported total debt 100.
    assert [(t.label, t.amount, t.reason) for t in check.components] == [
        ("tl-a", Decimal(100), None),
        ("tl-b", Decimal(0), None),
    ]
    tl_b = check.components[1]
    assert tl_b.observation_id is None and tl_b.original_amount is None
    assert [c.quote for c in tl_b.citations] == ["TL-B issued"]
    assert (check.calculated_value, check.status) == (Decimal(100), "PASS")
    # The kernel adapter reads the same facility at the same date as the same zero.
    adapter = {
        r.facility_id: r.carrying_value for r in _facilities(b) if r.period_id == period.period_id
    }
    assert adapter == {"tl-a": Decimal(100), "tl-b": Decimal(0)}


def test_debt_check_still_blocks_a_facility_issued_by_the_date_without_a_row() -> None:
    # Issued 2025-06-30, on the balance date itself: it exists then, so a missing
    # row is an absent input, never zero.
    b = _debt_book(date(2025, 6, 30))
    period = next(p for p in b.periods if p.period_id == "bs-2025-06-30")
    check = _debt(b, period, {})
    assert [(t.label, t.amount, t.reason) for t in check.components] == [
        ("tl-a", Decimal(100), None),
        ("tl-b", None, "Not supplied"),
    ]
    assert (check.calculated_value, check.status) == (None, "BLOCK")


def test_a_row_at_the_date_wins_over_the_issuance_zero_in_both_readers() -> None:
    # TL-B is issued 2025-10-01 but a row states 70 at 2025-06-30: the stated row is
    # the observation in the debt check and in the kernel adapter alike, never zero.
    b = _debt_book(date(2025, 10, 1))
    row = _facility("tl-b", "bs-2025-06-30", 70, date(2025, 10, 1))
    b = b.model_copy(update={"facilities": (*b.facilities, row)})
    period = next(p for p in b.periods if p.period_id == "bs-2025-06-30")
    check = _debt(b, period, {})
    # Hand-derived: TL-A 100 + TL-B 70 = 170 against reported total debt 100: not PASS.
    assert [(t.label, t.amount) for t in check.components] == [
        ("tl-a", Decimal(100)),
        ("tl-b", Decimal(70)),
    ]
    assert check.calculated_value == Decimal(170)
    assert check.status != "PASS"
    adapter = {
        r.facility_id: r.carrying_value for r in _facilities(b) if r.period_id == period.period_id
    }
    assert adapter == {"tl-a": Decimal(100), "tl-b": Decimal(70)}
