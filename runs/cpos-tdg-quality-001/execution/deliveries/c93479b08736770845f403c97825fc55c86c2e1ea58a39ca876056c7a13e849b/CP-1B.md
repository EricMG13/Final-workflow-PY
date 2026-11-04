# CP-1B — TDG actual first-quarter earnings update

## Request

Compare the issuer's first fiscal-quarter results, preserving exact periods:
current October 1–December 28, 2024 (89 inclusive days), prior October 1–December
30, 2023 (91 inclusive days). Both are labelled thirteen weeks by the issuer.
These are reported fiscal-quarter comparisons with a calendar-length limitation;
no dates, annualization or daily-rate adjustments are invented.

**Earnings view, Analyst Interpretation, Medium confidence:** reported sales,
operating income and operating cash increased, while distributions/repurchases
reduced the cash buffer. That supports historical earnings improvement with a
material cash-allocation constraint. It does not establish current liquidity
sufficiency, sustainable FCF, a rating or future refinancing ability.

## Sources

Actually opened and consumed `CP-1-attempt-2.md`, SHA-256
`8be815a5103120678d923721a7c52ab3ebaad28985a98df1f673be092d227582`, and the CP-0 source map.
This supplies all primary-statement, signed EBITDA bridge, account and period
facts below. Targeted checking uses H4, the retained December 28, 2024 10-Q,
SHA-256 `9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a`.
Locators are zero-based HTML table/row coordinates or one-based text-aid lines
identified by the source-preparation manifest. Evidence is unaudited consolidated
U.S. GAAP filing information, with management's non-GAAP measures attributed.

Selected broader method and later calculation/owner candidates:

- `skills/cp-1b-earnings-delta/references/REF_CP-1B_STEPS.md`: `5a5baa859471254ecba1807dfd067a8cc648fb5e0d40907dbc45a9b1edbd4889`.
- `src/deploy_workflow/earnings.py`: `6ae089ec784d105507b3577bddf517c787312c96da570640541d65baf4c0d8ed`.
- `src/deploy_workflow/owners/cp1b.py`: `db6d9307bb2f39abab7809a1a1660db0a9b2ec01a3523936d912500dd78b982d`.
- `src/deploy_vii/model/_cells.py`: `38c2ec4493b9b53065361db748a596687c7381eaf91659bc48fd9707ce7f2549`.
- `runs/tdg-003/CP-1B-instructions.md`: `412c3dd383807f50d811839c10613b984bd7c889dcd1fbedd0bff5dbaf056c0f`.

Execution is current-host-model analysis with local tools and existing Decimal
arithmetic, not isolated provider/API execution or legacy owner acceptance.
Actual private validation/label-function refusals are retained in the calculation
record. No IFRS identity, accepted execution head or provider receipt was fabricated.

## Findings

### Definition lock and top sheet

Amounts are USD millions except reported percentages. Ordinary EBITDA is the
issuer's net-income + D&A + net-interest + tax bridge; EBITDA As Defined adds
its signed adjustments. The source-rounded EBITDA margin below is explicitly
**As Defined**, not ordinary EBITDA margin. OCF-minus-capex 710/600 is a simple
cash-after-capex proxy, not a newly adopted FCF definition. Missing issuer FCF,
discretionary cash flow and maintenance/growth capex remain unavailable.

Reported current cash is 2,459. The issuer's cash-liquidity measure is 3,308,
including disclosed revolver availability 849; unrestricted/access conditions
remain unresolved. Carrying debt 25,049 and mechanical net carrying debt 22,590
are December instants. Their September comparisons 24,880 and 18,619 are
sequential balance changes, not prior-year December leverage observations.
No annual/LTM leverage, senior-secured leverage, covenant cover or FFO/debt is
calculated from this single-quarter update.

### Financial performance / comparator register

