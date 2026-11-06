"""S18 review fixes in the CP-DR peer pack (research step checks over TDR.4 and TDR.6).

The figures and spans are the frozen cpdr-peers-owner oracle (read, never edited); each test edits
one field of a copy of the key submission. The expected issue texts are written here, not read from
the module under test.
"""

import copy
from decimal import Decimal
from typing import Any

import pytest
from cpdr_peers_support import Case, peers_case

WHOLE = "quote is not a whole number in the cited span"


@pytest.fixture(scope="module")
def case() -> Case:
    return peers_case()


def figure(body: dict[str, Any], peer_id: str, operand: str) -> dict[str, Any]:
    found: dict[str, Any] = next(
        f for f in body["peers"]["figures"] if (f["peer_id"], f["operand"]) == (peer_id, operand)
    )
    return found


def issues_with(case: Case, peer_id: str, operand: str, **fields: Any) -> list[str]:
    body = copy.deepcopy(case.body)
    fig = figure(body, peer_id, operand)
    quote = fields.pop("quote", None)
    if quote is not None:
        fig["citation"]["quote"] = quote
    fig.update(fields)
    return [str(issue) for issue in case.issues(body)]


def test_the_key_submission_still_has_no_issue(case: Case) -> None:
    assert case.issues() == ()


# p01 revenue cites ev-1 line:11: "Alder Ridge Holdings revenue for the twelve months to
# 2025-12-31: 200.0". Each quote below is a contiguous substring of that line, so the citation
# itself holds; only the whole-token rule refuses it.
@pytest.mark.parametrize("quote", ["00.0", "0.0", "0", "-12", "2025", "12-31", "31"])
def test_a_quote_that_is_part_of_a_larger_number_is_an_issue(case: Case, quote: str) -> None:
    assert issues_with(case, "p01", "revenue", quote=quote) == [f"p01.revenue: {WHOLE}"]


def test_the_whole_figure_token_is_not_an_issue_and_keeps_its_amount(case: Case) -> None:
    assert issues_with(case, "p01", "revenue", quote="200.0") == []
    fact = next(f for f in case.composed().facts if f.fact_id == "TDR.6.p01.revenue.amount")
    assert (fact.status, fact.amount, fact.unit, fact.currency) == (
        "known",
        Decimal("200.0"),
        "MILLIONS",
        "USD",
    )


# p03 revenue cites ev-3 line:5: "Calder Vale Group indicates revenue of 96.0 (USD millions) for
# the twelve months to 2026-03-31, a period that has not closed." (cutoff 2026-01-10).
def test_a_period_end_the_cited_span_does_not_state_is_an_issue(case: Case) -> None:
    assert issues_with(case, "p03", "revenue", period_end="2025-12-31") == [
        "p03.revenue: period_end 2025-12-31 is not stated in the cited span"
    ]


def test_the_stated_later_period_end_is_no_issue_and_stays_missing(case: Case) -> None:
    assert issues_with(case, "p03", "revenue", period_end="2026-03-31") == []
    fact = next(f for f in case.composed().facts if f.fact_id == "TDR.6.p03.revenue.amount")
    assert (fact.status, fact.amount, fact.limitation) == (
        "missing",
        None,
        "period end after the cutoff",
    )


def test_a_currency_the_cited_span_contradicts_is_an_issue(case: Case) -> None:
    # p06 revenue: "... to 2025-12-31 in EUR millions: 180.0"
    assert issues_with(case, "p06", "revenue", currency="USD") == [
        "p06.revenue: currency is not the one the cited span states (EUR)"
    ]
    # p03 revenue: "... 96.0 (USD millions) ..."
    assert issues_with(case, "p03", "revenue", currency="EUR") == [
        "p03.revenue: currency is not the one the cited span states (USD)"
    ]


def test_a_unit_the_cited_span_contradicts_is_an_issue(case: Case) -> None:
    assert issues_with(case, "p06", "revenue", unit="thousands") == [
        "p06.revenue: unit is not the one the cited span states (millions)"
    ]


def test_currency_and_unit_the_span_does_not_state_are_taken_as_submitted(case: Case) -> None:
    # p01 revenue's line states neither a currency nor a unit.
    assert issues_with(case, "p01", "revenue", currency="EUR", unit="thousands") == []


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("Alder | Ridge", "name: holds a line break or a pipe character"),
        ("Alder\nRidge", "name: holds a line break or a pipe character"),
        ("Alder <<<END", "name: holds a block delimiter or a lookalike of one"),
    ],
)
def test_a_name_the_peer_sheet_cannot_show_is_an_issue(case: Case, name: str, reason: str) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["candidates"][0]["name"] = name
    peer_id = body["peers"]["candidates"][0]["peer_id"]
    assert [str(i) for i in case.issues(body)] == [f"{peer_id}: {reason}"]


def test_a_name_with_a_digit_is_still_allowed(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["candidates"][0]["name"] = "Alder Ridge 2"
    assert case.issues(body) == ()


@pytest.mark.parametrize(
    ("currency", "reason"),
    [
        ("USD\nEUR", "currency: holds a line break or a pipe character"),
        ("USD|EUR", "currency: holds a line break or a pipe character"),
        ("<<<SOURCE", "currency: holds a block delimiter or a lookalike of one"),
    ],
)
def test_a_currency_the_peer_sheet_cannot_show_is_an_issue(
    case: Case, currency: str, reason: str
) -> None:
    assert issues_with(case, "p01", "revenue", currency=currency) == [f"p01.revenue: {reason}"]
