# CP-1 — TDG December-quarter financial increment

## Request

Extract and interpret the actual December 28, 2024 Form 10-Q, with the displayed
comparatives and prior closing balance. Execution: current host model with local
tools and conversation context; no isolated provider/API or imported runtime.
This supplements, rather than replaces, the accepted FY2024 annual handoff.
The statements are unaudited, consolidated TD Group under U.S. GAAP.

## Sources

Consumed actual `CP-0.md`, SHA-256
`aa6752f51236ca51dc452f247c212764947878eb21ffd36e6caa75fbfecb809d`:
used its H4 path, c-1/c-5/c-3/c-4 map, unit warning and all six gap restrictions.
H4 is `data/public-corpus/v1/TDG/TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228.htm`,
SHA-256 `9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a`.
`source-preparation/manifest.json` identifies the exact text and inline metadata
reading aids. Original HTML table indexes/row indexes are zero-based locators;
the inline JSON supplies the original fact ID, concept, context, unit, scale,
sign, nil and format at each location. The source controls all displayed values.

Selected instructions and current numeric reader:

- `runs/tdg-002/selected-cp1-stage-instructions.md`: `422f635fc64b30a0986e7332efdfb1f8d7c5964010adb708815a0f70705f1393`.
- `runs/tdg-003/CP-1-instructions.md`: `12e94411700cd3bd4e0a39aab5fe5cb3a09c2d44a1aca135cf77997d0e8863ea`.
- `src/deploy_workflow/inline_xbrl.py`: `782243ca4b983383c44d13469bfbd527ff8b771fa9dc28dc03822db77a8b1433`.

The preparation parser version in the earlier manifest remains its actual
preparation version. The current amount reader was repaired only after actual
source facts exposed unsupported `fixed-zero` and `.01` values. Original source,
metadata aids and displayed lexemes remain unchanged. Compound units come from
`source-preparation/raw-unit-definitions.json`, not a unit-name guess.

## Findings

### Context, period, account and definition maps

| Basis | Exact source meaning |
|---|---|
| Current duration c-1 | 2024-10-01 to 2024-12-28; issuer heading “Thirteen Week Periods Ended”; inclusive date count 89. |
| Comparative duration c-5 | 2023-10-01 to 2023-12-30; same issuer heading; inclusive date count 91. No dates are adjusted to force equality. |
| Balance c-3 / c-4 | Instants 2024-12-28 / 2024-09-30. Cash-flow prior closing balance is 2023-12-30, not September 2024. |
| Money | USD millions in the displayed primary statements except indicated share/per-share items. Inline USD facts scale to original dollars; displayed millions are not multiplied twice. |
| EPS and par value | USD/share from original compound-unit numerator USD and denominator shares. EPS 7.62/4.87; par value `.01` is a source label fact, not USD millions. |
| Weighted shares / equity shares | Weighted shares 58.3/57.7 are millions of shares; equity share counts are exact shares, separate from monetary equity columns. |
| OPEX below gross profit | Calculated 261/255 = selling/admin 211/220 + intangible amortization 50/35. Cost of sales is not in this below-gross-profit expense block. |
| Total D&A | Issuer EBITDA bridge uses 90/71; intangible amortization 50/35 is not total D&A. |
| Cash-after-capex proxy | Calculated 710/600 = reported OCF 752/636 less capex magnitude 42/36. Not issuer-defined FCF, sustainable discretionary cash or debt-service surplus. |
| Debt carrying classification | Calculated December 25,049 = long-term 24,302 + current 98 + separate securitization 649. September 24,880 = 24,296 + 98 + 486. Not gross principal. |
| Mechanical net carrying debt | December 22,590 = 25,049 − reported cash 2,459; September 18,619 = 24,880 − 6,261. Reported cash is not certified unrestricted cash. |

### Financial interpretation and source conflicts

Reported sales are 2,006 versus 1,789; operating income 974 versus 787; net income
493 versus 382. These are actual reported comparative values with the unequal
calendar windows retained. They do not on their own establish price/volume,
organic growth, acquisition contribution or durable margins. H4's MD&A provides
a separate management sales bridge (table 51): organic sales 1,894/1,776 and
acquisition sales 112/13. Its categories sum to reported sales; they are issuer
classifications, not independently estimated attribution.