Comparison basis: reported fiscal Q1 year over year; exact window limitation
above applies to every row. Source locations are CP-1's named statement/bridge
sections and original H4 tables 10, 14 and 66. Percent changes below are calculated
from CP-1 values, rounded to two decimals only for display. Capex is kept signed;
positive percentage change means a larger outflow magnitude.

<!-- table-id: cp1b.model_comparator_register -->
| Metric | Prior | Current | Absolute change | Change % | Definition / source |
|---|---:|---:|---:|---:|---|
| Revenue | 1789 | 2006 | 217 | 12.13% | Reported sales |
| COGS | 747 | 771 | 24 | 3.21% | Reported expense |
| Gross profit | 1042 | 1235 | 193 | 18.52% | Reported |
| SG&A | 220 | 211 | -9 | -4.09% | Reported expense |
| Intangible amortization | 35 | 50 | 15 | 42.86% | Not total D&A |
| EBITDA | 859 | 1087 | 228 | 26.54% | Issuer ordinary EBITDA |
| EBITDA As Defined | 912 | 1061 | 149 | 16.34% | Signed issuer adjustments |
| EBIT | 787 | 974 | 187 | 23.76% | Reported operating income |
| Net interest expense | 300 | 378 | 78 | 26.00% | Accrual expense, not cash paid |
| Cash interest paid | 205 | 162 | -43 | -20.98% | Already included in OCF |
| Cash taxes paid | 11 | 37 | 26 | 236.36% | Net of refunds; already in OCF |
| OCF | 636 | 752 | 116 | 18.24% | Reported |
| Capex signed cash flow | -36 | -42 | -6 | 16.67% | Maintenance/growth split absent |
| OCF minus capex proxy | 600 | 710 | 110 | 18.33% | Calculated; not issuer FCF |
| Net income | 382 | 493 | 111 | 29.06% | Reported |
| Closing cash | 4135 | 2459 | -1676 | -40.53% | Quarter-end instants; not unrestricted cash |

| Additional required measure | Result / limitation |
|---|---|
| D&A | 71 prior / 90 current; source bridge, not just intangible amortization. |
| Gross margin | Source-rounded 58.2% → 61.6%; +3.4 percentage points. |
| EBITDA As Defined margin | Source-rounded 51.0% → 52.9%; +1.9 percentage points. |
| Maintenance/growth capex, aggregate normalized WC, issuer FCF and DCF | Not established under CP-1's definitions; do not invent a split or new metric. |
| Debt/EBITDA, net debt/EBITDA, senior-secured leverage, cash-interest cover and (EBITDA−capex)/cash-interest cover | No comparable reported/covenant ratios or accepted matching LTM bases in this increment. Quarterly quotients would answer a different question. |
| FFO/debt, issuer-FCF/debt and issuer-FCF conversion | Not Calculable: missing defined FFO/FCF and applicable matched bases. The cash-after-capex proxy does not substitute. |

### Variance mechanics and comparative credit evaluation

Revenue increased 217. The issuer's organic/acquisition sales categories explain
that arithmetic as organic +118 and acquisition +99 (H4 table 51). These are
management classifications. They do not independently isolate price, volume,
mix or purchase-accounting effects. Source MD&A attributes cost performance in
part to operating strategy and fixed overhead spread over volume, and identifies
FX gains (text 540); those are management explanations, not a causal model
validated by the comparative totals.

Ordinary EBITDA increased 228 while As Defined increased 149. The signed
adjustment bridge explains the difference: current 13 + 25 − 64 = −26 versus
prior 2 + 51 + source dash = 53, a decrease of 79. Thus growth in the adjusted
measure is lower than ordinary EBITDA growth. Recurrence/acceptance belongs in
CP-1D, especially the negative Other row and acquisition-related costs.

OCF increased 116, and the inherited cash-after-capex proxy increased 110.
Cash interest paid fell 43 while interest expense rose 78. The accrued-interest
change in CP-1's cash-flow statement is relevant to timing; these quantities
cannot be interchanged or subtracted again from OCF. Positive reported earnings
and OCF are the strongest counterargument to interpreting lower cash as an
operating collapse.

