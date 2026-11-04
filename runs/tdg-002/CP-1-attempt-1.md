# CP-1 — Annual financial foundation

## Request

Extract and interpret the annual financial foundation from the sole supplied issuer filing, with complete primary statements, relevant supplemental schedules, explicit gaps and consumer readiness. Scope is TransDigm Group Incorporated and consolidated subsidiaries, FY2022–FY2024, plus the September 30, 2023 and 2024 balance sheet instants. No quarterly, YTD or LTM series is constructed.

## Sources

**S1 — issuer source:** TransDigm Group Incorporated Form 10-K for fiscal year ended September 30, 2024. PDF: `data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`; SHA-256 `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af` (matches CP-0). Fresh text aid is `runs/tdg-001/source-pages.jsonl`; PDF pages below are one-based PDF page numbers, not printed labels. Text aid used for statement extraction and note reading; primary statement cells were cross-checked against the page text and PDF images retained by CP-0 for pages 105, 106 and 109. Relevant supplemental PDF pages 126–133 (debt), 141–142 (segments and EBITDA As Defined), 147–148 (leases), and 137 (tax) were read from the aid; no visual cell audit is claimed for these schedules.

Issuer is TransDigm Group Incorporated. The filing defines “Company” as TD Group with TransDigm Inc. and wholly/majority-owned subsidiaries under control (PDF 3); consolidation policy says statements include TD Group and subsidiaries with intercompany balances/transactions eliminated and uses U.S. GAAP (PDF 110). Currency is USD (PDF 55). FY convention is October 1 through September 30 (PDF 3). Annual income, comprehensive income, equity changes and cash-flow periods cover FY2022, FY2023 and FY2024; balance-sheet dates are September 30, 2023 and September 30, 2024 (PDF 105–109). Monetary statement amounts are USD millions unless noted. EPS/dividend per share are USD per share; weighted-average shares are millions of shares; share counts are individual shares. Balance-sheet amounts are instants, not duration flows.

The audit report states the consolidated financial statements were audited and opines fair presentation in conformity with U.S. GAAP (PDF 103). CP-0 notes that external authenticity/latest-version status was not independently checked and comparative reclassifications to conform to current presentation were disclosed as not material (PDF 110). Source authority is therefore the supplied filed annual report; this module does not authenticate an SEC download.

Subsequent event reviewed: the company drew the remaining $162.5 million available under the trade receivable securitization facility in October 2024 (PDF 131). This is post-period financing and is not added to September 30 reported debt or historical cash. CP-0 G1 about rotated PDF 156 remains unresolved because that supplemental non-GAAP table is outside this extraction; G2 cell/glyph verification remains a limitation for unvisually reviewed pages and notes; G3 external version/authenticity remains unexamined. PDF 156 is not needed for the extracted primary statements or EBITDA As Defined bridge on PDF 142.

## Findings

### T4.1–T4.3 — Source, entity, normalization

| Register | Retained determination |
|---|---|
| T4.1 source inventory | One source, S1, 2024 Form 10-K, issuer audited consolidated statements; source hash matches CP-0. Relevant statement pages 105–109; note pages specified above. No external comparison or authentication. Text aid is derivative; PDF remains evidence. |
| T4.2 entity/scope | TransDigm Group Incorporated with TransDigm Inc. and wholly/majority-owned subsidiaries under control, consolidated; U.S. GAAP; USD. Comparative FY periods in this filing retain same perimeter and basis. |
| T4.3 normalization | Monetary unit USD millions; statement parentheses retained as negative; printed dash “—” retained as dash and is not silently made zero. In a reconciliation only, a dash may be represented as zero where the printed statement presents no amount, with the scope stated. Share amounts, share counts and per-share values are never merged into USD millions. Reported statement lines remain as presented. Balance-sheet debt categories are kept separate from debt-note principal, unamortized issuance costs/discounts, and debt maturities. |

### T4.4 — Income statement and comprehensive-income/equity supplements

Reported consolidated income statement, PDF 106. Amounts USD millions except per-share values and weighted-average shares.

