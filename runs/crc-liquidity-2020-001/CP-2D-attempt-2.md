# CP-2D — CRC dated cash and funding dependence

## Request

**Ready with Limitations. Liquidity Risk Level: Tight for the thirteen-week
budget case, conditional on financing access and the stated projection.** The
source keeps cash at USD10m through draws and repayments; cash without that
financing is negative in the first tested week. The extended budget approaches
maturity with insufficient nominal liquidity headroom, before additional LC
effects. This does not establish actual historical compliance, a current credit
view, formal Months to Empty or twelve-month liquidity sufficiency.

Current host-model analysis on2026-11-04, with preceding context. I opened the
frozen request, budget transcription, original SEC passages, method and retained
calculation record. No isolated provider, independent assurance or native
accepted CP-0/CP-1/CP-2 heads are claimed. This historical CRC case is separate
from TDG and Frontier; subsequent outcomes are not used.

## Sources

`inputs.json` pins the request, source capture, budget-inputs.json, independent
pre-production Fraction expectations and exact method/helper revisions. The
wider selected CP-2D ten-step method is retained under
`docs/reuse/selected-methods/skills/cp-2d-liquidity-cash-flow-bridge/`;
the later pure Decimal sum/difference/ratio and missingness rules are reused.
Historical staff, export and native transport restrictions are not project authority.

### T2E.1 — source gate

| source_document_id | source_document_name | source_quality | period | entity_covered | data_supplied | limitation | downstream_use |
|---|---|---|---|---|---|---|---|
| CRC-DIP-A | Filed senior DIP agreement, Exhibit A initial budget | Original issuer SEC body; unaudited discussion projection | Budget dated2020-07-09; agreement2020-07-23 | California Resources Corporation / consolidated budget | Thirteen weeks ending2020-07-17–2020-10-09 and seven labelled monthly/stub periods through2021-01-15 | Form of Budget; subject to material change and for discussion. Not evidence of approved/achieved cash flows. | Dated cash/funding bridge and downstream funding review. |
| CRC-DIP-TERMS | Same filed senior agreement and attached interim order text | Original filed contractual text; limited located passages | Agreement2020-07-23; maturity2021-01-15, earlier termination possible | Senior borrower/credit parties, not an assumed combined senior/junior cash pool | Senior commitment, roll-up, LC exposure, liquidity tests, interim cash limit, maturity/termination and borrowing conditions | Final order, commitment schedule, subsequent modifications, approval and actual access not established. | Conditional access/covenant/capacity diagnostics; no historical breach certification. |
| CRC-CAPTURE | sources/filing-captures.txt | Retained actual web-tool passages,856 original SEC lines | Retrieved2026-11-04 | Same issuer/document | Source numbers, definitions and exact line locators | Capture hash is not a raw original-HTML/PDF hash or full-document coverage proof. | Repeatable located-source checks. |

Original source: https://www.sec.gov/Archives/edgar/data/1609253/000160925320000118/a20200723exhibit101.htm .
Budget pp1–3: SEC L2686–3280. Legal definitions L696/898/908/911/914/1127/1130;
financial covenants L2177–2180; interim-order amounts L3965–3977.

Monthly units are explicitly USD millions at L3057. Weekly units are **Derived**
from the same three-page budget and matching legal roll-ups, rather than a scale
legend repeated on the weekly page. Source whole-million amounts remain rounded.
Printed financial dashes in populated budget amount cells are interpreted as
zero **at displayed precision**, with original lexemes retained. That convention
does not turn a missing input, an absent cash-use category or unverified access
into zero, and does not assert an exact underlying economic zero.

## Findings

### T2E.2 — beginning liquidity and access

