"""Stage 2 close release (round 13 addendum 3): `readiness.citation_issues` refuses a blank
quote, whatever the span holds. `quoted` already matches nothing for an empty reading, but a
quote of invisible characters (U+200B, U+2800, a control) is a substring of a span that holds
the same characters."""

import pytest

from deploy_vii.contracts import Citation, Source, Span
from deploy_vii.readiness import citation_issues

SHA = "a" * 64
TEXT = "Net debt was 100.\u200b \u2800 \x01 \u034f end"
SOURCE = Source(
    source_id="doc",
    name="Doc",
    status="ready",
    sha256=SHA,
    spans=(Span(locator="page:1", text=TEXT), Span(locator="page:2", text="Other text.")),
)


def _cite(quote: str, locator: str = "page:1") -> Citation:
    return Citation(source_id="doc", source_sha256=SHA, locator=locator, quote=quote)


@pytest.mark.parametrize("quote", [" ", "\n\t", "\u200b", "\u2800", "\x01", "\u034f", " \u200b "])
def test_a_blank_quote_is_refused_whatever_the_span_holds(quote: str) -> None:
    (issue,) = citation_issues((_cite(quote),), (SOURCE,))
    assert issue == "Quote/locator mismatch: blank quote under doc page:1"


def test_a_blank_quote_under_a_missing_locator_keeps_the_locator_issue() -> None:
    (issue,) = citation_issues((_cite("\u2800", "page:9"),), (SOURCE,))
    assert issue.startswith("Quote/locator mismatch: no locator page:9 in doc")


def test_a_visible_quote_still_holds() -> None:
    issues = citation_issues((_cite("Net debt was 100."), _cite("\u200bNet debt")), (SOURCE,))
    expected = (
        "Quote/locator mismatch: quote not found under doc page:1 (normalised whitespace, "
        'quote marks and dashes): "\u200bNet debt"'
    )
    assert issues == (expected,)


def test_calls_sharing_positions_build_one_map_per_source() -> None:
    # S15-C07: a source's first lookup builds one {locator: first index} map that every later
    # lookup reads. The issues are a scan's. Expected by hand.
    digest = "c" * 64
    spans = tuple(Span(locator=f"page:{n}", text=f"Line {n}") for n in (1, 2, 3))
    source = Source(source_id="s", name="s.pdf", status="ready", sha256=digest, spans=spans)
    positions: dict[str, dict[str, int]] = {}

    def cite(locator: str, quote: str) -> Citation:
        return Citation(source_id="s", source_sha256=digest, locator=locator, quote=quote)

    assert citation_issues((cite("page:3", "Line 3"),), (source,), positions) == ()
    assert positions == {"s": {"page:1": 0, "page:2": 1, "page:3": 2}}
    found = citation_issues((cite("page:2", "Line 2"), cite("page:9", "x")), (source,), positions)
    assert found == ('Quote/locator mismatch: no locator page:9 in s: "x"',)
    assert positions == {"s": {"page:1": 0, "page:2": 1, "page:3": 2}}
