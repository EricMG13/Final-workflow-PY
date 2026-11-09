"""Small fact projections; these fixtures do not qualify analyst execution."""

import json
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import Citation, Fact, ModuleView
from deploy_workflow.financial_series import cp1_chart_series

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/expected.json").read_text())
S5_ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/s5-expected.json").read_text())
# Adopted financial_model._basis_id('historical', 'Q:<source period id>') identities.
BASES = (
    "166bb94eecfa6fdbd7bbc5a81ef57c48d46696fdc9032c1abe11abc6ad613dbb",
    "89e8b30cb7c8ce8b334dc7fba59bccc2c1dfd5ebc7d7f8b8caa5fff3c766f5cb",
    "36604f9b09d609dfe1b66ec07a153d836a007251b6564d183773b8be2b3c959a",
    "1a39b61b63ee7f787ffcf5706f5dbbea2def3aa196fc2c23e4d88b6d19b834e6",
)
METRICS = (
    "total_leverage_reported",
    "net_leverage_reported",
    "interest_coverage_reported",
    "cash_closing",
    "undrawn_rcf",
    "liquidity",
)
S5_METRICS = ("revenue", "adjusted_ebitda")
# Every S.5 value is read from the frozen S.5 oracle, never typed here.
S5_VALUES = {
    name: [
        Decimal(p["amount_exact"])
        for p in S5_ORACLE["chart_series"][0]["points"]
        if p["series"] == name
    ]
    for name in S5_METRICS
}


def fixture():
    facts = []
    citation = Citation(
        source_id="financial",
        source_sha256=ORACLE["source_authority"]["financial_sha256"],
        locator="page:5",
        quote="final maturity is December 31, 2029",
    )

    def row(table, identity, values, period):
        for field, value in values.items():
            numeric = isinstance(value, Decimal)
            money = field in {
                "principal",
                "carrying_value",
                "drawn_amount",
                "annual_amortisation",
            } or (table == "T4.10" and identity in (*METRICS[3:], *S5_METRICS))
            facts.append(
                Fact(
                    fact_id=f"{table}.{identity}.{field}",
                    label=field,
                    table_id=table,
                    row_id=f"{table}.{identity}",
                    field=field,
                    amount=value if numeric else None,
                    text=None if numeric or value is None else value,
                    status="missing" if value is None else "known",
                    limitation="Not supplied" if value is None else None,
                    period=period,
                    basis="IFRS · consolidated group",
                    citations=(citation,),
                    unit="MILLIONS" if money else "MULTIPLE" if numeric else None,
                    currency="USD" if money else None,
                    scale=Decimal(1000000) if money else Decimal(1),
                )
            )

    dates = ("2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01")
    for i, quarter in enumerate(ORACLE["quarters"]):
        pid = quarter["period_id"]
        row(
            "T4.14",
            pid,
            dict(
                period_id=pid,
                period_type="QUARTER",
                fiscal_year="2025",
                fiscal_quarter=str(i + 1),
                start_date=dates[i],
                end_date=quarter["quarter_end"],
                currency="USD",
                unit="MILLIONS",
                accounting_basis="IFRS",
                entity_perimeter="consolidated group",
            ),
            pid,
        )
        for metric in (*METRICS, *S5_METRICS):
            value = (
                S5_VALUES[metric][i]
                if metric in S5_METRICS
                else quarter[metric]["amount"]
                if metric in METRICS[:3]
                else quarter["cash_millions"]
                if metric == "cash_closing"
                else quarter["undrawn_rcf_millions"]
                if metric == "undrawn_rcf"
                else quarter["liquidity_millions"]
            )
            field = "model-basis:" + BASES[i]
            row("T4.10", metric, {"field_1": metric} if i == 0 else {}, "dashboard")
            row(
                "T4.10",
                metric,
                {field: None if value is None else Decimal(value)},
                f"Q{i + 1} 25: {dates[i]} to {quarter['quarter_end']}",
            )
            facts[-1] = facts[-1].model_copy(
                update=dict(
                    unit="MULTIPLE" if metric in METRICS[:3] else "MILLIONS",
                    currency=None if metric in METRICS[:3] else "USD",
                    scale=Decimal(1) if metric in METRICS[:3] else Decimal(1000000),
                    calculation_id=f"calculation.{metric}.{pid}",
                    value_class="calculated",
                )
            )
        row(
            "T4.18",
            pid,
            dict(
                facility_id="term-loan",
                facility_name="Northbridge Term Loan",
                period_id=pid,
                facility_type="TERM_LOAN",
                principal=Decimal(quarter["total_debt_millions"]),
                carrying_value=Decimal(quarter["total_debt_millions"]),
                drawn_amount=Decimal(quarter["total_debt_millions"]),
                maturity_date="2029-12-31",
                annual_amortisation=Decimal(0),
                currency="USD",
                lease_classification="NOT_LEASE",
            ),
            pid,
        )
    return ModuleView(
        module_id="CP-1",
        title="Financials",
        aliases=(),
        status="restricted",
        artifact_sha256="a" * 64,
        facts=tuple(facts),
    )