| Liquidity Component | Source-Supported Amount | Accessibility Status | Source Trace | Limitation / Restriction | Risk Mechanic | Credit Implication |
|---|---|---|---|---|---|---|
| Cash | USD47m opening for first weekly forecast period; monthly July opening USD97m | Provisional budget starting balances | L2870; L3163; footnote L3278 | Different scope: monthly July includes pre-petition weeks ending7/3 and7/10 plus post-petition weeks. Restriction certification absent. | Mixing the openings would overstate the weekly buffer. | Use each with its own schedule; neither certifies unconditional accessible liquidity. |
| Restricted cash | Insufficient Information | Insufficient Information | Legal definition L908 | No complete restricted/cash-collateral balance retained. | Consolidated cash under the agreement has specific exclusions. | Do not assume all book/budget cash is free cash. |
| Revolver commitment | USD483,010,655.62 senior total commitment at closing | Contract amount; access conditional | L1130; recitals/interim text L3965 | Includes noncash rollover/LC exposure; not all fresh cash. | Existing claims occupy the same commitment pool. | Gross commitment is not deployable cash. |
| Other committed liquidity | Budget's cash-draw/availability pool totals USD250m | Provisional budget convention | L2990–3018; L3239–3255 | Not independently verified as unconditional availability. | Draws convert unused capacity into cash rather than creating extra total liquidity. | Never add the pool and drawn cash twice. |
| Covenant-constrained availability | USD219m conditional cash-loan capacity after planned incremental LCs | Conditional diagnostic, not certified access | L696/898/908/1130; L3021; calculation record | Assumes unchanged full senior commitment, exact senior roll-up and existing LC amounts, planned USD31m extra LCs outstanding and no cash-collateral offset. | LCs consume shared credit exposure. | Budget's USD250m convention needs reconciliation to operative exposure and approvals. |
| Beginning accessible liquidity | Insufficient Information | Insufficient Information | Above source/access gaps | Final order, commitment schedule, cash restrictions and actual conditions not established. | Nominal headroom cannot substitute for usable resources. | Formal runway and complete twelve-month funding sufficiency remain unavailable. |

### T2E.3 — cash uses and timing

| Cash Use | Amount | Timing | Mandatory / Discretionary | Source Trace | Risk Mechanic | Credit Implication | Limitation |
|---|---|---|---|---|---|---|---|
| Budget operating disbursements | USD427m reported weekly total; USD904m reported monthly/stub total | Thirteen weeks / labelled periods to maturity | Mixed forecast; individual legal obligations not fully allocated | L2781–2794; L3107–3114 | AP, payroll, power and other operating payments absorb receipts. | Operational cash needs continue inside restructuring. | Not a complete mandatory-use or WC/capex classification. |
| Cash interest / fees | Combined USD38m weekly; USD65m monthly/stub | Same source horizons | Contractual/fee mix not separated | L2803–2816; L3122–3129 | Financing consumes cash in addition to operating payments. | Preserve the combined definition; do not call it pure cash interest. | Already included in net cash flow; never subtract it again. |
| Other budget disbursements | USD62m weekly; USD198m monthly/stub | Same source horizons | Mixed; allocation not established | L2818–2831; L3131–3138 | Other restructuring/financing/operational uses can absorb liquidity. | Follow the source aggregate without inventing its legal priority. | No unsupported tax, lease, capex or restructuring split. |
| Budget DIP paydowns | USD133m gross across the thirteen weeks | Weeks ending2020-07-24,2020-08-21,2020-09-25 | Planned revolving paydowns, not a proved scheduled amortization requirement | L2904–2914; calculations.json | Cash-positive weeks repay debt, followed by reborrowing. | Gross advances, repayments, net financing and peak usage differ. | Future execution is not demonstrated. |
| Maturity | Then-outstanding senior loan principal payable on Termination Date; specified commitment/LC/fronting fees have separate payment clauses. Complete takeout amount Insufficient Information | 2021-01-15, or an earlier defined termination event | Contractual, subject to governing documents/exit | Section2.5(a), L1253; section4.1, L1488–1498; L914/1127; sources/maturity-supplement.txt | Funding stops or must be taken out at termination. | Unused capacity at the final stub is not a refinancing solution. | LC collateral/drawing treatment and other claims require their own terms; no complete takeout/exit plan, junior maturity review or later amendments retained. |
| Cash taxes; debt amortization; lease payments | Insufficient Information separately | Twelve-month horizon | Insufficient Information | No complete disaggregation/schedule supplied | Aggregated disbursements do not establish each obligation's timing. | Full mandatory-use coverage cannot be certified. | Unknown is not zero and is not added again to an already-net source flow. |
| Mandatory/growth capex; WC outflows | Insufficient Information separately | Twelve-month horizon | Insufficient Information | Source operating aggregates only | Maintenance, growth and working-capital flexibility differ. | Do not claim deferral capacity or infer a standalone WC/capex response. | Preserve the source cash forecast without invented allocation. |
| Dividends; integration; litigation; pensions; other commitments | Insufficient Information separately | Twelve-month horizon | Insufficient Information | No full obligation inventory supplied | Omitted independent categories could change a full bridge. | No conclusion that all such uses are absent. | Source-budget scope only. |

