## Request
Build the canonical consolidated financial and credit-metric foundation for **Mattress Firm Holding Corp.**, as of **2014-09-11**, for the credit_snapshot pathway. Separate filed historical results, calculated trailing results, management acquisition adjustments and proposed financing. The requested downstream consumer is CP-4; this handoff does not establish contractual capacity or approve an investment.

## Sources
### Effective source assessments
Page references below are tool-page locators. References K, QA, QJ, AK, APA, PR, LK and LP resolve to the exact sources in this register. Transport hashes identify the supplied JSONL sources, not the embedded original-HTML hashes. Each supplied issuer source is assessed once; none is treated as superseded.

| Reference | Exact source name | Exact sha256 | Assessment and evidence used |
| --- | --- | --- | --- |
| K | 10-k-year-ended-2014-01-28.htm.jsonl | c90fb4f2d705df1983b9badec76e0dfa5e09fe1d44655e62dbdd69f29d1c6e0e | Audited consolidated annual reporting, FY2013 and comparatives; USD thousands except shares/per-share figures. Extractable from targeted text. page:92: “CONSOLIDATED BALANCE SHEETS”; page:93: “CONSOLIDATED STATEMENTS OF OPERATIONS”; page:94: “CONSOLIDATED STATEMENTS OF CASH FLOWS”; page:96: “Each of the fiscal years ended January 31, 2012”; page:51: “Adjusted EBITDA”. Notes used: pp.109–110, 119–120, 123, 133. |
| QA | 10-q-quarter-ended-2014-04-29.htm.jsonl | 8f9fc1a06ba22d6ea8c9d933738b1ff8a3a814380394c4d8cfc73ea5df28f30a | Unaudited consolidated Q1 reporting and prior-year quarter; USD thousands except shares/per-share figures. Independently active interim version. page:3: “Condensed Consolidated Balance Sheets”; page:4: “Thirteen Weeks Ended”; page:5: “The accompanying unaudited condensed consolidated financial statements”; page:31: “Intangible assets and other amortization”. Availability from p.12. |
| QJ | 10-q-quarter-ended-2014-07-29.htm.jsonl | fbf56cb7bfc37a040be57f9ac957ec88eefe9b00edd4be46da0db9295fdeab8e | Unaudited consolidated Q2 and first-half reporting and comparatives; USD thousands except shares/per-share figures. Later interim, not replacement of Q1. page:4: “Twenty-Six Weeks Ended”; page:5: “Cash paid for:”; page:7: “Results of operations of the acquired businesses are included”; page:12: “Total long-term debt”; page:39: “EBITDA”. Extractable from targeted text, including acquisition notes pp.8–9 and debt pp.12–14. |
| AK | 2014-08-29-8k-back-to-bed-asset-purchase.htm.jsonl | a0acd3bf499b4ba4a7cd1e5f758fae3c9b8ad75303b9ae5d6d9b523471080369 | Acquisition-event disclosure, not financial statements or financing agreement. page:1: “wholly owned indirect subsidiary”; page:2: “remains subject to customary closing conditions”. Supports buyer/perimeter and pending-status context only. |
| APA | 2014-08-29-ex2-1-asset-purchase-agreement.htm.jsonl | 9434330800aed3c3db065a695da5180719d58208abac8249b650e27954dae253 | Acquisition agreement, not a financing covenant source. page:10: “shall be $60,000,000, subject to certain adjustments as set forth herein.” Price is USD dollars, not the historical statement unit. Target financial statements are not established by this read. Execution/schedule limitations retained from CP-0. |
| PR | 2014-08-29-ex99-1-press-release.htm.jsonl | d8cf38c3f7b525dc0a9f1146c212ea7f6c27643f7f725361bb34ffffa195f61e | Issuer announcement and management language, subordinate to APA for terms. page:1: “will be funded by cash reserves and revolver borrowings.” Supports intended funding, not actual drawdown or closing. |
| LK | 2014-09-11-8k-item-7-01.htm.jsonl | ce052171e96a72fd90ffdafd421237ca2f87feb97eaa3f1a007130412e890cc3 | Current report classifying the lender presentation. page:1: “proposed debt terms, which have not been negotiated and remain subject to change.” page:2: “is being furnished”; supports non-operative, preliminary treatment. |
| LP | 2014-09-11-ex99-1-public-lender-presentation.htm.jsonl | 857af871696fd07f0b75ccdcfc96f54478c74b4ad29182f70f5e712cd8cf5e0e | Management/lender marketing information; USD millions on the financial pages used. Contains reported-derived, acquisition-pro-forma and prospective measures, not one GAAP book. page:5: “($ in millions)”; page:17: “Pro Forma Adjusted EBITDA has not been prepared in accordance with the requirements of Regulation S-X”; page:19: “Pro Forma LTM New Stores Opened EBITDA Adjustment”. Target bridges are usable as attributed estimates, not independently verified earnings. |

### Supplied handoff and settings
- **CP-0**, exact sha256 **c759dc43c4b5f5ab2ab8dbad2f364fb5590ff0f2d1d24f35ce5b572cc0a55b80**: source readiness, authority hierarchy, source-to-module map and retained gaps. This is the sole supplied current handoff. It is not a substitute for the issuer-page evidence underlying financial values.
- `context`, sha256 **bb8c7332f7352766b95fe66f1113bd386d45bc8d7cde006d983467f9aa1c1a60**, page:1: settings only, not issuer evidence. USD reporting convention; current/prior-period and several deal fields are blank and have not been interpreted as zero.
- No external research was used. Management's claims concerning targets, synergies and auditor involvement are issuer disclosures, not independent external verification.

### Binding, quantity and extraction conventions
All historical statement scopes below use the identical bindings: **currency: USD; unit: US$ thousands; entity_perimeter: Mattress Firm Holding Corp. and consolidated subsidiaries; accounting_basis: U.S. GAAP**. Annual results are audited; interim results are unaudited. Non-GAAP reconciliations supplement, but do not replace, those bindings. No standalone borrower or restricted-group financial book is supplied.

| Scope | Exact duration or instant | Source and binding qualification |
| --- | --- | --- |
| FY2012 | 2012-02-01 to 2013-01-29 | K pp.93–96; historical_duration; common bindings above. |
| FY2013 | 2013-01-30 to 2014-01-28 | K pp.93–96; historical_duration; common bindings above. |
| Q1 FY2013 / Q1 FY2014 | 2013-01-30 to 2013-04-30 / 2014-01-29 to 2014-04-29 | QA pp.3–6; thirteen-week historical_duration scopes; common bindings above. |
| Q2 FY2013 / Q2 FY2014 | 2013-05-01 to 2013-07-30 / 2014-04-30 to 2014-07-29 | QJ pp.3–7 and QA p.4; thirteen-week historical_duration scopes; common bindings above. |
| H1 FY2013 / H1 FY2014 | 2013-01-30 to 2013-07-30 / 2014-01-29 to 2014-07-29 | QJ pp.4–7; twenty-six-week historical_duration scopes; common bindings above. |
| Balance sheets | 2013-01-29; 2014-01-28; 2014-04-29; 2014-07-29 | K pp.92–93; QA p.3; QJ pp.3–4; period_end scopes; common bindings above. Instants have no duration start. |
| Calculated LTM Q2 FY2014 | 2013-07-31 to 2014-07-29 | FY2013 minus H1 FY2013 plus H1 FY2014; constructed duration, not a separately filed statement. Historical consolidation includes acquisitions only from their acquisition dates. |
| Marketing transaction case | LTM Q2 FY2014 reference, proposed financing as of 2014-09-11 | LP pp.4–5, 17–19; USD millions; management-defined combined/pro forma perimeter and non-GAAP basis, including pending targets and prospective adjustments. Never bound to the historical GAAP book. |

