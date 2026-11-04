---
module_id: CP-0
aliases_exercised: [CP-PARSE]
run_id: erste-parse-2024-001
issuer_id: ERSTE
issuer_name: Erste Group Bank AG
execution: current_host_model_with_preceding_context
source_as_of: 2024-12-31
status: ready_with_limitations_for_named_statement_intake
---

# CP-0 — historical Erste source preparation and readiness

## Request

Prepare the issuer-linked FY2024/comparative2023 income, balance-sheet and
cash-flow spreadsheets for CP-1. Run CP-PARSE as CP-0's absorbed preparation
phase, then judge readiness for the named statement intake. Actual current
host-model analysis with local tools; preceding context was available. No
provider, subagent, formula execution or workbook output.

**Result: ready with limitations for source-checked statement intake.** The
three spreadsheets can be read exactly, but several stored numbers conflict
with the corresponding issuer PDF. No blanket monetary import or rescaling is
permitted. The added, separately identified PDF supports the selected primary
statement observations after original-image/column checks. This does not
establish complete bank underwriting, capital adequacy or current conditions.

## Sources

All originals remain under `sources/`; exact URLs, byte sizes and hashes are
in `source-retrieval-with-pdf.json`. The issuer's annual-report download page
links the three statements and the Group Consolidated Financial Statements.
This provenance is stronger than a filename, but is not a new regulatory
filing/authenticity or post-publication amendment search.

| Source | Original | SHA-256 | Located identity and scope |
|---|---|---|---|
| W1 | AR24_Statement_of_income.xlsx | fb6f776a097c94382f21f2287cf2add54f141971d7ab01eadf9947dc2f0dbf29 | Tabelle1!A1: consolidated income statement; A3: EUR million; C3/D3: 1-12 23 / 1-12 24. EPS subsection has EUR thousand, individual shares and EUR per share. |
| W2 | AR24_Balancesheet.xlsx | 0ed7090071cd2b347e271d841fba75e0b0df74d4fd63ae956bd3de57b4413876 | Tabelle1!A1: consolidated balance sheet; A3/A38: EUR million; C3/D3 and C38/D38: Dec 23 / Dec 24 instants. |
| W3 | AR24_Cashflows.xlsx | a36a4c8bc09f31f2544e9e8eed3d70678b679f4d203d09ca88bec0e9380f690d | Tabelle1!A1: consolidated cash flows; A3: EUR million; C3/D3: 1-12 23 / 1-12 24. A64 defines its cash-equivalent/balance-sheet relationship. |
| P1 | AR2024_Group_Consolidated_Financial_Statements_en.pdf | fcb15a4a4ee76cfd1ae0142bbeaf1b0950bfa35c92626acee8791316ed707087 | PDF p.9/printed242 names Erste Group Bank AG and its group; FY ending31 December2024 and comparatives, EU-adopted IFRS. Selected statement images: PDF3/5/8, printed236/238/241. |

The embedded images in W1–W3 were inspected and show the Erste Group logo.
Their document creator/company metadata is not the issuer-identity oracle.
P1 p.9 establishes the group/parent distinction. Its authorisation paragraph
describes the report's then-status and potential later approvals; this check
does not infer that later approval or absence of revisions. Except for stated
exceptions, P1 uses millions of euro and allows rounding differences. The
management statements about restrictions are not a verified liquidity opinion.

## Findings

### Preparation and source fidelity

The existing `deploy_vii.preparation.xlsx_content` read all three supplied
sheets. Independent raw-OOXML reads matched **654 stored cells** exactly:
149 W1,258 W2,247 W3, including72 stored empty cells. Two merged-range metadata
spans bring the extracted span count to656. No formula, formula cache, comment,
macro, external-link part, hidden sheet/row/column or filter was observed.
Named ranges and merged ranges are retained in prepared Markdown. No Excel
application, external link or formula was launched.

Exact extraction is not equivalent to valid financial amounts. For example:

| Source cell / PDF row | Stored spreadsheet text | Separate PDF observation | Disposition |
|---|---|---|---|
| W1 Tabelle1!D4; P1 PDF3/printed236 net interest income,1-12 24 | 7.5279999999999996 | 7,528 under EUR million | Conflicting representations; retain both, do not repair/rescale W1. |
| W2 Tabelle1!D36; P1 PDF5/printed238 total assets,Dec 24 | 353.73599999999999 | 353,736 under EUR million | Same restriction; the PDF observation has its own source identity. |
| W3 Tabelle1!D33; P1 PDF8/printed241 operating cash flow,1-12 24 | -9.0289999999999999 | -9,029 under EUR million | Preserve sign and conflict; no derived replacement. |

