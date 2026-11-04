# CP-2E — TDG macro, hedging and absorbed ESG credit review

## Request

Assess interest-rate, FX, cost and ESG transmission to credit from the actual
FY2024 source and checked handoffs, including CP-2F's broader responsibilities.
Base balances are September 30, 2024; annual flows are October 1, 2023–September
30, 2024. USD millions unless noted. Derivative dates that were future at that
base remain historical scenarios; their subsequent outcomes have not been checked.
This is actual current-host-model analysis with local tools and conversation
context, not provider/API or imported owner execution.

**View: documented rate mitigation with dated protection changes; complete
macro-risk classification remains Insufficient Information.** The issuer reports
approximately 30 additional annual interest cost for a one-percentage-point rate
increase and approximately 77% fixed-rate gross debt. These are attributed
disclosures, not independently rebuilt net hedge results. Missing effective
exposure/FX/cost inputs prevent a calibrated overall sensitivity.

**ESG credit view:** remediation liabilities are a quantified historical
obligation with estimate uncertainty. Additional material deterioration is not
demonstrated. Environmental/physical/safety and transition channels warrant
specific monitoring; no ESG score, assumed greenium or invented debt ratchet is
assigned. Confidence is Medium for the bounded source interpretation.

## Sources

Actually opened CP-0, annual/quarterly CP-1, CP-1A, CP-1B, CP-1D, CP-2 and
CP-2D handoffs. Their exact paths/hashes are in
`CP-2E-attempt-1-calculations.json`. CP-1 supplies financial definitions and
facility data; CP-1A supplies business/governance context; CP-2/CP-1D supply
cash-conversion and recurring-cost reasoning; CP-2D supplies the actual quarterly
cash bridge and the access/forecast limits. None is replaced by memory or a fixture.

Original annual PDF SHA-256:
`dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`.
Short exact source excerpts and one-based PDF pages are retained in the
calculation record. Pages 151 (hedge terms) and 139 (remediation liabilities)
were rendered and visually checked; source images/hashes are retained.

Method selection: Deploy V-derived CP-2E and absorbed CP-2F analytical breadth
in the skill and its two method companions; later `src/deploy_vii/methods/cp2e.md`
and unchanged pure helpers provide applicable precision/missingness checks.
Hashes are retained in the calculation record. The descriptive T2F/T2G meanings
below follow the broader method, not the later runtime's different T2F mapping.
Historical quote limits and transport do not dictate source arithmetic or allow
facts to be relabelled to fit a synthetic example.

## Findings

### T2F.1 — source gate and evidence map

| Evidence | Source / date | Data and quality | Limitation / use |
|---|---|---|---|
| R | Annual PDF 54–55 / 2024-09-30 | Market-risk balances, reported rate/FX sensitivities; issuer disclosure | Reported sensitivities are not independently reconstructed scenarios. |
| H | PDF 150–152 / 2024-09-30 | Derivative programme, dated notional/strike schedules, hedge accounting and FX contracts | No full settlement/exposure attribution or independent legal review. |
| D | CP-1 debt register / 2024-09-30 | Principal, carrying amounts, terms and dates | Reporting amounts do not establish every debt/EBITDA functional currency. |
| O | PDF 17–19, 22–23 | Raw material, labour/production, physical, safety and transition risks | Risk disclosures identify mechanisms; they do not prove an event occurred or quantify elasticity. |
| E | PDF 139 / 2024-09-30 | Recorded environmental liabilities and estimate policy | Book liability is not future cash timing or an incremental stress loss. |

### T2F.2 — debt and rate exposure register

