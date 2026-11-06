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