def change(module, *, table=None, field=None, row=None, **updates):
    return module.model_copy(
        update={
            "facts": tuple(
                fact.model_copy(update=updates)
                if (table is None or fact.table_id == table)
                and (field is None or fact.field == field)
                and (row is None or fact.row_id == row)
                else fact
                for fact in module.facts
            )
        }
    )


def amounts(module, figure):
    facts = {f.fact_id: f for f in module.facts}
    return [facts[p.fact_id].amount for p in figure.points]


def test_source_first_series_values_identity_and_immutability():
    module = fixture()
    figures = cp1_chart_series(module)
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert [f.kind for f in figures] == ["line", "line", "line", "grouped", "grouped"]
    assert amounts(module, figures[0]) == [
        None,
        None,
        None,
        Decimal(ORACLE["quarters"][3]["total_leverage_reported"]["amount"]),
        None,
        None,
        None,
        Decimal(1),
    ]
    assert amounts(module, figures[1]) == [None, None, None, Decimal(6)]
    assert amounts(module, figures[2]) == [
        Decimal(v)
        for v in (
            "16.25",
            "17.5",
            "18.75",
            "20",
            "0",
            "0",
            "0",
            "0",
            "16.25",
            "17.5",
            "18.75",
            "20",
        )
    ]
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert figures[3].points[0].category == "2029-12-31"
    assert "2025-12-31" in figures[3].title and "principal" in figures[3].title.lower()
    assert figures[2].unit == "US$m"
    for figure in figures:
        assert len({(p.series, p.category) for p in figure.points}) == len(figure.points)
        for point in figure.points:
            assert point.companion_fact_ids
            assert set(point.companion_fact_ids) <= {f.fact_id for f in module.facts}
    with pytest.raises(FrozenInstanceError):
        figures[0].title = "forged"


@pytest.mark.parametrize("status", ["unrun", "blocked", "stale", "candidate", "not_in_pathway"])
def test_only_settled_cp1_is_projected(status):
    assert cp1_chart_series(fixture().model_copy(update={"status": status})) == ()
    assert cp1_chart_series(fixture().model_copy(update={"module_id": "CP-2"})) == ()


@pytest.mark.parametrize(
    "updates",
    [
        dict(unit="UNITS"),
        dict(scale=Decimal(1)),
        dict(currency="EUR"),
        dict(basis="IFRS · borrower"),
        dict(period="FY25: 2025-01-01 to 2025-12-31"),
    ],
)
def test_wrong_dimensions_or_period_fail_closed(updates):
    module = change(
        fixture(),
        table="T4.10",
        field="model-basis:" + BASES[0],
        row="T4.10.cash_closing",
        **updates,
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_missing_rcf_is_gap_and_term_headroom_never_substituted():
    module = change(
        fixture(),
        table="T4.10",
        row="T4.10.undrawn_rcf",
        field="model-basis:" + BASES[0],
        amount=None,
        status="missing",
        limitation="RCF unavailable",
    )
    assert amounts(module, cp1_chart_series(module)[2])[4] is None


def test_missing_quarter_is_disclosed_without_synthetic_points():
    module = fixture()
    module = module.model_copy(
        update={
            "facts": tuple(
                f for f in module.facts if f.row_id not in {"T4.14.q2-2025", "T4.18.q2-2025"}
            )
        }
    )
    figures = cp1_chart_series(module)
    assert all(not f.points and f.reason for f in figures[:3])


def test_missing_maturity_discloses_no_invented_date_or_zero():
    module = change(
        fixture(),
        table="T4.18",
        row="T4.18.q4-2025",
        field="maturity_date",
        text=None,
        status="missing",
        limitation="Maturity not supplied",
    )
    figure = cp1_chart_series(module)[3]
    assert not figure.points and "maturity" in figure.reason.lower()


def test_absent_current_facility_population_cannot_use_prior_balance():
    module = fixture()
    module = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.row_id != "T4.18.q4-2025")}
    )
    figure = cp1_chart_series(module)[3]
    assert not figure.points and figure.reason