Calendar starts follow the immediately preceding stated fiscal/quarter end; fiscal week-count and endpoints are preserved. K p.96 identifies FY2013 as a 52-week year; QJ p.7 identifies FY2014 as a 53-week year. No extra-week normalization has been applied.

The supplied tool set has no extract_statements function or retained raw-value ledger. **All statement cells below were manually transcribed from read_pages, not extracted by extract_statements**; this limitation applies to every reported table and requires downstream transcription review. No visual inspection, workbook-formula verification or full-filing coverage is claimed. Expense magnitudes in reported income-statement tables remain positive as printed; cash-flow outflows retain their printed negative signs. Monetary amounts, actual share counts and per-share amounts are not combined.

## Findings
### Reader summary
| Bottom line | Confidence | Main limitation |
| --- | --- | --- |
| Historical leverage is rising, acquisitions exceed internally generated free cash flow, and the proposed financing relies materially on adjusted earnings. | Medium | Target earnings, executable financing terms, closing liquidity and contractual covenant headroom remain unverified. |

| Finding | Creditor impact | Confidence |
| --- | --- | --- |
| Historical total leverage rises from 1.72 to 2.36 on reported EBITDA. | Acquisition funding raises debt faster than trailing reported earnings. | High |
| First-half EBITDA falls while adjusted EBITDA increases. | Adjustment dependence weakens the reliability of headline earnings growth for debt service. | High |
| First-half free cash flow after acquisitions is negative 83,297 in US$ thousands. | Acquisitions require balance-sheet cash, borrowing and noncash consideration rather than self-funding. | High |
| Existing cash plus disclosed revolver availability totals US$116.543 million at July 29, 2014. | Provides a historical liquidity cushion, not proof of post-acquisition availability. | High |
| Proposed leverage is 3.84 before incremental synergy and new-store adjustments, versus 3.29 with those adjustments. | Debt-service resilience is sensitive to management estimates and execution. | Medium |

### Financial base view
The financial base is the filed consolidated historical business, not the proposed combined company. Historical leverage is moderate but rising; reported cash generation does not fund the acquisition program. The marketing financing case depends materially on acquisition contributions and forward-looking adjustments. Liquidity is available under the existing facility, but neither pro forma closing liquidity nor covenant headroom is established.

### Reported income statements
Amounts are **US$ thousands**, positive expense magnitudes as printed. Net sales exclude the separately presented franchise fees; neither is silently relabelled total revenue. “Total gross profit” is the combined retail gross-profit/franchise-fee subtotal; K and QA print that subtotal without a label, while QJ supplies the label. Its source presentation is preserved below as “Combined subtotal, printed unlabeled”.

| Printed line / presentation | FY2012 | FY2013 | Q1 FY2013 | Q1 FY2014 | Q2 FY2013 | Q2 FY2014 | H1 FY2013 | H1 FY2014 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Net sales | 1,007,337 | 1,216,812 | 275,957 | 333,502 | 302,541 | 409,951 | 578,498 | 743,453 |
| Cost of sales | 614,572 | 751,487 | 171,515 | 212,652 | 182,096 | 246,547 | 353,611 | 459,199 |
| Gross profit from retail operations | 392,765 | 465,325 | 104,442 | 120,850 | 120,445 | 163,404 | 224,887 | 284,254 |
| Franchise fees and royalty income | 5,396 | 5,617 | 1,249 | 1,186 | 1,438 | 1,092 | 2,687 | 2,278 |
| Combined subtotal, printed unlabeled in K/QA; Total gross profit in QJ | 398,161 | 470,942 | 105,691 | 122,036 | 121,883 | 164,496 | 227,574 | 286,532 |
| Sales and marketing expenses | 245,555 | 289,533 | 63,731 | 75,665 | 75,768 | 99,998 | 139,499 | 175,663 |
| General and administrative expenses | 73,640 | 82,964 | 19,169 | 30,686 | 19,749 | 36,888 | 38,918 | 67,574 |
| Intangible asset impairment charge | 2,100 | — (reported) | Not supplied: no separate line | Not supplied: no separate line | Not supplied: no separate line | Not supplied: no separate line | Not supplied: no separate line | Not supplied: no separate line |
| Loss on store closings and impairment of store assets | 1,050 | 1,499 | 261 | 258 | 483 | 648 | 744 | 906 |
| Total operating expenses | 322,345 | 373,996 | 83,161 | 106,609 | 96,000 | 137,534 | 179,161 | 244,143 |
| Income from operations | 75,816 | 96,946 | 22,530 | 15,427 | 25,883 | 26,962 | 48,413 | 42,389 |
| Interest expense, net | 9,247 | 10,864 | 2,847 | 2,816 | 2,795 | 3,469 | 5,642 | 6,285 |
| Income before income taxes | 66,569 | 86,082 | 19,683 | 12,611 | 23,088 | 23,493 | 42,771 | 36,104 |
| Income tax expense | 26,698 | 33,158 | 7,674 | 4,891 | 8,965 | 9,194 | 16,639 | 14,085 |
| Net income | 39,871 | 52,924 | 12,009 | 7,720 | 14,123 | 14,299 | 26,132 | 22,019 |
| Source | K p.93 | K p.93 | QA p.4 | QA p.4 | QJ p.4 | QJ p.4 | QJ p.4 | QJ p.4 |

The operating-expense aggregate is **not cost of sales plus operating expenses**: cost of sales is above retail gross profit. The entire intervening operating block is sales/marketing, G&A, store-closing losses and, in FY2012, the separately printed intangible impairment. D&A is embedded in functional expenses and cannot be subtracted again. Calculation checks below reproduce each reported operating-profit subtotal without an unresolved difference.

### Reported consolidated balance sheets
US$ thousands; signed balance-sheet amounts. K pp.92–93, QA pp.3–4, QJ pp.3–4. All displayed asset and liability lines were reviewed for funding classification; equity is not classified as operating funding.

