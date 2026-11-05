"""Historical Frontier fixture: independent rational expectations, unchanged helper."""

import hashlib
import importlib.util
import re
import sys
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def decimal6(value):
    with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
        return str(
            (Decimal(value.numerator) / Decimal(value.denominator)).quantize(Decimal(".000001"))
        )


def check():
    source = ROOT / "runs/frontier-2020-001/sources/source-lines.txt"
    raw = source.read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "449e28443aebc42a7f5a2a323ca5dea1d4c34a2407531b9caaff47dcd3cac4d8"
    )
    lines = {
        int(line.split(":", 1)[0][1:]): line.split(":", 1)[1] for line in raw.decode().splitlines()
    }
    assert len(lines) == 1456
    assert all(
        i in lines for a, b in [(0, 100), (5921, 6344), (6830, 6923)] for i in range(a, b + 1)
    )

    def numbers(index):
        return [
            cell.strip().replace(",", "")
            for cell in lines[index].split("|")
            if re.fullmatch(r"[0-9][0-9,.]*", cell.strip())
        ]

    # Literal primary table checks; no production helper contributes expected values.
    for index, wanted in {
        6124: ["1306.1", "3523.2", "759.1"],
        6213: ["1654.1", "5274.1", "1107.1"],
        6127: ["749.0", "85", "637.6", "637.6"],
        6128: ["1740.0", "85", "1481.1", "1481.1"],
        6129: ["1650.0", "85", "1404.5", "1404.5"],
        6134: ["1600.0"],
        6139: ["615.8", "10", "58.7", "58.7"],
        6140: ["1600.0", "10", "152.5", "152.5"],
        6141: ["11445.4", "10", "1090.7", "1090.7"],
        6142: ["13.5", "10", "1.3", "1.3"],
        6143: ["8.7", "10", "0.8", "0.8"],
        6144: ["7.6", "10", "0.7", "0.7"],
        6145: ["15.4", "10", "1.5", "1.5"],
        6228: [],
        6229: ["464.9", "14", "64.4", "64.4"],
        6230: ["11445.4", "14", "1584.3", "1584.3"],
        6231: ["8.2", "14", "1.1", "1.1"],
        6232: ["8.3", "14", "1.2", "1.2"],
        6233: ["7.6", "14", "1.0", "1.0"],
        6234: ["15.4", "14", "2.1", "2.1"],
    }.items():
        assert numbers(index) == wanted, (index, numbers(index))
    for index, terms in {
        5988: ["assumed"],
        5998: ["each legal entity", "aggregation"],
        5977: ["10/31/20"],
        5983: ["11/1/20"],
        6324: ["Filing Date", "Liquidation Date", "pari passu"],
        6338: ["Filing Date"],
        6849: ["January 1, 2021"],
        6852: ["$10.00", "$12.50", "$11.25"],
        6853: ["$6.56", "$1.37", "$3.32", "$2.07", "$4.57"],
        2422: ["at least two-thirds", "more than one-half", "actually voted"],
    }.items():
        assert all(term in lines[index] for term in terms), index

    helper = (
        ROOT
        / "docs/reuse/selected-methods/skills/cp-4c-restructuring-fulcrum/scripts/recovery_waterfall.py"
    )
    assert (
        hashlib.sha256(helper.read_bytes()).hexdigest()
        == "2e6c084747be7f67052c5c333fc80d5954f0fe6dcdba14e6b933fffaae3c1878"
    )
    spec = importlib.util.spec_from_file_location("selected_recovery", helper)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    claims = [
        {
            "claim_id": "1L_AGGREGATE",
            "class": "three equal-rank first lien instruments",
            "amount": "4139.0",
            "entities": ["source aggregated pledged pool"],
        },
        {
            "claim_id": "2L",
            "class": "second lien collateral component",
            "amount": "1600.0",
            "entities": ["source aggregated pledged pool"],
        },
    ]
    assert sum(map(Fraction, ["749", "1740", "1650"])) == 4139
    cases = []
    values = []
    for label, pool, holdco, guc, published in [
        (
            "low",
            "3523.2",
            "1306.1",
            ["615.8", "1600", "11445.4", "13.5", "8.7", "7.6", "15.4"],
            ["58.7", "152.5", "1090.7"],
        ),
        (
            "high",
            "5274.1",
            "1654.1",
            ["0", "464.9", "11445.4", "8.2", "8.3", "7.6", "15.4"],
            ["0", "64.4", "1584.3"],
        ),
    ]:
        # Separate closed-form two-rank oracle, no invocation of production arithmetic.
        available = Fraction(pool)
        first = min(available, Fraction(4139))
        second = max(available - 4139, Fraction(0))
        assert second <= 1600 and first + second == available
        deficiencies = [4139 - first, 1600 - second]
        assert deficiencies == list(map(Fraction, guc[:2]))
        total = sum(map(Fraction, guc))
        rate = Fraction(holdco) / total
        payouts = [Fraction(amount) * rate for amount in guc]
        assert sum(payouts) == Fraction(holdco)
        helper_result = module.waterfall(pool, claims)
        assert [Fraction(str(row["recovered"])) for row in helper_result["claims"]] == [
            first,
            second,
        ]
        assert [Fraction(str(row["recovery_pct"])) for row in helper_result["claims"]] == [
            Fraction(decimal6(first / 4139)),
            Fraction(decimal6(second / 1600)),
        ]
        assert helper_result["fulcrum_claim_id"] == ("1L_AGGREGATE" if label == "low" else "2L")
        assert helper_result["residual_to_equity"] == 0 and helper_result["fully_allocated"] is True
        vals = [
            available,
            Fraction(holdco),
            Fraction(4139),
            first,
            second,
            *deficiencies,
            total,
            rate,
            *payouts,
            (first + payouts[0]) / 4139,
            (second + payouts[1]) / 1600,
            rate,
            *[Fraction(src) - calc for src, calc in zip(published, payouts[:3], strict=True)],
        ]
        values.append(vals)
        cases.append(
            {
                "case": label,
                "net_pledged_proceeds_USDm": pool,
                "holdco_available_USDm": holdco,
                "holdco_claims_USDm": dict(
                    zip(
                        [
                            "1L_deficiency",
                            "2L_deficiency",
                            "Senior_Notes",
                            "OPEB_deficiency",
                            "Lease_Rejection",
                            "Trade",
                            "Trade_deficiency",
                        ],
                        guc,
                        strict=True,
                    )
                ),
                "helper_result": helper_result,
            }
        )
    labels = [
        "net_pledged_proceeds_USDm",
        "holdco_available_USDm",
        "equal_rank_first_lien_claims_USDm",
        "first_lien_collateral_paid_USDm",
        "second_lien_collateral_paid_USDm",
        "first_lien_deficiency_USDm",
        "second_lien_deficiency_USDm",
        "holdco_unsecured_claims_USDm",
        "holdco_pro_rata_fraction",
        "first_lien_deficiency_paid_USDm",
        "second_lien_deficiency_paid_USDm",
        "senior_notes_paid_USDm",
        "OPEB_deficiency_paid_USDm",
        "lease_paid_USDm",
        "trade_paid_USDm",
        "trade_deficiency_paid_USDm",
        "first_lien_total_recovery_fraction",
        "second_lien_total_recovery_fraction",
        "senior_notes_total_recovery_fraction",
        "source_minus_calculated_1L_deficiency_paid_USDm",
        "source_minus_calculated_2L_deficiency_paid_USDm",
        "source_minus_calculated_senior_notes_paid_USDm",
    ]
    grid = {
        "heading": "Recovery numeric controls",
        "columns": ["Metric", "Low", "High"],
        "rows": [
            [name, decimal6(a), decimal6(b)] for name, a, b in zip(labels, *values, strict=True)
        ],
    }
    bridge = {
        "heading": "Plan equity bridge controls",
        "columns": ["Scenario", "EV_USDm", "Net_debt_USDm", "Pension_OPEB_USDm", "Equity_USDm"],
        "rows": [
            [n, v, "6560", "1370", str(Fraction(v) - 6560 - 1370)]
            for n, v in [("low", "10000"), ("midpoint", "11250"), ("high", "12500")]
        ],
    }
    assert [r[-1] for r in bridge["rows"]] == ["2070", "3320", "4570"]
    sensitivity = module.sensitivity(
        claims,
        [{"label": c["case"], "enterprise_value": c["net_pledged_proceeds_USDm"]} for c in cases],
    )
    assert sensitivity["fulcrum_stable"] is False
    try:
        module.waterfall("100", [claims[0], claims[0]])
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate guarantee claim was accepted")
    unknown = module.waterfall("500", [dict(claims[0], amount=None), claims[1]])
    assert unknown["status"] == "Not Calculable" and unknown["fulcrum_claim_id"] is None
    assert all(r["recovered"] is None for r in unknown["claims"])
    for amount, state, fulcrum in [
        ("0", "zero recovery", None),
        ("4139", "class boundary", None),
        ("5739", "fully repaid", None),
        ("5740", "fully repaid", None),
    ]:
        result = module.waterfall(amount, claims)
        assert result["allocation_state"] == state and result["fulcrum_claim_id"] == fulcrum
        assert result["residual_to_equity"] == (1 if amount == "5740" else 0)
    return {
        "scope": "Unchanged helper on source-defined net pledged liquidation pools, independent Fraction recovery/deficiency/plan-bridge expectations. Not independent full valuation, current rights or realized distributions.",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_rows_checked": 20,
        "cases": cases,
        "sensitivity": sensitivity,
        "synthetic_controls": 6,
    }, [grid, bridge]
