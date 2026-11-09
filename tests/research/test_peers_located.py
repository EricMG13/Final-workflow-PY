"""S16 A01/C01: a TDR.6 quote is a whole figure of its cited span, never a fragment of one.

The key submission cites ``ev-1 line:11``, which reads (``cases/cpdr-peers-owner/manifest.json``)
``Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200.0``. The only figure that
line states for revenue is ``200.0``: ``20`` and ``0.0`` cut it, ``2025``, ``12``, ``-12`` and
``31`` cut the date. Each must be the cut-figure issue, not a located amount. Expected values are
worked out by hand from that line and from the edited lines below.
"""

import copy
from typing import Any

import pytest
from cpdr_peers_support import Case, peers_case

from deploy_vii.contracts import Source
from deploy_workflow.research import peers as p


@pytest.fixture(scope="module")
def case() -> Case:
    return peers_case()


def _quoting(case: Case, quote: str) -> dict[str, Any]:
    body: dict[str, Any] = copy.deepcopy(case.body)
    body["peers"]["figures"][0]["citation"]["quote"] = quote  # p01 revenue, ev-1 line:11
    return body


def _with_line(case: Case, locator: str, text: str) -> tuple[Source, ...]:
    """The held sources with one ``ev-1`` span's text replaced (the item hash is kept, as a held
    item carries it; ``citation_issues`` compares the citation's hash with the source's)."""
    out = []
    for source in case.sources:
        if source.source_id == "ev-1":
            spans = tuple(
                s.model_copy(update={"text": text}) if s.locator == locator else s
                for s in source.spans
            )
            source = source.model_copy(update={"spans": spans})
        out.append(source)
    return tuple(out)


def _texts(case: Case, body: dict[str, Any], sources: tuple[Source, ...]) -> list[str]:
    pack = case.submission(body).peers
    return [str(i) for i in p.peer_issues(pack, case.brief, case.evidence, sources)]


@pytest.mark.parametrize("quote", ["20", "0.0", "00", "00.0", "2025", "12", "-12", "31"])
def test_a_fragment_of_the_span_is_the_cut_figure_issue(case: Case, quote: str) -> None:
    assert [str(i) for i in case.issues(_quoting(case, quote))] == [f"p01.revenue: {p.CUT_FIGURE}"]


def test_the_whole_figure_is_no_issue(case: Case) -> None:
    assert case.issues(_quoting(case, "200.0")) == ()


@pytest.mark.parametrize(
    ("line", "quote"),
    [
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: (12.3)", "12.3"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: -12.3", "12.3"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 1,200.0", "200.0"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 12.5%", "12.5"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 12/15", "12"),
        # Confidence review: a sign or bracket one space away, and space-grouped thousands.
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: - 12.3", "12.3"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: ( 12.3 )", "12.3"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200 000", "200"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 1 200.0", "200.0"),
    ],
)
def test_a_sign_separator_unit_or_date_beside_the_quote_cuts_it(
    case: Case, line: str, quote: str
) -> None:
    """``12.3`` out of ``(12.3)`` or ``-12.3`` would drop the sign; ``200.0`` out of ``1,200.0``
    drops the thousands; a scale suffix, a percent or a date part is not the figure."""
    got = _texts(case, _quoting(case, quote), _with_line(case, "line:11", line))
    assert got == [f"p01.revenue: {p.CUT_FIGURE}"]


def test_a_scale_suffix_on_the_figure_cuts_it_and_states_its_scale(case: Case) -> None:
    """``200.0bn``: the quote ``200.0`` is cut by the suffix, and the line states billions, not
    the declared millions of the Basis line."""
    line = "Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200.0bn"
    got = _texts(case, _quoting(case, "200.0"), _with_line(case, "line:11", line))
    assert got == [f"p01.revenue: {p.CUT_FIGURE}", f"p01.revenue: {p.UNSTATED_SCALE}"]