| Instrument | Principal / status | Rate basis / margin or coupon | Contractual maturity | Source / credit meaning |
|---|---:|---|---|---|
| Tranche I | 1,871 | Floating, Term SOFR +2.75% alternative | 2028-08-24 | D; benchmark/floor/election and reset terms needed for exact shock. |
| Tranche J | 3,632 | Floating, Term SOFR +2.50% alternative | 2031-02-28 | D. |
| Tranche K | 1,699 | Floating, Term SOFR +2.75% alternative | 2030-03-22 | D. |
| Tranche L | 1,500 | Floating, Term SOFR +2.50% alternative | 2032-01-19 | D. |
| Securitization | Gross 487 / carrying 486 | Floating, three-month Term SOFR +1.45% | 2025-07-11 | R/H/D; collateral and extension terms matter. |
| 5.50% subordinated notes | 2,650 | Fixed 5.50% | 2027-11-15 | D; benchmark shock does not directly reprice contractual fixed coupon. |
| 6.75% secured notes | 2,100 | Fixed 6.75% | 2028-08-15 | D. |
| 4.625% subordinated notes | 1,200 | Fixed 4.625% | 2029-01-15 | D. |
| 6.375% secured notes | 2,750 | Fixed 6.375% | 2029-03-01 | D. |
| 4.875% subordinated notes | 750 | Fixed 4.875% | 2029-05-01 | D. |
| 6.875% secured notes | 1,450 | Fixed 6.875% | 2030-12-15 | D. |
| 7.125% secured notes | 1,000 | Fixed 7.125% | 2031-12-01 | D. |
| 6.625% secured notes | 2,200 | Fixed 6.625% | 2032-03-01 | D. |
| 6.00% secured notes | 1,500 | Fixed 6.00% | 2033-01-15 | D. |
| Revolver | Commitment 910; available 843; LC 67; funded draw not established | Floating draw terms; unused commitment is not a funded balance | 2029-02-27 | D; no funded amount of 67 is inferred. |
| Government advances / finance leases | 17 / 262 in debt note | Conditional repayment / lease obligations, not automatically SOFR exposure | Different terms; no single rate maturity imposed | D; do not classify all remaining debt as fixed or unhedged. |

Amounts are USD reporting equivalents. Contractual currency, functional earnings,
cash and covenant currencies are separate facts; complete mismatch analysis is
not inferred from a USD presentation column.

### T2F.3 — hedge schedule and coverage distinctions

| Instrument | Notional | Effective / maturity | Disclosed reference terms | Coverage / limitation |
|---|---:|---|---|---|
| Swap | 500 | 2023-03-31 / 2025-03-31 | Reference fixed 3.00%; source illustrates 6.25% including then-stated 3.25% margin | H PDF 151; do not substitute the illustrated margin for current loan pricing. |
| Swap | 1,500 | 2023-03-31 / 2025-03-31 | Reference fixed 3.10%; source all-in illustration 6.35% | Same limitation. |
| Swap | 700 | 2023-03-31 / 2025-09-30 | Reference fixed 1.30%; source all-in illustration 4.55% | Same limitation. |
| Cap | 700 | 2023-03-31 / 2025-09-30 | Offsets three-month Term SOFR above 1.25% | Protection depends on exposure linkage/strike/reset; not a flat hedge ratio. |
| Collar | 1,100 | 2025-03-31 / 2026-09-30 | Floor 2.00%, ceiling 3.50% | Forward starting at September base; not current protection before start. |
| Collar | 500 | 2025-09-30 / 2026-09-30 | Floor 2.00%, ceiling 3.50% | Forward starting. |
| Collar | 1,338 | 2025-09-30 / 2027-09-30 | Floor 2.50%, ceiling 4.50% | Forward starting. |
| Collar | 1,550 | 2026-09-30 / 2027-09-30 | Floor 2.50%, ceiling 4.50% | Forward starting. |
| FX forwards | 120 USD-equivalent | Maximum duration twelve months from 2024-09-30 | Sell USD; Canadian dollar/euro contracts at trade-date spot equivalents | H PDF 152; currency transactions differ from all translated earnings. |

Active swap notionals sum to 2,700. Cap notional remains separately identified;
forward collars are not added to active coverage. No assumption that all
notionals cover distinct principal, or that accounting hedge effectiveness means
perfect economic protection. The company says derivative cash flows enter OCF,
and describes counterparty and credit-agreement-linked acceleration provisions
(PDF 150–151). Those are disclosed risks, not independent contract interpretation.
Derivative fair values are not protected debt principal.