| Row as reported | FY2024 | FY2023 | FY2022 |
|---|---:|---:|---:|
| NET SALES | 7,940 | 6,585 | 5,429 |
| COST OF SALES | 3,268 | 2,743 | 2,330 |
| GROSS PROFIT | 4,672 | 3,842 | 3,099 |
| SELLING AND ADMINISTRATIVE EXPENSES | 980 | 780 | 748 |
| AMORTIZATION OF INTANGIBLE ASSETS | 161 | 139 | 136 |
| INCOME FROM OPERATIONS | 3,531 | 2,923 | 2,215 |
| INTEREST EXPENSE—NET | 1,286 | 1,164 | 1,076 |
| REFINANCING COSTS | 58 | 56 | 1 |
| OTHER (INCOME) EXPENSE | (28) | (13) | 11 |
| INCOME FROM CONTINUING OPERATIONS BEFORE INCOME TAXES | 2,215 | 1,716 | 1,127 |
| INCOME TAX PROVISION | 500 | 417 | 261 |
| INCOME FROM CONTINUING OPERATIONS | 1,715 | 1,299 | 866 |
| INCOME FROM DISCONTINUED OPERATIONS, NET OF TAX | — | — | 1 |
| NET INCOME | 1,715 | 1,299 | 867 |
| LESS: NET INCOME ATTRIBUTABLE TO NONCONTROLLING INTERESTS | (1) | (1) | (1) |
| NET INCOME ATTRIBUTABLE TO TD GROUP | 1,714 | 1,298 | 866 |
| NET INCOME APPLICABLE TO TD GROUP COMMON STOCKHOLDERS | 1,481 | 1,260 | 780 |
| Earnings per share from continuing operations—basic and diluted (USD/share) | 25.62 | 22.03 | 13.38 |
| Earnings per share from discontinued operations—basic and diluted (USD/share) | — | — | 0.02 |
| Earnings per share (USD/share) | 25.62 | 22.03 | 13.40 |
| Cash dividends declared per common share (USD/share) | 110.00 | — | 18.50 |
| Weighted-average shares outstanding, basic and diluted (millions shares) | 57.8 | 57.2 | 58.2 |

Comprehensive income statement, PDF 107, USD millions:

| Row as reported | FY2024 | FY2023 | FY2022 |
|---|---:|---:|---:|
| Net income | 1,715 | 1,299 | 867 |
| Less: Net income attributable to noncontrolling interests | (1) | (1) | (1) |
| Net income attributable to TD Group | 1,714 | 1,298 | 866 |
| Foreign currency translation adjustment | 181 | 137 | (379) |
| Unrealized (losses) gains on derivatives | (124) | 20 | 352 |
| Pension and post-retirement benefit plans adjustment | (1) | 12 | 8 |
| Other comprehensive income (loss), net of tax, attributable to TD Group | 56 | 169 | (19) |
| TOTAL COMPREHENSIVE INCOME ATTRIBUTABLE TO TD GROUP | 1,770 | 1,467 | 847 |

Changes in stockholders’ deficit, PDF 108. USD millions except share-count rows. Source provides dated opening FY2022 and annual transactions; monetary rows shown here follow the reported total/equity effects. “—” remains source dash.

| Activity / reported row | FY2022 | FY2023 | FY2024 |
|---|---:|---:|---:|
| Opening balance date | Sep 30, 2021 | Sep 30, 2022 | Sep 30, 2023 |
| Opening common shares (individual) | 59,403,100 | 60,049,685 | 60,995,513 |
| Opening TD Group deficit | (2,910) | (3,766) | (1,978) |
| Changes in noncontrolling interest of consolidated subsidiaries, net | 1 | (1) | 1 |
| Special dividends and vested dividend equivalents declared | (1,045) | — | (6,368) |
| Accrued unvested dividend equivalents and other | (30) | (5) | (87) |
| Compensation expense recognized for employee stock options | 151 | 112 | 134 |
| Stock-based compensation activity | 132 | 215 | 245 |
| Stock repurchases under repurchase program | (912) | — | — |
| Net income attributable to TD Group | 866 | 1,298 | 1,714 |
| Foreign currency translation adjustment, net of tax | (379) | 137 | 181 |
| Unrealized gain (loss) on derivatives, net of tax | 352 | 20 | (124) |
| Pension and post-retirement benefit plans adjustment, net of tax | 8 | 12 | (1) |
| Closing balance date | Sep 30, 2022 | Sep 30, 2023 | Sep 30, 2024 |
| Closing common shares (individual) | 60,049,685 | 60,995,513 | 61,904,833 |
| Closing common stock par value | 1 | 1 | 1 |
| Closing additional paid-in capital | 2,113 | 2,440 | 2,819 |
| Closing accumulated deficit | (3,914) | (2,621) | (7,362) |
| Closing accumulated other comprehensive loss | (267) | (98) | (42) |
| Closing treasury shares (individual) | 5,688,639 | 5,688,639 | 5,688,639 |
| Closing treasury stock value | (1,706) | (1,706) | (1,706) |
| Closing noncontrolling interests | 7 | 6 | 7 |
| Closing total stockholders’ deficit | (3,766) | (1,978) | (6,283) |

Complete statement row transcription, PDF 108 (columns in source order: common shares; common stock par; APIC; accumulated deficit; accumulated other comprehensive loss; treasury shares; treasury stock value; noncontrolling interests; total). Values are in USD millions except shares; source dashes are retained.