### T2E.4 — working-capital and capex pressure

| Driver | Evidence | Expected Cash Impact | Risk Mechanic | Credit Implication | Source Trace | Limitation |
|---|---|---|---|---|---|---|
| Uneven receipts and payment timing | Source weekly net flows vary from a USD68m outflow to a USD63m inflow | The no-financing cash path is already negative by the first tested week | Collections/payment timing creates intra-period funding needs despite later cash-positive weeks. | Average burn or ending debt alone understates the funding pinch point. | L2705–2868; weekly table below | Budget projection, not actual collection performance or a proved recurring seasonal pattern. |
| Payables/payroll/power cash uses | Source-specific operating payment rows | Included in budget operating disbursements | Operating commitments can arrive before offsetting receipts. | Funding access must be timed to payments, not inferred from EBITDA. | L2721–2794 | Not a complete standalone working-capital bridge. |
| Capex flexibility / tax / leases | Insufficient Information | Insufficient Information separately | Unproven deferral or reclassification could make the bridge look better. | No mitigation is credited without evidence. | Missing disaggregation | No invented zero or repeated deduction from net flow. |

### Weekly funding bridge — USDm at source display precision

| Week ending | Source net cash flow | Source DIP draw / paydown | Calculated ending cash | Cash without DIP financing | Recomputed cash-loan balance | Reported cash-loan balance | Reported DIP availability |
|---|---|---|---|---|---|---|---|
| 2020-07-17 | (68) | 31 | 10 | (21) | 31 | 31 | 219 |
| 2020-07-24 | 13 | (13) | 10 | (8) | 18 | 18 | 232 |
| 2020-07-31 | (4) | 4 | 10 | (12) | 22 | 22 | 228 |
| 2020-08-07 | (31) | 31 | 10 | (43) | 53 | 53 | 197 |
| 2020-08-14 | (47) | 47 | 10 | (90) | 100 | 100 | 150 |
| 2020-08-21 | 57 | (57) | 10 | (33) | 43 | 43 | 207 |
| 2020-08-28 | (14) | 14 | 10 | (47) | 57 | 58 | 192 |
| 2020-09-04 | (9) | 9 | 10 | (56) | 66 | 67 | 183 |
| 2020-09-11 | (17) | 17 | 10 | (73) | 83 | 84 | 166 |
| 2020-09-18 | (37) | 37 | 10 | (110) | 120 | 120 | 130 |
| 2020-09-25 | 63 | (63) | 10 | (47) | 57 | 58 | 192 |
| 2020-10-02 | (5) | 5 | 10 | (52) | 62 | 63 | 187 |
| 2020-10-09 | (20) | 20 | 10 | (72) | 82 | 82 | 168 |

Source L2865–3018, with source opening weekly cash47. Cash recursion is opening
cash + source net cash flow + source DIP draw/paydown + source RBL flow (printed
dashes under the stated display-zero convention). Each cash equation reaches
the source ending10. The no-DIP case removes that financing only; it is an
analyst counterfactual, not a second issuer forecast. It first fails by the week
ending2020-07-17, without claiming the exact intraday exhaustion date.

Net new cash financing82 at the horizon end hides peak cash-loan usage120 in
the week ending2020-09-18. Gross advances215 and repayments133 are not a215
commitment requirement. The source's constant10 is an implicit budget cash target,
not a contractual minimum or independently proved operating reserve. Funding
must arrive on time; source cash-positive weeks do not repair a preceding
unfunded payment automatically.

