# CP-3D — Ares Capital Corporation

## Request

View: Ares Capital Corporation's December 31, 2024 evaluated debt disclosures support a bounded historical market-implied-risk analysis, not an executable market view. The July 2029 note's evaluated equivalent of 101.294118 per100 implies conditional maturity yields of 5.622366% in case A (equivalent treated as clean) and 6.316949% in case B (treated as dirty). Neither price-basis assumption wins on the evidence. Against a simple same-date Treasury comparison of 4.354685%, the respective spreads are 126.768113 and 196.226407 basis points. Those spreads compensate for a mixture of credit, liquidity, optionality, conventions and unexplained factors; they do not identify factual default probabilities. Positive published statutory coverage supports a funding-flexibility countercase, but cannot certify drawable liquidity or show that the market adequately compensates unsecured creditors.

Run `sol-remaining-arcc-market-20261105`; issuer_id ARCC; module CP-3D; method deploy-v-r14; public / relative_value; valuation and scenario settlement 2024-12-31; execution 2026-11-05. Owned object: market_implied_risk_map. Status: Completed with Limitations; committee status Requires More Work. This is a fresh live analytical handoff using admitted narrow historical CP-0/CP-1 and the current CP-4A, not a fresh full financial foundation, CP-2, ratings review, forecast, native full underwriting or full pathway. All six selected phases and ten register duties are addressed below, including explicitly unresolved outputs. Existing CP-OS live-loop context is preserved without rebuilding; orchestration is not analytical certification. Separate existing delivery rendering is outside this analytical handoff. Imported invocation/accepted-head gates, credential requirements, output prohibitions and navigation-only restrictions describe a prior version, not governing authority for this run.

## Sources

All seven pinned sources were read in full through the source tools: annual-selected pp1–2 (original annual pp94,95,290,291); supplement pp1–6 (especially L73–83 and L97–127); treasury pp1–2 (header and selected 12/31/2024 row); treasury-method pp1–2 (capture L818, L824, L831–833 and failed web CSV parse); selected-method pp1–2 (SKILL); method-steps p1 (REF A–F); offline-helper p1. Citations below distinguish source-page locators from original annual pages. No new visual inspection is claimed. Public issuer/legal/Treasury extracted evidence is used; no dealer entitlement, credentials, executable feed or new retrieval is claimed.

### Pinned source and upstream identities

| Object | Exact SHA256 | Coverage / role |
|---|---|---|
| annual-selected | c8de49a455d86045756e35a2096d11c92022076729f13dee364d0bafd4f0dc88 | Current selected annual text; original pp94,95,290,291 |
| supplement | bf82a65cae422d4814fa292ab3b9e5e5324f74d09643d6367ad6110055e6390c | Executed May 13, 2024 first supplemental indenture; July 2029 only |
| treasury | 6775840b76cd7fd41121f61d6f6c60184eca6b2ba49954ec7372c463cbeef34d | Official historical CSV, selected date matched to headers |
| treasury-method | 202c0857ef29f05cb2bff0725fea3f0fc00e3fc4051581f31c4058c41320f01c | Capture dated November 3, 2026; par CMT methodology, not a corporate quotation |
| selected-method | 7b1dcf5967f599a94a6b0c2138a51647a66fd73fc232c385bbec4b20286e02a4 | Six-phase method and full register schemas |
| method-steps | e1a3dc9584611edcf1e1dac66345aebba01e86b573c3ac7e7f848b7350683545 | REF A–F selected workflow |
| offline-helper | 5ff5531c5b5933e42532a300320f3bafc1e4b6b9c9ce20ef279df7089172ae79 | Fresh unchanged low-level PV/yield calls and independently checked Decimal roots; 110 checked numeric cells reported in record |
| Supplied historical CP-0 | f61415aa2b3c2d0d6fd79ad6853d49ec96e51d65e3130277e54f18e30b24626a | ARCC historical market-source admission, executed November 4, 2026; narrow source admission only |
| Supplied focused CP-1 | 68437034bceb3ebb0d04ad97e0746b255588aef701c8e7a6bcd8c38507b3ae1c | ARCC December 2024 debt extraction; no full BDC foundation |
| Current supplied CP-4A | fe5f4dc0f9bfb70ff9947c6ae98a19f7e0ecdede9e45b6be6b706b2142ced738 | Fresh November 5, 2026 capacity analysis for December 2024 / July 2029; transported as CP-4, run sol-remaining-arcc-capacity-20261105 |
| Original annual PDF in CP-0 lineage | 4483569e723b1a0c479d1ce45bcf64e11f6c82c98754bce1aa317641eb81e170 | Historical original 320-page file identity; not a claim of full current read |

The complete supplied raw predecessor handoffs remain retained as lineage, not overwritten by this synthesis. CP-4A's additional pinned identities are re-anchored exactly, without claiming those separate primary files were independently opened here: annual-selected `ec0dbd96488e2f6977a42bfc17085b6dd8410a9b39db7e7a0a3670c2d701f58b`; base-indenture `ef8ad4d8a3d5902746726697b6f6fa53058d7445b59d99157cbea6258bf2d459`; supplement `bf82a65cae422d4814fa292ab3b9e5e5324f74d09643d6367ad6110055e6390c`; selected-method `8a3b12f3f37359463434177759febac1ffcf0f8c484aa0508eb7119f7b6548b2`; method-runbook `1ca9d2d86d40772d6c4a1df3052af174ab10ee80a27460dfcee0de93a227e5bc`; method-steps `30cf03f343a9153aa85d6492e6bad519ab5d639395dae2b686de4b8276764e98`; checked-controls `5d03be730a3b856f071ae09c13a7771a41804bb5173d82cd4736b25f20fb9bbd`. Its own historical predecessors are CP-0 `8347534cab302ae92b4e097f7a7d08a0ea69945337a0cadaf575526578ea83e5`, focused CP-1 `ed934cea757dec38962ec99f87e86725e4d10e08a2b4865e0bee1ebd3ab4b240`, focused CP-4 `ff4a8bb2eef5f1a735628a5d1e99f1662eb8078858d0be80a9c199f4307569c9`. These are different source selections/lineages, not substitutes for this run's market-source hashes.

