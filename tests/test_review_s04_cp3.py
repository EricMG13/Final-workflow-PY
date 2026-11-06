"""Review S04: CP-3 relative value validation and composition (`deploy_vii.cp3_relative_value`).

Synthetic regressions over the cp3-cp6-owner oracle submissions (run as-of 2026-01-10); every
expected text below is written by hand.
"""

import copy
import dataclasses
import json
import re
from typing import Any

import pytest
import test_cp3_context_evidence as context_fixture
import test_method_cp3 as fixture

from deploy_vii import cp3_relative_value as engine
from deploy_vii.contracts import Fact
from deploy_workflow.owners.cp3 import CP3Inputs, CP3Result, compute

BASE = fixture.SUBMISSIONS["positive"]["relative_value"]


def _accepted(inputs: CP3Inputs) -> CP3Inputs:
    bound = tuple(i.model_copy(update={"status": "accepted"}) for i in inputs.bound)
    return dataclasses.replace(inputs, bound=bound, current=bound)


def _second_facility(inputs: CP3Inputs, facility_id: str, name: str) -> CP3Inputs:
    """CP-1 T4.18 with a second facility row (`<facility_id>.fy2025`)."""
    extra = tuple(
        Fact(
            fact_id=f"T4.18.{facility_id}.fy2025.{field}",
            label=field,
            table_id="T4.18",
            row_id=f"{facility_id}.fy2025",
            field=field,
            text=text,
        )
        for field, text in (("facility_id", facility_id), ("facility_name", name))
    )
    cp1 = inputs.cp1.model_copy(update={"facts": (*inputs.cp1.facts, *extra)})
    bound = tuple(
        i.model_copy(update={"sha256": cp1.content_hash()}) if i.input_id == "CP-1" else i
        for i in inputs.bound
    )
    return dataclasses.replace(inputs, cp1=cp1, bound=bound, current=bound)


def _run(literal: Any, *, accept: bool = False, facility: tuple[str, str] | None = None) -> Any:
    inputs = fixture.make_inputs("positive", literal)
    if facility is not None:
        inputs = _second_facility(inputs, *facility)
    return compute(_accepted(inputs) if accept else inputs)


def _with_second_instrument(literal: Any, facility_id: str) -> Any:
    second = copy.deepcopy(literal["instruments"][0])
    second["facility_id"] = facility_id
    literal["instruments"].append(second)
    return literal


def _fact(result: Any, fact_id: str) -> Fact:
    return next(f for f in result.report.facts if f.fact_id == fact_id)


# --- market evidence as_of (adversarial cp3_relative_value.py:1555) -------------------------


@pytest.mark.parametrize(
    ("as_of", "issue"),
    [
        (
            "December 31, 2099",
            "market_evidence[0].as_of December 31, 2099 is after the run as-of 2026-01-10",
        ),
        ("2099-12-31", "market_evidence[0].as_of 2099-12-31 is after the run as-of 2026-01-10"),
        ("none", "market_evidence[0].as_of is not a date (2026-01-09, 9 January 2026 or"),
        ("Q1", "market_evidence[0].as_of is not a date (2026-01-09, 9 January 2026 or"),
    ],
)
def test_a_quoted_row_states_a_date_not_after_the_run(as_of: str, issue: str) -> None:
    literal = copy.deepcopy(BASE)
    literal["market_evidence"][0]["as_of"] = as_of
    result = _run(literal)
    assert result.report is None
    assert any(i.startswith(issue) for i in result.issues), result.issues


@pytest.mark.parametrize("as_of", ["2026-01-09", "09 January 2026", "Jan. 9, 2026"])
def test_date_spellings_of_a_fresh_quote_compose(as_of: str) -> None:
    literal = copy.deepcopy(BASE)
    literal["market_evidence"][0]["as_of"] = as_of
    result = _run(literal)
    assert result.issues == ()


STALE = (
    "Stale quote: market_evidence[0] market quote dated January 9, 2019 is 2558 days before "
    "the run as-of 2026-01-10 (limit 30)"
)


def test_a_stale_model_quote_caps_confidence_like_a_context_quote() -> None:
    literal = copy.deepcopy(BASE)
    literal["market_evidence"][0]["as_of"] = "January 9, 2019"
    literal["preference"]["confidence"] = "High"
    result = _run(literal, accept=True)
    assert result.issues == (
        (
            "preference.confidence: capped below High because a market evidence quote is more "
            "than 30 days old"
        ),
    )


def test_a_stale_model_quote_is_an_own_limitation() -> None:
    literal = copy.deepcopy(BASE)
    literal["market_evidence"][0]["as_of"] = "January 9, 2019"
    result = _run(literal)
    assert result.issues == ()
    assert STALE in result.report.limitations


def test_the_oracle_quote_dates_are_fresh() -> None:
    result = _run(copy.deepcopy(BASE))
    assert result.issues == ()
    assert not any(line.startswith("Stale quote") for line in result.report.limitations)


