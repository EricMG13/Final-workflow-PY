# CP-1 — historical Erste prepared-source intake

## Request

Consume the current CP-0/CP-PARSE output and retain selected source-checked
observations from FY2024 and comparative2023. Actual current host model with
local file tools and preceding context, not a blind or independent provider
evaluation. This exercises prepared-source intake; it is not a full annual
CP-1 dataset or bank-credit assessment.

**Result: the prepared package is usable with the stated source restrictions.**
All four prepared representations were actually opened and their checksums
checked. The three worksheet structures are readable and selected matching
figures can be used. The conflicted workbook decimals remain ineligible for
automatic monetary import. The PDF observations below are separate evidence,
not corrected worksheet outputs.

## Sources

Consumed [CP-0](ERSTE_CP-0_20261104.md), SHA-256
`70bfdf7d947183d4b7c564faa917e89c89451cd423e4043bb8d1fb06aabf1d70`, and
[preparation ZIP](ERSTE_CP-PARSE_20261104_BATCH-001-of-001.zip), SHA-256
`5160e6f2d2af0dab433586c0213e04695e8f33cddd3a2830b0ada7dd47800516`.

| Opened representation | Consumed Markdown SHA-256 |
|---|---|
| parsed/W1/W1_CP-PARSE_20261104.md | 287e497930aa6e9cf75e22b3ea636086dd829f6b2e731f94d5751696bde89076 |
| parsed/W2/W2_CP-PARSE_20261104.md | 7b1687a4da90c789098161110c7be4ec46e81f369eeda3ac534e3adab68f690e |
| parsed/W3/W3_CP-PARSE_20261104.md | be463db392da8012758980451242d38fbbd0a64bb0fee476441a7bf1adebed80 |
| parsed/P1/P1_CP-PARSE_20261104.md | ff469ee53c7a598a895a13cc97a32977c8d9df0f0dc9a529f8c225c0024b615e |

Original-source hashes and paths remain those in CP-0's complete inventory.
The P1 source images of PDF3/5/8/9 were independently inspected in this same
session. Worksheets are issuer-linked supporting representations; P1's basis
page identifies Erste Group Bank AG/group, consolidated EU-adopted IFRS and
the year ending31 December2024 with comparatives. This observation does not
establish later approvals, revisions or current2026 conditions.

## Findings

### Selected matched worksheet observations

The values are individual reported observations, checked against corresponding
original PDF rows. Period labels remain those supplied. W2 is an instant;
income/cash-flow and EPS columns are annual durations. This is not a bank
liquidity, recurring-earnings or capital-adequacy conclusion.

| Observation | Prior2023 | Current2024 | Unit / quantity family | Period labels | Source locators and cross-check |
|---|---|---|---|---|---|
| Fee and commission expenses | -464 | -517 | EUR million; monetary | 1-12 23 / 1-12 24 | W1 Tabelle1!C11:D11; P1 PDF3/printed236, fee/commission-expense row. |
| Dividend income | 38 | 39 | EUR million; monetary | 1-12 23 / 1-12 24 | W1 Tabelle1!C12:D12; P1 PDF3/printed236, dividend-income row. |
| Earnings per share | 6.80 | 7.20 | EUR per share; currency_per_share | 1-12 23 / 1-12 24 | W1 Tabelle1!C39:D39; P1 PDF3/printed236, basic EPS row. Raw worksheet strings retain their leading spaces: " 6.80" / " 7.20". |
| Pledged as collateral — non-trading FVPL financial assets | 0 | 0 | EUR million; monetary | Dec 23 / Dec 24 instants | W2 Tabelle1!C11:D11, the nested pledged row under non-trading FVPL; P1 PDF5/printed238, same nested row. This is not all pledged collateral. |
| Acquisition of subsidiaries (net of cash and cash equivalents acquired) | 0 | -88 | EUR million; monetary | 1-12 23 / 1-12 24 | W3 Tabelle1!C42:D42; P1 PDF8/printed241, acquisition-of-subsidiaries row. |
| Disposal of subsidiaries | 0 | 28 | EUR million; monetary | 1-12 23 / 1-12 24 | W3 Tabelle1!C43:D43; P1 PDF8/printed241, disposal-of-subsidiaries row. |