Evidence shorthand: A94/A95/A290 = annual-selected p1 original pages; A291 = annual-selected pp1–2 original p291; S = supplement with page/line; T = treasury p1 selected row; TM = treasury-method p1 L818,831–833; K = offline-helper p1; C4 = supplied current CP-4A, named table or calculation. All annual amounts below are USD millions; prices, accrued and PV cash flows are USD per100 nominal principal. Dates are historical unless explicitly marked subsequent.

## Findings

### Market conclusion

The strongest supported market signal is a **positive but convention-sensitive July 2029 yield premium to Treasury**, not a distress verdict or a security preference. A291's 861 USDm Level 2 fair value divided by 850 USDm principal produces an evaluated equivalent, not an observed executable clean price. Unknown basis alone moves the maturity yield by about 69.458294bp between A and B—far more than the roughly 1.5bp rounding sensitivity within each case. Under A the June 15, 2029 par-call leg has the lower yield; under B maturity does. That reversal makes it especially important not to silently declare a unique contractual yield-to-worst. Source fair values improved versus 2023 for the eight continuing series, but those point changes exclude coupons, reinvestment and trading costs and are not total returns. The low 86 equivalent for the 3.200% November 2031 series cannot establish relative credit weakness versus a 7.000% January 2027 series above par.

Evidence → mechanism → creditor consequence: A94's swaps align issuer funding with a primarily floating-rate loan portfolio; this is BDC matched funding, not industrial EBITDA leverage. A95's unsecured payment ranking gives equal payment status against non-subordinated unsecured debt, but collateral priority and subsidiary claims reduce direct asset access separately. C4's published 196.2% statutory coverage against 150% supports historical financing flexibility; a fall in portfolio values would reduce the coverage numerator, potentially tighten borrowing-base eligibility and funding access, and make refinancing maturing parent debt more dependent on asset repayments/sales or equity. Added secured borrowing could preserve cash while reducing unsecured access to pledged value. No numerical recovery or probability follows from those mechanisms.

The strongest supported countercase is the positive historical 46.2 percentage-point published coverage margin, the issuer's dated material-compliance assertions, conditional funding access, and subsequent January 2025 capital-market issuance (A95; C4 T4C.4, T4C.5). It would win against an immediate funding-closure thesis if dated certificates demonstrated adequate pro forma coverage, borrowing-base eligibility, equity tests, lender commitments and accessible cash after intended uses. Those conditions are not supplied, so this countercase reduces conviction in distress inference without proving value or implementation readiness. The initiating deterioration to monitor is weaker loan performance/marks; the first financial break would be lost asset backing or funding eligibility, followed by restricted liquidity and more expensive or constrained refinancing. Observable tests are coverage disclosures, facility certificates, portfolio marks, actual draws and shareholder-return execution—not an unsupported generic recession shock.

### T3E.1 — market evidence

| security_id | issuer | currency | coupon | maturity/call | seniority | source | timestamp | quote_type | freshness |
|---|---|---|---|---|---|---|---|---|---|
| ARCC_March2025 | Ares Capital Corporation | USD | 4.250% fixed | 2025-03-01; full call terms not reviewed | Parent senior unsecured; collateral/structural qualifications A95 | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2 fair value; derived per100 | Historical same-date snapshot; stale for current trading |
| ARCC_July2025 | Ares Capital Corporation | USD | 3.250% fixed | 2025-07-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_January2026 | Ares Capital Corporation | USD | 3.875% fixed | 2026-01-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_July2026 | Ares Capital Corporation | USD | 2.150% fixed | 2026-07-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_January2027 | Ares Capital Corporation | USD | 7.000% fixed; issuer effective 6.978% includes swap | 2027-01-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94 swap receive leg; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_June2027 | Ares Capital Corporation | USD | 2.875% fixed | 2027-06-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_June2028 | Ares Capital Corporation | USD | 2.875% fixed | 2028-06-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |
| ARCC_March2029 | Ares Capital Corporation | USD | 5.875% fixed; issuer effective 6.575% includes swap | 2029-03-01; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94 swap receive leg; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only; prior source dash |
| 04010LBG7 / US04010LBG77 | Ares Capital Corporation | USD | 5.950% fixed; issuer effective 6.040% includes swap | Maturity 2029-07-15; par call 2029-06-15; earlier contingent make-whole | Parent senior unsecured; A95 qualifications | A94; A291; S p1 L73–83,97–122; p2 L123–127 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only; prior source dash |
| ARCC_November2031 | Ares Capital Corporation | USD | 3.200% fixed | 2031-11-15; full call terms not reviewed | Parent senior unsecured; A95 qualifications | A94; A291 | 2024-12-31; clock not supplied | Evaluated Level 2; derived per100 | Historical only |

Other identifiers are issuer-series keys, not invented CUSIPs/ISINs. Whether the corporate market was open at the unknown valuation clock is not supplied. A290 says fair values discount remaining payments at applicable market rates considering ratings or quotes if available; it does not identify executable observations.