### Extended monthly/stub bridge — USDm at source display precision

| Source period | Source opening cash | Source net cash flow | DIP draw / paydown | Ending cash | Ending cash-loan balance | Reported DIP availability | Cash plus nominal availability |
|---|---|---|---|---|---|---|---|
| Jul-2020, pre/post-petition weeks | 97 | (109) | 22 | 10 | 22 | 228 | 238 |
| Aug-2020 | 10 | (36) | 36 | 10 | 58 | 192 | 202 |
| Sep-2020 | 10 | — | — | 10 | 58 | 192 | 202 |
| Oct-2020 | 10 | (16) | 16 | 10 | 74 | 176 | 186 |
| Nov-2020 | 10 | (19) | 19 | 10 | 93 | 157 | 167 |
| Dec-2020 | 10 | (58) | 58 | 10 | 151 | 99 | 109 |
| Jan-2021 stub through2021-01-15 | 10 | (98) | 98 | 10 | 249 | 1 | 11 |

Source L3055–3280. The printed September flow dashes are retained; computation
uses displayed-zero interpretation, not proof of an exact zero underlying flow.
July's97 opening and pre-petition scope are not substituted for weekly47.
January stops at the fifteenth under source footnote2, matching the agreement's
stated maturity; it is not a full January or a twelve-month forecast.

### T2E.5 — bridge and twelve-month boundary

| Bridge Item | Amount | Source / Calculation | Status | Credit Comment | Source Trace |
|---|---|---|---|---|---|
| Beginning cash | USD47m weekly; USD97m July broader scope | Source budget, separate windows | Provisional | Not interchangeable or independently unrestricted. | L2870/3163/3278 |
| Accessible revolver availability | Insufficient Information | Cannot certify conditions from nominal budget pool | Insufficient Information | Do not add total facility or roll-ups as cash. | L696/908/911/1130/3965–3977 |
| Beginning accessible liquidity | Insufficient Information | Cash/access certification absent | Insufficient Information | Formal full-liquidity arithmetic is gated. | T2E.2 |
| Operating cash inflow/outflow | Reported weekly operating flow (19); monthly/stub (74) USDm | Separate source row, not net cash after other flows | Provisional | Not recurring free cash flow or a full WC/capex allocation. | L2797–2801/3117–3119 |
| Working-capital impact | Insufficient Information separately | Included effects not disaggregated | Insufficient Information | Never subtract an invented extra amount. | T2E.4 |
| Cash interest | Combined interest/fees38 weekly;65 monthly/stub USDm; pure interest Insufficient Information | Source combined row already enters net cash | Provisional | Do not double-count. | L2803–2816/3122–3129 |
| Cash taxes | Insufficient Information separately | No separate complete schedule | Insufficient Information | Not a zero assumption. | T2E.3 |
| Mandatory capex | Insufficient Information separately | No source maintenance/growth allocation | Insufficient Information | No automatic deferral credit. | T2E.4 |
| Debt amortization/maturities | Planned cash-loan paydowns, plus2021-01-15 contractual maturity; complete takeout amount Insufficient Information | Keep source cash budget and legal maturity separate | Provisional | Closing cash10 does not retire all then-outstanding obligations. | L2904–2914/914/1127 |
| Other cash uses | Source other disbursements62 weekly;198 monthly/stub USDm | Source aggregate, already included | Provisional | Category absence is not factual zero. | L2818–2831/3131–3138 |
| Weekly known cash bridge | USD47m −119m +82m =10m | Source net cash flow and net DIP funding | Calculated | Counterfactual without DIP ends negative72m; first shortage is much earlier. | Weekly table; calculations.json |
| Monthly/stub known cash bridge | USD97m −336m +249m =10m | Distinct larger source horizon | Calculated | Financed budget result, not independent cash generation. | Monthly table; calculations.json |
| Nominal capacity less planned incremental LCs | USD250m −31m =219m | Exact senior commitment less exact roll-up/existing LC; conditional additional LC adjustment | Calculated | Diagnostic under stated unchanged-pool/LC assumptions; no approval/access certificate. | Legal definitions and calculation record |
| Conditional target-cash funding gap | USD30m by final stub | Projected cash-loan need249 minus conditional capacity219 | Provisional | Keeping the source10 target would require added capacity, lower uses, LC changes or exit funding under those assumptions. | Monthly table; calculations.json |
| Cash with that hard capacity and unchanged uses | Negative USD20m by final stub | 97 −336 +219 | Provisional | Negative model cash is retained as an infeasibility signal, not floored or funded by a plug. | calculations.json |
| Ending accessible liquidity, full twelve months | Insufficient Information | Source stops at maturity; access/remaining uses unresolved | Insufficient Information | The finite budget does not become a complete twelve-month bridge. | T2E.9 |