| Printed line | 2013-01-29 | 2014-01-28 | 2014-04-29 | 2014-07-29 |
| --- | --- | --- | --- | --- |
| Cash and cash equivalents | 14,556 | 22,878 | 11,650 | 18,143 |
| Accounts receivable, net | 26,246 | 20,812 | 25,997 | 36,469 |
| Inventories | 63,228 | 81,507 | 97,262 | 104,845 |
| Deferred income taxes / deferred income tax asset | 3,710 | 4,729 | 4,090 | 4,090 |
| Prepaid expenses and other current assets | 18,855 | 16,348 | 27,100 | 27,367 |
| Total current assets | 126,595 | 146,274 | 166,099 | 190,914 |
| Property and equipment, net | 144,612 | 174,770 | 192,468 | 199,831 |
| Intangible assets, net | 82,479 | 84,391 | 90,586 | 91,796 |
| Goodwill | 358,978 | 366,647 | 434,767 | 468,530 |
| Debt issue costs and other, net | 12,015 | 12,549 | 14,146 | 13,765 |
| Total assets | 724,679 | 784,631 | 898,066 | 964,836 |
| Notes payable and current maturities of long-term debt | 33,930 | 3,621 | 5,594 | 8,877 |
| Accounts payable | 64,642 | 72,165 | 85,534 | 100,338 |
| Accrued liabilities | 41,106 | 42,435 | 46,399 | 71,004 |
| Customer deposits | 8,012 | 9,318 | 11,474 | 15,492 |
| Total current liabilities | 147,690 | 127,539 | 149,001 | 195,711 |
| Long-term debt, net of current maturities | 219,069 | 217,587 | 294,466 | 292,983 |
| Deferred income taxes / deferred income tax liability | 26,800 | 37,921 | 37,090 | 37,563 |
| Other noncurrent liabilities | 63,624 | 73,092 | 75,745 | 79,242 |
| Total liabilities | 457,183 | 456,139 | 556,302 | 605,499 |
| Common stock | 338 | 340 | 341 | 342 |
| Additional paid-in capital | 365,083 | 373,153 | 378,704 | 381,977 |
| Accumulated deficit | -97,925 | -45,001 | -37,281 | -22,982 |
| Total stockholders' equity | 267,496 | 328,492 | 341,764 | 359,337 |
| Total liabilities and stockholders' equity | 724,679 | 784,631 | 898,066 | 964,836 |

Source labels separated by a slash preserve an actual annual/interim label change, not a new aggregate. Debt includes notes payable and both current and noncurrent maturities; net debt deducts reported cash only. Restricted-cash status and unrestricted upstream availability are not established. Operating lease commitments, deferred rent, vendor incentives and customer deposits are **not** silently added to funded debt.

### Reported cash-flow foundation
US$ thousands; negative amounts are printed outflows. FY columns: K pp.94–95 and p.133; Q1: QA pp.4–5; H1: QJ pp.4–5. Q1 cash-interest and cash-tax cells are not supplied in the retained statement spans; no missing amount is set to zero. Cash-flow D&A is not the full D&A operand used in the EBITDA reconciliation.

| Printed line | FY2012 | FY2013 | Q1 FY2013 | Q1 FY2014 | H1 FY2013 | H1 FY2014 |
| --- | --- | --- | --- | --- | --- | --- |
| Net income | 39,871 | 52,924 | 12,009 | 7,720 | 26,132 | 22,019 |
| Depreciation and amortization | 23,507 | 29,498 | 6,210 | 8,692 | 13,441 | 18,201 |
| Loan fees and other amortization / Loan fee and other amortization | 2,361 | 2,207 | 503 | 594 | 1,050 | 2,239 |
| Deferred income tax expense | 17,131 | 12,349 | 712 | 246 | 1,842 | 1,711 |
| Stock-based compensation | 2,856 | 4,846 | 887 | 1,358 | 1,854 | 2,556 |
| Construction allowances from landlords | 5,567 | 5,464 | 1,248 | 1,747 | 2,765 | 2,988 |
| Net cash provided by operating activities | 78,738 | 103,441 | 15,963 | 7,128 | 40,664 | 58,269 |
| Purchases of property and equipment | -68,604 | -55,546 | -14,377 | -19,334 | -27,886 | -34,658 |
| Business acquisitions, net of cash acquired | -63,051 | -8,833 | — (reported) | -77,350 | -2,042 | -106,908 |
| Net cash used in investing activities | -131,655 | -64,379 | -14,377 | -96,684 | -29,928 | -141,566 |
| Proceeds from issuance of debt | 56,000 | 72,000 | 3,000 | 132,000 | 25,000 | 169,000 |
| Principal payments of debt | -36,983 | -105,966 | -18,476 | -54,427 | -45,424 | -93,268 |
| Net cash provided by (used in) financing activities | 19,527 | -30,740 | -14,497 | 78,328 | -18,922 | 78,562 |
| Net increase (decrease) in cash and cash equivalents | -33,390 | 8,322 | -12,911 | -11,228 | -8,186 | -4,735 |
| Cash and cash equivalents, beginning of period | 47,946 | 14,556 | 14,556 | 22,878 | 14,556 | 22,878 |
| Cash and cash equivalents, end of period | 14,556 | 22,878 | 1,645 | 11,650 | 6,370 | 18,143 |
| Interest paid / Cash paid for: Interest, outflow magnitude | 8,052 | 11,255 | Not supplied: retained statement lacks amount | Not supplied: retained statement lacks amount | 5,641 | 6,620 |
| Taxes paid / Cash paid for: Income taxes, outflow magnitude | 11,406 | 28,612 | Not supplied: retained statement lacks amount | Not supplied: retained statement lacks amount | 11,637 | 2,175 |

This is a selected cash-flow foundation, not a claim that every adjustment row is shown. The complete working-capital block relevant to the first-half comparison is retained separately:

| Printed cash-flow change, excluding business acquisitions; US$ thousands | H1 FY2013 | H1 FY2014 | Source |
| --- | --- | --- | --- |
| Accounts receivable | 1,475 | -14,136 | QJ p.4 |
| Inventories | -14,699 | -14,784 | QJ p.4 |
| Prepaid expenses and other current assets | -1,268 | -9,497 | QJ p.4 |
| Other assets | -2,074 | -1,730 | QJ p.4 |
| Accounts payable | 2,130 | 19,473 | QJ p.4 |
| Accrued liabilities | 1,049 | 24,557 | QJ p.4 |
| Customer deposits | 3,181 | 4,943 | QJ p.4 |
| Other noncurrent liabilities | 3,272 | -416 | QJ p.4 |

### Reported EBITDA definitions and adjustment register
US$ thousands. These are **source-reported non-GAAP measures**, not a reconstructed operating-profit-plus-cash-flow-D&A shortcut. K p.51, QA p.31, QJ p.39 explicitly add both “Depreciation and amortization” and “Intangible assets and other amortization”. Loan-fee amortization from the cash-flow statement is not substituted for the latter. Interest is net expense in the issuer bridge; cash-interest coverage uses cash paid instead.

