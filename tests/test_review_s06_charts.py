"""S06 review fixes in ``deploy_vii.charts``: missing is never zero, ticks keep their precision,
negative values stay on the axis. Expected texts are literals written from the specs below.
"""

import re
from decimal import Decimal

from deploy_vii.charts import render_svg
from deploy_vii.display import format_value
from deploy_vii.report_view import Block, Cell, ChartMark, ChartSpec, Row

Point = tuple[str, str, str | None, str, int | None]


def _spec(
    kind: str,
    series: tuple[str, ...],
    points: list[Point],
    unit_class: str = "amount",
    denominator: str | None = None,
) -> ChartSpec:
    """One mark per point: (series, category, value or None for a gap, role, decimals)."""
    marks, rows = [], []
    for index, (name, label, value, role, decimals) in enumerate(points):
        if value is None:
            ref = f"G{index + 1}"
            text = format_value(None, unit_class, "gap", gap_id=ref)  # type: ignore[arg-type]
            cell = Cell(text=text, prov="gap", gap_ref=ref, unit_class=unit_class, state="gap")
        else:
            ref = f"C{index + 1}"
            text = format_value(Decimal(value), unit_class, "known", decimals=decimals)  # type: ignore[arg-type]
            cell = Cell(text=text, prov="cited", ref_id=ref, unit_class=unit_class, state="known")
        marks.append(
            ChartMark(
                series=name,
                label=label,
                text=text,
                ref_id=ref,
                value=None if value is None else Decimal(value),
                role=role,
                decimals=decimals,
            )
        )
        rows.append(Row(row_id=f"r{index}", label=label, cells=(cell,)))
    twin = Block(
        block_id="twin",
        title="Twin",
        owner="MODEL",
        state="populated",
        kind="dense",
        columns=("Value",),
        rows=tuple(rows),
    )
    return ChartSpec(
        kind=kind,
        series=series,
        table_twin=twin,
        marks=tuple(marks),
        unit_class=unit_class,
        denominator=None if denominator is None else Decimal(denominator),
    )


def _labels(svg: str) -> list[str]:
    return re.findall(r'<g [^>]*aria-label="([^"]*)"', svg)


def _axis_y_ticks(svg: str) -> list[str]:
    return re.findall(r'text-anchor="end" class="ax">([^<]*)<', svg)


def _bridge(opening: str | None, middle: str | None) -> list[Point]:
    return [
        ("Cash", "Opening cash", opening, "total", None),
        ("Cash", "Operating cash flow", "40", "value", None),
        ("Cash", "Capex", "-15", "value", None),
        ("Cash", "Debt service", middle, "value", None),
        ("Cash", "Tax", "-5", "value", None),
        ("Cash", "Closing cash", "130", "total", None),
    ]


def test_a_waterfall_after_a_gap_states_no_running_total() -> None:
    svg = render_svg(_spec("waterfall", ("Cash",), _bridge(None, None)), chart_id="w", title="t")
    assert _labels(svg) == [
        "Cash, Opening cash: ∅ G1 (gap G1)",
        "Cash, Operating cash flow: 40, running total unknown (cited C2)",
        "Cash, Capex: (15), running total unknown (cited C3)",
        "Cash, Debt service: ∅ G4 (gap G4)",
        "Cash, Tax: (5), running total unknown (cited C5)",
        "Cash, Closing cash: 130 (cited C6)",
    ]
    assert "running total 25" not in svg and "running total 40" not in svg
    # Only the re-anchoring total is drawn as a bar; no connector leaves an unknown level.
    assert svg.count('class="bar wf-') == 1
    assert svg.count('class="connector"') == 0


def test_a_middle_gap_unanchors_the_steps_after_it_until_a_total() -> None:
    svg = render_svg(_spec("waterfall", ("Cash",), _bridge("100", None)), chart_id="w", title="t")
    assert _labels(svg) == [
        "Cash, Opening cash: 100 (cited C1)",
        "Cash, Operating cash flow: 40, running total 140 (cited C2)",
        "Cash, Capex: (15), running total 125 (cited C3)",
        "Cash, Debt service: ∅ G4 (gap G4)",
        "Cash, Tax: (5), running total unknown (cited C5)",
        "Cash, Closing cash: 130 (cited C6)",
    ]


