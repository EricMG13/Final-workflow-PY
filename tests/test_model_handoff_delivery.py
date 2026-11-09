"""Actual handoff publication and synthetic fault regressions, never provider proof."""

import json
import re
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import (
    DeliveryRequest,
    DerivedRows,
    HandoffInput,
    ModelRow,
    verify_delivery,
)
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


DELIVERY_REQUEST = (
    "runs/cpos-tdg-model-001/execution/"
    "delivery-07ede06e6c4828bde0fb39cd68f14e6f3c154a0837dc28734ac7074bf2b080f5.json"
)


@pytest.mark.parametrize(
    ("path", "contract"),
    [
        (DELIVERY_REQUEST, DeliveryRequest),
        ("runs/cpos-tdg-model-001/workflow.json", HandoffPlan),
    ],
)
def test_a_manifest_without_derived_rows_keeps_its_key_set(path, contract) -> None:
    raw = (ROOT / path).read_text(encoding="utf-8")
    written = json.loads(contract.model_validate_json(raw).model_dump_json())["model"]
    held = json.loads(raw)["model"]
    assert set(written) == set(held)
    assert "derived" not in written and "derived" not in held


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


def test_issuer_name_inside_another_word_does_not_establish_the_model_issuer() -> None:
    # "Digm" is the middle of "TransDigm": a name embedded in a longer word is not a match.
    run, specs, raw, layout = annual_only()
    with pytest.raises(ValueError, match="model_issuer: annual"):
        build_model(run.model_copy(update={"issuer_name": "Digm"}), specs, raw, layout)


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


def model_cells(publication) -> dict[tuple[str, str], str]:
    """(row label, column) -> displayed text across the published HTML Model rows."""
    report = json.loads(publication.files["model-report-view.json"])
    return {
        (row["row_id"], column): cell["text"]
        for block in report["blocks"]
        for row in block["rows"]
        for column, cell in zip(block["columns"], row["cells"], strict=True)
    }


def test_fractional_source_amounts_are_displayed_to_the_places_they_were_written() -> None:
    # Hand-derived from the replaced CP-1 row (columns FY2024, FY2023, FY2022): 0.4, (0.3) and
    # 220.5 are written to one place, so they show as 0.4, (0.3) and 220.5, never 0, 0 and 221.
    # Cash paid for taxes feeds no other row, so only its own cells change.
    row = b"| Cash paid during period for income taxes, net of refunds | 539 | 260 | 220 |"
    new = b"| Cash paid during period for income taxes, net of refunds | 0.4 | (0.3) | 220.5 |"
    publication = build_model(*annual_only(row, new))
    cells = model_cells(publication)
    assert [cells["tax_cash", p] for p in ("FY2024", "FY2023", "FY2022")] == [
        "0.4",
        "(0.3)",
        "220.5",
    ]
    # Whole-number sources keep zero places, and a calculated cell keeps its inputs' places.
    assert cells["revenue", "FY2024"] == "7,940"
    assert cells["cfo_less_capex", "FY2024"] == "1,880"
    values = json.loads(publication.files["calculation.json"])["values"]
    assert [values[p]["tax_cash"]["amount"] for p in ("FY2024", "FY2023", "FY2022")] == [
        "0.4",
        "-0.3",
        "220.5",
    ]


def test_a_small_nonzero_ratio_is_not_displayed_as_zero() -> None:
    # Hand-derived: issuer As Defined EBITDA 4173 over cash interest 1,000,000 is 0.004173, which
    # two places would show as 0.00x. The ratio gets the fewest places (3) that show it as 0.004x.
    row = b"| Cash paid during period for interest, net | 1,158 |"
    new = b"| Cash paid during period for interest, net | 1,000,000 |"
    cells = model_cells(build_model(*annual_only(row, new)))
    assert cells["issuer_earnings_cash_interest", "FY2024"] == "0.004x"
    # Ratios that are not near zero keep two places.
    assert cells["gross_carrying_multiple", "FY2024"].count(".") == 1
    assert len(cells["gross_carrying_multiple", "FY2024"].split(".")[1].rstrip("x")) == 2


@pytest.mark.parametrize(
    ("value", "places"),
    [
        # Hand-derived: two places unless half a unit in the last place exceeds |value|.
        (None, 2),
        (Decimal(0), 2),
        (Decimal("4.17"), 2),
        (Decimal("0.005"), 2),  # 0.01x at two places (half-up): not zero
        (Decimal("0.0049"), 3),  # 0.00x at two places, 0.005x at three
        (Decimal("-0.004"), 3),
        (Decimal("0.00000049"), 6),  # the contract's six-place cap
    ],
)
def test_ratio_places_widen_only_to_keep_a_nonzero_ratio_from_reading_zero(value, places):
    from deploy_workflow.model_handoff_delivery import _ratio_decimals

    assert _ratio_decimals(value) == places


REGISTER = "### T4.18 — Debt/facility register"


def derived_layout(before: bytes | None = None, after: bytes | None = None):
    run, specs, raw, layout = annual_only(before, after)
    layout = layout.model_copy(update={"derived": DerivedRows(debt_register=REGISTER)})
    return run, specs, raw, layout


def derived_values(*args):
    published = build_model(*derived_layout(*args))
    return published, json.loads(published.files["calculation.json"])["values"]


def rounded(exact: Fraction) -> Decimal:
    with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
        return Decimal(exact.numerator) / Decimal(exact.denominator)


DERIVED_KEYS = (
    "revenue_growth",
    "gross_margin",
    "adj_ebitda_margin",
    "adj_ebitda_growth",
    "senior_secured_debt",
    "senior_secured_multiple",
)