```text
BALANCE—September 30, 2021: 59,403,100 | 1 | 1,830 | (3,705) | (248) | (4,198,226) | (794) | 6 | (2,910)
Changes in noncontrolling interest of consolidated subsidiaries, net: — | — | — | — | — | — | — | 1 | 1
Special dividends ($18.50 per share) and vested dividend equivalents declared: — | — | — | (1,045) | — | — | — | — | (1,045)
Accrued unvested dividend equivalents and other: — | — | — | (30) | — | — | — | — | (30)
Compensation expense recognized for employee stock options: — | — | 151 | — | — | — | — | — | 151
Stock-based compensation activity: 646,585 | — | 132 | — | — | — | — | — | 132
Stock repurchases under repurchase program: — | — | — | — | — | (1,490,413) | (912) | — | (912)
Net income attributable to TD Group: — | — | — | 866 | — | — | — | — | 866
Foreign currency translation adjustment, net of tax: — | — | — | — | (379) | — | — | — | (379)
Unrealized gain on derivatives, net of tax: — | — | — | — | 352 | — | — | — | 352
Pension and post-retirement benefit plans adjustment, net of tax: — | — | — | — | 8 | — | — | — | 8
BALANCE—September 30, 2022: 60,049,685 | 1 | 2,113 | (3,914) | (267) | (5,688,639) | (1,706) | 7 | (3,766)
Changes in noncontrolling interest of consolidated subsidiaries, net: — | — | — | — | — | — | — | (1) | (1)
Accrued unvested dividend equivalents and other: — | — | — | (5) | — | — | — | — | (5)
Compensation expense recognized for employee stock options: — | — | 112 | — | — | — | — | — | 112
Stock-based compensation activity: 945,828 | — | 215 | — | — | — | — | — | 215
Net income attributable to TD Group: — | — | — | 1,298 | — | — | — | — | 1,298
Foreign currency translation adjustment, net of tax: — | — | — | — | 137 | — | — | — | 137
Unrealized gain on derivatives, net of tax: — | — | — | — | 20 | — | — | — | 20
Pension and post-retirement benefit plans adjustment, net of tax: — | — | — | — | 12 | — | — | — | 12
BALANCE—September 30, 2023: 60,995,513 | 1 | 2,440 | (2,621) | (98) | (5,688,639) | (1,706) | 6 | (1,978)
Changes in noncontrolling interest of consolidated subsidiaries, net: — | — | — | — | — | — | — | 1 | 1
Special dividends ($35.00 and $75.00 per share) and vested dividend equivalents declared: — | — | — | (6,368) | — | — | — | — | (6,368)
Accrued unvested dividend equivalents and other: — | — | — | (87) | — | — | — | — | (87)
Compensation expense recognized for employee stock options: — | — | 134 | — | — | — | — | — | 134
Stock-based compensation activity: 909,320 | — | 245 | — | — | — | — | — | 245
Net income attributable to TD Group: — | — | — | 1,714 | — | — | — | — | 1,714
Foreign currency translation adjustment, net of tax: — | — | — | — | 181 | — | — | — | 181
Unrealized loss on derivatives, net of tax: — | — | — | — | (124) | — | — | — | (124)
Pension and post-retirement benefit plans adjustment, net of tax: — | — | — | — | (1) | — | — | — | (1)
BALANCE—September 30, 2024: 61,904,833 | 1 | 2,819 | (7,362) | (42) | (5,688,639) | (1,706) | 7 | (6,283)
```

The filing also states FY2024 dividend declarations of $35 and $75 per share, while cash dividends/dividend equivalents paid in FY2024 were $2,038 million; declaration, accrual, payable and cash payment amounts are different concepts. FY2024 balance sheet includes $4,216 million dividends payable (PDF 105). Shares issued and weighted-average shares are distinct from per-share declarations.

### T4.5 — Cash-flow statement

Reported consolidated cash flows, PDF 109, USD millions. Parentheses are negative; source dash is “—”.

