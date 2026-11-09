"""`quotes.quoted_whole`: a value token quoted out of a larger quote (S13 A03/C05, S16 A01).

A fragment cut out of a larger figure or word is not a quote of it: the occurrence must start and
end on a word or number boundary. `quoted` keeps the plain substring rule for citation quotes
(the owners' figure readers refuse a cut figure at a quote edge themselves, round 11 B1).
Expectations are stated by hand from that rule.
"""

import pytest

from deploy_vii.cp4_legal import parse_threshold
from deploy_vii.quotes import quoted, quoted_whole

COVENANT = "the Total Net Leverage Ratio shall not exceed 12.50:1.00 as of the last day"


@pytest.mark.parametrize(
    ("quote", "text"),
    [
        ("2.50:1.00", COVENANT),  # cut after the leading 1 of 12.50
        ("50:1.00", COVENANT),  # cut after the decimal point of 12.50
        (".50:1.00", COVENANT),  # starts on the decimal point between digits
        ("12.5", COVENANT),  # cut before the final 0
        ("12.50:1.0", COVENANT),  # cut inside 1.00
        ("1.2 billion", "total debt of $11.2 billion"),
        ("1,000", "revenue of 21,000 million"),
        ("21", "revenue of 21,000 million"),  # cut before the thousands separator
        ("evenue", "revenue of 21,000 million"),  # cut inside a word
        ("a", "The Company has an amended facility"),  # only inside words
        ("66", "at least 66⅔% of the holders"),  # the fraction character is a digit
    ],
)
def test_fragment_inside_a_word_or_number_is_not_a_whole_quote(quote: str, text: str) -> None:
    assert not quoted_whole(quote, text)
    assert quoted(quote, text)  # the plain substring rule of citation quotes is unchanged


@pytest.mark.parametrize(
    ("quote", "text"),
    [
        ("12.50:1.00", COVENANT),
        ("shall not exceed 12.50:1.00", COVENANT),
        ("1.00", COVENANT),  # a whole number after the ratio colon
        ("$11.2 billion", "total debt of $11.2 billion."),
        ("11.2 billion", "total debt of $11.2 billion."),  # `$` is not part of the number
        ("21,000 million", "revenue of 21,000 million, up"),
        ("December 31", "as of December 31, 2025"),  # comma then space is not a separator
        ("priority", "first-\npriority liens"),  # the joined wrap; `-` is a boundary
        ("a", "The Company has a revolving facility"),  # a whole word
        ("5.00", "shall not exceed 5.00x"),  # a multiplier suffix is not part of the number
        ("1.2", "debt of $1.2bn"),
        ("2025", "for FY2025"),
        ("66⅔%", "at least 66⅔% of the holders"),
        ("(12.5)", "a loss of (12.5) million"),
        ("12.5", "a loss of -12.5 million"),  # the sign is a boundary; sign reading is the caller's
    ],
)
def test_whole_words_and_numbers_match(quote: str, text: str) -> None:
    assert quoted_whole(quote, text)
    assert quoted(quote, text)


def test_a_later_whole_occurrence_still_matches() -> None:
    # The first occurrence (in 12.50) is cut; the second stands alone.
    assert quoted_whole("2.50", "between 12.50 and 2.50 times")


def test_blank_quote_matches_nothing() -> None:
    assert not quoted_whole(" ­ ", COVENANT)


def test_cut_threshold_no_longer_verifies_a_wrong_covenant_level() -> None:
    # A 12.50x covenant must not be recorded as 2.50x: parse_threshold reads 2.50 from the cut
    # threshold_text, so the quote check is what refuses it.
    assert parse_threshold("2.50:1.00", "multiple")[0] is not None
    assert not quoted_whole("2.50:1.00", COVENANT)