def test_derived_rows_are_absent_without_the_request() -> None:
    published = build_model(*annual_only())
    values = json.loads(published.files["calculation.json"])["values"]
    assert not set(DERIVED_KEYS) & set(values["FY2024"])
    view = json.loads(published.files["model-view.json"])
    assert "derived" not in [t["table_id"] for t in view["modules"][0]["tables"]]


def test_derived_rows_follow_the_record_rules() -> None:
    _, values = derived_values()
    growth = {
        "FY2024": Fraction(271, 1317),
        "FY2023": Fraction(1156, 5429),
    }
    for period, exact in growth.items():
        assert Decimal(values[period]["revenue_growth"]["amount"]) == rounded(exact)
    assert values["FY2022"]["revenue_growth"]["amount"] is None
    assert values["FY2022"]["revenue_growth"]["reason"] == "PRIOR_PERIOD_MISSING"
    assert values["FY2022"]["adj_ebitda_growth"]["reason"] == "PRIOR_PERIOD_MISSING"
    fy24 = values["FY2024"]
    for key, exact in (
        ("gross_margin", Fraction(1168, 1985)),
        ("adj_ebitda_margin", Fraction(4173, 7940)),
        ("adj_ebitda_growth", Fraction(778, 3395)),
        ("senior_secured_multiple", Fraction(1540, 321)),
    ):
        assert Decimal(fy24[key]["amount"]) == rounded(exact)
    debt = fy24["senior_secured_debt"]
    assert debt["amount"] == "20020" and debt["unit"] == "MILLIONS"
    assert [s["locator"] for s in debt["sources"]] == [
        "line 367",
        "line 368",
        "line 375",
        "line 377",
        "line 379",
        "line 380",
        "line 381",
        "line 382",
    ]
    assert [s["cell_text"] for s in debt["sources"]] == [
        "carrying 486",
        "carrying 8,642",
        "carrying 2,077",
        "carrying 2,727",
        "carrying 1,438",
        "carrying 984",
        "carrying 2,180",
        "carrying 1,486",
    ]
    assert fy24["senior_secured_multiple"]["unit"] == "MULTIPLE"
    other = values["FY2023"]["senior_secured_multiple"]
    assert other["amount"] is None and other["reason"] == "REGISTER_DATE_DIFFERS"
    assert "2024-09-30" in other["note"]
    for key in ("revenue_growth", "gross_margin", "adj_ebitda_margin", "adj_ebitda_growth"):
        entry = fy24[key]
        assert entry["unit"] == "FRACTION" and entry["quantity_family"] == "dimensionless"
        assert entry["currency"] is None and entry["scale"] == "1"


def test_an_unclassified_register_row_gives_no_secured_total() -> None:
    _, values = derived_values(
        b"| Revolving credit facility | Commitment 910;",
        b"| Revolving credit facility | carrying 910;",
    )
    debt = values["FY2024"]["senior_secured_debt"]
    assert debt["amount"] is None and debt["reason"] == "UNCLASSIFIED_ROW"
    assert debt["note"] == "Revolving credit facility"
    multiple = values["FY2024"]["senior_secured_multiple"]
    assert multiple["amount"] is None and multiple["reason"] == "UNCLASSIFIED_ROW"


def test_a_repeated_label_beats_an_unclassified_row_whatever_the_row_order() -> None:
    # The store resolves after its loop: repeated label > unclassified row > incomplete row.
    # Here the unclassified revolver (carrying 910) comes first and the repeat later.
    run, specs, raw, layout = derived_layout(
        b"| Revolving credit facility | Commitment 910;",
        b"| Revolving credit facility | carrying 910;",
    )
    old = b"| 4.875% senior subordinated notes due 2029 | Principal 750; carrying 746 |"
    assert old in raw["annual"]
    raw["annual"] = raw["annual"].replace(
        old, b"| Term loans aggregate | Principal 750; carrying 746 |", 1
    )
    specs["annual"] = HandoffInput(path="changed.md", sha256=sha256(raw["annual"]).hexdigest())
    published = build_model(run, specs, raw, layout)
    debt = json.loads(published.files["calculation.json"])["values"]["FY2024"][
        "senior_secured_debt"
    ]
    assert debt["amount"] is None and debt["reason"] == "UNCLASSIFIED_ROW"
    assert debt["note"] == "repeated row label: Term loans aggregate"


def test_the_model_page_lists_the_derived_table() -> None:
    published, _ = derived_values()
    view = json.loads(published.files["model-view.json"])
    tables = {t["table_id"]: t for t in view["modules"][0]["tables"]}
    assert [r["row_id"] for r in tables["derived"]["rows"]] == list(DERIVED_KEYS)
    page = published.files["model.html"].decode()
    assert "Senior secured leverage (secured carrying debt / Adj EBITDA As Defined)" in page
    assert "FRACTION" not in page
    growth = next(r for r in tables["derived"]["rows"] if r["row_id"] == "revenue_growth")
    facts = {f["fact_id"]: f for f in view["modules"][0]["facts"]}
    assert facts[growth["fact_ids"][0]]["unit"] == "decimal_fraction"
    assert "20.58%" in page


def test_a_repeated_register_label_reads_on_the_page_as_the_store_says() -> None:
    published, values = derived_values(
        b"| Tranche I term loans | Principal 1,871 |",
        b"| Term loans aggregate | carrying 1,871 |",
    )
    assert values["FY2024"]["senior_secured_debt"]["reason"] == "UNCLASSIFIED_ROW"
    facts = {
        f["fact_id"]: f
        for f in json.loads(published.files["model-view.json"])["modules"][0]["facts"]
    }
    for key in ("senior_secured_debt", "senior_secured_multiple"):
        assert facts[f"derived.{key}.FY2024"]["limitation"] == (
            "the debt register repeats a row label: Term loans aggregate"
        )