| Row as reported | FY2024 | FY2023 | FY2022 |
|---|---:|---:|---:|
| Net income | 1,715 | 1,299 | 867 |
| Income from discontinued operations, net of tax | — | — | (1) |
| Depreciation | 149 | 129 | 116 |
| Amortization of intangible assets and product certification costs | 163 | 139 | 137 |
| Amortization of debt issuance costs, original issue discount and premium | 40 | 41 | 34 |
| Amortization of inventory step-up | 21 | 2 | 3 |
| Amortization of loss contract reserves | (35) | (34) | (39) |
| Refinancing costs | 58 | 56 | 1 |
| Gain on sale of businesses, net | (11) | — | (7) |
| Non-cash stock and deferred compensation expense | 217 | 157 | 184 |
| Deferred income taxes | 10 | 3 | (22) |
| Foreign currency exchange losses (gains) | 20 | 14 | (40) |
| (Gain) loss on settlement of ERP | — | (9) | 22 |
| Cash refund (contribution) for ERP settlement, net | — | 9 | (16) |
| Trade accounts receivable change | (84) | (212) | (190) |
| Inventories change | (104) | (261) | (134) |
| Income taxes (receivable) payable change | (62) | 168 | 58 |
| Other assets change | (60) | (44) | (56) |
| Accounts payable change | (11) | 12 | 58 |
| Accrued interest change | 60 | (45) | (21) |
| Accrued and other liabilities change | (41) | (49) | (6) |
| Net cash provided by operating activities | 2,045 | 1,375 | 948 |
| Capital expenditures | (165) | (139) | (119) |
| Acquisition of businesses, net of cash acquired | (2,347) | (762) | (437) |
| Other investing transactions | 71 | 1 | 3 |
| Net cash used in investing activities | (2,441) | (900) | (553) |
| Proceeds from exercise of stock options | 245 | 215 | 132 |
| Dividends and dividend equivalent payments | (2,038) | (38) | (1,091) |
| Repurchases of common stock | — | — | (912) |
| Proceeds from issuance of senior secured notes, net | 7,373 | 3,504 | — |
| Repayments of senior secured notes | (4,400) | (1,122) | — |
| Repayments of senior subordinated notes, net | (550) | (1,459) | — |
| Repayment on revolving credit facility | — | — | (200) |
| Proceeds from trade receivable securitization facility, net | 137 | — | — |
| Proceeds from term loans, net | 6,815 | 6,238 | — |
| Repayment on term loans | (4,403) | (7,334) | (75) |
| Financing costs and other, net | (8) | (20) | (2) |
| Net cash provided by (used in) financing activities | 3,171 | (16) | (2,148) |
| Effect of exchange rate changes on cash and cash equivalents | 14 | 12 | (33) |
| Net increase (decrease) in cash and cash equivalents | 2,789 | 471 | (1,786) |
| Cash and cash equivalents, beginning of period | 3,472 | 3,001 | 4,787 |
| Cash and cash equivalents, end of period | 6,261 | 3,472 | 3,001 |
| Cash paid during period for interest, net | 1,158 | 1,160 | 1,057 |
| Cash paid during period for income taxes, net of refunds | 539 | 260 | 220 |

### T4.6 — Balance sheet

Reported consolidated balance sheets, PDF 105, USD millions except share amounts; balance-sheet instants.

| Row as reported | Sep 30, 2024 | Sep 30, 2023 |
|---|---:|---:|
| Cash and cash equivalents | 6,261 | 3,472 |
| Trade accounts receivable—Net | 1,381 | 1,230 |
| Inventories—Net | 1,876 | 1,616 |
| Prepaid expenses and other | 511 | 420 |
| Total current assets | 10,029 | 6,738 |
| Property, plant and equipment—Net | 1,488 | 1,255 |
| Goodwill | 10,419 | 8,988 |
| Other intangible assets—Net | 3,446 | 2,747 |
| Other non-current assets | 204 | 242 |
| Total assets | 25,586 | 19,970 |
| Current portion of long-term debt | 98 | 71 |
| Short-term borrowings—trade receivable securitization facility | 486 | 349 |
| Accounts payable | 323 | 305 |
| Dividends payable | 4,216 | — |
| Accrued and other current liabilities | 1,216 | 854 |
| Total current liabilities | 6,339 | 1,579 |
| Long-term debt | 24,296 | 19,330 |
| Deferred income taxes | 766 | 627 |
| Other non-current liabilities | 468 | 412 |
| Total liabilities | 31,869 | 21,948 |
| Common stock par value | 1 | 1 |
| Common stock authorized shares (individual) | 224,400,000 | 224,400,000 |
| Common shares issued (individual) | 61,904,833 | 60,995,513 |
| Additional paid-in capital | 2,819 | 2,440 |
| Accumulated deficit | (7,362) | (2,621) |
| Accumulated other comprehensive loss | (42) | (98) |
| Treasury shares (individual) | 5,688,639 | 5,688,639 |
| Treasury stock at cost | (1,706) | (1,706) |
| Total TD Group stockholders’ deficit | (6,290) | (1,984) |
| Noncontrolling interests | 7 | 6 |
| Total stockholders’ deficit | (6,283) | (1,978) |
| Total liabilities and stockholders’ deficit | 25,586 | 19,970 |

### T4.8 and T4.14 — Period register

| Period | Type | Start | End | Basis / unit | Available use |
|---|---|---|---|---|---|
| FY2022 | Historical duration | 2021-10-01 | 2022-09-30 | U.S. GAAP / USD millions, with distinct non-monetary quantity families | Income, comprehensive income, equity changes, cash flows, segment sales/EBITDA; not quarters/YTD/LTM |
| FY2023 | Historical duration | 2022-10-01 | 2023-09-30 | Same | Same; balance sheet also has Sep 30, 2023 instant |
| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 | Same | Same; balance sheet also has Sep 30, 2024 instant |
| Sep 30, 2023 | Period end | — | 2023-09-30 | U.S. GAAP / USD millions, shares separate | Balance sheet only |
| Sep 30, 2024 | Period end | — | 2024-09-30 | Same | Balance sheet only |

