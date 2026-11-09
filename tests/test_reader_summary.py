"""The reader section of a handoff: plain language, restating only what the handoff already says."""

import pytest

from deploy_workflow.reader_summary import MAX_FINDINGS, reader_issues

BOTTOM_LINE = "Interest cover of 3.14x supports the credit, but liquidity is unproved."
LIMITATION = "Current liquidity was not supplied."
FINDING = "Net debt was 7,940 at year end."
VALID = f"""# Example

## Request

Assess the credit.

## Findings

### Reader summary

| Bottom line | Confidence | Main limitation |
| --- | --- | --- |
| {BOTTOM_LINE} | Medium | {LIMITATION} |

| Finding | Creditor impact | Confidence |
| --- | --- | --- |
| {FINDING} | Leverage limits new debt capacity. | High |

### Detail

Interest cover was 3.14x and net debt was 7,940. A later period shows 13.15 and 3.16.

## Gaps

None.
"""
FINDING_ROW = f"| {FINDING} | Leverage limits new debt capacity. | High |"


def words(count: int) -> str:
    return " ".join(["word"] * count)


def test_a_valid_handoff_has_no_issues() -> None:
    assert reader_issues(VALID) == ()


def test_a_not_assessable_row_with_a_limitation_is_valid() -> None:
    text = VALID.replace(
        f"{BOTTOM_LINE} | Medium |", "Credit quality cannot be judged. | Not assessable |"
    )
    assert reader_issues(text) == ()


def test_the_longest_allowed_section_is_valid() -> None:
    text = VALID.replace(BOTTOM_LINE, words(40)).replace(LIMITATION, words(30))
    text = text.replace(
        FINDING_ROW, "\n".join([f"| {words(30)} | {words(30)} | Low |"] * MAX_FINDINGS)
    )
    assert reader_issues(text) == ()


@pytest.mark.parametrize(
    ("before", "after", "cause"),
    [
        ("### Reader summary", "### Summary", "missing"),
        ("## Findings\n", "## Findings\n\nA paragraph first.\n", "first under"),
        ("## Findings\n", "## Request again\n", "first under"),
        (BOTTOM_LINE, words(41), "bottom line"),
        (LIMITATION, words(31), "limitation"),
        (FINDING, words(31), "finding"),
        ("Leverage limits new debt capacity.", words(31), "impact"),
        (FINDING_ROW, "\n".join([FINDING_ROW] * 6), "findings"),
        ("| Medium |", "| Moderate |", "Moderate"),
        ("| High |", "| Moderate |", "Moderate"),
        (LIMITATION, "", "limitation"),
        (FINDING, "", "finding"),
        (BOTTOM_LINE, "", "bottom line"),
        (FINDING, "The covenant review in CP-2G is open.", "CP-2G"),
        (FINDING, "The covenant table T4.3 is open.", "T4.3"),
        (FINDING, "The file deadbeefcafe0123 is open.", "deadbeefcafe0123"),
        ("3.14x supports", "3.1x supports", "3.1"),
        ("3.14x and net debt", "13.14x and net debt", "3.14"),
        ("7,940 at year", "940 at year", "940"),
        ("| Bottom line |", "| Conclusion |", "Bottom line"),
        ("| Finding |", "| Observation |", "Finding"),
        (f"\n| {BOTTOM_LINE} | Medium | {LIMITATION} |", "", "one row"),
        (FINDING_ROW, "", "findings"),
        (FINDING_ROW, f"| {FINDING} | High |", "three cells"),
    ],
)
def test_a_broken_section_gives_one_issue_naming_the_cause(
    before: str, after: str, cause: str
) -> None:
    assert before in VALID
    issues = reader_issues(VALID.replace(before, after))
    assert len(issues) == 1, issues
    assert cause in issues[0]


def test_a_repeated_section_is_refused() -> None:
    section = VALID[VALID.index("### Reader summary") : VALID.index("### Detail")]
    issues = reader_issues(VALID.replace("### Detail", section + "### Detail"))
    assert len(issues) == 1 and "more than once" in issues[0]


def test_a_number_only_inside_a_longer_number_does_not_match() -> None:
    rest = {"3.14": "13.14", "940": "7,940", "7,940": "7,940.5", "14": "3.14"}
    for number, longer in rest.items():
        text = VALID.replace(BOTTOM_LINE, f"Cover was {number}.").replace(FINDING, "None.")
        text = text.replace(
            "Interest cover was 3.14x and net debt was 7,940.", f"The value was {longer}."
        )
        assert any(f"{number} " in issue for issue in reader_issues(text)), number


