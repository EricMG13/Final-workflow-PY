"""Issuer-tagged zero is distinct from missing and from an untagged dash."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_workflow.inline_xbrl import Fact, parse


def tagged(text: str, *, format: str = "ixt:fixed-zero", nil: bool = False) -> Fact:
    return Fact(
        "f", "us-gaap:DividendsPayableCurrent", "c", "usd", text, 6, False, nil, format, 9, 20
    )


@pytest.mark.parametrize("text", ["—", "–", "-", "", "any text", "123"])
def test_fixed_zero_follows_declared_transform_and_retains_lexeme(text: str) -> None:
    fact = tagged(text)
    assert fact.amount() == Decimal(0)
    assert fact.lexeme == text
    assert replace(fact, nil=True).amount() is None


def test_missing_tag_does_not_turn_a_dash_into_zero() -> None:
    with pytest.raises(ValueError, match="unsupported numeric lexeme"):
        tagged("—", format="").amount()
    with pytest.raises(ValueError, match="unsupported numeric format"):
        tagged("—", format="ixt:unknown").amount()
    assert tagged("—", format="ixt:zerodash").amount() == 0
    assert tagged("1,234", format="ixt:num-dot-decimal").amount() == 1234000000
    assert tagged(".01", format="").amount() == 10000


def test_actual_tdg_dividends_payable_uses_fixed_zero() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "data/public-corpus/v1/TDG/TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228.htm"
    )
    document = parse(source.read_bytes())
    fact = next(f for f in document.facts if f.fact_id == "f-57")
    assert (fact.concept, fact.context_id, fact.unit_id, fact.format, fact.lexeme) == (
        "us-gaap:DividendsPayableCurrent",
        "c-3",
        "usd",
        "ixt:fixed-zero",
        "—",
    )
    instant = document.contexts[fact.context_id].instant
    assert instant is not None and instant.isoformat() == "2024-12-28"
    assert fact.amount() == 0
    par_value = next(f for f in document.facts if f.fact_id == "f-71")
    assert (par_value.lexeme, par_value.scale) == (".01", 0)
    assert par_value.amount() == Decimal("0.01")
