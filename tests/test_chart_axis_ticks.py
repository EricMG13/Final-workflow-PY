"""Axis tick labels carry the precision of the tick step, not the unit class's default.

Scope: synthetic ChartSpecs through charts.render_svg. Each expected axis is derived by hand from
the chart's tick rule (top = nice(max value * headroom), step = nice(range / tick count), with
nice() rounding up to 1, 2, 2.5, 5 or 10 times a power of ten) and is written out below.
"""

import re
from decimal import Decimal

import pytest

from deploy_vii import charts
from deploy_vii.display import format_value, places_to_show
from deploy_vii.report_view import Block, Cell, ChartMark, ChartSpec, Row


def axis_labels(kind: str, values: list[str], unit_class: str = "amount") -> list[str]:
    marks = tuple(
        ChartMark(
            series="A",
            label=f"P{i}",
            value=Decimal(v),
            text=format_value(Decimal(v), unit_class, "known"),
        )
        for i, v in enumerate(values)
    )
    twin = Block(
        block_id="twin",
        title="t",
        owner="o",
        state="populated",
        kind="dense",
        columns=("Value",),
        rows=tuple(
            Row(
                row_id=f"r{i}",
                label=m.label,
                cells=(Cell(text=m.text, state="known", prov="none", unit_class=unit_class),),
            )
            for i, m in enumerate(marks)
        ),
    )
    spec = ChartSpec(kind=kind, series=("A",), table_twin=twin, marks=marks, unit_class=unit_class)
    svg = charts.render_svg(spec, chart_id="c", title="t")
    # The category labels are P0, P1, ...; every other class="ax" text is a tick label.
    return [t for t in re.findall(r'class="ax">([^<]*)</text>', svg) if not t.startswith("P")]


@pytest.mark.parametrize(
    ("kind", "values", "unit_class", "expected"),
    [
        # line 0.4, 0.8: top nice(0.92) = 1, step nice(1/3) = 0.5 -> 0, 0.5, 1.
        ("line", ["0.4", "0.8"], "amount", ["0.0", "0.5", "1.0"]),
        # grouped 0.03, 0.05: top nice(0.056) = 0.1, step nice(0.1/3) = 0.05 -> 0, 0.05, 0.1.
        ("grouped", ["0.03", "0.05"], "amount", ["0.00", "0.05", "0.10"]),
        # waterfall 4 then 5 (running total reaches 9): top nice(9.9) = 10, step nice(10/4) = 2.5.
        ("waterfall", ["4", "5"], "amount", ["0.0", "2.5", "5.0", "7.5", "10.0"]),
        # percent 0.0003, 0.0004 (0.03%, 0.04%): top 0.0005, step nice(0.0005/3) = 0.0002 ->
        # 0, 0.02%, 0.04%: two places, where the class default of one would print 0.0% thrice.
        ("line", ["0.0003", "0.0004"], "percent", ["0.00%", "0.02%", "0.04%"]),
    ],
)
def test_fractional_tick_steps_get_the_places_they_need(kind, values, unit_class, expected):
    assert axis_labels(kind, values, unit_class) == expected


@pytest.mark.parametrize(
    ("values", "unit_class", "expected"),
    [
        # Whole-number steps keep the class default, so existing axes read as before.
        (["400", "800"], "amount", ["0", "500", "1,000"]),
        (["0.004", "0.008"], "percent", ["0.0%", "0.5%", "1.0%"]),
        (["1", "2"], "multiple", ["0.00x", "1.00x", "2.00x"]),
    ],
)
def test_axes_that_were_already_exact_are_unchanged(values, unit_class, expected):
    assert axis_labels("line", values, unit_class) == expected


@pytest.mark.parametrize(
    ("amounts", "unit_class", "expected"),
    [
        (["0", "5", "10"], "amount", 0),  # whole amounts keep the class default of 0
        (["0", "2.5", "5"], "amount", 1),
        (["0.001"], "amount", 3),
        (["0.0000001"], "amount", 6),  # at most six places
        (["0.0002"], "percent", 2),  # 0.0002 is 0.02%
        (["0.5"], "multiple", 2),  # the class default of 2 stands when nothing needs more
        (["0.12345"], "multiple", 5),
    ],
)
def test_places_to_show_is_the_class_default_or_the_places_the_amounts_need(
    amounts, unit_class, expected
):
    assert places_to_show([Decimal(a) for a in amounts], unit_class) == expected


def test_places_to_show_is_none_for_a_class_without_numbers():
    assert places_to_show([Decimal(1)], "text") is None
