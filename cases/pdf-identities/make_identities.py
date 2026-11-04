"""Write cases/pdf-identities/<DOC>.json: arithmetic identities of the primary statements.

Run from the repo root: python3 -I cases/pdf-identities/make_identities.py

Answer key (CP1H-R23, F1). The row labels and printed values below were read by the preparer from
tests/fixtures/pdf_pages/<DOC>/pNNN.txt. The script then checks, with stdlib only, that each label
occurs on a line of the named page together with its printed values in column order, and that each
identity holds exactly in Decimal arithmetic for every column. It aborts if either check fails.
No product code was read or run.

Printed strings are kept as printed without the currency sign: "(6,283)" is negative, a dash is zero.
Values are decimal strings in the statement's own unit (no scaling): USD millions (TDG, CZR, FUN),
USD thousands (SIX22), GBP millions (VMO2Q3, VMED25).
"""

import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(".")
PAGES = ROOT / "tests" / "fixtures" / "pdf_pages"
OUT = ROOT / "cases" / "pdf-identities"


def row(label, page, *printed):
    return {"label": label, "page": page, "printed": list(printed)}


# kind, id, equation text, sum lhs == sum rhs
SPECS = {
    "TDG": {
        "unit": "USD millions",
        "identities": [
            {
                "id": "TDG-BS-1",
                "kind": "BS",
                "equation": "total assets = total liabilities + total equity",
                "headers": ["2024", "2023"],
                "lhs": [row("TOTAL ASSETS", 105, "25,586", "19,970")],
                "rhs": [
                    row("Total liabilities", 105, "31,869", "21,948"),
                    row("Total stockholders’ deficit", 105, "(6,283)", "(1,978)"),
                ],
            },
            {
                "id": "TDG-BS-2",
                "kind": "BS",
                "equation": "total assets = the printed total of liabilities and equity",
                "headers": ["2024", "2023"],
                "lhs": [row("TOTAL ASSETS", 105, "25,586", "19,970")],
                "rhs": [
                    row("TOTAL LIABILITIES AND STOCKHOLDERS’ DEFICIT", 105, "25,586", "19,970")
                ],
            },
            {
                "id": "TDG-CFS-1",
                "kind": "CFS",
                "equation": "operating + investing + financing + exchange-rate effect = net change in cash",
                "headers": ["2024", "2023", "2022"],
                "lhs": [
                    row("Net cash provided by operating activities", 109, "2,045", "1,375", "948"),
                    row("Net cash used in investing activities", 109, "(2,441)", "(900)", "(553)"),
                    row(
                        "Net cash provided by (used in) financing activities",
                        109,
                        "3,171",
                        "(16)",
                        "(2,148)",
                    ),
                    row(
                        "EFFECT OF EXCHANGE RATE CHANGES ON CASH AND CASH EQUIVALENTS",
                        109,
                        "14",
                        "12",
                        "(33)",
                    ),
                ],
                "rhs": [
                    row(
                        "NET INCREASE (DECREASE) IN CASH AND CASH EQUIVALENTS",
                        109,
                        "2,789",
                        "471",
                        "(1,786)",
                    )
                ],
            },
            {
                "id": "TDG-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + net change = cash at end",
                "headers": ["2024", "2023", "2022"],
                "lhs": [
                    row(
                        "CASH AND CASH EQUIVALENTS, BEGINNING OF PERIOD",
                        109,
                        "3,472",
                        "3,001",
                        "4,787",
                    ),
                    row(
                        "NET INCREASE (DECREASE) IN CASH AND CASH EQUIVALENTS",
                        109,
                        "2,789",
                        "471",
                        "(1,786)",
                    ),
                ],
                "rhs": [
                    row("CASH AND CASH EQUIVALENTS, END OF PERIOD", 109, "6,261", "3,472", "3,001")
                ],
            },
        ],
    },
    "CZR": {
        "unit": "USD millions",
        "identities": [
            {
                "id": "CZR-BS-1",
                "kind": "BS",
                "equation": "total assets = total liabilities + total stockholders' equity",
                "headers": ["2025", "2024"],
                "lhs": [row("Total assets", 56, "31,639", "32,590")],
                "rhs": [
                    row("Total liabilities", 56, "27,953", "28,214"),
                    row("Total stockholders’ equity", 56, "3,686", "4,376"),
                ],
            },
            {
                "id": "CZR-BS-2",
                "kind": "BS",
                "equation": "total assets = the printed total of liabilities and equity",
                "headers": ["2025", "2024"],
                "lhs": [row("Total assets", 56, "31,639", "32,590")],
                "rhs": [row("Total liabilities and stockholders’ equity", 56, "31,639", "32,590")],
            },
            {
                "id": "CZR-CFS-1",
                "kind": "CFS",
                "equation": "operating + investing + financing = change in cash (no exchange-rate row is printed)",
                "headers": ["2025", "2024", "2023"],
                "lhs": [
                    row("Net cash provided by operating activities", 60, "1,302", "1,075", "1,809"),
                    row("Net cash used in investing activities", 60, "(571)", "(704)", "(1,256)"),
                    row("Net cash used in financing activities", 60, "(763)", "(498)", "(713)"),
                ],
                "rhs": [
                    row(
                        "Decrease in cash, cash equivalents and restricted cash",
                        60,
                        "(32)",
                        "(127)",
                        "(160)",
                    )
                ],
            },
            {
                "id": "CZR-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + change = cash at end",
                "headers": ["2025", "2024", "2023"],
                "lhs": [
                    row(
                        "Cash, cash equivalents and restricted cash, beginning of period",
                        60,
                        "1,016",
                        "1,143",
                        "1,303",
                    ),
                    row(
                        "Decrease in cash, cash equivalents and restricted cash",
                        60,
                        "(32)",
                        "(127)",
                        "(160)",
                    ),
                ],
                "rhs": [
                    row(
                        "Cash, cash equivalents and restricted cash, end of period",
                        60,
                        "984",
                        "1,016",
                        "1,143",
                    )
                ],
            },
            {
                "id": "CZR-CFS-3",
                "kind": "CFS",
                "equation": "continuation page 61: the reconciliation lines add to the closing cash printed on page 60",
                "headers": ["2025", "2024", "2023"],
                "lhs": [
                    row("Cash and cash equivalents", 61, "887", "866", "1,005"),
                    row("Restricted cash", 61, "85", "95", "122"),
                    row(
                        "Restricted and escrow cash included in other long-term assets, net",
                        61,
                        "12",
                        "55",
                        "16",
                    ),
                ],
                "rhs": [
                    row(
                        "Total cash, cash equivalents and restricted cash",
                        61,
                        "984",
                        "1,016",
                        "1,143",
                    )
                ],
            },
        ],
    },
    "FUN": {
        "unit": "USD millions",
        "identities": [
            {
                "id": "FUN-BS-1",
                "kind": "BS",
                "equation": "total assets = total liabilities + total equity",
                "headers": ["December 31, 2024", "December 31, 2025"],
                "lhs": [row("Total assets", 116, "285,196", "289,160")],
                "rhs": [
                    row("Total liabilities", 116, "240,338", "253,180"),
                    row("Total equity", 116, "44,858", "35,980"),
                ],
            },
            {
                "id": "FUN-BS-2",
                "kind": "BS",
                "equation": "total assets = the printed total of liabilities and equity",
                "headers": ["December 31, 2024", "December 31, 2025"],
                "lhs": [row("Total assets", 116, "285,196", "289,160")],
                "rhs": [row("Total liabilities and equity", 116, "285,196", "289,160")],
            },
            {
                "id": "FUN-CFS-1",
                "kind": "CFS",
                "equation": "operating + investing + financing + exchange-rate effect = net change in cash",
                "headers": ["2023", "2024", "2025"],
                "lhs": [
                    row(
                        "Net cash provided by/(used in) operating activities",
                        117,
                        "14,918",
                        "15,423",
                        "21,282",
                    ),
                    row(
                        "Net cash provided by/(used in) investing activities",
                        117,
                        "(17,628)",
                        "(24,370)",
                        "(18,049)",
                    ),
                    row(
                        "Net cash provided by/(used in) financing activities",
                        117,
                        "2,584",
                        "7,485",
                        "(3,205)",
                    ),
                    row(
                        "Effect of exchange rate changes on cash, cash equivalents, and restricted cash",
                        117,
                        "(104)",
                        "(458)",
                        "532",
                    ),
                ],
                "rhs": [
                    row(
                        "Net increase/(decrease) in cash, cash equivalents, and restricted cash",
                        117,
                        "(230)",
                        "(1,920)",
                        "560",
                    )
                ],
            },
            {
                "id": "FUN-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + net change = cash at end",
                "headers": ["2023", "2024", "2025"],
                "lhs": [
                    row(
                        "Cash, cash equivalents, and restricted cash at beginning of period",
                        117,
                        "25,340",
                        "25,110",
                        "23,190",
                    ),
                    row(
                        "Net increase/(decrease) in cash, cash equivalents, and restricted cash",
                        117,
                        "(230)",
                        "(1,920)",
                        "560",
                    ),
                ],
                "rhs": [
                    row(
                        "Cash, cash equivalents, and restricted cash at end of period",
                        117,
                        "25,110",
                        "23,190",
                        "23,750",
                    )
                ],
            },
        ],
    },
    "SIX22": {
        "unit": "USD thousands",
        "identities": [
            {
                "id": "SIX22-BS-1",
                "kind": "BS",
                "equation": "total assets = total liabilities + redeemable noncontrolling interests + total stockholders' deficit (the document's own grouping: redeemable NCI is between liabilities and stockholders' deficit)",
                "headers": ["January 2, 2022", "December 31, 2020"],
                "lhs": [row("Total assets", 93, "2,968,590", "2,772,691")],
                "rhs": [
                    row("Total liabilities", 93, "3,428,723", "3,407,862"),
                    row("Redeemable noncontrolling interests", 93, "522,067", "523,376"),
                    row("Total stockholders' deficit", 93, "(982,200)", "(1,158,547)"),
                ],
            },
            {
                "id": "SIX22-BS-2",
                "kind": "BS",
                "equation": "total assets = the printed total of liabilities and stockholders' deficit",
                "headers": ["January 2, 2022", "December 31, 2020"],
                "lhs": [row("Total assets", 93, "2,968,590", "2,772,691")],
                "rhs": [
                    row("Total liabilities and stockholders' deficit", 93, "2,968,590", "2,772,691")
                ],
            },
            {
                "id": "SIX22-CFS-1",
                "kind": "CFS",
                "equation": "operating + investing + financing + exchange-rate effect = net change in cash",
                "headers": ["January 2, 2022", "December 31, 2020", "December 31, 2019"],
                "lhs": [
                    row(
                        "Net cash provided by (used in) operating activities",
                        97,
                        "334,905",
                        "(190,880)",
                        "410,573",
                    ),
                    row(
                        "Net cash used in investing activities",
                        97,
                        "(121,701)",
                        "(90,894)",
                        "(139,126)",
                    ),
                    row(
                        "Net cash (used in) provided by financing activities",
                        97,
                        "(35,144)",
                        "266,721",
                        "(143,007)",
                    ),
                    row("Effect of exchange rate on cash", 97, "(235)", "(1,366)", "1,131"),
                ],
                "rhs": [
                    row(
                        "Net increase (decrease) in cash and cash equivalents",
                        97,
                        "177,825",
                        "(16,419)",
                        "129,571",
                    )
                ],
            },
            {
                "id": "SIX22-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + net change = cash at end",
                "headers": ["January 2, 2022", "December 31, 2020", "December 31, 2019"],
                "lhs": [
                    row(
                        "Cash and cash equivalents at beginning of period",
                        97,
                        "157,760",
                        "174,179",
                        "44,608",
                    ),
                    row(
                        "Net increase (decrease) in cash and cash equivalents",
                        97,
                        "177,825",
                        "(16,419)",
                        "129,571",
                    ),
                ],
                "rhs": [
                    row(
                        "Cash and cash equivalents at end of period",
                        97,
                        "335,585",
                        "157,760",
                        "174,179",
                    )
                ],
            },
        ],
    },
    "VMO2Q3": {
        "unit": "GBP millions",
        "identities": [
            {
                "id": "VMO2Q3-BS-1",
                "kind": "BS",
                "equation": "total assets (page 4) = total liabilities + total combined equity (page 5)",
                "headers": ["30 September 2025", "31 December 2024"],
                "lhs": [row("Total assets", 4, "46,576.8", "46,625.8")],
                "rhs": [
                    row("Total liabilities", 5, "26,938.7", "27,206.3"),
                    row("Total combined equity", 5, "19,638.1", "19,419.5"),
                ],
            },
            {
                "id": "VMO2Q3-BS-2",
                "kind": "BS",
                "equation": "total assets (page 4) = the printed total of equity and liabilities (page 5)",
                "headers": ["30 September 2025", "31 December 2024"],
                "lhs": [row("Total assets", 4, "46,576.8", "46,625.8")],
                "rhs": [row("Total equity and liabilities", 5, "46,576.8", "46,625.8")],
            },
            {
                "id": "VMO2Q3-CFS-1",
                "kind": "CFS",
                "equation": "operating (page 9) + investing (page 9) + financing (page 10) + exchange-rate effect = net change in cash",
                "headers": [
                    "Nine months ended 30 September 2025",
                    "Nine months ended 30 September 2024",
                ],
                "lhs": [
                    row("Net cash provided by operating activities", 9, "1,836.3", "1,514.4"),
                    row("Net cash used by investing activities", 9, "(533.2)", "(549.4)"),
                    row("Net cash used by financing activities", 10, "(1,345.0)", "(850.8)"),
                    row(
                        "Effect of exchange rate changes on cash and cash equivalents",
                        10,
                        "6.4",
                        "(1.3)",
                    ),
                ],
                "rhs": [
                    row(
                        "Net (decrease) increase in cash and cash equivalents",
                        10,
                        "(35.5)",
                        "112.9",
                    )
                ],
            },
            {
                "id": "VMO2Q3-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + net change = cash at end",
                "headers": [
                    "Nine months ended 30 September 2025",
                    "Nine months ended 30 September 2024",
                ],
                "lhs": [
                    row("Beginning of period", 10, "646.2", "243.1"),
                    row(
                        "Net (decrease) increase in cash and cash equivalents",
                        10,
                        "(35.5)",
                        "112.9",
                    ),
                ],
                "rhs": [row("End of period", 10, "610.7", "356.0")],
            },
        ],
    },
    "VMED25": {
        "unit": "GBP millions",
        "identities": [
            {
                "id": "VMED25-BS-1",
                "kind": "BS",
                "equation": "total assets (page 109) = total liabilities + total combined equity (page 110)",
                "headers": ["31 December 2025", "31 December 2024"],
                "lhs": [row("Total assets", 109, "38,117.9", "40,011.1")],
                "rhs": [
                    row("Total liabilities", 110, "27,341.5", "27,203.6"),
                    row("Total combined equity", 110, "10,776.4", "12,807.5"),
                ],
            },
            {
                "id": "VMED25-BS-2",
                "kind": "BS",
                "equation": "total assets (page 109) = the printed total of equity and liabilities (page 110)",
                "headers": ["31 December 2025", "31 December 2024"],
                "lhs": [row("Total assets", 109, "38,117.9", "40,011.1")],
                "rhs": [row("Total equity and liabilities", 110, "38,117.9", "40,011.1")],
            },
            {
                "id": "VMED25-CFS-1",
                "kind": "CFS",
                "equation": "operating (page 112) + investing (page 112) + financing (page 113) + exchange-rate effect = net change in cash",
                "headers": ["Year ended 31 December 2025", "Year ended 31 December 2024"],
                "lhs": [
                    row("Net cash provided by operating activities", 112, "2,763.1", "3,027.6"),
                    row("Net cash used by investing activities", 112, "(1,382.6)", "(1,509.9)"),
                    row("Net cash used by financing activities", 113, "(1,941.1)", "(1,276.9)"),
                    row(
                        "Effect of exchange rate changes on cash and cash equivalents",
                        113,
                        "5.8",
                        "11.9",
                    ),
                ],
                "rhs": [
                    row(
                        "Net (decrease) increase in cash and cash equivalents",
                        113,
                        "(554.8)",
                        "252.7",
                    )
                ],
            },
            {
                "id": "VMED25-CFS-2",
                "kind": "CFS",
                "equation": "cash at beginning + net change = cash at end",
                "headers": ["Year ended 31 December 2025", "Year ended 31 December 2024"],
                "lhs": [
                    row("Beginning of period", 113, "1,128.3", "875.6"),
                    row(
                        "Net (decrease) increase in cash and cash equivalents",
                        113,
                        "(554.8)",
                        "252.7",
                    ),
                ],
                "rhs": [row("End of period", 113, "573.5", "1,128.3")],
            },
        ],
    },
}