The issuer's ordinary EBITDA is 1,087/859 and EBITDA As Defined 1,061/912.
Current As Defined is lower than EBITDA because its adjustments include Other,
net (64), alongside acquisition/integration expenses 13 and stock/deferred
compensation 25. Do not assume every adjusted metric is higher than its base.
The source describes the acquisition row as integration/relocation, deal and
valuation/due-diligence costs, and inventory step-up amortization. Other includes
FX gains/losses, payroll withholding taxes, pension/deferred-compensation items
and other income/expense including a business sale gain (text lines 639–641,
661–664). This is management's definition; achievability/recurrence and creditor
acceptance remain CP-1D work. Both issuer bridges and the segment bridge below
reconcile. No covenant EBITDA is inferred.

Cash fell from September 6,261 to December 2,459. The complete reported bridge
is OCF +752, investing −24, financing −4,516 and FX −14, net change −3,802.
Financing includes dividend/equivalent cash payments −4,396, repurchases −316,
securitization cash proceeds +163, option proceeds +35 and financing costs/other
−2; the remaining source debt-flow cells display dashes. The annual handoff's
known October 4,348 payment is not the whole quarterly distribution line: the
quarter reports 4,396. Keep the distinct scope and residual rather than forcing
an unsupported reconciliation. OCF already includes interest, tax and working-
capital effects; cash interest 162 and cash taxes 37 are supplemental disclosures,
not additional deductions from OCF. The 201 accrued-interest cash-flow change
shows why expense 378 is not the same quantity as cash paid 162.

The issuer reports cash liquidity 3,308 = cash 2,459 + revolver borrowing
availability 849 (table 61, text 588–591). Text 598 identifies 61 letters of
credit, not funded revolver debt, and the unchanged February 27, 2029 revolver
maturity. It also explicitly attributes no first-quarter term-loan principal
payment to quarter-end timing despite the quarterly aggregate payment term 22.
Do not replace the reported no-payment fact with an assumed regular payment.

Securitization gross borrowing reached 650 with carrying value 649; the note
says remaining availability 163 was drawn in the first quarter and describes
collateral and extension conditions (text 347). The annual subsequent-event
figure 162.5 and quarterly rounded 163 retain their original precision; they
are not conflicting exact principal measures. July 11, 2025 expiry remains a
historical contractual date, not evidence of later renewal. The issuer's cash-
liquidity assertion and positive operating cash are counterweights to the cash
reduction, but no unrestricted-cash schedule, current covenant certificate or
complete forward forecast is supplied. Do not turn this historical update into
a current sufficiency, default or recovery conclusion.

### Exact retained statement and note rows

The following source-cell tables were copied with local tools and checked
against original HTML plus inline fact metadata. Empty source cells remain
empty; a source dash remains `—`. Reconciliation may use an explicitly tagged
zero-dash's numeric meaning without rewriting the displayed source cell.
Complete five primary statements follow, with the two equity windows separate.
Other note tables are selected supplements, not certification of every note.

