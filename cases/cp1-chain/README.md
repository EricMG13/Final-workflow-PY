# Public TDG FY2024 CP-1 source oracle

This directory freezes source-derived expectations for the TDG FY2024 public filing. It is an independent data oracle only; it contains no parser, composer, verifier or code under test.

## Source and count

- Raw source: `TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`, 160 physical pages, SHA-256 `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`.
- The actual units are p105 balance sheet (29 rows / 58 cells), p106 income statement (22 / 66), p107 comprehensive-income statement (8 / 24), and p109 cash-flow statement (44 / 132). Together they contain 103 rows / 280 cells.
- `tdg-financial-reference.json` is a byte-identical copy of the independently reviewed 95-row / 256-cell BS/IS/CFS reference. Its SHA remains `b57f652715d10c86a034592f895560cc7373de8af118f5b3edfa363bc444eeb6`; do not edit or regenerate it. The additional eight CI rows are separately transcribed from the raw PDF page 107 and independently source-reviewed.
- Page-text SHA-256 values and extraction method/version are in `manifest.json` and `expected.json`. PDF page numbers are physical pages. Line numbers refer to the frozen pypdf layout text for that physical page.

The 95 existing reference rows were cross-walked against direct pypdf page text by complete normalized label and exact raw value vector. Every row had one matching amount line, excluding the five specifically split labels whose parts were manually pinned to their printed PDF lines. The p106 weighted-average-shares heading is also retained as a label part for its “Basic and diluted” row. The copied financial reference itself remains byte-identical.

## Frozen semantics

- The issuer's page 3 fiscal policy says fiscal years end September 30 and FY2024 runs October 1, 2023 through September 30, 2024. FY2023/FY2022 starts follow the same printed annual period convention. Balance-sheet observations are instants and have no start date.
- USD millions is the ordinary amount unit. Common-stock share counts within its printed label do not change its two monetary cells. Treasury-stock cells remain negative.
- EPS and dividends per common share are USD/share. Weighted-average shares are millions of shares and carry no currency. Every one of the 280 cells has a typed quantity and a citation for its unit context.
- CI remains a distinct source statement kind and has unique CI row IDs/locators. An explicit IS enum alias is transport-only if the canonical legacy enum cannot represent CI; it cannot duplicate or merge CI into IS metrics.
- All 21 printed dash cells stay raw dashes and mean known zero under the existing independent rule. Missing or unselected facts are not zero.
- Nonmonetary quantities may be reported only for the exact cited source period. They cannot be added/subtracted across FY/YTD/LTM periods or used in monetary accounts, identities or cash adjustments.

## Label/source controls

`expected.json` freezes all four statement titles, unit contexts, period headers and section-caption positions, plus complete meaningful row labels, direct PDF label parts, value-line positions, periods, raw values, normalized values, units and typed per-cell quantity facts. It includes the five source wraps at p105:32–33, p105:37–38, p106:16–17, p106:22–23 and p106:25–26, plus the p106:32 heading attached to p106:33 weighted-average shares.

The `fixtures/` directory contains small invented text sources for generic controls: uppercase wrapped label, digit-bearing continuation, a true caption, blank/table boundary, note-vs-amount columns, ambiguous grouping refusal, page and line citation locators, mixed entity-column refusal, and typed-quantity/unit-citation/arithmetic refusals. These are synthetic controls, not TDG source data.

## Status and use

- `expected.json` is the only added extended expectation object; the independent 95-row financial reference is preserved as a sibling file.
- No candidate parser/composer output was used to set the oracle. Product table/claim/render validators are N/A at this preparation stage: there is no canonical public TDG chain module output yet, so there is nothing honest to validate or render.
- There is no case builder. Determinism is checked by hashing canonical normalized JSON twice; no builder is fabricated.
- Root froze the CP-2 consumer coordinates in the adopted implementation contract at `work/cp1-chain/interfaces.md` in the chain-proof worktree, linked from `work/cp1-chain-oracle/questions.md`. The source rows remain in this oracle; consumer selection/runtime IDs are not duplicated into the source key. The contract requires fresh authenticated producer/run identities, USD millions display and correction of the known T4.5 cash projection formatting defect. It is pending implementation and is not product proof.
