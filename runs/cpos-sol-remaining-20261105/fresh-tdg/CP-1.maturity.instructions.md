# Targeted repair of your retained current CP-1 draft
The complete original actual response is below. Make only the two exact text substitutions specified here. Return the whole corrected Markdown unchanged otherwise via write_handoff. Do not regenerate any table, calculation, source identity, definition or conclusion. All exact currentupstreamhashes remain unchanged. The original financial data passed independentprimarysourcechecks; hostmanualsource comparison identified the maturity-year conflict omission only. No new analysis or provider/source access is necessary beyond verifying the cited source pp126-127/133 if needed.

Replace exactly:
This schedule excludes short-term D01 as well as finance leases. Do not use its Fiscal 2025 amount alone as total consolidated near-term debt repayments.
With exactly:
This schedule excludes short-term D01 as well as finance leases. Do not use its Fiscal 2025 amount alone as total consolidated near-term debt repayments. The reported Fiscal 2027 maturity bucket of 92 conflicts with the 2,650 principal of 5.50% senior subordinated notes labeled due 2027 in D03 (S1 pp.126–127 versus p.133). Preserve both source observations: the total reconciliation does not validate the year allocation. Do not publish this as a reconciled instrument-by-year maturity wall or move amounts between years without supporting evidence.

Replace exactly:
Use reported maturity years and source schedule now; obtain/read operative terms for exact contractual schedule and live facility status. Do not infer revolver draws from availability difference.
With exactly:
Preserve reported maturity years and the source schedule with the unresolved Fiscal 2027 92-versus-2,650 conflict; do not treat the schedule as a reconciled maturity wall. Obtain/read operative terms and issuer reconciliation for exact contractual allocation and live facility status. Do not infer revolver draws from availability difference.