### T2F.4 — baseline exposure and reconciliation limits

| Measure | Amount / status | Basis and creditor meaning |
|---|---|---|
| Identified floating principal | 9,189 | Calculated 8,702 term loans +487 securitization. Gross funded exposure before protection; no invented revolver draw. |
| Gross debt classification total | 25,068 | 24,581 debt-note gross items +487 separate securitization; distinct from carrying total 24,880. |
| Reported fixed-rate share | Approximately 77% | R PDF 55; attributed issuer classification, not 77% of floating debt. |
| Qualified hedged/unhedged floating exposure | Not Calculable from this review | Effective exposure attribution, floors/reference/reset dates, cap/collar overlap and relevant period need a complete reconstruction. |
| Unhedged percentage of total debt | Not Calculable | Neither a residual from 77% nor a ratio mixing principal and carrying amounts is substituted. |

### T2F.5 — rate sensitivity and conditional illustration

| Case | Result | Status / assumptions and limits |
|---|---|---|
| Issuer one-percentage-point rate increase | Approximately +30 annual interest cost | Reported R PDF 55 on outstanding September borrowings. Retained as issuer estimate, not independent after-hedge validation. |
| Gross principal ×1% arithmetic control | 91.89 = 9,189 ×0.01 | Arithmetic only. Not a qualified cash/net sensitivity: floor, reset, hedge and period details are unresolved. Difference from 30 is not forced into an invented hedge ratio. |
| Independent effective unhedged +100 bp impact | Not Calculable | Requires the effective unhedged base and schedule; a known source benchmark does not replace missing reconstruction inputs. |
| Conditional use of reported approximately-30 estimate | Approximately 1,188 cash interest; approximately 1,850 OCF-minus-capex proxy; approximately 3.51x As Defined / cash interest | Analyst illustration only: treat 30 as incremental annual cash interest, add once to FY2024 cash interest 1,158 and subtract once from proxy 1,880; hold all other flows/earnings fixed, no tax/WC feedback. Not a forecast, covenant ratio, true FCF or runway. |

The single-facility pure legacy calculation was actually called with the term-
loan balance 8,702, unknown floor/hedge ratio and missing FX EBITDA share. It
correctly returned missing rate/FX outcomes for those missing inputs. Its narrow
quote step cannot accept a balance of this magnitude under the documented 999.9999
limit; no unit rescaling, fake zero floor or source truncation was used to pass it.
The assumed 30 remains approximate; exact conditional arithmetic does not add
economic precision to the source estimate.

### T2F.6 — FX and natural-offset register

| Exposure | Source evidence / currency distinction | Mechanism and limitation |
|---|---|---|
| Revenue/operating translation | R PDF 55: foreign subsidiaries, primarily GBP/euro; consolidated reporting USD | Translation can change USD revenue/profit/assets without an identical cash impact. No currency EBITDA share is supplied. |
| Transaction exposure | H PDF 152: purchases/sales and USD-selling forwards for CAD/euro | Cash exposure depends on transaction currency, timing and offsets; the forward notional is not all foreign sales. |
| Geographic sales | O PDF 19: approximately 2.9 billion sales to foreign customers | Customer geography is not invoicing currency, foreign EBITDA share or a hedgeable net exposure base. |
| Natural hedges | Foreign revenues/costs and balances may offset; complete split not supplied | Partial offsets cannot be sized from geography. No numerical net exposure assumed. |
| Reported FX sensitivity | R PDF 55: a 10% FX change would not materially affect FY2024 net income | Attributed issuer conclusion; not zero, not EBITDA/debt sensitivity, and not proof of future protection. |
| Debt/cash/covenant and repatriation mismatch | Full denomination, functional-currency, location/access and covenant maps not supplied | Numeric debt/EBITDA/cash mismatch remains missing. No reporting-currency shortcut. |

### T2F.7 — raw materials, inflation and pass-through