### Balance sheet
Original HTML table index 9; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-12-28 | 2024-09-30 |
|---|---|---|---|
| 2 | ASSETS |  |  |
| 3 | CURRENT ASSETS: |  |  |
| 4 | Cash and cash equivalents | 2,459 | 6,261 |
| 5 | Trade accounts receivable—Net | 1,285 | 1,381 |
| 6 | Inventories—Net | 1,930 | 1,876 |
| 7 | Prepaid expenses and other | 482 | 511 |
| 8 | Total current assets | 6,156 | 10,029 |
| 9 | PROPERTY, PLANT AND EQUIPMENT—NET | 1,477 | 1,488 |
| 10 | GOODWILL | 10,304 | 10,419 |
| 11 | OTHER INTANGIBLE ASSETS—NET | 3,360 | 3,446 |
| 12 | OTHER NON-CURRENT ASSETS | 218 | 204 |
| 13 | TOTAL ASSETS | 21,515 | 25,586 |
| 15 | LIABILITIES AND STOCKHOLDERS’ DEFICIT |  |  |
| 16 | CURRENT LIABILITIES: |  |  |
| 17 | Current portion of long-term debt | 98 | 98 |
| 18 | Short-term borrowings—trade receivable securitization facility | 649 | 486 |
| 19 | Accounts payable | 315 | 323 |
| 20 | Dividends payable | — | 4,216 |
| 21 | Accrued and other current liabilities | 1,222 | 1,216 |
| 22 | Total current liabilities | 2,284 | 6,339 |
| 23 | LONG-TERM DEBT | 24,302 | 24,296 |
| 24 | DEFERRED INCOME TAXES | 762 | 766 |
| 25 | OTHER NON-CURRENT LIABILITIES | 418 | 468 |
| 26 | Total liabilities | 27,766 | 31,869 |
| 27 | TD GROUP STOCKHOLDERS’ DEFICIT: |  |  |
| 28 | Common stock - $.01 par value; authorized 224,400,000 shares; issued 62,022,913 and 61,904,833 at December 28, 2024 and September 30, 2024, respectively | 1 | 1 |
| 29 | Additional paid-in capital | 2,887 | 2,819 |
| 30 | Accumulated deficit | (6,877) | (7,362) |
| 31 | Accumulated other comprehensive loss | (247) | (42) |
| 32 | Treasury stock, at cost; 5,941,439 and 5,688,639 shares at December 28, 2024 and September 30, 2024, respectively | (2,022) | (1,706) |
| 33 | Total TD Group stockholders’ deficit | (6,258) | (6,290) |
| 34 | NONCONTROLLING INTERESTS | 7 | 7 |
| 35 | Total stockholders’ deficit | (6,251) | (6,283) |
| 36 | TOTAL LIABILITIES AND STOCKHOLDERS’ DEFICIT | 21,515 | 25,586 |

### Income statement
Original HTML table index 10; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | NET SALES | 2,006 | 1,789 |
| 4 | COST OF SALES | 771 | 747 |
| 5 | GROSS PROFIT | 1,235 | 1,042 |
| 6 | SELLING AND ADMINISTRATIVE EXPENSES | 211 | 220 |
| 7 | AMORTIZATION OF INTANGIBLE ASSETS | 50 | 35 |
| 8 | INCOME FROM OPERATIONS | 974 | 787 |
| 9 | INTEREST EXPENSE—NET | 378 | 300 |
| 11 | OTHER INCOME | (23) | (1) |
| 12 | INCOME FROM CONTINUING OPERATIONS BEFORE INCOME TAXES | 619 | 488 |
| 13 | INCOME TAX PROVISION | 126 | 106 |
| 16 | NET INCOME | 493 | 382 |
| 17 | LESS: NET INCOME ATTRIBUTABLE TO NONCONTROLLING INTERESTS | — | — |
| 18 | NET INCOME ATTRIBUTABLE TO TD GROUP | 493 | 382 |
| 19 | NET INCOME APPLICABLE TO TD GROUP COMMON STOCKHOLDERS | 444 | 281 |
| 20 | Earnings per share attributable to TD Group common stockholders: |  |  |
| 23 | Earnings per share | 7.62 | 4.87 |
| 24 | Cash dividends declared per common share | — | 35.00 |
| 25 | Weighted-average shares outstanding: |  |  |
| 26 | Basic and diluted | 58.3 | 57.7 |

### Comprehensive income
Original HTML table index 11; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | Net income | 493 | 382 |
| 4 | Less: Net income attributable to noncontrolling interests | — | — |
| 5 | Net income attributable to TD Group | 493 | 382 |
| 6 | Other comprehensive (loss) income, net of tax: |  |  |
| 7 | Foreign currency translation adjustment | (227) | 91 |
| 8 | Unrealized gains (losses) on derivatives | 22 | (53) |
| 9 | Pension and post-retirement benefit plans adjustment | — | — |
| 10 | Other comprehensive (loss) income, net of tax, attributable to TD Group | (205) | 38 |
| 11 | TOTAL COMPREHENSIVE INCOME ATTRIBUTABLE TO TD GROUP | 288 | 420 |