def test_duplicate_fact_coordinates_and_missing_metric_fail_closed():
    module = fixture()
    duplicate = module.facts[0].model_copy(update={"fact_id": "duplicate"})
    with pytest.raises(ValueError):
        cp1_chart_series(module.model_copy(update={"facts": (*module.facts, duplicate)}))
    module = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.row_id != "T4.10.cash_closing")}
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_missing_quarters_do_not_hide_a_missing_metric_implementation():
    module = fixture()
    module = module.model_copy(
        update={
            "facts": tuple(
                f
                for f in module.facts
                if f.row_id not in {"T4.14.q2-2025", "T4.18.q2-2025", "T4.10.cash_closing"}
            )
        }
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_malformed_nonknown_maturity_fails_closed_instead_of_claiming_source_gap():
    module = change(
        fixture(),
        table="T4.18",
        row="T4.18.q4-2025",
        field="maturity_date",
        status="missing",
        limitation="Not supplied",
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_nonhistorical_period_cannot_become_current_facility_snapshot():
    module = change(
        fixture(), table="T4.14", row="T4.14.q4-2025", field="period_type", text="FORECAST"
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_empty_period_register_cannot_hide_malformed_facility_payload():
    module = change(
        fixture(),
        table="T4.18",
        row="T4.18.q4-2025",
        field="maturity_date",
        status="missing",
        limitation="Not supplied",
    )
    module = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.table_id != "T4.14")}
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def _with_period(module, pid, kind, start, end):
    """`module` plus a T4.14 row copied from q1-2025 with the given identity and dates; the fiscal
    quarter is not applicable (as the FY alias below writes it). No T4.10 or T4.18 row is added."""
    added = []
    for f in module.facts:
        if f.row_id != "T4.14.q1-2025":
            continue
        updates = {"fact_id": f"T4.14.{pid}.{f.field}", "row_id": f"T4.14.{pid}", "period": pid}
        text = {"period_id": pid, "period_type": kind, "start_date": start, "end_date": end}
        if f.field in text:
            updates["text"] = text[f.field]
        if f.field == "fiscal_quarter":
            updates.update(text=None, status="not_applicable", limitation=kind)
        added.append(f.model_copy(update=updates))
    return module.model_copy(update={"facts": (*module.facts, *added)})


# S11-C01: a 10-Q book holds a six- or nine-month YTD period and a leverage book an LTM period;
# the contract allows both (financial_contracts.FinancialPeriod.period_type). By hand: the four
# quarters are unchanged, so the five figures S.1-S.5 are all supplied; the LTM ending on the
# latest quarter end (2025-12-31) must not compete with q4-2025 for the facility snapshot, whose
# principal stays the oracle's 50; no chart point may cite the YTD or LTM row.
@pytest.mark.parametrize(
    "pid,kind,start,end",
    [
        ("ytd-h1-2025", "YTD", "2025-01-01", "2025-06-30"),
        ("ltm-q3-2025", "LTM", "2024-10-01", "2025-09-30"),
        ("ltm-q4-2025", "LTM", "2025-01-01", "2025-12-31"),
    ],
)
def test_ytd_and_ltm_register_periods_are_left_out_of_the_charts(pid, kind, start, end):
    module = _with_period(fixture(), pid, kind, start, end)
    figures = cp1_chart_series(module)
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert [f.reason for f in figures] == [None] * 5
    assert all(f.points for f in figures)
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert not any(pid in p.fact_id for f in figures for p in f.points)


def test_a_facility_row_at_a_ytd_period_and_an_ltm_without_dates_are_left_out():
    # By hand: the q4-2025 snapshot is unchanged (principal 50, one point); the facility row dated
    # at the YTD period is validated for its own period and then ignored, and the LTM period
    # needs no end date to be left out of the charts.
    module = _with_period(fixture(), "ytd-h1-2025", "YTD", "2025-01-01", "2025-06-30")
    module = _with_period(module, "ltm-x", "LTM", "2024-07-01", "2025-06-30")
    module = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": None, "status": "not_applicable", "limitation": "LTM"})
                if f.row_id == "T4.14.ltm-x" and f.field == "end_date"
                else f
                for f in module.facts
            )
        }
    )
    twin = [
        f.model_copy(
            update={
                "fact_id": f.fact_id.replace("q4-2025", "ytd-h1-2025"),
                "row_id": "T4.18.ytd-h1-2025",
                "period": "ytd-h1-2025",
                **({"text": "ytd-h1-2025"} if f.field == "period_id" else {}),
            }
        )
        for f in module.facts
        if f.row_id == "T4.18.q4-2025"
    ]
    module = module.model_copy(update={"facts": (*module.facts, *twin)})
    figures = cp1_chart_series(module)
    assert [f.reason for f in figures] == [None] * 5
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert not any("ytd-h1" in p.fact_id or "ltm-x" in p.fact_id for f in figures for p in f.points)