| Printed reconciliation line | FY2012 | FY2013 | Q1 FY2013 | Q1 FY2014 | Q2 FY2013 | Q2 FY2014 | H1 FY2013 | H1 FY2014 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Depreciation and amortization | 23,507 | 29,498 | 6,210 | 8,692 | 7,231 | 9,509 | 13,441 | 18,201 |
| Intangible assets and other amortization | 1,506 | 2,489 | 541 | 763 | 612 | 848 | 1,153 | 1,611 |
| EBITDA | 100,829 | 128,933 | 29,281 | 24,882 | 33,726 | 37,319 | 63,007 | 62,201 |
| Intangible asset impairment charge | 2,100 | — (reported) | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row |
| Loss on store closings and impairment of store assets | 1,050 | 1,499 | 261 | 258 | 483 | 648 | 744 | 906 |
| Financial sponsor fees and expenses | 74 | 26 | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row |
| Stock-based compensation | 2,856 | 4,846 | 887 | 1,358 | 967 | 1,198 | 1,854 | 2,556 |
| Secondary offering costs | 1,915 | — (reported) | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row | Not supplied: not a bridge row |
| Vendor new store funds | 953 | 808 | 887 | -97 | 96 | -346 | 983 | -443 |
| Acquisition-related expenses | 11,980 | 1,736 | 326 | 2,564 | 124 | 7,193 | 450 | 9,757 |
| Other | -789 | 2,131 | 581 | 1,786 | 607 | 3,184 | 1,188 | 4,970 |
| Adjusted EBITDA | 120,968 | 139,979 | 32,223 | 30,751 | 36,003 | 49,196 | 68,226 | 79,947 |

**Definition risk.** QJ pp.38–39 and K p.50 explicitly warn that excluded costs may recur. Acquisition-related adjustments combine noncash inventory purchase-accounting effects with cash transaction/integration costs; no cash/noncash split is supplied for the 9,757 first-half adjustment. “Other” includes ERP costs: QJ p.39 reports $2.9 million in H1 FY2014 versus $1.2 million in H1 FY2013. No recurrence exclusion is endorsed here. Vendor new-store funds substitute cash receipts for the amortized reduction of cost of sales; the negative current-period adjustment is retained, not flipped into an add-back. These funds are deferred liabilities amortized over 36 months, not recurring sales.

**Earnings implication.** H1 net sales rise from 578,498 to 743,453, but operating income declines from 48,413 to 42,389 and reported EBITDA declines from 63,007 to 62,201. Adjusted EBITDA instead rises from 68,226 to 79,947. The calculated adjustment gap expands from 5,219 to 17,746. The issuer's acquisition and ERP activity therefore materially changes the relationship between reported earnings and adjusted debt-service capacity; headline adjusted growth is not equivalent to organic improvement. Q2's reported EBITDA improves, but does not reverse the first-half decline. Sources: QJ pp.4, 39; QA p.31.

### Financials and credit metrics
This table is the canonical dashboard for the selected historical base. All monetary values are **US$ thousands**; ratios are **x**, rounded to two decimals. EBITDA and adjusted EBITDA are source-reported except calculated LTM; FCF and net debt are analyst definitions. FCF = reported CFO less cash purchases of property and equipment, after cash interest and taxes already included in CFO. It is not maintenance-only FCF or an acquisition-inclusive free-cash-flow measure.

| Metric | FY2013 / 2014-01-28 | H1 FY2013 | H1 FY2014 / 2014-07-29 | LTM ended 2014-07-29 | Basis / limitation |
| --- | --- | --- | --- | --- | --- |
| EBITDA | 128,933 | 63,007 | 62,201 | 128,127 | K p.51; QJ p.39; LTM calculation C1. |
| Adjusted EBITDA | 139,979 | 68,226 | 79,947 | 151,700 | Issuer-adjusted, not covenant EBITDA; C1. |
| Cash interest paid, outflow magnitude | 11,255 | 5,641 | 6,620 | 12,234 | K p.133; QJ p.5; C1. |
| CFO | 103,441 | 40,664 | 58,269 | 121,046 | K p.94; QJ p.4; C1. |
| Cash capex, outflow magnitude | 55,546 | 27,886 | 34,658 | 62,318 | K p.94; QJ p.5; C1. Growth/maintenance split Not supplied. |
| FCF before acquisitions | 47,895 | 12,778 | 23,611 | 58,728 | C2; cash capex only. |
| FCF after acquisitions | 39,062 | 10,736 | -83,297 | Not calculable: LTM acquisition bridge not constructed | C2; actual acquisition cash outflow deducted. |
| Total debt at period end | 221,208 | Not supplied: comparative instant not retained | 301,860 | 301,860 | Source-reported debt totals QJ p.12; current plus noncurrent debt included. |
| Net debt at period end | 198,330 | Not calculable: comparable debt instant not retained | 283,717 | 283,717 | C3; reported cash deducted, cash transferability unverified. |
| Total debt / EBITDA | 1.72 | Not calculable: no comparable debt instant | Not calculable: six-month earnings not annualized | 2.36 | C4; historical, not covenant ratio. |
| Net debt / EBITDA | 1.54 | Not calculable: no comparable debt instant | Not calculable: six-month earnings not annualized | 2.21 | C4. |
| EBITDA / cash interest | 11.46 | Not supplied: not selected for chart comparison | Not supplied: not selected for chart comparison | 10.47 | C4; total cash interest paid, not net-interest expense. |
| Total debt / adjusted EBITDA | Not supplied: alternate annual ratio not calculated | Not calculable: no comparable debt instant | Not calculable: six-month earnings not annualized | 1.99 | C4; issuer-adjusted earnings, no acquisition annualization. |
| Net debt / adjusted EBITDA | Not supplied: alternate annual ratio not calculated | Not calculable: no comparable debt instant | Not calculable: six-month earnings not annualized | 1.87 | C4; not legal headroom. |
| Contractual leverage/coverage headroom | Not calculable: definitions and thresholds missing | Not calculable: definitions and thresholds missing | Not calculable: definitions and thresholds missing | Not calculable: definitions and thresholds missing | Qualitative compliance statements are not quantitative headroom. |

### Chart data: leverage
| Period | Total debt / EBITDA | Net debt / EBITDA | Reporting unit | Basis and limitation |
| --- | --- | --- | --- | --- |
| FY2013 ended 2014-01-28 | 1.72 | 1.54 | x | Calculated: 221,208 debt and 198,330 net debt / 128,933 reported EBITDA; K pp.51, 92–93; QJ p.12; C3–C4. |
| LTM ended 2014-07-29 | 2.36 | 2.21 | x | Calculated: 301,860 debt and 283,717 net debt / 128,127 reported-derived LTM EBITDA; QJ pp.3, 12, 39; C1, C3–C4. Not pro forma or covenant leverage. |

### Chart data: interest cover
| Period | EBITDA / cash interest | Reporting unit | Basis and limitation |
| --- | --- | --- | --- |
| FY2013 ended 2014-01-28 | 11.46 | x | 128,933 / 11,255 cash interest paid; K pp.51, 133; C4. |
| LTM ended 2014-07-29 | 10.47 | x | 128,127 / 12,234; K pp.51, 133 and QJ pp.5, 39; C1, C4. Not the presentation's adjusted EBITDA/net-interest measure. |

### Chart data: liquidity
| Period | Cash | Undrawn committed facilities | Reporting unit | Basis and limitation |
| --- | --- | --- | --- | --- |
| 2014-01-28 | 22.878 | 77.1 | US$m | K pp.92, 119. Disclosed availability after 21.0 drawn and 1.9 letters of credit; annual debt classification reflects subsequent February amendment. Cash converted in C7. |
| 2014-04-29 | 11.65 | 98.4 | US$m | QA pp.3, 12. Reported availability after 1.6 letters of credit; no revolver borrowings. Not covenant-unconditional cash. C7. |
| 2014-07-29 | 18.143 | 98.4 | US$m | QJ pp.3, 13. Reported availability after 1.6 letters of credit; excludes additional unused term-loan capacity and proposed ABL. C7. |