### Comparative equity roll-forward
Original HTML table index 12; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | Common shares | Par USD m | APIC USD m | Accumulated deficit USD m | AOCI USD m | Treasury shares | Treasury USD m | NCI USD m | Total equity USD m |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | BALANCE—September 30, 2023 | 60,995,513 | 1 | 2,440 | (2,621) | (98) | (5,688,639) | (1,706) | 6 | (1,978) |
| 5 | Changes in noncontrolling interest of consolidated subsidiaries, net | — | — | — | — | — | — | — | 1 | 1 |
| 6 | Special dividends ($35.00 per share) and vested dividend equivalents | — | — | — | (2,020) | — | — | — | — | (2,020) |
| 7 | Accrued unvested dividend equivalents and other | — | — | — | (7) | — | — | — | — | (7) |
| 8 | Compensation expense recognized for employee stock options | — | — | 26 | — | — | — | — | — | 26 |
| 9 | Stock-based compensation activity | 216,150 | — | 52 | — | — | — | — | — | 52 |
| 10 | Net income attributable to TD Group | — | — | — | 382 | — | — | — | — | 382 |
| 11 | Foreign currency translation adjustment, net of tax | — | — | — | — | 91 | — | — | — | 91 |
| 12 | Unrealized loss on derivatives, net of tax | — | — | — | — | (53) | — | — | — | (53) |
| 13 | Pension and postretirement benefit plans adjustment, net of tax | — | — | — | — | — | — | — | — | — |
| 14 | BALANCE—December 30, 2023 | 61,211,663 | 1 | 2,518 | (4,266) | (60) | (5,688,639) | (1,706) | 7 | (3,506) |

### Current equity roll-forward
Original HTML table index 13; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | Common shares | Par USD m | APIC USD m | Accumulated deficit USD m | AOCI USD m | Treasury shares | Treasury USD m | NCI USD m | Total equity USD m |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | BALANCE—September 30, 2024 | 61,904,833 | 1 | 2,819 | (7,362) | (42) | (5,688,639) | (1,706) | 7 | (6,283) |
| 6 | Accrued unvested dividend equivalents and other | — | — | — | (8) | — | — | — | — | (8) |
| 7 | Compensation expense recognized for employee stock options | — | — | 33 | — | — | — | — | — | 33 |
| 8 | Stock-based compensation activity | 118,080 | — | 35 | — | — | — | — | — | 35 |
| 9 | Stock repurchases under repurchase program | — | — | — | — | — | (252,800) | (316) | — | (316) |
| 10 | Net income attributable to TD Group | — | — | — | 493 | — | — | — | — | 493 |
| 11 | Foreign currency translation adjustment, net of tax | — | — | — | — | (227) | — | — | — | (227) |
| 12 | Unrealized gain on derivatives, net of tax | — | — | — | — | 22 | — | — | — | 22 |
| 13 | Pension and postretirement benefit plans adjustment, net of tax | — | — | — | — | — | — | — | — | — |
| 14 | BALANCE—December 28, 2024 | 62,022,913 | 1 | 2,887 | (6,877) | (247) | (5,941,439) | (2,022) | 7 | (6,251) |