def test_the_register_is_read_as_the_store_reads_it() -> None:
    # The store's CARRYING is case-sensitive: "Carrying 910" is no carrying value, so the
    # revolver is not an unclassified row; 20020 is the hand-summed T4.18 total.
    _, values = derived_values(
        b"| Revolving credit facility | Commitment 910;",
        b"| Revolving credit facility | Carrying 910;",
    )
    assert values["FY2024"]["senior_secured_debt"]["amount"] == "20020"
    # A repeated label whose later row has no carrying value is ignored.
    _, values = derived_values(
        b"| Tranche I term loans | Principal 1,871 |",
        b"| Term loans aggregate | Principal 1,871 |",
    )
    assert values["FY2024"]["senior_secured_debt"]["amount"] == "20020"
    # A register date the reader cannot parse is not "recorded at another date".
    _, values = derived_values(
        b"| Sep 30, 2024 amount / status |", b"| September 30, 2024 amount / status |"
    )
    assert values["FY2024"]["senior_secured_debt"]["reason"] == "NOT_SOURCED"


def test_growth_uses_the_previous_fiscal_year_if_both_are_full_years() -> None:
    from deploy_vii.model.frame import Cell
    from deploy_workflow.handoff_delivery import ModelDelivery, ModelPeriod
    from deploy_workflow.model_handoff_delivery import _AnnualReader, _derived_cells

    def growth(periods, revenue):
        layout = ModelDelivery(
            periods={
                k: ModelPeriod(start_date=s, end_date=e, balance_column=None)
                for k, (s, e) in periods.items()
            },
            anchors={},
            rows={},
        )
        raw = b"# A\n"
        spec = HandoffInput(path="a.md", sha256=sha256(raw).hexdigest())
        cells = {
            p: {
                "revenue": Cell(Decimal(v), basis="REPORTED"),
                "gross_profit": Cell(Decimal(1), basis="REPORTED"),
                "issuer_as_defined": Cell(Decimal(1), basis="REPORTED"),
            }
            for p, v in revenue.items()
        }
        _derived_cells(_AnnualReader(raw, spec, layout), cells, DerivedRows())
        return cells["FY2024"]["revenue_growth"]

    weeks52 = growth(
        {
            "FY2023": (date(2022, 10, 2), date(2023, 9, 30)),
            "FY2024": (date(2023, 10, 1), date(2024, 9, 28)),
        },
        {"FY2023": "6585", "FY2024": "7940"},
    )
    assert weeks52.value is not None and weeks52.reason is None
    short = growth(
        {
            "FY2023": (date(2023, 4, 1), date(2023, 9, 30)),
            "FY2024": (date(2023, 10, 1), date(2024, 9, 30)),
        },
        {"FY2023": "3000", "FY2024": "7940"},
    )
    assert short.value is None and short.reason == "PRIOR_PERIOD_MISSING"
    assert short.note == "the prior period is not a full year"


def test_the_page_names_the_unclassified_row_and_the_ambient_context_is_ignored() -> None:
    published, _ = derived_values(
        b"| Revolving credit facility | Commitment 910;",
        b"| Revolving credit facility | carrying 910;",
    )
    facts = {
        f["fact_id"]: f
        for f in json.loads(published.files["model-view.json"])["modules"][0]["facts"]
    }
    for key in ("senior_secured_debt", "senior_secured_multiple"):
        assert facts[f"derived.{key}.FY2024"]["limitation"] == (
            "the debt register has a row that cannot be classified: Revolving credit facility"
        )
    args = derived_layout(b"| NET SALES | 7,940 |", b"| NET SALES | 6,617.91 |")
    expected = build_model(*args).files
    with localcontext(Context(prec=3, rounding="ROUND_CEILING")):
        assert build_model(*args).files == expected


BRIDGE = "### Issuer segment EBITDA As Defined bridge"
QUARTER_REGISTER = "### Debt — December 28, 2024"
WINDOW = "2024-10-01–2024-12-28"
ADVANCES = b"| 15 | Government refundable advances | 16 | \xe2\x80\x94 | \xe2\x80\x94 | 16 |\n"
LEASES = b"| 16 | Finance lease obligations | 260 | \xe2\x80\x94 | \xe2\x80\x94 | 260 |\n"


def quarter_build(register: bool = False, drop: tuple[bytes, ...] = ()):
    """The CASE inputs asking for quarter rows; `drop` removes lines from a quarter copy."""
    request, specs, raw = source_inputs()
    if drop:
        for line in drop:
            assert line in raw["quarter"]
            raw["quarter"] = raw["quarter"].replace(line, b"", 1)
        specs["quarter"] = HandoffInput(
            path="changed.md", sha256=sha256(raw["quarter"]).hexdigest()
        )
    rows = DerivedRows(
        quarter_bridge=BRIDGE, quarter_debt_register=QUARTER_REGISTER if register else None
    )
    layout = request.model.model_copy(update={"derived": rows})
    published = build_model(request.run, specs, raw, layout)
    return json.loads(published.files["calculation.json"])["quarters"]


