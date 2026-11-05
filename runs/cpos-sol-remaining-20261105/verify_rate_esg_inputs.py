"""Read-only source, arithmetic and missingness checks for two distinct cases."""

import json
from dataclasses import asdict
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path

from deploy_workflow.owners.cp2e import Operands, derive_sensitivity

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_bytes())


def display(number):
    number = F(number)
    with localcontext() as ctx:
        ctx.prec = 65
        ctx.rounding = ROUND_HALF_EVEN
        return str(
            (Decimal(number.numerator) / Decimal(number.denominator)).quantize(Decimal(".000001"))
        )


def macro():
    expected = load(ROOT / "runs/cpos-tdg-macro-esg-001/expectations.json")
    old = load(ROOT / "runs/tdg-003/CP-2E-attempt-1-calculations.json")
    pages = {
        r["page"]: " ".join(r["text"].split())
        for r in map(
            json.loads, (ROOT / "runs/tdg-001/source-pages.jsonl").read_text().splitlines()
        )
    }
    for q in old["quotes"].values():
        assert " ".join(q["quote"].split()) in pages[q["pdf_page"]]
    terms = sum(map(F, expected["term_principals"]))
    floating = terms + F(expected["securitization_principal"])
    gross = F(expected["debt_note_gross_items"]) + F(expected["securitization_principal"])
    added = F(expected["source_approximate_added_interest"])
    interest = F(expected["base_interest"]) + added
    values = [
        floating,
        gross,
        F(expected["carrying_debt"]),
        sum(F(x[0]) for x in expected["active_swaps"]),
        F(expected["cap"][0]),
        floating * F(expected["shock_bp"]) / 10000,
        added,
        interest,
        F(expected["base_proxy"]) - added,
        F(expected["base_as_defined"]) / interest,
        sum(map(F, expected["environment_current"])),
        sum(map(F, expected["environment_prior"])),
    ]
    check = load(CAMPAIGN / "tdg-macro-esg/CP-2E.checks.json")["numeric_tables"][0]["rows"]
    assert [display(v) for v in values] == [display(r[1]) for r in check[:12]]
    assert [r[1] for r in check[12:]] == ["—"] * 3
    retained = load(CAMPAIGN / "tdg-macro-esg/legacy-diagnostic.json")
    inputs = {
        k: Decimal(v) if isinstance(v, str) and k != "rate_type" else v
        for k, v in retained["inputs"].items()
    }
    result = derive_sensitivity(
        operands=Operands(**inputs),
        rate_shocks_bp=(Decimal(100),),
        fx_shocks=(Decimal(".1"),),
        hedge_ratio=None,
    )
    assert json.loads(json.dumps(asdict(result), default=str)) == retained["actual"]
    assert result.rate[0].gross.amount is None
    assert result.fx[0].ebitda_after.amount is None and result.hedge.amount is None
    assert abs(F(result.floating_share.amount) - terms / gross) < F(1, 10**30)


def enel():
    old = ROOT / "runs/enel-sdg-2021-001"
    expected = load(old / "expectations.json")
    i = expected["source_inputs"]
    principal, step, price = (
        F(i["principal_eur_m"]),
        F(i["step_bp"]) / 10000,
        F(i["issue_price_pct"]) / 100,
    )
    ratio = F(i["kpi_ratio_counts"][0]) / F(i["kpi_ratio_counts"][1]) * 100
    values = [
        step,
        F(0),
        step,
        F(0),
        principal * step,
        principal * step,
        principal * price,
        principal * (1 - price),
        ratio,
        F(i["target_pct"]) - ratio,
        F(i["target_pct"]) - F("54.5"),
    ]
    check = load(CAMPAIGN / "enel-sdg/CP-2E.checks.json")["numeric_tables"][0]["rows"]
    assert [display(v) for v in values] == [r[1] for r in check]
    retained = load(CAMPAIGN / "enel-sdg/retained-calculations.json")["outputs"]
    for (key, _), value in zip(check, values, strict=True):
        assert abs(F(retained[key]) - value) < F(1, 10**30)
    assert i["observation"] < i["knowledge_cutoff"] < i["reference_date"] < i["maturity"]
    assert F(55) >= F(i["target_pct"]) and not all(x is True for x in (True, True, None))
    assert retained["initial_annual_coupon_eur_m"] == "0" and None != F(0)


if __name__ == "__main__":
    macro()
    enel()
    print(
        "TDG 15 controls / missing diagnostic and Enel 11 source arithmetic values verified separately"
    )
