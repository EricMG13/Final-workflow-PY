# CP-1 — dated valuation-input increment

## Request

Supply located FY2025 valuation operands for CP-1C. Current host-model source
read-through on 2026-11-04, with preceding context. This is a limited input
increment, not full CP-1 acceptance, independent assurance or current underwriting.
The 2024 peer case supplies the earlier candidate rationale only.

## Sources

The source is the original issuer filing body accessed at the SEC. Retained
`sources/filing-captures.txt` contains the actual browser-tool passages and search
outcomes. Its hash identifies the capture, not the raw HTML or a PDF. Direct
downloads failed (SEC/TDG 403, issuer PDF links 404); no original-byte equivalence
or full-document extraction/coverage is claimed.

- Moog FY2025 10-K: https://www.sec.gov/Archives/edgar/data/67887/000162828025054103/mog-20250927.htm
- TDG FY2025 10-K: https://www.sec.gov/Archives/edgar/data/1260221/000126022125000081/tdg-20250930.htm

## Findings

### Moog — source amounts in USD thousands except actual shares and USD/share prices

| Operand | Source figure | Period / original locator | Meaning / boundary |
|---|---|---|---|
| Class A outstanding | 28,424,853 shares | 2025-09-27; balance sheet p41, SEC L1035–1037 | Issued43,863,458; excludes treasury15,013,457 and SECT425,148; share rollforward p43 L1134–1146. |
| Class B outstanding | 3,237,452 shares | 2025-09-27; p41 L1038–1040 | Issued7,416,255; excludes treasury2,825,989, SECT526,644 and SERP826,170; p43 L1137–1156. |
| Class A closing price | USD204.64/share | As of2025-09-27; note19 p78 L2349 | Issuer's disclosed as-of closing-price basis, not a separately retrieved exchange tape. |
| Class B closing price | USD206.00/share | As of2025-09-27; note19 p78 L2349 | Keep the second class's own price. |
| Basic / diluted weighted-average shares | 31,680,280 / 32,082,601 shares | FY2025; p75 L2230–2232 | Annual EPS denominators, not period-end market-cap shares. |
| Net sales | 3,860,624 | FY ended2025-09-27; earnings p39 L939–940 | Reported FY2025; revised prior-year columns are not the earlier peer case's original numbers. |
| Earnings before income taxes | 312,648 | FY2025; p39 L953 | Consolidated pretax, not segment operating profit. |
| Interest expense line | 72,075 | FY2025; p39 L946; MD&A L702/723 | The source labels interest expense; no separate interest-income normalization is retained. |
| Depreciation / amortization | 94,013 / 9,715 | FY2025; cash flow p44 L1171–1172 | Note22 total D&A103,728 at L2579–2585 independently corroborates the sum. |
| Borrowing principal | 946,000 | 2025-09-27; note10 p61 L1671–1682 | Revolver195,000 + term250,000 + SECT facility1,000 + senior notes500,000. |
| Debt issuance cost deduction | 314 | Same date; note10 L1680 | Principal/carrying-value bridge, not additional debt. |
| Current debt / long-term debt | 1,563 / 944,123 | Same date; balance sheet L1019/1026 | Sum is net carrying value, not borrowing principal. |
| Borrowing fair value | 932,570 | Same date; note13 p64 L1801 | Issuer's Level2 fair-value estimate versus principal946,000. |
| Finance lease current / long term / total | 14,920 / 119,155 / 134,075 | Same date; note7 p58 L1546–1548 | In accrued/other liabilities, outside the borrowing captions. |
| Operating lease liabilities | 64,246 | Same date; note7 L1537–1539 | Excluded from the chosen finance-debt EV convention; no rent adjustment to earnings. |
| Cash and cash equivalents | 62,013 | Same date; balance sheet p41 L1002 | Cash deduction used in the defined bridge. Full legal/distributable accessibility not established. |
| Restricted cash | 200 | Same date; balance sheet L1003 | Separate asset; not deducted as available cash. |
| Sold receivables | 125,000 | Same date; note4 p54 L1445 | Derecognized under RPA; disclosed supplemental debt-like sensitivity, not GAAP borrowing. |
| Preferred / minority interests | No separate amount reported in the retained equity statement | p41 L1033–1050; note18 p75 L2247–2248 | Preferred shares are authorized, with conditional future-issuance language. No independent market value for either interest is retained. Do not manufacture an exact economic zero. |
| Short-term investments eligible for deduction | No separately established eligible amount | Current asset captions p41 L1000–1008; note13 L1777–1801 | Derivatives are not cash investments; pension/trust assets are not automatically available corporate cash. No unknown amount becomes a deduction. |
| Other debt-like claims | Unquantified adjustment beyond the chosen bridge | p41 L1027; note13 L1789–1800 | Pension liabilities157,218 and contingent consideration473 are disclosed, but full economic adjustments are not established by this increment. |

The class counts can be checked through issued less treasury/trust shares.
The trusts' shares are excluded from EPS outstanding shares (note20 p78,
L2360–2362); do not add them a second time to the source's stated outstanding.

### TDG — source amounts in USD millions

| Operand | Source figure | Period / original locator | Meaning / boundary |
|---|---|---|---|
| Net sales | 8,831 | FY ended2025-09-30; income statement SEC L1701–1703, MD&A L611 | Same fiscal-year cohort as peer, three-day end-date difference, no calendarisation. |
| Net income / tax | 2,074 / 555 | FY2025; EBITDA reconciliation p32 L1047/1051 | Source's reported ordinary EBITDA reconciliation. |
| Interest expense-net / D&A | 1,572 / 367 | FY2025; p32 L1049–1050 | Net interest differs from Moog's expense-labelled line. |
| Ordinary EBITDA | 4,568 | FY2025; p32 L1052 | Reported non-GAAP ordinary EBITDA, not operating EBIT+D&A. |
| EBITDA As Defined | 4,760 | FY2025; p32 L1054–1058 | Ordinary plus42 +157 +11 −18; not interchangeable with the Moog proxy. |

## Calculations

CP-1C must calculate the selected bridges and multiples; this input increment
does not select or justify a peer multiple. Missing economic adjustments remain
missing. A positive known-components result does not establish complete EV.

## Gaps

Selected located passages, not full source-pack inspection or raw-file retention.
No current price tape, complete preferred/minority/investment or economic-claims
review, normalized interest-income bridge or actual transaction-comp case.
Both annual filings were published after the fiscal-year-end dates: this is
retrospective source analysis, not a tradeable September2025 backtest.

## Next module

CP-1C: construct the dated known-components EV proxy, keep complete EV distinct,
and explain conditional individual-peer indications and their limits.