The cash buffer nevertheless fell: December cash is 1,676 below the prior-year
December balance and 3,802 below September. The sequential cash decline is
reconciled by the actual OCF/investing/financing/FX bridge, including financing
outflow 4,516. This indicates cash-allocation pressure alongside improved
historical earnings. No claim of covenant breach or impending distress follows.

No accepted budget, management numerical guidance, agency case or prior forecast
benchmark was supplied. Actual-versus-guidance/agency evaluation is unavailable.
Sequential earnings and LTM comparison also remain unavailable from this checked
increment; do not treat the static CP-2A shocks as forecasts of this quarter.

### Corporate actions, comparability and conflicts

| Event / scope | Evidence and comparison effect | Credit consequence / limitation |
|---|---|---|
| FY2024 acquisitions contribute to both comparison definitions | CP-1/H4 table 51 acquisition sales 112/13; earlier acquisitions and measurement-period adjustments appear in Note 2 | Organic categories help identify contribution, but no complete acquisition-adjusted like-for-like/pro-forma bridge is established. |
| CPI and SEI settlement updates | H4 text 215/234: CPI cumulative cash price 1,386 includes 1 paid in fiscal Q1; SEI 171 includes 1 paid in Q1 | Annual CPI 1,385 and interim 1,386 retain their dates/settlement distinction; no silent overwrite of prior canonical value. |
| October 18, 2024 distribution | H4 text 587: common dividend 4,216 and vested equivalents 131; annual handoff/PDF 146 identifies equivalents 132 | **Unresolved disclosure difference:** 131 versus 132. Retain both; do not force equality, classify the difference as rounding, or derive an unsupported residual allocation. |
| Whole-quarter distributions | CP-1 cash flows: 4,396 paid in the quarter, versus 2,038 prior | Different scope from the single October event; not a conflict requiring those totals to match. |
| Share repurchases | CP-1/current equity and H4 text 274: 252,800 shares for 316; remaining authorization 972 | Cash allocation competes with creditor buffers; authorization is not a cash commitment or legal-capacity opinion. |
| Securitization draw | CP-1 debt/flow maps: rounded quarterly cash proceeds 163 and carrying debt 649; annual event disclosure 162.5 | Preserve reporting precision, period and principal/carrying distinction; do not count the same financing twice. |
| Business-sale/FX and other adjustment items | CP-1 EBITDA footnote definitions and cash-flow gain row | Affect comparability; no unsupported sale date, buyer or allocation of the entire Other row is inferred. |
| Period/accounting compatibility | Real dates differ in length; both source periods remain U.S. GAAP | No annualization or IFRS relabeling. Literal fiscal-quarter differences can be shown with the stated limitation. |

### Validation, add-backs and publication readiness

<!-- table-id: cp1b.model_validation_register -->
| Metric / period | CP-1 versus original source | Result |
|---|---|---|
| Revenue 2006/1789; ordinary EBITDA 1087/859; As Defined 1061/912 | H4 tables 10/66, literal values and definitions | PASS for retained values; no replacement canonical figures. |
| CFO 752/636 and quarter closing cash 2459/4135 | H4 table 14 and independent statement checks | PASS; prior cash is the actual comparative December instant. |
| December carrying debt 25049 and cash-after-capex proxy 710/600 | CP-1 classification/proxy formulas, not issuer-reported totals under those exact names | PASS for stated derived meanings; no prior-year debt inferred. |
| Issuer FCF / reported leverage / guidance / workbook outputs | Not supplied or not published | WARN / unavailable; not zero and not a fabricated comparison. |

