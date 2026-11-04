"""Independent gpt-6.1-sol Standard/global30m tier and conservative hold oracle."""

import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from _pack import ScriptedAdapter, make_rig, ok

from deploy_workflow.model.loop import StepStopped
from deploy_workflow.model.pricing import (
    PRICES,
    ContextTooLong,
    ModelPrice,
    Priced,
    computed_usd,
    price_usage,
    request_reservation_usd,
)
from deploy_workflow.model.turn import Usage

ORACLE = json.loads((Path(__file__).parents[2] / "cases/pricing/sol-long-context.json").read_text())
D = Decimal


@pytest.mark.parametrize("config", ORACLE["configurations"])
@pytest.mark.parametrize("index", range(len(ORACLE["computed_examples"])))
def test_tier_examples_are_exact_for_both_sol_efforts(config: str, index: int) -> None:
    row = ORACLE["computed_examples"][index]
    usage = Usage(
        input_tokens=row["input_tokens"],
        cached_read_tokens=row["cached_read_tokens"],
        cache_write_tokens=row["cache_write_tokens"],
        output_tokens=row["output_tokens"],
        reasoning_tokens=165 if row["input_tokens"] == 280184 else 0,
    )
    assert price_usage(config, usage) == Priced(D(row["usd"]), "computed")


def test_threshold_switches_whole_request_and_is_strict() -> None:
    std, long = ORACLE["computed_examples"][:2]

    def usage(row: dict[str, int]) -> Usage:
        return Usage(**{key: value for key, value in row.items() if key != "usd"})

    assert price_usage("sol-medium", usage(std)).usd == D("0.54400000")
    assert price_usage("sol-medium", usage(long)).usd == D("1.08800400")
    assert price_usage("sol-medium", Usage(input_tokens=272_000, output_tokens=1)).usd == D(
        "0.54401000"
    )
    assert price_usage("sol-medium", Usage(input_tokens=272_001, output_tokens=1)).usd == D(
        "1.08801900"
    )


def test_actual_e4240_usage_is_long_tier_and_reasoning_is_already_output() -> None:
    row = ORACLE["computed_examples"][-1]
    usage = Usage(
        input_tokens=280184,
        cached_read_tokens=3544,
        cache_write_tokens=276514,
        output_tokens=3152,
        reasoning_tokens=165,
    )
    charge = price_usage("sol-high", usage).usd
    assert charge == D(row["usd"])
    assert Fraction(charge) == Fraction(D("1.43106280"))


def test_missing_tier_or_usage_fields_fail_closed() -> None:
    incomplete = ModelPrice(
        input=D(2),
        cached_read=D("0.1"),
        cache_write=D("2.5"),
        output=D(10),
        long_context_after=272_000,
        long_input=D(4),
    )
    assert (
        price_usage("sol-medium", Usage(input_tokens=272_001, output_tokens=1)).cost_status
        == "computed"
    )
    assert computed_usd("openai", incomplete, Usage(input_tokens=272_001, output_tokens=1)) is None
    assert (
        price_usage("sol-high", Usage(input_tokens=272_001, output_tokens=None)).cost_status
        == "unknown"
    )
    assert price_usage(
        "sol-high", Usage(input_tokens=1_050_001, cached_read_tokens=0, output_tokens=0)
    ) == Priced(None, "unknown")


def test_live_reservation_uses_ceiling_and_refuses_above_it() -> None:
    price = PRICES["sol-medium"]
    policy = ORACLE["reservation_policy"]
    expected = D(policy["reservation_usd"])
    assert Fraction(expected) == Fraction(
        policy["context_ceiling_input_tokens"] * 5 + policy["output_max_tokens"] * 15,
        1_000_000,
    )
    assert request_reservation_usd(price, 12_000, policy["output_max_tokens"]) == expected
    assert (
        request_reservation_usd(
            price, policy["context_ceiling_input_tokens"], policy["output_max_tokens"]
        )
        == expected
    )
    with pytest.raises(ContextTooLong):
        request_reservation_usd(
            price, policy["context_ceiling_input_tokens"] + 1, policy["output_max_tokens"]
        )


@pytest.mark.parametrize(
    ("price", "input_rate", "output_rate"),
    [
        (
            ModelPrice(
                input=D(9),
                cached_read=D(12),
                cache_write=D(7),
                output=D(20),
                long_context_after=3,
                long_input=D(5),
                long_cached_read=D(6),
                long_cache_write=D(8),
                long_output=D(15),
                max_context_tokens=10,
                reservation_context_tokens=10,
            ),
            12,
            20,
        ),
        (
            ModelPrice(
                input=D(4),
                cached_read=D(3),
                cache_write=D(5),
                output=D(10),
                long_context_after=3,
                long_input=D(8),
                long_cached_read=D(7),
                long_cache_write=D(6),
                long_output=D(16),
                max_context_tokens=10,
                reservation_context_tokens=10,
            ),
            8,
            16,
        ),
        (
            ModelPrice(
                input=D(9),
                cached_read=D(7),
                cache_write=D(6),
                output=D(20),
                long_context_after=3,
                long_input=D(8),
                long_cached_read=D(5),
                long_cache_write=D(4),
                long_output=D(15),
                max_context_tokens=10,
                reservation_context_tokens=10,
            ),
            9,
            20,
        ),
    ],
)
def test_custom_ceiling_hold_covers_the_highest_input_and_output_tiers(
    price: ModelPrice, input_rate: int, output_rate: int
) -> None:
    assert request_reservation_usd(price, 1, 2) == D(10 * input_rate + 2 * output_rate) / 10**6


def test_live_loop_refuses_insufficient_hold_before_adapter_send(tmp_path: Path) -> None:
    rig = make_rig(
        tmp_path,
        [ok()],
        adapter=ScriptedAdapter([ok()], ruling=Path("docs/rulings/live.md")),
        cap="6.72455999",
        max_output=ORACLE["reservation_policy"]["output_max_tokens"],
    )
    with pytest.raises(StepStopped) as stopped:
        rig.loop.run()
    assert stopped.value.reason == "BudgetExhausted"
    assert rig.adapter.sent == []
    (record,) = rig.records()
    assert record["error_class"] == "BudgetExhausted"
    assert (record["reserved_usd"], record["settled_usd"]) == ("0", "0")