def test_ltm_adj_ebitda_is_fy_plus_ytd_less_prior_ytd() -> None:
    quarters = quarter_build()
    assert list(quarters) == [WINDOW]
    entry = quarters[WINDOW]["ltm_adj_ebitda"]
    assert entry["amount"] == "4322"  # 4,173 + 1,061 - 912
    assert entry["unit"] == "MILLIONS" and entry["currency"] == "USD"
    assert (entry["period"], entry["start_date"], entry["end_date"]) == (
        WINDOW,
        "2023-12-31",  # the day after the prior-year window ends: the twelve months start here
        "2024-12-28",
    )
    assert entry["formula"] == (
        "fiscal-year Adj EBITDA As Defined + year-to-date window - prior-year window"
    )
    assert [(s["source_id"], s["locator"], s["cell_text"]) for s in entry["sources"]] == [
        ("annual", "line 350", "4,173"),
        ("quarter", "line 351", "1,061"),
        ("quarter", "line 351", "912"),
    ]
    assert "senior_secured_debt" not in quarters[WINDOW]


def test_the_tdg_quarter_register_cannot_be_classified() -> None:
    entries = quarter_build(register=True)[WINDOW]
    for key in ("senior_secured_debt", "senior_secured_multiple"):
        assert entries[key]["amount"] is None and entries[key]["reason"] == "UNCLASSIFIED_ROW"
    assert entries["senior_secured_debt"]["note"] == "Government refundable advances"


def test_a_classifiable_quarter_register_gives_quarter_end_leverage() -> None:
    entries = quarter_build(register=True, drop=(ADVANCES, LEASES))[WINDOW]
    # 649 + 8,645 + 2,079 + 2,728 + 1,438 + 986 + 2,181 + 1,486
    assert entries["senior_secured_debt"]["amount"] == "20192"
    assert entries["senior_secured_debt"]["start_date"] is None
    assert entries["senior_secured_debt"]["end_date"] == "2024-12-28"
    assert Decimal(entries["senior_secured_multiple"]["amount"]) == rounded(Fraction(20192, 4322))
    assert entries["senior_secured_multiple"]["unit"] == "MULTIPLE"


def test_a_repeated_quarter_register_label_gives_no_total() -> None:
    request, specs, raw = source_inputs()
    twin = b"| 4 | Term loans | 8,702 | (24) | (33) | 8,645 |\n"
    assert twin in raw["quarter"]
    raw["quarter"] = raw["quarter"].replace(twin, twin * 2, 1)
    raw["quarter"] = raw["quarter"].replace(ADVANCES, b"").replace(LEASES, b"")
    specs["quarter"] = HandoffInput(path="changed.md", sha256=sha256(raw["quarter"]).hexdigest())
    rows = DerivedRows(quarter_bridge=BRIDGE, quarter_debt_register=QUARTER_REGISTER)
    layout = request.model.model_copy(update={"derived": rows})
    published = build_model(request.run, specs, raw, layout)
    debt = json.loads(published.files["calculation.json"])["quarters"][WINDOW][
        "senior_secured_debt"
    ]
    assert debt["amount"] is None and debt["reason"] == "UNCLASSIFIED_ROW"
    assert debt["note"] == "repeated row label: Term loans"


def test_quarters_are_absent_without_a_quarter_bridge_request() -> None:
    assert "quarters" not in json.loads(build_model(*annual_only()).files["calculation.json"])
    request, specs, raw = source_inputs()
    published = build_model(request.run, specs, raw, request.model)
    assert "quarters" not in json.loads(published.files["calculation.json"])
    rows = DerivedRows(debt_register=REGISTER)
    layout = request.model.model_copy(update={"derived": rows})
    published = build_model(request.run, specs, raw, layout)
    assert "quarters" not in json.loads(published.files["calculation.json"])


ROW_BRIDGE = b"| 9 | Total Company EBITDA As Defined | 1,061 | 912 |\n"
TERM_ROW = b"| 4 | Term loans | 8,702 | (24) | (33) | 8,645 |\n"
SECURITIZATION_ROW = (
    "| 3 | Short-term borrowings—trade receivable securitization facility | 650 | (1) | — | 649 |\n"
).encode()
NOTES_2033 = (
    "| 14 | 6.00% secured notes due 2033 (“2033 Secured Notes”) | 1,500 | (14) | — | 1,486 |\n"
).encode()
LONG_TERM = b"| 19 | Long-term debt | 24,479 | (130) | (47) | 24,302 |\n"


def edited_quarters(quarter=(), annual=(), register=False, periods=None):
    """The CASE quarter rows after in-memory text edits (old, new) of the retained handoffs."""
    request, specs, raw = source_inputs()
    layout = request.model
    for key, edits in (("quarter", quarter), ("annual", annual)):
        for old, new in edits:
            assert old in raw[key]
            raw[key] = raw[key].replace(old, new, 1)
        if edits:
            specs[key] = HandoffInput(path="changed.md", sha256=sha256(raw[key]).hexdigest())
    if annual:
        for key in ("forecast", "forecast_exact"):
            del specs[key], raw[key]
        layout = layout.model_copy(update={"extra_handoffs": {}, "forecast_exact": None})
    if periods:
        merged = {
            **layout.periods,
            **{k: layout.periods[k].model_copy(update=v) for k, v in periods.items()},
        }
        layout = layout.model_copy(update={"periods": merged})
    rows = DerivedRows(
        quarter_bridge=BRIDGE, quarter_debt_register=QUARTER_REGISTER if register else None
    )
    layout = layout.model_copy(update={"derived": rows})
    published = build_model(request.run, specs, raw, layout)
    return json.loads(published.files["calculation.json"])["quarters"]


