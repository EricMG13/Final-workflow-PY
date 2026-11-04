# CP-0 — TDG annual source readiness

Run: `tdg-001`, 2026-11-04. This is a new model-authored response in the current
assistant session, using local file tools. It is not a historical reconstruction,
an isolated provider run or proof of the imported runtime.

Instructions: [CP-0](../../prompts/CP-0.md), SHA-256
`51e721cb787fb7567ff29cae956ef141443cd2a7cbbdd286b0cf09f8f66b5535`.
Method selection: Deploy V `c4d2e356` ancestry; Deploy Workflow method tree
`6f4a3997e7356352898c410cb7a045722aa5bf03` at selected revision
`2c809379cbba508888b7fbe28ee14eac5a294bbf`; targeted coverage and consumer-readiness
amendments recorded in [the methodology review](../../METHODOLOGY-REVIEW.md).
The linked prompt defines this bounded check, not certification of every CP-0 duty.

## Request

Determine whether the supplied TDG annual PDF can support CP-1 extraction of its
annual primary financial statements and comparative columns. Quarterly analysis,
current covenant compliance, adjusted metrics and a complete credit report are
outside this request.

## Sources

- **S1:** [TDG annual report PDF](../../data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf).
- Project-root-relative source path:
  `data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`.
- SHA-256: `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`.
- Size: 4,378,190 bytes; 160 PDF pages. Page numbers below are **one-based PDF
  pages**, not the printed page labels.
- Fresh text extraction: [source-pages.jsonl](source-pages.jsonl), one record per
  PDF page, using the project's installed pypdf in layout mode. This is a reading
  aid; S1 remains the evidence. No historical model output was used as a source.
- Authority: the document identifies itself as a Form 10-K and includes an audit
  opinion. This check establishes its contents, not a fresh SEC download or
  authentication. No conflicting version was supplied to this check; versions
  outside S1 were not compared. No draft marker was observed on the examined pages.

## Findings

### Identity, periods and presentation

| Finding | Located evidence in S1 |
|---|---|
| Registrant is TransDigm Group Incorporated; document is its FY2024 Form 10-K. | PDF 1: “TransDigm Group Incorporated”; “FORM 10-K”; “For the fiscal year ended September 30, 2024”. |
| Consolidated TD Group and subsidiaries, rather than a standalone subsidiary or guarantor perimeter. | PDF 110: “include the accounts of TD Group and subsidiaries. Intercompany balances and transactions have been eliminated.” |
| U.S. GAAP presentation. | PDF 110: “The accompanying consolidated financial statements were prepared in conformity with U.S. GAAP”. |
| Reporting currency is USD. | PDF 55: “Because our consolidated financial statements are presented in U.S. dollars”. |
| Fiscal-year convention ends September 30; FY2024 is October 1, 2023 through September 30, 2024. | PDF 3: “the year ending or ended September 30.”; “October 1, 2023 to September 30, 2024.” |
| Balance sheets are instants at September 30, 2024 and 2023. They do not have duration start dates. | PDF 105: “AS OF SEPTEMBER 30, 2024 AND 2023”. |
| Income, comprehensive income, changes in stockholders' deficit and cash flows cover FY2024, FY2023 and FY2022. The equity statement also opens at September 30, 2021. | PDF 101 statement index; PDF 106–109 headings and dated rows. The fiscal-year convention on PDF 3 supplies the annual duration starts; the equity opening balance is not a fourth income-statement period. |
| The audit opinion covers the two balance-sheet dates and three fiscal years. | PDF 103: “in conformity with U.S. generally accepted accounting principles.” The opinion is read as evidence of the document's accounting basis, not a new assurance opinion by this module. |
| Comparative reclassifications are disclosed. | PDF 110: “prior year amounts to conform to the current year presentation, none of which are material.” Use the comparative columns in this filing and retain this qualification. |

### Page map for CP-1

