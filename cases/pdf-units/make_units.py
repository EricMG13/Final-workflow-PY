"""Write cases/pdf-units/<DOC>.json: the true primary-statement units of six real PDFs.

Run from the repo root: python3 -I cases/pdf-units/make_units.py

Answer key (CP1H-R23, F1). Every entry is the preparer's own reading of the page text in
tests/fixtures/pdf_pages/<DOC>/pNNN.txt. No product code was read or run. The script only checks
that each printed title line it records occurs in the fixture page it names.

Page numbers are the PDF page index in the intake ("page:N"), not the printed folio.
Kinds: BS balance sheet / statement of financial position; IS income statement / statement of
operations / profit or (loss); CI statement of comprehensive income; CFS cash flows;
SE changes in equity.
"""

import json
from pathlib import Path

ROOT = Path(".")
PAGES = ROOT / "tests" / "fixtures" / "pdf_pages"
OUT = ROOT / "cases" / "pdf-units"

# Each unit: kind, title_lines (printed, in order, on the first page), pages, basis, optional
# continuation {page: how the continuation shows}, optional uncertain.
DOCS = {
    "TDG": {
        "document": "TransDigm Group FY2024 annual report (10-K, fiscal year ended 30 Sep 2024)",
        "units": [
            {
                "kind": "BS",
                "title_lines": ["CONSOLIDATED BALANCE SHEETS"],
                "pages": [105],
                "basis": "Title line 2 of p105 (printed F-3), upper case, followed by 'AS OF SEPTEMBER 30, 2024 AND 2023'; the table ends with TOTAL LIABILITIES AND STOCKHOLDERS' DEFICIT on the same page.",
            },
            {
                "kind": "IS",
                "title_lines": ["CONSOLIDATED STATEMENTS OF INCOME"],
                "pages": [106],
                "basis": "Title line 2 of p106 (F-4); NET SALES through NET INCOME ATTRIBUTABLE TO TD GROUP and per-share data on the one page.",
            },
            {
                "kind": "CI",
                "title_lines": ["CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME"],
                "pages": [107],
                "basis": "Title line 2 of p107 (F-5); starts from Net income, ends at TOTAL COMPREHENSIVE INCOME ATTRIBUTABLE TO TD GROUP.",
            },
            {
                "kind": "SE",
                "title_lines": ["CONSOLIDATED STATEMENTS OF CHANGES IN STOCKHOLDERS’ DEFICIT"],
                "pages": [108],
                "basis": "Title line 2 of p108 (F-6); three fiscal years of BALANCE rows, ends at BALANCE—September 30, 2024.",
            },
            {
                "kind": "CFS",
                "title_lines": ["CONSOLIDATED STATEMENTS OF CASH FLOWS"],
                "pages": [109],
                "basis": "Title line 2 of p109 (F-7); operating, investing and financing sections and the cash roll all on the one page.",
            },
        ],
        "not_units": [
            {
                "page": 62,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 15(a)(1) list of the statements with F-page numbers; dot leaders and page numbers, no statement data.",
            },
            {
                "page": 101,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 8 / Item 15(a)(1) index page of the F-pages; titles and page references only.",
            },
            {
                "page": 104,
                "looks_like": "none (page before the BS)",
                "reason": "Tail of the auditor's report (critical audit matter on goodwill, signature, F-2); prose.",
            },
            {
                "page": 110,
                "looks_like": "mentions 'consolidated statements of income'",
                "reason": "Notes to the financial statements, Note 1 text (F-8); lower-case references inside sentences.",
            },
        ],
    },
    "CZR": {
        "document": "Caesars Entertainment FY2025 10-K (year ended 31 Dec 2025)",
        "units": [
            {
                "kind": "BS",
                "title_lines": ["CONSOLIDATED BALANCE SHEETS"],
                "pages": [56],
                "basis": "Title line 2 of p56 (folio 56) under the company name; assets, liabilities and equity on the one page; ends with Total liabilities and stockholders’ equity.",
            },
            {
                "kind": "IS",
                "title_lines": ["CONSOLIDATED STATEMENTS OF OPERATIONS"],
                "pages": [57],
                "basis": "Title line 2 of p57 (folio 57); NET REVENUES to per-share and share counts on the one page.",
            },
            {
                "kind": "CI",
                "title_lines": ["CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME (LOSS)"],
                "pages": [58],
                "basis": "Title line 2 of p58 (folio 58); a short table from Net income (loss) to Comprehensive income (loss) attributable to Caesars. This is the unit the pre-flight said the locator missed.",
            },
            {
                "kind": "SE",
                "title_lines": ["CONSOLIDATED STATEMENTS OF STOCKHOLDERS’ EQUITY"],
                "pages": [59],
                "basis": "Title line 2 of p59 (folio 59); Balance rows for 1 Jan 2023 through 31 Dec 2025.",
            },
            {
                "kind": "CFS",
                "title_lines": ["CONSOLIDATED STATEMENTS OF CASH FLOWS"],
                "pages": [60, 61],
                "continuation": {
                    "61": "No title. The header 'Years Ended December 31,' and '(In millions) 2025 2024 2023' repeat at the top, then the cash reconciliation and the supplemental and non-cash disclosures, then the folio 61 note line."
                },
                "basis": "Title line 2 of p60 (folio 60). The operating, investing and financing sections end on p60 with 'Cash, cash equivalents and restricted cash, end of period'. p61 continues the same table (repeated column header, no new title). p61 belongs to the statement because it repeats the column header, because the 'accompanying notes are an integral part' line appears only on p61 (not on p60), and because p61's reconciliation ties to the closing cash printed on p60 (identity CZR-CFS-3).",
            },
        ],
        "not_units": [
            {
                "page": 53,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 8 index to the consolidated financial statements: titles with page numbers 56 to 60.",
            },
            {
                "page": 55,
                "looks_like": "none (page before the BS)",
                "reason": "Tail of the auditor's report (critical audit matter, signature); prose.",
            },
            {
                "page": 62,
                "looks_like": "mentions 'Consolidated Balance Sheets', 'Statements of Operations', 'Statements of Cash Flows'",
                "reason": "Page after the CFS continuation: first page of Notes to Consolidated Financial Statements, defines the terms; no data table.",
            },
            {
                "page": 101,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 15(a)(i) list of the statements included in Item 8; titles and period words only.",
            },
        ],
    },
    "FUN": {
        "document": "Ford Motor Company FY2025 10-K (year ended 31 Dec 2025). The brief and the pre-flight call this document 'Six Flags 2025 10-K'; its text is Ford's (f-20251231.pdf, FORD MOTOR COMPANY AND SUBSIDIARIES).",
        "units": [
            {
                "kind": "IS",
                "title_lines": ["CONSOLIDATED INCOME STATEMENTS"],
                "pages": [115],
                "basis": "Title near the top of p115 (printed 111). Revenues to diluted shares, then the next statement title follows on the same page.",
            },
            {
                "kind": "CI",
                "title_lines": ["CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME"],
                "pages": [115],
                "basis": "Second title in the lower half of p115 (about line 39 of the page text), after the income statement's per-share and share rows; from Net income/(loss) to Comprehensive income/(loss) attributable to Ford Motor Company. Two units share this page.",
            },
            {
                "kind": "BS",
                "title_lines": ["CONSOLIDATED BALANCE SHEETS"],
                "pages": [116],
                "basis": "Title near the top of p116 (printed 112). The VIE table below it (assets and liabilities of consolidated variable interest entities) is a memo table, not part of the balance sheet columns.",
            },
            {
                "kind": "CFS",
                "title_lines": ["CONSOLIDATED STATEMENTS OF CASH FLOWS"],
                "pages": [117],
                "basis": "Title near the top of p117 (printed 113); all three sections and the cash roll on the one page.",
            },
            {
                "kind": "SE",
                "title_lines": ["CONSOLIDATED STATEMENTS OF EQUITY"],
                "pages": [118],
                "basis": "Title near the top of p118 (printed 114); balances at 31 Dec 2022 to 31 Dec 2025, footnotes (a) and (b), then the 'accompanying notes' line.",
            },
        ],
        "not_units": [
            {
                "page": 4,
                "looks_like": "mentions of income statements, balance sheets",
                "reason": "Table of contents of the 10-K (MD&A items with page numbers). No statement data.",
            },
            {
                "page": 104,
                "looks_like": "list of the five statements",
                "reason": "Item 15(a)1 bullet list of the financial statements included; titles with period words only.",
            },
            {
                "page": 114,
                "looks_like": "none (page before the income statement)",
                "reason": "Tail of the auditor's report (critical audit matters, warranty and finance receivables); prose.",
            },
            {
                "page": 119,
                "looks_like": "none (page after the SE)",
                "reason": "Notes to the Financial Statements, table of contents of the notes; no statement data.",
            },
        ],
    },
    "SIX22": {
        "document": "Six Flags Entertainment Corporation 10-K for the year ended 2 Jan 2022 (printed from sec.gov HTML)",
        "units": [
            {
                "kind": "BS",
                "title_lines": ["Consolidated Balance Sheets"],
                "pages": [93],
                "basis": "Title case, after the company name on p93 (folio 52); 'As of' header over January 2, 2022 and December 31, 2020; ends with Total liabilities and stockholders' deficit.",
            },
            {
                "kind": "IS",
                "title_lines": ["Consolidated Statements of Operations"],
                "pages": [94],
                "basis": "Title case, p94 (folio 53); three years January 2, 2022, December 31, 2020, December 31, 2019.",
            },
            {
                "kind": "CI",
                "title_lines": ["Consolidated Statements of Comprehensive Income (Loss)"],
                "pages": [95],
                "basis": "Title case, p95 (folio 54); Net income (loss) to Comprehensive income (loss) attributable to Six Flags Entertainment Corporation, then footnotes (1) to (3).",
            },
            {
                "kind": "SE",
                "title_lines": ["Consolidated Statements of Equity (Deficit)"],
                "pages": [96],
                "basis": "Title case, p96 (folio 55); balances at December 31, 2018 through January 2, 2022.",
            },
            {
                "kind": "CFS",
                "title_lines": ["Consolidated Statements of Cash Flows"],
                "pages": [97],
                "basis": "Title case, p97 (folio 56); the three sections and the cash roll on the one page.",
            },
        ],
        "not_units": [
            {
                "page": 86,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 8 'Index to Consolidated Financial Statements' with folio numbers 52 to 56.",
            },
            {
                "page": 92,
                "looks_like": "none (page before the BS)",
                "reason": "Tail of the auditor's report (KPMG, tenure line); no data.",
            },
            {
                "page": 98,
                "looks_like": "none (page after the CFS)",
                "reason": "Note 1 'Description of Business', prose.",
            },
            {
                "page": 160,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Item 15(a)(1) and (2) list of the financial statements with folio numbers.",
            },
        ],
    },
    "VMO2Q3": {
        "document": "VMED O2 UK Holdings Limited condensed consolidated IFRS quarterly bond report, 30 Sep 2025 (nine months)",
        "units": [
            {
                "kind": "BS",
                "title_lines": [
                    "Condensed Consolidated Statements",
                    "of Financial Position (unaudited)",
                ],
                "pages": [4, 5],
                "continuation": {
                    "5": "Title repeated on two lines as 'Condensed Consolidated Statements' / 'of Financial Position (unaudited) – continued'; liabilities and equity side."
                },
                "basis": "Two-line title on p4 (folio 4) with assets down to Total assets. p5 carries the same title with '– continued' and the liabilities and equity down to Total equity and liabilities. The statement is a two-page table.",
            },
            {
                "kind": "IS",
                "title_lines": [
                    "Condensed Consolidated Statements",
                    "of Profit or (Loss) (unaudited)",
                ],
                "pages": [6],
                "basis": "Two-line title on p6 (folio 6); the income statement is called 'Profit or (Loss)'; columns three months 2025 and 2024, nine months 2025 and 2024.",
            },
            {
                "kind": "CI",
                "title_lines": [
                    "Condensed Consolidated Statements",
                    "of Comprehensive Income (Loss)",
                    "(unaudited)",
                ],
                "pages": [7],
                "basis": "Three-line title on p7 (folio 7); Net profit to Comprehensive income, split Owners and NCI.",
            },
            {
                "kind": "SE",
                "title_lines": [
                    "Condensed Consolidated Statements",
                    "of Changes in Equity (unaudited)",
                ],
                "pages": [8],
                "basis": "Two-line title on p8 (folio 8); balances at 1 January 2025 onward.",
            },
            {
                "kind": "CFS",
                "title_lines": [
                    "Condensed Consolidated Statements",
                    "of Cash Flows (unaudited)",
                ],
                "pages": [9, 10],
                "continuation": {
                    "10": "Title repeated as 'of Cash Flows (unaudited) – continued'; financing section, FX effect and the cash roll."
                },
                "basis": "Two-line title on p9 (folio 9) with operating and investing sections; p10 repeats the title with '– continued' and holds financing, the exchange effect, net change and the opening and closing cash.",
            },
        ],
        "not_units": [
            {
                "page": 2,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Contents page listing the condensed statements and notes with page numbers.",
            },
            {
                "page": 3,
                "looks_like": "none",
                "reason": "Divider page headed 'Condensed Consolidated Financial Statements'; no data.",
            },
            {
                "page": 11,
                "looks_like": "none (page after the CFS)",
                "reason": "Note 1 'Basis of Presentation', two-column prose; mentions 'consolidated statements of profit or (loss)' in a sentence.",
            },
        ],
    },
    "VMED25": {
        "document": "VMED O2 UK Limited 2025 Annual Report and Consolidated Financial Statements (year ended 31 Dec 2025)",
        "units": [
            {
                "kind": "IS",
                "title_lines": ["Consolidated Statements of Profit or (Loss)"],
                "pages": [107],
                "basis": "Title on p107 (folio 107) after the running header; Revenue to Net loss, split Owners and NCI; the income statement is called 'Profit or (Loss)'.",
            },
            {
                "kind": "CI",
                "title_lines": ["Consolidated Statements of Comprehensive Income (Loss)"],
                "pages": [108],
                "basis": "Title on p108 (folio 108); Net loss to Comprehensive loss, split Owners and NCI.",
            },
            {
                "kind": "BS",
                "title_lines": ["Consolidated Statements of Financial Position"],
                "pages": [109, 110],
                "continuation": {
                    "110": "Title repeated as 'Consolidated Statements of Financial Position (continued)'; liabilities and equity, then the board approval note."
                },
                "basis": "p109 (folio 109) holds assets down to Total assets. p110 repeats the title with '(continued)' and holds liabilities and equity down to Total equity and liabilities.",
            },
            {
                "kind": "SE",
                "title_lines": ["Consolidated Statements of Changes in Equity"],
                "pages": [111],
                "basis": "Title on p111 (folio 111); two blocks, the year 2025 (1 January 2025 to 31 December 2025) and the year 2024, on the one page.",
            },
            {
                "kind": "CFS",
                "title_lines": ["Consolidated Statements of Cash Flows"],
                "pages": [112, 113],
                "continuation": {
                    "113": "Title repeated as 'Consolidated Statements of Cash Flows (continued)'; financing section, FX effect and the cash roll."
                },
                "basis": "p112 (folio 112) holds operating and investing; p113 repeats the title with '(continued)' and holds financing, the exchange effect, net change and opening and closing cash.",
            },
        ],
        "not_units": [
            {
                "page": 2,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Annual report contents page, titles with page numbers 107 to 112, plus the company statements.",
            },
            {
                "page": 34,
                "looks_like": "CFS: 'Consolidated Statements of Cash Flows' heading and the net cash rows",
                "reason": "Financial Review (MD&A): a summarised table of net cash flows and prose; not the primary statement. It names 'page 112' for the real statement.",
            },
            {
                "page": 106,
                "looks_like": "BS, IS, CI, SE, CFS titles",
                "reason": "Contents list of the Financial Statements section with folio numbers.",
            },
            {
                "page": 114,
                "looks_like": "none (page after the CFS)",
                "reason": "Notes to the Consolidated Financial Statements, Note 1 'Basis of Presentation', prose.",
            },
            {
                "page": 172,
                "looks_like": "BS: 'Company Statements of Financial Position'",
                "reason": "Ruling: company-only statements of a separate entity (the parent), with their own notes (p174-176), and no income statement or cash flow statement. They are not the group's primary statements, and a locator must not emit them as units.",
            },
            {
                "page": 173,
                "looks_like": "SE: 'Company Statements of Changes in Equity'",
                "reason": "Ruling: company-only statements of a separate entity (the parent), with their own notes (p174-176), and no income statement or cash flow statement. They are not the group's primary statements, and a locator must not emit them as units.",
            },
        ],
    },
}