def value(printed: str) -> Decimal:
    s = printed.strip()
    if s in {"—", "-"}:
        return Decimal(0)
    neg = s.startswith("(") and s.endswith(")")
    num = Decimal(re.sub(r"[(),\s]", "", s))
    return -num if neg else num


def check_row(doc: str, r: dict) -> None:
    text = (PAGES / doc / f"p{r['page']:03d}.txt").read_text("utf-8")
    for line in text.split("\n"):
        i = line.find(r["label"])
        if i < 0:
            continue
        pos = i + len(r["label"])
        ok = True
        for p in r["printed"]:
            j = line.find(p, pos)
            if j < 0:
                ok = False
                break
            pos = j + len(p)
        if ok:
            return
    raise AssertionError(f"{doc} p{r['page']}: no line with {r['label']!r} and {r['printed']}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for doc, spec in SPECS.items():
        manifest = json.loads((PAGES / doc / "manifest.json").read_text("utf-8"))
        idents = []
        for ident in spec["identities"]:
            n = len(ident["headers"])
            for side in ("lhs", "rhs"):
                for r in ident[side]:
                    assert len(r["printed"]) == n, (ident["id"], r["label"])
                    check_row(doc, r)
            columns = []
            for c, header in enumerate(ident["headers"]):
                lhs = sum(value(r["printed"][c]) for r in ident["lhs"])
                rhs = sum(value(r["printed"][c]) for r in ident["rhs"])
                assert lhs == rhs, (ident["id"], header, lhs, rhs)
                columns.append(
                    {
                        "header_text": header,
                        "lhs_sum": str(lhs),
                        "rhs_sum": str(rhs),
                        "values": {
                            r["label"]: str(value(r["printed"][c]))
                            for r in ident["lhs"] + ident["rhs"]
                        },
                    }
                )
            idents.append(
                {
                    "id": ident["id"],
                    "kind": ident["kind"],
                    "equation": ident["equation"],
                    "lhs": ident["lhs"],
                    "rhs": ident["rhs"],
                    "columns": columns,
                }
            )
        out = {
            "schema": "pdf-identities/1",
            "doc": doc,
            "source_name": manifest["source_name"],
            "source_sha256": manifest["source_sha256"],
            "unit": spec["unit"],
            "note": "label and page name a row of tests/fixtures/pdf_pages/<doc>/pNNN.txt; printed values are in column order; each identity is lhs sum == rhs sum, exact, per column",
            "identities": idents,
        }
        (OUT / f"{doc}.json").write_text(
            json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8"
        )
        print(doc, len(idents), "identities")


main()