### T3E.2 — pricing conventions

| security_id | bid/mid/ask or evaluated price | yield | spread/OAS/DM | duration | benchmark | observation ID |
|---|---|---|---|---|---|---|
| 04010LBG7 case A | Evaluated equivalent 101.294118 assumed clean; dirty 104.021201 | Conditional maturity 5.622366%; par call 5.618164%; minimum 5.618164% | Simple maturity premium 126.768113bp; OAS/z-spread/DM not calculable: curve/option model absent | Modified 3.836448 years, maturity path | Analyst 3Y/5Y interpolated par CMT 4.354685% | A291_20241231_July2029_A; K case A |
| 04010LBG7 case B | Same evaluated equivalent assumed dirty; clean 98.567034 | Conditional maturity 6.316949%; par call 6.324223%; minimum 6.316949% | Simple maturity premium 196.226407bp; OAS/z-spread/DM not calculable | Modified 3.813151 years, maturity path | Same analyst par-CMT comparison | A291_20241231_July2029_B; K case B |
| Nine other parent series | Evaluated equivalents in curve controls; not bid/mid/ask | Not calculable on reviewed evidence: full terms/basis not locked | Not calculable: no supported comparable spread curve | Not calculable: full pricing conventions not reviewed | No instrument-specific benchmark lock | A291_20241231_other_parent_series |

Both July cases lock settlement/valuation 2024-12-31, USD, analyst 30E/360 and semiannual nominal annual yield. No FX conversion. The contract's twelve 30-day months does not independently select the exact end-of-month variant; dealer-convention confirmation is absent. Accrued begins July 15, 2024, after the actual first July 15, 2024 payment from May 13 issuance; January 2025 is a regular coupon, not an invented initial stub. Business-day delay without extra interest is contractual (S p1 L81); scenario times use scheduled unadjusted dates, not a fully confirmed settlement calendar. The minimum of maturity and one par-call leg is **not complete contractual YTW** and does not exhaust make-whole states. No vendor-reported yield or spread was supplied.

### T3E.3 — issuer curve

| security_id | maturity/call date | spread/yield | seniority | curve residual | explanation status |
|---|---|---|---|---|---|
| ARCC_March2025 | 2025-03-01 / calls not fully reviewed | Not calculable: reviewed terms/basis incomplete; equivalent 99.833333 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | Price observation only, not cheap/rich |
| ARCC_July2025 | 2025-07-15 / calls not fully reviewed | Not calculable; equivalent 99.040000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | Coupon/maturity differences retained |
| ARCC_January2026 | 2026-01-15 / calls not fully reviewed | Not calculable; equivalent 98.869565 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | No residual attributed |
| ARCC_July2026 | 2026-07-15 / calls not fully reviewed | Not calculable; equivalent 95.700000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | Low coupon is a possible price influence, not measured attribution |
| ARCC_January2027 | 2027-01-15 / calls not fully reviewed | Not calculable; equivalent 103.666667 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | 7.000% coupon, not issuer's swapped rate |
| ARCC_June2027 | 2027-06-15 / calls not fully reviewed | Not calculable; equivalent 95.000000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | No preference inferred |
| ARCC_June2028 | 2028-06-15 / calls not fully reviewed | Not calculable; equivalent 92.080000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | No preference inferred |
| ARCC_March2029 | 2029-03-01 / calls not fully reviewed | Not calculable; equivalent 101.000000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | Different coupon/terms; not a matched July comparator |
| 04010LBG7 | 2029-07-15 / 2029-06-15 par call | A/B maturity 5.622366% / 6.316949%; simple premium 126.768113 / 196.226407bp | Parent senior unsecured, A95 | Not calculable: single conditional yield point is not an issuer curve | No other-series spread extrapolation; S only governs July |
| ARCC_November2031 | 2031-11-15 / calls not fully reviewed | Not calculable; equivalent 86.000000 | Parent senior unsecured, A95 | Not calculable: no comparable yield curve | Longer low-coupon price cannot prove higher credit risk |

### T3E.4 — comparators

| comparator | alignment basis | spread/yield/price | period | difference | comparability limitation |
|---|---|---|---|---|---|
| U.S. Treasury 3Y / 5Y par CMT | USD, same date; ACT365 maturity tenor 1657/365 | 4.27% / 4.38%; analyst interpolation 4.354685% | 2024-12-31, TM indicative inputs near 3:30PM | July maturity yield less benchmark: A 126.768113bp; B 196.226407bp | Sovereign not corporate; par curve not zero curve; clocks not synchronized; no legal make-whole determination |
| Eight continuing ARCC series, own prior values | Same series, same principal; disclosed fair values | Prior equivalents and point changes in controls | 2023-12-31 versus 2024-12-31 | All eight equivalents higher; not total return | No same-convention historical yields, causal decomposition or transaction path |
| Corporate peers / index cohort | Required currency, seniority, tenor, date and options alignment | Not supplied: no peer/index quotes | Historical comparison date requested | Not calculable: cohort absent | No relative-value residual or rank supported |

T also reports 2Y 4.25%, 7Y 4.48%, 10Y 4.58%. The 3Y/5Y interpolation is an analyst comparison using the maturity horizon, not a bootstrap, OAS, z-spread, DM, or the supplement's future H.15 Treasury-rate procedure. TM describes indicative bid-side quotations, not transactions, and Treasury's monotone convex par-curve method since December 6, 2021. The failed web CSV parsing capture is preserved; the admitted direct CSV supplies the row, not an invented successful web parse.

### T3E.5 — loss break-even