Supported annual comparisons are those printed in the supplied filing. Unsupported: any quarter, half-year, YTD, LTM, forecast, or post-September historical period. No annual figure is allocated into shorter periods.

### T4.9 — Calculation register

See `CP-1-attempt-1-calculations.txt` for exact Decimal operands, formulas and results. In summary: complete gross-profit-to-operating-profit block reconciles in each year; balance sheet balances at both dates; cash movement reconciles in all three years; FY2024 EBITDA As Defined reconciles to pretax income; and FY2024 operating cash less capex is 1,880. These are calculations, not issuer-reported values. The last figure is a simple cash-after-capex indicator, not issuer-defined free cash flow.

### T4.10 — Source-supported dashboard

| Measure | FY2024 | FY2023 | FY2022 | Source/qualification |
|---|---:|---:|---:|---|
| Net sales | 7,940 | 6,585 | 5,429 | Reported, PDF 106 |
| Gross profit | 4,672 | 3,842 | 3,099 | Reported, PDF 106 |
| Income from operations | 3,531 | 2,923 | 2,215 | Reported, PDF 106 |
| Pretax continuing income | 2,215 | 1,716 | 1,127 | Reported, PDF 106 |
| Net income | 1,715 | 1,299 | 867 | Reported, PDF 106 |
| Net cash provided by operating activities | 2,045 | 1,375 | 948 | Reported, PDF 109 |
| Capital expenditures | (165) | (139) | (119) | Reported, PDF 109 |
| Operating cash less capex | 1,880 | 1,236 | 829 | Calculated; simple subtraction only |
| Cash closing | 6,261 | 3,472 | 3,001 | Reported, PDF 109 |
| EBITDA As Defined, total company | 4,173 | 3,395 | 2,646 | Non-GAAP issuer metric, PDF 142 |
| Total debt carrying value incl. separately shown securitization | 24,880* | 19,750* | Not reconstructed | *2024: 24,296 long-term + 98 current portion + 486 securitization; 2023: 19,330 + 71 + 349. This classification sum is not gross principal. |

The statement line block between gross profit and operating profit is complete: selling and administrative expenses plus amortization of intangible assets (PDF 106). The source's cash-flow D&A/add-back rows and segment D&A do not redefine this expense block. Segment revenue and EBITDA values are retained in T4.16–17.

### Financial read-through

Annual reported activity expanded through the comparison window: net sales rose from 5,429 in FY2022 to 7,940 in FY2024, and operating income rose from 2,215 to 3,531 (income statement, PDF 106). FY2024 remained the third year in which the complete expense block can be reconciled directly from gross profit to operating income; the cost structure includes both selling and administrative expense and intangible amortization, which must remain separate. Segment sales were reported across Power & Control, Airframe and Non-aviation, with the detailed mix shown in T4.16 (PDF 141).

Cash from operations increased from 948 in FY2022 to 2,045 in FY2024, while the cash-flow statement shows FY2024 cash investment in acquisitions of 2,347 and capital expenditure of 165; net cash provided by investing activities was a 2,441 outflow (PDF 109). Thus the operating cash inflow did not translate one-for-one into cash available for debt reduction or distributions. FY2024 financing activities provided 3,171, including net issuance proceeds and term-loan proceeds, alongside dividends and dividend equivalents paid of 2,038 (PDF 109). Cash ended at 6,261, up from 3,472 a year earlier, while the balance sheet also reports 4,216 dividends payable (PDF 105, 109). This combination reflects a period-end cash balance alongside substantial declared-but-unpaid distribution liability; it is not by itself a conclusion about unrestricted liquidity or sustainable distributions.

Funding is predominantly debt-financed in the reported balance sheet: long-term debt is 24,296, with current debt classifications and securitization borrowings shown separately, while total stockholders’ deficit is 6,283 (PDF 105). Debt-note carrying amounts, original principal, maturity schedules and revolving availability are different measures (T4.18). The non-GAAP EBITDA As Defined measure reconciles to pretax income but includes specified adjustments and carries issuer-stated analytical limitations (PDF 140–142); it should not be substituted for GAAP operating profit or cash flow. These statements support an annual trend description, not a current covenant, refinancing, leverage headroom or forward liquidity conclusion.

### T4.11 — Definition conflicts and alternative positions

