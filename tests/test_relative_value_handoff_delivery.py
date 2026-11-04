"""Real retained comparison plus synthetic chart-transport boundary controls."""

import hashlib
import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

from deploy_vii.report_view import pathways
from deploy_workflow.markdown_delivery import _yield_observations, literal_module
from deploy_workflow.owners.cpos import run_handoffs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-arcc-rv-001"


def test_actual_relative_value_sections_and_four_exact_conditional_yields(tmp_path):
    data = json.loads((CASE / "workflow.json").read_bytes())
    for group in ("sources", "instructions", "retained_handoffs"):
        for spec in data[group].values():
            spec["path"] = str((CASE / spec["path"]).resolve())
    manifest = tmp_path / "workflow.json"
    manifest.write_text(json.dumps(data))
    responses = {m: Path(s["path"]).read_bytes() for m, s in data["retained_handoffs"].items()}

    def no_execute(task):
        raise AssertionError("Chart delivery must not rerun analytical models")

    def check(task, raw):
        assert raw == responses[task.module_id]
        return ()

    report = run_handoffs(manifest, tmp_path / "state", execute=no_execute, check=check)
    view = json.loads((report.parent / "view.json").read_bytes())
    assert [m["module_id"] for m in view["modules"]] == ["CP-3D", "CP-3", "CP-6"]
    rv = json.loads((report.parent / "report-view.json").read_bytes())
    assert tuple(b["block_id"] for b in rv["blocks"]) == next(
        p.blocks for p in pathways() if p.id == "relative_value"
    )
    assert all(b["state"] == "populated" for b in rv["blocks"])
    assert rv["blocks"][0]["kind"] == "dense" and len(rv["blocks"][0]["rows"]) == 2
    figure = rv["blocks"][1]["figures"][0]
    assert figure["fig_id"] == "RV.1" and figure["chart"]["unit_class"] == "percent"
    marks = figure["chart"]["marks"]
    assert len(marks) == 4
    expected = json.loads((ROOT / "runs/arcc-selection-2024-001/expectations.json").read_bytes())
    with localcontext() as context:
        context.prec = 80
        for source in expected["securities"].values():
            for case, label in (("assume_clean", "Assume clean"), ("assume_dirty", "Assume dirty")):
                mark = next(
                    m
                    for m in marks
                    if m["label"] == source["maturity"] + " · " + source["isin"]
                    and m["series"] == label
                )
                source_points = (
                    Decimal(source["cases"][case]["maturity_yield_decimal_expected"]) * 100
                ).quantize(Decimal(".000000001"), rounding=ROUND_HALF_UP)
                assert Fraction(mark["value"]) == Fraction(source_points) / 100
                assert (
                    mark["text"]
                    == f"{source_points.quantize(Decimal('.000001'), rounding=ROUND_HALF_UP):f}%"
                )
                passport = next(p for p in rv["passports"] if p["ref_id"] == mark["ref_id"])
                fields = {f["name"]: f["value"] for f in passport["fields"]}
                assert fields["Source"] == "CP-3"
                assert fields["SHA-256"] == hashlib.sha256(responses["CP-3"]).hexdigest()
                assert str(source_points) in fields["Quote"]
    assert [m["text"] for m in marks] == [
        r["cells"][0]["text"] for r in figure["chart"]["table_twin"]["rows"]
    ]
    assert "separate clean/dirty" in figure["summary"].lower()
    for module, raw in responses.items():
        assert (report.parent / (module + ".md")).read_bytes() == raw
    assert run_handoffs(manifest, tmp_path / "state", execute=no_execute, check=check) == report
    assert len(list((tmp_path / "state/requests").glob("*/*/*.response.md"))) == 3


def chart_source(rows, *, header="Yield, %", owner="CP-3"):
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    raw = (
        f"# {owner} — synthetic transport\n\n## Request\n\nTest only.\n\n"
        f"## Sources\n\nSynthetic, not issuer evidence.\n\n## Findings\n\n"
        f"### Conditional yield observations\n\n| Instrument | Maturity | Price basis | {header} |\n"
        f"|---|---|---|---:|\n{body}\n\n## Calculations\n\nNone.\n\n"
        "## Gaps\n\nNo model proof.\n\n## Next module\n\nTransport only.\n"
    ).encode()
    module, _, _ = literal_module(owner, raw)
    return module, module.tables[0], date(2024, 12, 31)


def test_missing_zero_and_negative_yield_stay_distinct_under_low_decimal_precision():
    rows = [
        ("A", "2029-03-01", "Assume clean", "0"),
        ("A", "2029-03-01", "Assume dirty", ""),
        ("B", "2029-07-15", "Assume clean", "-0.123456789"),
        ("B", "2029-07-15", "Assume dirty", "6.316949000"),
    ]
    args = chart_source(rows)
    with localcontext() as context:
        context.prec = 2
        module, _, points = _yield_observations(*args)
    facts = {f.fact_id: f for f in module.facts}
    values = [facts[p.fact_id] for p in points]
    assert [f.amount for f in values] == [
        Decimal(0),
        None,
        Decimal("-.00123456789"),
        Decimal(".06316949000"),
    ]
    assert values[0].status == "known" and values[1].status == "missing"


@pytest.mark.parametrize("token", ["NaN", "Infinity", "1e2", "5.6%", "5,6", "5 USD", "9" * 65])
def test_non_plain_or_non_percent_numeric_token_refuses(token):
    with pytest.raises(ValueError, match="markdown_yield"):
        _yield_observations(
            *chart_source(
                [
                    ("A", "2029-03-01", "Assume clean", token),
                    ("A", "2029-03-01", "Assume dirty", "6"),
                ]
            )
        )


@pytest.mark.parametrize("maturity", ["2029-02-30", "20290301", "2024-12-31", "2024-01-01"])
def test_invalid_or_nonfuture_maturity_refuses(maturity):
    with pytest.raises(ValueError):
        _yield_observations(
            *chart_source(
                [("A", maturity, "Assume clean", "5"), ("A", maturity, "Assume dirty", "6")]
            )
        )


@pytest.mark.parametrize(
    "header,owner,basis",
    [
        ("Yield, bp", "CP-3", "Assume clean"),
        ("Yield, %", "CP-2", "Assume clean"),
        ("Yield, %", "CP-3", "Observed"),
    ],
)
def test_wrong_unit_owner_or_unlocked_basis_refuses(header, owner, basis):
    with pytest.raises(ValueError, match="markdown_yield"):
        _yield_observations(
            *chart_source(
                [("A", "2029-03-01", basis, "5"), ("A", "2029-03-01", "Assume dirty", "6")],
                header=header,
                owner=owner,
            )
        )


@pytest.mark.parametrize(
    "rows",
    [
        [("A", "2029-03-01", "Assume clean", "5"), ("A", "2029-03-01", "Assume clean", "6")],
        [("A", "2029-03-01", "Assume clean", "5"), ("A", "2030-07-15", "Assume clean", "6")],
        [("A", "2029-03-01", "Assume clean", "5"), ("A", "2030-07-15", "Assume dirty", "6")],
        [("A", "2029-03-01", "Assume clean", "5")],
        [("A", "2029-03-01", "Assume clean", ""), ("A", "2029-03-01", "Assume dirty", "")],
    ],
)
def test_duplicate_conflicting_omitted_or_all_missing_cases_refuse(rows):
    with pytest.raises(ValueError, match="markdown_yield"):
        _yield_observations(*chart_source(rows))