def test_a_complete_bridge_keeps_its_running_totals() -> None:
    svg = render_svg(_spec("waterfall", ("Cash",), _bridge("100", "-10")), chart_id="w", title="t")
    assert _labels(svg)[3:5] == [
        "Cash, Debt service: (10), running total 115 (cited C4)",
        "Cash, Tax: (5), running total 110 (cited C5)",
    ]
    assert svg.count('class="bar wf-') == 6


def test_a_debt_stack_after_a_gap_states_no_cumulative_multiple() -> None:
    points: list[Point] = [
        ("Debt", "RCF", "100", "value", None),
        ("Debt", "TLB", None, "value", None),
        ("Debt", "Notes", "200", "value", None),
    ]
    svg = render_svg(
        _spec("debt_stack", ("Debt",), points, denominator="100"), chart_id="d", title="t"
    )
    assert _labels(svg) == [
        "Debt, RCF: 100, cumulative 1.00x (cited C1)",
        "Debt, TLB: ∅ G2 (gap G2)",
        "Debt, Notes: 200, cumulative unknown (cited C3)",
    ]
    assert "3.00x" not in svg  # the axis ends at the last known cumulative multiple, 1.00x
    assert re.findall(r'class="ax">(\d\.\d\dx)<', svg) == ["1.00x"]


def _stack_total(svg: str) -> list[str]:
    return re.findall(r'class="lb small">([^<]*)<', svg)


def test_a_stack_with_a_gap_component_has_no_total() -> None:
    points: list[Point] = [("A", "FY24", "100", "value", None), ("B", "FY24", None, "value", None)]
    svg = render_svg(_spec("stacked", ("A", "B"), points), chart_id="s", title="t")
    assert _stack_total(svg) == []


def test_a_stack_total_keeps_its_components_declared_decimals() -> None:
    points: list[Point] = [("A", "FY24", "0.25", "value", 2), ("B", "FY24", "0.30", "value", 2)]
    svg = render_svg(_spec("stacked", ("A", "B"), points), chart_id="s", title="t")
    assert _stack_total(svg) == ["0.55"]


def test_a_negative_stack_stays_inside_the_plot() -> None:
    points: list[Point] = [
        ("A", "FY24", "-60", "value", None),
        ("B", "FY24", "-60", "value", None),
        ("A", "FY25", "50", "value", None),
        ("B", "FY25", "10", "value", None),
    ]
    svg = render_svg(_spec("stacked", ("A", "B"), points), chart_id="s", title="t")
    assert _axis_y_ticks(svg) == ["(200)", "(100)", "0", "100"]
    plot_bottom = 160 - 26.0
    for y, height in re.findall(
        r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"', svg
    ):
        assert float(y) + float(height) <= plot_bottom + 0.01


def test_sub_unit_amount_ticks_are_spelled_exactly() -> None:
    points: list[Point] = [("Cash", "FY24", "0.4", "value", 1), ("Cash", "FY25", "0.7", "value", 1)]
    svg = render_svg(_spec("grouped", ("Cash",), points), chart_id="g", title="t")
    assert _axis_y_ticks(svg) == ["0.0", "0.5", "1.0"]


def test_per_share_ticks_honour_the_declared_decimals() -> None:
    points: list[Point] = [("EPS", "FY23", "0.12", "value", 2), ("EPS", "FY24", "0.31", "value", 2)]
    svg = render_svg(_spec("line", ("EPS",), points), chart_id="l", title="t")
    assert _axis_y_ticks(svg) == ["0.00", "0.20", "0.40"]