# --- a none row's source (adversarial cp3_relative_value.py:1066) ----------------------------


def test_a_none_row_never_names_an_invented_source() -> None:
    literal = copy.deepcopy(BASE)
    literal["market_evidence"].append(
        {
            "source_id": "Bloomberg TRACE feed",
            "kind": "none",
            "quote": None,
            "as_of": "Not available",
            "limitation": "No trade reported",
        }
    )
    result = _run(literal)
    assert result.report is None
    assert (
        "market_evidence[2]: a none row's source_id is none or a pack source, not "
        "Bloomberg TRACE feed"
    ) in result.issues


def test_a_none_row_may_name_none_or_a_pack_source() -> None:
    for source_id in ("none", "financial"):
        literal = copy.deepcopy(BASE)
        literal["market_evidence"].append(
            {
                "source_id": source_id,
                "kind": "none",
                "quote": None,
                "as_of": "Not available",
                "limitation": "No trade reported",
            }
        )
        result = _run(literal)
        assert result.issues == (), source_id
        assert _fact(result, "T3.3.m03.source").text == source_id


# --- facility coverage, the talk-only cap and the withheld ranking ---------------------------


def test_every_cp1_facility_has_an_instruments_row() -> None:
    result = _run(copy.deepcopy(BASE), facility=("notes-2031", "Northbridge 2031 Notes"))
    assert result.report is None
    assert "instruments: CP-1 facility notes-2031 has no instruments row" in result.issues


def test_a_preference_citing_talk_only_is_capped_below_high() -> None:
    literal = copy.deepcopy(BASE)
    literal["preference"]["basis"]["quotes"] = [literal["market_evidence"][1]["quote"]]
    literal["preference"]["confidence"] = "High"
    result = _run(literal, accept=True)
    assert result.issues == (
        (
            "preference.confidence: capped below High because the market evidence is indicative "
            "talk only"
        ),
    )


def test_insufficient_information_ranks_no_instruments() -> None:
    literal = _with_second_instrument(copy.deepcopy(BASE), "notes-2031")
    literal["preference"]["ordering"] = ["term-loan", "notes-2031"]
    literal["preference"]["confidence"] = "Insufficient Information"
    result = _run(literal, facility=("notes-2031", "Northbridge 2031 Notes"))
    assert result.report is None
    assert (
        "preference.ordering: an Insufficient Information preference ranks no instruments"
        in result.issues
    )


def test_two_facilities_with_one_name_are_told_apart_by_id() -> None:
    literal = _with_second_instrument(copy.deepcopy(BASE), "term-loan-2")
    literal["preference"]["ordering"] = ["term-loan-2", "term-loan"]
    result = _run(literal, facility=("term-loan-2", "Northbridge Term Loan"))
    assert result.issues == ()
    assert _fact(result, "T3.4.preference.ordering").text == (
        "Northbridge Term Loan (term-loan-2) > Northbridge Term Loan (term-loan)"
    )


# --- claim limitations are spelled (code review cp3_relative_value.py:1724/1731) -------------


def test_claim_limitations_spell_their_figure_references() -> None:
    literal = copy.deepcopy(BASE)
    literal["preference"]["limitation"] = "Provisional at {{FIG:total_leverage_reported}} leverage"
    literal["instruments"][0]["limitation"] = "One quote at {{FIG:net_leverage_reported}} net"
    result = _run(literal)
    assert result.issues == ()
    claims = {c.claim_id: c for c in result.report.claims}
    assert claims["T3.4.preference"].limitation == "Provisional at 1.67x leverage"
    assert claims["T3.1.i01"].limitation == "One quote at 1.00x net"


# --- the context file's deal talk (code review cp3_relative_value.py:599) --------------------


def test_an_inverted_talk_range_is_refused() -> None:
    raw = context_fixture.context_bytes("deal-talk").decode()
    low = re.search(r'"talk_spread_bps_low": "([0-9.]+)"', raw)
    high = re.search(r'"talk_spread_bps_high": "([0-9.]+)"', raw)
    assert low is not None and high is not None and low[1] != high[1]
    document = json.loads(raw)
    deal = next(d for d in document["deal_terms"] if d["talk_spread_bps_low"])
    deal["talk_spread_bps_low"], deal["talk_spread_bps_high"] = high[1], low[1]
    index = document["deal_terms"].index(deal)
    edited = json.dumps(document, indent=2).encode()
    pack = context_fixture.pack_for(
        "deal-talk", context_fixture.context_source("deal-talk", edited)
    )
    inputs = context_fixture.inputs_for("deal-talk", pack)
    evidence = engine.context_evidence(pack, engine.facilities(inputs.cp1))
    assert evidence.rows == ()
    assert (
        f"context source unreadable: deal_terms[{index}].talk_spread_bps_low must not exceed "
        "talk_spread_bps_high"
    ) in evidence.issues


def test_cp3_result_type_is_unchanged() -> None:
    assert isinstance(_run(copy.deepcopy(BASE)), CP3Result)
