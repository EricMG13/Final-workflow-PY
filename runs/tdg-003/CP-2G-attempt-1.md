# CP-2G — TDG conditional annual credit paths

## Request

Test three annual conditional paths using checked issuer history, the dated
FY2025 guidance dossier and CP-2A's actual stress handoff. Current host-model
analysis with local tools and conversation context; no provider/API, complete
legacy owner or accepted full-underwriting forecast. USD millions; consolidated
group. Base balances: September 30, 2024. Historical guidance as-of: November 7,
2024. FY2025–FY2027 planning windows are October 1–September 30; only the first
guidance end date is source-confirmed here. Later windows are planning assumptions.

**Conditional result:** the stipulated reference reduces book debt and modelled
leverage; the combined downside crosses the 3x analyst coverage watch in FY2025.
Accessible liquidity, minimum cash and refinancing feasibility remain unknown.
These are illustrations, not an evidence-supported central issuer forecast.
Confidence is Medium in the bounded calculation, lower for economic applicability.

## Sources

Actually opened CP-0 source maps, annual CP-1, CP-2A, CP-1D, CP-2D and CP-2's
macro update. Exact consumed hashes, instruction/method hashes, operands and
outputs are retained in `CP-2G-attempt-1-calculations.json`. CP-1 supplies actual
history/definitions; CP-2A supplies the selected stress and watch meanings;
CP-1D supplies unresolved earnings quality; CP-2D/CP-2 supply cash-allocation,
access and dated hedge limitations. None supplies the conditional cash drivers.

The standalone `../tdg-guidance-001/CP-DR-attempt-1.md` has SHA-256
`e74a0b1f4b30af1ecb761b5833081e99db000b01b64ad2274131b53bc552ff44`.
I opened its actual SEC/issuer web captures and checked issuer, historical date,
FY2025 label, USD-million units, ranges and signed Table 6 bridge. Direct raw
HTML retrieval was refused; these are exact retained tool-text captures, not
raw source bytes. The SEC and IR copies are one issuer-origin evidence family.

Method: Deploy V-derived CP-2G skill and six method companions, with applicable
later precision/missingness protections and unchanged `cp2g.forecast`/
`test_breaks` helpers. Source revisions are pinned in the calculation record.
The later annual core omits quarterly troughs, new borrowing/refinancing and
separate tax/WC response. Those limitations are preserved, not adopted as
universal analytical rules. Current six-heading transport governs.

## Findings

### T2H.1 — upstream and research adoption

| Producer | Actual contribution | Carried restriction |
|---|---|---|
| CP-0 / CP-1 | Consolidated FY2024 source identities, exact historical amounts | Selected source/visual scope, not full-pack certification. |
| CP-2A | Combined 20% earnings decline / 10% interest increase; 7x / 3x watches | Illustrative static assumptions, not calibrated probabilities or covenants. |
| CP-1D | Signed issuer bridge and unresolved quality earnings/debt inventory | Do not turn As Defined into sustainable or agency earnings. |
| CP-2D / CP-2 | Actual distributions, quarter cash decline and access/hedge questions | Later quarter remains observed comparison, not a complete annual forecast base. |

<!-- table-id: cpdr.adoptions -->

| question_id | research_sha256 | disposition | reason | analytical_effect |
|---|---|---|---|---|
| RQ-guidance | e74a0b1f4b30af1ecb761b5833081e99db000b01b64ad2274131b53bc552ff44 | QUALIFIED | Dated issuer guidance is usable as an attributed earnings anchor; it does not validate cash conversion or future achievement. | Preserve exact first-year revenue/EBITDA midpoints separately; do not relabel net interest/tax provisions as cash. |

### T2H.2 — historical-to-conditional bridge and definitions

| Metric | FY2024 actual / September instant | Conditional treatment |
|---|---:|---|
| Revenue | 7,940 | Actual opening revenue; future growth is an explicit driver. |
| Ordinary EBITDA / EBITDA As Defined | 3,813 / 4,173 | Forward engine uses As Defined-style earnings; no quality denominator supplied. |
| OCF / capex / OCF-minus-capex proxy | 2,045 / 165 / 1,880 | Actual historical cash measures; not silently reproduced by the forward engine. |
| Cash interest / cash taxes | 1,158 / 539 | Actual cash payments; distinct from guidance accrual expense/provision. |
| Carrying debt / cash | 24,880 / 6,261 | Opening reported balances; gross principal and accessible cash are different. |
| True issuer FCF / working-capital-only input | Not supplied / unresolved | Remain null; no tax/WC residual is invented to force historical reconciliation. |