| Driver | Evidence | Mechanism / creditor implication | Quantification and follow-up |
|---|---|---|---|
| Material/component cost or supply | O PDF 17–18: supplier disruptions, cost rises and certification constraints can impede replacement | Higher costs or interrupted output reduce margins/cash; inventory/qualification lags can absorb liquidity. | No spend volumes, cost elasticity or contractual indexation; no invented percentage shock. |
| Wages/labour/production | O PDF 17/19: skilled personnel, labour disagreements and supply-chain cost risks | Costs and delayed deliveries can weaken cash conversion, including customer OEM output effects. | Missing wage share, contractual recovery and timing. |
| Energy/freight/tariffs | O PDF 19: energy, transport and tariff-related supply/cost channels | Cost and availability shifts can raise cash demands and impair delivery; not all are commodity-price exposures. | No sourced cash-cost coefficients or hedge volumes. |
| Pass-through | O PDF 17 explicitly conditions impact on inability to pass increases to customers; CP-1A describes proprietary products | Proprietary content is a possible counterweight, not proof of price recovery without lag or demand effects. | Obtain contracts, realised price/cost bridge and timing before sizing net impact. |

### T2F.8 — macro synthesis and monitoring

| Driver | Transmission / contrary evidence | Dated condition or monitoring need |
|---|---|---|
| Rate/hedge changes | More unprotected repricing can consume cash; fixed coupons and disclosed derivatives mitigate selected exposure | At the historical base, 2025-03-31 and 2025-09-30 swap/cap expiries and collar starts change protection. Verify actual subsequent renewals/settlements rather than call them upcoming today. |
| FX | Transaction/translation mix affects different metrics; issuer reports nonmaterial historical NI sensitivity | Obtain actual currency bridge and offsets, especially GBP versus CAD/euro hedge coverage. |
| Cost/demand interaction | Cost pressure combined with aviation-demand weakness can impair conversion; proprietary/aftermarket demand may help recovery | Actual price/cost, inventory, output, cash-interest and hedge-settlement evidence must test this chain. |
| Liquidity/refinancing | Additional cash interest or operating pressure competes with distributions and obligations | Preserve CP-2D's dated cash/access gaps and historical July 2025 securitization expiry; no actual renewal/default inference. |

### T2F.9 — macro gaps

| Gap | Consequence | Targeted evidence |
|---|---|---|
| Full effective rate/hedge exposure map | Independent net +100 bp cash effect and hedge ratio unavailable | Facility rate/floor/reset/election, covered principal, strike/basis/overlap and cash-settlement schedule; reconcile issuer 30 benchmark. |
| Currency split and natural offsets | No quantitative FX debt/EBITDA/cash or covenant mismatch | Currency-level revenues/costs/earnings/debt/cash and forward-linked transactions. |
| Input costs and recovery | No calibrated commodity/inflation/FCF sensitivity | Volumes/spend, contractual pass-through, actual recovery lags and operating assumptions. |
| Current/future access and events | No current liquidity, refi result or cash forecast | Updated access/covenant package, hedge/facility outcomes and cash-use forecast. |

### T2G.1 — ESG source reliability and gate

| Source | Reliability | Disclosure-risk assessment | Phase status |
|---|---|---|
| E PDF 139 / annual statements | Recorded financial liabilities; financial-statement audit context | Estimate uncertainty remains; this is not assurance of an emissions target or future remediation outturn. | Source available for identified obligations. |
| O PDF 17–19/22–23 | Issuer risk/management disclosure | Target and mitigation claims remain attributed; no evidence of greenwashing is asserted from missing assurance alone. | Partial credit transmission review possible. |
| Sustainability-linked instruments / assurance | No operative SLL/SLB KPI/SPT/ratchet document or independent emissions assurance reviewed | Cannot confirm absence, a zero ratchet or verified progress. | Specific mechanics remain unavailable, not assumed Not Applicable. |

### T2G.2 — environmental and transition exposure

