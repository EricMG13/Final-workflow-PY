"""S01 review: CP-0 extraction coverage and absence claims.

Synthetic sources (no issuer); expectations are literal page ranges and texts.
"""

import time

import pytest

from deploy_vii.contracts import Source, Span
from deploy_vii.readiness import absent_page_ranges, extraction_coverage


def _source(*pages: int) -> Source:
    return Source(
        source_id="s",
        name="n",
        status="ready",
        sha256="a" * 64,
        spans=tuple(Span(locator=f"page:{page}", text="x") for page in pages),
    )


@pytest.mark.parametrize(
    ("pages", "missing"),
    [
        ((1, 2, 3), []),
        ((3, 1, 2), []),
        ((1, 3), ["page:2"]),
        ((1, 4, 5, 9), ["page:2 to page:3", "page:6 to page:8"]),
        ((7, 2, 4), ["page:3", "page:5 to page:6"]),  # unordered
        ((5,), []),
        ((0, 2), ["page:1"]),
    ],
)
def test_missing_pages_between_first_and_last(pages: tuple[int, ...], missing: list[str]) -> None:
    record = extraction_coverage(_source(*pages))
    assert record["pages_missing_between_first_and_last"] == missing


def test_a_huge_page_number_does_not_enumerate_every_page() -> None:
    started = time.perf_counter()
    record = extraction_coverage(_source(1, 10**12))
    assert time.perf_counter() - started < 1.0
    assert record["pages_missing_between_first_and_last"] == ["page:2 to page:999999999999"]


def test_a_mixed_locator_source_has_no_page_gap_field() -> None:
    source = Source(
        source_id="s",
        name="n",
        status="ready",
        sha256="a" * 64,
        spans=(Span(locator="page:1", text="x"), Span(locator="sheet:A1", text="y")),
    )
    assert "pages_missing_between_first_and_last" not in extraction_coverage(source)


@pytest.mark.parametrize(
    "text",
    [
        "No pages 53-96 are missing",
        "no pages 53 to 96 missing",
        "missing pages: none (pages 3-9 retained)",
        "Missing: none for pages 3-9",
        "Pages absent: none; pages 3-9 retained",
        "missing pages = [] (pages 3-9 retained)",
    ],
)
def test_negated_absence_with_a_page_range_is_not_an_absence_claim(text: str) -> None:
    assert absent_page_ranges(text) == ()


@pytest.mark.parametrize(
    ("text", "ranges"),
    [
        ("pages 33-52 not present", ((33, 52),)),
        ("pages 12 to 180 of the filing are absent", ((12, 180),)),
        ("not complete with missing pages 53-96", ((53, 96),)),
        ("pages 33-52 not present and also missing", ((33, 52),)),
        ("none of pages 53-96 are missing", ((53, 96),)),  # documented: a range in between
        ("No pages 1-2 missing; pages 53-96 are missing", ((53, 96),)),
        ("There are no pages 53-96 and they are missing", ((53, 96),)),
        ("missing pages: 53-96", ((53, 96),)),
        ("Missing: nothing retained for pages 3-9", ((3, 9),)),
        ("pages 10-20 absent: none were extracted", ((10, 20),)),
        ("pages 10-20 missing: none of their text was extracted", ((10, 20),)),
        ("missing from pages 40-60", ()),
        ("no pages missing", ()),
    ],
)
def test_absence_claims_still_found(text: str, ranges: tuple[tuple[int, int], ...]) -> None:
    assert absent_page_ranges(text) == ranges