### Cash flows
Original HTML table index 14; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | OPERATING ACTIVITIES: |  |  |
| 4 | Net income | 493 | 382 |
| 6 | Adjustments to reconcile net income to net cash provided by operating activities: |  |  |
| 7 | Depreciation | 40 | 36 |
| 8 | Amortization of intangible assets and product certification costs | 50 | 35 |
| 9 | Amortization of debt issuance costs, original issue discount and premium | 9 | 11 |
| 10 | Amortization of inventory step-up | 7 | 1 |
| 11 | Amortization of loss contract reserves | (19) | (5) |
| 13 | Gain on sale of businesses, net | (19) | — |
| 14 | Non-cash stock and deferred compensation expense | 25 | 51 |
| 15 | Deferred income taxes | (2) | — |
| 16 | Foreign currency exchange (gains) losses | (20) | 14 |
| 20 | Changes in assets/liabilities, net of effects from acquisitions and sales of businesses: |  |  |
| 21 | Trade accounts receivable | 80 | 94 |
| 22 | Inventories | (79) | (78) |
| 23 | Income taxes payable | 91 | 94 |
| 24 | Other assets | (2) | 3 |
| 25 | Accounts payable | (3) | (21) |
| 26 | Accrued interest | 201 | 82 |
| 27 | Accrued and other liabilities | (100) | (63) |
| 28 | Net cash provided by operating activities | 752 | 636 |
| 29 | INVESTING ACTIVITIES: |  |  |
| 30 | Capital expenditures | (42) | (36) |
| 31 | Acquisition of businesses, net of cash acquired | (29) | (14) |
| 33 | Other investing transactions | 47 | — |
| 34 | Net cash used in investing activities | (24) | (50) |
| 35 | FINANCING ACTIVITIES: |  |  |
| 36 | Proceeds from exercise of stock options | 35 | 52 |
| 37 | Dividends and dividend equivalent payments | (4,396) | (2,038) |
| 38 | Repurchases of common stock | (316) | — |
| 41 | Proceeds from issuance of senior secured notes, net | — | 983 |
| 45 | Proceeds from term loans, net | — | 988 |
| 46 | Proceeds from trade receivable securitization facility, net | 163 | 100 |
| 47 | Repayment on term loans | — | (16) |
| 48 | Financing costs and other, net | (2) | (2) |
| 49 | Net cash (used in) provided by financing activities | (4,516) | 67 |
| 50 | EFFECT OF EXCHANGE RATE CHANGES ON CASH AND CASH EQUIVALENTS | (14) | 10 |
| 51 | NET (DECREASE) INCREASE IN CASH AND CASH EQUIVALENTS | (3,802) | 663 |
| 52 | CASH AND CASH EQUIVALENTS, BEGINNING OF PERIOD | 6,261 | 3,472 |
| 53 | CASH AND CASH EQUIVALENTS, END OF PERIOD | 2,459 | 4,135 |
| 54 | SUPPLEMENTAL DISCLOSURE OF CASH FLOW INFORMATION: |  |  |
| 55 | Cash paid during the period for interest, net | 162 | 205 |
| 56 | Cash paid during the period for income taxes, net of refunds | 37 | 11 |

### Debt — December 28, 2024
Original HTML table index 30; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | Gross USD m | Costs USD m | Discount USD m | Net USD m |
|---|---|---|---|---|---|
| 3 | Short-term borrowings—trade receivable securitization facility | 650 | (1) | — | 649 |
| 4 | Term loans | 8,702 | (24) | (33) | 8,645 |
| 6 | 5.50% senior subordinated notes due 2027 (“5.50% 2027 Notes”) | 2,650 | (9) | — | 2,641 |
| 7 | 6.75% secured notes due 2028 (“2028 Secured Notes”) | 2,100 | (14) | (7) | 2,079 |
| 8 | 4.625% senior subordinated notes due 2029 (“4.625% 2029 Notes”) | 1,200 | (6) | — | 1,194 |
| 9 | 6.375% secured notes due 2029 (“2029 Secured Notes”) | 2,750 | (21) | (1) | 2,728 |
| 10 | 4.875% senior subordinated notes due 2029 (“4.875% 2029 Notes”) | 750 | (4) | — | 746 |
| 11 | 6.875% secured notes due 2030 (“2030 Secured Notes”) | 1,450 | (12) | — | 1,438 |
| 12 | 7.125% secured notes due 2031 (“2031 Secured Notes”) | 1,000 | (8) | (6) | 986 |
| 13 | 6.625% secured notes due 2032 (“2032 Secured Notes”) | 2,200 | (19) | — | 2,181 |
| 14 | 6.00% secured notes due 2033 (“2033 Secured Notes”) | 1,500 | (14) | — | 1,486 |
| 15 | Government refundable advances | 16 | — | — | 16 |
| 16 | Finance lease obligations | 260 | — | — | 260 |
| 17 |  | 24,578 | (131) | (47) | 24,400 |
| 18 | Less: current portion | 99 | (1) | — | 98 |
| 19 | Long-term debt | 24,479 | (130) | (47) | 24,302 |

