# PDF unit, identity and column-period answer keys (CP1H-R23, task F1)

Prepared for the builders of T19, T20 and T21. Written by the preparer from the text of the documents only: no product code (`financial_workflow.py`'s unit locator, `statement_extract.py`'s parser) was read or run. Frozen once reviewed; builders do not edit these files.

Page numbers are the intake locator `page:N` (1-based PDF page index), not the printed folio.

## Files

| Path | What it is | Made by |
|---|---|---|
| `tests/fixtures/pdf_pages/<DOC>/pNNN.txt` | The exact `text` of span `page:NNN` of the product intake (deploy_vii preparation, pypdf 6.21.2), written as UTF-8 bytes unchanged. 59 pages over six documents. | `cases/pdf-units/make_pages.py <dir of DOC.source.json>` |
| `tests/fixtures/pdf_pages/<DOC>/manifest.json` | `{source_name, source_sha256, extractor, pages: {"NNN": sha256 of the file}}` | same script |
| `cases/pdf-units/<DOC>.json` | The true primary-statement units (BS, IS, CI, SE, CFS): title as printed (and its lines), pages including continuation pages, a `basis` note, and `not_units` (fixture pages that look like a statement but are not, each with the reason). `fixture_pages_not_listed` is empty: every fixture page is a unit page or a listed `not_unit`. | `cases/pdf-units/make_units.py` (checks each printed title line occurs on its first page) |
| `cases/pdf-identities/<DOC>.json` | Exact arithmetic identities: BS (assets = liabilities + equity, and assets = the printed total row), CFS (operating + investing + financing + FX effect where printed = net change; opening + change = closing). Row labels as printed, the page, printed values in column order, and the expected sums per column in Decimal strings. | `cases/pdf-identities/make_identities.py` (aborts unless each label and its printed values occur together on a line of the named page and every identity holds exactly) |
| `cases/column-periods/SHC.json`, `TDG.json` | Column to period oracle for every statement unit (BS, IS, CFS) of `cases/statement-rows` for SHC (6 units, 16 columns) and TDG (12 units, 30 columns), in printed column order. Key: `<source_id>\|<kind>\|line:S-line:E`. | `cases/column-periods/make_column_periods.py` |

Counts: units 5 per document (30 total); identities TDG 4, CZR 5, FUN 4, SIX22 4, VMO2Q3 4, VMED25 4 (25 total); pages TDG 9, CZR 10, FUN 8, SIX22 9, VMO2Q3 10, VMED25 13.

## Facts the builders must not assume away

- `FUN` is Ford Motor Company's FY2025 10-K (`f-20251231.pdf`, "FORD MOTOR COMPANY AND SUBSIDIARIES"). The brief and the pre-flight call it "Six Flags 2025 10-K"; the text is Ford's. The Six Flags 10-K is `SIX22`.
- FUN prints the income statement and the comprehensive income statement on one page (p115), so two units share a page. Its IS and CI columns run oldest to newest (2023, 2024, 2025); its BS columns are 2024, 2025.
- Statements span two pages in VMO2Q3 (BS 4-5, CFS 9-10) and VMED25 (BS 109-110, CFS 112-113); the second page repeats the title with "continued". Titles can be two or three lines ("Condensed Consolidated Statements" / "of Financial Position (unaudited)"). IFRS income statements are titled "Profit or (Loss)".
- CZR's CFS continues on p61 with no title; p61 is in the unit (ruled: repeated column header, the 'accompanying notes' line only on p61, reconciliation ties to closing cash).
- SIX22's balance sheet puts "Redeemable noncontrolling interests" between liabilities and stockholders' deficit, so SIX22-BS-1 adds three terms.
- CZR prints no exchange-rate row in its CFS, so CZR-CFS-1 has three terms.
- FUN's "Net increase/(decrease) in cash, cash equivalents, and restricted cash" is printed twice on p117 with the same values (once before the opening balance and once after).
- TDG column header text: the two-line BS header on p105 is `2024 2023` with the date only in the title ("AS OF SEPTEMBER 30, 2024 AND 2023").

## Limits

- Units, `not_units` and identities are for the six documents and the fixture pages only. Pages not in a fixture folder are not judged. A page listed under `not_units` is judged only as the text of that page.
- Identity values are as printed, in the statement's own unit (USD millions for TDG, CZR, FUN; USD thousands for SIX22; GBP millions for VMO2Q3, VMED25). The key checks arithmetic on printed numbers; it does not say the pypdf text order is right for any other cell.
- Income statements have no identity (no check exists in the brief).
- Column periods exist only for SHC and TDG (the frozen statement-rows documents). They were read from the header lines of the converted HTML text (line numbers of the repo's `convert_html` output at the statement-rows key).
- A pre-flight fix census (`work/build/cp1h/preflight-pdf.md`) is not an input; nothing here was derived from it.

## `uncertain` entries

1. `VMED25.json` not_units p172 and p173 were ruled out of units (company-only statements of a separate entity, own notes p174-176, no income or cash flow statement); no longer uncertain.
2. `TDG.json` (column-periods), every week-based column (Q2FY24, Q3FY24 and Q1FY25, IS and CFS): `start` is null with `uncertain`: "start not printed; week counts back from the end date conflict with the October 1 fiscal-year start for some columns". Tests compare `kind` and `end` only.

Column-period kinds: instant, quarter, half, nine_months, year. The four TDG thirty-nine-week columns use `nine_months`.