These discrepancies exist in original workbook XML. The parser did not create
them. Some other source cells match the PDF, including literal zero; a uniform
multiplier would damage those cells. CP-1 must check the individual figure,
quantity family, period and source rather than infer a general conversion.

P1's selected original images were inspected. Its raw text contains private-use
font glyphs: the inspected grouping comma, decimal point and colon are not
ordinary ASCII in the extraction. Prepared P1 Markdown retains that text
unchanged and records the limitation. Original images and printed/PDF page maps
remain available in `preparation/P1/`. Text count alone is not visual proof.

### Analytical appendix — complete canonical registers

#### P1 — Pipeline

One CP-0 run, preparation then readiness. Scope: three full supplied spreadsheet
sheets plus P1 PDF pages3,5,8,9 for statement/source comparison. Four checked
prepared representations; one validated supporting Markdown ZIP. Source
conflicts restrict use, not faithful packaging of the conflicted evidence.

#### P2 — Workspace and immutability

Originals: `sources/`. Derivatives: `preparation/` and `package/`. Original
hashes were checked before and after ingestion. Original spreadsheets were
never saved/recalculated. `instructions.md` and `triage-frozen.json` remain
retained; `instructions-2.md` and `triage-frozen-2.json` explicitly add P1 after
the surprising original lexemes were observed. No predecessor was edited.

#### P3 — Input inventory and version map

The four-source table above is the complete effective pack. W1/W2/W3 are
complementary statement downloads, not duplicates. P1 is the corresponding
broader report presentation, retained separately, not a replacement of workbook
bytes. All four hashes differ. No supplied legal amendment, draft/final pair,
restatement or inaccessible original is invented. Workbook metadata dates are
March2025 file-edit metadata, not FY periods or proof of publication/approval.
All four sources are English. Each workbook has one visible `Tabelle1`; P1
contains170 PDF pages. Source age is explicit: historical2024, not current2026.

#### P4 — Frozen triage

| Source | Evidence | Authority/uniqueness | Structure | Duplicate penalty | Total | Decision / mode |
|---|---|---|---|---|---|---|
| W1 | 4 | 2 | 1 | 0 | 7 | PARSE_FULL; SHEET_RANGE/TABLE_FIRST |
| W2 | 4 | 2 | 1 | 0 | 7 | PARSE_FULL; SHEET_RANGE/TABLE_FIRST |
| W3 | 4 | 2 | 1 | 0 | 7 | PARSE_FULL; SHEET_RANGE/TABLE_FIRST |
| P1 | 5 | 3 | 2 | 0 | 10 | PARSE_TARGETED; TABLE_FIRST/LAYOUT_TEXT plus original-image check |

Selection follows the requested evidence, not length. No user include/exclude
override. No skipped duplicate, low-value or blocked access source within this
effective pack. Failed TDG/EPD retrieval attempts supplied no bytes to this case
and are recorded separately in retrieval provenance.

#### P5 — Parse jobs and coverage

| Source | Retained/examined | Excluded/unreadable | Fidelity / limits |
|---|---|---|---|
| W1 | One sheet,Tabelle1!A1:D43;149 cells; merged A32:D32; all headers/notes read | No supplied sheet/range excluded or unreadable; absent cells stay absent | Exact stored data checked; source numeric conflicts; native Excel display geometry unverified. |
| W2 | One sheet,Tabelle1!A1:D66;258 cells; no merge; all rows read | None | Same numeric restriction; raw empty is not zero. |
| W3 | One sheet,Tabelle1!A1:D64;247 cells; merged A64:D64; all rows/footnote read | None | Same numeric restriction; cash-flow sign/definition retained. |
| P1 | Four selected PDF pages:3,5,8,9; text and source images examined |166 pages outside targeted scope:1–2,4,6–7,10–170; no unreadable selected page | Selected statement fidelity checked; raw font glyphs retained; no full annual/notes review. |

Coverage reconciles per source/unit. Retaining every stored cell does not imply
every number is economically correct. Notes references remain references; the
referenced notes were not all reviewed. The two source merges do not create
values in their empty covered cells. Workbook logos were examined; no evidence
chart or analytical slide was identified in these three supplied workbooks.

#### P6 — Prepared-artifact register

