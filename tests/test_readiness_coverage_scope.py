"""Absence claims are compared only with the pack sources they are about (S15 C01).

Before the fix a CONDITIONAL consumer's `missing_source` (about a source outside the pack) was
checked against the consumer's attached sources, or every ready paged source, and an uncited gap
description against every paged source. A true statement that pages of a document never supplied
are absent then counted as a contradiction of the pack's own coverage.

The pack: `annual-report` (ar.pdf), ready, pages 1-100 retained; `compliance-cert`, missing.
Expected issues are derived by hand from those page numbers.
"""

from datetime import date

import pytest

from deploy_vii.contracts import Citation, Claim, Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import (
    ConsumerReadiness,
    ReadinessGap,
    ReadinessReview,
    SourceAssessment,
    absent_page_ranges,
    coverage_issues,
)

H = "a" * 64
AR = Source(
    source_id="annual-report",
    name="ar.pdf",
    status="ready",
    sha256=H,
    spans=tuple(Span(locator=f"page:{i}", text=f"p{i}") for i in range(1, 101)),
)
CC = Source(
    source_id="compliance-cert",
    name="cc.pdf",
    status="missing",
    limitation="Requested file is absent",
)
RUN = Run(
    run_id="r1", issuer_id="i1", issuer_name="Issuer", as_of=date(2026, 1, 1), case_kind="synthetic"
)
PACK = PreparedPack(run=RUN, sources=(AR, CC))
CITE = Citation(source_id="annual-report", source_sha256=H, locator="page:1", quote="p1")


def _contradiction(first: int, last: int) -> str:
    return (
        f"Absence claim contradicts extraction coverage: page:{first} to page:{last} retained in "
        "annual-report"
    )


def _review(
    *,
    missing_source: str = "Covenant certificate not supplied",
    source_ids: tuple[str, ...] = (),
    limitations: tuple[str, ...] = ("Covenant certificate absent",),
    gap: str = "Facility agreement not supplied",
    gap_citations: tuple[Citation, ...] = (),
) -> ReadinessReview:
    return ReadinessReview(
        pack_sha256=PACK.content_hash(),
        objective="x",
        reporting_period="FY25",
        issuer_confirmed=True,
        sources=(
            SourceAssessment(
                source_id="annual-report",
                document_family="AR",
                authority="filed",
                entity="I",
                period="FY25",
                version_relationship="final",
                fidelity="verified",
                citations=(CITE,),
            ),
        ),
        consumers=(
            ConsumerReadiness(
                module_id="CP-4",
                readiness="CONDITIONAL",
                evidence_demand="covenants",
                source_ids=source_ids,
                rationale="needs certificate",
                citations=(),
                missing_source=missing_source,
                limitations=limitations,
            ),
        ),
        gaps=(
            ReadinessGap(
                gap_id="g1",
                kind="source",
                severity="material",
                description=gap,
                affected_modules=("CP-4",),
                remediation="Upload it",
                citations=gap_citations,
            ),
        ),
        analysis=(
            Claim(claim_id="c1", text="Annual report is the only source.", citations=(CITE,)),
        ),
    )


def test_true_absence_of_documents_never_supplied_is_not_a_contradiction() -> None:
    review = _review(
        missing_source="Compliance certificate pages 1-20 not supplied",
        gap="Facility agreement pages 30-45 not supplied",
    )
    assert coverage_issues(PACK, review) == ()


def test_missing_source_is_not_read_against_the_consumers_attached_sources() -> None:
    # the consumer uses the annual report; its missing source is another document
    review = _review(
        source_ids=("annual-report",),
        missing_source="Compliance certificate pages 1-20 not supplied",
    )
    assert coverage_issues(PACK, review) == ()


def test_an_uncited_gap_that_names_a_pack_source_is_still_checked() -> None:
    # "Annual report" names annual-report as whole words; it retains pages 30-45
    review = _review(gap="Annual report pages 30-45 not supplied")
    assert coverage_issues(PACK, review) == (_contradiction(30, 45),)


def test_a_missing_source_that_names_a_pack_source_is_still_checked() -> None:
    review = _review(missing_source="ar.pdf pages 1-20 not supplied")
    assert coverage_issues(PACK, review) == (_contradiction(1, 20),)


def test_a_cited_gap_and_an_attached_limitation_keep_their_own_scope() -> None:
    # neither text names a source; the citation and the attachment still scope them
    review = _review(
        source_ids=("annual-report",),
        limitations=("pages 5-6 are absent",),
        gap="pages 30-45 not supplied",
        gap_citations=(CITE,),
    )
    assert coverage_issues(PACK, review) == (
        _contradiction(5, 6),
        _contradiction(30, 45),
    )