### Chart data: debt maturities
| Period | Debt maturing | Reporting unit | Basis and limitation |
| --- | --- | --- | --- |
| Next twelve months from 2014-07-29 | 8.877 | US$m | QJ pp.3, 12 current maturities, converted in C7. Current classification is a twelve-month proxy, not a complete dated amortization schedule. |
| January 2016 existing-facility final maturity | Not supplied: final balloon after intervening amortization not quantified | US$m | QJ pp.12–13 describes January 2016 final maturities and 0.8 quarterly term installments; 296,795 term balance is not the final balloon amount. Other notes extend through fiscal 2016. |

The annual maturity schedule at **2014-01-28**, separately preserved as historical reported facts, is 3,621 in FY2014 and 217,587 in FY2015, total 221,208 US$ thousands (K p.120). It is not substituted for July's larger debt stock. K p.119 says the annual revolver classification reflects the February 27, 2014 extension. The increase from annual quarterly installments of $0.5 million identified in CP-0 to interim $0.8 million is consistent with a changed borrowing stock and amendment chronology, but no contract-based reconciliation is certified.

### Cash-flow quality and non-debt funding review
**Acquisition funding, not operating cash burn, drives the financing need.** H1 CFO of 58,269 covers cash capex of 34,658 and leaves 23,611 before acquisitions. Deducting 106,908 of acquisitions produces negative 83,297. Q1 alone produces negative 12,206 before acquisitions and negative 89,556 after them. FY2013, by contrast, leaves 39,062 after acquisitions. These figures are after reported interest/taxes, not EBITDA-based proxies. K pp.94–95; QA pp.4–5; QJ pp.4–5; C2.

The H1 working-capital block contributes **8,410**, compared with a **6,934 outflow** in H1 FY2013. Accounts payable, accruals and customer deposits provide funding against receivables/inventory/prepayments; excluding those three liability inflows, the block consumes **40,563**. Cash taxes paid are 2,175 versus 11,637, although current H1 income-tax expense is 14,085. CFO improvement therefore is not solely evidence of stronger cash earnings and should not be extrapolated without liability and tax timing support. Construction allowances of 2,988 also sit inside CFO. Sources: QJ pp.4–5; C6.

| Reviewed material non-debt funding item | Reported values, US$ thousands | Risk mechanic and creditor implication | Evidence and limitation |
| --- | --- | --- | --- |
| Customer deposits, each reported balance reviewed | 8,012 at 2013-01-29; 9,318 at 2014-01-28; 11,474 at 2014-04-29; 15,492 at 2014-07-29 | Customer prepayments finance operations but imply future delivery/refund obligations. Growth supplies working capital; slower orders or refunds could reverse the support. Not funded debt. | K p.93; QA p.3; QJ p.3. H1 operating inflow 4,943 and acquired deposits 1,231 are distinct from the balance movement; QJ pp.4, 8. |
| Deferred lease liabilities | 46,789 at 2013-01-29; 53,521 at 2014-01-28 | Straight-line rent and landlord incentives create accounting liabilities; they are not equivalent to total lease debt. Rent commitments remain outside unadjusted leverage. | K pp.109, 123. Latest separate balance Not supplied in retained interim notes; aggregate other noncurrent liabilities cannot be substituted. |
| Deferred vendor incentives | 13,653 at 2013-01-29; 14,333 at 2014-01-28 | Upfront vendor funding supports cash while future cost-of-sales amortization affects earnings; cash and adjusted-EBITDA timing differ. It is not unrestricted recurring revenue. | K pp.51, 123; QJ p.39. Latest separate balance Not supplied. |
| Product warranty returns, less current portion | 2,044 at 2013-01-29; 2,807 at 2014-01-28 | Represents future claims rather than financing capacity; treating the reserve as debt would mix operating estimates with borrowings. Cash requirements remain relevant to liquidity. | K p.123; current warranty provisions 1,735 and 1,994 separately reported there. Interim detailed reserve roll-forward Not supplied. |
| Other noncurrent liability detail, “Other” | 1,138 at 2013-01-29; 2,431 at 2014-01-28 | Undifferentiated obligations remain an explicit disclosure gap; no assumption that they are either debt-like or harmless. | K p.123. Additional classification required if material to legal indebtedness or liquidity. |

Accrued liabilities and accounts payable were also reviewed, but remain separately classified operating liability accounts rather than invented off-balance-sheet facilities. K p.123 details employee, tax, advertising, construction, return, warranty, interest and insurance accruals. The latest 71,004 accrual balance lacks the same detailed breakdown in retained interim evidence. Deferred taxes are not cash borrowing; common stock, APIC and accumulated deficit are equity, not non-debt funding stories.

### Capital structure and acquisition events
At July 29, 2014, source-reported debt is **301,860**, comprising term loans **296,795**, revolver **none**, and equipment financing/other notes **5,065**, all US$ thousands (QJ p.12). Current maturities of 8,877 are included, not incremental debt. Mattress Holding Corp. is the subsidiary borrower; the consolidated public parent is not silently equated to that borrower. The filing describes substantially-all-assets security and parent/subsidiary guarantees subject to exceptions; neither the public parent's guarantee nor a complete restricted-group perimeter is established (QJ pp.12–14).

QJ p.13 reports extended/revolver LIBOR margins of **3.50%**, base-rate margins of **2.50%**, weighted-average outstanding rate **3.8%**, and quarterly term installments **$0.8 million** in FY2014/FY2015. These are disclosed existing terms, not a verified legal instrument. QJ p.14 reports Perfect Mattress notes of $1.0 million at 7.75%, Mattress Liquidators notes of $3.4 million at 6.00%, and $0.7 million insurance-premium financing; these rounded descriptions are not forced to reconcile exactly to the precise 5,065 aggregate. Compliance is reported at July 29, 2014, but tested ratios, definitions and thresholds are unavailable.

**Completed first-half acquisitions.** QJ pp.7–9 identifies Yotes, Southern Max, Sleep Experts and Mattress Liquidators, consolidated from their respective effective dates. The purchase allocation totals **115,491**; less a **3,500 seller note**, **3,441 equity consideration** and **1,642 acquired cash** gives reported cash acquisition spending of **106,908**. Purchase accounting is management-estimated and subject to adjustments. The $100 million incremental term borrowing funded Sleep Experts and revolver repayment. The annual-to-July debt roll-forward retains an unexplained **1,420** increase after net cash borrowing and the disclosed seller note; it is not labelled operating cash flow or presumed additional acquisition debt. See C5.

**Post-balance-sheet events within the as-of horizon.** AK pp.1–2 and APA p.10 establish an agreement for Back to Bed-related assets at **$60,000,000**, subject to adjustments, with cash/revolver funding intended, not a completed July acquisition. PR p.1 corroborates that intention. LP p.4 reports a September 4 agreement to acquire Sleep Train and that Best Mattress closed on September 8. Best Mattress is therefore a subsequent-to-July event known by the as-of date; its actual closing debt/cash balances are not supplied. Back to Bed and Sleep Train remain pending in the lender case. These events are not backfilled into historical balance sheets.