def page_text(doc: str, n: int) -> str:
    return (PAGES / doc / f"p{n:03d}.txt").read_text("utf-8")


def squash(s: str) -> str:
    return " ".join(s.split())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for doc, spec in DOCS.items():
        manifest = json.loads((PAGES / doc / "manifest.json").read_text("utf-8"))
        have = {int(k) for k in manifest["pages"]}
        units = []
        for u in spec["units"]:
            for p in u["pages"]:
                assert p in have, (doc, p)
            first = squash(page_text(doc, u["pages"][0]))
            for line in u["title_lines"]:
                assert squash(line) in first, (doc, u["kind"], line)
            for p in u.get("continuation", {}):
                assert int(p) in u["pages"]
            entry = {
                "kind": u["kind"],
                "title_as_printed": " ".join(u["title_lines"]),
                "title_lines": u["title_lines"],
                "pages": u["pages"],
                "basis": u["basis"],
            }
            if "continuation" in u:
                entry["continuation"] = u["continuation"]
            if "uncertain" in u:
                entry["uncertain"] = u["uncertain"]
            units.append(entry)
        for n in spec["not_units"]:
            assert n["page"] in have, (doc, n["page"])
        covered = {p for u in units for p in u["pages"]} | {n["page"] for n in spec["not_units"]}
        context_only = sorted(have - covered)
        out = {
            "schema": "pdf-units/1",
            "doc": doc,
            "document": spec["document"],
            "source_name": manifest["source_name"],
            "source_sha256": manifest["source_sha256"],
            "page_numbering": "page N = the intake locator page:N (1-based PDF page index), not the printed folio",
            "units": units,
            "not_units": spec["not_units"],
            "fixture_pages_not_listed": context_only,
        }
        (OUT / f"{doc}.json").write_text(
            json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8"
        )
        print(doc, len(units), "units", len(spec["not_units"]), "not_units", context_only)


main()