def test_a_page_range_past_the_pack_named_source_is_not_flagged() -> None:
    # annual-report holds pages 1-100, so pages 101-120 are truly absent
    review = _review(gap="Annual report pages 101-120 not supplied")
    assert coverage_issues(PACK, review) == ()


# A source is named by its id or by its file name without directory and extension, as whole words.
DIR = Source(
    source_id="src1",
    name="inputs/Annual Report 2024.pdf",
    status="ready",
    sha256=H,
    spans=tuple(Span(locator=f"page:{i}", text=f"p{i}") for i in range(1, 101)),
)
WORD = Source(
    source_id="report",
    name="r.pdf",
    status="ready",
    sha256=H,
    spans=(Span(locator="page:1", text="p1"),),
)


def _named_gap(source: Source, gap: str) -> tuple[str, ...]:
    pack = PreparedPack(run=RUN, sources=(source,))
    review = _review(gap=gap).model_copy(update={"pack_sha256": pack.content_hash()})
    return coverage_issues(pack, review)


def test_a_file_name_in_a_directory_is_named_without_its_directory_or_extension() -> None:
    expected = (
        "Absence claim contradicts extraction coverage: page:30 to page:45 retained in src1",
    )
    for gap in (
        "Annual Report 2024 pages 30-45 not supplied",
        "annual report 2024.pdf pages 30-45 not supplied",
        "inputs/Annual Report 2024.pdf pages 30-45 not supplied",
    ):
        assert _named_gap(DIR, gap) == expected, gap


def test_a_text_naming_part_of_a_file_name_or_only_a_longer_word_names_no_source() -> None:
    # "Annual Report" lacks "2024"; "reporting" is not the word "report"
    assert _named_gap(DIR, "Annual Report pages 30-45 not supplied") == ()
    assert _named_gap(WORD, "Reporting pages 1-1 not supplied") == ()
    assert _named_gap(WORD, "The report pages 1-1 not supplied") == (
        "Absence claim contradicts extraction coverage: page:1 to page:1 retained in report",
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # S15-A03: one page, a list and the "pp." form are absence claims too. Expected by hand:
        # each named page or range is one (first, last) item, a single page (N, N).
        ("page:7 is missing", ((7, 7),)),
        ("Pages 3 and 4 are missing", ((3, 3), (4, 4))),
        ("pp. 3-5 missing", ((3, 5),)),
        ("pages 3, 5-7 and 9 not supplied", ((3, 3), (5, 7), (9, 9))),
        ("pages 3-5 are missing", ((3, 5),)),  # unchanged
        # not absence claims: a locative, a negation, no absence word, a reversed range
        ("missing from page 7", ()),
        ("no pages missing", ()),
        ("page 7 holds the covenant table", ()),
        ("pages 9-3 are missing", ()),
        # a page number no pack can hold (5,000 digits) is skipped, not a ValueError from int()
        ("pages 1-" + "1" * 5000 + " missing", ()),
    ],
)
def test_absent_pages_include_single_pages_and_lists(
    text: str, expected: tuple[tuple[int, int], ...]
) -> None:
    assert absent_page_ranges(text) == expected


def test_a_single_retained_page_called_missing_is_flagged() -> None:
    # page 7 of annual-report (pages 1-100 retained) is called missing in the source's own gap
    review = _review(gap="annual-report page:7 is missing", gap_citations=(CITE,))
    assert coverage_issues(PACK, review) == (_contradiction(7, 7),)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # nine digits is the largest page read; ten digits is skipped (no pack holds such a page)
        ("page 999999999 is missing", ((999999999, 999999999),)),
        ("page 1000000000 is missing", ()),
        # an absence claim after a long unrelated lead is still read (the look-back is 200
        # characters before the pages, not a limit on the clause); a locative inside it still holds
        ("alpha " * 100 + "pages 3-5 missing", ((3, 5),)),
        ("missing " + "x " * 5 + "from pages 40-60", ()),
        # a locative further than the look-back before the pages no longer excludes them
        ("missing from " + "w " * 150 + "pages 40-60", ((40, 60),)),
        # lists keep each item; a reversed item is dropped, the others stay
        ("pages 9-3, 5 and 7 missing", ((5, 5), (7, 7))),
        ("p. 4 & 6 absent", ((4, 4), (6, 6))),
    ],
)
def test_absent_pages_bounds_and_lists(text: str, expected: tuple[tuple[int, int], ...]) -> None:
    assert absent_page_ranges(text) == expected
