"""Independent rational controls against literal May 2025 N-PORT positions."""

import hashlib
import re
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS = {"n": "http://www.sec.gov/edgar/nport"}
LITERALS = [
    (888, "US04010LBK89", "4430000", "4393034.75", "0.014252072815", "2030-09-01", "5.50", "0"),
    (1453, "US04010LBB80", "1347000", "1256309.72", "0.004075774180", "2028-06-15", "2.88", "0"),
    (
        1780,
        "US04010LBG77",
        "10247000",
        "10424576.41",
        "0.033819860419",
        "2029-07-15",
        "5.95",
        "1213674.2128",
    ),
    (2173, "US04010LBH50", "10572000", "10414771.10", "0.033788049610", "2032-03-08", "5.80", "0"),
    (
        2561,
        "US04010LBF94",
        "7177000",
        "7273541.42",
        "0.023597136795",
        "2029-03-01",
        "5.88",
        "306062.3530",
    ),
]


def check():
    path = ROOT / "runs/lqd-portfolio-001/sources/LQD-20250531-NPORT.xml"
    raw = path.read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "7617ce8e9f605035939d57fdf019636510ba08d9cb2388d561be04d574bb11df"
    )
    root = ET.fromstring(raw)

    def value(path):
        return root.findtext(path, namespaces=NS)

    assert value(".//n:genInfo/n:seriesId") == "S000004361"
    assert value(".//n:genInfo/n:seriesLei") == "549300FYCXFXG8POR355"
    assert value(".//n:repPdDate") == "2025-05-31"
    assert value(".//n:repPdEnd") == "2026-02-28"
    nav = Fraction("30823830378.19")
    assert Fraction(value(".//n:netAssets")) == nav
    assert Fraction(value(".//n:totAssets")) - Fraction(value(".//n:totLiabs")) == nav
    items = root.findall(".//n:invstOrSec", NS)
    snippets = re.findall(rb"<invstOrSec>.*?</invstOrSec>", raw, re.DOTALL)
    assert len(items) == len(snippets) == 2910
    included = [
        i
        for i, el in enumerate(items, 1)
        if el.findtext("n:lei", namespaces=NS) == "WEQ82666OJYSI5GUAB47"
    ]
    excluded = [
        i
        for i, el in enumerate(items, 1)
        if el.findtext("n:lei", namespaces=NS) == "549300IANZJVZPTICV54"
    ]
    assert included == [r[0] for r in LITERALS] and excluded == [887, 2092]
    grids = []
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):

        def fmt(f):
            f = Fraction(f)
            return str(
                (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal(".000000001"))
            )

        rows = []
        for ordinal, isin, par, mv, pct, maturity, coupon, loan in LITERALS:
            el = items[ordinal - 1]
            assert el.find("n:identifiers/n:isin", NS).get("value") == isin
            for tag, expected in [
                ("units", "PA"),
                ("curCd", "USD"),
                ("fairValLevel", "2"),
                ("payoffProfile", "Long"),
                ("isRestrictedSec", "N"),
                ("debtSec/n:maturityDt", maturity),
                ("debtSec/n:couponKind", "Fixed"),
                ("debtSec/n:isDefault", "N"),
                ("debtSec/n:areIntrstPmntsInArrs", "N"),
                ("debtSec/n:isPaidKind", "N"),
            ]:
                assert el.findtext("n:" + tag, namespaces=NS) == expected
            for tag, expected in [
                ("balance", par),
                ("valUSD", mv),
                ("pctVal", pct),
                ("debtSec/n:annualizedRt", coupon),
            ]:
                assert Fraction(el.findtext("n:" + tag, namespaces=NS)) == Fraction(expected)
            lending = el.find("n:securityLending/n:loanByFundCondition", NS)
            if Fraction(loan):
                assert lending is not None and lending.get("isLoanByFund") == "Y"
                assert Fraction(lending.get("loanVal")) == Fraction(loan)
            else:
                assert (
                    lending is None
                    and el.findtext("n:securityLending/n:isLoanByFund", namespaces=NS) == "N"
                )
            # These five published percentages are consistent with truncation at 12 places.
            # Preserve them separately from ratios recomputed using the matched filing NAV.
            assert 0 <= Fraction(mv) / nav * 100 - Fraction(pct) < Fraction(1, 10**12)
            rows.append([isin, fmt(par), fmt(mv), pct, fmt(coupon), fmt(loan)])
        par = sum(Fraction(r[2]) for r in LITERALS)
        mv = sum(Fraction(r[3]) for r in LITERALS)
        subset = sum(Fraction(r[3]) for r in LITERALS if r[5].startswith("2029"))
        selected_par, selected_mv = Fraction(LITERALS[2][2]), Fraction(LITERALS[2][3])
        assert (
            par == 33773000 and mv == Fraction("33762233.40") and subset == Fraction("17698117.83")
        )
        loan = sum(Fraction(r[7]) for r in LITERALS)
        assert loan == Fraction("1519736.5658") < mv
        amounts = [
            ("fund_nav_USD", nav),
            ("issuer_par_USD", par),
            ("issuer_value_USD", mv),
            ("maturity2029_value_USD", subset),
            ("on_loan_subset_USD", loan),
            ("issuer_pct_NAV", mv / nav * 100),
            ("selected_pct_NAV", selected_mv / nav * 100),
            ("maturity2029_pct_issuer", subset / mv * 100),
            ("price10_loss_USD", mv / 10),
            ("price10_loss_NAV_bps", mv / 10 / nav * 10000),
        ]
        for r in [Fraction(2, 5), Fraction(3, 5)]:
            name = str(int(r * 100))
            amounts.extend(
                [
                    ("recovery" + name + "_proceeds_USD", par * r),
                    ("recovery" + name + "_loss_USD", mv - par * r),
                    ("recovery" + name + "_loss_NAV_bps", (mv - par * r) / nav * 10000),
                ]
            )
        amounts.extend(
            [
                ("selected_recovery40_proceeds_USD", selected_par * Fraction(2, 5)),
                ("selected_recovery40_loss_USD", selected_mv - selected_par * Fraction(2, 5)),
                (
                    "selected_recovery40_loss_NAV_bps",
                    (selected_mv - selected_par * Fraction(2, 5)) / nav * 10000,
                ),
            ]
        )
        grids = [
            {
                "heading": "Holding controls",
                "columns": [
                    "ISIN",
                    "Par_USD",
                    "Value_USD",
                    "Reported_pct_NAV",
                    "Reported_coupon_pct",
                    "On_loan_value_USD",
                ],
                "rows": rows,
            },
            {
                "heading": "Exposure and loss controls",
                "columns": ["Metric", "Value"],
                "rows": [[label, fmt(f)] for label, f in amounts],
            },
        ]
    extract = b"Source: LQD-20250531-NPORT.xml SHA256 7617ce8e9f605035939d57fdf019636510ba08d9cb2388d561be04d574bb11df; retained literal fragments, not whole filing. Holdings scanned:2910. Exact issuer LEI match includes5; related issuer887/2092 explicitly excluded. Ordinals1-based.\n\n"
    extract += re.search(rb"<genInfo>.*?</genInfo>", raw, re.DOTALL)[0] + b"\n\n"
    for tag in [b"totAssets", b"totLiabs", b"netAssets"]:
        extract += re.search(b"<" + tag + b">.*?</" + tag + b">", raw)[0] + b"\n"
    for ordinal in sorted(included + excluded):
        extract += (
            f"\n\nOriginal invstOrSec ordinal {ordinal}; {'INCLUDED' if ordinal in included else 'EXCLUDED related issuer'}:\n".encode()
            + snippets[ordinal - 1]
        )
    return extract, grids