| Exposure | Evidence/date | Transmission and affected driver |
|---|---|---|
| Remediation obligations | E PDF 139: current 5 and non-current 36 at 2024-09-30; prior 3/41 | Actual recorded obligation 41 versus prior 44; timing/estimate changes can affect cash. Decline in accrual is not proof of cash paid or lower future cost. |
| Transition regulation / customer demand | O PDF 18: compliance-cost and air-travel regulation channels | Direct/supplier cost and aviation-demand exposure; no quantified regulatory stress or new law is invented. |
| Physical facility exposure | O PDF 18: storms, fires, sea-level/water issues at some facilities | Asset damage/output interruption and uninsured costs can reduce cash; site-level vulnerability and insurance recovery unknown. |
| Emissions target | O PDF 18: at least 50% absolute Scope 1/2 reduction by 2031 versus FY2019; issuer says direct emissions relatively low | Target is not achieved performance or a debt covenant. Costs, baseline tonnes and independently verified progress not supplied. |

### T2G.3 — social and operational exposure

| Exposure | Evidence | Credit channel / status |
|---|---|---|
| Product failure / safety | O PDF 22–23: injury/product liability, insurance limits and customer reputation | Event-risk: liability, interruption or lost approvals/orders could impair cash; no actual new crash/event is asserted. |
| Labour/key skills and supply continuity | O PDF 17/19: personnel, labour disputes and raw-material availability | Ongoing/event-risk: wage costs, qualification/delivery delays and customer output changes. No strike forecast or quantified loss. |
| Regulatory/litigation/permit issues | O PDF 22 and E PDF 139 | Defence/legal costs, remediation and operating restrictions can affect cash; legal merits/outcomes unreviewed. |
| Governance/financial policy | Refer to actual CP-1A and CP-1D/CP-2 reasoning | No duplicate sponsor/governance score or invented owner identity. |

### T2G.4 — credit materiality before inference

| Factor | Classification | Basis / catalyst |
|---|---|---|
| Remediation | Watch, with quantified baseline obligation 41 | Existing liability and estimate uncertainty are real; material incremental deterioration is not established. Trigger: revised cost/scope/payment demand or failed third-party contribution. |
| Product safety / operating continuity | Watch | Issuer-specific product/approval and liability mechanism; trigger: actual failure, recall, claim, regulatory restriction or sustained disruption. |
| Physical/transition exposure | Watch | Documented operational/customer channels; trigger: site event, funded compliance plan or binding regulation with quantified cash effect. |
| Target achievement / disclosure quality | Insufficient Information for progress/cost assessment | No baseline/progress/assurance metrics supplied. Do not infer fraud or a credit penalty. |
| Sustainability pricing / greenium | Insufficient Information | No operative ratchet or source-backed investor-pricing evidence. No spread benefit/cost is assigned. |

### T2G.5 — sustainability-linked instrument mechanics

| Instrument / KPI / SPT | Ratchet, test date and symmetry | Credit/pricing conclusion |
|---|---|---|
| No operative sustainability-linked terms reviewed | Unresolved; no bps value or verification term substituted | The corporate 2031 emissions target is not evidence of a loan/bond margin ratchet. Obtain actual terms before assessing size, direction, symmetry or covenant effect. |

### T2G.6 — refinancing and cost-of-capital linkage

| Effect | Direction / quantification | Funding relevance / limitation |
|---|---|---|
| Remediation or operating cash needs | Potential cash use, quantified baseline liability but unknown timing/stress | Can compete with liquidity and debt-service/refinancing needs; not proof of restricted access or a funding shortfall. |
| Mandate exclusions or sustainability premium | Not established for this issuer's instruments | No investor-flow/quote/agency evidence supplied; generic ESG narratives do not create a spread estimate. |
| Historical maturity exposure | July 2025 facility and FY2028–FY2029 concentration remain from CP-1 | Link operating/funding questions to actual dates; do not infer later outcomes or an ESG-caused refinancing result. |

### T2G.7 — ESG credit synthesis and counterevidence