| security_id | model | horizon | recovery | discount/benchmark | implied default/loss/break-even | formula ID | limitation |
|---|---|---|---|---|---|---|---|
| 04010LBG7 A | Constant annual loss-compensation proxy | ACT365F 1657/365 = 4.539726 years | Assumed 20% | 4.354685% simple par-CMT benchmark | Annual 1.584601%; horizon 6.994598% | L1 / L2; K A | Not factual or risk-neutral PD; includes non-credit premium |
| 04010LBG7 A | Same proxy | Same maturity horizon | Assumed 40% | Same benchmark | Annual 2.112802%; horizon 9.239242% | L1 / L2; K A | No default timing/recovery calibration |
| 04010LBG7 A | Same proxy | Same maturity horizon | Assumed 60% | Same benchmark | Annual 3.169203%; horizon 13.601708% | L1 / L2; K A | Higher assumed recovery raises implied break-even rate |
| 04010LBG7 B | Same proxy | Same maturity horizon | Assumed 20% | Same benchmark | Annual 2.452830%; horizon 10.661723% | L1 / L2; K B | Unknown price basis materially changes inference |
| 04010LBG7 B | Same proxy | Same maturity horizon | Assumed 40% | Same benchmark | Annual 3.270440%; horizon 14.011024% | L1 / L2; K B | No empirical forecast or hazard calibration |
| 04010LBG7 B | Same proxy | Same maturity horizon | Assumed 60% | Same benchmark | Annual 4.905660%; horizon 20.415558% | L1 / L2; K B | No causal assignment of premium to losses |

L1 = (maturity yield − benchmark)/(1 − recovery). L2 = 1 − (1 − L1)^(1657/365). These are constant annual loss/default break-even proxies compounded over an ACT365 horizon, not a discounted survival cash-flow model. Recovery is an analyst assumption, not CP-4C output. No recovery delay, default timing curve, coupon loss allocation or separate loss discounting is calibrated. The benchmark subtraction is the only rate adjustment; liquidity/option/convention/unexplained premium cannot be assigned causal shares. Do not read these figures as objectively market-implied probabilities.

### T3E.6 — liquidity and technicals

| security_id | bid-ask | trade frequency/volume | issue size | ownership/flow/supply evidence | direction | confidence |
|---|---|---|---|---|---|---|
| 04010LBG7 | Not supplied: no two-way quote | Not supplied: no TRACE/lot/depth history | 850 USDm nominal at 2024-12-31 | May 2024 issue documented; ownership/fund/ETF/CLO flows and dealer positioning not supplied | Liquidity effect indeterminate; evaluated is not executable | High on size/identity, low on liquidity inference |
| Other nine parent series | Not supplied | Not supplied | Each 500–1250 USDm nominal; controls show exact amounts | No sourced holder concentration, index changes or fund positioning | No liquidity or preference rank | Low on technical inference |
| ARCC subsequent supply / returns | Not supplied | Not supplied | January 2025 issuance 1000 USDm; February 2025 program up to 1000 USDm | A95: 5.800% March 8, 2032 notes; repurchase-program extension to February 15, 2026, discretionary authority | Later issuance supports subsequent access; repurchases could use resources only if executed | High on dated disclosure; no period-flow inference |

Issue size alone proves neither liquidity nor investor preference. Market clock, bid/ask, depth, dealer executable quotes, price dispersion, no-trade days and flows are absent. The January issuance and February authorization are subsequent events, never December cash or flows. Authorization is not an executed outflow or known unused balance.

### T3E.7 — fundamental reconciliation

| market implication | CP-2/2H/2R evidence | aligned/divergent | possible basis | unresolved question |
|---|---|---|---|---|
| Positive conditional July premium but no demonstrated distress price | CP-2/2H/2R not supplied; C4 T4C.4 gives historical 196.2% against 150% | not_comparable to missing CP-2; bounded consistency with positive coverage only | Published cushion may support access; premium also contains non-credit components | Do transaction-date coverage and accessible funding survive intended uses? |
| Unsecured claim premium cannot be isolated | No full asset quality, CP-4C recovery or rating trigger study; A95 and C4 T4C.6 show priority mechanisms | not_comparable | Parent equal payment ranking differs from effective collateral subordination and structural subsidiary subordination | What asset value is actually available to the note issuer after prior claims? |
| Evaluated point gains for continuing series | No fundamental-period bridge or CP-2G forecast supplied | not_comparable | Passage of time, rates, coupons, credit and conventions could affect price | Which observed rate/credit/technical changes explain the gains? |
| Conditional funding flexibility, not unused headroom certificate | C4 C6: 2219 USDm conditional ceiling difference; C7: 3348 USDm reported revolver availability within approximately 5100 USDm aggregate | not_comparable to a full liquidity forecast | 2219 is conditional expansion comparison, not an additional freely undrawn cash line; reported availability has tests | Obtain certificates, collateral map and cash-location schedule before any drawable-funding conclusion |

The supplied instruction's 2219 USDm nominal conditional facility figure must not be promoted into current unused headroom: C4 explicitly derives it as 6732 minus 4513, a conditional ceiling comparison. Neither that figure nor the revolver subamount is additive to aggregate availability. The statutory 46.2pp margin is a rounded-display ratio subtraction, not dollars. C4 also distinguishes the notes' Act incurrence framework from the separate facility maintenance ratio and the duration-qualified default provisions; no actual breach is established. No missing CP-2/2H data, ratings, industrial EBITDA test, TDG or Ford evidence is fabricated or merged. Non-debt float/deposit/deferred-revenue/supplier-finance trend evidence is not supplied; payables are not a substitute.

### T3E.8 — sensitivities

