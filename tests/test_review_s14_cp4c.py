"""S14 review fixes for CP-4C: claim units, the CP-4 head refusal and the T4.18 reader.

Expected values are literal: the issue texts, the statement wording and the CP-1 T4.18 terms
are written here, not taken from the module's own output.
"""

import dataclasses
from typing import Any

import pytest
import test_cp4c_valuation_context as vc
import test_method_cp4c as m

from deploy_vii.contracts import Fact, Module
from deploy_workflow.owners import cp4c
from deploy_workflow.owners.period_basis import DEFAULT_BASIS

UNITS_ISSUE = (
    "claims[{i}].amount_quote: the quoted statement does not state its amounts in USD millions, "
    "so its row is not read as a claim"
)


def _page4(ctx: cp4c.Cp4cContext, old: str, new: str) -> cp4c.Cp4cContext:
    """The context with `old` replaced by `new` on the financial page:4 statement."""
    fin = next(s for s in ctx.pack.sources if s.source_id == "financial")
    spans = tuple(
        sp.model_copy(update={"text": sp.text.replace(old, new)}) if sp.locator == "page:4" else sp
        for sp in fin.spans
    )
    sources = tuple(
        fin.model_copy(update={"spans": spans}) if s.source_id == "financial" else s
        for s in ctx.pack.sources
    )
    return dataclasses.replace(ctx, pack=ctx.pack.model_copy(update={"sources": sources}))


POSITIVE_HEADER = "IFRS; consolidated group; USD; amounts in millions; unaudited"


@pytest.mark.parametrize(
    "header",
    [
        "IFRS; consolidated group; USD; amounts in thousands; unaudited",  # another scale
        "IFRS; consolidated group; EUR; amounts in millions; unaudited",  # another currency
        "IFRS; consolidated group; amounts in millions; unaudited",  # no currency stated
        "IFRS; consolidated group; USD; unaudited",  # no scale stated
    ],
)
def test_a_source_row_on_a_statement_not_in_run_millions_is_refused(header: str) -> None:
    """adv S14 cp4c.py:637: the cited row's cell is never stamped USD millions unless the page's
    own statement says so; the refusal is a content issue and the compose step never reads it."""
    ctx = _page4(m._context("positive"), POSITIVE_HEADER, header)
    sub = m._inputs("positive").submission
    sources = [(i, c.amount_source) for i, c in enumerate(sub.claims)]
    assert sources == [(0, "cp1_total_debt"), (1, "source_row"), (2, "source_row")]
    issues = cp4c.content_issues(cp4c.Cp4cInputs(context=ctx, submission=sub))
    assert issues[:2] == (UNITS_ISSUE.format(i=1), UNITS_ISSUE.format(i=2))
    with pytest.raises(ValueError, match="c02 reads no number"):
        cp4c.claim_classes(sub, ctx)


def test_the_run_millions_statement_still_reads_its_rows() -> None:
    ctx = m._context("positive")
    sub = m._inputs("positive").submission
    claims = {k.class_id: k.claim.amount for k in cp4c.claim_classes(sub, ctx)}
    assert claims == {"c01": m.D("50.00"), "c02": m.D("20.00"), "c03": m.D("10")}
    assert cp4c.states_run_millions("Currency: USD; amounts in millions.\nPeriod end  Q4", "USD")
    assert not cp4c.states_run_millions("USD; amounts in millions.\nNo header here", "USD")


@pytest.mark.parametrize(
    ("fact_id", "text", "issue"),
    [
        (
            "T4.13.rating.rating",
            "Moderate",
            (
                "CP-4 T4.13.rating.rating: the lender protection rating is 'Moderate'; the own "
                "limitation states Insufficient Information, so another rating fails closed "
                "(round 8 A-2 #4)"
            ),
        ),
        (
            "T4.10.r02.conditions",
            "Consent of the majority lenders",
            (
                "CP-4 T4.10.r02.conditions: the additional-debt conditions differ from the "
                "every-lender consent the new-money limitation states, so they fail closed "
                "(round 8 A-2 #4)"
            ),
        ),
    ],
)
def test_a_cp4_head_this_version_cannot_word_is_a_content_issue(
    fact_id: str, text: str, issue: str
) -> None:
    """adv S14 cp4c.py:1589: the refusal is journaled by the validator, so compute never raises
    its own head check after a model response."""
    ctx = m._context("positive")
    facts = tuple(m._refact(f, text=text) if f.fact_id == fact_id else f for f in ctx.cp4.facts)
    bad = dataclasses.replace(ctx, cp4=dataclasses.replace(ctx.cp4, facts=facts))
    sub = m._inputs("positive").submission
    assert cp4c.content_issues(cp4c.Cp4cInputs(context=bad, submission=sub)) == (issue,)
    with pytest.raises(ValueError, match="^CP-4C submission has issues: CP-4 "):
        cp4c.compute(cp4c.Cp4cInputs(context=bad, submission=sub))


# --- the CP-1 T4.18 reader -------------------------------------------------------------------
def _f(table: str, row: str, field: str, text: str) -> Fact:
    return Fact(
        fact_id=f"{table}.{row}.{field}",
        label=f"{row} · {field}",
        table_id=table,
        row_id=row,
        field=field,
        text=text,
    )


