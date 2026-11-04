# CP-3D — ARCC historical evaluated-market and convention map

## Request

Diagnose actual December31 2024 debt valuation evidence and explicitly
conditional pricing implications for Ares Capital Corporation. **Completed with
Limitations for this historical evaluated-price/convention function.** Current
host model with preceding context, execution2026-11-04; no agents, provider/native
accepted heads or current research claim. No security ranking, trade or size.

The primary conclusion is a convention risk: the July2029 note's disclosed value
can support substantially different calculated yields depending on an unresolved
clean/dirty basis. That uncertainty is larger than the source's monetary rounding
effect. The low-coupon2031 note's discount cannot independently establish greater
credit distress; coupon, maturity and evaluation methodology matter. Real
evaluated levels, contractual cash flows and a same-date Treasury curve permit
positive calculation and diagnosis, but no executable spread or factual default
probability. Resolve basis/time and liquidity before using these results to
select securities. The strongest countercase to a distress reading is that much
of the price dispersion can reflect contractual coupon and rate exposure.

## Sources

| Input actually consumed | Exact pin / source scope |
|---|---|
| CP-0.md | `f61415aa2b3c2d0d6fd79ad6853d49ec96e51d65e3130277e54f18e30b24626a`; source/evidence readiness and limits. |
| CP-1-market-inputs.md | `68437034bceb3ebb0d04ad97e0746b255588aef701c8e7a6bcd8c38507b3ae1c`; ten parent unsecured series and distinct principal/carrying/fair-value/coupon roles. |
| ARCC FY2024 original PDF | SHA `4483569e723b1a0c479d1ce45bcf64e11f6c82c98754bce1aa317641eb81e170`; retained in ../arcc-2024-001/sources. P94 terms/swaps,95 priority,290 methodology,291 values/Level2. Original p291 viewed this run. [Official issuer PDF](https://www.arcc.ares.com/media/document/2d13e49e-cace-422e-9c89-57a907b12dab/assets/Q4_2024_10K.pdf?disposition=inline). |
| Executed July2029 supplement | ../arcc-2024-001/sources/supplement-lines.txt L73–83 and97–127; exact retained public captures, original raw HTML unavailable. Identity, coupon dates, day-count description, par-call/make-whole. |
| Official Treasury source | sources/treasury-2024.csv SHA `6775840b76cd7fd41121f61d6f6c60184eca6b2ba49954ec7372c463cbeef34d`; Date12/31/2024, headers1Mo–30Yr, 250 rows. [Official historical table](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2024); exact public capture and CSV retrieval metadata retained. |
| Prior actual CP-4A coverage answer | ../arcc-2024-001/CP-4A-attempt-1.md SHA `ca53528bf1f6d9758a7d9194e76af181eb884e237388fe46e839e601606168b6`; bounded published statutory coverage, not a full CP-2 fundamental view. |

Selected broader CP-3D source/convention/curve/technical questions and later
numeric/provenance safeguards are pinned in the method archive/verification.
The later floating-loan simple-discount slice does not replace fixed-bond analysis.
Current project transport governs; no native accepted lineage is fabricated.

## Findings

### T3E.1 — instrument, source and freshness gate

All ten rows below are distinct **Ares Capital Corporation parent senior unsecured
USD series**, matched by issuer/coupon/maturity tuple. Only July2029 has the full
selected executed supplement: CUSIP04010LBG7, ISIN US04010LBG77, 5.950%, Jul15 2029.
Issuer swap economics do not change noteholder cash flows. Annual p95 describes
effective subordination to secured collateral and structural subordination to
subsidiary/financing-vehicle claims; identical covenant/call terms across all
series are not established. No CLO/facility observation is mixed into this group.

Source class for **every issuer value**: estimated/evaluated, Level2, as of
**2024-12-31**, exact time unknown, based on applicable market rates or quotes if
available. These are rounded aggregate issuer financial disclosures, not observed
per100 clean bid/mid/offer prices or last trades. No market-open/executable status
is established. The Treasury row is same-date indicative bid-side-derived par
rates, approximately3:30pm source methodology, not an executable corporate quote.

Freshness: **historical/outdated now**, deliberately usable for the user's
functional proof. ARCC's audit is dated February5 2025; this is not a December31
information-availability backtest. No “maintained current” loan-workbook rule is
imported into this historical fixed-bond case.

### T3E.2 — actual evaluated observations and calculated equivalents

Absolute amounts are USD **millions**. Per100 equivalents = estimated aggregate
fair value / principal outstanding ×100, **Calculated**, unknown clean/dirty
basis. This is a transformation of source facts, not a new quote. The corresponding
carrying values remain in CP-1 and cannot be used as the price denominator.

| Series maturity | Fixed coupon | Principal | Estimated FV2024 | Evaluated equivalent/100 | Equivalent2023, same principal | Change points, not total return |
|---|---:|---:|---:|---:|---:|---:|
| Mar1 2025 | 4.250% | 600 | 599 | 99.833 | 97.833 | +2.000 |
| Jul15 2025 | 3.250% | 1,250 | 1,238 | 99.040 | 95.840 | +3.200 |
| Jan15 2026 | 3.875% | 1,150 | 1,137 | 98.870 | 96.261 | +2.609 |
| Jul15 2026 | 2.150% | 1,000 | 957 | 95.700 | 91.300 | +4.400 |
| Jan15 2027 | 7.000% | 900 | 933 | 103.667 | 103.000 | +0.667 |
| Jun15 2027 | 2.875% | 500 | 475 | 95.000 | 91.600 | +3.400 |
| Jun15 2028 | 2.875% | 1,250 | 1,151 | 92.080 | 88.720 | +3.360 |
| Mar1 2029 | 5.875% | 1,000 | 1,010 | 101.000 | — | — |
| Jul15 2029 | 5.950% | 850 | 861 | 101.294 | — | — |
| Nov15 2031 | 3.200% | 700 | 602 | 86.000 | 83.714 | +2.286 |

The March/July2029 prior source values are dashes and prior principal was0; a
zero prior price, percentage return or spread history is not invented. Overlapping
series' equivalent increases include time-to-maturity/rate/evaluation effects,
not just credit improvement. Coupons, reinvestment and actual transactions are
absent from those price changes; they are not realized total returns.

### T3E.3 — issuer curve and residual interpretation

| Actual issuer observation | Supported mechanism | Residual status |
|---|---|---|
| Jan2027 7.000% equivalent103.667 versus Jun2027 2.875% equivalent95.000 | Different coupons, maturity and possibly liquidity/calls can explain different prices at the same seniority | Raw8.667-point difference is not normalized RV or extra default compensation. No comparable yield residual without terms/basis. |
| Jul2029 5.950% equivalent101.294 versus Nov2031 3.200% equivalent86.000 | Lower coupon plus longer maturity increases discount/rate exposure at a common required yield | The14-point vicinity is not a source-backed distress gradient or spread curve. Exact source difference is15.294 points; do not use rounded narrative as another calculation. |
| Jul2029 conditional spread126.77bp or196.23bp depending on price basis | Same actual value, different accrual interpretation; basis uncertainty changes model residual | Material convention/evaluation explanation, **not** identified credit/liquidity premium. Full issuer spread curve is unproven. |

### T3E.4 — benchmark and pricing-convention lock

Official Dec31 Treasury par curve: 2Yr4.25%, 3Yr4.27%, 5Yr4.38%, 7Yr4.48%,
10Yr4.58%. For Jul15 2029, actual remaining time1657/365 =4.539726 years.
Analyst linear interpolation between3Yr and5Yr gives **4.354685%**. This is
same-date USD maturity context, not an exact duration hedge, bootstrapped spot
curve, OAS, Z-spread or loan DM. No independent corporate peer/index/rating
comparison has been supplied. Intraday issuer/Treasury synchronization is unknown.

Conditional pricing conventions, fixed **before** calculations:

- Valuation date Dec31 2024, contractual Jul15 2029 maturity; no assumed current
  trade/T+settlement date. Explicit analyst scenario **30E/360** accrual/time
  fractions with semiannual nominal discounting; not asserted exact dealer/legal
  end-of-month implementation of the source's12×30-day description.
- Fixed noteholder coupon **5.950%**; **6.040%** is the issuer's effective post-swap
  rate, excluded from note cash flows. Per100 regular half-year coupon2.975;
  assumed accrued from Jul15 to Dec31 = **2.727083**.
- Source equivalent **861/850×100 =101.294118**. CaseA assumes this is clean and
  prices dirty104.021201; caseB assumes it is dirty and prices101.294118. Neither
  is declared the source's actual quote convention. Reporting precision is ±0.5
  USDm sensitivity, equivalent ±0.058824 per100, not a quoted bid/ask.
- Maturity leg has ten remaining scheduled payments, including102.975 redemption
  cash at4.541667 selected-convention years. Known Jun15 2029 par-call leg pays
  prior coupons and final **102.479167**, including a partial5-month coupon.
  The future Treasury+30bp make-whole path is contingent; no fixed early par calls
  are invented. Business-day payment mechanics and actual dealer convention are
  not fully modeled.

| Conditional Jul2029 result | A: equivalent assumed clean | B: equivalent assumed dirty |
|---|---:|---:|
| Nominal semiannual maturity yield | 5.622366% | 6.316949% |
| Jun15 2029 par-call yield | 5.618164% | 6.324223% |
| Minimum of those two tested terminal legs only | 5.618164%, par-call leg | 6.316949%, maturity leg |
| Maturity yield less interpolated Treasury, simple bp | 126.77 | 196.23 |
| Modified duration, maturity-scenario years | 3.836448 | 3.813151 |
| Approximate yield interval from ±0.5 USDm FV rounding | 5.607631–5.637111% | 6.301725–6.332184% |

The price-basis difference is **69.46bp** in maturity yield and changes the lower
of the two tested legs. More displayed decimals cannot resolve it. No full
yield-to-worst, option-adjusted spread, dealer-calculated yield or tradeable
mispricing is established.

### T3E.5 — conditional loss break-even, not a factual default probability

Formula: annual simple expected-loss break-even p = simple yield residual /
(1−assumed recovery). Cumulative illustration =1−(1−p)^T over T=1657/365 years.
No independent probability calibration or default-timing/recovery valuation is
supplied. This approximation equates an annual residual to expected loss; it
does **not** solve a fully discounted coupon/default/recovery model. The residual
also includes liquidity, optionality, risk premium, curve/convention and evaluation
effects. The actual note price or Treasury source does not quote these probabilities.

| Analyst recovery assumption | A annual break-even | A cumulative illustration | B annual break-even | B cumulative illustration |
|---|---:|---:|---:|---:|
| 20% | 1.584601% | 6.994598% | 2.452830% | 10.661723% |
| 40% | 2.112802% | 9.239242% | 3.270440% | 14.011024% |
| 60% | 3.169203% | 13.601708% | 4.905660% | 20.415558% |

Higher recovery requires more defaults to absorb the same assumed annual spread
compensation; it is not a prediction that higher recovery causes defaults. No
recovery from another issuer, source asset coverage or par-call price is silently
substituted for these explicit assumptions.

### T3E.6 — actual liquidity/technical evidence and absent evidence

| Factor | Evidence / direction / confidence |
|---|---|
| Issue size | Jul2029 outstanding850 USDm; other source series500–1,250 USDm. Reported size only, **not** proof of exit liquidity, depth or no price impact. |
| Bid/ask, trades, volume, dealer depth | Insufficient Information. No assumed zero width, active trading or executable price. |
| Evaluation depth | Level2 estimated source values, market rates/quotes if available. Exact underlying broker/inputs unavailable. Medium confidence in disclosure identity; Low in tradable level. |
| Ownership, fund flows, ETF/CLO eligibility, positioning | Insufficient Information; no flow, ownership or technical squeeze is invented. |
| Supply | Source identifies March/July2029 issues during2024; this establishes supply existed, not placement demand, flow pressure or future spread direction. Later January2025 issuance stays subsequent, outside these December values. |

### T3E.7 — fundamental reconciliation and strongest countercase

Actual prior CP-4A reports **196.2%** published statutory asset coverage against
a150% after-borrowing minimum, **46.2 percentage points** of published ratio
cushion. This is an asset-value incurrence measure, not cash, complete compliance,
recovery or a market PD. Classification versus the conditional spread/default
model is **not_comparable**; a full matching CP-2/2G/2H fundamental/rating view
is absent in this market case. Positive statutory cushion and nonzero market
compensation can coexist without contradiction. No artificial rating divergence
or fundamental-to-market probability calibration is asserted.

Downside mechanism: deteriorating portfolio values/income can reduce coverage
and funding flexibility, while risk premiums/rates or poor liquidity depress note
value. The later consequence depends on actual cash/access and maturities;
this map does not quantify an issuer default path. The strongest countercase to
reading discounted low-coupon bonds as distress is coupon/rate/maturity mechanics
and the published positive coverage snapshot. It wins over a distress inference
until matched quotes and issuer-specific asset-quality/funding evidence support
one. It does not establish the correct current credit assessment.

### T3E.8 — conditional price sensitivity

Parallel shifts to the selected **all-in maturity yield**, holding supplied
cash flows/convention and valuation-date accrued constant. These are analyst
shocks, not observed moves or isolated credit-spread shocks. Source-equivalent
comparison basis follows each case; optionality/future calls remain outside.

| Case / assumed shock | Repriced equivalent/100 | Change points | Change versus input |
|---|---:|---:|---:|
| A clean assumption, −100bp | 105.380519 | +4.086401 | +4.034194% |
| A clean assumption, +100bp | 97.395770 | −3.898348 | −3.848543% |
| B dirty assumption, −100bp | 105.248851 | +3.954733 | +3.904208% |
| B dirty assumption, +100bp | 97.520675 | −3.773442 | −3.725234% |

The asymmetric price changes reflect the fixed-cash-flow PV shape, not an actual
option-adjusted convexity estimate. No FX shock is needed for this USD/USD
comparison; issuer asset-side currency exposures are not assessed here.

### T3E.9 — monitoring handoff

| Observable / threshold | Cadence / dependent action | Evidence basis / restriction |
|---|---|---|
| Clean/dirty, accrued, timestamp and exact quote convention resolved | Before any price-based selection or model refresh | Material69.46bp basis uncertainty exceeds rounding; request matched quote/valuation convention. No fresh trade level exists here. |
| Consistent-basis simple spread change≥25bp | Analyst watch on each future matched observation; CP-3/6 should reassess cause | Illustrative watch, not agency/covenant threshold. Cannot trigger from mixing A/B cases or stale points. |
| Real two-way market, volume and settlement/call mechanics available | Before implementation/size; CP-3B/6A | Verify executable lots and price impact; source size alone is insufficient. |
| Updated asset coverage, asset-quality marks, funding uses and maturities | Each reporting/financing event; CP-2/3C/4A | Published cushion is historical and not a default trigger; after-transaction certificate/fundamental work needed. |
| Jun15 2029 par-call approach or changed redemption plan | Dated contractual event; CP-3/3A | Preserve actual contingent make-whole versus par-call terms; no invented call probability. |

### T3E.10 — gaps and overall market handoff

| Missing/conflicting item | Affected function / consequence | Required evidence |
|---|---|---|
| Fair-value clean/dirty basis and exact time | Two conditional yields/spreads retained; no observed point estimate or executable conclusion | Issuer valuation method detail or contemporaneous matched dealer/transaction convention. |
| Exact EOM/dealer convention and business-day pricing | 30E/360 is an explicit scenario, not market-standard certification | Governing/quote conventions and a qualified dated engine before production publication. |
| Contingent earlier make-whole path | No full YTW/OAS or fixed early par-call list | Exact redemption date/rates and option model where decision-relevant. |
| Other notes' complete terms and matching quotes | Actual evaluated context is not a normalized multi-security spread curve or preference | Per-series governing terms and matched dated price conventions. |
| External corporate peers/index/rating and full fundamental view | No sector residual, rating-implied PD or calibrated disagreement | Matching corporate observations and actual CP-2/2G/2H handoffs. |
| Liquidity, flows and portfolio | No implementation capacity, size, technical attribution or correlation | Real two-way/trade/holding/mandate evidence. |
| Historical source and rounded inputs | Outdated functional case, no current recommendation or information-availability backtest | Current source only when the later task requires it; preserve this historical case. |

## Calculations

`CP-3D-calculations.json`, SHA `6a7189eeb6fa57a80403b0ec47474c3a4108401dc96940965c86d3965b7985a7`,
retains literal source values, exact Fraction cash-flow legs and conventions,
actual results and independent48-digit Decimal checks. The unchanged archived
helper's **low-level** `yield_to` / `_pv` solve supplied cash flows; a separate
Decimal Newton/PV calculation verifies roots, repricing, shocks and loss cases.

The helper's **high-level** `compute` still correctly refuses dated settlement
and30E/360 overrides. No supported high-level dated-bond interface, default
ACT/365F convention or native runtime acceptance is claimed. These are explicit
case cash-flow calculations. Source monetary values and calculated prices/ratios
remain separate; missing inputs never become zero. No production code changed.

## Gaps

T3E.10 governs. Confidence is Medium for selected source identity/arithmetic,
Low for executable market/credit inferences. All ten functional views were
considered, but exact current pricing, full option/default calibration and
implementation remain unproven. This is substantive conditional pricing output,
not a pass granted by empty tables or an unsupported refusal.

## Next module

CP-3 must actually open this handoff, preserve the two price-basis cases, coupon/
swap distinction, evaluated status and source date, and state what this changes
for the next security-comparison step. It may not treat the low-coupon discount
as distress or the69.46bp convention effect as an opportunity. Full fundamentals,
other-series legal/pricing and portfolio phases remain actual proof obligations.
Delivery/CP-OS must eventually carry the populated results with their assumptions;
Markdown output alone is not end-to-end completion.
