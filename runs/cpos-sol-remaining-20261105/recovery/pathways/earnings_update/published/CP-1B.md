# CP-1B — TDG historical December-quarter earnings comparison

## Request

Run `sol-remaining-tdg-earnings-20261105`, issuer `TDG`, TransDigm Group Incorporated; module CP-1B, attempt 1; method version `deploy-v-r14`; public earnings-update pathway. Historical analytical as-of: **2024-12-28**; run date encoded in the supplied run ID: **2026-11-05**. Compare fiscal Q1 **2024-10-01 through 2024-12-28** with **2023-10-01 through 2023-12-30**, retaining both issuer “Thirteen Week Periods Ended” labels and unequal actual calendar windows. No date repair, daily rebasing or annualized quarterly leverage is used.

**Earnings view...** Reported operating performance improved materially: revenue rose 217 to 2006, EBITDA As Defined rose 149 to 1061, and OCF rose 116 to 752. This is not an unqualified improvement in creditor protection: signed adjustments reduced current EBITDA to EBITDA As Defined, accrued-interest timing supported operating cash, and dividend/equivalent payments of 4396 plus repurchases of 316 drove a substantial cash reduction. Source-supported historical comparison is usable by CP-1D and CP-2D with restrictions; canonical model publication is blocked by missing upstream stable IDs and definition-register completeness, not by failure of the observed figures to reconcile.

Selected method: `cp-os b57a344 REF_CP-1B_STEPS.md`, SHA-256 `5a5baa859471254ecba1807dfd067a8cc648fb5e0d40907dbc45a9b1edbd4889`; calculation/source safeguards associated with final-workflow `886c1e1`. The supplied calculation-discipline section was applied before authoring. Excel is input only; this is an intermediate Markdown handoff carrying report, model, chart and JSON content, not a new workbook or final delivery. This response uses live source reads and Decimal tool executions, not an earlier CP-1B replay. Provider/model identity, paid-execution receipts and orchestration acceptance are not exposed by these tools and are not independently certified here. CP-0 and CP-1 are checked retained interim handoffs, not freshly executed modules in this test.

## Sources

The supplied CP-0 handoff is anchored to SHA-256 `aa6752f51236ca51dc452f247c212764947878eb21ffd36e6caa75fbfecb809d`; CP-1 to `8be815a5103120678d923721a7c52ab3ebaad28985a98df1f673be092d227582`. Their content was supplied in this request, including c-1/c-5 duration and c-3/c-4 balance mappings, statement rows, signed issuer bridges and limitations. Neither handoff supplies a separate current upstream run_id or machine-readable stable metric_id, period_id or addback_id register. These fields cannot be invented. H1–H4 retain the same issuer filings and representations used upstream. Tool inventory confirms the pinned source identities; this is not a new external-authenticity check.

T4.1 — source inventory:

| Source File Name | Document Type | Period Coverage | Evidence Quality Tier | Analytical Use | Limitations |
|---|---|---|---|---|---|
| H1: TDG_2024-03-30_10-Q_0001260221-24-000046_tdg-20240330.htm | Retained issuer 10-Q | Quarter ended 2024-03-30 | Primary filing, unaudited interim | Upstream scope inventory only | No full financial reread here; not an LTM input certification |
| H2: TDG_2024-06-29_10-Q_0001260221-24-000069_tdg-20240629.htm | Retained issuer 10-Q | Quarter ended 2024-06-29 | Primary filing, unaudited interim | Upstream scope inventory only | Same restriction |
| H3: TDG_2024-09-30_10-K_0001260221-24-000083_tdg-20240930.htm | Retained issuer 10-K | FY ended 2024-09-30 | Primary annual filing | FY-end identity; retained handoff context | Not a freshly validated annual/LTM financial extension |
| H4: TDG_2024-12-28_10-Q_0001260221-25-000014_tdg-20241228.htm | Retained issuer 10-Q, signed 2025-02-04 | Current/prior December quarters; 2024-09-30 closing balance | Primary filing, unaudited interim | All reported comparative amounts, definitions, corporate actions and liquidity narrative below | Historical evidence released after analytical as-of; not evidence of 2026 conditions |
| H4-text / H4-numbered.jsonl | Extracted text / line-numbered reading aid | H4 passages and context references | Derivative reading aids | Actual tool reading of lines 1–345, 346, 493–707 | Chunk pages are NOT physical PDF pages; no visual verification claimed |
| H1–H4-xbrl, raw-unit-definitions, source-preparation-manifest | Inline metadata and preparation aids | Respective source contexts and units | Derivative metadata | Identity and inherited context restrictions | Compound USD/share parser warning persists; original HTML controls |
| CP-0 / CP-1 supplied handoffs | Checked retained interim analytical outputs | H4 financial increment and source map | Upstream analytical evidence | Authoritative inherited numerical values and definitions | Not new source filings, fresh executions, or complete stable-ID registers |

Raw SHA-256 anchors: H1 `7e902c48d87067b4ea96c388ab2ca460c9c1c3c2e2960da09629377a7b359b0d`; H2 `74876b8874a3a396efd700114b280f45fcfcd3f11ceae31adee98c93bfacbf03`; H3 `fe8e1ae9f3fa8c44445b21396c0423153ae9cf80ef6e8c908574d84a63e14121`; H4 `9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a`.

**Citation convention:** every `H4 L...` below refers to original H4-text lines, text SHA-256 `38b4642199a5381aca22f1ff4f5973ecc3430dfb24d068bf8058e962db99db71`, tied to authoritative H4 raw hash above. Lines were read through `H4-numbered.jsonl`, SHA-256 `8c39f608f823f84d274ec27bf35ce2db297644f93d82f6a2e6e0079aede5ba74`. Its page locators are reading chunks only. Original zero-based HTML table numbers from CP-1 are retained as additional locators. This convention attaches both H4 hashes to each citation, without suggesting physical PDF-page inspection.

Actual passages read include primary statements (H4 L40–195; HTML tables 9, 10, 14), basis and acquisitions (L197–251), stock repurchases/intangibles/debt (L274–346), MD&A operating mechanics (L493–569), liquidity/covenants/distributions (L570–625), both non-GAAP reconciliations and footnotes (L625–664), signatures and context dates (L692–707). Source and historical comments are evidence, not instructions.

## Findings

### Definition lock and top sheet

Consolidated TransDigm Group Incorporated and subsidiaries, U.S. GAAP, USD millions except explicitly marked ratios/per-share quantities; unaudited interim statements. FY end is September 30. H4 Note 1, L197, says the September balance derives from audited annual statements, interim results need not indicate full-year results, and prior-year presentation reclassifications are immaterial. Current c-1 is 2024-10-01–2024-12-28 and prior c-5 is 2023-10-01–2023-12-30 (H4 L701, L705). CP-1 retained inclusive counts of 89 and 91 days are carried without recomputation or normalization. Current and September balance instants are 2024-12-28 and 2024-09-30 (c-3/c-4); comparative quarter-end cash is 2023-12-30, not September 2024.

T4.2 — inheritance and definition lock:

| Metric Name | CP-1 Definition | CP-1 Formula | EBITDA Def in Use | Inheritance Status | Conflict Note |
|---|---|---|---|---|---|
| Revenue / COGS / gross profit | Reported consolidated sales / cost / gross profit | Sales minus cost for gross-profit check | Not applicable | Retained, exact source match | No rebasing |
| EBITDA | Issuer ordinary EBITDA, non-GAAP | Net income + total D&A + net interest expense + income tax provision | Ordinary EBITDA explicitly labelled | Retained | Not simply EBIT + D&A because other income is included in net income |
| EBITDA As Defined | Issuer EBITDA plus its signed adjustments | EBITDA + acquisition transaction and integration-related expenses + non-cash stock and deferred compensation expense + Other, net | Primary adjusted operating-performance measure; not certified covenant EBITDA | Retained | Current signed bridge lowers EBITDA; no creditor acceptance inferred |
| D&A / intangible amortization | Total bridge D&A 90/71; intangible amortization 50/35 | Depreciation + amortization for total D&A | As above | Retained | Do not substitute intangible amortization for total D&A |
| OCF | Reported net cash provided by operating activities | Reported cash-flow statement | Not applicable | Retained | Already includes paid interest/taxes and asset/liability effects |
| OCF minus capex proxy | Cash after reported total capex, not sustainable FCF | OCF + signed capex | Not applicable | Retained | 710/600; no maintenance/growth split or discretionary-cash certification |
| Total / net debt | Carrying debt includes separate securitization; mechanical net debt subtracts reported cash | Long-term + current portion + securitization; less cash | No matched LTM denominator supplied | Retained December/September amounts | Not gross principal or unrestricted-cash net debt |
| FCF / DCF / FFO / leverage | No complete canonical definition/value register supplied | null for missing definitions/bases | No annualized quarter substitute | Gated | Proxy is not relabelled FCF; stable IDs missing |
| Cash-interest diagnostics | Cash paid is supplemental cash-flow figure 162/205 | Explicit historical ratios shown below, not new canonical CP-1 metrics | As Defined primary; ordinary EBITDA secondary | Source-supported analytical diagnostics only | Full CP-1 KPI definition register absent; model export blocked |

T4.3 — top sheet:

| Row Label | Value / Observation |
|---|---|
| Issuer | TransDigm Group Incorporated, consolidated |
| Period(s) | Fiscal Q1 2024-10-01–2024-12-28 versus 2023-10-01–2023-12-30; both issuer-labelled thirteen-week periods |
| EBITDA Def | Ordinary EBITDA and EBITDA As Defined retained separately; latter is primary adjusted measure |
| Revenue | Prior 1789; current 2006; change 217 / 12.13% |
| EBITDA | Ordinary 859 → 1087; As Defined 912 → 1061 |
| EBITDA Margin | Ordinary 48.02% → 54.19%; As Defined 50.98% → 52.89% |
| FCF | Sustainable/issuer-defined FCF unavailable; OCF minus capex proxy 600 → 710 only |
| Total/Net Leverage | Not Calculable: no matched validated LTM denominator and complete canonical definition |
| Cash Interest Coverage | Historical As Defined / cash interest 4.45x → 6.55x; timing-sensitive, not covenant or annual coverage |
| Liquidity | At 2024-12-28 cash 2459; issuer revolver availability 849; issuer cash liquidity 3308; not all certified unrestricted/accessible |
| Key YoY Variance | Revenue 12.13%, As Defined EBITDA 16.34%, OCF 18.24%; closing cash down 40.53% against prior December |
| Key Credit Observation | Better operations, but shareholder cash uses dominate retained cash; no supported leverage/headroom conclusion |

### Financial performance / comparator register

All monetary values below are USD millions. Table displays “Not supplied” or “Not calculable” render missing/null data without converting them to zero; JSON retains actual null values. Prior/current flow columns retain the exact windows stated above; closing cash is their respective end-date balance. Absolute change = current minus prior. Change percentages use positive prior denominators, not daily-normalized bases. These are separately labelled historical Decimal comparisons, not native acceptance by the later paired-period component.

| Metric | Prior | Current | Absolute change | Change % | Definition / source |
|---|---|---|---|---|---|
| Revenue | 1789 | 2006 | 217 | 12.13% | Reported net sales; H4 L79, table 10 row 3 |
| COGS | 747 | 771 | 24 | 3.21% | Reported cost of sales; L80, table 10 row 4 |
| Gross profit | 1042 | 1235 | 193 | 18.52% | Reported gross profit; L81, table 10 row 5 |
| SG&A | 220 | 211 | -9 | -4.09% | Selling and administrative expenses; L82, table 10 row 6 |
| Intangible amortization | 35 | 50 | 15 | 42.86% | Intangible amortization only; L83, table 10 row 7 |
| EBITDA | 859 | 1087 | 228 | 26.54% | Issuer ordinary EBITDA; L628–633, table 66 row 8 |
| EBITDA As Defined | 912 | 1061 | 149 | 16.34% | Issuer signed adjusted measure; L635–638, table 66 row 13 |
| EBIT | 787 | 974 | 187 | 23.76% | Reported income from operations; L84, table 10 row 8 |
| Net interest expense | 300 | 378 | 78 | 26.00% | Accrual measure, not paid interest; L85 |
| Cash interest paid | 205 | 162 | -43 | -20.98% | Cash paid for interest, net; L194, table 14 row 55 |
| Cash taxes paid | 11 | 37 | 26 | 236.36% | Cash tax net of refunds; L195, table 14 row 56 |
| OCF | 636 | 752 | 116 | 18.24% | Net cash from operating activities; L173 |
| Capex signed cash flow | -36 | -42 | -6 | 16.67% | Source outflows preserved; H4 L175 reread. (-6)/(-36) = 6/36 by simultaneous sign inversion; calculate ratio(6,36). Positive change means greater cash outflow, not improvement |
| OCF minus capex proxy | 600 | 710 | 110 | 18.33% | OCF + signed capex; CP-1 inherited proxy, not sustainable FCF |
| Net income | 382 | 493 | 111 | 29.06% | Consolidated net income; L89 |
| Closing cash | 4135 | 2459 | -1676 | -40.53% | Respective December closing cash; L192, table 14 row 53 |

| Additional required measure | Prior | Current | Absolute change | Change % / status | Definition / source |
|---|---|---|---|---|---|
| Gross margin | 58.24% | 61.57% | 3.32 pp | Percentage-point comparison | Gross profit / revenue; H4 L79–81; unrounded ratios used for difference |
| EBITDA margin | 48.02% | 54.19% | 6.17 pp | Percentage-point comparison | Ordinary EBITDA / revenue; L633, L79 |
| EBITDA As Defined margin | 50.98% | 52.89% | 1.91 pp | Percentage-point comparison | As Defined / revenue; L638, L79 |
| Total D&A | 71 | 90 | 19 | 26.76% | Issuer bridge D&A; L630; not intangible amortization alone |
| Total capex magnitude | 36 | 42 | 6 | 16.67% | Presentation of cash use, not replacement of signed source capex |
| Maintenance capex | Not supplied | Not supplied | Not calculable | Not Calculable | No split provided |
| Growth capex | Not supplied | Not supplied | Not calculable | Not Calculable | No split provided |
| Asset/liability cash-flow contribution | 111 | 188 | 77 | 69.37% | Broad sum of L166–172; includes tax/interest accruals, NOT a narrowly defined trade-WC metric; opposite sign in EBITDA reconciliation L647 |
| Canonical WC change | Not supplied | Not supplied | Not calculable | Not Calculable | Full inherited WC metric definition absent; broad contribution above must not silently become canonical WC |
| FCF | Not supplied | Not supplied | Not calculable | Not Calculable | Sustainable/issuer-defined FCF unavailable |
| DCF | Not supplied | Not supplied | Not calculable | Not Calculable | Definition and required cash claims absent |

T4.5 — KPI dashboard. Ratios involving quarterly cash payments are historical diagnostics only, not new canonical metrics or covenant ratios. Positive denominator checks were executed. Missing values propagate as null.

