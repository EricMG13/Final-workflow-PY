"""Offline controls of the campaign checker; not live analytical proof."""

import hashlib
import json
import runpy
from fractions import Fraction
from pathlib import Path

import pytest

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]
HARNESS = runpy.run_path(str(CASE / "run_module.py"))


@pytest.mark.parametrize("mutation", ["missing_as_zero", "wrong_entity", "wrong_locator"])
def test_lmi_map_refuses_source_corruption(tmp_path, mutation):
    checks = runpy.run_path(str(CASE / "verify_legal_inputs.py"))
    original = CASE / "lmi-structure/CP-4B.md"
    assert checks["verify_lmi_map"](original)
    raw = original.read_text()
    replacements = {
        "missing_as_zero": ("| — | — | — | ICA p.11 L592", "| 0 | — | — | ICA p.11 L592"),
        "wrong_entity": ("| LMI AEROSPACE, INC. |", "| Different issuer |"),
        "wrong_locator": ("| ICA p.11 L592–L596; P; Q |", "| ICA p.11 L597–L601; P; Q |"),
    }
    before, after = replacements[mutation]
    assert raw.count(before) == 1
    path = tmp_path / "mutated.md"
    path.write_text(raw.replace(before, after))
    with pytest.raises(AssertionError):
        checks["verify_lmi_map"](path)


def test_frontier_source_recovery_and_null_boundaries_ignore_decimal_context():
    from decimal import ROUND_FLOOR, localcontext

    check = runpy.run_path(str(CASE / "verify_recovery_inputs.py"))["check"]
    expected = check()
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_FLOOR
        assert check() == expected


def sample():
    _, task, check = HARNESS["load_task"](CASE / "tdg-earnings/CP-1B.task.json")
    raw = (ROOT / "runs/tdg-003/CP-1B-attempt-1.md").read_text()
    # Synthetic provenance-format adaptation over a frozen historical answer.
    raw = raw.replace(
        "## Sources\n",
        "## Sources\nU.S. GAAP; 2024-10-01 to 2024-12-28; 2023-10-01 to 2023-12-30; "
        + ", ".join(hashlib.sha256(v).hexdigest() for v in task.handoffs.values())
        + "\n",
        1,
    )
    return task, check, raw


def test_frozen_control_reaches_existing_delivery():
    task, check, raw = sample()
    assert check(task, raw.encode()) == ()


@pytest.mark.parametrize(
    "before,after,diagnostic",
    [
        ("| Revenue | 1789 | 2006 | 217 |", "| Revenue | 1789 | 2006 | 218 |", "Revenue"),
        ("| Capex signed cash flow | -36 | -42 |", "| Capex signed cash flow | 36 | 42 |", "Capex"),
        ("2024-12-28", "2024-12-29", "2024-12-28"),
        ("| Revenue | 1789 | 2006 |", "| Revenue | | 2006 |", "Comparator"),
        ("12.13%", "12.12%", "Revenue"),
        ("### Financial performance / comparator register", "### Different", "Comparator"),
    ],
)
def test_bad_source_math_period_and_selector_refuse(before, after, diagnostic):
    task, check, raw = sample()
    assert before in raw
    assert any(diagnostic in issue for issue in check(task, raw.replace(before, after).encode()))


def test_changed_pinned_instruction_refuses_before_model(tmp_path):
    original = CASE / "tdg-earnings/CP-1B.task.json"
    spec = json.loads(original.read_bytes())
    for entries in (spec["sources"], spec["handoffs"], {"instruction": spec["instructions"]}):
        for item in entries.values():
            item["path"] = str((original.parent / item["path"]).resolve())
    spec["instructions"]["sha256"] = "0" * 64
    path = tmp_path / "task.json"
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="cpos_input_changed"):
        HARNESS["load_task"](path)


def budget_sample():
    """Synthetic checker/selector control, never issuer analytical proof."""
    path = CASE / "crc-liquidity/CP-2D.task.json"
    spec, task, check = HARNESS["load_task"](path)
    expected = json.loads((path.parent / spec["checks"]).read_bytes())
    layout = json.loads((path.parent / spec["layout"]).read_bytes())
    text = "## Request\n\nLiquidity view: CRC synthetic checker control only, as of 2020-07-23.\n\n"
    text += " ".join(expected["required_terms"]) + "\n\n## Sources\n\nSynthetic.\n\n## Findings\n\n"
    grids = {grid["heading"]: grid for grid in expected["numeric_tables"]}
    for route in layout["routes"]:
        if route["kind"] != "table":
            continue
        grid = grids.get(route["heading"], {"columns": ["Field", "Value"], "rows": [["X", "Y"]]})
        text += "### " + route["heading"] + "\n\n"
        for row in [grid["columns"], ["---"] * len(grid["columns"]), *grid["rows"]]:
            text += "| " + " | ".join(row) + " |\n"
        text += "\n"
    text += "## Calculations\n\nSynthetic.\n\n## Gaps\n\nSynthetic.\n\n## Next module\n\nSynthetic.\n"
    return task, check, text


def test_budget_checker_accepts_exact_source_grid_control():
    task, check, text = budget_sample()
    assert check(task, text.encode()) == ()


@pytest.mark.parametrize(
    "before,after",
    [
        ("| 2020-07-17 | -68 |", "| 2020-07-18 | -68 |"),
        ("| 2020-07-17 | -68 |", "| 2020-07-17 | 68 |"),
        ("| Sep-2020 | 10 | — | — |", "| Sep-2020 | 10 | 0 | — |"),
        ("| Sep-2020 | 10 | — | — |", "| Sep-2020 | 10 | Not supplied | — |"),
        ("| Jan-2021 stub through 2021-01-15 |", "| Jan-2021 |"),
        ("| 2020-07-17 | -68 |", "| 2020-07-17 | |"),
    ],
)
def test_budget_checker_rejects_date_sign_dash_missing_and_stub_corruption(before, after):
    task, check, text = budget_sample()
    assert before in text
    assert check(task, text.replace(before, after).encode())


def test_explicit_repair_preserves_exact_pinned_model_draft():
    path = CASE / "crc-liquidity/CP-3C.tenor-repair.task.json"
    _, task, _ = HARNESS["load_task"](path)
    assert task.draft == (path.parent / "CP-3C.md").read_bytes()


def test_market_and_pair_controls_are_independent_of_decimal_context():
    from decimal import ROUND_FLOOR, localcontext

    from verify_market_inputs import check as market
    from verify_selection_inputs import check as pair

    expected = market(), pair()
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_FLOOR
        assert (market(), pair()) == expected
    differences = expected[1][1][-1]["rows"]
    # Rounded source values alone can reverse the clean-basis point yield ordering.
    assert Fraction(differences[0][-2]) < 0 < Fraction(differences[0][-1])
    assert 0 < Fraction(differences[1][-2]) < Fraction(differences[1][-1])


def test_portfolio_source_percentages_do_not_require_nearest_rounding():
    from decimal import ROUND_FLOOR, localcontext

    from verify_portfolio_inputs import LITERALS, check

    expected = check()
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_FLOOR
        assert check() == expected
    selected = LITERALS[2]
    recalculated = Fraction(selected[3]) / Fraction("30823830378.19") * 100
    # The actual published selected-note percentage is lower by > half a final digit.
    assert Fraction(1, 2 * 10**12) < recalculated - Fraction(selected[4]) < Fraction(1, 10**12)
    assert b"ordinal 887; EXCLUDED" in expected[0]
    assert b"ordinal 2092; EXCLUDED" in expected[0]