| scenario | driver | spread/yield/price assumption | calculated move | convexity/call limitation |
|---|---|---|---|---|
| A −100bp / +100bp | Parallel all-in yield shock | Maturity yield 5.622366% shifted by −/+1pp; same maturity flows and accrued | Equivalent 105.380519 / 97.395770; +4.086401 / −3.898348 points | Not spread-only forecast; endogenous call changes excluded |
| B −100bp / +100bp | Parallel all-in yield shock | Maturity yield 6.316949% shifted by −/+1pp; same flows | Equivalent 105.248851 / 97.520675; +3.954733 / −3.773442 points | Same conditional path, not full callable convexity |
| A source rounding | Rounded fair value | 861 ±0.5 USDm; equivalent ±0.0588235294 per100 | Maturity yield range 5.607631%–5.637111% | Rounding interval only, not confidence interval or bid/ask |
| B source rounding | Same rounded fair value | Same fair-value interval under dirty assumption | Maturity yield range 6.301725%–6.332184% | Separate from unknown basis and market error |
| Unknown clean/dirty basis | Change interpretation, not source value | A versus B; accrued 1309/480 per100 | Maturity yield difference about 69.458294bp | Neither case favored; not an observed trading range |
| Recovery 20% / 40% / 60% | Loss-proxy denominator | Keep each case's maturity spread fixed | Six annual/horizon results in loss controls | Not recovery underwriting; no calibrated hazard or discount model |

### T3E.9 — monitoring

| observable | threshold | cadence/event | downstream module | evidence source |
|---|---|---|---|---|
| Clean/dirty convention and executable quotation | Any confirmed basis or two-way lot changes admission; no unsupported price target | Before any implementation; new quote date | CP-3A / CP-3B | Obtain dealer/vendor convention, timestamp, bid/ask and executable size; A291 current limitation |
| Act asset coverage | 150% reported after-borrowing minimum; historical 196.2%; deterioration consumes cushion | Each disclosure and proposed borrowing/use | CP-4 / CP-3C / CP-2D | C4 T4C.4; obtain unrounded certificate and relief bridge |
| Facility access / asset eligibility | Actual tested maintenance ratio, equity and borrowing base; exact headroom not supplied | Each draw, material asset mark and certificate | CP-2D / CP-3C | C4 T4C.3–5; obtain operative facility and certificates |
| Portfolio credit/valuation deterioration | First adverse marks, non-accrual changes or collateral eligibility loss; no fabricated numerical trigger | Each portfolio report or material credit event | CP-2 / CP-2A / CP-3A | Full BDC asset-quality sources required; C4 nearest pressure point |
| Actual debt uses / repurchases / encumbrance | Executed use, not January supply or February authority alone | Transaction announcement and execution | CP-4 / CP-3C / CP-6 | A95; C4 T4C.6–7 |
| Call / legal-control events | Redemption notice or applicable consent, defeasance or combined control/rating event | Event-driven | CP-4 / CP-3A | S pp1–3 L97–150,157–175,217–288; C4 legal discussion |
| Corporate peer and issuer curve evidence | Only compare after currency, terms, basis, tenor and date alignment | New comparable evidence | CP-3A | Obtain reviewed other-note terms and aligned cohort quotes |

## Calculations

All four control tables round numeric cells to six decimal places without percent signs or thousands separators. Yield and loss cells are fractions; Simple_spread_bps is in basis points. Change_percent is percentage change, not a fraction. Em dashes preserve source-missing prior observations; they do not mean zero.

### Evaluated curve controls

| Series | Principal_USDm | Carrying_USDm | Fair_USDm | Equivalent_per100 | Prior_equivalent_per100 | Change_points |
|---|---|---|---|---|---|---|
| March2025 | 600.000000 | 600.000000 | 599.000000 | 99.833333 | 97.833333 | 2.000000 |
| July2025 | 1250.000000 | 1252.000000 | 1238.000000 | 99.040000 | 95.840000 | 3.200000 |
| January2026 | 1150.000000 | 1148.000000 | 1137.000000 | 98.869565 | 96.260870 | 2.608696 |
| July2026 | 1000.000000 | 996.000000 | 957.000000 | 95.700000 | 91.300000 | 4.400000 |
| January2027 | 900.000000 | 891.000000 | 933.000000 | 103.666667 | 103.000000 | 0.666667 |
| June2027 | 500.000000 | 497.000000 | 475.000000 | 95.000000 | 91.600000 | 3.400000 |
| June2028 | 1250.000000 | 1248.000000 | 1151.000000 | 92.080000 | 88.720000 | 3.360000 |
| March2029 | 1000.000000 | 985.000000 | 1010.000000 | 101.000000 | — | — |
| July2029 | 850.000000 | 835.000000 | 861.000000 | 101.294118 | — | — |
| November2031 | 700.000000 | 692.000000 | 602.000000 | 86.000000 | 83.714286 | 2.285714 |

March2029 and July2029 prior equivalents and changes are Not calculable: A291 has source dashes and no prior outstanding principal; division by zero is not performed. Formula E1 = fair value / nominal principal ×100, with each year's USDm units cancelling. E2 = current equivalent minus prior equivalent, not total return. Carrying amounts include costs/discount/premium and specified hedge adjustments (A291 footnotes 3–4); they are not the E1 denominator. The ten parent series total 9200 nominal, 9144 carrying and 8963 estimated fair USDm, whereas the consolidated debt group is 13789 nominal, 13727 carrying and 13552 fair USDm (A291). Facilities and consolidated securitizations are outside the ten-series subset, not omitted claims from a full capital structure.