def _period(pid: str, kind: str, end: str) -> list[Fact]:
    row = f"p-{pid}"
    return [
        _f("T4.14", row, "period_id", pid),
        _f("T4.14", row, "period_type", kind),
        _f("T4.14", row, "end_date", end),
    ]


def _terms(fid: str, pid: str, secured: str, seniority: str = "SENIOR") -> list[Fact]:
    row = f"{fid}-{pid}"
    return [
        _f("T4.18", row, "facility_id", fid),
        _f("T4.18", row, "period_id", pid),
        _f("T4.18", row, "secured_status", secured),
        _f("T4.18", row, "seniority", seniority),
    ]


PERIODS = [
    *_period("q4-2025", "QUARTER", "2025-12-31"),
    *_period("fy-2025", "FY", "2025-12-31"),
    *_period("q1-2026", "QUARTER", "2026-03-31"),
]
# The issuer's secured facility is `tlb`; it became unsecured in Q1 2026.
TLB = [
    *_terms("tlb", "q4-2025", "SECURED"),
    *_terms("tlb", "fy-2025", "SECURED"),
    *_terms("tlb", "q1-2026", "UNSECURED"),
]


def _cp4_mapping(fid: str) -> cp4c.Cp4Head:
    head = m._context("positive").cp4
    facts = tuple(
        m._refact(f, text=fid) if f.fact_id == cp4c.CP4_FACILITY_ID else f for f in head.facts
    )
    return dataclasses.replace(head, facts=facts)


def test_the_secured_facility_is_the_one_cp4_maps_not_a_fixture_id() -> None:
    """cr S14 cp4c.py:2682: an issuer whose facility id is not `term-loan` is read."""
    assert cp4c.secured_facility_id(_cp4_mapping("tlb")) == "tlb"
    module = Module.model_construct(module_id="CP-1", facts=(*PERIODS, *TLB))
    head = cp4c.cp1_of(module, "accepted", "tlb", "q4-2025")
    assert head.facility_id == "tlb"
    assert (head.secured_status.text, head.seniority.text) == ("SECURED", "SENIOR")
    with pytest.raises(ValueError, match="states no term-loan terms for q4-2025"):
        cp4c.cp1_of(module, "accepted", "term-loan", "q4-2025")
    unmapped = _cp4_mapping("tlb")
    gone = tuple(
        m._refact(f, text=None, status="missing", limitation="Not stated")
        if f.fact_id == cp4c.CP4_FACILITY_ID
        else f
        for f in unmapped.facts
    )
    with pytest.raises(ValueError, match="states no known facility id"):
        cp4c.secured_facility_id(dataclasses.replace(unmapped, facts=gone))


def _upstream(t418: list[Fact]) -> cp4c.Upstream:
    base = vc.upstream_of(None)
    cp1 = dataclasses.replace(base.cp1, facility_id="tlb")
    return dataclasses.replace(base, cp1=cp1, register=tuple(PERIODS), t418=tuple(t418))


def test_the_terms_are_read_at_the_run_basis_schedule_period() -> None:
    """cr S14 cp4c.py:2728: the context-free reader takes the latest quarter (q1-2026), but the
    run on the FY2025 basis reads the Q4 2025 terms, the period of its claims (as CP-3C does)."""
    facts = (*PERIODS, *TLB)
    latest = cp4c._facility_terms(facts, "tlb")
    assert (latest[0].text, latest[0].fact_id) == ("UNSECURED", "T4.18.tlb-q1-2026.secured_status")
    cp1 = cp4c._cp1_at(_upstream(TLB), DEFAULT_BASIS)
    assert DEFAULT_BASIS.schedule_period == "q4-2025"
    assert (cp1.secured_status.text, cp1.secured_status.fact_id) == (
        "SECURED",
        "T4.18.tlb-q4-2025.secured_status",
    )


@pytest.mark.parametrize(
    ("alias_rows", "message"),
    [
        ([], "states no tlb secured_status for fy-2025, the alias of q4-2025"),
        (
            _terms("tlb", "fy-2025", "SECURED", "SUBORDINATED"),
            "seniority differs between its q4-2025 row and its fy-2025 alias",
        ),
    ],
)
def test_an_alias_without_the_row_or_with_other_terms_fails_closed(
    alias_rows: list[Fact], message: str
) -> None:
    """cr S14 cp4c.py:2757: CP-3C refuses an FY alias that lacks the facility's row; so does
    CP-4C now (it used to skip a missing alias row)."""
    rows = [*_terms("tlb", "q4-2025", "SECURED"), *alias_rows]
    with pytest.raises(ValueError, match=message):
        cp4c._facility_terms((*PERIODS, *rows), "tlb", "q4-2025")


def test_terms_unreadable_at_the_basis_are_one_issue_line_not_a_raise() -> None:
    """The basis-period read runs in `_view_basis`, so the validator and the view report it."""
    upstream = _upstream(_terms("tlb", "q1-2026", "SECURED"))
    pack = m._context("positive").pack
    sub = m._inputs("positive").submission
    line = "CP-4C: CP-1 T4.18 states no tlb terms for q4-2025"
    assert cp4c._lines(pack, sub, upstream) == (line,)
    block: Any = cp4c.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == line
