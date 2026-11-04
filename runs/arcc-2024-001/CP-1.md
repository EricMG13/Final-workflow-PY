# CP-1 — ARCC focused FY2024 coverage inputs

## Request

Actual focused extraction for CP-4/CP-4A, consuming CP-0
`8347534cab302ae92b4e097f7a7d08a0ea69945337a0cadaf575526578ea83e5`.
Issuer: Ares Capital Corporation and consolidated subsidiaries; FY2024 and
2024-12-31 closing balances. Analysis 2026-11-04, historical/outdated evidence.
Current host model with context; no complete CP-1 foundation/native pass claim.

## Sources

Original issuer-hosted FY2024 PDF and its pinned pypdf page text admitted by
CP-0. All page numbers below are **1-based PDF pages**. Financial-note amounts
are USD millions, except percentages/per-unit data. The named notes refer to
July 15, 2029 maturity, distinct from March 2029 notes.

## Findings

| ID | Published input | Amount / unit | Period / quantity role / locator |
|---|---|---:|---|
| F01 | Asset coverage | 196% | 2024-12-31; rounded whole-percent presentation; Note 5, PDF p274 / F-164. |
| F02 | Asset coverage per unit for July 2029 Notes | USD 1,962 per USD 1,000 | FY2024 closing; senior-securities table, PDF p65; not the note's market price, asset value per share or coupon. Same group coverage presentation recurs by class; do not sum it. |
| F03 | Coverage denominator/formula definition | See definition below | PDF p65 footnote 2. |
| F04 | Applicable reported borrowing coverage minimum | 150% | Note 5 p274, effective June 21, 2019, measured after borrowing; contractual incorporation remains CP-4's work. |
| F05 | Aggregate senior securities principal outstanding | 13,789 USDm | 2024-12-31, Note 5 p274. |
| F06 | Aggregate carrying debt | 13,727 USDm | Same date/Note 5 p274; not interchangeable with F05. |
| F07 | July 2029 note principal | 850 USDm | Same date/Note 5 p274, reconciles principal amount in senior-securities table p65. |
| F08 | July 2029 note carrying value | 835 USDm | Same date/p274; footnotes p275 include issue costs/discount-premium and hedge-accounting effects; not a principal reduction. |
| F09 | July 2029 contractual fixed coupon received under associated swap | 5.950% | Note 5 p282 / F-172 swap row; contract still to be checked by CP-4. |
| F10 | July 2029 effective stated interest rate including swap | 6.040% | Same page, debt table with footnote 1; different economic basis from contractual coupon. |
| F11 | Cash and cash equivalents | 635 USDm | 2024-12-31, MD&A PDF p88; not automatically nettable against covenant senior securities. |
| F12 | Reported additional facility availability | Approximately 5.1 USDbn | Same date, MD&A p88; expressly subject to borrowing-base and other restrictions. Not unconditional liquidity, legal basket capacity or extra coverage headroom. |
| E01 | New March 2032 notes issued | 1,000 USDm | January 2025 subsequent event, Note 16 p300; not December principal. 5.800% fixed coupon; forward-starting swap effective Jan 8, 2026, not an already active 2024 swap. |
| E02 | Share repurchase authorization extension | Up to 1,000 USDm aggregate authorization | February 2025, Note 16 pp300–301: expiry extended Feb 15, 2025 to Feb 15, 2026. This is authority, not evidence of an executed 1,000 repurchase or known unused authority. |

F03: coverage for senior debt is consolidated total assets less liabilities and
indebtedness not represented by senior securities, divided by total senior
securities representing indebtedness. The published per-unit figure is that
ratio multiplied by USD 1,000. The source describes exemptive relief for specified
SBA debentures and historical accounting reclassifications; do not infer new
exclusions or reclassify all liabilities as debt. EBITDA is not this numerator.

## Calculations

No headroom calculation here. F02 supplies finer **published** coverage precision
than F01; it is not an unrounded raw ratio. Principal and carrying value remain
separate source facts. F05 minus F06 is not available cash or incremental debt
capacity. No forecast or pro-forma post-period coverage is created.

## Gaps

Unrounded covenant numerator/denominator bridge, actual transaction-date
certificate, full facility/series covenant set, realized subsequent repurchases,
net new-debt uses and complete contemporaneous changes. This focused extraction
does not recalculate all financial statements, every facility or subsequent ratio.

## Next module

CP-4 should use F04 with the selected executed documents, retain exemptions and
series-specific changes, and classify the test trigger. CP-4A may then use F02
and F03 for a published-precision coverage cushion, without substituting F06,
F08, F11 or F12 for the contractual denominator or dollar borrowing capacity.