| Source | Canonical prepared Markdown inside the package |
|---|---|
| W1 | parsed/W1/W1_CP-PARSE_20261104.md |
| W2 | parsed/W2/W2_CP-PARSE_20261104.md |
| W3 | parsed/W3/W3_CP-PARSE_20261104.md |
| P1 | parsed/P1/P1_CP-PARSE_20261104.md |

Every source block/table has sheet/cell/range or PDF/printed-page locators.
`BATCH_INDEX.md` records exact prepared-file hashes; `CHECKSUMS.sha256` covers
all seven Markdown members. Raw extraction JSON is a reading/check aid, not
an extra analytical handoff or an issuer authority.

#### P7 — Representation catalog

| Retained logical source | Single ACTIVE_CONTENT | Original role | Permitted use |
|---|---|---|---|
| W1 | Prepared W1 Markdown | Authority/provenance of stored spreadsheet content | Structure, labels and source quotations; each numeric use needs separate PDF check. |
| W2 | Prepared W2 Markdown | Same | Same; preserve instant periods and zeros. |
| W3 | Prepared W3 Markdown | Same | Same; preserve signed cash flows and source footnote. |
| P1 | Prepared targeted P1 Markdown, with explicit original-image check requirement | Independent report presentation, not workbook fallback | Selected source-verified statements/basis; unreviewed pages cannot support conclusions. |

No source has two active prepared representations. The original remains
verification provenance; consulting its image does not make a second active
analytical artifact. No required failed parse is silently bypassed.

#### P8 — Package and QA

[ERSTE_CP-PARSE_20261104_BATCH-001-of-001.zip](ERSTE_CP-PARSE_20261104_BATCH-001-of-001.zip)
has eight members: four prepared Markdown files, PACKAGE_INDEX.md,
TRIAGE_REGISTER.md, BATCH_INDEX.md and CHECKSUMS.sha256. Uncompressed116,303
bytes; one batch within20-source/250MB limits; each source output set occurs
exactly once. Originals, generated workbooks, executables and nested ZIPs are
absent. Safe relative paths, unique members, exact archived bytes, all seven
checksums and batch reconciliation passed.

ZIP SHA-256: `5160e6f2d2af0dab433586c0213e04695e8f33cddd3a2830b0ada7dd47800516`.
Inventory, original hashes, identity/period map, triage, locators, raw fidelity,
coverage and representation uniqueness passed for the named scope. Numerical
source agreement is restricted as above; no false financial acceptance follows
from the package pass. Unexercised scan/OCR, slide, legal amendment and
multi-batch cases are not claimed by this run.

## Calculations

Not applicable to CP-0. No financial normalization, multiplication, ratio,
reconciliation or credit calculation. Hash/count/score/checksum checks concern
preparation only. The conflict table quotes distinct source representations.

## Gaps

| ID | Affected work | Required action |
|---|---|---|
| G1 | Automatic financial import from W1/W2/W3; source decimals conflict with corresponding PDF numbers | Retain raw cells. For each selected financial observation, check the original PDF row/column and cite it separately. Do not apply a blanket multiplier or overwrite workbook cells. |
| G2 | P1 raw text contains private-use punctuation glyphs | Use retained original page images and explicit row/column checks. Do not parse the raw glyph text as an unqualified numeric dataset. |
| G3 | Complete financial/credit/risk/capital assessment requires other statements and notes | This pass examined only four of170 PDF pages. Read the affected source sections before broader work; no adequacy/credit conclusion. |
| G4 | Current status, source revisions and final authorisations not re-established | Preserve historical FY2024/as-at-report status; obtain current and governing evidence when requested. |
| G5 | Native Excel display/layout beyond metadata not rendered | Raw exact cells/structures and logos were checked. No unsupported full-screen display fidelity claim; selected financial values instead require the independently inspected PDF. |

## Next module

**CP-1: ready with limitations for the named intake.** Open this single CP-0
handoff and the verified ZIP. Read all three prepared worksheet headers and
the named numeric conflict rows before selecting observations. Confirm the
individual matching worksheet cells for fees, dividends, EUR/share EPS,
source zero and subsidiary cash flows against P1 images; preserve each
quantity family, period and source identity. Separately read the source PDF's
net interest income, total assets and operating cash flow without pretending
they were corrected workbook values. Carry G1–G5 forward and retain actual
consumed hashes. No bank credit ratio or source rescaling is requested.

Separate delivery must publish the actual CP-1 observations and CP-0
restrictions in populated HTML. The supporting ZIP is source preparation,
not completion of the requested analytical/delivery loop.