@pytest.mark.parametrize(
    ("line", "quote"),
    [
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: -12.3", "-12.3"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200.0.", "200.0"),
        ("Alder Ridge Holdings revenue, twelve months to 2025-12-31, was 200.0, up.", "200.0"),
    ],
)
def test_a_whole_figure_with_its_sign_or_sentence_punctuation_holds(
    case: Case, line: str, quote: str
) -> None:
    assert _texts(case, _quoting(case, quote), _with_line(case, "line:11", line)) == []


def test_a_parenthesised_negative_quoted_whole_is_the_missing_cell(case: Case) -> None:
    """``(12.3)`` is not read by the table rule: no issue, a missing cell, never ``12.3``."""
    line = "Alder Ridge Holdings revenue for the twelve months to 2025-12-31: (12.3)"
    body = _quoting(case, "(12.3)")
    assert _texts(case, body, _with_line(case, "line:11", line)) == []
    fact = {f.fact_id: f for f in case.composed(body).facts}["TDR.6.p01.revenue.amount"]
    assert (fact.status, fact.amount, fact.limitation) == ("missing", None, p.UNREADABLE)


# --- S16 A02/C02: unit, currency, period end and length are the span's (or its Basis: line's) ---
#
# ev-1 line:5 reads "Basis: twelve months to the period end shown; USD; amounts in millions; ...";
# line:11 states only the length and the date, so USD and millions come from the Basis line. ev-2
# has no Basis line: line:6 reads "... for the twelve months to 2025-12-31 in EUR millions: 180.0"
# (figure 25 of the key, p06 revenue) and line:8 "... total debt ... in EUR millions: 90.0"
# (figure 27, p06 debt). Each expected issue list is read by hand off the edited line.


def _figure(case: Case, index: int, **fields: str) -> dict[str, Any]:
    body: dict[str, Any] = copy.deepcopy(case.body)
    body["peers"]["figures"][index].update(fields)
    return body


def _edited(case: Case, source_id: str, locator: str, text: str) -> tuple[Source, ...]:
    out = []
    for source in case.sources:
        if source.source_id == source_id:
            spans = tuple(
                s.model_copy(update={"text": text}) if s.locator == locator else s
                for s in source.spans
            )
            source = source.model_copy(update={"spans": spans})
        out.append(source)
    return tuple(out)


REVENUE = "p01.revenue: "


def test_a_quarter_in_eur_thousands_declared_usd_millions_is_refused(case: Case) -> None:
    """The A02 repro: three refusals, none of which the Basis line (USD, millions, twelve months)
    may answer, because the cited line states its own currency, scale and length."""
    line = "Alder Ridge Holdings revenue for the three months to 2025-12-31, EUR thousands: 200.0"
    got = _texts(case, case.body, _edited(case, "ev-1", "line:11", line))
    assert got == [
        REVENUE + p.UNSTATED_CURRENCY,
        REVENUE + p.UNSTATED_SCALE,
        REVENUE + p.UNSTATED_LENGTH,
    ]
    # Declared as the line states it, only the length (a quarter) is still refused.
    body = _figure(case, 0, unit="thousands", currency="EUR")
    assert _texts(case, body, _edited(case, "ev-1", "line:11", line)) == [
        REVENUE + p.UNSTATED_LENGTH
    ]


def test_a_declared_basis_the_span_and_basis_line_do_not_state_is_refused(case: Case) -> None:
    """The C02 reverse case: thousands and EUR over a USD-millions basis; then a period end the
    line does not state (it states 2025-12-31)."""
    assert [str(i) for i in case.issues(_figure(case, 0, unit="thousands", currency="EUR"))] == [
        REVENUE + p.UNSTATED_CURRENCY,
        REVENUE + p.UNSTATED_SCALE,
    ]
    assert [str(i) for i in case.issues(_figure(case, 0, period_end="2025-09-30"))] == [
        REVENUE + p.UNSTATED_END
    ]