| Content | PDF page(s) | Printed label | Unit / period instruction |
|---|---:|---|---|
| Fiscal-year convention | 3 | 1 | September 30 year-end; explicit FY2024 start/end. |
| Reporting currency | 55 | 53 | USD, supported by the explicit currency statement above. |
| Financial statement index | 101 | 99 | Resolves statement and note locations. |
| Audit opinion | 103–104 | F-1–F-2 | Opinion text examined on 103; 104 located as continuation. |
| Consolidated balance sheets | 105 | F-3 | “Amounts in millions, except share amounts”; instants 2024-09-30 and 2023-09-30. Preserve embedded per-share par value separately. |
| Consolidated statements of income | 106 | F-4 | “Amounts in millions, except per share amounts”; annual 2024/2023/2022. Monetary rows are USD millions; EPS and dividends per share are USD/share; weighted-average shares are millions of shares. |
| Consolidated statements of comprehensive income | 107 | F-5 | “Amounts in millions”; annual 2024/2023/2022. |
| Consolidated statements of changes in stockholders' deficit | 108 | F-6 | “Amounts in millions, except share amounts”; annual changes and dated opening/closing balances. Actual share counts and embedded dividends per share require their own quantity families. |
| Consolidated statements of cash flows | 109 | F-7 | “Amounts in millions”; annual 2024/2023/2022. Parentheses carry sign; retain source dashes without silently treating every dash as missing or zero. |
| Basis and consolidation policy | 110 | F-8 | Consolidation, U.S. GAAP and comparative reclassification qualification. |
| Notes, for targeted follow-up | 110–153 | F-8–F-51 | Located from the index. Full note coverage has not been reviewed. |

Additional routing, **not completed analysis**: non-GAAP definition/bridges on
PDF 52–54; debt on 126–133; taxes on 137; segment information/reconciliation on
141–142; leases on 147–148. Read the actual passages if a later request needs
these topics. The rotated supplemental reconciliation on 156 is subject to G1.

### Coverage actually examined

- Extraction produced 160 page records; 157 contain text. Empty text records:
  PDF 156, 159 and 160. Text presence does not establish completeness.
- Text examination covered identity/period policy on 1 and 3, currency passage on
  55, index on 101, audit opinion passage on 103, primary statement headings and
  units on 105–109, consolidation policy on 110, and foreign-currency policy on
  114. A page-heading scan and the topic locators above support routing only.
- Visual checks: primary statement headings/column layout on
  [105](page-105.png), [106](page-106.png) and [109](page-109.png), plus the
  extraction exceptions [156](page-156.png), [159](page-159.png) and
  [160](page-160.png). Page 156 contains a rotated non-GAAP reconciliation;
  159 and 160 appear blank at the retained render resolution. Pages 107 and 108
  were rendered but not visually reviewed. No cell-by-cell statement audit is
  claimed by CP-0.
- The extractor emitted a CFF font warning and a rotated-text warning. The latter
  corresponds to a visible missed table on 156. Unexamined pages and individual
  glyph fidelity remain unverified; the PDF must resolve uncertain amounts/signs.

## Calculations

Not applicable to CP-0.

## Gaps

| ID | Limitation | Affected work | Required action |
|---|---|---|---|
| G1 | Rotated PDF 156 has content but no extracted text. | Any use of its supplemental historical non-GAAP reconciliation. | Read a suitable render or alternate extraction and verify the particular rows before use. It does not block the primary statements on 105–109. |
| G2 | Font/rotation warnings; most pages have not received visual or cell-level verification. | Any uncertain glyph, sign, column or note; broad completeness claims. | CP-1 checks its extracted figures against the PDF and requests a targeted reread if ambiguous. Do not promote text availability to full review. |
| G3 | One supplied annual PDF only; external authenticity and competing revisions were not checked. | Claims about latest filings, quarterly history or source-version conflicts. | Obtain/compare those sources only if that scope is requested. This does not prevent extraction of the identified annual columns. |

## Next module

**CP-1: ready with limitations** for annual primary-statement extraction. Issuer,
perimeter, currency, period convention and required statement locations are
established; no required primary-statement page is missing from the text extraction.

Resolve the S1 path from the project root or follow the relative PDF link above.
Use [source-pages.jsonl](source-pages.jsonl) as the text aid and the page map for
PDF 105–109; use 3, 55, 103 and 110 for period/currency/basis context. Verify S1's
hash before use. Keep G1–G3 attached to this handoff.

CP-1 may extract the reported annual statements with exact dates, quantity families,
source page references and missingness. It must distinguish reported values from
any subsequently calculated value. This handoff contains no financial dataset,
calculated OPEX, adjusted EBITDA conclusion, credit judgment or delivery approval.
The immediate consumer check is only to open the required pages and demonstrate
correct interpretation of representative money, per-share and share-count rows.
