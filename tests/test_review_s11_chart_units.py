"""S11 review: chart cells keep their own quantity family, unit and displayed precision.

Synthetic handoffs; expected amounts, units and decimals are literal values.
"""

import json
from decimal import Decimal

import pytest

from deploy_workflow.handoff_delivery import MarkdownRoute, delivery_files, token_decimals
from deploy_workflow.markdown_delivery import _numeric_observations, literal_module


def chart(header: str, rows: list[str], **route: object):
    raw = (
        "# CP-1 Acme\n## Request\nAcme Corp.\n## Sources\nx\n## Findings\n"
        f"### Chart data: liquidity\n{header}\n|---|---|---|---|\n" + "\n".join(rows) + "\n"
        "## Calculations\nNone.\n## Gaps\nNone.\n## Next module\nDelivery.\n"
    ).encode()
    module, _, _ = literal_module("CP-1", raw)
    table = next(t for t in module.tables if t.row_header == "Period")
    selected = MarkdownRoute.model_validate(
        {
            "module_id": "CP-1",
            "heading": "Chart data: liquidity",
            "kind": "chart",
            "block_id": "model-chart-strip",
            "figure_id": "S.3",
            "orientation": "period-rows",
            "chart_unit": "US$m",
            **route,
        }
    )
    return _numeric_observations(module, table, selected)


def typed(result):
    module, _, points = result
    facts = {f.fact_id: f for f in module.facts}
    return [
        (
            facts[p.fact_id].period,
            facts[p.fact_id].amount,
            facts[p.fact_id].status,
            facts[p.fact_id].unit,
            facts[p.fact_id].decimals,
        )
        for p in points
    ]


def test_per_share_column_in_period_rows_is_refused():
    with pytest.raises(ValueError, match="share/per-share quantities are not monetary totals"):
        chart(
            "| Period | EPS, USD per share | Reporting unit | Basis and limitation |",
            ["| FY2024 | 3.25 | US$m | reported |"],
            value_columns=("EPS, USD per share",),
        )


def test_source_reporting_unit_outranks_the_route_unit():
    with pytest.raises(ValueError, match="source Reporting unit 'EUR thousands'"):
        chart(
            "| Period | Cash | Reporting unit | Basis and limitation |",
            ["| FY2024 | 3.25 | EUR thousands | reported |"],
            value_columns=("Cash",),
        )


def test_matching_or_unstated_unit_types_the_exact_value():
    assert typed(
        chart(
            "| Period | Cash | Reporting unit | Basis and limitation |",
            ["| FY2024 | 1,234.5 | US$m | reported |", "| FY2025 | 812 |  | reported |"],
            value_columns=("Cash",),
        )
    ) == [
        ("FY2024", Decimal("1234.5"), "known", "MILLIONS", 1),
        ("FY2025", Decimal(812), "known", "MILLIONS", 0),
    ]


def test_gap_in_another_unit_stays_a_gap_not_a_refusal():
    assert typed(
        chart(
            "| Period | Cash | Reporting unit | Basis and limitation |",
            ["| FY2024 | Not supplied: reported in EUR thousands | EUR thousands | reported |"],
            value_columns=("Cash",),
        )
    ) == [("FY2024", None, "missing", "MILLIONS", 2)]


@pytest.mark.parametrize(
    "token,unit_class,places",
    [
        ("6.425", "multiple", 3),
        ("4", "multiple", 0),
        ("(1,234.50)", "amount", 2),
        ("0.0625", "percent", 2),
        ("0.05", "percent", 0),
        ("1.123456789", "amount", 6),
    ],
)
def test_display_places_come_from_the_source_spelling(token, unit_class, places):
    assert token_decimals(token, unit_class) == places


def test_table_route_into_a_chart_block_is_refused(tmp_path):
    from test_pathway_handoff_charts import job

    manifest = job(tmp_path)
    data = json.loads(manifest.read_bytes())
    route = dict(data["layout"]["routes"][1], block_id="model-chart-strip")
    data["layout"]["routes"].append(route)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="a chart block shows only chart routes"):
        delivery_files(manifest)