### Conditional pricing controls

| Case | Equivalent | Dirty | Clean | Accrued | Maturity_yield_fraction | Par_call_yield_fraction | Minimum_two_legs_fraction | Simple_spread_bps | Modified_duration | DV01 |
|---|---|---|---|---|---|---|---|---|---|---|
| A_assume_equivalent_clean | 101.294118 | 104.021201 | 101.294118 | 2.727083 | 0.056224 | 0.056182 | 0.056182 | 126.768113 | 3.836448 | 0.039907 |
| B_assume_equivalent_dirty | 101.294118 | 101.294118 | 98.567034 | 2.727083 | 0.063169 | 0.063242 | 0.063169 | 196.226407 | 3.813151 | 0.038625 |

Exact scenario inputs from S p1 L79–83 and K: equivalent = 1722/17; coupon = 119/40 per half-year; analyst 30E/360 accrued days July 15–December 31 =165, so accrued = 5.95×165/360 = 1309/480 per100. A dirty = 848813/8160; B clean = 804307/8160. Maturity horizon for benchmark/loss compounding is ACT365F 1657/365, distinct from the 30E/360 PV maturity time 109/24. Benchmark B1 = 0.0427 + [(1657/365−3)/(5−3)]×(0.0438−0.0427) = 79473/1825000 = 0.043546849315068493150684931506849315068. No premature rounding is used in formulas; the controls are display rounding.

### Dated scenario cash-flow schedule

| Scheduled date | Maturity-path time in years, exact 30E/360 | Maturity-path amount per100, exact | Par-call-path time in years, exact | Par-call-path amount per100, exact |
|---|---|---|---|---|
| 2025-01-15 | 1/24 | 119/40 | 1/24 | 119/40 |
| 2025-07-15 | 13/24 | 119/40 | 13/24 | 119/40 |
| 2026-01-15 | 25/24 | 119/40 | 25/24 | 119/40 |
| 2026-07-15 | 37/24 | 119/40 | 37/24 | 119/40 |
| 2027-01-15 | 49/24 | 119/40 | 49/24 | 119/40 |
| 2027-07-15 | 61/24 | 119/40 | 61/24 | 119/40 |
| 2028-01-15 | 73/24 | 119/40 | 73/24 | 119/40 |
| 2028-07-15 | 85/24 | 119/40 | 85/24 | 119/40 |
| 2029-01-15 | 97/24 | 119/40 | 97/24 | 119/40 |
| 2029-06-15 | Not applicable: no maturity-path payment | Not applicable: no payment | 107/24 | 4919/48 |
| 2029-07-15 | 109/24 | 4119/40 | Not applicable: redeemed in call scenario | Not applicable: redeemed in call scenario |

The call payment is par plus 5.95×150/360 = 100+119/48 =4919/48, not par plus a full July coupon. Before June 15, 2029, S p1 L101–107 requires max[100, PV of remaining scheduled payments assuming par-call maturity at contractual Treasury Rate+30bp minus redemption-date accrued] then adds accrued in either case; the redemption price has contractual rounding. S pp1–2 L115–127 defines the future H.15/alternative Treasury selection and observation procedure. These contingent future states are not exhausted by the two legs above and are not calculated using today's analyst benchmark. No invented fixed par-call schedule is assigned before that date.

PV1: dirty price = Σ CF_i/(1+y/2)^(2t_i). Solve separately for maturity and the explicit par-call path using the same dirty purchase price. D1: modified duration = −(∂dirty/∂y)/dirty on the maturity path. V1: DV01 = dirty × modified duration /10000, in USD per100 per basis point. The K record retains unchanged low-level yield/PV results, fresh calls and independent 50-digit Decimal PV/derivative checks; this handoff consumes that kernel without claiming model-side script execution or a rebuilt dated engine. The high-level helper intentionally rejects dated/nonzero-accrued or unsupported convention inputs; its rejection is not overridden into a general dated-support claim.

Full retained results before display rounding: A maturity 0.05622366058445431, call 0.05618164480320495, spread 126.76811269385823bp, modified duration 3.8364477866891664; B maturity 0.06316949000391184, call 0.06324222628574597, spread 196.22640688843347bp, modified duration 3.8131508622712516. A's minimum is call; B's minimum is maturity. Spread S1 always uses maturity yield minus B1, times10000, not the minimum leg. Neither result is OAS or full YTW.

### Loss break-even controls

| Case_recovery | Recovery_fraction | Annual_loss_fraction | Horizon_loss_fraction |
|---|---|---|---|
| A_assume_equivalent_clean_1/5 | 0.200000 | 0.015846 | 0.069946 |
| A_assume_equivalent_clean_2/5 | 0.400000 | 0.021128 | 0.092392 |
| A_assume_equivalent_clean_3/5 | 0.600000 | 0.031692 | 0.136017 |
| B_assume_equivalent_dirty_1/5 | 0.200000 | 0.024528 | 0.106617 |
| B_assume_equivalent_dirty_2/5 | 0.400000 | 0.032704 | 0.140110 |
| B_assume_equivalent_dirty_3/5 | 0.600000 | 0.049057 | 0.204156 |

L1/L2 retain K's full results: A annual 0.015846014086732276 / 0.021128018782309705 / 0.03169202817346455 and horizon 0.06994598134478347 / 0.09239241615504412 / 0.13601708392562928; B annual 0.024528300861054182 / 0.03270440114807225 / 0.049056601722108364 and horizon 0.10661722524863171 / 0.14011023884426865 / 0.20415557789532812, in recovery order 20/40/60. These are conditional compensation proxies, not factual probabilities.

