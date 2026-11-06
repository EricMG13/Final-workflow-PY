"""S14 review fixes for CP-3D: the label boundary and the spelling of typed figures.

Expected spellings and issue texts are literal, written from the quote as typed.
"""

import copy
from typing import Any

import test_method_cp3d as t

from deploy_workflow.owners import cp3d

QUOTE_DATE = "January 9, 2026"


def _quoted(page: str, bid: str, offer: str) -> tuple[cp3d.MarketContext, dict[str, Any]]:
    raw = copy.deepcopy(t.SUBMISSIONS["positive"])
    for obs, level in ((raw["observations"][0], bid), (raw["observations"][1], offer)):
        obs.update(locator="page:9", quote=page, level_text=level, as_of_text=QUOTE_DATE)
    return t._with_page(t._context("positive"), "market", "page:9", page), raw


def _cells(sub: cp3d.MarketImpliedSubmission, ctx: cp3d.MarketContext) -> dict[str, Any]:
    result = cp3d.market_implied_result(submission=sub, context=ctx)
    return {c.fact_id: c for tb in result.tables for row in tb.rows for c in row.facts}


def test_a_truncated_level_is_not_labelled_by_a_longer_figure() -> None:
    """adv S14 cp3d.py:796: `offer 99` is not read inside `offer 99.25`, even when a whole `99`
    (the spread) occurs once elsewhere in the quote."""
    page = "Dealer quotation on January 9, 2026: bid 98.75 and offer 99.25, a spread of 99 bp."
    ctx, raw = _quoted(page, "98.75", "99")
    issues = cp3d.submission_issues(submission=t._submission(raw), context=ctx)
    assert issues == ("observations[1]: offer level_text 99 is not labelled offer in the quote",)


def test_the_label_boundary_matches_the_token_boundary() -> None:
    assert cp3d._labelled("offer", "99.25", "bid 98.75 and offer 99.25, a spread")
    assert cp3d._labelled("offer", "99", "bid 98 and offer 99.")
    assert not cp3d._labelled("offer", "99", "offer 99.25")
    assert not cp3d._labelled("offer", "99", "offer 99,25")
    assert not cp3d._labelled("offer", "99", "offer 99, 250")
    assert not cp3d._labelled("offer", "99", "offer 990")


def test_quoted_levels_and_recovery_are_shown_as_typed() -> None:
    """adv S14 cp3d.py:1512/1784: eighths and a half-percent recovery keep their places."""
    page = "Dealer quotation on January 9, 2026: bid 98.375 and offer 99.125."
    ctx, raw = _quoted(page, "98.375", "99.125")
    raw["recovery"]["percent_text"] = "72.5"
    sub = t._submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    cells = _cells(sub, ctx)
    shown = {fid: (str(cells[fid].amount), cells[fid].shown) for fid in cells}
    assert shown["T3E.1.r01.level"] == ("0.98375", "98.375%")
    assert shown["T3E.1.r02.level"] == ("0.99125", "99.125%")
    assert shown["T3E.4.r01.value"] == ("0.725", "72.5%")


def test_two_place_levels_and_a_whole_recovery_keep_the_pinned_spelling() -> None:
    page = "Dealer quotation on January 9, 2026: bid 98.5 and offer 99."
    ctx, raw = _quoted(page, "98.5", "99")
    sub = t._submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    cells = _cells(sub, ctx)
    assert cells["T3E.1.r01.level"].shown == "98.50%"
    assert cells["T3E.1.r02.level"].shown == "99.00%"
    assert cells["T3E.4.r01.value"].shown == "70%"


def test_a_reference_rate_level_is_shown_as_typed() -> None:
    """adv S14 cp3d.py:1721: a 4.375 percent fixing is not shown as 4.38%."""
    page = "Published January 10, 2026.\nThe SOFR reference rate is 4.375 percent."
    ctx = t._with_page(t._context("positive"), "financial", "page:9", page)
    raw = copy.deepcopy(t.SUBMISSIONS["positive"])
    raw["terms"]["reference_rate"]["absence"] = None
    quote = {"source_id": "financial", "locator": "page:9", "quote": page.split("\n")[1]}
    raw["terms"]["reference_rate"]["level"] = {"quote": quote, "percent_text": "4.375"}
    sub = t._submission(raw)
    assert cp3d.submission_issues(submission=sub, context=ctx) == ()
    cell = _cells(sub, ctx)["T3E.3.r04.mid"]
    assert (str(cell.amount), cell.shown) == ("0.04375", "4.375%")