### Debt — September 30, 2024
Original HTML table index 31; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | Gross USD m | Costs USD m | Discount USD m | Net USD m |
|---|---|---|---|---|---|
| 3 | Short-term borrowings—trade receivable securitization facility | 487 | (1) | — | 486 |
| 4 | Term loans | 8,702 | (25) | (35) | 8,642 |
| 6 | 5.50% 2027 Notes | 2,650 | (9) | — | 2,641 |
| 7 | 2028 Secured Notes | 2,100 | (15) | (8) | 2,077 |
| 8 | 4.625% 2029 Notes | 1,200 | (6) | — | 1,194 |
| 9 | 2029 Secured Notes | 2,750 | (22) | (1) | 2,727 |
| 10 | 4.875% 2029 Notes | 750 | (4) | — | 746 |
| 11 | 2030 Secured Notes | 1,450 | (12) | — | 1,438 |
| 12 | 2031 Secured Notes | 1,000 | (9) | (7) | 984 |
| 13 | 2032 Secured Notes | 2,200 | (20) | — | 2,180 |
| 14 | 2033 Secured Notes | 1,500 | (14) | — | 1,486 |
| 15 | Government refundable advances | 17 | — | — | 17 |
| 16 | Finance lease obligations | 262 | — | — | 262 |
| 17 |  | 24,581 | (136) | (51) | 24,394 |
| 18 | Less: current portion | 99 | (1) | — | 98 |
| 19 | Long-term debt | 24,482 | (135) | (51) | 24,296 |

### Segment revenue
Original HTML table index 39; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | Net sales to external customers |  |  |
| 4 | Power & Control |  |  |
| 5 | Commercial and non-aerospace OEM | 195 | 179 |
| 6 | Commercial and non-aerospace aftermarket | 341 | 300 |
| 7 | Defense | 491 | 411 |
| 8 | Total Power & Control | 1,027 | 890 |
| 10 | Airframe |  |  |
| 11 | Commercial and non-aerospace OEM | 278 | 294 |
| 12 | Commercial and non-aerospace aftermarket | 333 | 302 |
| 13 | Defense | 335 | 266 |
| 14 | Total Airframe | 946 | 862 |
| 16 | Total Non-aviation | 33 | 37 |
| 18 | Net Sales | 2,006 | 1,789 |

### Issuer segment EBITDA As Defined bridge
Original HTML table index 40; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | EBITDA As Defined |  |  |
| 4 | Power & Control | 585 | 512 |
| 5 | Airframe | 516 | 431 |
| 6 | Non-aviation | 12 | 14 |
| 7 | Total segment EBITDA As Defined | 1,113 | 957 |
| 8 | Less: Unallocated corporate EBITDA As Defined | 52 | 45 |
| 9 | Total Company EBITDA As Defined | 1,061 | 912 |
| 10 | Depreciation and amortization expense | 90 | 71 |
| 11 | Interest expense-net | 378 | 300 |
| 12 | Acquisition transaction and integration-related expenses | 13 | 2 |
| 13 | Non-cash stock and deferred compensation expense | 25 | 51 |
| 15 | Other, net | (64) | — |
| 16 | Income from continuing operations before income taxes | 619 | 488 |

### Lease future payments — remaining FY2025 and later
Original HTML table index 48; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | Operating USD m | Finance USD m |
|---|---|---|---|
| 2 | 2025 | 21 | 19 |
| 3 | 2026 | 15 | 22 |
| 4 | 2027 | 11 | 22 |
| 5 | 2028 | 7 | 23 |
| 6 | 2029 | 4 | 23 |
| 7 | Thereafter | 11 | 423 |
| 8 | Total future minimum lease payments | 69 | 532 |
| 9 | Less: imputed interest | 11 | 272 |
| 10 | Present value of lease liabilities reported | 58 | 260 |

### Issuer net-income to EBITDA and EBITDA As Defined bridge
Original HTML table index 66; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | Net Income | 493 | 382 |
| 4 | Adjustments: |  |  |
| 5 | Depreciation and amortization expense | 90 | 71 |
| 6 | Interest expense-net | 378 | 300 |
| 7 | Income tax provision | 126 | 106 |
| 8 | EBITDA | 1,087 | 859 |
| 9 | Adjustments: |  |  |
| 10 | Acquisition transaction and integration-related expenses (1) | 13 | 2 |
| 11 | Non-cash stock and deferred compensation expense (2) | 25 | 51 |
| 12 | Other, net (3) | (64) | — |
| 13 | EBITDA As Defined | 1,061 | 912 |