### Yield shock controls

| Case_shock_bps | Equivalent_price | Change_points | Change_percent |
|---|---|---|---|
| A_assume_equivalent_clean_-100 | 105.380519 | 4.086401 | 4.034194 |
| A_assume_equivalent_clean_100 | 97.395770 | -3.898348 | -3.848543 |
| B_assume_equivalent_dirty_-100 | 105.248851 | 3.954733 | 3.904208 |
| B_assume_equivalent_dirty_100 | 97.520675 | -3.773442 | -3.725234 |

K shock prices retain full values: A 105.38051888787732 / 97.39576979148895; B 105.24885054974374 / 97.52067517237987, in −100/+100 order. Q1 reprices identical maturity cash flows at y±0.01; A equivalent equals shocked dirty less fixed accrued, B equivalent equals shocked dirty. Q2 subtracts exact base equivalent 1722/17; Q3 divides point change by base equivalent and multiplies100 for percent. These are parallel all-in yield shocks, not spread-only predictions; optional redemption may change realized upside and convexity.

Source rounding: K A yield bounds are 0.056076310912778746–0.05637111261316614 and B 0.0630172503712057–0.06332183847001426. They come from source fair value 860.5–861.5 USDm with principal held at850, not quote precision or a market confidence band. Unknown basis effects remain separate.

### Supporting Decimal calculation trace

| Calculation | Operands / source references | Period / currency / quantity | Tool result / role |
|---|---|---|---|
| Parent-note principal sum | 600+1250+1150+1000+900+500+1250+1000+850+700; A94/A291 | 2024-12-31; USDm nominal | calculate sum =9200; not total group debt |
| Parent-note carrying sum | 600+1252+1148+996+891+497+1248+985+835+692; A291 | Same date; USDm carrying | calculate sum =9144 |
| Parent-note fair sum | 599+1238+1137+957+933+475+1151+1010+861+602; A291 | Same date; USDm estimated fair | calculate sum =8963 |
| Accrued | 1309/480; S L81–83; K explicit scenario | Settlement 2024-12-31; USD per100 | calculate ratio =2.7270833333333333333333333333333333333 |
| A dirty / B clean | 848813/8160 and 804307/8160; K | Same settlement; USD per100 | calculate ratios =104.02120098039215686274509803921568627 / 98.567034313725490196078431372549019608 |
| Base equivalent | 1722/17; A291 861/850×100; K | Same date; USD per100 | calculate ratio =101.29411764705882352941176470588235294 |
| Horizon / benchmark | 1657/365; 79473/1825000; T/K | Same valuation date to 2029-07-15; years / yield fraction | calculate ratios =4.5397260273972602739726027397260273973 / 0.043546849315068493150684931506849315068 |
| January2026 current/prior/change | 2274/23; 2214/23; 60/23; A291/K | 2024/2023; USD per100 / points | calculate ratios =98.869565217391304347826086956521739130 / 96.260869565217391304347826086956521739 / 2.6086956521739130434782608695652173913 |
| A DV01 | 10000/3.8364477866891664 =2606.5778960150910014453942027041269058; A dirty divided by that; K | 2024-12-31 conditional maturity path; USD per100 per bp | calculate ratios =0.039907190626997443621117647058823529410; algebraically dirty×duration/10000 |
| B DV01 | 10000/3.8131508622712516 =2622.5031112573488929708299857514091749; B dirty divided by that; K | Same quantity / path | calculate ratios =0.038624975204888795618823529411764705882 |
| Shock point changes | Each full K shock equivalent minus 1722/17 | Same date, conditional path; per100 points | calculate sums =4.08640124081849647058823529411764706; −3.89834785556987352941176470588235294; 3.95473290268491647058823529411764706; −3.77344247467895352941176470588235294 |
| Shock percentage changes | Above deltas /1.0129411764705882352941176470588235294 (base equivalent/100) | Same date/path; percentage change | calculate ratios =4.0341940240368432055749128919860627190; −3.8485431791340214866434378629500580709; 3.9042078597934715447154471544715447167; −3.7252335696598263646922183507549361197 |
| Source rounding equivalent interval | 0.5/8.5; A291/K | Same date; ±USDm transformed to per100 | calculate ratio =0.058823529411764705882352941176470588235 |
| Published coverage margin | 196.2−150; C4 C4 | 2024-12-31; percentage points | calculate sum =46.2; rounded display, not dollars |
| Conditional facility ceiling comparison | 6732−4513; C4 C6 | 2024-12-31; USDm commitment ceilings | calculate sum =2219; conditional difference, not certified unused drawability |

Supporting sums/ratios used the existing Decimal-38 half-even calculate kernel. Low-level roots, derivatives, nonlinear shocks and loss compounding are consumed unchanged from K, not recomputed by a claimed model-side script. Numerical execution does not certify source convention, liquidity or legal capacity.

## Gaps

### T3E.10 — gaps