def test_a_period_type_outside_the_contract_still_fails_closed():
    with pytest.raises(ValueError, match="Unsupported historical chart period type"):
        cp1_chart_series(_with_period(fixture(), "wk-2025", "WEEK", "2025-01-01", "2025-01-07"))


def test_fy_q4_snapshot_alias_is_not_double_counted_and_conflict_refuses():
    module = fixture()
    added = []
    for f in module.facts:
        if f.row_id in {"T4.14.q4-2025", "T4.18.q4-2025"}:
            updates = dict(
                fact_id=f.fact_id.replace("q4-2025", "fy-2025"),
                row_id=f.row_id.replace("q4-2025", "fy-2025"),
                period="fy-2025",
            )
            if f.field == "period_id":
                updates["text"] = "fy-2025"
            if f.field == "period_type":
                updates["text"] = "FY"
            if f.field == "start_date":
                updates["text"] = "2025-01-01"
            if f.field == "fiscal_quarter":
                updates.update(text=None, status="not_applicable", limitation="FY")
            added.append(f.model_copy(update=updates))
    module = module.model_copy(update={"facts": (*module.facts, *added)})
    assert amounts(module, cp1_chart_series(module)[3]) == [Decimal(50)]
    module = change(
        module, table="T4.18", row="T4.18.fy-2025", field="principal", amount=Decimal(51)
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def trailing(module, metrics, periods):
    """The quarter facts of `metrics` restated on `periods` (CP-1's trailing period, S13 C01)."""
    quarter = dict(zip(("model-basis:" + b for b in BASES), periods, strict=True))
    return module.model_copy(
        update={
            "facts": tuple(
                fact.model_copy(update={"period": quarter[fact.field]})
                if fact.table_id == "T4.10"
                and fact.row_id.removeprefix("T4.10.") in metrics
                and fact.field in quarter
                else fact
                for fact in module.facts
            )
        }
    )


# CP-1 states the twelve months ending each quarter: Q1-Q3 lack earlier quarters (null start), Q4
# is the 2025 year, 2025-01-01 to 2025-12-31 = 365 days (hand-counted).
LTM = (
    "LTM Q1 25: null to 2025-03-31",
    "LTM Q2 25: null to 2025-06-30",
    "LTM Q3 25: null to 2025-09-30",
    "LTM Q4 25: 2025-01-01 to 2025-12-31",
)


def test_quarter_leverage_and_coverage_may_state_their_trailing_period():
    plain = cp1_chart_series(fixture())
    module = trailing(fixture(), METRICS[:3], LTM)
    figures = cp1_chart_series(module)
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert [amounts(module, f) for f in figures[:2]] == [
        amounts(fixture(), f) for f in plain[:2]
    ]  # the same points, only the stated period differs


@pytest.mark.parametrize(
    "periods",
    [
        ("LTM Q1 25: null to 2025-03-31",) * 4,  # ends at the wrong quarter end
        (*LTM[:3], "LTM Q4 25: 2025-06-01 to 2025-12-31"),  # a 214 day window
        (*LTM[:3], "LTM Q4 25: 2024-01-01 to 2025-12-31"),  # a 731 day window
        (*LTM[:3], "LTM Q4 25: 2025-01-01 to 2025-12-30"),  # ends a day early
        (*LTM[:3], "Q4 25: 2025-01-01 to 2025-12-31"),  # a 365 day span not labelled trailing
        (*LTM[:3], "LTM Q4 25: soon to 2025-12-31"),
    ],
)
def test_trailing_period_of_another_window_fails_closed(periods):
    with pytest.raises(ValueError, match="canonical QUARTER dates"):
        cp1_chart_series(trailing(fixture(), METRICS[:3], periods))


def test_money_series_do_not_take_the_trailing_period():
    with pytest.raises(ValueError, match="canonical QUARTER dates"):
        cp1_chart_series(trailing(fixture(), METRICS[3:], LTM))


def _fy_alias(module, *, facility):
    """`module` plus an FY 2025 period ending on q4-2025's date (2025-12-31), copied from q4-2025,
    with or without the q4-2025 facility row copied to it."""
    rows = {"T4.14.q4-2025", "T4.18.q4-2025"} if facility else {"T4.14.q4-2025"}
    added = []
    for f in module.facts:
        if f.row_id not in rows:
            continue
        updates = {
            "fact_id": f.fact_id.replace("q4-2025", "fy-2025"),
            "row_id": f.row_id.replace("q4-2025", "fy-2025"),
            "period": "fy-2025",
        }
        text = {"period_id": "fy-2025", "period_type": "FY", "start_date": "2025-01-01"}
        if f.field in text:
            updates["text"] = text[f.field]
        if f.field == "fiscal_quarter":
            updates.update(text=None, status="not_applicable", limitation="FY")
        added.append(f.model_copy(update=updates))
    return module.model_copy(update={"facts": (*module.facts, *added)})


def test_fy_alias_without_facility_rows_uses_the_selected_quarter_snapshot():
    # S11-C03. By hand: q4-2025 and fy-2025 both end 2025-12-31; the explicit quarter is selected
    # and carries the only facility (term-loan, principal 50, maturity 2029-12-31). The FY alias
    # has no facility row, so there is nothing to compare: S.4 is the quarter's one point, 50.
    module = _fy_alias(fixture(), facility=False)
    figures = cp1_chart_series(module)
    assert [f.reason for f in figures] == [None] * 5
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert [p.category for p in figures[3].points] == ["2029-12-31"]
    assert figures[3].points[0].fact_id == "T4.18.q4-2025.principal"
    # An alias that does carry the facility is still compared, and a conflict still refuses.
    conflicting = change(
        _fy_alias(fixture(), facility=True),
        table="T4.18",
        row="T4.18.fy-2025",
        field="principal",
        amount=Decimal(51),
    )
    with pytest.raises(ValueError, match="Conflicting same-date facility snapshot aliases"):
        cp1_chart_series(conflicting)


def _relabel(module, labels=None, starts=None):
    """Set the four quarters' (fiscal_year, fiscal_quarter) labels and start dates in date order."""
    order = ("q1-2025", "q2-2025", "q3-2025", "q4-2025")
    for i, pid in enumerate(order):
        if labels:
            year, quarter = labels[i]
            module = change(module, row=f"T4.14.{pid}", field="fiscal_year", text=year)
            module = change(module, row=f"T4.14.{pid}", field="fiscal_quarter", text=quarter)
        if starts:
            module = change(module, row=f"T4.14.{pid}", field="start_date", text=starts[i])
    return module


SCOPE = (
    "Charts require four contiguous reported QUARTER periods numbered Q1 to Q4 of one fiscal "
    "year; no periods were fabricated."
)


@pytest.mark.parametrize(
    "labels,starts",
    [
        # A March year end: Jan-Mar 2025 is Q4 FY2025, Apr-Dec 2025 are Q1-Q3 FY2026.
        ((("2025", "4"), ("2026", "1"), ("2026", "2"), ("2026", "3")), None),
        # Q2 2024 to Q1 2025 of a calendar year (relabelled; the dates stay contiguous).
        ((("2024", "2"), ("2024", "3"), ("2024", "4"), ("2025", "1")), None),
        # Q1-Q4 of one year but Q3 starts a day late: a one-day gap, not an overlap.
        (None, ("2025-01-01", "2025-04-01", "2025-07-02", "2025-10-01")),
    ],
)
def test_four_quarters_not_q1_to_q4_of_one_year_get_the_unsupported_reason(labels, starts):
    # S11-C04. By hand: S.1-S.3 and S.5 carry the reason with no points; S.4 (the facility
    # snapshot at the latest date, q4-2025, principal 50) does not depend on the quarter strip.
    module = _relabel(fixture(), labels, starts)
    figures = cp1_chart_series(module)
    assert [(f.fig_id, f.reason, f.points) for f in figures if f.fig_id != "S.4"] == [
        (fig_id, SCOPE, ()) for fig_id in ("S.1", "S.2", "S.3", "S.5")
    ]
    assert figures[3].reason is None and amounts(module, figures[3]) == [Decimal(50)]


@pytest.mark.parametrize(
    "labels,starts",
    [
        # Q2 starts on Q1's end date (2025-03-31): the quarters overlap.
        (None, ("2025-01-01", "2025-03-31", "2025-07-01", "2025-10-01")),
        # Q3 starts after its own end (2025-09-30).
        (None, ("2025-01-01", "2025-04-01", "2025-10-01", "2025-10-01")),
        # A repeated (fiscal year, quarter).
        ((("2025", "1"), ("2025", "1"), ("2025", "3"), ("2025", "4")), None),
        # Labels that run backwards against the dates.
        ((("2025", "1"), ("2025", "3"), ("2025", "2"), ("2025", "4")), None),
        # A quarter number outside 1 to 4.
        ((("2025", "1"), ("2025", "2"), ("2025", "3"), ("2025", "5")), None),
    ],
)
def test_contradictory_quarter_identities_still_fail_closed(labels, starts):
    with pytest.raises(ValueError, match="QUARTER"):
        cp1_chart_series(_relabel(fixture(), labels, starts))


def test_an_alias_facility_missing_from_the_selected_quarter_is_no_complete_snapshot():
    # S11-C03 adversarial. By hand: the FY 2025 alias (ending 2025-12-31 like q4-2025) carries a
    # facility "revolver" that the selected quarter lacks, so the population {term-loan,
    # revolver} is not what q4-2025 supplies: S.4 is unsupported, never a one-facility wall.
    module = _fy_alias(fixture(), facility=False)
    extra = []
    for f in fixture().facts:
        if f.row_id != "T4.18.q4-2025":
            continue
        updates = {
            "fact_id": f.fact_id.replace("q4-2025", "fy-2025-revolver"),
            "row_id": "T4.18.fy-2025-revolver",
            "period": "fy-2025",
        }
        if f.field == "period_id":
            updates["text"] = "fy-2025"
        if f.field == "facility_id":
            updates["text"] = "revolver"
        extra.append(f.model_copy(update=updates))
    module = module.model_copy(update={"facts": (*module.facts, *extra)})
    figures = cp1_chart_series(module)
    assert figures[3].reason == "No complete current facility snapshot is supplied."
    assert figures[3].points == ()
    assert [f.reason for f in figures if f.fig_id != "S.4"] == [None] * 4


def test_fiscal_year_labels_of_another_format_across_a_year_end_get_the_reason():
    # S11-C04 adversarial: "FY2025" Q4 then "FY2026" Q1-Q3, contiguous dates: trailing four.
    module = _relabel(
        fixture(), (("FY2025", "Q4"), ("FY2026", "Q1"), ("FY2026", "Q2"), ("FY2026", "Q3"))
    )
    figures = cp1_chart_series(module)
    assert [f.reason for f in figures if f.fig_id != "S.4"] == [SCOPE] * 4
    # The same labels in the normal Q-prefixed form of one year still chart (nothing weakened).
    ok = cp1_chart_series(
        _relabel(
            fixture(), (("FY2025", "Q1"),) + (("FY2025", "Q2"), ("FY2025", "Q3"), ("FY2025", "Q4"))
        )
    )
    assert [f.reason for f in ok] == [None] * 5


@pytest.mark.parametrize(
    "field,text",
    [("currency", "EUR"), ("accounting_basis", "US GAAP"), ("unit", "THOUSANDS")],
)
def test_a_register_in_another_currency_unit_or_basis_gets_the_unsupported_reason(field, text):
    # S11-C08. By hand: every T4.14 period states EUR (or US GAAP, or thousands); the projection
    # converts nothing, so S.1 to S.5 in order each carry the same reason and no points.
    figures = cp1_chart_series(change(fixture(), table="T4.14", field=field, text=text))
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4", "S.5"]
    assert {f.points for f in figures} == {()}
    assert {f.reason for f in figures} == {figures[0].reason}
    assert "another currency, unit, accounting basis or perimeter" in figures[0].reason