| KPI Category | Metric Name | Prior | Current | YoY Change | Trend Direction | Calculation Status | Analyst Note |
|---|---|---|---|---|---|---|---|
| Leverage | Total Debt/EBITDA | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | Matched LTM and authoritative definition unavailable; no quarterly annualization |
| Leverage | Net Debt/EBITDA | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | Same; unrestricted-cash status also missing |
| Leverage | Senior secured leverage | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | No legal numerator/denominator certification |
| Coverage | EBITDA As Defined / cash interest | 4.45x | 6.55x | 2.10x | Apparent improvement | Calculated diagnostic | 912/205; 1061/162; payment timing materially limits inference |
| Coverage | Ordinary EBITDA / cash interest | 4.19x | 6.71x | 2.52x | Apparent improvement | Calculated diagnostic | 859/205; 1087/162; not a substitute for matched annual coverage |
| Coverage | (As Defined EBITDA - total capex magnitude) / cash interest | 4.27x | 6.29x | 2.02x | Apparent improvement | Calculated diagnostic | 876/205; 1019/162; no maintenance/growth split, no tax deduction |
| Cash | FFO/Debt | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | No inherited FFO definition/value and matched basis |
| Cash | FCF/Debt | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | Proxy is not FCF; no valid matched basis |
| Cash | FCF conversion | Not calculable | Not calculable | Not calculable | Unknown | Not Calculable | Canonical/sustainable FCF absent |
| Cash | Proxy / EBITDA As Defined | 65.79% | 66.92% | 1.13 pp | Slight improvement | Calculated diagnostic | 600/912; 710/1061; not labelled canonical FCF conversion |
| Profitability | Gross margin | 58.24% | 61.57% | 3.32 pp | Improved | Calculated | Foreign exchange/loss-contract effects temper extrapolation |
| Profitability | EBITDA As Defined margin | 50.98% | 52.89% | 1.91 pp | Improved | Calculated | Signed bridge remains management-defined |
| Growth | Revenue growth | Not supplied | 12.13% | Not calculable | Improved YoY sales | Calculated current YoY only | Prior year's own growth needs another comparison period |
| Liquidity | Closing cash | 4135 | 2459 | -1676 | Deteriorated | Reported and calculated delta | December-to-December, not September-to-December |
| Liquidity | Issuer cash liquidity | Not supplied | 3308 | Not calculable | No matched prior measure | Current arithmetic checked | 2459 + 849; H4 L588–591; no prior December availability supplied |

### Variance mechanics and comparative credit evaluation

T4.6 — material variance mechanics (same fiscal quarter YoY; unequal calendar windows retained). Numerical deltas below reuse executed calculations or explicitly quoted issuer bridge values.

| Metric | Comparison Basis | Prior Value | Current Value | Abs Change | % Change | Mgmt Driver | Analyst Driver | Credit Implication |
|---|---|---|---|---|---|---|---|---|
| Revenue | Reported fiscal Q1 YoY | 1789 | 2006 | 217 | 12.13% | Organic sales increase 118; acquisition sales increase 99; H4 L520–523 | Both organic and acquisition contribution; no independent price/volume attribution | Broader earnings base, but not constant-perimeter reported growth |
| Gross profit | Same pair | 1042 | 1235 | 193 | 18.52% | Value-driven strategy and fixed-cost absorption; FX gains; L526–540 | Favorable accounting/FX items accompany genuine sales growth | Margin gain should not be fully extrapolated |
| SG&A | Same pair | 220 | 211 | -9 | -4.09% | Stock/deferred compensation reduction; L543–551 | Underlying SG&A excluding named items rose to 184 from 174, per issuer | Headline expense improvement is not wholly structural savings |
| Intangible amortization | Same pair | 35 | 50 | 15 | 42.86% | FY2024 acquisition intangibles; L551 | Acquisition perimeter raises noncash amortization | Reported EBIT and non-GAAP measures need separate interpretation |
| EBIT | Same pair | 787 | 974 | 187 | 23.76% | Operating factors above | Gross profit gain 193 + SG&A relief 9 - amortization increase 15 = 187 | Clear reported operating improvement |
| EBITDA | Same pair | 859 | 1087 | 228 | 26.54% | Sales, cost absorption and other reported income effects | Includes other income; ordinary EBITDA is not EBIT + D&A alone | Larger gain than adjusted measure warrants bridge scrutiny |
| EBITDA As Defined | Same pair | 912 | 1061 | 149 | 16.34% | Segment growth and acquisitions; L563–569 | Net adjustments change from 53 to -26, a -79 swing | Avoid assuming all adjustments add earnings |
| Net interest expense | Same pair | 300 | 378 | 78 | 26.00% | Higher borrowings and issuer-reported 10 lower interest income; L551 | Expense rises despite lower quarter cash payment | Debt burden offsets operating improvement |
| Net income | Same pair | 382 | 493 | 111 | 29.06% | Operating gains, interest burden, sale gain and tax effects; L551 | EBIT gain 187 - interest increase 78 + other-income gain 22 - tax-provision increase 20 = 111 | Stronger reported earnings, with nonrecurring/mix effects |
| OCF | Same pair | 636 | 752 | 116 | 18.24% | Receipt, inventory and supplier-payment timing; L592 | Broad asset/liability contribution rises 77; accrued-interest contribution rises 119 | Cash generation improves but not solely from durable earnings |
| Cash interest paid | Same pair | 205 | 162 | -43 | -20.98% | Supplemental payments, semiannual note schedules; L194, L609 | Accrual net interest is 378; current accrued-interest cash-flow source 201 | Quarterly coverage improvement is not matched economic debt-service relief |
| Cash taxes paid | Same pair | 11 | 37 | 26 | 236.36% | Cash-flow supplemental disclosure; L195 | Cash paid is not tax provision 126/106 | Use cash tax in cash analysis without deducting it twice from OCF |
| Capex magnitude | Same pair | 36 | 42 | 6 | 16.67% | Investment at existing operations; L175 | Total capex only; no maintenance/growth split | Proxy cash flow improves despite greater spend |
| Proxy cash after capex | Same pair | 600 | 710 | 110 | 18.33% | Higher OCF partly offset by capex | Not sustainable free/discretionary cash | Useful historical cash marker, not distribution capacity |
| Closing cash | December instant YoY | 4135 | 2459 | -1676 | -40.53% | Distribution-heavy financing; L181–192 | September-to-December reduction separately -3802 | Lower cash cushion despite stronger earnings |

Management's sales bridge is 1894/1776 organic sales and 112/13 acquisition sales (H4 L520–523; HTML table 51). The increases 118 and 99 sum to 217. The organic-category growth ratio is 6.64% (118/1776); the organic and acquisition contributions to consolidated prior sales are 6.60 and 5.53 percentage points respectively (118/1789 and 99/1789). The issuer's 5.5% acquisition column is a contribution to total growth, not acquisition-category growth; it must not be read as 99/13. Categories reclassify acquired businesses after one year, so even this management organic bridge is not a substitute for independent pro forma constant-perimeter earnings. Management attributes organic defense improvement of 80 to government spending outlays, aftermarket improvement of 57 to flight hours/utilization, and OEM decline of 16 to the Boeing strike (L523). No price/volume split is supplied.

Cost and margin quality are mixed. The MD&A reports cost of sales excluding separately listed items of 801/732, inventory step-up 7/1, loss-contract amortization -19/-5, and foreign-currency gains/losses -20/14 (H4 L526–539). These issuer components explain why headline COGS growth is much lower than sales growth. SG&A excluding listed costs is 184/174 while the stock/deferred compensation component is 23/45 (L543–551); management links the reduction to stock-price-sensitive valuation. These are analytical cautions, not authority to create another adjusted EBITDA or reverse CP-1 normalization. Acquisitions also raise intangible amortization. Gross margin and ordinary EBITDA margin therefore improve more than EBITDA As Defined margin; quality and recurrence remain CP-1D work.

The signed issuer bridge matters: acquisition transaction and integration-related expenses rise from 2 to 13 (change 11); non-cash stock and deferred compensation expense falls from 51 to 25 (change -26); Other, net moves from a displayed dash to -64 (numerically zero to -64 only for this explicitly zero-dash bridge). Total signed adjustments move from 53 to -26, a -79 swing. EBITDA growth of 228 plus that swing gives As Defined growth of 149. Other, net includes foreign currency, payroll withholding taxes on dividend equivalents/options, non-service pension costs, deferred compensation payments and miscellaneous income including business sale gain (H4 L639–641, L663–664). No recurrence or achievability conclusion is inferred from arithmetic agreement.