def test_numbers_beside_punctuation_still_match() -> None:
    text = VALID.replace(FINDING, "Debt was 7,940, cover 3.14x; dates FY2024 and 30 Sep 2024.")
    text = text.replace("### Detail\n", "### Detail\n\nFY2024 to 30 Sep 2024.\n")
    assert reader_issues(text) == ()


def test_a_number_only_inside_a_hash_or_reference_does_not_match() -> None:
    base = VALID.replace("## Gaps", "## Gaps\n\nFile deadbeef77cafe0123456789 and table T8.25.")
    for number in ("77", "8.25"):
        text = base.replace(BOTTOM_LINE, f"Cover was {number}.")
        assert any(f"number {number} " in issue for issue in reader_issues(text)), number


def test_windows_line_endings_do_not_hide_the_section() -> None:
    assert reader_issues(VALID.replace("\n", "\r\n")) == ()


def with_detail(summary: str, detail: str) -> str:
    """VALID with `summary` as the finding sentence and `detail` as the handoff's own text."""
    text = VALID.replace(FINDING, summary).replace(
        "Interest cover was 3.14x and net debt was 7,940.", detail
    )
    return text.replace(BOTTOM_LINE, "Credit is mixed.")


@pytest.mark.parametrize(
    ("summary", "detail", "accepted"),
    [
        # Sign: the handoff writes a decline as (12.3)%; a summary of 12.3% states a rise.
        ("Revenue grew 12.3%.", "Revenue change was (12.3)%.", False),
        ("Revenue fell by (12.3)%.", "Revenue change was (12.3)%.", True),
        ("Revenue fell by -12.3%.", "Revenue change was (12.3)%.", True),
        ("Revenue fell by (12.3%).", "Revenue change was (12.3)%.", True),
        ("Revenue fell by -12.3%.", "Revenue change was 12.3%.", False),
        # Unit: 4.1x is a multiple, not a percentage; a bare number states no unit.
        ("Leverage is 4.1%.", "Net leverage was 4.1x.", False),
        ("Leverage is 4.1x.", "Net leverage was 4.1x.", True),
        ("Leverage is 4.1.", "Net leverage was 4.1x.", True),
        ("Leverage is 4.1x.", "Net leverage was 4.1.", True),
        # Scale: 250 thousand is not 250 million.
        ("Cash was US$250 million.", "Cash was 250 US$ thousands.", False),
        ("Cash was US$250 thousand.", "Cash was 250 US$ thousands.", True),
        ("Cash was 250 million.", "Cash was 250 millions.", True),
        # Hyphens in ranges and compounds are not minus signs; a footnote marker is not a sign.
        ("Margins held in 2023-2024.", "The years 2023-2024 and a 5-year plan.", True),
        ("A 5-year plan.", "A 5-year plan, see 1) below.", True),
    ],
)
def test_a_summary_figure_keeps_the_sign_unit_and_scale_the_handoff_wrote(
    summary: str, detail: str, accepted: bool
) -> None:
    issues = reader_issues(with_detail(summary, detail))
    assert (issues == ()) is accepted, issues
    if not accepted:
        assert len(issues) == 1 and "does not match the handoff" in issues[0]
        assert detail.split(" was ")[-1].rstrip(".") in issues[0]


@pytest.mark.parametrize(
    ("summary", "absent"),
    [
        # Hand-derived: a malformed figure is still read as its digit runs, as before the sign
        # and unit check; none of these runs is in the handoff, so each is reported.
        ("Version 1.2.3 applies.", ("1.2", "3")),
        ("Dated 28.12.2024.", ("28.12", "2024")),
        ("Margin was 12,5%.", ("12", "5")),
        ("Debt was 1,2345.", ("1", "2345")),
    ],
)
def test_a_malformed_summary_figure_is_still_checked(summary: str, absent: tuple[str, ...]) -> None:
    issues = reader_issues(with_detail(summary, "Nothing numeric here."))
    assert issues == tuple(
        f"Reader summary number {n} does not appear in the handoff" for n in absent
    )


def test_a_malformed_figure_written_the_same_in_the_handoff_matches() -> None:
    assert reader_issues(with_detail("Version 1.2.3 applies.", "Version 1.2.3 applies.")) == ()
