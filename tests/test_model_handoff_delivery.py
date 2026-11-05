"""Actual handoff publication and synthetic fault regressions, never provider proof."""

import json
import re
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import HandoffInput, ModelRow, verify_delivery
from deploy_workflow.model_handoff_delivery import build_model
from deploy_workflow.owners.cpos import HandoffPlan, run_handoffs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-tdg-model-001"


def source_inputs():
    request = HandoffPlan.model_validate_json((CASE / "workflow.json").read_bytes())
    specs = {
        "annual": request.retained_handoffs["CP-1"],
        "current_synthesis": request.retained_handoffs["CP-2"],
        **request.model.extra_handoffs,
    }
    specs["forecast_exact"] = request.model.forecast_exact
    raw = {k: (CASE / spec.path).read_bytes() for k, spec in specs.items()}
    return request, specs, raw


@pytest.fixture(scope="module")
def published():
    request, specs, raw = source_inputs()
    return build_model(request.run, specs, raw, request.model)


def annual_only(before: bytes | None = None, after: bytes | None = None):
    request, specs, raw = source_inputs()
    specs = {k: v for k, v in specs.items() if k in {"annual", "current_synthesis"}}
    raw = {k: v for k, v in raw.items() if k in specs}
    if before is not None:
        # The primary statement precedes repeated dashboard/header text in this frozen handoff.
        assert before in raw["annual"]
        raw["annual"] = raw["annual"].replace(before, after, 1)
        specs["annual"] = HandoffInput(path="changed.md", sha256=sha256(raw["annual"]).hexdigest())
    layout = request.model.model_copy(update={"extra_handoffs": {}, "forecast_exact": None})
    return request.run, specs, raw, layout


def test_81_values_against_independent_source_fraction_checks(published) -> None:
    calculation = json.loads(published.files["calculation.json"])
    oracle = json.loads((ROOT / "runs/tdg-model-001/verification.json").read_bytes())[
        "calculation_checks"
    ]
    assert len(oracle) == 81
    for check in oracle:
        value = calculation["values"][check["period"]][check["key"]]
        expected = check["expected_fraction"]
        if expected is None:
            assert value["amount"] is None and value["reason"]
        else:
            exact = Fraction(expected)
            with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
                rounded = Decimal(exact.numerator) / Decimal(exact.denominator)
            assert Decimal(value["amount"]) == rounded
        ratio = check["key"] in {
            "gross_carrying_multiple",
            "net_carrying_multiple",
            "issuer_earnings_cash_interest",
        }
        assert value["quantity_family"] == ("dimensionless" if ratio else "monetary")
        assert value["unit"] == ("MULTIPLE" if ratio else "MILLIONS")
        assert value["currency"] == (None if ratio else "USD")
        assert value["scale"] == ("1" if ratio else "1000000")
        year = int(check["period"][-4:])
        if check["key"] in {"cash", "carrying_debt", "net_carrying_debt"}:
            assert value["start_date"] is None
            assert value["end_date"] == f"{year}-09-30"
        else:
            assert (value["start_date"], value["end_date"]) == (
                f"{year - 1}-10-01",
                f"{year}-09-30",
            )
    assert calculation["values"]["FY2024"]["operating_ebitda"]["amount"] == "3843"
    assert calculation["values"]["FY2024"]["issuer_ordinary_ebitda"]["amount"] == "3813"
    assert calculation["values"]["FY2024"]["issuer_as_defined"]["amount"] == "4173"


def test_raw_cells_quotes_blanks_and_attached_sources_are_exact(published) -> None:
    _, specs, raw = source_inputs()
    facts = {f.fact_id: f for f in published.module.facts}
    cells = 0
    blank = 0
    for source in published.sources:
        assert source.sha256 == sha256(raw[source.source_id]).hexdigest()
        assert published.files[source.source_id + ".md"] == raw[source.source_id]
    for table in published.module.tables:
        if not table.table_id.startswith("raw-"):
            continue
        for row in table.rows:
            values = [facts[fid] for fid in row.fact_ids]
            cite = values[0].citations[0]
            original = raw[cite.source_id].decode().splitlines()[int(cite.locator.split()[-1]) - 1]
            assert cite.quote == original and cite.source_sha256 == specs[cite.source_id].sha256
            fields = [
                c.strip().replace("\x00", "|")
                for c in original[1:-1].replace(r"\|", "\x00").split("|")
            ]
            clean = lambda s: s.replace("**", "").replace("`", "")
            assert row.label == clean(fields[0])
            for field, fact in zip(fields[1:], values, strict=True):
                cells += 1
                if field:
                    assert fact.status == "known" and fact.text == clean(field)
                else:
                    blank += 1
                    assert fact.status == "missing" and fact.text is None and fact.amount is None
    assert cells > 1779 and blank == 46
    assert published.files["forecast_exact.json"] == raw["forecast_exact"]
    for name in published.files:
        assert not name.endswith((".xlsx", ".xls", ".xlsm"))