### Management pro forma financing and earnings sensitivity
All amounts in this subsection are **US$ millions**, on the management transaction perimeter. LP p.5 reports proposed sources of **821**: balance-sheet cash **18**, new ABL draw **42**, new term loan **720**, and equity **40**. Uses are Sleep Train **440**, bolt-ons **66**, existing debt **297**, fees/expenses **18**. Proposed total debt is **767**, including **4** other notes; individual rounded secured-debt components do not establish an exact accounting balance. The proposed 125 ABL commitment is not the same as undrawn cash availability, and 18 cash used in sources is not evidence of closing cash of zero. LP p.5 expects further free cash flow before closing. LK pp.1–2 explicitly says terms are unnegotiated and the data preliminary.

| Earnings layer | Amount | Evidence category and implication |
| --- | --- | --- |
| Calculated historical LTM adjusted EBITDA | 151.700 equivalent to 151,700 US$ thousands | Calculated from filed reconciliations, C1; not acquisition annualized. |
| Completed-acquisition pro forma adjustment, including purchasing synergies | 10.8 | Management estimate, LP pp.17–19; includes pre-acquisition contribution and prospective synergies. |
| Standalone pro forma adjusted EBITDA | 162.6 | Management reported, LP p.18. Sum of displayed 151.7 and 10.8 is 162.5; 0.1 display difference retained, not overwritten. |
| Sleep Train contribution including synergies | 44.6 | Management estimate, LP p.18: includes 30.3 adjusted EBITDA, 1.8 America’s Mattress contribution, 10.0 run-rate synergy component and 2.5 additional purchasing synergies. |
| Bolt-on contribution including synergies | 9.1 | Management estimate, LP p.19; includes Back to Bed and Best Mattress. |
| Combined pro forma adjusted EBITDA with synergies | 216.3 | Source-reported, LP p.18; calculated bridge C8 matches displayed components. |
| New-store EBITDA annualization | 16.8 | LP p.19: 32.5 pro forma less 15.7 actual; not reported historical earnings. |
| Combined with new-store annualization | 233.1 | Calculated 216.3 + 16.8; LP p.5 rounds to 233. |

LP p.5 reports combined adjusted EBITDA **200** before incremental synergy/new-store layers, but already on an adjusted and acquisition-pro-forma perimeter. Using proposed debt **767**, calculated leverage is **3.84** on that displayed 200, **3.55** on 216.3 and **3.29** on 233.1. The source rounds the latter layers to **3.5x** and **3.3x**. This is a denominator sensitivity, not a forecast of achieved earnings or proof of contractual leverage. Historical LTM leverage of **2.36** cannot be compared to the marketing **3.3x** without explaining the different earnings perimeter. LP p.5's **5.8x** adjusted EBITDA/net-interest cover is not EBITDA/cash-interest cover and is excluded from that chart.

LP pp.17–19 warns that completed-acquisition and bolt-on financials were not audited/reviewed and may not be comparable. LK p.2 says many target statements were not prepared under GAAP and prospective measures lack a practicable quantitative GAAP reconciliation. The standalone and target synergy adjustments therefore remain management estimates; neither positive direction nor recurrence exclusions are independently endorsed.

### Segment and reporting-basis review
K pp.109–110 identifies retail and franchise reportable segments. Retail aggregates company-operated regions, e-commerce and special events; franchise results are represented by the franchise-fee/royalty line because associated costs are not distinguished. Separate franchise asset balances are not disclosed as material. The reported income statement already preserves both segment revenue streams; no synthetic franchise EBITDA allocation is made.

QJ p.6 says the FIFO-to-weighted-average inventory change was not retrospectively applied because management judged the effect immaterial. QJ p.7 describes cash-flow reclassifications of construction allowances with no effect on total CFO. These affect comparability and presentation, not permission to restate prior results. Acquisition timing, the forthcoming extra fiscal week, and ongoing ERP-related costs further restrict inference of organic growth or a steady-state run rate.

### Readiness and evidence-quality judgments
The retained statements support a bounded historical consolidated foundation and calculated historical leverage/coverage/FCF. They do not support a complete model, covenant capacity or certified acquisition underwriting. Direct source claims retain directly sourced lineage; arithmetic claims retain calculated lineage; forward-looking synergy and annualization claims remain management estimates; causal credit implications are analyst interpretation. No numerical confidence score or independent QA certification is asserted.

| Requested downstream use | Assessment | Evidence available | Restriction and required action |
| --- | --- | --- | --- |
| CP-4: entity scope and capital structure | Limited | K pp.95–96; QJ pp.12–14; historical debt and consolidation tables | Obtain borrower/restricted-group accounts, final obligor/guarantor map and collateral exceptions. Consolidated assets do not prove guarantee coverage. |
| CP-4: debt classification, schedule and maturity profile | Limited | QJ pp.12–14; current maturities and stated January 2016 final dates | Obtain governing instruments, exact amortization and dated debt balances; resolve 1,420 roll-forward residual and updated maturity distribution. |
| CP-4: EBITDA definitions and covenant metrics | Limited for descriptive comparison; missing for contractual calculations | K pp.50–51; QJ pp.38–39 | Obtain contractual EBITDA/debt/interest definitions, baskets, acquisition annualization and equity-cure provisions. Do not import marketing adjustments automatically. |
| CP-4: covenant compliance and headroom | Missing quantitative test; qualitative compliance directly sourced | QJ p.14 reports compliance | Obtain compliance certificate, tested ratios, thresholds and waivers/amendments. Historical 2.36 leverage is not tested covenant leverage. |
| CP-4: operative proposed financing capacity and liquidity | Not ready | LK pp.1–2; LP pp.4–5; CP-0 retained legal/appraisal gaps | Obtain negotiated financing documents, marketing term sheet, borrowing-base certificate/appraisal and post-closing sources/uses. No legal capacity inference from proposals. |

Coverage review addresses leverage, cash-interest coverage, cash-flow quality, liquidity, data quality, definition risks and key gaps above. No underlying source-identity conflict was found. Remaining source preparation/visual-fidelity, omitted acquisition schedules, target financials, borrowing-base, legal-document and obligor-map gaps remain applicable to the uses that depend on them; none is dismissed as irrelevant. Unread pages remain available, not asserted absent. No supplied narrative-evidence or independent quality-scope register exists; judgments here are bounded to located evidence rather than invented register entries.

## Calculations
### Calculation policy and rounding
All new arithmetic used below was executed with the supplied Decimal-38 calculate kernel. Operands are signed decimal amounts; monetary calculations retain **USD, US$ thousands, Mattress Firm Holding Corp. and consolidated subsidiaries**, unless explicitly labelled management transaction **US$ millions**. Ratios are fractions displayed in x, rounded to two decimals; no ratio uses a non-positive denominator. Display rounding is not a source-printed subtotal. Extra exploratory calculator outputs not used as observations are not part of the canonical dataset.