### Issuer OCF to EBITDA and EBITDA As Defined bridge
Original HTML table index 69; row indexes below are zero-based source locators. USD millions except labelled share/per-share rows.

| Source row | Label | 2024-10-01–2024-12-28 | 2023-10-01–2023-12-30 |
|---|---|---|---|
| 3 | Net cash provided by operating activities | 752 | 636 |
| 4 | Adjustments: |  |  |
| 5 | Changes in assets and liabilities, net of effects from acquisitions and sales of businesses | (188) | (111) |
| 6 | Interest expense-net (1) | 369 | 289 |
| 7 | Income tax provision-current | 128 | 106 |
| 8 | Amortization of inventory step-up | (7) | (1) |
| 9 | Loss contract amortization | 19 | 5 |
| 10 | Gain on sale of businesses, net | 19 | — |
| 11 | Non-cash stock and deferred compensation expense (2) | (25) | (51) |
| 12 | Foreign currency exchange gains (losses) | 20 | (14) |
| 13 | EBITDA | 1,087 | 859 |
| 14 | Adjustments: |  |  |
| 15 | Acquisition transaction and integration-related expenses (3) | 13 | 2 |
| 16 | Non-cash stock and deferred compensation expense (2) | 25 | 51 |
| 17 | Other, net (4) | (64) | — |
| 18 | EBITDA As Defined | 1,061 | 912 |

## Calculations

`CP-1-attempt-1-calculations.json` retains 627 checks: statement and equity
identities, gross/cost/net debt reconciliation, segment/issuer EBITDA bridges,
period counts and 478 inline numeric readings against original row content and
scale/sign. Raw HTML table cells were read separately from the production inline
parser. Exact Decimal/integer expectations came from those displayed source
rows; no golden fixture or production financial calculation supplied them.
The original visible dashes remain in the handoff; transformed zero is not a
missing-data substitution. The unsupported number-word fact “three” describes
reportable segment count and remains outside numeric-reader support.

Checks do not establish source authenticity or comprehensive visual review.
The numeric checks and source table copy are deterministic local work; the
interpretation above is the current model's actual response to the instructions.
Neither establishes isolated API reliability or receipt-based runtime acceptance.

## Gaps

| ID | Restriction and affected consumer | Action |
|---|---|---|
| G1 | Unequal exact quarter durations and differing reporting instants | CP-1B must state dates/comparability; no silent date repair or equal-duration runtime claim. |
| G2 | H1/H2/H3 full financial extension and complete note/image review remain open | Use source readiness scope honestly; no complete multi-quarter/LTM or whole-pack claim. |
| G3 | Source compound units must be read from retained original unit XML | EPS/par value cannot become USD millions; weighted shares differ from exact equity shares. |
| G4 | Restricted/unrestricted cash, current borrowing conditions and forward cash-use plan absent | CP-2D/CP-2G need those inputs before sufficiency/runway; issuer cash liquidity remains attributed. |
| G5 | Full executed debt/guarantee/collateral documents and lender covenant certificate absent | CP-4/CP-3C cannot infer capacity, priority or covenant headroom from annual/interim narrative alone. |
| G6 | Adjustment quality, maintenance capex, acquisition pro formas and sustained cash conversion unproven | CP-1D/CP-2 must assess definitions/recurrence; calculated OCF-minus-capex is only a proxy. |
| G7 | Original-source external-version and visual limitations from CP-0 persist | Use exact locators for consequential claims; obtain specific missing evidence rather than invent it. |

## Next module

CP-1B: consume this actual handoff's two reported quarter columns, original
contexts and issuer organic/acquisition bridge. Test the legacy core's real
accounting/date/nonzero-comparison restrictions, keeping unsupported runtime
behavior distinct from supported analysis. CP-2D: the observed quarterly cash
bridge replaces a known-events-only cash illustration for December historical
facts; keep future accessibility and cash-use gaps. CP-1D: inspect the actual
signed issuer adjustments. Delivery may copy the verified data, definitions,
source references and limits without another analytical extraction.