| Topic | Reported positions / resolution |
|---|---|
| Income statement amortization versus cash-flow D&A | Income statement specifically prints amortization of intangible assets: 161 / 139 / 136. Cash-flow statement separately prints depreciation 149 / 129 / 116 and intangible plus product certification amortization 163 / 139 / 137. Segment schedule reports total D&A 312 / 268 / 253. Retain each definition; do not substitute one for another. |
| EBITDA | No GAAP EBITDA line appears on primary statements. Issuer-reported “EBITDA As Defined” is a non-GAAP management measure including specified add-backs and reconciles through pretax income; it is not synonymous with operating income, EBITDA mechanically calculated from GAAP lines, or cash-flow D&A. |
| Debt | Balance sheet carrying categories differ from debt-note gross principal and net-of-issuance-cost/discount figures. Finance leases and government refundable advances are included in debt note schedule. Revolver commitments are not borrowings. Securitization carrying value appears separately from long-term debt. |
| Dividends | FY2024 dividends declared per share (110.00) and cash dividend payments (2,038) differ by measure and timing; dividend payable of 4,216 includes declared but unpaid amount at period end. Do not treat declared/share as cash paid or infer cash dividend per share from aggregate payment. |
| Cash after capex | 1,880 is only OCF less capital expenditures. It is not issuer-defined FCF and does not include acquisitions, dividends, debt service, or other cash demands. |
| Source dashes | Printed “—” is retained. For the specific reconciliation of a displayed total, dash may mean no amount in that statement row; this does not establish an underlying economic zero for another use. |

### T4.16 — Segment revenue register

Net sales by reportable segment, PDF 141, USD millions. These are annual segment revenue observations, not a separate entity perimeter. Intersegment sales were stated immaterial and eliminated; consolidated net sales reconcile.

| Reported line | FY2024 | FY2023 | FY2022 |
|---|---:|---:|---:|
| Power & Control — Commercial and non-aerospace OEM | 840 | 690 | 603 |
| Power & Control — Commercial and non-aerospace aftermarket | 1,198 | 1,057 | 847 |
| Power & Control — Defense | 1,903 | 1,569 | 1,423 |
| Total Power & Control | 3,941 | 3,316 | 2,873 |
| Airframe — Commercial and non-aerospace OEM | 1,280 | 989 | 715 |
| Airframe — Commercial and non-aerospace aftermarket | 1,289 | 1,112 | 785 |
| Airframe — Defense | 1,240 | 993 | 891 |
| Total Airframe | 3,809 | 3,094 | 2,391 |
| Total Non-aviation | 190 | 175 | 165 |
| Net Sales | 7,940 | 6,585 | 5,429 |

Completeness check: P&C sub-lines sum to its reported totals; Airframe sub-lines sum to its totals; the reported segment totals sum to consolidated net sales for each year. No further Non-aviation sub-line split is provided in this table; do not fabricate it.

### T4.17 — Reported EBITDA and add-back bridge

Issuer schedule, PDF 142; USD millions. The schedule presents segment EBITDA As Defined and reconciles this non-GAAP measure to continuing pretax income.

| Reported line | FY2024 | FY2023 | FY2022 |
|---|---:|---:|---:|
| Power & Control EBITDA As Defined | 2,236 | 1,866 | 1,531 |
| Airframe EBITDA As Defined | 1,962 | 1,547 | 1,121 |
| Non-aviation EBITDA As Defined | 81 | 71 | 65 |
| Total segment EBITDA As Defined | 4,279 | 3,484 | 2,717 |
| Less: Unallocated corporate EBITDA As Defined | 106 | 89 | 71 |
| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 |
| Depreciation and amortization expense | 312 | 268 | 253 |
| Interest expense-net | 1,286 | 1,164 | 1,076 |
| Acquisition transaction and integration-related expenses | 70 | 18 | 18 |
| Non-cash stock and deferred compensation expense | 217 | 157 | 184 |
| Refinancing costs | 58 | 56 | 1 |
| Other, net | 15 | 16 | (13) |
| Income from continuing operations before income taxes | 2,215 | 1,716 | 1,127 |

Definition: issuer defines EBITDA As Defined as earnings before interest, taxes, depreciation and amortization plus certain corporate non-operating items including noncash stock/deferred compensation, FX gains/losses, acquisition integration and transaction expenses, and refinancing costs (PDF 140–141). Issuer explicitly warns it is not a U.S. GAAP performance measure, has analytical limitations and should not be used in isolation or as substitute for GAAP analysis (PDF 141). FY2024 capex and D&A by segment: Power & Control capex 90 / D&A 133; Airframe 73 / 172; Non-aviation 2 / 6; Corporate dash / 1; totals 165 / 312 (PDF 142). Dash preserved.

### T4.18 — Debt/facility register

Amounts USD millions. Principal values are not carrying values. Note 10 schedule, PDF 126–133, was reviewed. The debt schedule excludes no known line within its stated coverage, but this is not a covenant analysis.