### C1 — constructed trailing financials
Each row uses **FY2013 − H1 FY2013 + H1 FY2014**, to construct 2013-07-31 to 2014-07-29. No acquisition full-year backfill or synergies are included.

| Quantity; USD thousands | Complete source operands | Calculated result | Component references |
| --- | --- | --- | --- |
| EBITDA | 128,933 − 63,007 + 62,201 | 128,127 | K p.51; QJ p.39 |
| Adjusted EBITDA | 139,979 − 68,226 + 79,947 | 151,700 | K p.51; QJ p.39 |
| Cash interest paid | 11,255 − 5,641 + 6,620 | 12,234 | K p.133; QJ p.5 |
| CFO | 103,441 − 40,664 + 58,269 | 121,046 | K p.94; QJ p.4 |
| Cash capex, magnitude | 55,546 − 27,886 + 34,658 | 62,318 | K p.94; QJ p.5 |

### C2 — free-cash-flow bridges
| Period and quantity; USD thousands | Formula with source components | Calculated result |
| --- | --- | --- |
| FY2013 FCF before acquisitions | 103,441 − 55,546; K p.94 | 47,895 |
| FY2013 after acquisitions | 103,441 − 55,546 − 8,833; K p.94 | 39,062 |
| H1 FY2013 before acquisitions | 40,664 − 27,886; QJ pp.4–5 | 12,778 |
| H1 FY2013 after acquisitions | 12,778 − 2,042; QJ p.5 and preceding calculation | 10,736 |
| H1 FY2014 before acquisitions | 58,269 − 34,658; QJ pp.4–5 | 23,611 |
| H1 FY2014 after acquisitions | 58,269 − 34,658 − 106,908; QJ pp.4–5 | -83,297 |
| Q1 FY2014 before acquisitions | 7,128 − 19,334; QA p.4 | -12,206 |
| Q1 FY2014 after acquisitions | 7,128 − 19,334 − 77,350; QA p.4 | -89,556 |
| LTM Q2 FY2014 before acquisitions | 121,046 − 62,318; C1 | 58,728 |

Cash capex excludes unpaid capital additions: K p.133 reports 6,276 at FY2013 end and QJ p.5 reports 5,929 at July 29, 2014. These are not added to cash FCF without a full payable roll-forward. Maintenance/growth capex, adjusted CFO and FFO are Not calculable: required definitions and adjustment splits are not supplied.

### C3 — debt and net-debt bridges
| Instant; USD thousands | Formula | Calculated result / check | Sources |
| --- | --- | --- | --- |
| 2014-01-28 debt split check | 221,208 − 3,621 − 217,587 | 0 difference | K p.93; QJ p.12 reported total |
| 2014-04-29 total debt | 5,594 + 294,466 | 300,060 | QA p.3; aggregate not printed in that balance sheet |
| 2014-01-28 net debt | 221,208 − 22,878 | 198,330 | QJ p.12; K p.92 |
| 2014-07-29 net debt | 301,860 − 18,143 | 283,717 | QJ pp.3, 12 |
| Annual-to-July debt increase | 301,860 − 221,208 | 80,652 | QJ p.12 |

### C4 — historical ratio calculations
| Period and ratio | Formula using C1/C3 and cited reported operands | Kernel result rounded to six decimals | Display |
| --- | --- | --- | --- |
| FY2013 total leverage | 221,208 / 128,933 | 1.715682 | 1.72 |
| FY2013 net leverage | 198,330 / 128,933 | 1.538241 | 1.54 |
| LTM Q2 FY2014 total leverage | 301,860 / 128,127 | 2.355944 | 2.36 |
| LTM Q2 FY2014 net leverage | 283,717 / 128,127 | 2.214342 | 2.21 |
| FY2013 cash-interest cover | 128,933 / 11,255 | 11.455620 | 11.46 |
| LTM Q2 FY2014 cash-interest cover | 128,127 / 12,234 | 10.473026 | 10.47 |
| LTM Q2 FY2014 adjusted total leverage | 301,860 / 151,700 | 1.989848 | 1.99 |
| LTM Q2 FY2014 adjusted net leverage | 283,717 / 151,700 | 1.870250 | 1.87 |

The intermediate column is rounded to six decimals, despite retaining full kernel precision in execution. Numerators/denominators have matching USD-thousand units. These are analytical ratios, not legal definitions.

### C5 — acquisition and debt roll-forward reconciliation
- H1 FY2014 cash acquisition spending: **115,491 − 3,500 − 3,441 − 1,642 = 106,908**, USD thousands. QJ pp.8–9: acquired net assets/purchase allocation less seller-note consideration, equity consideration and acquired cash. This reproduces the reported acquisition cash outflow.
- H1 net cash debt issuance: **169,000 − 93,268 = 75,732**, USD thousands, QJ p.5.
- Opening debt plus cash net borrowing less closing debt: **221,208 + 75,732 − 301,860 = -4,920**, USD thousands. QJ pp.5, 12. Closing debt exceeds this cash-only bridge.
- Including the disclosed noncash seller note: **221,208 + 75,732 + 3,500 − 301,860 = -1,420**, USD thousands. QJ pp.8–9. **Unresolved difference: 1,420**, not assigned to an invented category; investigate other noncash financing, accrued/financed premiums, acquisition liabilities and timing with the debt ledger.

### C6 — expense, EBITDA and working-capital checks
The following expense block checks use printed positive magnitudes. Each first result equals reported total operating expenses; subtracting it from combined gross profit gives the reported operating profit. Cost of sales is excluded from this block.

| Period; USD thousands | Complete operating expense sum | Calculated expense total | Combined gross profit less total = calculated operating profit | Sources |
| --- | --- | --- | --- | --- |
| FY2012 | 245,555 + 73,640 + 2,100 + 1,050 | 322,345 | 398,161 − 322,345 = 75,816 | K p.93 |
| FY2013 | 289,533 + 82,964 + 1,499 | 373,996 | 470,942 − 373,996 = 96,946 | K p.93; impairment shown as dash |
| Q1 FY2013 | 63,731 + 19,169 + 261 | 83,161 | 105,691 − 83,161 = 22,530 | QA p.4 |
| Q1 FY2014 | 75,665 + 30,686 + 258 | 106,609 | 122,036 − 106,609 = 15,427 | QA p.4 |
| Q2 FY2013 | 75,768 + 19,749 + 483 | 96,000 | 121,883 − 96,000 = 25,883 | QJ p.4 |
| Q2 FY2014 | 99,998 + 36,888 + 648 | 137,534 | 164,496 − 137,534 = 26,962 | QJ p.4 |
| H1 FY2013 | 139,499 + 38,918 + 744 | 179,161 | 227,574 − 179,161 = 48,413 | QJ p.4 |
| H1 FY2014 | 175,663 + 67,574 + 906 | 244,143 | 286,532 − 244,143 = 42,389 | QJ p.4 |