Cash/earnings interpretation: OCF already incorporates paid interest, paid taxes and asset/liability movements. Its 188/111 broad asset/liability contribution includes accrued interest of 201/82, tax payable 91/94, receivables 80/94, inventory -79/-78, other assets -2/3, payables -3/-21 and other accruals -100/-63 (H4 L165–173). The issuer EBITDA cash bridge reverses these broad contributions as -188/-111. It then uses interest expense net of debt-cost amortization of 369/289 and current tax provision of 128/106, not cash paid of 162/205 and 37/11 (L645–661). The two bridges reconcile but are different quantities; neither proves sustainable FCF. No cash-interest or tax double deduction is made from OCF.

The dated cash bridge is decisive. September cash 6261 + OCF 752 - investing 24 - financing 4516 - FX 14 = December cash 2459, a reduction of 3802 or 60.73%. This is distinct from the December YoY reduction of 1676. Financing comprises -4396 dividends/equivalents, -316 repurchases, +163 securitization, +35 option proceeds and -2 financing costs/other. Source term-loan repayment and issuance lines display dashes; management explicitly says no first-quarter term-loan payment occurred because of quarter-end timing despite the contractual quarterly aggregate 22 (H4 L598). Do not insert a hypothetical payment. Positive OCF and issuer cash liquidity of 3308 are counterweights to cash extraction, not proof of accessible forward runway.

No accepted budget, base case, numeric guidance, rating-agency expectation or peer benchmark is supplied for a matched variance test. Sequential income, complete validated LTM, prior-year YTD beyond this first quarter, and matched peer metrics are unavailable. Historical prior-quarter or annual amounts must not be mixed into the fiscal-Q1 flow comparison. Qualitative management optimism is not a quantified accepted forecast. These gaps do not block the source-supported YoY analysis above.

T4.8 — benchmark register:

| Metric | Benchmark Source | Benchmark Type | Expected Value | Actual Value | Variance | Credit Implication |
|---|---|---|---|---|---|---|
| Revenue | No accepted benchmark supplied | Budget/base case/guidance/rating agency | Not supplied | 2006 | Not calculable | No beat/miss claim |
| EBITDA As Defined | No accepted benchmark supplied | Same | Not supplied | 1061 | Not calculable | No outperformance-versus-plan claim |
| Sustainable FCF | Not supplied | Same | Not supplied | Not supplied | Not calculable | Proxy cannot fill benchmark or FCF gap |
| Peer margins/leverage | No defined peer universe/metrics | Peer | Not supplied | Not supplied | Not calculable | No relative-ranking claim; CP-1C remains separate |

T4.7 — corporate actions and comparability (events identified in the relevant H4 passages, not a certification that every H1–H3 event was reread):

| Event | Date | Description | Quantified Impact | Comparability Effect | Credit Implication | Source |
|---|---|---|---|---|---|---|
| Raptor Scientific acquisition | 2024-07-31 | Cash-funded; Airframe; purchase allocation remains provisional | Approximate purchase price 646, including first-quarter settlement received 1 | Current quarter contains business absent prior comparison | Adds earnings/perimeter; pro forma results deemed immaterial by issuer, not supplied | H4 L197–215, Note 2 |
| CPI Electron Device Business acquisition | 2024-06-06 | Cash-funded; Power & Control; provisional allocations | Approximate purchase price 1386, including first-quarter settlement paid 1 | Expanded current perimeter and amortization | Purchase-accounting revisions limit precise constant-perimeter attribution | L215–234 |
| SEI acquisition | 2024-05-21 | Cash-funded; Airframe | Approximate purchase price 171, including first-quarter settlement paid 1 | Current perimeter expansion | Same pro forma limitation | L234–251 |
| FPT acquisition | 2024-03-01 | Cash-funded; Airframe | Approximate purchase price 57 | Current perimeter expansion | Integration/add-back quality unproven | L251 |
| Extant product-line businesses | Current quarter; individual dates not supplied | Power & Control; acquisition method; preliminary allocation | Purchase price 29; FY2024 series 86 | Acquired product lines affect earnings comparability | Additional capital allocation and integration needs | L251; cash flow L176 |
| Purchase-price allocations | Current quarter | Open measurement periods and fair-value revisions | CPI intangible adjustment 141; Raptor intangible adjustment 4; SEI intangible adjustment 7, issuer tables | Amortization effects cannot be attributed solely to organic performance | No new adjusted canonical values | L198–250, L308 |
| Business disposal / other investing | Current quarter; exact disposal date/details absent | Gain on sale reported; other investing inflow separately disclosed | Gain 19; other investing inflow 47 | One-off income and cash effects; do not equate 47 entirely to disposal proceeds | Need transaction detail for recurrence and cash-quality review | L161, L177, L551, L652 |
| Dividend paid on September declaration | 2024-10-18 | Special dividend 75 per common share; equivalents under option plans | Dividend 4216; total quarterly equivalents 180; total quarterly distribution cash 4396 | September liability settlement is not a new first-quarter dividend declaration | Cash extraction materially lowers buffer | L587, L625, L181 |
| Repurchases | Fiscal Q1; source intervals 2024-10-27–2024-11-23 and 2024-11-24–2024-12-28 | Common shares repurchased | Cash 316; 252800 shares; remaining authorization 972 | No current-quarter financing cash comparability with prior dash | Shareholder allocation competes with debt reduction; authorization is not cash commitment | L274, L671–675 |
| Securitization amendment and draw | Amendment 2024-07-12; draw in current quarter | Capacity increased; final availability drawn | Capacity/gross borrowing 650, carrying 649; quarter draw 163; expiry 2025-07-11 | Higher debt and lower remaining facility liquidity | Historical refinancing/extension dependency; no subsequent renewal assumed | L311, L346, L625 |
| Prior comparator financing | Prior fiscal Q1 | Senior-secured note and term-loan proceeds present in prior cash flow | Net note proceeds 983 and term-loan proceeds 988; current both dashes | Financing-cash YoY is not an operating trend | Separate refinancing from earnings | L183–186; L609 |
| Covenant amendment context | 2024-03-22 | Amendment 15 identified as latest restrictive-covenant change | Incremental debt tests and revolver trigger described, not headroom quantified | No assumption legal definitions equal analytical ratios | Full documentation/certificate needed | L625 |
| Accounting/reclassification | Reported at 2024-12-28 | Prior reclassifications described as immaterial; new ASUs future adoption | No material financial impact quantified | No material restatement reported in the read passage; no independent full restatement certification | Preserve presentation warning; no adjustment made | L197 |

The retained annual comment of an October 4348 payment is not the quarterly distribution line. H4 resolves the scope: 4216 dividend + 180 total quarterly equivalents = 4396. Of the equivalents, 131 relate to the September special dividend, leaving 49 other quarterly equivalents. The arithmetic difference between 4396 and the retained 4348 comment is 48, but it is not a newly inferred transaction: the annual figure and quarterly rounded components retain separate scope and precision. H4's quarterly line is authoritative for this quarter. A newly declared first-quarter dividend must not be inferred from cash payment of the September declaration (H4 L625).

T4.9 — conflict log:

| Conflict Description | Source(s) | Metric(s) | Period(s) | Materiality | Resolution Status | Downstream Impact |
|---|---|---|---|---|---|---|
| Thirteen-week labels versus unequal source calendar windows | CP-0/CP-1; H4 c-1/c-5 | All flows | Both Q1 windows | High methodological | Retained exact dates, no repair | Later IFRS/equal-duration component cannot certify this case |
| Ordinary EBITDA exceeds As Defined currently | CP-1; H4 L633–638 | EBITDA bridge | Current Q1 | High | Reconciled signed -26 net adjustments | CP-1D must retain negative Other, net |
| Interest expense versus paid interest versus cash-bridge interest | H4 L85, L194, L648, L661 | Interest | Both quarters | High | Distinct quantities, no substitution | No timing-blind cash coverage interpretation |
| September cash versus prior December cash | H4 L44, L191–192 | Cash | 2024-09-30, 2024-12-28, 2023-12-30 | High | Separate sequential balance bridge and YoY balance comparison | CP-2D receives both, not conflated |
| Annual October payment comment versus quarterly distributions | CP-1 commentary; H4 L625 | Distributions | Current Q1 | High | Quarterly line supported by 4216 + 180; annual comment not forced to equal it | Use 4396 for observed quarter; retain annual precision/scope caution |
| Direct signed capex denominator rejected by kernel | Decimal ratio execution; H4 L175 | Capex change % | Both Q1 | Medium | Resolved algebraically: (-6)/(-36) = 6/36 = 16.67%; original signed values unchanged | Positive percentage indicates increased cash use; no native component acceptance inferred |
| Full upstream IDs/run_id/definition register absent | Supplied CP-1/CP-0 | Machine-ready fields/KPI definitions | Entire increment | High | Unresolved; block canonical export | No invented IDs or canonical synonyms |
| Rounded issuer percentages versus calculated ratios | H4 L539, L568; CP-1 | Margins | Both Q1 | Low | Issuer rounded display kept distinct from calculated ratios | Differences computed from unrounded fractions |
| Carrying debt versus gross principal | CP-1; H4 L311–344, L575 | Debt | December/September | High | Carrying basis locked | No gross-principal leverage substituted |

No numerical transcription mismatch was found in the selected CP-1 financial values and issuer adjustment rows checked against the read H4 passages. That bounded statement is not an assertion that all definitions, legal terms or every filing were validated.

### Monitoring and method changes justified by observed output

Track dated cash, not just earnings or a headline adjusted multiple. CP-2D should start its historical bridge with 6261 at 2024-09-30, apply +752/-24/-4516/-14, and close at 2459 on 2024-12-28. Separately retain prior 2023-12-30 cash of 4135. Refresh cash restrictions, location/accessibility, revolver borrowing conditions, near-term interest/tax payment dates, acquisition commitments and shareholder allocation plans before any runway or funding-sufficiency conclusion. The fully drawn securitization's 2025-07-11 contractual expiry is a historical forward trigger from this as-of, not evidence of an actual later default or renewal.

T4.10 — evidence-linked monitoring assessment:

| Signal Type | Metric/Indicator | Evidence | Severity | Credit Implication | Recommended Action |
|---|---|---|---|---|---|
| Improvement | Sales and adjusted operating earnings | Revenue +217; As Defined +149; H4 L520–523, L568 | Material positive | More earnings support, partly acquired | Track organic defense/aftermarket and acquisition cohort roll-off |
| Quality caution | Gross margin and SG&A drivers | FX/loss-contract effects; compensation valuation; L526–551 | Medium | Headline gains not all recurring cost advantage | CP-1D inspect adjustment composition and earnings quality |
| Deterioration | Cash buffer/extraction | Cash -3802 since September; distributions -4396, repurchases -316; L181–192 | High | Better earnings did not produce balance-sheet retention | CP-2D refresh dated sources/uses and policy sensitivity |
| Timing caution | Interest/OCF | Paid interest 162; expense 378; accrued-interest source 201; L85, L171, L194 | High | Quarter cash conversion/coverage may reverse with payment dates | Obtain schedule; do not extrapolate coverage |
| Refinancing trigger | Fully drawn securitization | Gross 650; expiry 2025-07-11; L346, L625 | High monitoring priority | No unused capacity in this facility at as-of | Obtain extension/termination conditions and subsequent evidence separately |
| Covenant proximity | Revolver springing covenant | L625: usage above 40% / 364 triggers trailing-four-quarter test 7.50x, or 8.00x in specified acquisition circumstances | Unknown headroom | Trigger terms are not a computed covenant breach/headroom | CP-4 obtain documents, certificate, usage definitions and legal EBITDA |
| Incremental capacity | Debt-incurrence tests | L625: 7.25x net and 5.00x secured-net tests described | Unknown headroom | Not maintenance thresholds or available dollar capacity | No analytical headroom from quarterly earnings |
| Rating migration | Agency thresholds/outlook | No agency evidence supplied | Unassessable | No rating-trigger claim | Obtain dated agency criteria and matched financial basis |
| Liquidity counterweight | Cash plus issuer revolver availability | 2459 + 849 = 3308; L588–591; compliance attributed at L625 | Positive but conditional | Liquidity assertion not independent accessibility test | Validate borrowing conditions and restricted cash |

Method change justified by output: use the existing shared Decimal-38 kernel for a **separately labelled historical U.S. GAAP unequal-window comparison**. The later paired-period component is narrowly IFRS-only/equal-duration; it cannot certify this case. Its engine was not rebuilt and no native acceptance is manufactured. Kernel output rejects direct division by a negative denominator. Preserve that raw tool result in the trace, but calculate the conventional signed capex percentage by simultaneous numerator/denominator sign inversion: (-6)/(-36) equals 6/36, or 16.67%. This algebra does not change the signed original pair, dates, economic convention or accounting basis. Missing stable IDs require an export gate, not replacement canonical IDs. No changes to accounting basis, CP-1 values, normalization, add-back labels or source dates are justified by this run.

Overall earnings view: the observed fiscal-Q1 comparison shows better sales, reported operating earnings, adjusted operating earnings and OCF, with margin expansion. Acquisition perimeter, foreign currency and compensation valuation complicate extrapolation; accrued-interest timing complicates cash conversion. Distribution-heavy cash uses, not an operating loss, explain the cash contraction. Historical figures and restrictions are ready for bounded CP-1D and CP-2D consumption. Sustainable cash generation, matched LTM leverage, covenant headroom, current liquidity sufficiency and benchmark performance remain unproven. The following validation/readiness registers preserve those distinctions rather than elevating arithmetic agreement into model acceptance.

## Calculations

All new sums, differences and ratios were executed with `calculate`, Decimal-38 half-even. Source figures are inherited CP-1 displayed USD millions, not re-normalized dollar facts. Tool inputs have no metadata fields, so this trace supplies the period, currency, quantity, source and formula map for those calls. Ratio outputs are fractions; percentage display shifts the decimal point and rounds to two decimals only. Margin changes use unrounded ratio differences multiplied by 100 for percentage points. `null` is missing/not calculable, never zero. A source dash `—` remains a dash; explicit zero-dash bridge arithmetic is separately disclosed below.

#### Calculation trace and reproducibility map