### Access and covenant interpretation

The senior commitment483.01065562 USDm includes senior roll-up82.871057 USDm
and existing LC capacity150.13959862 USDm. Removing those leaves250 USDm before
the budget's31 incremental LCs. Under the stated same-pool, fully outstanding,
uncollateralized-LC diagnostic, cash-loan capacity becomes219 USDm. The junior
roll-up650 USDm is not fresh operating cash and is not subtracted a second time
from this senior-only commitment. This is a version/definition comparison of an
initial discussion budget with filed terms, not proof that the actual company
borrowed beyond capacity or breached a covenant.

The attached interim-order text permits85 USDm new cash before final approval.
The weekly budget first projects a cash-loan balance above that amount at100
USDm in the week ending2020-08-14; its peak120 exceeds that interim limit by35.
That identifies dependence on further authorization and other borrowing
conditions. It does not prove when an actual final order was entered or any
actual draw was rejected. Termination also includes an absent-final-order trigger
forty days after the petition and possible earlier sale/plan/commitment events.

Contractual Liquidity is unused commitments after total credit exposure plus
defined unrestricted cash. It is neither cash alone nor the source cash target.
The daily floor is35 USDm; the four-Friday average floor is50 USDm. Even the
budget's unadjusted final cash-plus-availability proxy is11,24 below the daily
floor, before planned incremental LC effects. Under the conditional LC adjustment,
the final diagnostic is negative20,55 below that floor. Negative capacity or
liquidity is not certified actual availability: it flags that the unchanged
scenario cannot all be executed as written. There are no daily balances or
complete Friday/access inputs to certify compliance, identify a precise breach
date or calculate a formal rolling-average covenant result.

### T2E.6 — runway and Months to Empty

| Metric | Result | Basis / restriction |
|---|---|---|
| First no-DIP weekly cash shortage | Week ending2020-07-17; negative USD21m | Counterfactual with source cash/uses and no DIP draw; exact intraday date unknown. |
| Peak no-DIP cash shortage | Week ending2020-09-18; negative USD110m | Peak funding to retain the source10 target is120, not the horizon-end82 cash-loan balance. |
| Formal Months to Empty | Insufficient Information | Beginning unrestricted/access-certified liquidity and a representative burn basis are not established. |
| Full twelve-month funding sufficiency | Insufficient Information | Source weekly/monthly budgets terminate before twelve months; exit, debt takeout and remaining cash uses unresolved. |

An average burn calculation would erase payment timing: later cash-positive
weeks cannot cure the first tested unfunded week. No annualization, invented
monthly duration or positive MTE based on nominal unused capacity is supplied.

### T2E.7 — mitigants and constraints