Additional calculated checks, all USD thousands:
- FY2013 EBITDA: **52,924 + 33,158 + 10,864 + 29,498 + 2,489 = 128,933**, K pp.51, 93–94. Both amortization rows included.
- H1 FY2014 EBITDA: **22,019 + 14,085 + 6,285 + 18,201 + 1,611 = 62,201**, QJ pp.4, 39.
- FY2013 adjusted EBITDA: **128,933 + 1,499 + 26 + 4,846 + 808 + 1,736 + 2,131 = 139,979**, K p.51. Source dash-only rows are not invented missing operands.
- H1 FY2014 adjusted EBITDA: **62,201 + 906 + 2,556 − 443 + 9,757 + 4,970 = 79,947**, QJ p.39.
- Adjustment gaps: **79,947 − 62,201 = 17,746** for H1 FY2014; **68,226 − 63,007 = 5,219** for H1 FY2013, QJ p.39.
- H1 FY2014 operating-asset/liability block: **−14,136 − 14,784 − 9,497 − 1,730 + 19,473 + 24,557 + 4,943 − 416 = 8,410**, QJ p.4.
- H1 FY2013 corresponding block: **1,475 − 14,699 − 1,268 − 2,074 + 2,130 + 1,049 + 3,181 + 3,272 = -6,934**, QJ p.4.
- Current block excluding accounts payable/accruals/customer-deposit inflows: **8,410 − 19,473 − 24,557 − 4,943 = -40,563**, QJ p.4. This is a sensitivity to liability funding, not adjusted CFO.

### C7 — chart unit conversion and liquidity
Source amounts divided by **1,000** convert US$ thousands to US$ millions; no FX conversion occurs.
- Cash: **22,878 / 1,000 = 22.878** at 2014-01-28 (K p.92); **11,650 / 1,000 = 11.65** at 2014-04-29 (QA p.3); **18,143 / 1,000 = 18.143** at 2014-07-29 (QJ p.3).
- Latest current maturities: **8,877 / 1,000 = 8.877**, QJ pp.3, 12. Historical annual schedule equivalents: **3,621 / 1,000 = 3.621** and **217,587 / 1,000 = 217.587**, K p.120; these are not an updated July schedule.
- July historical cash plus disclosed revolver availability: **18.143 + 98.4 = 116.543**, US$ millions, QJ pp.3, 13. The 98.4 is source-reported availability after letters of credit, not an assumption that all commitment is available.

### C8 — management transaction denominator sensitivity
USD millions; proposed combined perimeter, not the historical GAAP book. LP pp.5, 17–19.
- Displayed standalone bridge: **151.7 + 10.8 = 162.5**, versus source-reported **162.6**; display discrepancy **0.1** retained. Equivalent USD-thousand check: **151,700 + 10,800 − 162,600 = -100**. Rounded input precision prevents exact underlying reconciliation.
- Combined management bridge: **162.6 + 44.6 + 9.1 = 216.3**.
- Including new-store annualization: **216.3 + 16.8 = 233.1**; LP p.5 displays rounded 233.
- Proposed debt / displayed combined adjusted EBITDA before incremental synergies/new-store adjustment: **767 / 200 = 3.835**, displayed **3.84**.
- Proposed debt / combined EBITDA with synergies: **767 / 216.3 = 3.5460009246417013407304669440591770689**, displayed **3.55**.
- Proposed debt / combined EBITDA with synergies/new-store annualization: **767 / 233.1 = 3.2904332904332904332904332904332904333**, displayed **3.29**.

Rounded marketing inputs are unsuitable for verifying legal leverage or precise incremental borrowing capacity. No cash-interest denominator or actual closing cash balance has been invented for this case.

## Gaps
| Underlying gap | Severity / affected uses | Values, periods and recipients affected | Action |
| --- | --- | --- | --- |
| Governing credit agreements, restatement/amendments and negotiated new financing absent | Critical for CP-4 legal conclusions | Existing and proposed covenant EBITDA/debt/interest definitions, thresholds, baskets, cures, guarantor/security coverage; QJ pp.12–14, LK p.1. All legal headroom conclusions blocked. | Obtain complete dated financing documents and compliance certificates; retain proposals as proposals. |
| Target financials, synergy support and purchase-accounting comparability | High for transaction underwriting; not a block to bounded historical facts | LP's 10.8, 44.6, 9.1 and 16.8 earnings layers; LK p.2 and LP pp.17–19. Actual September closing balances and full target cash-flow statements Not supplied. | Obtain target statements, bridge precision, cash/noncash adjustment splits, synergy execution evidence and acquisition accounting. |
| Actual post-balance-sheet liquidity and proposed borrowing-base availability | High for funding and CP-4 | July 116.543 is historical only. Pending acquisitions and Best Mattress closing may change cash/debt. Illustrative ABL material is not a borrowing-base certificate; CP-0 retained appraisal gap. | Obtain dated debt/cash balances, completed sources/uses, reserves/eligibility, appraisal and borrowing-base certificate. Do not assume proposed undrawn ABL equals liquidity. |
| Detailed debt roll-forward and updated amortization/maturity profile | Medium; High if relied upon for refinancing capacity | Unexplained 1,420 increase after cash borrowing/seller note; QJ pp.5, 8–9, 12. July current maturities 8,877 are known, January 2016 final balloon is not quantified. | Reconcile debt ledger including premium/equipment financing and noncash notes; obtain dated amortization schedule and resolve annual/interim installment chronology. |
| Manual extraction and incomplete preparation/visual assurance | Medium for financial foundation; potentially High for entity map | All transcribed reported tables; CP-0's unavailable preparation manifest/pack hash, chart graphics and organizational mapping. Accessible text is not full-fidelity validation. | Independently verify source rows and signs; obtain retained structured extraction and rendered presentation where necessary. No full-filing or visual checks asserted. |
| Cash-flow repeatability and non-debt liability detail | Medium for liquidity and debt classification | H1 liability-funded cash flow, low cash taxes, 71,004 accruals and 79,242 other noncurrent liabilities; QJ pp.3–5. Latest deferred rent/vendor/warranty breakdowns unavailable. Maintenance/growth split and adjusted CFO/FFO Not calculable. | Obtain detailed accrual/reserve/tax roll-forwards, vendor cash receipts, lease cash requirements and capex split; classify miscellaneous liabilities before calling them debt or harmless. |
| Reporting perimeter, accounting change and acquisition schedules | Medium for historical comparisons; High for legal/transaction work | Consolidated parent is not borrower/restricted group; FIFO/weighted-average transition and acquisition timing restrict organic comparisons. APA omitted schedules/executed ancillary and closing evidence remain CP-0 gaps. | Obtain restricted-group accounts, legal entity schedules, omitted acquisition schedules and closing evidence. Keep GAAP historical, adjusted and marketing cases separate. |

## Next module
Provide this bounded financial foundation to **CP-4** for descriptive debt/entity/earnings-definition cross-reference only. **Do not run or represent completion of the full legal/covenant workflow** without the governing agreements, amendments, compliance tests and proposed financing documents identified above. Its required legal conclusions remain blocked even though historical consolidated financial metrics are usable.

First priority is governing-document and covenant-certificate collection; next reconcile the debt residual and current liquidity, then substantiate target financials and adjustments. Preserve the historical reported book as the base and the marketing transaction case as a separate attributed scenario. This is an intermediate CP-OS handoff, not a final investment recommendation.