| Priority factor | Evidence → cash mechanism → implication | Confidence / contrary evidence |
|---|---|---|
| Remediation estimates and cash timing | Recorded obligations 41 and uncertain scope/allocations → possible cash/earnings revisions → a cash-buffer monitoring question after distributions | Medium, bounded. Company states excess costs are not expected to materially harm its position/results on available information; this counterevidence is retained, not replaced by a stress loss. |
| Safety/operating continuity | Product/approval dependence and potential uninsured claims → interruption/liability/cash pressure → creditor monitoring | Medium for the mechanism, not probability. No new realised event, loss or PD/LGD estimate established. |
| Climate/target | Issuer low-direct-emissions claim and air-travel/supplier exposure → possible indirect demand/cost/capex channel | Scope/quantum uncertain. Do not convert a target or reputation claim into funded protection or demonstrated earnings effect. |

### T2G.8 — ESG gaps

| Gap | Affected conclusion | Follow-up |
|---|---|---|
| Site-level remediation scope, allocations, payment timing and recoveries | Incremental cash sensitivity, not the known 41 liability | Obtain obligation roll-forward, funded plan and changes in estimates. |
| Physical/transition cost and emissions evidence | Materiality/target progress and funded mitigation | Obtain site risks/insurance, actual capex/operating plan, baseline emissions and verified progress. |
| Sustainability-linked terms and market evidence | Ratchet/greenium/refinancing-access assessment | Obtain operative documents, KPI/SPT/test dates, verification and source-backed pricing/investor evidence. |
| Safety/labour/operational event detail | Actual loss, interruption and remediation assessment | Obtain event-specific disclosure when a trigger occurs; no event or loss is invented. |

### Overall credit implication and CP-6 question

The macro downside is an adverse rate/reset or cost/demand move that reduces
cash conversion just as historical protection changes and obligations/distributions
compete for funds. Fixed coupons, derivatives, positive operating cash and
potential price recovery are real counterweights; their future adequacy is not
proved by notionals, source estimates or a qualitative business description.

The single best-supported CP-2F debate question is whether remediation estimate/
payment uncertainty could materially consume the post-distribution cash buffer.
The recorded liability supplies an actual baseline; it does not prove an
incremental loss, imminent funding call, default or recovery impairment. Current
cash-access and revised remediation evidence would strengthen or weaken that
concern. CP-6 should preserve the issuer's contrary cost expectation and avoid
an ESG-values judgement.

## Calculations

The calculation record retains all consumed hashes, selected revisions, exact
located source excerpts, visual-source identities, actual legacy output and
independent integer/Fraction checks. Existing Decimal arithmetic verifies the
9,189 principal sum, gross total 25,068, 2,700 active swap notional, arithmetic
91.89 bps control, conditional approximately-30 illustration, and environmental
totals 41/44. It does not independently reconstruct the issuer sensitivity.
Unknown effective unhedged balance, floor, FX EBITDA share and sustainability
ratchet remain null. No provider run or new production code occurred.

## Gaps

All T2F.9/T2G.8 and inherited source, date, fiscal-comparability, access, forecast,
legal and financial-definition limits remain. Alias routing CP-2F → CP-2E was
executed, and the broader ESG responsibilities were actually considered. Neither
routing nor populated registers prove complete quantum or full module coverage.
No current macroeconomic conditions, regulations or realised 2025/2026 outcomes
were inferred from this historical filing.

## Next module

CP-2 should consume the reported-versus-reconstructed rate distinction, timing
of protection, cash/FX/cost gaps and the actual remediation evidence. CP-2G needs
dated forecast assumptions rather than a flat unsupported hedge ratio; CP-3C
needs actual refinancing/access evidence. CP-6 should use the specific debate
question above with contrary evidence. CP-1E feedback: annual PDF 139 expressly
states no preferred shares outstanding at September 2024/2023; do not infer that
all hybrid/other claims are absent. Delivery may publish the checked historical
analysis and conditional illustration with their scope; actual deliverables
replace CP-MEMO. Downstream consumption remains required for this bounded loop.