| Mitigant / Constraint | Evidence | Risk Mechanic | Credit Implication | Source Trace | Limitation |
|---|---|---|---|---|---|
| Planned committed funding / cash-positive weeks | Source financing schedule maintains10 cash; some weeks repay debt | Timely revolving availability can bridge uneven operating receipts/payments. | Strongest counterargument to immediate cash failure; supports the conditional thirteen-week path. | L2865–3018 | It wins only if approvals, access, cash availability and forecast timing hold. |
| Final-order / borrowing constraints | Interim new cash85; forecast100 by week ending2020-08-14 | Requested cash capacity can depend on approvals before the largest need. | Monitor approval and borrowing conditions before the payment week. | L3974; weekly table | No actual authorization/draw history or automatic available amount inferred. |
| LC / roll-up encumbrance | Senior roll-up, existing and planned incremental LCs occupy exposure | Gross facility size overstates new cash; draws do not add equal total liquidity. | Reconcile the pool before relying on capacity. | L696/898/908/1130/3965 | Diagnostic assumptions, not a full legal opinion/access certificate. |
| Budget variance and liquidity covenants | Disbursement variance tests; daily35/four-Friday50 liquidity floors | Overspending or shrinking headroom may constrain financing before cash is exhausted. | Trigger targeted legal/funding review; a stable10 cash line is not sufficient comfort. | L2177–2180 | No actual variances or certified daily/Friday balances. |
| Exit/maturity requirement | Source January stub ends at2021-01-15 maturity, earlier termination possible | Funding must be repaid, converted or replaced; unused commitment expires. | CP-3C must identify actual takeout/exit terms rather than carry capacity forward. | L914/1127/3280 | No successful exit/refinancing credited from later outcomes. |
| Capex deferral, asset sales, sponsor support | Insufficient Information | Unsupported mitigation may not arrive or may create other cash obligations. | No balancing source is invented. | T2E.9 | A target repair request, not an adverse factual conclusion. |

### Liquidity risk and causal sequence

**Liquidity Risk Level: Tight — thirteen-week budget-conditional scope.** The
positive evidence is a specified financing schedule, cash-positive repayment
weeks and nominal budget availability above projected peak cash-loan usage.
It can cover the displayed near-term path if executable. The constraint is
dependence on approvals/conditions and an unproven complete liquidity definition;
longer-horizon nominal headroom also erodes toward maturity. This supports
heightened funding monitoring, not an unconditional Adequate conclusion.

Initiating risk: receipts arrive late, cash uses exceed projection, or financing
authorization/access is absent. First observable break: the initial no-financing
week cannot meet the projected cash path; further authorization becomes relevant
before the week with cash-loan balance100. Financial transmission: committed
headroom and covenant liquidity can shrink even while cash is mechanically held
at10. Later consequence: the extended budget needs a reconciled facility/LC basis
and a maturity takeout. Observable triggers are approval/borrowing notices,
receipt/payment variances, cash below the budget target, increasing LC exposure,
liquidity-test headroom and approaching termination. Actual twelve-month and
current-issuer Liquidity Risk Level remain Insufficient Information.

### T2E.9 — gaps ledger

| Gap | Missing Data | Why It Matters | Impact on Output | Required Follow-Up | Downstream Module Affected |
|---|---|---|---|---|---|
| Source stage / access | Approved updated budget, final order, commitment schedule, drawing conditions and actual collateral/cash access | A proposed draw is not verified accessible funding. | Unconditional opening liquidity and full funding sufficiency unavailable. | Obtain operative approvals, schedules, certificates and actual access evidence. | CP-3C, CP-4, CP-5, CP-6 |
| Cash-use allocation | Complete taxes, leases, capex, WC and other obligation schedules | Aggregate budget rows cannot certify every mandatory/discretionary use. | Full twelve-month bridge and mitigant assessment limited. | Source-tagged cash-use and operating/financing schedules. | CP-2G, CP-3C |
| Covenant input frequency | Daily unrestricted cash/credit exposure and all required Friday observations | Monthly points cannot certify a daily or four-Friday test. | Formal compliance/headroom and exact break date unavailable. | Exact legal-input calendar and balances. | CP-4A, CP-3C |
| Maturity / exit | Senior/junior takeout terms, full cash-collateral requirements and later amendments/exit plan | Unused capacity cannot discharge obligations at termination. | Complete maturity funding amount/feasibility unavailable. | Dated operative takeout and exit documents; do not use hindsight as forecast evidence. | CP-3C, CP-4 |
| Burn applicability | Access-certified opening resources and representative normalized burn | Restructuring/timing/financing flows distort straight-line runway. | Formal Months to Empty missing. | Validated cash-access and burn basis with seasonality/one-off review. | CP-2G, CP-3C |
| Twelve-month horizon / native proof | Cash uses/sources beyond the January stub; full source-pack and native/controller integration | A six-month-to-maturity budget does not establish a twelve-month pathway. | No complete twelve-month/current/native claim. | Target the missing period/source functions and CP-OS integration. | CP-OS, CP-2G, delivery |

