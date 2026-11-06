"""Review S04: CP-3's instrument-action phrases (`business_context.ACTIONS`) on synthetic text."""

import pytest

from deploy_vii.business_context import prohibited_issues
from deploy_vii.cp3_relative_value import CP3_PROHIBITED_KINDS


@pytest.mark.parametrize(
    "text",
    [
        "The sponsor sold its European unit and used proceeds to repay the term loan.",
        "The issuer bought back notes below par during the year.",
        "The loan funded a buy-and-build strategy.",
        "Asset sell-downs reduce secured debt.",
        "A broad sell-off widened spreads.",
    ],
)
def test_issuer_history_is_not_an_instrument_action(text: str) -> None:
    assert prohibited_issues("x", text, kinds=CP3_PROHIBITED_KINDS) == ()


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("Holders should sell the notes.", "sell"),
        ("We would buy the term loan.", "buy"),
        ("Switch into the notes.", "switch into"),
        ("The analysis recommends the term loan.", "recommends"),
        ("Overweight the secured tranche.", "overweight"),
    ],
)
def test_action_phrases_stay_prohibited(text: str, phrase: str) -> None:
    assert prohibited_issues("x", text, kinds=CP3_PROHIBITED_KINDS) == (
        f'x: prohibited conclusion (instrument action): "{phrase}"',
    )