| Trace | Period / quantity / source | Executed inputs or formula | Result / handling |
|---|---|---|---|
| C01–C16 | Same reported Q1 pair; USD million differences; first comparator table source rows | For each row, sum(current, -prior), in displayed order | 217; 24; 193; -9; 15; 228; 149; 187; 78; -43; 26; 116; -6; 110; 111; -1676 |
| C17 | Same pair, ratio fractions; same source rows | Each above difference / prior using calculate ratio | Display percentages in first comparator table; direct capex ratio(-6,-36) returns null, `ZERO_OR_NEGATIVE_DENOMINATOR`. After rereading H4 L175, conventional signed growth is computed equivalently as ratio(6,36), 16.67%, by reversing both signs, not just the denominator |
| C18 | Same Q1 pair; total D&A, USD millions; H4 L630 | 90 - 71; 19 / 71 | 19; 26.76% |
| C19 | Same pair; margin fractions; H4 L79–81, L633, L638 | 1235/2006; 1042/1789; 1087/2006; 859/1789; 1061/2006; 912/1789 | Gross 0.61565304087736789631106679960119641077 / 0.58244829513694801565120178870877585243; ordinary 0.54187437686939182452642073778664007976 / 0.48015651201788708775852431525992174399; As Defined 0.52891326021934197407776669990029910269 / 0.50978200111794298490776970374510899944 |
| C20 | Same pair; margin fraction differences | Current minus prior unrounded ratios from C19 | 0.03320474574041988065986501089242055834; 0.06171786485150473676789642252671833577; 0.01913125910139898916999699615519010325; display 3.32/6.17/1.91 pp |
| C21 | Same pair; cash-interest coverage, dimensionless; H4 L194, L633, L638 | 1061/162; 912/205; 1087/162; 859/205; current-prior differences | As Defined 6.5493827160493827160493827160493827160 / 4.4487804878048780487804878048780487805, delta 2.1006022282445046672688949111713339355; ordinary 6.7098765432098765432098765432098765432 / 4.1902439024390243902439024390243902439, delta 2.5196326407708521529659741041854862993 |
| C22 | Same pair; capex-adjusted diagnostic, USD millions then ratio; H4 L175, L194, L638 | 1061-42=1019; 912-36=876; 1019/162; 876/205; difference | 6.2901234567901234567901234567901234568 / 4.2731707317073170731707317073170731707; delta 2.0169527250828063836193917494730502861 |
| C23 | Same pair; proxy and conversion, H4 L173, L175, L638 | 752+(-42); 636+(-36); 710/1061; 600/912; ratio difference | 710/600 USD millions; conversion 0.66918001885014137606032045240339302545 / 0.65789473684210526315789473684210526316; delta 0.01128528200803611290242571556128776229 or 1.13 pp |
| C24 | Current/prior Q1 ordinary EBITDA, USD millions; H4 L628–633 | sum(493,90,378,126); sum(382,71,300,106) | 1087; 859 |
| C25 | Current/prior Q1 As Defined EBITDA, USD millions; H4 L635–638 | sum(1087,13,25,-64); sum(859,2,51,0) | 1061; 912. Prior Other, net displayed `—`; zero only for explicitly identified bridge cell, not missing data |
| C26 | Current/prior Q1 OCF-to-EBITDA check, USD millions; H4 L645–655 | sum(752,-188,369,128,-7,19,19,-25,20); sum(636,-111,289,106,-1,5,0,-51,-14) | 1087; 859. Prior gain-on-sale cell displayed `—`, explicit zero-dash in check only |
| C27 | Current/prior Q1 broad asset/liability contribution, USD millions; H4 L166–172 | sum(80,-79,91,-2,-3,201,-100); sum(94,-78,94,3,-21,82,-63); difference and 77/111 | 188; 111; change 77 / 69.37%; not canonical trade WC |
| C28 | Q1 adjustment swing, USD millions; H4 L635–637 | sum(13,25,-64); sum(2,51,0); 13-2; 25-51; -64-0; -26-53 | Current net -26; prior net 53; component changes 11/-26/-64; net swing -79 |
| C29 | Current/prior Q1 cash-flow and current cash bridge, USD millions; H4 L173–192 | sum(752,-24,-4516,-14); sum(636,-50,67,10); 6261-3802; 3472+663 | Net changes -3802 / 663; closing 2459 / 4135 |
| C30 | Current Q1 financing, USD millions; H4 L180–188 | sum(-4396,-316,163,35,-2) | -4516; other source debt-flow cells remain displayed dashes |
| C31 | Current quarter distribution scope, USD millions; H4 L625; retained annual comment | 4216+180; 180-131; 4396-4348 | 4396; 49 other quarterly equivalents; 48 arithmetic gap to differently scoped retained comment, not an inferred transaction |
| C32 | December/September carrying debt, USD millions; H4 L56–62, L575; CP-1 | sum(24302,98,649); sum(24296,98,486); 25049-2459; 24880-6261; differences | Debt 25049/24880; mechanical net debt 22590/18619; changes 169/3971; no leverage ratio |
| C33 | 2024-12-28 issuer cash liquidity, USD millions; H4 L588–591 | 2459+849 | 3308; attribution/availability limitations retained |
| C34 | Sales bridge; same Q1 pair, USD millions and fractions; H4 L520–523 | 118+99; 118/1776; 118/1789; 99/1789 | 217; 6.64% organic-category growth; contributions 6.60 pp and 5.53 pp |
| C35 | Earnings variance bridge, same pair, USD millions; H4 L79–89 | sum(193,9,-15); sum(187,-78,22,-20) | EBIT change 187; net-income change 111 |
| C36 | Interest timing, same pair, USD millions; H4 L171 | 201-82 | 119 accrued-interest contribution increase |
| C37 | September-to-December cash, USD millions and fraction; H4 L44 | 2459-6261; -3802/6261 | -3802; -60.73%; not the YoY cash delta |
| C38 | Capex signed growth and magnitude cross-check; same pair, ratio; H4 L175 reread | (-6)/(-36) evaluated as 6/36 using calculate, simultaneous sign inversion | 0.16666666666666666666666666666666666667 = 16.67%; signed pair remains -36/-42 and difference -6. Direct negative-denominator tool rejection retained in C17 |
| C39 | Validation differences; USD millions; CP-1 against H4 passages identified below | calculate sum(value,-value) separately for 2006,1789,1087,859,1061,912,752,636,710,600,25049,24880,2459,6261,4135,13,2,25,51,-64,0 | All 0; exact displayed-million tolerance 0; ID/definition export blocks remain |

#### Canonical comparator export gate

<!-- table-id: cp1b.model_comparator_register -->

`metric_id` and period IDs below are null because the supplied CP-1 handoff does not contain stable IDs. This is a blocked export manifest, not replacement IDs. The row order corresponds to the first comparator table; that table carries the exact figures and labels. Comparison basis is reported fiscal same-quarter YoY, not equal-duration acceptance. Perimeter changes are true because acquired businesses contribute; material restatement/definition changes are not evidenced in read H4 passages. Basis flag refers to accounting basis, not the separately disclosed unequal calendar-window limitation.

| metric_id | current_period_id | reference_period_id | comparison_basis | current_value | reference_value | absolute_change | percentage_change | calculation_status | restatement_flag | basis_change_flag | perimeter_change_flag | definition_change_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 2006 | 1789 | 217 | 12.13% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 771 | 747 | 24 | 3.21% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 1235 | 1042 | 193 | 18.52% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 211 | 220 | -9 | -4.09% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 50 | 35 | 15 | 42.86% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 1087 | 859 | 228 | 26.54% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 1061 | 912 | 149 | 16.34% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 974 | 787 | 187 | 23.76% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 378 | 300 | 78 | 26.00% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 162 | 205 | -43 | -20.98% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 37 | 11 | 26 | 236.36% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 752 | 636 | 116 | 18.24% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | -42 | -36 | -6 | 16.67% | Calculated by simultaneous sign inversion; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 710 | 600 | 110 | 18.33% | Proxy only; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 493 | 382 | 111 | 29.06% | Calculated; ID export blocked | false | false | true | false |
| Not supplied | Not supplied | Not supplied | YOY_SAME_QUARTER | 2459 | 4135 | -1676 | -40.53% | Closing instants; ID export blocked | false | false | true | false |

#### Financial and add-back validation

<!-- table-id: cp1b.model_validation_register -->

Numbers in this register are comparison readings only; CP-1 remains authoritative. Parenthetical explanations identify the metric without inventing a canonical metric_id. Period date descriptions in the explanation are not replacement period IDs. Numeric equality is distinct from export status. Tolerance 0 applies to displayed USD million values, not original-dollar precision.