### Overall liquidity view

Overall, the historical initial budget presents tight, execution-dependent
near-term liquidity. The displayed weekly path maintains10 cash with financing,
but the first no-DIP tested week is negative21. Unconditional accessible opening
liquidity and complete twelve-month uses are not established. Peak cash-loan
need120, rather than final82, makes the timing of authorization and capacity
material. The longer source budget approaches maturity with nominal liquidity
below the contractual daily floor before further LC effects. Formal Months to
Empty and actual compliance are unavailable. This is a completed bounded cash/
funding analysis with limitations, not a complete current twelve-month assessment.

## Calculations

The unchanged CP-2D pure Decimal helpers operate on source display amounts.
The pre-production independent Fraction oracle agrees across164 numerical and
date-index checks. Same-host visibility of that oracle is disclosed; this is not
blind or independent-model assurance. Unknown accessible-capacity inputs remain
null; an actual Gap-propagation check distinguishes them from a supplied zero.

### Source rounding reconciliation — no plugs

| Test | Sum / calculation on displayed cells | Source displayed total / balance | Difference or interpretation |
|---|---|---|---|
| Weekly receipts | 409 | 407 | Source total minus displayed sum = negative2 USDm. |
| Weekly total disbursements | 524 | 527 | Source total minus displayed sum = positive3 USDm. |
| Weekly reported net flow | Sum negative119 | Negative119 | Sum matches; total receipts407 less disbursements527 gives negative120, one lower. |
| Weekly net financing | Gross215 less repayments133 =82 | 82 | Exact at displayed precision; peak balance120 is a different quantity. |
| Weekly known cash bridge | 47 −119 +82 =10 | 10 | Cash equations match; receipt/disbursement detail is not silently rewritten to force them. |
| Cash-loan balance roll-forward | Recomputed57/66/83/57/62 in affected weeks | Source58/67/84/58/63 | Source minus recomputed cumulative balance =positive1 in those weeks; retain both. |
| Monthly/stub net cash and financing | Negative336 and positive249 | Negative336 and positive249 | With the distinct opening97, ending cash is10. |
| Conditional LC-adjusted cash capacity | (483010655.62 −82871057.00 −150139598.62) /1000000 −31 | 219 USDm | Exact legal amount conversion, conditional exposure assumptions. |
| Conditional budget-target funding gap | 249 −219 | 30 USDm | Alternative capacity case, not an asserted actual liquidity shortfall. |
| Final nominal liquidity diagnostic | 10 +1 =11; 11 −35 =negative24 | Contract daily floor35 | Point-in-time source-budget diagnostic; no formal historical breach claim. |
| Final LC-adjusted diagnostic | 10 +1 −31 =negative20; less35 =negative55 | Conditional same-pool assumptions | Infeasible unchanged case; not negative certified availability or an automatic draw. |

These discrepancies are consistent with independently rounded whole-million
cells; underlying unrounded figures are not retained, so that explanation is
not independently proved. They are logged rather than corrected, classified as
an issuer misstatement or hidden with a zero residual.

## Gaps

The T2E.9 restrictions and source-stage/date/scale/dash decisions remain attached
to every result. A filed initial discussion budget is real evidence for the
function exercised, not approved realized liquidity. There is no full-year cash
forecast, formal MTE, certified covenant result, assured refinancing, current
issuer conclusion, independent assurance or accepted native/controller pathway.
Full original-byte/source-pack coverage is unproven; located passages are retained.

## Next module

CP-3C must actually read and consume the first/peak funding dates and amounts,
the interim/final-order dependency, LC/roll-up capacity distinction, contract
liquidity tests, January stub/maturity and unresolved takeout. It must not present
the source closing10 as unconditional funding sufficiency, add roll-ups as new
cash, use January as a full month, infer a historical breach or supply a plug.
The separate delivery process then publishes the tables and substantive reasoning
from these handoffs using the existing HTML design; no analytical rerun or
workbook output is required. Full CP-OS/pathway completion remains open.