def test_charts_have_18_exact_table_twins_and_missing_observation(published) -> None:
    report = json.loads(published.files["model-report-view.json"])
    values = json.loads(published.files["calculation.json"])["values"]
    series_keys = {
        "Operating EBIT plus D&A": "operating_ebitda",
        "Issuer ordinary EBITDA": "issuer_ordinary_ebitda",
        "Issuer As Defined": "issuer_as_defined",
        "Reported CFO": "cfo",
        "CFO less gross cash capex": "cfo_less_capex",
        "S&A plus IS amortization": "opex_magnitude",
    }
    assert report["blocks"][1]["kind"] == "dense"
    assert report["blocks"][1]["columns"] == ["FY2022", "FY2023", "FY2024"]
    figures = report["blocks"][0]["figures"]
    assert len(figures) == 3
    marks = 0
    gaps = 0
    for figure in figures:
        chart = figure["chart"]
        for mark, twin in zip(chart["marks"], chart["table_twin"]["rows"], strict=True):
            marks += 1
            assert mark["value"] == values[mark["label"]][series_keys[mark["series"]]]["amount"]
            assert mark["text"] == twin["cells"][0]["text"]
            if mark["value"] is None:
                gaps += 1
                assert mark["series"] == "Issuer ordinary EBITDA" and mark["label"] == "FY2022"
                assert twin["cells"][0]["state"] == "gap"
            else:
                assert twin["cells"][0]["state"] == "known"
    assert (marks, gaps) == (18, 1)


def test_balance_selector_must_match_source_instant() -> None:
    run, specs, raw, layout = annual_only()
    periods = dict(layout.periods)
    periods["FY2024"] = periods["FY2024"].model_copy(update={"balance_column": "Sep 30, 2023"})
    with pytest.raises(ValueError, match="model_balance_period:.*FY2024"):
        build_model(run, specs, raw, layout.model_copy(update={"periods": periods}))


def test_annual_dates_must_match_reported_fiscal_window() -> None:
    run, specs, raw, layout = annual_only()
    periods = dict(layout.periods)
    periods["FY2024"] = periods["FY2024"].model_copy(update={"start_date": date(2024, 1, 1)})
    with pytest.raises(ValueError, match="model_period: source dates differ"):
        build_model(run, specs, raw, layout.model_copy(update={"periods": periods}))


@pytest.mark.parametrize(
    "label",
    [
        "Earnings per share (USD/share)",
        "Weighted-average shares outstanding, basic and diluted (millions shares)",
        "Common shares issued (individual; quantity separated from carrying amount)",
    ],
)
def test_explicit_nonmonetary_source_selector_cannot_be_money(label: str) -> None:
    run, specs, raw, layout = annual_only()
    rows = dict(layout.rows)
    rows["revenue"] = ModelRow(table="income", label=label)
    with pytest.raises(ValueError, match="model_quantity_family"):
        build_model(run, specs, raw, layout.model_copy(update={"rows": rows}))


def test_true_zero_interest_is_retained_while_ratio_is_missing() -> None:
    args = annual_only(
        b"| Cash paid during period for interest, net | 1,158 |",
        b"| Cash paid during period for interest, net | 0 |",
    )
    values = json.loads(build_model(*args).files["calculation.json"])["values"]["FY2024"]
    assert values["interest_cash"]["amount"] == "0"
    assert values["issuer_earnings_cash_interest"]["amount"] is None
    assert values["issuer_earnings_cash_interest"]["reason"] == "ZERO_OR_NEGATIVE_DENOMINATOR"