def test_a_quarter_register_without_its_required_secured_rows_gives_no_total() -> None:
    for gone in (TERM_ROW, SECURITIZATION_ROW):
        edits = [(ADVANCES, b""), (LEASES, b""), (gone, b"")]
        debt = edited_quarters(quarter=edits, register=True)[WINDOW]["senior_secured_debt"]
        assert debt["amount"] is None and debt["reason"] == "COMPONENT_MISSING"


@pytest.mark.parametrize(
    "label", ["Total secured notes", "TOTAL senior secured notes", "total term loans"]
)
def test_a_total_labelled_register_row_is_a_subtotal(label: str) -> None:
    subtotal = f"| 14a | {label} | 10,950 | (88) | (14) | 10,898 |\n".encode()
    edits = [(ADVANCES, b""), (LEASES, b""), (NOTES_2033, NOTES_2033 + subtotal)]
    debt = edited_quarters(quarter=edits, register=True)[WINDOW]["senior_secured_debt"]
    assert debt["amount"] == "20192"


def test_two_net_columns_in_the_quarter_register_are_refused() -> None:
    edits = [(b"| Costs USD m |", b"| Net costs USD m |")]
    with pytest.raises(ValueError, match="Net"):
        edited_quarters(quarter=edits, register=True)


def test_a_repeated_bridge_row_is_refused() -> None:
    with pytest.raises(ValueError, match="model_row"):
        edited_quarters(quarter=[(ROW_BRIDGE, ROW_BRIDGE + ROW_BRIDGE)])