| Instrument / facility | Sep 30, 2024 amount / status | Terms / maturity / limitation |
|---|---|---|
| Trade receivable securitization | Gross 487; issuance costs (1); carrying 486; commitment 650; later October draw of remaining 162.5 is post-period | Term SOFR + 1.45%; maturity July 11, 2025; secured by substantially all domestic operations’ trade receivables; PDF 130–131. |
| Term loans aggregate | Principal 8,702; carrying 8,642 after issuance costs 25 and discount 35 | Fully drawn; revolving facility is separate; aggregate rate varies by tranche and rate election. |
| Tranche I term loans | Principal 1,871 | Maturity Aug 24, 2028; Term SOFR + 2.75%. |
| Tranche J term loans | Principal 3,632 | Maturity Feb 28, 2031; Term SOFR + 2.50%. |
| Tranche K term loans | Principal 1,699 | Maturity Mar 22, 2030; Term SOFR + 2.75%. |
| Tranche L term loans | Principal 1,500 | Maturity Jan 19, 2032; Term SOFR + 2.50%. |
| Revolving credit facility | Commitment 910; available 843; drawn 67 implied by commitment less availability, not separately stated as a direct row | Term SOFR + 2.25%; maturity Feb 2029; unused commitment fee 0.5%. Do not equate capacity with cash or availability with unrestricted liquidity. |
| 5.50% senior subordinated notes due 2027 | Principal 2,650; carrying 2,641 | Contractual coupon 5.50%, due 2027. |
| 6.75% secured notes due 2028 | Principal 2,100; carrying 2,077 | 6.75%, due 2028. |
| 4.625% senior subordinated notes due 2029 | Principal 1,200; carrying 1,194 | 4.625%, due 2029. |
| 6.375% secured notes due 2029 | Principal 2,750; carrying 2,727 | 6.375%, due 2029. |
| 4.875% senior subordinated notes due 2029 | Principal 750; carrying 746 | 4.875%, due 2029. |
| 6.875% secured notes due 2030 | Principal 1,450; carrying 1,438 | 6.875%, due 2030. |
| 7.125% secured notes due 2031 | Principal 1,000; carrying 984 | 7.125%, due 2031. |
| 6.625% secured notes due 2032 | Principal 2,200; carrying 2,180 | 6.625%, due 2032. |
| 6.00% secured notes due 2033 | Principal 1,500; carrying 1,486 | 6.00%, due 2033. |
| Government refundable advances | 17 | Repayment depends on year-over-year commercial aviation revenue growth for certain CMC Electronics product lines. Not a conventional bond facility. |
| Finance lease obligations | 262 | Carrying value equals gross in debt table; lease maturity schedule separately disclosed. |

FY2023 comparative debt-note totals: securitization gross 350/carrying 349; term loans principal 6,249/carrying 6,179; notes include 2026 secured principal 4,400, 7.50% subordinated 2027 principal 550, 5.50% subordinated 2027 principal 2,650, 2028 secured 2,100, 4.625% 2029 subordinated 1,200, 4.875% 2029 subordinated 750, 2030 secured 1,450, government advances 21 and finance leases 193. The source debt table totals gross long-term items 19,563, costs (106), discounts/premiums (56), net 19,401; current portion 71, long-term debt carrying 19,330 (PDF 127). Revolver commitments in FY2023 were 810, available 755, rate 2.50%, fee 0.5%.

Debt maturity schedule excluding finance leases at Sep 30, 2024 (PDF 133), USD millions: FY2025 93; FY2026 92; FY2027 92; FY2028 6,637; FY2029 4,768; thereafter 12,637; total 24,319. This schedule is principal maturity presentation excluding finance leases and is distinct from carrying value and current classification. Lease maturity table is separately given below.

Lease supplement (PDF 147–148): operating lease cost 22 (FY2024) and 21 (FY2023); finance lease amortization 12/9 and finance interest 16/13; total lease cost 50/43. Operating lease cash outflows from operations 21/21; finance lease operating outflows 14/10; finance lease financing outflows 6/5. At Sep 30, 2024/2023 operating lease liabilities 62/67; finance lease liabilities 262/193. Operating remaining term 5.4 years, discount rate 6.1%; finance remaining term 21.0 years, discount rate 7.0%. Finance lease maturities include future payments 541, imputed interest 279, present value 262; operating maturities future payments 75, imputed interest 13, present value 62. These are lease-note measures and not added again to debt carrying totals.

### T4.15 — Account mappings for later publication

| Source row family | Later account mapping candidate | Mapping limitation |
|---|---|---|
| Net sales | revenue | Consolidated GAAP sales; segment rows remain separate detail. |
| Cost of sales | cogs | Expense presented as positive magnitude on income statement; keep source presentation. |
| Selling/admin | sga | Distinct from D&A and acquisition add-backs. |
| Income statement amortization | depreciation_amortization only if the adapter preserves its exact narrower label | The row is intangible amortization, not total D&A. Safer as issuer-specific detail. |
| Interest expense—net | interest_expense_total | Net of interest income; cash interest separately disclosed in supplemental cash flow. |
| Income tax provision | income_tax_total | Accrual provision; cash taxes separately disclosed. |
| Net cash provided by operating activities | cfo_ncfo | Cash flow statement source line. |
| Capital expenditures | capex_total | Source outflow negative; includes capital expenditures, no maintenance/growth split. |
| Cash closing | closing_cash | Cash and cash equivalents, excludes any separately classified restricted cash; none shown as a balance-sheet row. |
| Balance sheet debt rows | current portion, short-term securitization, long-term debt | Carrying values; do not map to principal or facility commitments as equivalent amounts. |
| EBITDA As Defined | ebitda_adjusted only with explicit label/definition caveat | Do not recast as GAAP EBITDA or EBITDA derived from accounts. |