The [dated outlook](https://transdigmgroupinc.gcs-web.com/news-releases/news-release-details/transdigm-group-reports-fiscal-2024-fourth-quarter-and-year-end/)
supplies sales 8,750–8,950 and As Defined earnings 4,615–4,755; calculated
midpoints are 8,850 and 4,685. Its [Table 6](https://www.sec.gov/Archives/edgar/data/1260221/000126022124000082/exhibit991tdg2024q4earning.htm)
reconciles ordinary EBITDA 4,479 and signed adjustments 206 to 4,685. Net
interest expense 1,540 and tax provision 616 retain their accrual definitions.

Finite reference drivers yield FY2025 revenue **8,849.924** and earnings
**4,685.1497656**. Residuals versus the exact source midpoints are **−0.076**
and **+0.1497656**. These are explicit assumption-rounding differences, not
source corrections or exact guidance reproduction. The displayed source margin
52.9% is rounded; it is not the exact midpoint ratio.

### T2H.3 — assumption register

Every row applies to the consolidated group and three planning years; rates
are decimal fractions. Classes distinguish source facts from analyst choices.

| ID | Driver / values FY2025; FY2026; FY2027 | Class / rationale and limits |
|---|---|---|
| G | Revenue growth 0.1146; 0.05; 0.05 | Analyst judgment: finite first-year approximation to guidance midpoint growth; later growth is stipulated, not guidance/consensus. |
| M | Earnings margin 0.5294 throughout | Analyst judgment: finite first-year midpoint ratio approximation, then held. No resolved sustainable margin claim. |
| K | Capex/revenue 0.02 throughout | Analyst judgment for a bounded calculation; no sourced maintenance/growth forecast. |
| W | Combined cash-tax/WC share 0.10 throughout | Analyst judgment, not a source tax rate or actual WC bridge; cash effects of adjustments remain unresolved. |
| I | Cash interest/opening carrying debt 0.06 throughout | Analyst judgment, not a coupon, guidance cash payment or independently reconstructed hedge schedule. |
| D | Distributions 4,348; 0; 0 | First year includes only the approximate located October event. Additional distributions excluded by scenario stipulation; zero is not a finding of absence. The 131/132 source difference persists. |
| P | Debt cash repayment/book reduction 1,000 each year | Analyst judgment, assuming no noncash book changes; not a sourced maturity schedule. No automatic sweep. |
| X | New issuance, M&A, buybacks, other financing/investing excluded | Explicit calculation boundary, not source-confirmed zero. Debt raised before opening is not added again. |
| L | Unconditional facility access and minimum cash unknown | Missing evidence; accessible liquidity stays null even with positive model cash. |
| S | Downside earnings −20%, cash interest +10% each year | Actual CP-2A assumptions adopted; all other drivers held, no probability. |
| U | Upside margin 0.5494 throughout, other reference drivers held | Analyst disconfirming case: 2 percentage points higher margin, not management guidance. |

Simplified model CFO = model earnings − assumed cash interest − combined tax/WC;
cash proxy = model CFO − capex. These engine measures are not reported CFO,
issuer FCF or distributable cash. Distributions and repayments are outside that
proxy and deducted exactly once from cash. Leases, adjustment cash effects,
noncash debt changes and full financing obligations are not separately resolved.

### T2H.4 — operating paths

Rounded display only; exact values and formula results remain in the calculation
record. This table uses G/M/K/W/I/S/U as applicable.

| Case / FY | Revenue | Earnings | Model CFO | Capex | Cash proxy |
|---|---:|---:|---:|---:|---:|
| Reference / 2025 | 8,849.92 | 4,685.15 | 2,307.36 | 177.00 | 2,130.36 |
| Reference / 2026 | 9,292.42 | 4,919.41 | 2,557.37 | 185.85 | 2,371.52 |
| Reference / 2027 | 9,757.04 | 5,165.38 | 2,816.87 | 195.14 | 2,621.73 |
| Downside / 2025 | 8,849.92 | 3,748.12 | 1,221.05 | 177.00 | 1,044.05 |
| Downside / 2026 | 9,292.42 | 3,935.53 | 1,430.20 | 185.85 | 1,244.36 |
| Downside / 2027 | 9,757.04 | 4,132.30 | 1,646.52 | 195.14 | 1,451.38 |
| Upside / 2025 | 8,849.92 | 4,862.15 | 2,484.36 | 177.00 | 2,307.36 |
| Upside / 2026 | 9,292.42 | 5,105.26 | 2,743.21 | 185.85 | 2,557.37 |
| Upside / 2027 | 9,757.04 | 5,360.52 | 3,012.01 | 195.14 | 2,816.87 |

### T2H.5 — debt and cash roll-forward

| Case / FY | Opening debt | Repayment | Closing debt | Cash interest | Opening cash | Distributions | Closing cash |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reference / 2025 | 24,880 | 1,000 | 23,880 | 1,492.80 | 6,261.00 | 4,348 | 3,043.36 |
| Reference / 2026 | 23,880 | 1,000 | 22,880 | 1,432.80 | 3,043.36 | 0 | 4,414.88 |
| Reference / 2027 | 22,880 | 1,000 | 21,880 | 1,372.80 | 4,414.88 | 0 | 6,036.61 |
| Downside / 2025 | 24,880 | 1,000 | 23,880 | 1,642.08 | 6,261.00 | 4,348 | 1,957.05 |
| Downside / 2026 | 23,880 | 1,000 | 22,880 | 1,576.08 | 1,957.05 | 0 | 2,201.40 |
| Downside / 2027 | 22,880 | 1,000 | 21,880 | 1,510.08 | 2,201.40 | 0 | 2,652.78 |
| Upside / 2025 | 24,880 | 1,000 | 23,880 | 1,492.80 | 6,261.00 | 4,348 | 3,220.36 |
| Upside / 2026 | 23,880 | 1,000 | 22,880 | 1,432.80 | 3,220.36 | 0 | 4,777.72 |
| Upside / 2027 | 22,880 | 1,000 | 21,880 | 1,372.80 | 4,777.72 | 0 | 6,594.60 |

Each opening cash/debt equals the previous closing value. Closing cash = opening
cash + cash proxy − distributions − repayments. All stipulated-equation residuals
are zero; that is not a reconciliation to actual future outcomes. No negative
cash is floored and no facility draw plugs a shortfall. Unconditional undrawn
capacity and accessible liquidity are null throughout all three cases.

### T2H.6 — calculated metrics and definitions

| Case / FY | Carrying debt / earnings | Mechanical net debt / earnings | Earnings / cash interest | Cash proxy / closing debt |
|---|---:|---:|---:|---:|
| Reference / 2025 | 5.10x | 4.45x | 3.14x | 8.92% |
| Reference / 2026 | 4.65x | 3.75x | 3.43x | 10.36% |
| Reference / 2027 | 4.24x | 3.07x | 3.76x | 11.98% |
| Downside / 2025 | 6.37x | 5.85x | 2.28x | 4.37% |
| Downside / 2026 | 5.81x | 5.25x | 2.50x | 5.44% |
| Downside / 2027 | 5.29x | 4.65x | 2.74x | 6.63% |
| Upside / 2025 | 4.91x | 4.25x | 3.26x | 9.66% |
| Upside / 2026 | 4.48x | 3.55x | 3.56x | 11.18% |
| Upside / 2027 | 4.08x | 2.85x | 3.90x | 12.87% |

Mechanical net debt deducts all modelled cash; it is not available-cash leverage.
No covenant ratio, agency metric, fixed-charge cover, liquidity runway or rating
is supplied. Current debt-quality/earnings-definition questions remain unresolved.

### T2H.7 — first tests and consequences

| Test | Reference | Downside | Upside | Meaning |
|---|---|---|---|---|
| 3x analyst coverage watch | Not reached by FY2027 | FY2025, remains below through FY2027 | Not reached by FY2027 | First tested earnings/debt-service warning under stipulated stress, not a covenant breach. |
| 7x analyst total-leverage watch | Not reached by FY2027 | Not reached by FY2027 | Not reached by FY2027 | Assumed repayments/growth improve this measure despite stress. |
| Cash proxy ≤0 / coverage ≤1x | Neither reached by FY2027 | Neither reached by FY2027 | Neither reached by FY2027 | Does not test actual funding need, required cash or unmodelled obligations. |
| Minimum accessible liquidity | Not Calculable | Not Calculable | Not Calculable | Missing minimum cash/access evidence; positive year-end cash cannot close it. |

The shock's initiating condition is margin/cash pressure while interest rises;
the first modelled break is weaker coverage. Later debt-service/refinancing
consequences require dated facility and cash-use evidence. The model assumes no
mitigation; distribution restraint or refinancing is not silently credited as a
funding solution. July 2025 securitization timing and later note/loan maturities
still require CP-2D/CP-3C review, not an assumption that 1,000 covers every use.

### T2H.8 — deleveraging and disconfirmation

Reference leverage falls from 5.10x to 4.24x; downside from 6.37x to 5.29x under
the same 1,000 annual repayments. This is repayment/growth-dependent and assumes
no extra distributions, M&A, buybacks or financing. It is not an issuer commitment.
The 2-point higher-margin case increases cash generation and strengthens cover,
which is a concrete counterargument to a uniformly adverse conversion thesis.
It wins only if actual earnings convert to accessible cash and cash uses stay
within the stipulated boundary. Missed guidance, lost protection, additional
extraction or unmodelled obligations could reverse that conclusion. No target
date for actual deleveraging or probability is inferred.

### T2H.9 — gaps and delivery-driver readiness

| Gap | Affected result | Required evidence / repair |
|---|---|---|
| Unsupported complete cash drivers and later-year operating assumptions | Reference is conditional, not the most evidence-supported central forecast | Actual cash-interest/hedge path, tax/WC bridge, capex, operating plan and financing/distributions. |
| No minimum cash, location/restrictions or unconditional facility access | Liquidity, runway and funding sufficiency unavailable | Dated access/covenant evidence and complete intra-year uses. |
| Maturities/refinancing, leases, noncash book changes and other uses omitted | Debt/cash path does not prove full obligations covered | Calendar of cash and principal/book adjustments, including securitization. |
| No actual segment-slot allocation and segment/financing driver decisions | CP-MODEL driver publication not ready | Preserve null active growth/other-use inputs; do not infer slots from display order or fill zeros. |
| Calendar-only wrapper | Full owner refuses actual September base | Supply/validate explicit fiscal planning windows before a future wrapper integration; never relabel TDG as calendar year. |
| Inherited CP-0/CP-1/CP-1D/CP-2D and research limits | Source, quality, current status and cash applicability remain bounded | Carry exact dates, preferred-stock scope, 131/132 difference and raw-retrieval limitation. |

<!-- table-id: cp2g.cp_model_forecast_drivers -->

| Driver family | Case / years | Value / readiness | Reason |
|---|---|---|---|
| Division growth / exact slot IDs | Reference/downside, FY2025–FY2027 | null; not ready | No validated segment-slot map or segment forecasts; consolidated growth is not a substitute. |
| Acquisitions, net equity, dividends, other financing/investing | Reference/downside, FY2025–FY2027 | Full publication inputs null; not ready | Stipulated illustration exclusions and one approximate event are not a complete financing plan. |

This is an explicit readiness summary, **not the full per-slot exporter contract**.
No source or driver table was fabricated to claim workbook readiness. CP-MODEL
remains a downstream publication consumer, with targeted input gaps.

## Calculations

Unchanged pure `forecast` and `test_breaks` actually executed for nine annual
rows. The record retains exact Decimals, input/source/method identities and
215 numeric/ratio/balance/break/missingness checks, plus nine cash recurrences
recomputed solely from stipulated inputs using independent rational arithmetic.
Ratios agree within 1e-30; known sums/products are exact. A separate adversarial
missing-opening-cash check propagates missing cash/net debt/liquidity while
retaining known revenue/earnings. It is not an issuer scenario.

Actual `require_calendar` rejects the source base 2023-10-01–2024-09-30; actual
`fy_periods` prints January–December windows. This is a confirmed restricted
implementation, not a passed calendar integration. The date-free pure engine
is reused with the explicit planning windows above; no source date, runtime
receipt or accepted head is invented. No production code changed.

## Gaps

T2H.9 and every conditional assumption remain binding. A complete source-backed
forecast, quarterly troughs, current conditions, refinancing feasibility, agency/
covenant conclusions and CP-MODEL workbook publication remain unproven. No actual
FY2025 outcome found in search was admitted to the historical model.

## Next module

CP-2 must actually consume the coverage-watch result, countercase and full cash/
access limitations before integrating this illustration. CP-2D/CP-3C need complete
uses/access and facility evidence. CP-2H needs actual agency triggers. Delivery
may reproduce the checked conditional figures with their assumptions and exact
handoff references. Actual deliverables replace CP-MEMO; this Markdown alone
does not complete the user's task.