def test_the_prior_window_must_start_with_the_fiscal_year_and_the_year_be_full() -> None:
    header = "| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |"
    at = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text().index(BRIDGE)
    block = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text()[at:]
    block = block[: block.index(header) + len(header)]
    early = [(block.encode(), block.replace("2023-10-01–", "2023-09-24–").encode())]
    ltm = edited_quarters(quarter=early)[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["reason"] == "WINDOW_MISSING"
    assert "prior-year window" in ltm["note"]
    stub = [
        (
            b"| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 |",
            b"| FY2024 | Historical duration | 2024-01-01 | 2024-09-30 |",
        )
    ]
    ltm = edited_quarters(annual=stub, periods={"FY2024": {"start_date": date(2024, 1, 1)}})[
        WINDOW
    ]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["reason"] == "WINDOW_MISSING"
    assert "full year" in ltm["note"]


@pytest.mark.parametrize(
    ("prior_end", "days"), [("2023-12-21", 373), ("2024-01-05", 358), ("2023-12-23", 371)]
)
def test_the_ltm_must_span_a_year_like_the_kernel(prior_end: str, days: int) -> None:
    """Prior-window end to this window end, hand-counted: 2024-12-28 less each end."""
    header = "| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |"
    text = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text()
    block = text[text.index(BRIDGE) :]
    block = block[: block.index(header) + len(header)]
    edit = [(block.encode(), block.replace("2023-12-30", prior_end).encode())]
    ltm = edited_quarters(quarter=edit)[WINDOW]["ltm_adj_ebitda"]
    if days == 371:  # the kernel's upper bound is inclusive
        assert ltm["amount"] == "4322"
        return
    assert ltm["amount"] is None and ltm["reason"] == "WINDOW_MISSING"
    assert str(days) in ltm["note"] and "364" in ltm["note"]


def bridge_with_column(header: str, value: str) -> list[tuple[bytes, bytes]]:
    """An edit adding a column to the bridge table: `value` on its Total Company row."""
    text = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text()
    start = text.index(BRIDGE)
    table = text[start : text.index("\n\n", text.index("| Source row", start))]
    lines = []
    for line in table.split("\n")[2:]:
        if not line.startswith("|"):
            continue
        cell = "---" if line.startswith("|---") else ""
        if "Total Company EBITDA As Defined" in line:
            cell = value
        if line.startswith("| Source row"):
            cell = header
        lines.append(line + f" {cell} |")
    block = table[table.index("| Source row") :]
    return [(block.encode(), "\n".join(lines).encode())]


def test_one_window_printed_twice_is_refused() -> None:
    edits = bridge_with_column("2024-10-01-2024-12-28", "1,070")
    with pytest.raises(ValueError, match="window"):
        edited_quarters(quarter=edits)


def test_two_matching_prior_windows_give_no_ltm() -> None:
    edits = bridge_with_column("2023-10-02–2023-12-30", "915")
    ltm = edited_quarters(quarter=edits)[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["reason"] == "WINDOW_MISSING"
    assert ltm["note"] == "two prior-year windows match"


def test_a_dash_operand_keeps_its_own_reason() -> None:
    dash = ROW_BRIDGE.replace(b"| 1,061 |", "| — |".encode())
    ltm = edited_quarters(quarter=[(ROW_BRIDGE, dash)])[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["reason"] == "NOT_STATED"
    header = (
        b"| Reported line | FY2024 | FY2023 | FY2022 |\n|---|---:|---:|---:|\n"
        b"| Power & Control EBITDA As Defined |"
    )
    renamed = header.replace(b"FY2024", b"FY 2024")
    ltm = edited_quarters(annual=[(header, renamed)])[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and "FY2024" in ltm["note"]


def test_a_total_row_inside_an_html_comment_is_not_read() -> None:
    row = b"| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 |"
    draft = (
        b"<!-- superseded draft\n| Reported line | FY2024 |\n|---|---:|\n"
        b"| Total Company EBITDA As Defined | 9,999 |\n-->\n\n"
    )
    visible = row.replace(b"As Defined |", b"As Defined (as reported) |", 1)
    title = b"### T4.17 \xe2\x80\x94 Reported EBITDA and add-back bridge"
    edits = [(row, visible), (title, draft + title)]
    ltm = edited_quarters(annual=edits)[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None


# Register hardening: delivery and the store classify the same register rows alike.
LAST_NOTE = (
    b"| 6.00% secured notes due 2033 | Principal 1,500; carrying 1,486 |"
    b" 6.00%; matures January 15, 2033 (PDF 46). |\n"
)
SUBTOTALS = (
    (b"Secured notes subtotal", b"carrying 12,892"),
    (b"Subtotal secured notes", b"carrying 12,892"),
    (b"Secured notes, total", b"carrying 12,892"),
    (b"Term loans, total", b"carrying 8,642"),
    (b"**Total secured notes**", b"carrying 12,892"),
)


def annual_debt(before: bytes, after: bytes) -> dict[str, object]:
    return derived_values(before, after)[1]["FY2024"]["senior_secured_debt"]


def quarter_debt(*edits: tuple[bytes, bytes]) -> dict[str, object]:
    cleaned = [(ADVANCES, b""), (LEASES, b""), *edits]
    return edited_quarters(quarter=cleaned, register=True)[WINDOW]["senior_secured_debt"]


@pytest.mark.parametrize(("label", "carrying"), SUBTOTALS)
def test_a_subtotal_labelled_annual_register_row_is_not_summed(label: bytes, carrying: bytes):
    extra = b"| " + label + b" | " + carrying + b" | Sum of the rows above. |\n"
    # 486 + 8,642 + 2,077 + 2,727 + 1,438 + 984 + 2,180 + 1,486, by hand
    assert annual_debt(LAST_NOTE, LAST_NOTE + extra)["amount"] == "20020"


def test_an_emphasised_annual_register_label_is_read_by_its_words():
    row = b"| Term loans aggregate | Principal 8,702; carrying 8,642"
    bold = b"| **Term loans aggregate** | Principal 8,702; carrying 8,642"
    assert annual_debt(row, bold)["amount"] == "20020"
    assert (
        annual_debt(row, row.replace(b"Term loans aggregate", b"_Term loans aggregate_"))["amount"]
        == "20020"
    )


@pytest.mark.parametrize(
    "label", [b"Secured notes subtotal", b"Subtotal secured notes", b"Secured notes, total"]
)
def test_a_subtotal_labelled_quarter_row_is_not_summed(label: bytes):
    notes = b"| 14a | " + label + b" | 10,950 | (88) | (14) | 10,898 |\n"
    terms = b"| 4a | Term loans, total | 8,702 | (24) | (33) | 8,645 |\n"
    got = quarter_debt((NOTES_2033, NOTES_2033 + notes), (TERM_ROW, TERM_ROW + terms))
    assert got["amount"] == "20192"  # 649 + 8,645 + 2,079 + 2,728 + 1,438 + 986 + 2,181 + 1,486


def test_an_emphasised_quarter_register_label_is_read_by_its_words():
    total = b"| 14a | **Total secured notes** | 10,950 | (88) | (14) | 10,898 |\n"
    assert quarter_debt((NOTES_2033, NOTES_2033 + total))["amount"] == "20192"
    assert (
        quarter_debt((TERM_ROW, TERM_ROW.replace(b"| Term loans |", b"| **Term loans** |")))[
            "amount"
        ]
        == "20192"
    )


QUARTER_ANCHOR = "### Debt — December 28, 2024\n".encode()
ANNUAL_ANCHOR = "### T4.18 — Debt/facility register\n".encode()


def test_a_register_anchor_without_its_own_table_reads_no_other_heading_s_table() -> None:
    interposed = QUARTER_ANCHOR + b"### Another section\n"
    got = quarter_debt((QUARTER_ANCHOR, interposed))
    assert (got["reason"], got["amount"]) == ("NOT_SOURCED", None)
    assert got["note"] == "no table under ### Debt — December 28, 2024"
    got = annual_debt(ANNUAL_ANCHOR, ANNUAL_ANCHOR + b"\n### Another section\n")
    assert (got["reason"], got["amount"]) == ("NOT_SOURCED", None)
    assert got["note"] == "no table under ### T4.18 — Debt/facility register"


ROW_13 = (
    "| 13 | 6.625% secured notes due 2032 (“2032 Secured Notes”) | 2,200 | (19) | — | 2,181 |\n"
)
OLD_13 = "| 13 | 6.625% secured notes due 2032 | 2,200 | (19) | — | 2,180 |"
HIDDEN_TEXT = {
    "opens at row end": ROW_13[:-1] + "<!-- restated\n" + OLD_13 + "\n-->\n",
    "own lines": ROW_13 + "<!-- restated\n" + OLD_13 + "\n-->\n",
    "one line": ROW_13 + "<!-- reviewer note -->\n",
}


@pytest.mark.parametrize("case", HIDDEN_TEXT)
def test_hidden_text_between_register_rows_is_refused_not_truncated(case: str) -> None:
    edits = [(ADVANCES, b""), (LEASES, b""), (ROW_13.encode(), HIDDEN_TEXT[case].encode())]
    with pytest.raises(ValueError, match="Debt .* December 28, 2024"):
        edited_quarters(quarter=edits, register=True)


def test_a_repeated_fiscal_year_ebitda_row_is_refused_whatever_its_spacing() -> None:
    row = b"| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 |"
    spaced = b"|  Total Company EBITDA As Defined | 9,999 | 3,395 | 2,646 |\n" + row
    ltm = edited_quarters(annual=[(row, spaced)])[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["reason"] == "WINDOW_MISSING"


# Fix round 1: one label rule, one hidden-text rule, one heading rule, one row rule.
WRAPPED_TOTALS = (
    b"***Total secured notes***",
    b"**_Total secured notes_**",
    b"__*Total secured notes*__",
    b"Secured notes (total)",
    b"Secured notes total:",
    b"Secured notes, total.",
    b"**Total** secured notes",
    b"**Total secured notes**:",
    b"Secured\xc2\xa0notes\xc2\xa0 total",
)


@pytest.mark.parametrize("label", WRAPPED_TOTALS)
def test_a_subtotal_is_skipped_whatever_its_emphasis_or_punctuation(label: bytes) -> None:
    annual = b"| " + label + b" | carrying 10,892 | Sum of the notes above. |\n"
    assert annual_debt(LAST_NOTE, LAST_NOTE + annual)["amount"] == "20020"
    quarter = b"| 14a | " + label + b" | 10,950 | (88) | (14) | 10,898 |\n"
    assert quarter_debt((NOTES_2033, NOTES_2033 + quarter))["amount"] == "20192"


def test_a_total_inside_a_label_is_unclassified_and_a_totalizer_is_not_a_total() -> None:
    inner = b"| Secured total notes | carrying 50 | x |\n"
    got = annual_debt(LAST_NOTE, LAST_NOTE + inner)
    assert (got["amount"], got["reason"], got["note"]) == (
        None,
        "UNCLASSIFIED_ROW",
        "Secured total notes",
    )
    quarter = b"| 14b | Secured total notes | 50 | \xe2\x80\x94 | \xe2\x80\x94 | 50 |\n"
    assert quarter_debt((NOTES_2033, NOTES_2033 + quarter))["reason"] == "UNCLASSIFIED_ROW"
    totalizer = b"| Totalizer secured notes due 2031 | carrying 50 | x |\n"
    assert annual_debt(LAST_NOTE, LAST_NOTE + totalizer)["amount"] == "20070"  # 20020 + 50
    quarter = b"| 14b | Totalizer secured notes | 50 | \xe2\x80\x94 | \xe2\x80\x94 | 50 |\n"
    assert quarter_debt((NOTES_2033, NOTES_2033 + quarter))["amount"] == "20242"  # 20192 + 50


@pytest.mark.parametrize("space", ["  ", " "])
def test_labels_that_differ_only_in_inner_spacing_are_one_repeated_label(space: str) -> None:
    twin = LAST_NOTE.replace(b"6.00% secured", ("6.00%" + space + "secured").encode())
    got = annual_debt(LAST_NOTE, LAST_NOTE + twin)
    assert (got["amount"], got["reason"]) == (None, "UNCLASSIFIED_ROW")
    row = b"| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 |"
    spaced = row.replace(b"Company EBITDA", ("Company" + space + "EBITDA").encode())
    ltm = edited_quarters(annual=[(row, spaced.replace(b"4,173", b"9,999") + b"\n" + row)])
    assert ltm[WINDOW]["ltm_adj_ebitda"]["amount"] is None


@pytest.mark.parametrize(
    "shape", ["<!-->", "<!--->", "<!-- reviewer note -->", "<!-- reviewer note --> see PDF 46"]
)
def test_every_comment_shape_between_register_rows_is_refused(shape: str) -> None:
    edits = [(ADVANCES, b""), (LEASES, b""), (NOTES_2033, NOTES_2033 + shape.encode() + b"\n")]
    with pytest.raises(ValueError, match="model_table: .* December 28, 2024"):
        edited_quarters(quarter=edits, register=True)
    tail = LAST_NOTE + shape.encode() + b"\n"
    with pytest.raises(ValueError, match=r"model_table: .* T4\.18"):
        derived_values(LAST_NOTE, tail)


def test_a_comment_opened_at_a_row_end_and_closed_after_the_table_is_refused() -> None:
    opened = NOTES_2033[:-1] + b"<!-- restated\n"
    edits = [(NOTES_2033, opened), (LONG_TERM, LONG_TERM + b"-->\n")]
    with pytest.raises(ValueError, match="model_table"):
        edited_quarters(quarter=[(ADVANCES, b""), (LEASES, b""), *edits], register=True)


def test_a_commented_or_fenced_draft_register_above_the_real_one_is_not_read() -> None:
    head = b"| Source row | Label | Gross USD m | Costs USD m | Discount USD m | Net USD m |\n"
    draft = (
        head
        + b"|---|---|---|---|---|---|\n| 3 | Trade receivable securitization | 1 | 1 | 1 | 1 |\n"
    )
    anchor = QUARTER_ANCHOR + b"Original HTML table index 30;"
    for wrap in ((b"<!--\n", b"-->\n\n"), (b"```\n", b"```\n\n")):
        edit = QUARTER_ANCHOR + wrap[0] + draft + wrap[1] + b"Original HTML table index 30;"
        assert quarter_debt((anchor, edit))["amount"] == "20192"


def test_an_indented_heading_ends_the_search_and_hash_prose_does_not() -> None:
    got = quarter_debt((QUARTER_ANCHOR, QUARTER_ANCHOR + b"   ### Another section\n"))
    assert (got["reason"], got["amount"]) == ("NOT_SOURCED", None)
    prose = QUARTER_ANCHOR + b"#1 lien first.\n\n"
    assert quarter_debt((QUARTER_ANCHOR, prose))["amount"] == "20192"
    got = annual_debt(ANNUAL_ANCHOR, ANNUAL_ANCHOR + b"#1 lien first.\n\n")
    assert got["amount"] == "20020"


def test_an_indented_or_space_padded_register_row_is_still_a_row() -> None:
    assert annual_debt(LAST_NOTE, b"   " + LAST_NOTE)["amount"] == "20020"
    assert annual_debt(LAST_NOTE, LAST_NOTE[:-1] + b"   \n")["amount"] == "20020"


def test_the_ltm_start_and_the_missing_table_message_follow_the_accepted_window() -> None:
    header = "| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |"
    text = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text()
    block = text[text.index(BRIDGE) :]
    block = block[: block.index(header) + len(header)]
    edit = [(block.encode(), block.replace("2023-12-30", "2023-12-21").encode())]
    ltm = edited_quarters(quarter=edit)[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] is None and ltm["start_date"] is None


SPLITS = (  # what follows the register's last row (Long-term debt); the 2033 notes moved there
    b"\n<!-- note -->\n" + NOTES_2033,
    b"\n<!-- a\n\nb -->\n" + NOTES_2033,
    b"\n" + NOTES_2033,
    b"\n" + NOTES_2033 + b"---\n",  # a rule under a row never makes it a heading
    b"\t" + NOTES_2033,  # indented by a tab: not a row, but it holds a pipe
    NOTES_2033[2:],  # without its leading pipe
    b"<!-- note --> " + NOTES_2033,  # row text after a comment on the same line
    b"<!--> " + NOTES_2033,
    b"<!-- a\nb --> " + NOTES_2033,
)


@pytest.mark.parametrize("moved", SPLITS)
def test_a_register_split_by_a_blank_line_or_hidden_text_is_refused(moved: bytes) -> None:
    edits = [(ADVANCES, b""), (LEASES, b""), (NOTES_2033, b""), (LONG_TERM, LONG_TERM + moved)]
    with pytest.raises(ValueError, match="model_table: the table under ### Debt"):
        edited_quarters(quarter=edits, register=True)


def test_a_plural_total_label_is_a_subtotal() -> None:
    row = b"| Subtotals: secured notes | carrying 12,892 | x |\n"
    assert annual_debt(LAST_NOTE, LAST_NOTE + row)["amount"] == "20020"


@pytest.mark.parametrize("underline", [b"-", b"="])
def test_a_setext_heading_ends_the_anchor_search(underline: bytes) -> None:
    got = quarter_debt((QUARTER_ANCHOR, QUARTER_ANCHOR + b"Next\n" + underline * 9 + b"\n"))
    assert (got["reason"], got["amount"]) == ("NOT_SOURCED", None)


@pytest.mark.parametrize("rule", [b"---\n", b"===\n", b"-\n"])
def test_a_rule_under_a_register_row_never_makes_the_row_a_heading(rule: bytes) -> None:
    last = quarter_debt((NOTES_2033, b""), (LONG_TERM, LONG_TERM + NOTES_2033 + rule))
    assert last["amount"] == "20192"  # the 2033 notes stay in the register: the hand key
    with pytest.raises(ValueError, match="model_table"):  # rows after the rule: a split
        annual_debt(LAST_NOTE, LAST_NOTE + rule)


BRIDGE_TWINS = {
    "spacing": b"| 9a | Total Company  EBITDA As Defined | 9,999 | 912 |\n",
    "bold": b"| 9a | **Total Company EBITDA As Defined** | 9,999 | 912 |\n",
    "colon": b"| 9a | Total Company EBITDA As Defined: | 9,999 | 912 |\n",
}


@pytest.mark.parametrize("twin", BRIDGE_TWINS.values(), ids=BRIDGE_TWINS)
@pytest.mark.parametrize("after", [True, False], ids=["after", "before"])
def test_a_repeated_bridge_ebitda_row_is_refused_whatever_its_spelling(
    twin: bytes, after: bool
) -> None:
    edit = ROW_BRIDGE + twin if after else twin + ROW_BRIDGE
    with pytest.raises(ValueError, match="model_row: expected one"):
        edited_quarters(quarter=[(ROW_BRIDGE, edit)])


def test_a_bold_bridge_ebitda_row_alone_is_the_row() -> None:
    bold = ROW_BRIDGE.replace(
        b"| Total Company EBITDA As Defined |", b"| **Total Company EBITDA As Defined** |"
    )
    ltm = edited_quarters(quarter=[(ROW_BRIDGE, bold)])[WINDOW]["ltm_adj_ebitda"]
    assert ltm["amount"] == "4322"  # 4,173 + 1,061 - 912, by hand


def test_a_bridge_without_a_label_column_is_refused_by_name() -> None:
    header = "| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |"
    text = (ROOT / "runs/tdg-003/CP-1-attempt-2.md").read_text()
    at = text.index(BRIDGE)
    block = text[at:]
    block = block[: block.index(header) + len(header)]
    unlabelled = block.replace("| Label |", "| Caption |")
    with pytest.raises(ValueError, match="model_columns: the quarter bridge needs a Label column"):
        edited_quarters(quarter=[(block.encode(), unlabelled.encode())])


def test_a_repeated_quarter_subtotal_gives_the_annual_outcome() -> None:
    annual_row = b"| Secured notes subtotal | carrying 10,892 | x |\n"
    quarter_row = b"| 14a | Secured notes subtotal | 10,950 | (88) | (14) | 10,898 |\n"
    annual = annual_debt(LAST_NOTE, LAST_NOTE + annual_row * 2)
    quarter = quarter_debt((NOTES_2033, NOTES_2033 + quarter_row * 2))
    assert (annual["amount"], annual["reason"]) == (None, "UNCLASSIFIED_ROW")
    assert (quarter["amount"], quarter["reason"]) == (None, "UNCLASSIFIED_ROW")
