"""Retained publication integration and synthetic chart-boundary checks, not live proof."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import View
from deploy_vii.display import format_value
from deploy_vii.report_view import ReportView
from deploy_workflow.handoff_delivery import MarkdownRoute, delivery_files
from deploy_workflow.markdown_delivery import _numeric_observations, literal_module

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runs/cpos-sol-medium-20261105"


def job(tmp_path):
    data = json.loads(next(SOURCE.glob("delivery-*.json")).read_bytes())
    for item in data["handoffs"].values():
        item["path"] = str((SOURCE / item["path"]).resolve())
    for item in data["model"]["extra_handoffs"].values():
        item["path"] = str((SOURCE / item["path"]).resolve())
    if data["model"]["forecast_exact"]:
        data["model"]["forecast_exact"]["path"] = str(
            (SOURCE / data["model"]["forecast_exact"]["path"]).resolve()
        )
    data["layout"] = {
        "blocks": ["financials-credit-metrics", "company-profile", "model-chart-strip"],
        "scope": "Retained annual source/calc publication; synthetic maturity gap tests adapter only.",
        "routes": [
            {
                "module_id": "CP-MODEL",
                "heading": "Annual source and computation register",
                "kind": "table",
                "block_id": "financials-credit-metrics",
            },
            {
                "module_id": "CP-1A",
                "heading": "Business model",
                "kind": "table",
                "block_id": "company-profile",
            },
        ],
    }
    for fid, heading, rows in [
        (
            "S.1",
            "Defined historical ratios — not covenant/agency measures",
            [
                "Carrying borrowing / issuer EBITDA As Defined",
                "Mechanical net carrying borrowing / issuer EBITDA As Defined",
            ],
        ),
        (
            "S.2",
            "Defined historical ratios — not covenant/agency measures",
            ["Issuer EBITDA As Defined / reported cash interest"],
        ),
        ("S.3", "Annual source and computation register", ["Cash"]),
    ]:
        data["layout"]["routes"].append(
            {
                "module_id": "CP-MODEL",
                "heading": heading,
                "kind": "chart",
                "block_id": "model-chart-strip",
                "figure_id": fid,
                "value_columns": ["FY2022", "FY2023", "FY2024"],
                "row_labels": rows,
                "chart_unit": "x" if fid in ["S.1", "S.2"] else "US$m",
            }
        )
    raw = b"# CP-4 TDG\n\n## Request\nTransDigm Group Incorporated. Synthetic gap only.\n## Sources\nSynthetic test.\n## Findings\n### Maturity\n| Period | Principal USDm |\n|---|---|\n| FY2027 disputed | Not supplied: year allocation unresolved |\n## Calculations\nNone.\n## Gaps\nSynthetic gap.\n## Next module\nDelivery.\n"
    answer = tmp_path / "maturity.md"
    answer.write_bytes(raw)
    data["handoffs"]["CP-4"] = {"path": str(answer), "sha256": hashlib.sha256(raw).hexdigest()}
    data["layout"]["routes"].append(
        {
            "module_id": "CP-4",
            "heading": "Maturity",
            "kind": "chart",
            "block_id": "model-chart-strip",
            "figure_id": "S.4",
            "value_columns": ["Principal USDm"],
            "orientation": "period-rows",
            "chart_unit": "US$m",
        }
    )
    # Use the real current handoff's exact business-register selector.
    current = Path(data["handoffs"]["CP-1A"]["path"]).read_text()
    module, _, meta = literal_module("CP-1A", current.encode())
    selected = next(t for t in module.tables if t.row_header == "ID / required row")
    data["layout"]["routes"][1]["heading"] = meta[selected.table_id][0]
    data["layout"]["routes"][1]["table_header"] = selected.row_header
    manifest = tmp_path / "delivery.json"
    manifest.write_text(json.dumps(data))
    return manifest


def test_model_and_full_chart_strip_reuse_exact_handoff_values(tmp_path):
    manifest = job(tmp_path)
    files = delivery_files(manifest)
    report = ReportView.model_validate_json(files["report-view.json"])
    view = View.model_validate_json(files["view.json"])
    assert [b.kind for b in report.blocks] == ["period_grid", "keyvalue", "chart"]
    figures = report.blocks[-1].figures
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4"]
    assert [m.value for m in figures[2].chart.marks] == [
        Decimal(3001),
        Decimal(3472),
        Decimal(6261),
    ]
    assert [m.value for m in figures[3].chart.marks] == [None]
    assert figures[3].chart.marks[0].ref_id.startswith("G")
    assert "G" in figures[3].chart.table_twin.rows[0].cells[0].text
    assert "model.html" in files and "calculation.json" in files
    assert b'["model", "Model", "model.html"]' in files["report.html"]
    calc = json.loads(files["calculation.json"])["values"]
    model = next(m for m in view.modules if m.module_id == "CP-MODEL")
    for figure in figures[:3]:
        for mark in figure.chart.marks:
            assert mark.value is None or mark.ref_id
    assert model.artifact_sha256 == hashlib.sha256(files["calculation.json"]).hexdigest()
    assert calc["FY2024"]["issuer_ordinary_ebitda"]["amount"] == "3813"
    assert json.loads(files["delivery.json"])["cp_model_published"] is True
    assert View.model_validate_json(files["model-view.json"]).modules == (model,)
    from deploy_workflow.handoff_delivery import HandoffInput
    from deploy_workflow.owners.cpos import _comparison_bundle

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name, raw in files.items():
        (bundle / name).write_bytes(raw)
    _comparison_bundle(
        bundle,
        HandoffInput(
            path="delivery.json", sha256=hashlib.sha256(files["delivery.json"]).hexdigest()
        ),
    )


def numeric_raw(raw_value="0", label="FY2025"):
    head = "# CP-4 TDG\n## Request\nTDG.\n## Sources\nSynthetic.\n## Findings\n### Wall\n"
    table = f"| Period | Principal USDm |\n|---|---|\n| {label} | {raw_value} |\n"
    tail = "## Calculations\nNone.\n## Gaps\nTest.\n## Next module\nDelivery.\n"
    return (head + table + tail).encode()


def numeric(raw_value="0", label="FY2025", raw=None, **changes):
    module, _, _ = literal_module("CP-4", raw or numeric_raw(raw_value, label))
    route = MarkdownRoute.model_validate_json(
        json.dumps(
            {
                "module_id": "CP-4",
                "heading": "Wall",
                "kind": "chart",
                "block_id": "maturity-wall",
                "figure_id": "S.4",
                "value_columns": ["Principal USDm"],
                "orientation": "period-rows",
                "chart_unit": "US$m",
                **changes,
            }
        )
    )
    return _numeric_observations(module, module.tables[0], route)


@pytest.mark.parametrize(
    "value,expected",
    [("0", "0"), ("(1,234.50)", "-1234.50"), ("—", None), ("Not calculable: missing inputs", None)],
)
def test_explicit_chart_cells_preserve_signed_exact_values_and_gaps(value, expected):
    module, _, points = numeric(value)
    fact = next(f for f in module.facts if f.fact_id == points[0].fact_id)
    assert fact.amount == (None if expected is None else Decimal(expected))
    assert fact.citations[0].quote.endswith("| " + value + " |")


@pytest.mark.parametrize(
    ("value", "unit", "shown"),
    [
        # Hand-derived: places = digits after the point in the source token; a "%" token is a
        # fraction, so two of its places are the percent scaling (0.0725 -> 7.25%).
        ("0.004", "US$m", "0.004"),
        ("150", "US$m", "150"),
        ("1,234.5", "US$m", "1,234.5"),
        ("(0.30)", "US$m", "(0.30)"),
        ("0.125", "x", "0.125x"),
        ("12.3456", "x", "12.3456x"),
        ("0.0725", "%", "7.25%"),
        ("0.004", "%", "0.4%"),
        ("0.12", "%", "12%"),
    ],
)
def test_chart_cell_is_shown_to_the_places_the_source_token_was_written(value, unit, shown):
    block, figure, column = {
        "US$m": ("maturity-wall", "S.4", "Principal USDm"),
        "x": ("metric-strip", "S.1", "Principal USDm"),
        "%": ("yield-against-maturity", "RV.1", "Principal_fraction"),
    }[unit]
    raw = numeric_raw(value).replace(b"Principal USDm", column.encode())
    module, _, points = numeric(
        value, chart_unit=unit, block_id=block, figure_id=figure, value_columns=[column], raw=raw
    )
    fact = next(f for f in module.facts if f.fact_id == points[0].fact_id)
    unit_class = {"US$m": "amount", "x": "multiple", "%": "percent"}[unit]
    assert format_value(fact.amount, unit_class, "known", decimals=fact.decimals) == shown


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e99", "12,34", "1%", "1x", "0 USD"])
def test_untyped_or_ambiguous_chart_numeric_spellings_refuse(value):
    with pytest.raises(ValueError, match="markdown_chart"):
        numeric(value)


def test_wrong_quantity_or_missing_and_duplicate_selectors_refuse():
    for changes in (
        {"label": "USD/share"},
        {"value_columns": ["Unknown"]},
        {"value_columns": ["Principal USDm", "Principal USDm"]},
        {"row_labels": ["Absent"]},
    ):
        with pytest.raises(ValueError, match="markdown_chart"):
            numeric(**changes)


def test_model_extra_handoff_cannot_override_actual_annual_source(tmp_path):
    manifest = job(tmp_path)
    data = json.loads(manifest.read_text())
    data["model"]["extra_handoffs"]["annual"] = data["handoffs"]["CP-4"]
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="model_inputs"):
        delivery_files(manifest)


@pytest.mark.parametrize(
    "change",
    [{"currency": "EUR"}, {"unit": "SHARES"}, {"scale": Decimal(1)}, {"amount": Decimal("NaN")}],
)
def test_typed_chart_must_preserve_currency_quantity_scale_and_finiteness(tmp_path, change):
    from deploy_vii.contracts import Fact, ModuleView, ReportTable, TableColumn, TableRow

    fact = Fact(
        fact_id="f",
        table_id="t",
        row_id="r",
        field="c",
        label="Cash",
        amount=Decimal(5),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period="FY2024",
    )
    fact = fact.model_copy(update=change)
    table = ReportTable(
        table_id="t",
        title="Cash",
        columns=(TableColumn(field="c", label="FY2024"),),
        rows=(TableRow(row_id="r", label="Cash", fact_ids=("f",)),),
    )
    module = ModuleView(
        module_id="CP-MODEL",
        title="Test",
        aliases=(),
        status="candidate",
        artifact_sha256="0" * 64,
        facts=(fact,),
        tables=(table,),
    )
    route = MarkdownRoute(
        module_id="CP-MODEL",
        heading="Cash",
        kind="chart",
        block_id="metric-strip",
        figure_id="S.3",
        chart_unit="US$m",
        value_columns=("FY2024",),
    )
    with pytest.raises(ValueError, match="unit/currency differs"):
        _numeric_observations(module, table, route)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "wrong_figure"])
def test_chart_strip_must_have_exactly_its_complete_figure_set(tmp_path, mutation):
    manifest = job(tmp_path)
    data = json.loads(manifest.read_bytes())
    if mutation == "missing":
        data["layout"]["routes"].pop()
    elif mutation == "duplicate":
        data["layout"]["routes"].append(data["layout"]["routes"][-1])
    else:
        data["layout"]["routes"][-1]["block_id"] = "financials-credit-metrics"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="markdown_chart"):
        delivery_files(manifest)


def test_current_live_pair_yields_use_exact_rounded_fractions_without_repricing():
    raw = (ROOT / "runs/cpos-sol-remaining-20261105/arcc-selection/CP-3.md").read_bytes()
    module, _, metadata = literal_module("CP-3", raw)
    table = next(
        t for t in module.tables if metadata[t.table_id] == ("Pair pricing controls", "table")
    )
    route = MarkdownRoute(
        module_id="CP-3",
        heading="Pair pricing controls",
        kind="chart",
        block_id="yield-against-maturity",
        figure_id="RV.1",
        value_columns=("Maturity_yield_fraction",),
        orientation="period-rows",
        chart_unit="%",
    )
    updated, _, points = _numeric_observations(module, table, route)
    facts = {f.fact_id: f for f in updated.facts}
    assert [facts[p.fact_id].amount for p in points] == [
        Decimal("0.056003"),
        Decimal("0.061317"),
        Decimal("0.056224"),
        Decimal("0.063169"),
    ]
    assert all(
        facts[p.fact_id].unit == "PERCENT"
        and facts[p.fact_id].currency is None
        and facts[p.fact_id].scale == 1
        for p in points
    )
    assert updated.facts[: len(module.facts)] == module.facts
    assert all(facts[p.fact_id].citations for p in points)
    with pytest.raises(ValueError, match="markdown_chart"):
        MarkdownRoute(
            module_id="CP-3",
            heading="Ambiguous",
            kind="chart",
            block_id="yield-against-maturity",
            figure_id="RV.1",
            value_columns=("Yield %",),
            orientation="period-rows",
            chart_unit="%",
        )


@pytest.mark.parametrize("before", [True, False])
def test_coverage_lists_the_chart_block_whichever_route_comes_first(tmp_path, before):
    manifest = job(tmp_path)
    data = json.loads(manifest.read_text())
    routes = data["layout"]["routes"]
    index = next(i for i, r in enumerate(routes) if r["module_id"] == "CP-4")
    extra = {
        "module_id": "CP-4",
        "heading": "Maturity",
        "kind": "table",
        "block_id": "company-profile",
    }
    routes.insert(index if before else index + 1, extra)
    manifest.write_text(json.dumps(data))
    entries = json.loads(delivery_files(manifest)["coverage.json"])["modules"]["CP-4"]
    table = next(e for e in entries if e["kind"] == "table")
    assert sorted(table["blocks"]) == ["company-profile", "model-chart-strip"]