# "USD|x", "USD\n" and "USD " are S16 C03: a pipe or line break would make peer_sheet refuse the
# whole pack after settle, and a trailing space would drop the peer, so review refuses them.
@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "XYZ", "USD|x", "USD\n", "USD "])
def test_a_currency_that_is_not_an_iso_code_is_refused(case: Case, currency: str) -> None:
    got = [str(i) for i in case.issues(_figure(case, 0, currency=currency))]
    assert got == [REVENUE + p.NOT_A_CODE]


@pytest.mark.parametrize(
    ("line", "wrong"),
    [
        # A symbol on the line overrides the Basis line: EUR, and an ambiguous bare dollar sign.
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in €: 200.0",
            "currency",
        ),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: $200.0", "currency"),
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in GBP: 200.0",
            "currency",
        ),
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31, USD bn: 200.0",
            "scale",
        ),
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 (thousands): 200.0",
            "scale",
        ),
        ("Alder Ridge Holdings Q4 revenue to 2025-12-31: 200.0", "length"),
        ("Alder Ridge Holdings revenue for the nine months to 2025-12-31: 200.0", "length"),
        ("Alder Ridge Holdings half-year revenue to 2025-12-31: 200.0", "length"),
        ("Alder Ridge Holdings 9M revenue to 2025-12-31: 200.0", "length"),
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in euros: 200.0",
            "currency",
        ),
        (
            "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in dollars: 200.0",
            "currency",
        ),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200.0 k", "scale"),
        ("Alder Ridge Holdings twelve months to 2025-12-31 (2024-12-31: 180.0): 200.0", "end"),
        ("Alder Ridge Holdings revenue for the twelve months to 2025-12-30: 200.0", "end"),
    ],
)
def test_the_cited_line_states_another_basis(case: Case, line: str, wrong: str) -> None:
    issue = {
        "currency": p.UNSTATED_CURRENCY,
        "scale": p.UNSTATED_SCALE,
        "length": p.UNSTATED_LENGTH,
        "end": p.UNSTATED_END,
    }[wrong]
    assert _texts(case, case.body, _edited(case, "ev-1", "line:11", line)) == [REVENUE + issue]


@pytest.mark.parametrize(
    "line",
    [
        "Alder Ridge Holdings LTM revenue to December 31, 2025: 200.0",
        "Alder Ridge Holdings revenue, 12-month period to 31 Dec 2025, US$ m: 200.0",
        "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in USD millions: 200.0",
        "Alder Ridge Holdings revenue for the twelve months to 2025-12-31 in US dollars: 200.0 m",
    ],
)
def test_the_cited_line_states_the_declared_basis_in_other_words(case: Case, line: str) -> None:
    assert _texts(case, case.body, _edited(case, "ev-1", "line:11", line)) == []


def test_without_a_basis_line_a_flow_needs_twelve_months_and_a_balance_does_not(
    case: Case,
) -> None:
    """ev-2 has no Basis line. Revenue to a date with no length is refused; debt is a balance at
    its period end, so the same wording holds for it."""
    revenue = "Garrowby Holdings SE revenue to 31 December 2025 in EUR millions: 180.0"
    got = _texts(case, case.body, _edited(case, "ev-2", "line:6", revenue))
    assert got == ["p06.revenue: " + p.UNSTATED_LENGTH]
    debt = "Garrowby Holdings SE total debt at 31 December 2025 in EUR millions: 90.0"
    assert _texts(case, case.body, _edited(case, "ev-2", "line:8", debt)) == []
    unstated = "Garrowby Holdings SE total debt at 31 December 2025: 90.0"
    got = _texts(case, case.body, _edited(case, "ev-2", "line:8", unstated))
    assert got == ["p06.debt: " + p.UNSTATED_CURRENCY, "p06.debt: " + p.UNSTATED_SCALE]


# --- Second-model review: adversarial cases, expected issues read by hand off each edited line ---
#
# Every line below is ``line:11`` of ev-1 (revenue of p01, declared USD millions, 2025-12-31); the
# Basis line (USD, amounts in millions, twelve months) answers whatever the line does not state.

HEAD = "Alder Ridge Holdings revenue for the twelve months to 2025-12-31"