The zero in W2 C11/D11 and the W3 prior acquisition/disposal zeros are explicit
stored/source zeros. W3 C10/D10,C12/D12,C17/D17 and C26/D26 are blank group-header
cells; none supplies a zero cash flow or an extra subtotal. W1's weighted-share
rows have a separate individual-share quantity family; its EUR-thousand EPS
operands and EUR-per-share outcome do not inherit the primary table's EUR-million
unit. No EPS calculation was performed here.

### Separate PDF observations

| Observation | Prior2023 | Current2024 | Unit / quantity family | Period labels | Source locator and worksheet restriction |
|---|---|---|---|---|---|
| Net interest income | 7,228 | 7,528 | EUR million; monetary | 1-12 23 / 1-12 24 | P1 PDF3/printed236, net-interest-income row. W1 C4/D4 stores 7.2279999999999998 / 7.5279999999999996; those cells were not rescaled or used as these amounts. |
| Total assets | 337,155 | 353,736 | EUR million; monetary | Dec 23 / Dec 24 instants | P1 PDF5/printed238, total-assets row. W2 C36/D36 stores 337.15499999999997 / 353.73599999999999; PDF column order was checked visually because the extracted total row runs together. |
| Cash flow from operating activities | 2,586 | -9,029 | EUR million; monetary | 1-12 23 / 1-12 24 | P1 PDF8/printed241, operating-cash-flow row. W3 C33/D33 stores 2.5859999999999999 / -9.0289999999999999; sign and source conflict retained. |

The original workbook XML already contains the discrepant decimals. Faithful
parsing exposed them. A global conversion would alter other correctly matched
cells, including zero and the fee-expense values. Accordingly, there is no
authorised numerical repair rule; every additional financial use requires its
own source/period/unit check. The observed cause is conflicting source
representations, not a demonstrated failure of the extraction function.

P1's cash-flow footnote equates cash and cash equivalents with its balance-sheet
cash-and-cash-balances line. That is a reported definition, not certification of
unrestricted cash access. No industrial EBITDA/FCF shortcut is applied to this
bank statement. P1's private-use font punctuation required the original images;
the retained text alone was not the numeric oracle.

## Calculations

No financial calculations, rescaling, ratio, reconciliation or normalized
earnings dataset. Both sets of observations above are read from supplied source
rows. Hash/checksum operations establish consumed identities only. The prior
independent observation file was available in the same host context; agreement
with it does not establish independent-context model reliability.

## Gaps

| ID | Restriction retained from CP-0 | Effect on this output and next use |
|---|---|---|
| G1 | Workbook decimals conflict with corresponding PDF values | No blanket worksheet monetary import or rescaling. Only individually source-checked worksheet observations are shown; separately sourced PDF amounts stay separate. |
| G2 | P1 raw font glyphs need original-image interpretation | PDF3/5/8 source images and column order were checked for the selected rows; other raw values need the same check. |
| G3 | Only selected statements/basis examined, not full annual/notes scope | No complete statement reconstruction/reconciliation, credit assessment, bank-capital or funding/adequacy conclusion. |
| G4 | Historical evidence; current revisions/approvals not re-established | FY2024/comparative2023 only; not a current2026 issuer opinion. |
| G5 | Full native Excel display geometry unverified | Stored cell/metadata and individual PDF matches support the stated intake scope, not universal workbook display fidelity. |

## Next module

Separate delivery: construct populated HTML from these actual observation and
restriction tables and CP-0's source-warning content. Preserve both columns,
units, instant/duration distinction, source/cell/page references, source zeros,
the restriction on raw workbook decimals and G1–G5. No workbook output, second
analytical execution, synthetic replacement figures or native accepted head.
Further analytical work requires the affected full source sections first.