<!-- table-id: cp1b.addback_validation_register -->
| Issuer adjustment | Current / prior source cells | Label/definition match | Result |
|---|---|---|---|
| Acquisition transaction and integration-related expenses | 13 / 2 | Exact CP-1/H4 table 66 row 10 labels and source footnote | PASS transcription; not creditor acceptance. |
| Non-cash stock and deferred compensation expense | 25 / 51 | Exact CP-1/H4 table 66 row 11 labels | PASS transcription; not an assumption of cost disappearance. |
| Other, net | (64) / — | Exact CP-1/H4 table 66 row 12 and signed source footnote | PASS transcription; negative adjustment and source dash preserved. |

<!-- table-id: cp1b.cp_model_snapshot_fields -->
| field_id | value | status | source_id / locator | as_of |
|---|---|---|---|---|
| historical_performance | Reported fiscal Q1 sales, operating income and OCF increased; distributions and repurchases reduced the cash buffer. Adjusted and ordinary EBITDA growth differ because signed adjustments changed. | READY for this bounded historical field | H4 tables 10,14,66; CP-1 period/definition map | 2024-12-28 |

<!-- table-id: cp1b.model_readiness -->
| downstream_module | status | blocking evidence / explanation |
|---|---|---|
| CP-MODEL / delivery | historical field available; full publication remains restricted | No published workbook/chart validation, accepted LTM/current-accessibility/forward case, or resolution of 131/132 equivalents discrepancy. Preserve source scope and all limitations. |

### Monitoring and method changes justified by observed output

Track dated cash after distributions; future dividend/repurchase decisions;
revolver availability and borrowing conditions; the securitization renewal
milestone; operating cash versus interest accruals; adjusted-EBITDA definitions;
and organic/acquisition attribution. Evidence of sustained cash conversion,
accessible liquidity and policy restraint would strengthen the creditor case.
New extraction, weak conversion, restricted access or refinancing delays would
weaken it. Quantified covenant/rating thresholds remain absent.

The later pure period validator actually returned `incompatible_dimensions`
for the source-derived U.S. GAAP metadata. Its implementation hard-codes IFRS.
A separately supplied diagnostic report of actual nonzero deltas produced
`unsupported_pair` in its label function, which admits only flat or missing
comparisons. The source dates also fail its equal-calendar-duration condition;
that condition was inspected without falsifying the accounting metadata to
reach it. These are limitations of the imported earnings slice, not model
inability or issuer failures. Before automation, it needs matched actual
accounting/perimeter handling, a disclosed fiscal-comparability policy and
ordinary nonzero/driver/guidance assessments. No synthetic label substitution
or global accounting/date relaxation is justified.

## Calculations

`CP-1B-attempt-1-calculations.json` retains the exact consumed handoff hash,
source dates, 17 numerical comparisons, two margin-point changes and actual
legacy diagnostic results. Existing `_cells.CONTEXT` supplies 38-digit half-even
Decimal arithmetic; independent Fraction checks verify each delta exactly and
growth within 1e-35. Display is rounded only after those checks. The additional
signed-adjustment and sales-bridge arithmetic is retained in the same record.

## Gaps

All CP-1 G1–G7 remain. Additional constraints: the 131/132 vested-equivalents
source difference needs clarification; complete corporate-action/perimeter,
acquisition-adjusted and normalized recurring performance remain unproven;
quarterly leverage/covenant bases, peer/agency/guidance benchmarks, full LTM
series and workbook outputs are not available. The broader method's validation
registers do not prove that publication ran. Stronger confidence and current
liquidity/refinancing conclusions require those specific inputs.

## Next module

**CP-2D** should use the actual reported cash bridge and distinguish the October
event from whole-quarter distributions, retaining the equivalents discrepancy.
**CP-1D** should challenge the actual signed adjustments and cash-conversion
interpretation, retaining missing recurrence evidence. **Delivery** can consume
the historical-performance field and checked comparison table now. CP-MEMO has
been replaced by actual deliverables; no extra memo analysis is required.
This earnings answer is source-limited host-model evidence; actual downstream
consumption remains required and the imported owner/runtime remains unqualified.