@pytest.mark.parametrize(
    ("line", "quote"),
    [
        # Comparative columns: a decimal figure is not grouped with the digits beside it.
        (f"{HEAD}: 200.0 180.0", "200.0"),
        (f"{HEAD}: 180.0 200.0", "200.0"),
        (f"{HEAD}: 200.0 150", "200.0"),
        (f"{HEAD}: 200.0 year ended", "200.0"),
        # A ticker or heading that is also an ISO 4217 code is not the currency of the line.
        ("AMD revenue for the twelve months to 2025-12-31: 200.0", "200.0"),
        ("Allstate (ALL) revenue for the twelve months to 2025-12-31: 200.0", "200.0"),
        (
            "TOP picks: Alder Ridge Holdings revenue for the twelve months to 2025-12-31: 200.0",
            "200.0",
        ),
        # An ordinal day is a date.
        (
            "Alder Ridge Holdings revenue for the twelve months to December 31st, 2025: 200.0",
            "200.0",
        ),
        # Equals sign, no space after the colon.
        (f"{HEAD} = 200.0", "200.0"),
        (f"{HEAD}:200.0", "200.0"),
    ],
)
def test_a_legitimate_layout_is_not_refused(case: Case, line: str, quote: str) -> None:
    assert _texts(case, _quoting(case, quote), _with_line(case, "line:11", line)) == []


@pytest.mark.parametrize(
    ("line", "quote", "issue"),
    [
        # The year of the period, and a count of time, are not the amount.
        ("Alder Ridge 2025 revenue for the twelve months to 2025-12-31: 200.0", "2025", p.A_YEAR),
        ("Alder Ridge revenue for the 12 months to 2025-12-31: 200.0", "12", p.CUT_FIGURE),
        # A percentage with a space or as a word is not an amount.
        (f"{HEAD}: 12.5 %", "12.5", p.CUT_FIGURE),
        (f"{HEAD}: 12.5 percent", "12.5", p.CUT_FIGURE),
        (f"{HEAD}: 125 bps", "125", p.CUT_FIGURE),
        # A dash used as a separator cannot be told from a minus sign: refused, not read as +200.0.
        (f"{HEAD} – 200.0", "200.0", p.CUT_FIGURE),
        # A scale or currency printed in a form the Basis line must not answer for.
        (f"{HEAD} (USD 000s): 200.0", "200.0", p.UNSTATED_SCALE),
        (f"{HEAD} (USD '000): 200.0", "200.0", p.UNSTATED_SCALE),
        (f"{HEAD}, RMB: 200.0", "200.0", p.UNSTATED_CURRENCY),
        (f"{HEAD}, in rand: 200.0", "200.0", p.UNSTATED_CURRENCY),
        # A date in a form the reader does not know is not the declared period end.
        (
            "Alder Ridge Holdings revenue for the twelve months to 12/31/2025: 200.0",
            "200.0",
            p.UNSTATED_END,
        ),
        (
            "Alder Ridge Holdings revenue for the twelve months to December 2025: 200.0",
            "200.0",
            p.UNSTATED_END,
        ),
    ],
)
def test_a_figure_that_is_not_the_stated_amount_is_refused(
    case: Case, line: str, quote: str, issue: str
) -> None:
    assert _texts(case, _quoting(case, quote), _with_line(case, "line:11", line)) == [
        REVENUE + issue
    ]


def test_a_dash_separated_figure_quoted_with_its_dash_is_the_missing_cell(case: Case) -> None:
    """The repair for a ``label - 200.0`` line: quote the dash too and the cell is ``missing``
    (the table rule reads no amount), never 200.0 and never -200.0."""
    line = f"{HEAD} - 200.0"
    body = _quoting(case, "- 200.0")
    assert _texts(case, body, _with_line(case, "line:11", line)) == []
    fact = {f.fact_id: f for f in case.composed(body).facts}["TDR.6.p01.revenue.amount"]
    assert (fact.status, fact.amount, fact.limitation) == ("missing", None, p.UNREADABLE)