| metric_id | period_id | cp1_value | cp1b_comparison_value | difference | tolerance | status | explanation | source_or_conflict_ref |
|---|---|---|---|---|---|---|---|---|
| Not supplied | Not supplied | 2006 | 2006 | 0 | 0 | WARN | Revenue, current Q1; numeric PASS, stable IDs absent | H4 L79; ID conflict |
| Not supplied | Not supplied | 1789 | 1789 | 0 | 0 | WARN | Revenue, prior Q1; numeric PASS | H4 L79; ID conflict |
| Not supplied | Not supplied | 1087 | 1087 | 0 | 0 | WARN | EBITDA, current Q1; numeric PASS | H4 L633; ID conflict |
| Not supplied | Not supplied | 859 | 859 | 0 | 0 | WARN | EBITDA, prior Q1; numeric PASS | H4 L633; ID conflict |
| Not supplied | Not supplied | 1061 | 1061 | 0 | 0 | WARN | EBITDA As Defined, current Q1; numeric PASS | H4 L638; ID conflict |
| Not supplied | Not supplied | 912 | 912 | 0 | 0 | WARN | EBITDA As Defined, prior Q1; numeric PASS | H4 L638; ID conflict |
| Not supplied | Not supplied | 752 | 752 | 0 | 0 | WARN | OCF, current Q1; numeric PASS | H4 L173; ID conflict |
| Not supplied | Not supplied | 636 | 636 | 0 | 0 | WARN | OCF, prior Q1; numeric PASS | H4 L173; ID conflict |
| Not supplied | Not supplied | Not supplied | Not supplied | Not calculable | 0 | BLOCK | Canonical/sustainable FCF, both quarters absent; not silently replaced by proxy | CP-1 definition gap |
| Not supplied | Not supplied | 710 | 710 | 0 | 0 | WARN | Current OCF-minus-capex proxy matches, not canonical FCF | H4 L173, L175; C23 |
| Not supplied | Not supplied | 600 | 600 | 0 | 0 | WARN | Prior proxy matches, not canonical FCF | Same |
| Not supplied | Not supplied | 25049 | 25049 | 0 | 0 | WARN | Carrying debt at 2024-12-28; numeric PASS | H4 L575; C32 |
| Not supplied | Not supplied | 24880 | 24880 | 0 | 0 | WARN | Carrying debt at 2024-09-30; numeric PASS; no prior-December debt supplied | H4 L575; C32 |
| Not supplied | Not supplied | 2459 | 2459 | 0 | 0 | WARN | Cash at 2024-12-28; numeric PASS | H4 L44, L192 |
| Not supplied | Not supplied | 6261 | 6261 | 0 | 0 | WARN | Cash at 2024-09-30; numeric PASS | H4 L44 |
| Not supplied | Not supplied | 4135 | 4135 | 0 | 0 | WARN | Cash at 2023-12-30; numeric PASS | H4 L192 |

<!-- table-id: cp1b.addback_validation_register -->

Every disclosed issuer-specific adjustment label is checked once per supplied quarter below. No generic aggregation replaces an issuer label. Because CP-1 supplies no addback_id/period_id register, exhaustive canonical-ID coverage cannot be certified and all rows are BLOCK for CP-MODEL despite numeric and label matches. Source prior Other, net is a displayed dash, explicitly zero only in bridge arithmetic. It is not missing.

| addback_id | period_id | cp1_value | cp1b_comparison_value | difference | tolerance | status | label_match | definition_change_flag | explanation | source_or_conflict_ref |
|---|---|---|---|---|---|---|---|---|---|---|
| Not supplied | Not supplied | 13 | 13 | 0 | 0 | BLOCK | true | false | Current: Acquisition transaction and integration-related expenses; exact label/value match; IDs missing | H4 L635, L639; HTML table 66 row 10 |
| Not supplied | Not supplied | 2 | 2 | 0 | 0 | BLOCK | true | false | Prior: Acquisition transaction and integration-related expenses; exact label/value match; IDs missing | Same |
| Not supplied | Not supplied | 25 | 25 | 0 | 0 | BLOCK | true | false | Current: Non-cash stock and deferred compensation expense; exact label/value match; IDs missing | H4 L636, L640; table 66 row 11 |
| Not supplied | Not supplied | 51 | 51 | 0 | 0 | BLOCK | true | false | Prior: Non-cash stock and deferred compensation expense; exact label/value match; IDs missing | Same |
| Not supplied | Not supplied | -64 | -64 | 0 | 0 | BLOCK | true | false | Current: Other, net; signed deduction retained; IDs missing | H4 L637, L641; table 66 row 12 |
| Not supplied | Not supplied | — | — | 0 | 0 | BLOCK | true | false | Prior: Other, net; dash retained, explicit numerical zero only for arithmetic; IDs missing | Same |

<!-- table-id: cp1b.model_readiness -->

| downstream_module | status | blocking_metric_ids | blocking_period_ids | conflict_refs | explanation |
|---|---|---|---|---|---|
| CP-MODEL | blocked | null — upstream stable IDs/complete FCF and KPI definitions absent | null — date contexts exist but stable period IDs absent | ID-register gap; FCF block; addback-ID blocks; unreconciled pro forma perimeter scope | Numeric readings agree; no alternative canonical value emitted. Cannot certify comparator IDs exist in CP-1, exhaustive issuer-ID coverage or complete definition inheritance. Acquisition impacts are identified, not fully pro forma reconciled. Obtain upstream registers before canonical publication |

<!-- table-id: cp1b.cp_model_snapshot_fields -->

| field_id | value | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|
| historical_performance | Fiscal-Q1 reported sales, operating earnings and EBITDA As Defined improved, but acquisition/FX/compensation effects complicate extrapolation and distribution-heavy financing reduced dated cash despite positive OCF. Historical trend is usable with unequal source windows and no leverage/runway inference. | READY | H4-text / H4-raw | L79–89, L173–195, L520–551, L625–664; c-1/c-5; HTML tables 10, 14, 51, 66, 69 | 2024-12-28 |

Snapshot READY certifies only this evidence-grounded narrative field, not CP-MODEL publication readiness.

#### Markdown-carried HTML Model, chart and JSON content

The following is reusable presentation content, not a replacement canonical Analysis envelope, workbook, or proof of acceptance. Exact values come from the comparator and cash bridge above. No external action, new deliverable or chart-rendering/visual check is claimed.

<article data-module="CP-1B" data-status="historical-only"><header>TDG fiscal Q1 historical comparison — USD millions</header><p>Revenue: 1789 → 2006. EBITDA As Defined: 912 → 1061. OCF: 636 → 752. Closing cash: 4135 → 2459.</p><p>Unequal actual calendar windows retained. Not native IFRS/equal-duration acceptance. Canonical model publication blocked pending upstream stable IDs and definition registers. Cash-after-capex is a proxy, not sustainable FCF.</p></article>