| missing/stale/conflicting item | affected calculation/security | impact | required evidence |
|---|---|---|---|
| Evaluated clean/dirty basis, exact clock and settlement conventions not supplied | July A/B yields, accrued interpretation and spread | Both cases remain; neither is an observed executable price | Issuer valuation convention and dated dealer/vendor basis confirmation |
| Other nine series' full operative terms / identifiers not reviewed | Comparable issuer yield curve, duration, residuals, full YTW | Price-only observations; no unsupported yield/spread curve or rich/cheap rank | Operative series supplements, amendments, conventions and verified identifiers |
| No corporate peer/index cohort, bid/ask, depth or trades | Relative-value residual and liquidity/technicals | Not calculable: matched comparator/liquidity evidence absent | Same-date aligned cohort quotes, TRACE/dealer depth and executable lots |
| No ownership/flows/positioning evidence | All series' technical explanations | Cannot assign flow or liquidity premium shares | Dated holder, fund, ETF/CLO, index and dealer-positioning evidence |
| Incomplete contingent make-whole state analysis | July contractual worst outcomes / OAS | Two-leg minimum only; no full contractual YTW or OAS | Future-state rate/option model and complete legal/calendar implementation |
| Rounded issuer fair values and source prior dashes | Curve precision and historical change | ±0.5 USDm sensitivity separate from basis uncertainty; no prior change for new 2024 series | Unrounded valuations, basis and observation history; preserve prior dashes |
| CP-2/2H/2R, full BDC asset-quality, forecast and recovery work absent | Fundamental reconciliation, probability interpretation, selection | No fabricated underwriting/ratings/forecast or recovery calibration | Full BDC foundation, dated ratings evidence, asset quality/funding bridge and CP-4C if required |
| No unrounded legal coverage / facility / cash-access certificate | Statutory headroom and financing access | 46.2pp is not dollars; 2219 is conditional ceiling difference, not current unused headroom | C4 G1/G2 certificates, transaction uses, collateral/entity/cash maps |
| Subsequent-event timing and swap-date conflict | January 2025 issuance narrative only | A95 says forward swap effective January 8, 2032; C4 says January 8, 2026. Unresolved, excluded from all pricing/coverage inputs | Operative March 2032 issuance/swap documents; retain both source statements rather than silently choose |
| Non-debt funding float trend not supplied | Full BDC funding/perimeter interpretation | No substitute from payables, no assumed zero | Deposit/deferred-revenue/supplier-finance history and legal classification |
| Annual filed later than valuation date; current market/mandate absent | Historical inference and implementation | Not an information-availability backtest; not current investment advice | Point-in-time availability archive for a backtest; separately dated current market and mandate for action |

### Six-phase execution and QA

| Phase / check | Actual coverage and outcome | Limitation / disposition |
|---|---|---|
| 1 / REF A evidence gate | All selected annual/terms/Treasury pages read; T3E.1 maps ten parent series and verified July identifier | Evaluated source only; no market-open clock, executable feed or new visual checks |
| 2 / REF B convention lock | T3E.2 and exact schedule lock dated A/B scenarios, coupon, accrued, yield, benchmark and call legs | Analyst 30E/360, dealer confirmation missing; high-level dated interface refusal preserved |
| 3 / REF C engine | T3E.3–5 and controls report evaluated curve, bounded comparator and six loss cases; K unchanged PV results consumed | No other-note yield curve, matched corporate cohort, OAS or calibrated PD |
| 4 / REF D technicals and reconciliation | T3E.6–8 distinguish size from liquidity, subsequent supply from period flows, and absent CP-2 from C4 evidence | No causal technical attribution; not_comparable to missing fundamentals |
| 5 / REF E credit handoff | Priced/unpriced map, strongest countercase, causal downside and T3E.9 monitoring carried to CP-3A | No recommendation, terminal rank or size authority |
| 6 / REF F QA and artifacts | Ten full-schema registers, four exact control tables, source dates/units/identity/convention checks, supporting calculate calls and handoff submission | No unavailable confidence/completeness/validation script execution claim; acceptance checks are not full underwriting certification |
| Identity / term conflict QA | Noteholder coupons distinguished from swapped effective rates: July 5.950 vs6.040; January2027 7.000 vs6.978; March2029 5.875 vs6.575 | Different economic roles, not rates to average; later swap-date conflict retained separately |
| Units / perimeter QA | USDm nominal/carrying/fair distinct; per100 equivalents calculated from fair/nominal; full group not equated to parent-note subset | Matched-funded BDC debt not industrial leverage; no inferred legal dollar capacity |
| Evidence quality / analytical confidence | High for extracted historical identities/amounts; conditional mathematics traceable to K; lower for credit attribution and implementation | Qualitative confidence only; no invented numerical confidence score or script validation |

This is actual bounded analytical execution of the selected function with disclosed gaps, not a native accepted-head certification, executable market, full underwriting or full pathway. Source and tool coverage are explicit. Source text was treated as evidence, including prior-version method machinery, rather than authority overriding current instructions.

## Next module

The next full **CP-3A security-selection module** should consume this current output, with both A and B preserved and no inference that CP-3D has already selected a security. Priced conditionally: a positive July maturity-yield premium to an analyst Treasury comparator, sensitivity to all-in yields, a two-leg call/maturity minimum and recovery-dependent loss-compensation proxies. Not isolated or shown adequately priced: actual credit loss, effective collateral priority, subsidiary asset access, legal/funding flexibility, future make-whole states, liquidity/flow premia and valuation-basis uncertainty. The most material curve/peer residual remains unmeasurable, not an opportunity signal.

CP-3A must obtain other-series operative terms and comparable observed prices before cross-security preference; obtain asset/collateral/entity reach and certified funding inputs before treating structural risk as compensated; and obtain aligned corporate cohorts before relative valuation. CP-3B would separately need executable liquidity and mandate constraints; CP-3C/CP-2D would need actual refinancing and funding bridges. CP-6 can challenge the strongest favorable inference by testing whether published coverage and conditional access survive intended uses. These downstream modules are not claimed to have run here. Preserve full raw handoff, exact hashes, historical dates, conditional cases, priced/unpriced risks and unresolved conflicts in the separate existing delivery renderer. **No trade, rank, recommendation or sizing authority is conveyed.**