Original actual retained response:
```markdown
# CP-1 — TransDigm Group Incorporated — annual financial foundation

## Request

Run `sol-fresh-tdg-complete-20261105`, CP-1 attempt 1; DeployV-r14 ancestry with the supplied CP-1 amendments and Markdown transport. Execution: November 5, 2026. Historical accounting base: September 30, 2024, with FY2024/FY2023/FY2022 annual comparisons. This is neither current underwriting nor an availability backtest. This intermediate handoff supplies the financial foundation for CP-1A, CP-1B, CP-1D, CP-2 and CP-MODEL, and subsequently CP-4 legal and CP-6 committee work. It does not perform those modules, give an investment recommendation, certify legal capacity, or claim a validation/promotion gate has run.

## Sources

### T4.1–T4.3 — Source, entity, normalization

The complete current CP-0 Markdown supplied in `task.handoffs` was consumed, including its map and G01–G10. Its supplied SHA256 identity is `8a0611cc768e043abd52c2bf4899f6b0a6d560a1c264f7fbc991fa6d10863963`; no independent handoff-byte hashing tool is exposed, so this is the supplied identity, not a claimed local rehash. No earlier CP-1 response was used. `list_sources` reanchored the annual PDF and aid to their exact current pinned hashes before source reading.

| Register / source | Identity / authority | Scope / treatment |
|---|---|---|
| T4.1 S1-annual-report.pdf | SHA256 `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`; 160 pages; issuer annual Form 10-K | Sole issuer accounting evidence in this module. Primary consolidated statements and notes control. |
| T4.1 S1-text-aid.jsonl | SHA256 `3ef306e99b330ddf535f096a1a507d9a8feadc559101e4b410d061dce67778db`; 160 pages | Derivative representation, not independent corroboration; inventory verified, not used as separate accounting evidence. |
| T4.1 CP-0 | Exact supplied identity above | Upstream scope, source paths, navigation and inherited limitations; not a substitute for extracting the statements anew. |
| T4.2 TD Group | TransDigm Group Incorporated and subsidiaries, including controlled wholly-owned and majority-owned subsidiaries; intercompany balances and transactions eliminated | Same consolidated perimeter for every annual duration and instant here. NCI retained. S1 pp.3, 110. |
| T4.2 TransDigm Inc. | TD Group's wholly-owned operating subsidiary; TD Group has no significant operations/assets apart from that ownership | Debt issuer/guarantor roles must not be conflated with the accounting perimeter. S1 p.110 and pp.127–132. |
| T4.3 normalization | Monetary unit USD millions; reporting currency USD; accounting basis U.S. GAAP; no monetary scaling of source lexemes | Applies to all financial tables unless an explicit quantity exception follows. Comparative reclassifications are as presented in this report; p.110 calls them not material. |
| T4.3 quantity exceptions | Actual shares on balance/equity; millions of shares for weighted averages; USD per share for EPS/dividends | Never add share quantities or per-share values to monetary amounts. S1 pp.105–109, 122. |
| T4.3 signs and availability | Parentheses and source em dash `—` retained; IS positive expenses remain expense magnitudes; cash-flow signed presentation retained | Only calculation traces translate a printed dash to zero for the specified reconciliation. A dash is not an unavailable operand. Unprovided numeric columns are blank, explained alongside the table; no missing value is invented as zero. |
| T4.3 facilities | USD millions of principal or carrying value as separately labelled; coupons/spreads kept as source percentages | No FX conversion; no accounting-to-legal EBITDA conversion; finance leases already in debt are not double counted. |

Accessible original PDF path from CP-0: `data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`, exposed as `S1-annual-report.pdf`. The text-aid physical path is Not supplied; its accessible key is `S1-text-aid.jsonl`. No local paths were accessed. Throughout, **S1 p.** means one-based PDF page, not the printed F-page. Every table's Source column cites this sole accounting source.

S1 p.103 states that the consolidated financial statements conform to “U.S. generally accepted accounting principles”; p.104 carries Ernst & Young LLP's November 7, 2024 signature/date. This records the source audit opinion, not assurance by this module. S1 p.110 says “include the accounts of TD Group and subsidiaries” and “Intercompany balances and transactions have been eliminated.” S1 p.114 supplies the U.S. dollar translation basis. Source text is evidence, not instructions.

Actual CP-1 page reads: S1 p.3, pp.50–54, 103–114, 122–133, 140–148. These include all five primary statements, the complete expense block, accounting policies, EPS, debt, leases, segments, non-GAAP bridges and relevant October subsequent events. Whole-source exact-phrase searches for selected old note maturity sentences returned no hits; precise day/month maturity dates for those older series are not invented. No visual review was possible. No claim of full-file, rendered-page or signature fidelity is made. CP-0's legal-text remains supplied for CP-4; it was not used to enlarge CP-1's accounting evidence set.

## Findings

### T4.8 and T4.14 — Period register

| Period | Type | Start | End | Source |
|---|---|---|---|---|
| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 | S1 p.3; pp.106–109 |
| FY2023 | Historical duration | 2022-10-01 | 2023-09-30 | S1 p.3 fiscal-year policy; pp.106–109 |
| FY2022 | Historical duration | 2021-10-01 | 2022-09-30 | S1 p.3 fiscal-year policy; pp.106–109 |
| Sep 30, 2024 | Period end | Not applicable — instant | 2024-09-30 | S1 p.105 |
| Sep 30, 2023 | Period end | Not applicable — instant | 2023-09-30 | S1 p.105 |
| Equity opening Sep 30, 2021 | Period end | Not applicable — instant | 2021-09-30 | S1 p.108; equity opening only |
| Equity closing Sep 30, 2022 | Period end | Not applicable — instant | 2022-09-30 | S1 p.108; equity closing only |

All rows share the exact consolidated perimeter, USD / monetary unit USD millions and U.S. GAAP basis in T4.2–T4.3; quantity exceptions remain separate. Instant rows have no duration start; this is not a missing-date issue. No quarterly, YTD, LTM, pro forma acquisition annualization, or FY2022 primary balance sheet is constructed. Equity balances do not supply a full FY2022 balance sheet. The FY2023 and FY2022 starts apply the explicit September fiscal-year policy, not an invented quarter convention.

### T4.4 — Income statement and comprehensive-income/equity supplements

Amounts in USD millions except the separately identified per-share and share rows. IS row IDs are stable across all three periods. Labels retain the source wording; source line wrapping and dot leaders are omitted.

| Item | FY2024 | FY2023 | FY2022 | Row ID / quantity | Source |
|---|---|---|---|---|---|
| NET SALES | 7,940 | 6,585 | 5,429 | IS01 money | S1 p.106 |
| COST OF SALES | 3,268 | 2,743 | 2,330 | IS02 expense magnitude | S1 p.106 |
| GROSS PROFIT | 4,672 | 3,842 | 3,099 | IS03 money | S1 p.106 |
| SELLING AND ADMINISTRATIVE EXPENSES | 980 | 780 | 748 | IS04 expense magnitude | S1 p.106 |
| AMORTIZATION OF INTANGIBLE ASSETS | 161 | 139 | 136 | IS05 expense magnitude | S1 p.106 |
| INCOME FROM OPERATIONS | 3,531 | 2,923 | 2,215 | IS06 money | S1 p.106 |
| INTEREST EXPENSE—NET | 1,286 | 1,164 | 1,076 | IS07 expense magnitude, net | S1 p.106 |
| REFINANCING COSTS | 58 | 56 | 1 | IS08 expense magnitude | S1 p.106 |
| OTHER (INCOME) EXPENSE | (28) | (13) | 11 | IS09 signed expense convention | S1 p.106 |
| INCOME FROM CONTINUING OPERATIONS BEFORE INCOME TAXES | 2,215 | 1,716 | 1,127 | IS10 money | S1 p.106 |
| INCOME TAX PROVISION | 500 | 417 | 261 | IS11 expense magnitude | S1 p.106 |
| INCOME FROM CONTINUING OPERATIONS | 1,715 | 1,299 | 866 | IS12 money | S1 p.106 |
| INCOME FROM DISCONTINUED OPERATIONS, NET OF TAX | — | — | 1 | IS13 money | S1 p.106 |
| NET INCOME | 1,715 | 1,299 | 867 | IS14 money, including NCI | S1 p.106 |
| LESS: NET INCOME ATTRIBUTABLE TO NONCONTROLLING INTERESTS | (1) | (1) | (1) | IS15 signed deduction | S1 p.106 |
| NET INCOME ATTRIBUTABLE TO TD GROUP | 1,714 | 1,298 | 866 | IS16 money | S1 p.106 |
| NET INCOME APPLICABLE TO TD GROUP COMMON STOCKHOLDERS | 1,481 | 1,260 | 780 | IS17 money, two-class numerator | S1 p.106 |
| Earnings per share from continuing operations—basic and diluted | 25.62 | 22.03 | 13.38 | IS18 USD per share | S1 p.106 |
| Earnings per share from discontinued operations—basic and diluted | — | — | 0.02 | IS19 USD per share | S1 p.106 |
| Earnings per share | 25.62 | 22.03 | 13.40 | IS20 USD per share | S1 p.106 |
| Cash dividends declared per common share | 110.00 | — | 18.50 | IS21 USD per share, declared not paid | S1 p.106 |
| Basic and diluted weighted-average shares outstanding | 57.8 | 57.2 | 58.2 | IS22 weighted-average shares, millions; source header “Weighted-average shares outstanding:” and subrow “Basic and diluted” | S1 p.106 |

The complete intervening operating expense block is **IS04 selling/admin plus IS05 intangible amortization**, not cost of sales and not total D&A. No other row occurs between gross profit and operating income on p.106. The calculated sum belongs in Calculations, not as an invented reported subtotal. R&D is included in selling/admin (S1 p.110); finance-lease asset amortization is included in depreciation (p.111). These disclosures do not change the source IS labels.

EPS quantity clarification, not a replacement for IS22:

| Item | FY2024 | FY2023 | FY2022 | Row ID / quantity | Source |
|---|---|---|---|---|---|
| Weighted-average common shares outstanding | 55.8 | 54.9 | 54.8 | EPS01 million shares | S1 p.122 |
| Vested options deemed participating securities | 2.0 | 2.3 | 3.4 | EPS02 million shares | S1 p.122 |
| Total shares for basic and diluted earnings per share | 57.8 | 57.2 | 58.2 | EPS03 million shares | S1 p.122 |
| Dividends declared or paid on participating securities | (233) | (38) | (86) | EPS04 monetary deduction | S1 p.122 |

S1 p.114 describes the two-class method and vested options' non-forfeitable dividend rights. Do not call IS22 common shares alone. Note 4 p.122 agrees with the primary income statement's amounts.

Comprehensive income — all monetary, USD millions:

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Net income | 1,715 | 1,299 | 867 | CI01 | S1 p.107 |
| Less: Net income attributable to noncontrolling interests | (1) | (1) | (1) | CI02 | S1 p.107 |
| Net income attributable to TD Group | 1,714 | 1,298 | 866 | CI03 | S1 p.107 |
| Foreign currency translation adjustment | 181 | 137 | (379) | CI04 | S1 p.107 |
| Unrealized (losses) gains on derivatives | (124) | 20 | 352 | CI05 | S1 p.107 |
| Pension and post-retirement benefit plans adjustment | (1) | 12 | 8 | CI06 | S1 p.107 |
| Other comprehensive income (loss), net of tax, attributable to TD Group | 56 | 169 | (19) | CI07 | S1 p.107 |
| TOTAL COMPREHENSIVE INCOME ATTRIBUTABLE TO TD GROUP | 1,770 | 1,467 | 847 | CI08 | S1 p.107 |

Stockholders' deficit — exact source order; actual shares in Common shares and Treasury shares; all other quantities USD millions. EQ IDs identify each source row and year. Source treasury share parentheses are retained rather than silently turned positive.

| Item | Period / ID | Common shares | Par | APIC | Accumulated deficit | AOCI | Treasury shares | Treasury value | NCI | Total | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BALANCE—September 30, 2021 | Sep 30, 2021 / EQ01 | 59,403,100 | 1 | 1,830 | (3,705) | (248) | (4,198,226) | (794) | 6 | (2,910) | S1 p.108 |
| Changes in noncontrolling interest of consolidated subsidiaries, net | FY2022 / EQ02 | — | — | — | — | — | — | — | 1 | 1 | S1 p.108 |
| Special dividends ($18.50 per share) and vested dividend equivalents declared | FY2022 / EQ03 | — | — | — | (1,045) | — | — | — | — | (1,045) | S1 p.108 |
| Accrued unvested dividend equivalents and other | FY2022 / EQ04 | — | — | — | (30) | — | — | — | — | (30) | S1 p.108 |
| Compensation expense recognized for employee stock options | FY2022 / EQ05 | — | — | 151 | — | — | — | — | — | 151 | S1 p.108 |
| Stock-based compensation activity | FY2022 / EQ06 | 646,585 | — | 132 | — | — | — | — | — | 132 | S1 p.108 |
| Stock repurchases under repurchase program | FY2022 / EQ07 | — | — | — | — | — | (1,490,413) | (912) | — | (912) | S1 p.108 |
| Net income attributable to TD Group | FY2022 / EQ08 | — | — | — | 866 | — | — | — | — | 866 | S1 p.108 |
| Foreign currency translation adjustment, net of tax | FY2022 / EQ09 | — | — | — | — | (379) | — | — | — | (379) | S1 p.108 |
| Unrealized gain on derivatives, net of tax | FY2022 / EQ10 | — | — | — | — | 352 | — | — | — | 352 | S1 p.108 |
| Pension and post-retirement benefit plans adjustment, net of tax | FY2022 / EQ11 | — | — | — | — | 8 | — | — | — | 8 | S1 p.108 |
| BALANCE—September 30, 2022 | Sep 30, 2022 / EQ12 | 60,049,685 | 1 | 2,113 | (3,914) | (267) | (5,688,639) | (1,706) | 7 | (3,766) | S1 p.108 |
| Changes in noncontrolling interest of consolidated subsidiaries, net | FY2023 / EQ13 | — | — | — | — | — | — | — | (1) | (1) | S1 p.108 |
| Accrued unvested dividend equivalents and other | FY2023 / EQ14 | — | — | — | (5) | — | — | — | — | (5) | S1 p.108 |
| Compensation expense recognized for employee stock options | FY2023 / EQ15 | — | — | 112 | — | — | — | — | — | 112 | S1 p.108 |
| Stock-based compensation activity | FY2023 / EQ16 | 945,828 | — | 215 | — | — | — | — | — | 215 | S1 p.108 |
| Net income attributable to TD Group | FY2023 / EQ17 | — | — | — | 1,298 | — | — | — | — | 1,298 | S1 p.108 |
| Foreign currency translation adjustment, net of tax | FY2023 / EQ18 | — | — | — | — | 137 | — | — | — | 137 | S1 p.108 |
| Unrealized gain on derivatives, net of tax | FY2023 / EQ19 | — | — | — | — | 20 | — | — | — | 20 | S1 p.108 |
| Pension and post-retirement benefit plans adjustment, net of tax | FY2023 / EQ20 | — | — | — | — | 12 | — | — | — | 12 | S1 p.108 |
| BALANCE—September 30, 2023 | Sep 30, 2023 / EQ21 | 60,995,513 | 1 | 2,440 | (2,621) | (98) | (5,688,639) | (1,706) | 6 | (1,978) | S1 p.108 |
| Changes in noncontrolling interest of consolidated subsidiaries, net | FY2024 / EQ22 | — | — | — | — | — | — | — | 1 | 1 | S1 p.108 |
| Special dividends ($35.00 and $75.00 per share) and vested dividend equivalents declared | FY2024 / EQ23 | — | — | — | (6,368) | — | — | — | — | (6,368) | S1 p.108 |
| Accrued unvested dividend equivalents and other | FY2024 / EQ24 | — | — | — | (87) | — | — | — | — | (87) | S1 p.108 |
| Compensation expense recognized for employee stock options | FY2024 / EQ25 | — | — | 134 | — | — | — | — | — | 134 | S1 p.108 |
| Stock-based compensation activity | FY2024 / EQ26 | 909,320 | — | 245 | — | — | — | — | — | 245 | S1 p.108 |
| Net income attributable to TD Group | FY2024 / EQ27 | — | — | — | 1,714 | — | — | — | — | 1,714 | S1 p.108 |
| Foreign currency translation adjustment, net of tax | FY2024 / EQ28 | — | — | — | — | 181 | — | — | — | 181 | S1 p.108 |
| Unrealized loss on derivatives, net of tax | FY2024 / EQ29 | — | — | — | — | (124) | — | — | — | (124) | S1 p.108 |
| Pension and post-retirement benefit plans adjustment, net of tax | FY2024 / EQ30 | — | — | — | — | (1) | — | — | — | (1) | S1 p.108 |
| BALANCE—September 30, 2024 | Sep 30, 2024 / EQ31 | 61,904,833 | 1 | 2,819 | (7,362) | (42) | (5,688,639) | (1,706) | 7 | (6,283) | S1 p.108 |

### T4.5 — Cash-flow statement

All rows USD millions. CF42 uses the Model's sentence-case alias for the source's uppercase closing-cash label; CF43–CF44 omit “the” from the source supplemental “during the period” labels. Amounts and definitions are unchanged. Other labels retain source wording. CF37/CF38 also preserve the source cash-flow sign.

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Net income | 1,715 | 1,299 | 867 | CF01 | S1 p.109 |
| Income from discontinued operations, net of tax | — | — | (1) | CF02 | S1 p.109 |
| Depreciation | 149 | 129 | 116 | CF03 | S1 p.109 |
| Amortization of intangible assets and product certification costs | 163 | 139 | 137 | CF04 | S1 p.109 |
| Amortization of debt issuance costs, original issue discount and premium | 40 | 41 | 34 | CF05 | S1 p.109 |
| Amortization of inventory step-up | 21 | 2 | 3 | CF06 | S1 p.109 |
| Amortization of loss contract reserves | (35) | (34) | (39) | CF07 | S1 p.109 |
| Refinancing costs | 58 | 56 | 1 | CF08 | S1 p.109 |
| Gain on sale of businesses, net | (11) | — | (7) | CF09 | S1 p.109 |
| Non-cash stock and deferred compensation expense | 217 | 157 | 184 | CF10 | S1 p.109 |
| Deferred income taxes | 10 | 3 | (22) | CF11 | S1 p.109 |
| Foreign currency exchange losses (gains) | 20 | 14 | (40) | CF12 | S1 p.109 |
| (Gain) loss on settlement of the Esterline Retirement Plan (the “ERP”) | — | (9) | 22 | CF13 | S1 p.109 |
| Cash refund (contribution) for the ERP settlement, net | — | 9 | (16) | CF14 | S1 p.109 |
| Trade accounts receivable | (84) | (212) | (190) | CF15 | S1 p.109 |
| Inventories | (104) | (261) | (134) | CF16 | S1 p.109 |
| Income taxes (receivable) payable | (62) | 168 | 58 | CF17 | S1 p.109 |
| Other assets | (60) | (44) | (56) | CF18 | S1 p.109 |
| Accounts payable | (11) | 12 | 58 | CF19 | S1 p.109 |
| Accrued interest | 60 | (45) | (21) | CF20 | S1 p.109 |
| Accrued and other liabilities | (41) | (49) | (6) | CF21 | S1 p.109 |
| Net cash provided by operating activities | 2,045 | 1,375 | 948 | CF22 | S1 p.109 |
| Capital expenditures | (165) | (139) | (119) | CF23 | S1 p.109 |
| Acquisition of businesses, net of cash acquired | (2,347) | (762) | (437) | CF24 | S1 p.109 |
| Other investing transactions | 71 | 1 | 3 | CF25 | S1 p.109 |
| Net cash used in investing activities | (2,441) | (900) | (553) | CF26 | S1 p.109 |
| Proceeds from exercise of stock options | 245 | 215 | 132 | CF27 | S1 p.109 |
| Dividends and dividend equivalent payments | (2,038) | (38) | (1,091) | CF28 | S1 p.109 |
| Repurchases of common stock | — | — | (912) | CF29 | S1 p.109 |
| Proceeds from issuance of senior secured notes, net | 7,373 | 3,504 | — | CF30 | S1 p.109 |
| Repayments of senior secured notes | (4,400) | (1,122) | — | CF31 | S1 p.109 |
| Repayments of senior subordinated notes, net | (550) | (1,459) | — | CF32 | S1 p.109 |
| Repayment on revolving credit facility | — | — | (200) | CF33 | S1 p.109 |
| Proceeds from trade receivable securitization facility, net | 137 | — | — | CF34 | S1 p.109 |
| Proceeds from term loans, net | 6,815 | 6,238 | — | CF35 | S1 p.109 |
| Repayment on term loans | (4,403) | (7,334) | (75) | CF36 | S1 p.109 |
| Financing costs and other, net | (8) | (20) | (2) | CF37 | S1 p.109 |
| Net cash provided by (used in) financing activities | 3,171 | (16) | (2,148) | CF38 | S1 p.109 |
| EFFECT OF EXCHANGE RATE CHANGES ON CASH AND CASH EQUIVALENTS | 14 | 12 | (33) | CF39 | S1 p.109 |
| NET INCREASE (DECREASE) IN CASH AND CASH EQUIVALENTS | 2,789 | 471 | (1,786) | CF40 | S1 p.109 |
| CASH AND CASH EQUIVALENTS, BEGINNING OF PERIOD | 3,472 | 3,001 | 4,787 | CF41 | S1 p.109 |
| Cash and cash equivalents, end of period | 6,261 | 3,472 | 3,001 | CF42 | S1 p.109 |
| Cash paid during period for interest, net | 1,158 | 1,160 | 1,057 | CF43 | S1 p.109 |
| Cash paid during period for income taxes, net of refunds | 539 | 260 | 220 | CF44 | S1 p.109 |

CF15–CF21 are explicitly “Changes in assets/liabilities, net of effects from acquisitions and sales of businesses.” They are not equal to simple year-end balance-sheet movements. The operating/investing/financing section headings and adjustment headers carry no amounts. All quantitative rows on p.109, including the supplemental disclosures, are retained above.

### T4.6 — Balance sheet

USD millions except actual shares contained in stock descriptions. Model aliases use sentence case for Long-term debt and the source's initial-cap Short-term borrowings line. BS21/BS25 descriptions preserve the original share disclosures.

| Item | Sep 30, 2024 | Sep 30, 2023 | Row ID | Source |
|---|---|---|---|---|
| Cash and cash equivalents | 6,261 | 3,472 | BS01 | S1 p.105 |
| Trade accounts receivable—Net | 1,381 | 1,230 | BS02 | S1 p.105 |
| Inventories—Net | 1,876 | 1,616 | BS03 | S1 p.105 |
| Prepaid expenses and other | 511 | 420 | BS04 | S1 p.105 |
| Total current assets | 10,029 | 6,738 | BS05 | S1 p.105 |
| PROPERTY, PLANT AND EQUIPMENT—NET | 1,488 | 1,255 | BS06 | S1 p.105 |
| GOODWILL | 10,419 | 8,988 | BS07 | S1 p.105 |
| OTHER INTANGIBLE ASSETS—NET | 3,446 | 2,747 | BS08 | S1 p.105 |
| OTHER NON-CURRENT ASSETS | 204 | 242 | BS09 | S1 p.105 |
| TOTAL ASSETS | 25,586 | 19,970 | BS10 | S1 p.105 |
| Current portion of long-term debt | 98 | 71 | BS11 | S1 p.105 |
| Short-term borrowings—trade receivable securitization facility | 486 | 349 | BS12 | S1 p.105 |
| Accounts payable | 323 | 305 | BS13 | S1 p.105 |
| Dividends payable | 4,216 | — | BS14 | S1 p.105 |
| Accrued and other current liabilities | 1,216 | 854 | BS15 | S1 p.105 |
| Total current liabilities | 6,339 | 1,579 | BS16 | S1 p.105 |
| Long-term debt | 24,296 | 19,330 | BS17 | S1 p.105 |
| DEFERRED INCOME TAXES | 766 | 627 | BS18 | S1 p.105 |
| OTHER NON-CURRENT LIABILITIES | 468 | 412 | BS19 | S1 p.105 |
| Total liabilities | 31,869 | 21,948 | BS20 | S1 p.105 |
| Common stock | 1 | 1 | BS21; source description: $.01 par value; authorized 224,400,000 shares; issued 61,904,833 and 60,995,513 at September 30, 2024 and September 30, 2023, respectively | S1 p.105 |
| Additional paid-in capital | 2,819 | 2,440 | BS22 | S1 p.105 |
| Accumulated deficit | (7,362) | (2,621) | BS23 | S1 p.105 |
| Accumulated other comprehensive loss | (42) | (98) | BS24 | S1 p.105 |
| Treasury stock, at cost | (1,706) | (1,706) | BS25; source description: 5,688,639 shares at September 30, 2024 and September 30, 2023, respectively | S1 p.105 |
| Total TD Group stockholders’ deficit | (6,290) | (1,984) | BS26 | S1 p.105 |
| NONCONTROLLING INTERESTS | 7 | 6 | BS27 | S1 p.105 |
| Total stockholders’ deficit | (6,283) | (1,978) | BS28 | S1 p.105 |
| TOTAL LIABILITIES AND STOCKHOLDERS’ DEFICIT | 25,586 | 19,970 | BS29 | S1 p.105 |

### T4.16 — Segment revenue and completeness

USD millions; all three reportable segments retained exactly once. Power & Control and Airframe are the aerospace businesses; Non-aviation remains separate, not dropped into corporate. S1 pp.140–141 describe each business, internal reporting and immaterial intersegment sales.

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Power & Control — Commercial and non-aerospace OEM | 840 | 690 | 603 | SG01 | S1 p.141 |
| Power & Control — Commercial and non-aerospace aftermarket | 1,198 | 1,057 | 847 | SG02 | S1 p.141 |
| Power & Control — Defense | 1,903 | 1,569 | 1,423 | SG03 | S1 p.141 |
| Total Power & Control | 3,941 | 3,316 | 2,873 | SG04 | S1 p.141 |
| Airframe — Commercial and non-aerospace OEM | 1,280 | 989 | 715 | SG05 | S1 p.141 |
| Airframe — Commercial and non-aerospace aftermarket | 1,289 | 1,112 | 785 | SG06 | S1 p.141 |
| Airframe — Defense | 1,240 | 993 | 891 | SG07 | S1 p.141 |
| Total Airframe | 3,809 | 3,094 | 2,391 | SG08 | S1 p.141 |
| Total Non-aviation | 190 | 175 | 165 | SG09 | S1 p.141 |
| Net Sales | 7,940 | 6,585 | 5,429 | SG10 | S1 p.141 |
| Power & Control EBITDA As Defined | 2,236 | 1,866 | 1,531 | SG11 | S1 p.142 |
| Airframe EBITDA As Defined | 1,962 | 1,547 | 1,121 | SG12 | S1 p.142 |
| Non-aviation EBITDA As Defined | 81 | 71 | 65 | SG13 | S1 p.142 |
| Total segment EBITDA As Defined | 4,279 | 3,484 | 2,717 | SG14 | S1 p.142 |
| Less: Unallocated corporate EBITDA As Defined | 106 | 89 | 71 | SG15 magnitude deducted | S1 p.142 |
| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 | SG16 | S1 p.142 |

### T4.17 — Reported EBITDA and add-back definitions

**Net income to EBITDA and EBITDA As Defined, reported (PDF 53):**

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Net Income | 1,715 | 1,299 |  | EB01 | S1 p.53 |
| Depreciation and amortization expense | 312 | 268 |  | EB02 | S1 p.53 |
| Interest expense-net | 1,286 | 1,164 |  | EB03 | S1 p.53 |
| Income tax provision | 500 | 417 |  | EB04 | S1 p.53 |
| EBITDA | 3,813 | 3,148 |  | EB05 | S1 p.53 |
| Acquisition transaction and integration-related expenses | 70 | 18 |  | EB06 | S1 p.53 |
| Non-cash stock and deferred compensation expense | 217 | 157 |  | EB07 | S1 p.53 |
| Refinancing costs | 58 | 56 |  | EB08 | S1 p.53 |
| Other, net | 15 | 16 |  | EB09 | S1 p.53 |
| EBITDA As Defined | 4,173 | 3,395 |  | EB10 | S1 p.53 |

Blank FY2022 cells mean p.53 does not supply that comparison. They do not mean zero. FY2022 EBITDA As Defined and its constituent deductions are separately reported on p.142 below; no FY2022 ordinary EBITDA is silently filled into the p.53 reported bridge.

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Total Company EBITDA As Defined | 4,173 | 3,395 | 2,646 | NB01 | S1 p.142 |
| Depreciation and amortization expense | 312 | 268 | 253 | NB02 | S1 p.142 |
| Interest expense-net | 1,286 | 1,164 | 1,076 | NB03 | S1 p.142 |
| Acquisition transaction and integration-related expenses | 70 | 18 | 18 | NB04 | S1 p.142 |
| Non-cash stock and deferred compensation expense | 217 | 157 | 184 | NB05 | S1 p.142 |
| Refinancing costs | 58 | 56 | 1 | NB06 | S1 p.142 |
| Other, net | 15 | 16 | (13) | NB07 | S1 p.142 |
| Income from continuing operations before income taxes | 2,215 | 1,716 | 1,127 | NB08 | S1 p.142 |

The NB deduction rows are positive magnitudes to subtract, except the FY2022 negative Other, net, which reverses on subtraction. This is a reported continuing-pretax bridge, not the p.53 net-income bridge.

S1 p.53 footnotes define EB06 as acquisition integration, relocation, transaction/diligence and inventory-step-up costs; EB07 as stock-incentive and deferred compensation; EB08 as new issuance, extinguishment, refinancing and amendment expenses; EB09 primarily as FX transactions, payroll withholding taxes on dividend equivalents/options, non-service pension, deferred compensation payments and miscellaneous income/expense. These are issuer adjustment descriptions, not independent acceptance of nonrecurrence or cash savings. S1 p.52 expressly says the measure excludes cash integration costs and does not represent discretionary cash; pp.140–141 call it the management segment performance measure and warn it is non-GAAP.

The reported cash-to-EBITDA bridge is also retained to prevent definition substitution:

| Item | FY2024 | FY2023 | FY2022 | Row ID | Source |
|---|---|---|---|---|---|
| Net cash provided by operating activities | 2,045 | 1,375 |  | CB01 | S1 p.54 |
| Changes in assets and liabilities, net of effects from acquisitions and sales of businesses | 272 | 415 |  | CB02 | S1 p.54 |
| Interest expense-net | 1,246 | 1,123 |  | CB03 | S1 p.54 |
| Income tax provision—current | 490 | 414 |  | CB04 | S1 p.54 |
| Loss contract amortization | 35 | 34 |  | CB05 | S1 p.54 |
| Non-cash stock and deferred compensation expense | (217) | (157) |  | CB06 | S1 p.54 |
| Refinancing costs | (58) | (56) |  | CB07 | S1 p.54 |
| EBITDA | 3,813 | 3,148 |  | CB08 | S1 p.54 |

CB08 then uses EB06–EB09 to reach EB10, with the same figures as p.53. FY2022 is not provided on p.54. CB03 excludes debt-cost/premium/discount amortization per its footnote; it is neither IS07 nor cash interest CF43.

### T4.18 — Debt and facility register

USD millions. Principal/gross and net carrying amounts are separate observations. Each dash is printed, not an inferred unavailable value. D01 securitization is outside D14's long-term debt subtotal. Individual tranche carrying values are not allocated from the aggregate term-loan carrying value.

| Item / ID | Principal 2024 | Debt costs 2024 | OID / premium 2024 | Carrying 2024 | Principal 2023 | Debt costs 2023 | OID / premium 2023 | Carrying 2023 | Source |
|---|---|---|---|---|---|---|---|---|---|
| D01 Short-term securitization | 487 | (1) | — | 486 | 350 | (1) | — | 349 | S1 pp.126–127 |
| D02 Term loans | 8,702 | (25) | (35) | 8,642 | 6,249 | (22) | (48) | 6,179 | S1 pp.126–127 |
| D03 5.50% senior subordinated notes due 2027 | 2,650 | (9) | — | 2,641 | 2,650 | (12) | — | 2,638 | S1 pp.126–127 |
| D04 6.75% secured notes due 2028 | 2,100 | (15) | (8) | 2,077 | 2,100 | (19) | (10) | 2,071 | S1 pp.126–127 |
| D05 4.625% senior subordinated notes due 2029 | 1,200 | (6) | — | 1,194 | 1,200 | (7) | — | 1,193 | S1 pp.126–127 |
| D06 6.375% secured notes due 2029 | 2,750 | (22) | (1) | 2,727 |  |  |  |  | S1 p.126 |
| D07 4.875% senior subordinated notes due 2029 | 750 | (4) | — | 746 | 750 | (5) | — | 745 | S1 pp.126–127 |
| D08 6.875% secured notes due 2030 | 1,450 | (12) | — | 1,438 | 1,450 | (14) | — | 1,436 | S1 pp.126–127 |
| D09 7.125% secured notes due 2031 | 1,000 | (9) | (7) | 984 |  |  |  |  | S1 p.126 |
| D10 6.625% secured notes due 2032 | 2,200 | (20) | — | 2,180 |  |  |  |  | S1 p.126 |
| D11 6.00% secured notes due 2033 | 1,500 | (14) | — | 1,486 |  |  |  |  | S1 p.126 |
| D12 Government refundable advances | 17 | — | — | 17 | 21 | — | — | 21 | S1 pp.126–127 |
| D13 Finance lease obligations | 262 | — | — | 262 | 193 | — | — | 193 | S1 pp.126–127 |
| D14 Long-term debt including current portion, subtotal | 24,581 | (136) | (51) | 24,394 | 19,563 | (106) | (56) | 19,401 | S1 pp.126–127 |
| D15 Less: current portion | 99 | (1) | — | 98 | 71 | — | — | 71 | S1 pp.126–127 |
| D16 Long-term debt | 24,482 | (135) | (51) | 24,296 | 19,492 | (106) | (56) | 19,330 | S1 pp.126–127 |
| D17 6.25% secured notes due 2026 |  |  |  |  | 4,400 | (25) | 2 | 4,377 | S1 p.127 |
| D18 7.50% senior subordinated notes due 2027 |  |  |  |  | 550 | (2) | — | 548 | S1 p.127 |

Blank cells reflect no row for that instrument in the respective dated debt table, not an invented balance. The redemption of D17 and D18 is expressly disclosed on pp.129–130; new D06/D09/D10/D11 issuance is expressly disclosed on pp.127–131. Gross debt including D01 is calculated separately; D14 must not be called total consolidated debt.

| Facility / ID | Currency / observation at Sep 30, 2024 | Rate / terms as reported | Maturity / limitation | Source |
|---|---|---|---|---|
| F01 Term tranche I | USD; principal 1,871; 2023 4,536 | Term SOFR plus 2.75%; quarterly principal 5 after Amendment 16 | August 24, 2028; no tranche-level carrying allocation | S1 pp.129–132 |
| F02 Term tranche J | USD; principal 3,632; 2023 — | Term SOFR plus 2.50%; quarterly principal 9 after Amendment 16 | February 28, 2031 | S1 pp.130, 132 |
| F03 Term tranche K | USD; principal 1,699; 2023 — | Term SOFR plus 2.75%; quarterly principal 4 | March 22, 2030 | S1 pp.129, 132 |
| F04 Term tranche L | USD; principal 1,500; 2023 — | Term SOFR plus 2.50%; issued at 0.25% discount | January 19, 2032 | S1 pp.131–132 |
| F05 Replaced tranche H | USD; 2024 —; 2023 principal 1,713 | Historical Term SOFR plus 3.25%; replaced by K in FY2024 | Historical February 22, 2027 | S1 p.132 |
| F06 Revolver | USD; commitments 910; reported available 843; 2023 commitments 810, available 755 | Term SOFR plus 2.25% after Amendment 14; unused fee 0.5%; no drawn balance is inferred from commitment less availability | February 2029; availability is a historical reported amount, not current or unrestricted liquidity | S1 pp.128, 132 |
| F07 Securitization | USD; capacity 650; gross drawn 487; carrying 486 | Term SOFR plus 1.45%; 2024 applicable rate 6.73%; substantially all domestic trade receivables collateral; annual extension right conditional on no termination event | July 11, 2025; availability depends on eligible receivables, not merely nominal capacity minus drawn | S1 pp.130–131 |
| F08 2031 secured notes | USD; D09 | 7.125%; June 1 / December 1 interest payments | December 1, 2031 | S1 pp.127–128 |
| F09 2029 secured notes | USD; D06 | 6.375%; March 1 / September 1; includes additional 550 issuance | March 1, 2029 | S1 pp.128–130 |
| F10 2032 secured notes | USD; D10 | 6.625%; March 1 / September 1 | March 1, 2032 | S1 p.128 |
| F11 2033 secured notes | USD; D11 | 6.00%; September 19, 2024 issuance | 2033; exact day/month not retained from reviewed annual pages | S1 pp.126, 131 |
| F12 Other outstanding notes | USD; D03/D04/D05/D07/D08 | Fixed coupons and maturity years in D-register labels; secured versus senior subordinated kept separate | Exact day/month maturity and call schedules Not supplied in reviewed annual passages; operative instruments needed for legal analysis | S1 pp.126, 132; unsuccessful phrase searches noted in Sources |
| F13 Government advances | USD reporting value 17, comparative 21 | Repayment tied to specified Canadian commercial-aviation revenue growth; not an ordinary bullet bond | No contractual schedule reconstructed | S1 p.131 |

S1 p.132 states existing adjusted Term SOFR loans are not subject to a floor and permits alternate-base-rate or adjusted Term SOFR options. It also reports compliance with secured and subordinated note covenants. This is an issuer statement, not a recalculated covenant test, certificate, or CP-4 opinion. S1 p.52 links its EBITDA As Defined to a revolver financial covenant under certain circumstances on a pro forma basis; this does not establish legal basket capacity or unrestricted-group EBITDA.

Long-term debt repayment schedule, **excluding finance leases** (source-reported USD millions, S1 p.133):

| Item | Amount | Row ID | Source |
|---|---|---|---|
| Fiscal 2025 | 93 | MAT01 | S1 p.133 |
| Fiscal 2026 | 92 | MAT02 | S1 p.133 |
| Fiscal 2027 | 92 | MAT03 | S1 p.133 |
| Fiscal 2028 | 6,637 | MAT04 | S1 p.133 |
| Fiscal 2029 | 4,768 | MAT05 | S1 p.133 |
| Thereafter | 12,637 | MAT06 | S1 p.133 |
| Total | 24,319 | MAT07 | S1 p.133 |

This schedule excludes short-term D01 as well as finance leases. Do not use its Fiscal 2025 amount alone as total consolidated near-term debt repayments.

### Lease observations and material non-debt funding items

All monetary amounts USD millions. FY2022 columns are not supplied in the reviewed Note 17 tables; no lease estimate is filled.

| Item | FY2024 | FY2023 | FY2022 | Row ID / classification | Source |
|---|---|---|---|---|---|
| Operating lease cost | 22 | 21 |  | LS01; cost of sales or selling/admin | S1 p.147 |
| Finance lease amortization of leased assets | 12 | 9 |  | LS02; cost of sales | S1 p.147 |
| Finance lease interest | 16 | 13 |  | LS03; interest expense-net | S1 p.147 |
| Total lease cost | 50 | 43 |  | LS04 | S1 p.147 |
| Operating cash outflows from operating leases | 21 | 21 |  | LS05 | S1 p.147 |
| Operating cash outflows from finance leases | 14 | 10 |  | LS06 | S1 p.147 |
| Financing cash outflows from finance leases | 6 | 5 |  | LS07; not a second capex deduction | S1 p.147 |
| ROU assets obtained for operating lease obligations | 21 | 17 |  | LS08 noncash | S1 p.147 |
| ROU assets obtained for finance lease obligations | 83 | 48 |  | LS09 noncash | S1 p.147 |

| Item | Sep 30, 2024 | Sep 30, 2023 | Row ID / classification | Source |
|---|---|---|---|---|
| Operating lease ROU assets | 61 | 64 | LS10; within BS09 | S1 p.148 |
| Current operating lease liabilities | 19 | 16 | LS11; within BS15 | S1 p.148 |
| Long-term operating lease liabilities | 43 | 51 | LS12; within BS19 | S1 p.148 |
| Total operating lease liabilities | 62 | 67 | LS13; not included in calculated debt K07 | S1 p.148 |
| Finance lease ROU assets, net | 252 | 176 | LS14; within BS06 | S1 p.148 |
| Current finance lease liabilities | 6 | 5 | LS15; within BS11 | S1 p.148 |
| Long-term finance lease liabilities | 256 | 188 | LS16; within BS17 | S1 p.148 |
| Total finance lease liabilities | 262 | 193 | LS17; already in D13 | S1 p.148 |

At September 30, 2024, remaining operating/finance lease terms are 5.4years / 21.0 years and discount rates 6.1% / 7.0%, respectively (S1 p.148; source spelling retained for 5.4years).

| Lease maturity | Operating | Finance | Source |
|---|---|---|---|
| 2025 | 22 | 20 | S1 p.148 |
| 2026 | 16 | 21 | S1 p.148 |
| 2027 | 12 | 22 | S1 p.148 |
| 2028 | 7 | 23 | S1 p.148 |
| 2029 | 5 | 23 | S1 p.148 |
| Thereafter | 13 | 432 | S1 p.148 |
| Total future minimum lease payments | 75 | 541 | S1 p.148 |
| Less: imputed interest | 13 | 279 | S1 p.148 |
| Present value of lease liabilities reported | 62 | 262 | S1 p.148 |

All liability lines BS11–BS20 were reviewed for funding relevance, not just financial debt. Material non-debt stories are as follows:

| Item / ID | Documented fact | Financial interpretation / limitation | Source |
|---|---|---|---|
| BS14 dividend funding / SE01 | Dividends payable 4,216 at the base date, source dash comparative. Note 16 reports common special dividends declared 6,153, of which 1,937 paid in FY2024 and 4,216 accrued | Cash at the base date precedes a material declared cash payment; it cannot be treated as permanently surplus cash. This is not a legal-capacity finding. | S1 pp.105, 146 |
| BS15 accrued liabilities / ND01 | Total 1,216 / 854. Components 2024 / 2023: compensation 256 / 217; interest 185 / 125; dividend equivalents 180 / 19; contract liabilities 168 / 79; tax payable 108 / 138; loss contracts 50 / 42; warranties 36 / 28; environmental/litigation 27 / 16; operating leases 19 / 16; FX forwards 1 / 5; other 186 / 169 | Non-debt cash and performance obligations remain relevant alongside debt. Do not reclassify the whole block as borrowing. Contract liabilities include advance receipts; Note 4 does not determine their cash repayment profile. | S1 p.125; contract-liability context p.122 |
| BS18 deferred taxes / ND02 | 766 / 627 | Accounting liability, not a scheduled borrowing; no assumption that all is payable within a liquidity horizon. | S1 pp.105, 113 |
| BS19 other noncurrent liabilities / ND03 | 468 / 412; disclosed subcomponents include stock-based-compensation liabilities 102 / 48 and operating leases 43 / 51; FY2024 future dividend equivalents 47 noncurrent | Liability-based compensation and dividend-equivalent obligations can require later resources. Full decomposition of BS19 has not been established; do not label its remainder pension debt. | S1 pp.105, 143, 146, 148 |
| SE02 October securitization draw | Remaining 162.5 drawn in October 2024 | Post-period financing only; not included in BS12 or FY2024 CF34. | S1 p.131 |
| SE03 October dividends | 4,216 special dividend and 132 dividend equivalents paid in October 2024 | Post-period cash payments only; not subtracted again from reported FY2024 cash or blended into CF28. No complete post-event cash balance is computed. | S1 p.146 |

### T4.10 — Source-supported dashboard

Reported rows cite source; calculated rows reference the traces below. Monetary values USD millions; margins/conversions are fractions, not percentages. Rounded analytical ratios are displayed to six decimal places, with unrounded Decimal-38 outputs retained in the calculation execution record. Unprovided FY2022 balance-dependent quantities and ordinary reported EBITDA are blank; reasons follow the table.

| Item | FY2024 | FY2023 | FY2022 | Status / row reference | Source |
|---|---|---|---|---|---|
| Revenue | 7,940 | 6,585 | 5,429 | Reported IS01 | S1 p.106 |
| Operating income | 3,531 | 2,923 | 2,215 | Reported IS06 | S1 p.106 |
| EBITDA, issuer ordinary | 3,813 | 3,148 |  | Reported EB05; FY2022 not in p.53 | S1 p.53 |
| EBITDA As Defined, total company | 4,173 | 3,395 | 2,646 | Reported SG16/NB01 | S1 p.142 |
| CFO | 2,045 | 1,375 | 948 | Reported CF22 | S1 p.109 |
| Capex, signed | (165) | (139) | (119) | Reported CF23 | S1 p.109 |
| Cash, year end | 6,261 | 3,472 | 3,001 | Reported CF42; FY2022 not a full balance sheet | S1 p.109 |
| Below-gross-profit operating expense block | 1,141 | 919 | 884 | Calculated K01 | IS04–IS05, S1 p.106 |
| FCF = CFO plus signed capex | 1,880 | 1,236 | 829 | Calculated K02; before acquisitions/distributions | CF22–CF23, S1 p.109 |
| Changes in assets/liabilities cash effect | (302) | (431) | (291) | Calculated K03, complete CF15–CF21 block | S1 p.109 |
| Gross margin | 0.588413 | 0.583447 | 0.570823 | Calculated K04 | IS03 / IS01 |
| Operating margin | 0.444710 | 0.443888 | 0.407994 | Calculated K05 | IS06 / IS01 |
| EBITDA As Defined margin | 0.525567 | 0.515566 | 0.487383 | Calculated K06 | SG16 / IS01 |
| Debt carrying value including securitization and finance leases | 24,880 | 19,750 |  | Calculated K07 | BS11 + BS12 + BS17 |
| Cash-netted carrying debt | 18,619 | 16,278 |  | Calculated K08, unrestricted-cash assumption not established | K07 − BS01 |
| Carrying debt / EBITDA As Defined | 5.962138 | 5.817378 |  | Calculated K09; analytical, not covenant | K07 / SG16 |
| Cash-netted carrying debt / EBITDA As Defined | 4.461778 | 4.794698 |  | Calculated K10; mechanical cash netting only | K08 / SG16 |
| Operating income / net interest expense | 2.745723 | 2.511168 | 2.058550 | Calculated K11; not cash-interest covenant coverage | IS06 / IS07 |
| CFO / EBITDA As Defined | 0.490055 | 0.405007 | 0.358277 | Calculated K12; cash conversion, not covenant | CF22 / SG16 |

FY2022 K07–K10 cannot be calculated from the supplied primary balance sheets; no debt balance is inferred from cash-flow issuance/repayments. FCF is a bounded analyst definition, not issuer reported FCF, FFO, maintenance FCF, cash available for dividends, or debt-service capacity. No maintenance/growth split, adjusted CFO, FFO, covenant headroom, unrestricted cash, or current liquidity is supplied by these calculations.

### T4.11 — Definitions and alternative positions

| Issue | Positions retained | Treatment / affected work |
|---|---|---|
| D&A scope | IS05 161 / 139 / 136 is intangible amortization only; CF04 163 / 139 / 137 includes product certification; CF03 149 / 129 / 116 is depreciation. NB02 312 / 268 / 253 is reported bridge D&A | CF03 + CF04 reconciles NB02; do not replace IS05 with NB02 in the expense block. S1 pp.106, 109, 124, 142. |
| Ordinary EBITDA vs operating income | EB05 starts from net income, not IS06; includes below-operating items before selected add-backs | EB05 is not IS06 plus D&A. Differences are separately traced; earnings-quality work must distinguish definitions. S1 pp.53, 106. |
| EBITDA As Defined vs legal EBITDA | Issuer describes specified adjustments and a conditional pro forma revolver covenant relationship, but no current certificate or full operative facility package is reviewed here | Retain issuer language as reported, not a legal capacity calculation. CP-4 must interpret the supplied indenture and identify additional needed documents. S1 pp.52, 132, 141. |
| Stock compensation variants | CF10 / EB07 217 / 157 / 184 includes deferred compensation; Note 16 stock compensation alone 188 / 135 / 153; equity APIC recognition EQ25/EQ15/EQ05 134 / 112 / 151 | Not contradictory canonical alternatives: scopes differ. Do not substitute APIC recognition or stock-only expense for the bridge add-back. S1 pp.108–109, 143. |
| Debt gross vs net | D14 gross 24,581 and carrying 24,394 exclude D01; BS long-term debt excludes current portion | Principal, carrying debt, and legal indebtedness are not interchangeable. Analytical K07 uses reported carrying amounts; finance leases included once. S1 pp.105, 126–127. |
| Lease wording | S1 p.131 calls 262 / 193 finance lease value “net of the current portion”; p.148 explicitly splits total 262 / 193 into current 6 / 5 and long-term 256 / 188 | Use explicit Note 17 classification with p.126's total for accounting; retain narrative wording inconsistency. Do not add current leases again. |
| Cash-flow bridge changes | CB02 adds back 272 / 415, versus the absolute CF15–CF21 block totals 302 / 431 | Distinct reported bridge versus calculated complete cash-flow block. Differences 30 / 16 are not forced to zero or called a working-capital error. Detailed reclassification explanation remains open. S1 pp.54, 109. |
| Dividends | CF28 cash paid, IS21 per-share declarations, BS14 accrual, EQ23 equity charge and Note 16 common/option amounts have different scopes/timing | No assumption of zero dividends in FY2023: CF28 reports cash payments despite IS21's common-dividend dash. Equity-versus-note residual is disclosed in T4.19. |

### Evidence-based annual read-through

**Operating performance.** TransDigm's reported revenue and operating income both increased from FY2023 to FY2024 (IS01, IS06); K13 calculates increases of 1,355 and 608, with growth fractions 0.205771 and 0.208005. Gross and operating margins rose on the calculated K04–K05 definitions. All three segment revenue totals increased (SG04, SG08, SG09); SG01–SG07 show the relevant commercial/OEM, aftermarket and defense rows without attributing the consolidated increase to an untested price/volume/organic cause. The source explains that segments reflect internal performance reporting and corporate reconciliation, not independent legal obligors (S1 pp.140–142). No forecast follows from these historical comparisons.

**Cash conversion.** CFO increased by 670 (K13; CF22); the complete source changes-in-assets/liabilities block remained a cash use, but its use narrowed by 129 (K03/K13). K12 conversion improved, and K02 CFO less capex increased. CF24 acquisitions and CF28 distributions are outside that FCF definition, so this does not establish cash available for debt paydown. Cash interest CF43 is distinct from IS07 and CB03, while tax paid CF44 is distinct from IS11; neither accrual earnings nor the issuer's EBITDA adjustment bridge is a substitute for cash flows. Source non-GAAP cautions explicitly identify interest, taxes, replacement expenditure and cash integration costs as omitted burdens (S1 p.52).

**Funding and leverage.** K07 carrying debt increased by 5,130 (K13), while reported cash CF42 increased and the cash-netted K10 multiple declined. Gross carrying leverage K09 nevertheless increased: the two directions are not contradictory because cash netting changes the numerator. The liquidity implication of that netting is restricted: BS14/SE01 identifies a declared payment obligation and SE03 records its October settlement. S1 p.131 explicitly says the fourth-quarter notes and term-loan proceeds, together with cash on hand, were used to fund the special-dividend declaration. S1 p.128 separately identifies 2031 notes/Tranche J proceeds and cash as financing the CPI Electron Device acquisition. These are documented funding links, not an inference from simultaneous debt and dividends. Reported positive financing CF38 supported the historical cash rollforward; no claim that all base-date cash was accessible, unrestricted or permanent is made.

**Coverage and quality.** Operating-income/net-interest coverage K11 improved, but it is an accounting ratio using net interest, not cash coverage or a covenant headroom test. EB06–EB09 include compensation, financing and acquisition-related adjustments across comparative periods; CP-1D must test recurrence and cash consequences rather than accepting their add-back status. S1 p.143 discloses liability-based awards and recurring measurement; S1 p.52 warns of cash integration cost exclusions. No independent adjusted earnings restatement is presented here.

## Calculations

### T4.9 — Calculation traces and T4.19 reconciliations

All new arithmetic used the supplied Decimal-38 `calculate` kernel. Signed source lexemes were translated to decimal operands only in calculations: commas removed; parentheses negative; expense magnitudes subtracted where appropriate. Results below are calculated, not source-printed facts. Ratios require positive denominators, which are present for every displayed ratio. All monetary operands are consolidated USD millions, and same-year annual flows are not mixed with post-period events. Balance-dependent ratios pair the year-end instant with that fiscal year's duration. No ratio is represented as a legal test.

| Trace ID | Definition / operand references and formula | FY2024 result | FY2023 result | FY2022 result | Source / limitation |
|---|---|---|---|---|---|
| K01 | Complete below-gross-profit expense block = IS04 + IS05: 980+161; 780+139; 748+136 | 1,141 | 919 | 884 | S1 p.106; calculated aggregate only |
| K02 | FCF = CF22 + CF23: 2045−165; 1375−139; 948−119 | 1,880 | 1,236 | 829 | S1 p.109; not after acquisitions or dividends |
| K03 | CF15+CF16+CF17+CF18+CF19+CF20+CF21: −84−104−62−60−11+60−41; −212−261+168−44+12−45−49; −190−134+58−56+58−21−6 | (302) | (431) | (291) | S1 p.109; complete source block, not working-capital balance movement |
| K04 | Gross margin = IS03 / IS01: 4672/7940; 3842/6585; 3099/5429 | 0.588413 | 0.583447 | 0.570823 | Fraction; source pp.106 |
| K05 | Operating margin = IS06 / IS01: 3531/7940; 2923/6585; 2215/5429 | 0.444710 | 0.443888 | 0.407994 | Fraction; source p.106 |
| K06 | EBITDA As Defined margin = SG16 / IS01: 4173/7940; 3395/6585; 2646/5429 | 0.525567 | 0.515566 | 0.487383 | Fraction; sources pp.106, 142 |
| K07 | Carrying debt = BS17+BS11+BS12: 24296+98+486; 19330+71+349 | 24,880 | 19,750 |  | USD millions; FY2022 balance not supplied |
| K08 | Cash-netted carrying debt = K07−BS01: 24880−6261; 19750−3472 | 18,619 | 16,278 |  | Mechanical netting; cash accessibility not established |
| K09 | K07 / SG16: 24880/4173; 19750/3395 | 5.962138 | 5.817378 |  | Multiples; no FY2022 debt operand |
| K10 | K08 / SG16: 18619/4173; 16278/3395 | 4.461778 | 4.794698 |  | Multiples; not covenant leverage |
| K11 | IS06 / IS07: 3531/1286; 2923/1164; 2215/1076 | 2.745723 | 2.511168 | 2.058550 | Multiples of net accrual interest |
| K12 | CF22 / SG16: 2045/4173; 1375/3395; 948/2646 | 0.490055 | 0.405007 | 0.358277 | Cash-conversion fraction |

Blank numeric FY2022 cells in K07–K10 mean Not calculable because the primary debt instant is not supplied. The separate gap entries below state affected consumers.

K13 FY2024 versus FY2023 calculated annual deltas, all money USD millions: IS01 7940−6585 = **1,355**, divided by FY2023 6585 = **0.20577069096431283219438116932422171602**; IS06 3531−2923 = **608**, divided by FY2023 2923 = **0.20800547382825863838522066370167635990**; CF22 2045−1375 = **670**; SG16 4173−3395 = **778**; K03 −302−(−431) = **129**; K07 24880−19750 = **5,130**. Source references are IS pp.106, CF p.109, SG p.142 and BS p.105. Growth denominators are strictly positive.

The following residual checks were actually run. A residual is the signed component sum minus the reported total, not an independently reported figure. Each comma-separated residual below is in FY2024 / FY2023 / FY2022 order unless explicitly stated otherwise.

| Check ID | Exact row formula / operands | Calculated residual / result | Source and scope |
|---|---|---|---|
| R01 Gross-to-operating consistency | (IS01−IS02−IS03)+(IS03−IS04−IS05−IS06); operands 7940−3268−4672+4672−980−161−3531; 6585−2743−3842+3842−780−139−2923; 5429−2330−3099+3099−748−136−2215 | 0 / 0 / 0 | S1 p.106; complete expense block verified by reading |
| R02 Pretax | IS06−IS07−IS08−IS09−IS10; 3531−1286−58+28−2215; 2923−1164−56+13−1716; 2215−1076−1−11−1127 | 0 / 0 / 0 | S1 p.106 |
| R03 CFO | CF01+CF02+CF03+CF04+CF05+CF06+CF07+CF08+CF09+CF10+CF11+CF12+CF13+CF14+K03−CF22 | 0 / 0 / 0 | S1 p.109; all operating rows included |
| R04 Investing | CF23+CF24+CF25−CF26: −165−2347+71+2441; −139−762+1+900; −119−437+3+553 | 0 / 0 / 0 | S1 p.109 |
| R05 Financing | Sum CF27–CF37 minus CF38; 245−2038+0+7373−4400−550+0+137+6815−4403−8−3171; 215−38+0+3504−1122−1459+0+0+6238−7334−20+16; 132−1091−912+0+0+0−200+0+0−75−2+2148 | 0 / 0 / 0 | S1 p.109 |
| R06 Cash movement | CF22+CF26+CF38+CF39−CF40: 2045−2441+3171+14−2789; 1375−900−16+12−471; 948−553−2148−33+1786 | 0 / 0 / 0 | S1 p.109 |
| R07 Opening-to-closing cash | CF41+CF40−CF42: 3472+2789−6261; 3001+471−3472; 4787−1786−3001 | 0 / 0 / 0 | S1 p.109; closing cash agrees BS01 in supplied BS years |
| R08 Current assets | BS01+BS02+BS03+BS04−BS05: 6261+1381+1876+511−10029; 3472+1230+1616+420−6738 | 0 / 0 for Sep 30, 2024 / Sep 30, 2023 | S1 p.105 |
| R09 Total assets | BS05+BS06+BS07+BS08+BS09−BS10: 10029+1488+10419+3446+204−25586; 6738+1255+8988+2747+242−19970 | 0 / 0 | S1 p.105 |
| R10 Current liabilities | BS11+BS12+BS13+BS14+BS15−BS16: 98+486+323+4216+1216−6339; 71+349+305+0+854−1579 | 0 / 0 | S1 p.105; source dividend dash zero only in this check |
| R11 Total liabilities | BS16+BS17+BS18+BS19−BS20: 6339+24296+766+468−31869; 1579+19330+627+412−21948 | 0 / 0 | S1 p.105 |
| R12 Balance equation | BS20+BS28−BS10: 31869−6283−25586; 21948−1978−19970 | 0 / 0 | S1 p.105 |
| R13 Comprehensive income | CI03+CI04+CI05+CI06−CI08: 1714+181−124−1−1770; 1298+137+20+12−1467; 866−379+352+8−847 | 0 / 0 / 0 | S1 p.107 |
| R14 Equity total rollforward | Opening total + each source movement total − closing total. FY2024: −1978+1−6368−87+134+245+1714+181−124−1+6283; FY2023: −3766−1−5+112+215+1298+137+20+12+1978; FY2022: −2910+1−1045−30+151+132−912+866−379+352+8+3766 | 0 / 0 / 0 | EQ rows, S1 p.108; share counts not added to money |
| R15 Ordinary EBITDA | EB01+EB02+EB03+EB04−EB05: 1715+312+1286+500−3813; 1299+268+1164+417−3148 | 0 / 0 | S1 p.53; FY2022 not supplied in this bridge |
| R16 Add-back bridge | EB05+EB06+EB07+EB08+EB09−EB10: 3813+70+217+58+15−4173; 3148+18+157+56+16−3395 | 0 / 0 | S1 p.53 |
| R17 Cash-to-EBITDA bridge | CB01+CB02+CB03+CB04+CB05+CB06+CB07−CB08: 2045+272+1246+490+35−217−58−3813; 1375+415+1123+414+34−157−56−3148 | 0 / 0 | S1 p.54 |
| R18 Segment revenue subrows | SG01+SG02+SG03−SG04; SG05+SG06+SG07−SG08 | Each segment 0 / 0 / 0 | S1 p.141; all nine underlying revenue rows retained |
| R19 Consolidated segment revenue | SG04+SG08+SG09−SG10: 3941+3809+190−7940; 3316+3094+175−6585; 2873+2391+165−5429 | 0 / 0 / 0 | S1 p.141; SG10 equals IS01 |
| R20 Segment EBITDA after corporate | SG11+SG12+SG13−SG15−SG16: 2236+1962+81−106−4173; 1866+1547+71−89−3395; 1531+1121+65−71−2646 | 0 / 0 / 0 | S1 p.142 |
| R21 Continuing pretax bridge | NB01−NB02−NB03−NB04−NB05−NB06−NB07−NB08 | 0 / 0 / 0 | S1 p.142; includes subtracting negative FY2022 NB07 |
| R22 D&A cross-check | CF03+CF04−NB02: 149+163−312; 129+139−268; 116+137−253 | 0 / 0 / 0 | S1 pp.109, 142 |
| R23 FY2024 debt subtotal | D02+D03+D04+D05+D06+D07+D08+D09+D10+D11+D12+D13−D14 gross: 8702+2650+2100+1200+2750+750+1450+1000+2200+1500+17+262−24581 | 0 | S1 p.126; D01 deliberately excluded |
| R24 Gross-to-carrying and total debt | 24581−136−51−24394; then 24394+486−24880 | 0; 0 | S1 pp.105, 126; K07 definition |
| R25 Maturity schedule | 93+92+92+6637+4768+12637−24319; 24581−262−24319 | 0; 0 | S1 pp.126, 133; finance leases excluded, securitization outside subtotal |
| R26 Finance lease classification | LS17−LS16−LS15 = 262−256−6 | 0 | S1 p.148, FY2024; resolves classification, not p.131 wording |
| R27 Ordinary EBITDA versus operating income plus D&A | EB05−IS06−EB02: 3813−3531−312; 3148−2923−268 | (30) / (43) | S1 pp.53, 106; definitional differences, not assumed reconciliation errors |
| R28 Cash-change definition difference | Absolute K03−CB02: 302−272; 431−415 | 30 / 16 | S1 pp.54, 109; detailed scope reclassification not resolved |
| R29 Dividend scope comparison | EQ23 charge magnitude − common declared − vested equivalents: 6368−6153−233 | (18) | S1 pp.108, 146; scopes not proven identical; no forced adjustment |

R03 zero substitutions are limited to printed dashes: FY2024 CF02/CF13/CF14 and FY2023 CF02/CF09. R05 uses zero only for the source dashes in that financing block: FY2024 CF29/CF33; FY2023 CF29/CF33/CF34; FY2022 CF30/CF31/CF32/CF34/CF35. R10 uses zero only for FY2023 BS14. Original glyphs remain in reported tables. No zero stands for an absent annual column or missing facility operand. Other subtotal, per-share, equity-column and individual debt-row checks not listed above were not separately kernel-tested; full extraction is not a claim of exhaustive automated validation.

R27 is consistent with the ordinary EBITDA bridge's inclusion of below-operating items; it must not be erased by substituting an operating EBITDA definition. R28 remains an unresolved definition alignment, even though each of the two source bridges reconciles independently. R29 is an unresolved cross-presentation comparison, not evidence that the annual statements fail to balance.

### T4.15 — Publication account mappings

| Source row(s) | Canonical mapping / sign | Publication constraint |
|---|---|---|
| IS01, IS02, IS03, IS04, IS05, IS06 | revenue; cogs negative when normalized; gross_profit; sga negative; intangible_amortization negative; ebit | Keep reported display magnitudes separate from signed model accounts; IS05 not total D&A |
| IS07–IS17 | net_interest_expense negative; refinancing_costs negative; other_nonoperating sign reversed from expense convention; pretax_income; income_tax_expense negative; continuing_income; discontinued_income; net_income; nci_deduction; parent_net_income; common_income | Do not collapse consolidated, parent and common-stockholder income |
| IS18–IS21, IS22, EPS01–EPS03 | per_share quantities; million-share denominators | Never map to monetary millions; retain two-class quantity definition |
| CF03, CF04, NB02 | depreciation; cash-flow amortization; reported bridge D&A | Distinct fields with explicit cross-check, no substitution into the IS expense block |
| CF22, CF23, K02 | cfo; signed capex_total; calculated FCF | CF24 acquisitions and CF28 distributions excluded from K02, not unavailable |
| CF24–CF44 | acquisitions; other_investing; investing_cash_flow; equity_issuance; dividends_and_equivalents_paid; buybacks; instrument-level debt proceeds/repayments; financing_other; financing_cash_flow; fx_cash_effect; net_cash_change; opening_cash; closing_cash; cash_interest_paid; cash_taxes_paid | Preserve issuer detail rather than invent gross debt issuance from net proceeds |
| CF01–CF21 | Source operating adjustment detail, other: rows as necessary | CF15–CF21 summed only under the explicitly stated K03 definition |
| BS01–BS10 | cash; net_receivables; inventory; other_current_assets; total_current_assets; net_ppe; goodwill; net_other_intangibles; other_noncurrent_assets; total_assets | No FY2022 full balance sheet; cash-flow cash is not a substitute |
| BS11, BS12, BS17, K07 | current_long_term_debt; short_term_securitization; long_term_debt; calculated total_carrying_debt | Do not add D13 or current leases twice |
| BS13–BS20 excluding debt rows | trade_payables; other:dividends_payable; accrued_current_liabilities; total_current_liabilities; deferred_tax_liability; other_noncurrent_liabilities; total_liabilities | Keep material dividend accrual and non-debt funding stories |
| BS21–BS29 | common_stock; apic; accumulated_deficit; aoci; treasury_stock; parent_equity; nci; total_equity; liabilities_and_equity | Monetary account mapping separate from embedded actual-share disclosures |
| EB05 / EB10 / SG16 | issuer_ordinary_ebitda / issuer_ebitda_as_defined | Non-GAAP labels retained; not covenant EBITDA or analyst accepted earnings |
| SG01–SG10 | segment revenue detail and consolidated total | Preserve Non-aviation and no duplicate segment allocation |
| CI01–CI08 and EQ01–EQ31 | comprehensive-income and equity supplementary detail | Preserve source order, signs and actual-share columns; not extra IS periods |
| D/F/MAT/LS registers | facility principal, carrying value, rate, maturity and leases | Financial accounting classification is not legal ranking/capacity certification |

## Gaps

### T4.12 — Targeted issues and repair actions

| Gap ID / inherited issue | Review performed / current position | Affected values, periods and consumers | Action / limitation |
|---|---|---|---|
| G01–G02 text fidelity | All required primary text read; p.108 full equity table assigned carefully. No rendering tool. CP-0 end-matter text exceptions not re-examined | All primary display fidelity; CP-MODEL and evidence QA; not a reason to suppress readable annual facts | Retain text-only qualification; obtain rendering if visual proof is required. Empty end-matter text is not a verified blank image. |
| G03 note review, partially resolved | CP-1 read policies, EPS, debt pp.126–133, segments pp.140–143, leases pp.147–148, subsequent events pp.131/146 and bridges pp.52–54. Full acquisition and other note sets not reviewed | CP-1A detailed deal/PPA context; CP-1D adjustment testing; CP-2 broader synthesis | Next consumer read its required pages; do not inherit a claim all annual notes were analyzed. Primary statement extraction is available now. |
| G04 annual-only source | Three annual durations and two full balance instants extracted; no quarterly/YTD source or primary FY2022 balance sheet | Quarterly/YTD/LTM deltas and FY2022 K07–K10, CP-1B/CP-2/CP-MODEL | Source extension needed only for those requested constructions; do not invent quarters from annual totals. |
| G05 operative legal package | CP-1 used annual debt summaries only; CP-0 confirms full executed 2033 indenture already supplied | Covenant EBITDA, capacity, basket use, collateral/intercreditor opinions; CP-4 and CP-6 | CP-4 read supplied legal-text; request other controlling documents/certificates/use inputs as needed. No duplicate request for the existing indenture. |
| G06–G08 current decision inputs | No quotes, live facility confirmations, forecasts, cash-access evidence or portfolio inputs supplied | Current liquidity/refinancing/relative value/stress/portfolio sizing; CP-3C/CP-2/CP-6 | Obtain dated targeted inputs before those conclusions. Missing is not adverse evidence or an invented zero. |
| G09 downstream work | This CP-1 is newly submitted, not host-accepted and not a completed downstream analysis | All downstream consumers; especially CP-4/CP-6 | Host source/instruction review, then one module at a time. No pathway completion claim. |
| G10 agreement dates | CP-0's September 19 annual narrative versus September 5 legal purchase-agreement definition distinction preserved; annual p.131 reread, legal not reinterpreted | CP-1A chronology; CP-4 date-specific references | Retain document roles/dates; obtain agreement if exact chronology becomes material. |
| G11 definition alignments | R28 30 / 16 cash-block differences; R29 (18) equity-versus-note dividend comparison retained; p.131 lease wording conflicts with explicit p.148 split | CP-1D cash/adjustment quality and CP-1A distribution chronology; CP-MODEL should not publish conflated fields | Read supporting detailed disclosures or obtain issuer reconciliation if exact alignment is needed. Use separate reported fields now; p.148 controls explicit lease classification. |
| G12 bounded metrics | Ordinary reported FY2022 EBITDA not in reviewed p.53 bridge; no FFO, maintenance/growth capex split, unrestricted cash, certificate-based headroom, or tranche-level carrying allocation retained | Specific CP-1D/CP-2/CP-MODEL fields, not basic annual income/cash summaries | Keep blank numerical cells with explicit reason; request/source additional operands only for selected use. Never backfill with zero or a different definition. |
| G13 facility detail | Older notes' exact day/month maturities/call schedules and revolver drawn amount not established from reviewed annual passages; phrase searches returned no hits | Detailed debt publication; CP-3C refinancing and CP-4 legal | Use reported maturity years and source schedule now; obtain/read operative terms for exact contractual schedule and live facility status. Do not infer revolver draws from availability difference. |

## Next module

### T4.13 — Consumer-specific readiness and commands

| Consumer | Can consume now | Remaining restriction / next action |
|---|---|---|
| CP-1A business / transaction context | Consolidated scope, three segments, historical acquisitions cash outflow CF24, dated debt issuance/funding links, declared-versus-paid dividends and subsequent-event register | Ready with limitations for annual historical fact pack after host review. Read full business and acquisition note, distinguish G10 dates. No new transaction brief or current deal is supplied. |
| CP-1B earnings delta | Supported FY2024/FY2023/FY2022 annual IS, segment revenue, expense composition, annual cash-flow rows, K13 deltas and definition register | Annual comparison supported; price/volume/organic attribution requires further located narrative and acquisition evidence. Quarterly/YTD/LTM delta unavailable, not approximated. |
| CP-1D earnings quality | Reported EB/NB/CB bridges, all adjustments and descriptions, CFO and capex, cash interest/taxes, leases, R27–R29 and recurring compensation context | Suitable starting evidence, not completed challenge. Test each add-back's cash content/recurrence and resolve required scope alignments; no automatic acceptance of issuer adjusted EBITDA. |
| CP-2 fundamental credit | Annual financials, calculated leverage/coverage/conversion, historical cash/debt/facility/maturity observations and material non-debt funding stories | Annual historical synthesis supported with limitations. Cash netting is mechanical, post-event liquidity not built, legal headroom/current credit/forecast conclusions not supported. |
| CP-MODEL publication | Complete five-statement extraction with supplements, period/quantity register, stable IDs, account mappings, source dashboard and separate calculation traces | Bounded annual publication may proceed only after host evidence/presentation review. Preserve blanks and reasons, original source dashes, equity shares, definitions and subsequent-event dates. No Model/charts/JSON delivery or validation is claimed here. |
| CP-4 legal | Annual accounting perimeter, carrying/principal distinction, maturities, reported issuer compliance language and supplied 2033 indenture document boundary | Use supplied legal-text under CP-0's pinned identity, not annual EBITDA as capacity. Financial facts do not certify current basket usage, guarantees, perfection or whole-package covenant compliance. |
| CP-6 committee | Historical accounting evidence, documented funding/distribution facts and explicit limitations after required downstream handoffs | Not decision-ready: current analytical challenge, market/portfolio/forecast and legal-capacity inputs remain constrained. No clearance, sizing or mandate conclusion. |

Immediate next action is host source/instruction review of this retained CP-1 artifact, followed by CP-1A or the next selected module under the existing CP-OS workflow. Fresh consumers can use S1's exact source key/hash/path and the located rows directly; no older campaign handoff is needed. CP-3C owns refinancing, CP-4 legal and CP-6 committee work. This file is the financial foundation, not completion of their analyses or delivery. All eighteen selected T4 responsibilities are covered above; T4.7 is not part of the selected catalog.
```