def test_missing_operand_is_not_backfilled_from_reported_ebit() -> None:
    args = annual_only(
        b"| SELLING AND ADMINISTRATIVE EXPENSES | 980 |",
        b"| SELLING AND ADMINISTRATIVE EXPENSES |  |",
    )
    values = json.loads(build_model(*args).files["calculation.json"])["values"]["FY2024"]
    assert values["selling_admin"]["amount"] is None
    assert values["ebit"]["amount"] is None and values["operating_ebitda"]["amount"] is None
    assert values["ebit_reported"]["amount"] == "3531"


def test_source_projected_window_cannot_be_published_as_historical() -> None:
    args = annual_only(b"| FY2024 | Historical duration |", b"| FY2024 | Projected |")
    with pytest.raises(ValueError, match="model_period: FY2024 is not a historical duration"):
        build_model(*args)


def test_ambient_decimal_precision_cannot_change_model() -> None:
    args = annual_only()
    expected = json.loads(build_model(*args).files["calculation.json"])["values"]
    with localcontext(Context(prec=6, rounding=ROUND_DOWN)):
        actual = json.loads(build_model(*args).files["calculation.json"])["values"]
    assert actual == expected


def test_all_missing_observations_cannot_complete_a_populated_model() -> None:
    run, specs, raw, layout = annual_only()
    raw["annual"] = re.sub(
        rb"(?<=\|)\s*(?:-?[0-9][0-9,.]*|\([0-9,.]+\))\s*(?=\|)", b" \xe2\x80\x94 ", raw["annual"]
    )
    specs["annual"] = HandoffInput(path="all-missing.md", sha256=sha256(raw["annual"]).hexdigest())
    with pytest.raises(ValueError, match="model_empty"):
        build_model(run, specs, raw, layout)


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (
            b"| SELLING AND ADMINISTRATIVE EXPENSES | 980 |",
            b"| SELLING AND ADMINISTRATIVE EXPENSES | 981 |",
            "model_reconciliation",
        ),
        (b"| Capital expenditures | (165) |", b"| Capital expenditures | 165 |", "model_capex"),
        (b"Monetary unit USD millions", b"Monetary unit EUR millions", "model_units"),
        (b"| NET SALES | 7,940 |", b"| NET SALES | NaN |", "model_number"),
        (
            b"| Row as reported | FY2024 | FY2023 | FY2022 |",
            b"| Row as reported | FY2024 | FY2024 | FY2022 |",
            "model_columns",
        ),
    ],
)
def test_invalid_source_mapping_refuses(before: bytes, after: bytes, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_model(*annual_only(before, after))


def test_changed_forecast_base_and_foreign_extra_issuer_refuse() -> None:
    request, specs, raw = source_inputs()
    raw = dict(raw)
    specs = dict(specs)
    exact = json.loads(raw["forecast_exact"])
    exact["consumed"] = {}
    raw["forecast_exact"] = json.dumps(exact).encode()
    specs["forecast_exact"] = HandoffInput(
        path="changed.json", sha256=sha256(raw["forecast_exact"]).hexdigest()
    )
    with pytest.raises(ValueError, match="model_forecast_basis"):
        build_model(request.run, specs, raw, request.model)
    request, specs, raw = source_inputs()
    raw = dict(raw)
    specs = dict(specs)
    raw["quarter"] = (
        raw["quarter"].replace(b"# CP-1 \xe2\x80\x94 TDG", b"# CP-1 \xe2\x80\x94 ARCC", 1)
        + b"\nA peer is TransDigm Group Incorporated.\n"
    )
    specs["quarter"] = HandoffInput(path="foreign.md", sha256=sha256(raw["quarter"]).hexdigest())
    with pytest.raises(ValueError, match="model_issuer: quarter"):
        build_model(request.run, specs, raw, request.model)


@pytest.mark.parametrize("fault", ["bad_consumed_type", "nonfinite"])
def test_malformed_retained_forecast_is_not_published(fault: str) -> None:
    request, specs, raw = source_inputs()
    raw = dict(raw)
    specs = dict(specs)
    exact = json.loads(raw["forecast_exact"])
    if fault == "bad_consumed_type":
        exact["consumed"] = []
    else:
        exact["unusable_number"] = float("nan")
    raw["forecast_exact"] = json.dumps(exact).encode()
    specs["forecast_exact"] = HandoffInput(
        path="changed.json", sha256=sha256(raw["forecast_exact"]).hexdigest()
    )
    with pytest.raises(ValueError):
        build_model(request.run, specs, raw, request.model)


def cp_os_job(tmp_path: Path) -> Path:
    data = json.loads((CASE / "workflow.json").read_bytes())
    for group in (
        data["sources"],
        data["instructions"],
        data["retained_handoffs"],
        data["model"]["extra_handoffs"],
    ):
        for spec in group.values():
            spec["path"] = str((CASE / spec["path"]).resolve())
    spec = data["model"]["forecast_exact"]
    spec["path"] = str((CASE / spec["path"]).resolve())
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(data))
    return path