def test_a_two_and_a_half_step_is_not_rounded_into_uneven_labels() -> None:
    points: list[Point] = [
        ("Cash", "Opening", "9", "total", None),
        ("Cash", "Flow", "-2", "value", None),
    ]
    svg = render_svg(_spec("waterfall", ("Cash",), points), chart_id="w", title="t")
    assert _axis_y_ticks(svg) == ["0.0", "2.5", "5.0", "7.5", "10.0"]


def test_whole_number_ticks_are_unchanged() -> None:
    points: list[Point] = [
        ("Cash", "FY24", "40", "value", None),
        ("Cash", "FY25", "70", "value", None),
    ]
    svg = render_svg(_spec("grouped", ("Cash",), points), chart_id="g", title="t")
    assert _axis_y_ticks(svg) == ["0", "50", "100"]


def test_an_all_negative_percent_axis_tops_out_at_zero() -> None:
    points: list[Point] = [
        ("Margin", "FY23", "-0.02", "value", None),
        ("Margin", "FY24", "-0.03", "value", None),
    ]
    svg = render_svg(_spec("line", ("Margin",), points, "percent"), chart_id="l", title="t")
    assert _axis_y_ticks(svg) == ["(4.0)%", "(2.0)%", "0.0%"]


def test_an_all_zero_axis_still_spans_zero_to_one() -> None:
    points: list[Point] = [
        ("Cash", "FY24", "0", "value", None),
        ("Cash", "FY25", "0", "value", None),
    ]
    svg = render_svg(_spec("grouped", ("Cash",), points), chart_id="g", title="t")
    assert _axis_y_ticks(svg) == ["0.0", "0.5", "1.0"]


def _bullet(current: str) -> str:
    points: list[Point] = [
        ("Threshold", "Interest cover", "2.0", "value", None),
        ("Current", "Interest cover", current, "value", None),
    ]
    spec = _spec("bullet", ("Threshold", "Current"), points, "multiple")
    return render_svg(spec, chart_id="b", title="t")


def test_a_negative_bullet_value_is_drawn_left_of_zero_on_the_axis() -> None:
    svg = _bullet("-1.2")
    ticks = re.findall(r'text-anchor="middle" class="ax">([^<]*)<', svg)
    # Axis: -_nice(1.2 * 1.1) = -2 to _nice(2.0 * 1.1) = 2.5, step _nice(4.5 / 4) = 2.
    assert ticks == ["(2.00)x", "0.00x", "2.00x"]
    zero_x = float(re.findall(r'<line x1="([\d.]+)"[^>]*class="grid"', svg)[1])
    ((x, width),) = re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="12"', svg)
    assert float(x) >= 190.0  # inside the plot, not over the category labels
    assert abs(float(x) + float(width) - zero_x) < 0.01  # ends at zero
    assert float(width) > 20  # a real length, not a 1px stub at the axis origin
    # Its text sits right of the zero line, clear of the bar and the category gutter.
    (text_x,) = re.findall(r'<text x="([\d.]+)" y="[\d.]+" class="lb small">\(1\.20\)x<', svg)
    assert float(text_x) == zero_x + 6


def test_a_positive_bullet_keeps_its_axis_from_zero() -> None:
    svg = _bullet("3.1")
    ticks = re.findall(r'text-anchor="middle" class="ax">([^<]*)<', svg)
    # Axis: 0 to _nice(3.1 * 1.1) = 5, step _nice(5 / 4) = 2.
    assert ticks == ["0.00x", "2.00x", "4.00x"]
    ((x, _),) = re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="12"', svg)
    assert float(x) == 190.0


def test_a_bridge_with_no_known_level_draws_no_axis() -> None:
    points: list[Point] = [
        ("Cash", "Opening cash", None, "total", None),
        ("Cash", "Inflow", "10", "value", None),
        ("Cash", "Outflow", "-5", "value", None),
    ]
    svg = render_svg(_spec("waterfall", ("Cash",), points), chart_id="w", title="t")
    assert _axis_y_ticks(svg) == []
    assert _labels(svg)[1:] == [
        "Cash, Inflow: 10, running total unknown (cited C2)",
        "Cash, Outflow: (5), running total unknown (cited C3)",
    ]