```json
{
  "run_id": "sol-remaining-tdg-earnings-20261105",
  "module_id": "CP-1B",
  "as_of": "2024-12-28",
  "currency": "USD",
  "quantity": "millions",
  "canonical_export_ready": false,
  "native_paired_period_acceptance": false,
  "comparison_scope": "separately labelled historical U.S. GAAP unequal-window comparison",
  "periods": [
    {"period_id": null, "context": "c-5", "start": "2023-10-01", "end": "2023-12-30", "issuer_label": "Thirteen Week Periods Ended"},
    {"period_id": null, "context": "c-1", "start": "2024-10-01", "end": "2024-12-28", "issuer_label": "Thirteen Week Periods Ended"}
  ],
  "source_id": "H4-text",
  "source_sha256": "38b4642199a5381aca22f1ff4f5973ecc3430dfb24d068bf8058e962db99db71",
  "chart_content": {
    "type": "paired_reported_values",
    "order": ["prior", "current"],
    "series": [
      {"label": "Revenue", "metric_id": null, "values": ["1789", "2006"], "locator": "L79"},
      {"label": "EBITDA As Defined", "metric_id": null, "values": ["912", "1061"], "locator": "L638"},
      {"label": "OCF", "metric_id": null, "values": ["636", "752"], "locator": "L173"},
      {"label": "OCF minus capex proxy", "metric_id": null, "values": ["600", "710"], "locator": "L173,L175; CP-1 proxy"},
      {"label": "Closing cash", "metric_id": null, "values": ["4135", "2459"], "locator": "L192"}
    ]
  },
  "current_cash_waterfall": {
    "opening_as_of": "2024-09-30",
    "closing_as_of": "2024-12-28",
    "opening": "6261",
    "ocf": "752",
    "investing": "-24",
    "financing": "-4516",
    "fx": "-14",
    "change": "-3802",
    "closing": "2459",
    "locator": "L173-L192"
  },
  "formula_rules": {
    "absolute_change": "sum(current, negative prior)",
    "percentage_change_fraction": "ratio(absolute_change, prior); for two negative operands invert both signs algebraically before ratio",
    "proxy": "sum(OCF, signed capex)",
    "margin_change_pp": "100 times sum(current ratio, negative prior ratio)",
    "missing": "null; never zero"
  },
  "signed_capex": {"prior": "-36", "current": "-42", "change": "-6", "percentage_change_fraction": "0.16666666666666666666666666666666666667", "calculation": "(-6)/(-36) equals ratio(6,36); both signs inverted", "direct_tool_rejection": "ZERO_OR_NEGATIVE_DENOMINATOR"},
  "restricted_cash_status": null,
  "sustainable_fcf": null,
  "matched_ltm_leverage": null,
  "restrictions": ["No date repair or daily rebase", "No annualized quarterly leverage", "No new canonical IDs or replacement values", "No covenant headroom or current runway certification", "Source dashes differ from missing values"]
}
```

## Gaps

T4.11 — cumulative gaps and limitations:

| Gap Description | Affected Metric/Section | Affected Period(s) | Downstream Impact | Severity | Recommended Action |
|---|---|---|---|---|---|
| Exact unequal calendar windows; later component IFRS-only/equal-duration | All comparative calculations | Both Q1 windows | Source-supported history allowed; native acceptance unavailable | High methodological | Retain dates/labels; use separately labelled Decimal comparison, not rebuilt engine |
| Separate upstream run_id and stable metric/period/addback IDs absent | Canonical validation/export | Entire increment | CP-MODEL blocked; exhaustive ID coverage cannot be certified | High | Obtain exact CP-1 registers and upstream run identifiers; do not infer IDs from labels |
| Complete CP-1 KPI/FCF/FFO/WC definition register absent | FCF, DCF, FFO, canonical WC, coverage export | Both Q1 | Missing values remain null; diagnostics cannot become new canonical metrics | High | Load existing definitions; no synonym/value replacement |
| No maintenance/growth capex split or sustainable cash-generation evidence | FCF, conversion | Both Q1 | 710/600 remains proxy only | High | CP-1D/CP-2 obtain recurring capex and cash-claim information |
| Acquisition pro formas not supplied; open measurement periods | Organic/constant-perimeter earnings | Current versus prior Q1 | Cannot isolate durable acquired/organic margin contribution | Medium/high | Use issuer bridge with attribution; obtain cohort/pro forma detail if material |
| Adjustment recurrence/achievability and cash status not proven | EBITDA As Defined bridge | Both Q1 | Arithmetic agreement is not creditor acceptance | High | CP-1D challenge each signed issuer label and its underlying components |
| No accepted budget/base case/guidance/agency or peer data | Comparative evaluation | Both Q1 | No forecast beat/miss or peer ranking | Medium | Obtain dated accepted benchmarks; CP-1C for peer scope |
| H1/H2/H3 not fully re-extended; complete matched LTM absent | Sequential/LTM/leverage | Other quarters/full year | No synthetic LTM or quarter-annual mixing | High | Validate existing canonical annual and quarterly inputs first |
| Unrestricted cash, location/accessibility and current borrowing conditions absent | Liquidity/runway/net debt | 2024-12-28 and forward | Issuer liquidity 3308 not certified accessible; no runway conclusion | High | CP-2D obtain bank/restriction and borrowing-condition detail |
| Executed legal documents, covenant certificate, legal EBITDA and rating thresholds absent | Covenant/refinancing/rating headroom | Historical as-of and forward | No legal capacity, proximity or rating-trigger calculation | High | CP-4/CP-3C/CP-2H obtain dated evidence |
| Disposal detail and other-investing breakdown absent | Sale gain 19 / investing inflow 47 | Current Q1 | Do not equate total inflow to disposal proceeds or assume recurrence | Medium | Obtain transaction-level disclosure |
| Forward cash uses, interest/tax schedules and capital-allocation plan absent | Sustainable conversion and runway | Subsequent periods | Timing-supported quarter ratios not forecasts | High | CP-2D/CP-2G refresh dated cash needs and commitments |
| Later renewal/repayment evidence absent for July 2025 expiry | Securitization | Subsequent to 2024-12-28 | Historical expiry not actual default/renewal evidence | High monitoring | Obtain subsequent filings separately; preserve historical cut-off |
| Extracted text is not visual check; external authenticity/exhibit completeness unverified | Source assurance | H1–H4 | Bounded passage validation only | Medium | Inspect raw HTML if ambiguity arises; preserve CP-0 restrictions |
| Compound-unit parser limitation persists | EPS/par value/share metrics | All source periods | No USD-million conversion from USD/share; no EPS-derived cash metrics | Medium | Use original unit XML if those metrics enter scope |
| Provider/model/payment receipts not exposed | Live-test acceptance | Current run | Financial tool execution does not certify paid model identity or broader pathway reliability | Execution limitation | Orchestrator must attach actual receipt and acceptance evidence; not infer it from this report |

## Next module

**CP-1D — ready for bounded historical challenge, not a completed adjustment-quality opinion.** Consume ordinary EBITDA 1087/859, EBITDA As Defined 1061/912, total D&A 90/71, acquisition transaction and integration-related expenses 13/2, non-cash stock and deferred compensation expense 25/51, and Other, net -64/—. Retain the exact issuer labels and footnotes (H4 L628–664, tables 66/69), negative sign and zero-dash distinction. Consume OCF 752/636, cash paid interest 162/205, cash paid taxes 37/11, signed capex -42/-36 and proxy 710/600; the 188/111 broad asset/liability contribution includes accrued-interest timing and is not canonical trade WC. Challenge recurrence/achievability without treating reconciled adjustments as accepted add-backs. Preserve both date windows and the missing matched-LTM restriction.

**CP-2D — ready for observed historical liquidity facts only.** Consume opening cash 6261 at 2024-09-30; +752 OCF, -24 investing, -4516 financing, -14 FX; closing 2459 at 2024-12-28. Financing details are -4396 dividends/equivalents, -316 repurchases, +163 securitization, +35 options and -2 other. Prior December cash 4135 is a different reference instant. Consume issuer revolver availability 849 and issuer cash liquidity 3308 with accessibility/condition caveats; do not count fully drawn securitization as unused liquidity. Carry gross/carrying securitization 650/649, historical expiry 2025-07-11, reported no quarter term-loan payment and letter-of-credit usage 61. Carry December/September carrying debt 25049/24880 and mechanical net debt 22590/18619 only with basis restrictions. No future cash sufficiency, covenant headroom, renewal or default conclusion follows.

**CP-MODEL — blocked for canonical publication.** Obtain the existing CP-1 stable IDs, complete definition/calculation/addback registers, and upstream run identifiers; resolve or expressly gate missing FCF and pro forma/perimeter fields. Do not create aliases or replacement canonical figures. The single READY historical-performance snapshot and Markdown presentation content are reusable but do not override this block.

Recommended next analytical increment: CP-1D, then CP-2D, one at a time under the requested live-test pathway; broader pathways remain separate tests. Separate delivery may consume this intermediate handoff after evidence checks and orchestration receipts. No downstream execution, external action or final delivery is asserted here.