def test_cp_os_publishes_complete_model_bundle_resumes_and_refuses_tampering(
    tmp_path: Path,
) -> None:
    manifest = cp_os_job(tmp_path)
    data = json.loads(manifest.read_bytes())
    expected = {m: Path(s["path"]).read_bytes() for m, s in data["retained_handoffs"].items()}

    def no_execute(task):
        pytest.fail("Model publication must not rerun analytical modules")

    def check(task, raw):
        assert raw == expected[task.module_id]
        return ()

    directory = tmp_path / "state"
    report = run_handoffs(manifest, directory, execute=no_execute, check=check)
    record = json.loads(next(directory.glob("completed-*.json")).read_bytes())
    assert record["cp_model_published"] is True
    assert (report.parent / "model.html").exists() and (report.parent / "calculation.json").exists()
    assert '["model", "Model", "model.html"]' in report.read_text()
    assert 'href="calculation.json"' in report.read_text()
    assert run_handoffs(manifest, directory, execute=no_execute, check=check) == report
    delivery_manifest = directory / f"delivery-{record['delivery_manifest_sha256']}.json"
    assert verify_delivery(delivery_manifest, report.parent) == report
    (report.parent / "model.html").write_text("Forged Model")
    receipt_path = report.parent / "delivery.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["files"]["model.html"] = sha256(b"Forged Model").hexdigest()
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="delivery_changed: model.html"):
        run_handoffs(manifest, directory, execute=no_execute, check=check)


def test_model_config_change_does_not_repeat_analysis(tmp_path: Path) -> None:
    manifest = cp_os_job(tmp_path)
    data = json.loads(manifest.read_bytes())
    expected = {m: Path(s["path"]).read_bytes() for m, s in data["retained_handoffs"].items()}

    def no_execute(task):
        pytest.fail("Publication revision must not rerun analysis")

    def check(task, raw):
        assert raw == expected[task.module_id]
        return ()

    directory = tmp_path / "state"
    before = run_handoffs(manifest, directory, execute=no_execute, check=check)
    old = before.read_bytes()
    data["model"]["extra_handoffs"].pop("forecast")
    data["model"]["forecast_exact"] = None
    manifest.write_text(json.dumps(data))
    after = run_handoffs(manifest, directory, execute=no_execute, check=check)
    assert before != after and before.read_bytes() == old
    assert not (after.parent / "forecast_exact.json").exists()
    assert len(list(directory.glob("completed-*.json"))) == 2


def test_incomplete_model_write_never_completes_and_resume_keeps_analysis(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = cp_os_job(tmp_path)
    data = json.loads(manifest.read_bytes())
    expected = {m: Path(s["path"]).read_bytes() for m, s in data["retained_handoffs"].items()}

    def no_execute(task):
        pytest.fail("Publication recovery must not rerun analysis")

    def check(task, raw):
        assert raw == expected[task.module_id]
        return ()

    original = Path.write_bytes

    def interrupted(path, content):
        if path.name == "model.html":
            raise OSError("Model write interrupted")
        return original(path, content)

    directory = tmp_path / "state"
    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", interrupted)
        with pytest.raises(OSError, match="Model write interrupted"):
            run_handoffs(manifest, directory, execute=no_execute, check=check)
    assert not list(directory.glob("completed-*.json")) and not (directory / "deliveries").exists()
    assert run_handoffs(manifest, directory, execute=no_execute, check=check).exists()