## Calculations

See the retained transcript `runs/tdg-002/CP-1-attempt-1-calculations.txt`. Principal reconciliations:

- Complete expense block: gross profit less selling/admin and intangible amortization equals reported operating income for FY2022–FY2024.
- Balance sheet: liabilities plus total deficit/equity equals assets at both balance dates.
- Cash flow: operating + investing + financing + FX equals net cash change and reconciles opening to closing cash for all three years.
- Issuer EBITDA As Defined bridge: total company measure less reported reconciliation rows equals pretax continuing income in each annual column. A detailed FY2024 transcript is retained.
- FY2024 OCF less capex yields 1,880; defined only as subtraction, not issuer FCF.
- Debt reconciliation keeps gross long-term components, costs/discounts, current portion, carrying value, and separately reported securitization borrowings distinct.

## Gaps

| Gap | Source review and affected use | Required action |
|---|---|---|
| G1 carried: rotated PDF 156 | CP-0 reported rotated non-GAAP supplemental reconciliation lacks text extraction; not reviewed visually here. It may affect supplemental historical adjusted EBITDA/add-back definitions outside PDF 142 bridge. | If that table is needed, inspect the rotated original page and verify each row before use. |
| G2 carried: glyph / full-cell validation | Statements 105–109 were extracted and key statement pages cross-checked; not every note schedule or glyph received a visual audit. A text aid can misread a cell/sign. | Targeted PDF visual check where a downstream calculation depends on a disputed or consequential cell. |
| G3 carried: source scope | Only supplied annual 10-K, no independent SEC retrieval or competing filing version examined. | Obtain additional filings only for version validation or shorter period history. |
| G4 | No quarters, YTD, LTM, transaction-specific pro forma results, covenant calculations, restricted cash schedule or full liquidity forecast in the source extraction. | Do not construct shorter periods; request relevant interim/transaction/covenant/liquidity material for those conclusions. |
| G5 | Facility disclosure does not supply a complete standardized borrowing-base/utilization calculation or a full covenant EBITDA bridge for all uses; revolver drawn amount is inferable only by commitment less available, and terms are summarized. | Review credit agreement/updated facility certificates if exact availability or covenant headroom is needed. |
| G6 | Cash-after-capex is calculable but no issuer maintenance/growth capex split or single universally defined FCF series is supplied by the statements. | Use OCF and capex source rows directly; do not label simple subtraction as issuer FCF. |
| G7 | Dividend declared, payable, and cash paid are different; no per-share cash payment allocation by period can be derived from total cash payments. | Keep separate and obtain detailed distribution records if cash dividend per share is required. |
| G8 | Complete note coverage was not performed; acquisition purchase-price effects and all add-back eligibility/cash status were not audited here. | Target specific notes and supporting schedules before transaction-adjusted earnings or earnings-quality classification. |

## Next module

**CP-1A business/transaction context:** can use entity, audited annual history, segments, acquisition cash spending and identified source limits. Transaction-specific pro forma revenue/earnings and quarterly bridge remain missing.

**CP-1B earnings delta:** can compare annual reported FY2022–FY2024 statements, including expense block and issuer EBITDA As Defined. Cannot establish quarter-to-quarter or transaction-adjusted delta; do not mix amortization/D&A definitions.

**CP-1D earnings quality:** can examine annual cash conversion, working-capital changes, cash taxes/interest, capex, acquisitions, and the issuer’s EBITDA bridge. Limited by no detailed cash/noncash testing of every add-back, no maintenance/growth capex split and no independent note-level verification.

**CP-2 fundamental credit:** can consume annual assets/liabilities, cash, debt carrying amounts, selected principal/facility/maturity terms, cash flows and reported EBITDA As Defined with its limitations. Not sufficient for covenant compliance/opinion, current liquidity, complete debt waterfall or transaction pro forma. Post-period October draw remains distinct.

**CP-MODEL publication:** has populated annual source statements, separate supplement schedules, period/unit details, mapping suggestions, calculations, definitions and explicit gaps. It can publish the supported annual actuals once adapter rules preserve all distinctions above. It must retain the gap states and must not substitute missing periods or invented calculation definitions.

These are readiness assessments for bounded use, not a claim that any downstream consumer, runtime validation gate, full credit review or final deliverable has run. This is an intermediate analytical handoff.
