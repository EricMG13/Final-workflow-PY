# CP-3 — historical LQD holdings: ARCC portfolio exposure and downside

## Request

Evaluate the portfolio-input, exposure, conditional-loss and monitoring functions
of absorbed CP-3B. Current host model, preceding context retained, 2026-11-04;
no subagents, provider calls, independent-context assurance or native acceptance.
**Full CP-3 security-selection gate remains blocked.** The prior market intake
has no completed preference, and the December2024 analytical context does not
become May2025 underwriting. Supported holdings calculations below are a bounded
functional result, not a completed security-selection or executable sizing run.

**Portfolio observation: 2025-05-31.** Historical, retrieved in November2026;
not current research or an information-availability backtest. The source's
2026-02-28 fiscal-year-end field is not the holdings date. Output mode:
**Generic Portfolio-Fit Logic with actual named-portfolio exposure**, not
mandate-specific sizing. Decision posture **Requires More Work**; portfolio role
**Watchlist / monitoring only**. Decision confidence **Insufficient Information**.
Imported numeric-confidence/envelope qualification is unexecuted, as frozen in
instructions; no all-runbook completion claim. No new position size was supplied.

## Sources

Pins are in inputs.json; raw primary sources and retrieval hashes are retained.

| Key | Source / exact locator | Permitted use / limitation |
| --- | --- | --- |
| N | [LQD NPORT-P XML](https://www.sec.gov/Archives/edgar/data/1100663/000175272425177725/primary_doc.xml), series S000004361; genInfo/repPdDate; fundInfo; invstOrSec ordinals 1-based | Dated fund-accounting holdings and matching NAV. USD values; PA balances are par. Not executable prices or current positions. Raw SHA256 7617ce8e9f605035939d57fdf019636510ba08d9cb2388d561be04d574bb11df |
| F | [SEC Form N-PORT](https://www.sec.gov/files/formn-port.pdf), effective December11 2023, General Instructions A/G, Items C.2 and C.12(c); PDF pages2,6,13,19 | pctVal is percentage of fund net assets, not decimal weight. On-loan value is part of an investment, not an additional holding. Current retrieved reference copy, not fund mandate |
| HM | ../arcc-market-2024-001/CP-3D-attempt-2.md and CP-3-market-consumer.md | December31 2024 evaluated prices and conditional pricing, incomplete selection gate. Not May2025 prices or liquidity |
| HL | ../arcc-lite-2024-001/ARCC_CP-L10_20261104-attempt-3.md | Historical BDC screening only; no full fundamental/mandate conclusion |
| H4 / H4A | ../arcc-2024-001/CP-4.md and CP-4A-attempt-1.md | Selected July2029 executed-note interpretation and historical statutory cushion; no 2025 current compliance or all-series coverage |
| M | Archived CP-3B_RUNBOOK.md, CP-3B_SCHEMA_REFERENCE.md, REF_CP-3B_STEPS.md; source hashes in inputs.json | Selected substantive nine-register/ten-step method, dates2026-06/07. Current project six-heading transport; full gate and confidence qualification explicitly unfulfilled |

The current iShares webpage is retained as retrieval context only. Its
November2026 NAV and vendor-valued holdings are not calculation inputs.

## Findings

### Portfolio view

LQD reported **33,773,000 USD par** of five ARCC notes at a combined
**33,762,233.40 USD value**, **0.109532894% of matching fund NAV**. This measures
the named issuer's held exposure; a small NAV share alone does not prove unused
capacity, diversification compliance or easy exit. Two notes maturing in2029
account for **17,698,117.83 USD**, **52.419866957% of this issuer holding's value**;
this is the fund's ARCC maturity grouping, not ARCC's total refinancing wall.

A purely conditional40%-of-par recovery assumption implies a20,253,033.40 USD
loss against the held market value, **6.570576451 fund-NAV basis points**. No fund
loss budget is supplied, so this is loss transmission, not risk-budget utilization
or an actual recovery forecast. The useful next step is to obtain same-date
selection/terms, mandate, trading and budget evidence, rather than turn held
amounts or historical evaluated values into a proposed trade.

### T3C.0 — Actual held-instrument evidence

| XML ordinal / CUSIP | ISIN | Maturity | Reported coupon % | Par USD | Value USD | Reported %NAV | Value on loan USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 888 / 04010LBK8 | US04010LBK89 | 2030-09-01 | 5.50000000 | 4430000.00000000 | 4393034.75000000 | 0.014252072815 | 0; source reports not on loan |
| 1453 / 04010LBB8 | US04010LBB80 | 2028-06-15 | 2.88000000 | 1347000.00000000 | 1256309.72000000 | 0.004075774180 | 0; source reports not on loan |
| 1780 / 04010LBG7 | US04010LBG77 | 2029-07-15 | 5.95000000 | 10247000.00000000 | 10424576.41000000 | 0.033819860419 | 1213674.21280000 |
| 2173 / 04010LBH5 | US04010LBH50 | 2032-03-08 | 5.80000000 | 10572000.00000000 | 10414771.10000000 | 0.033788049610 | 0; source reports not on loan |
| 2561 / 04010LBF9 | US04010LBF94 | 2029-03-01 | 5.88000000 | 7177000.00000000 | 7273541.42000000 | 0.023597136795 | 306062.35300000 |

N: each row has exact issuer LEI WEQ82666OJYSI5GUAB47, Long, DBT, USD,
fair-value level2, not restricted, default/interest-arrears/PIK flags N as of the
reported date. Those flags are neither a rating nor zero default probability.
Reported coupons2.880/5.880 are preserved; they do not replace the earlier
annual's2.875/5.875 contractual precision. No yield or coupon change is inferred.
On-loan values sum1,519,736.5658 USD and are not added to issuer value/par.

### T3C.1 — Portfolio Input Gate

| Input | Available / Missing | Source | Limitation | Portfolio Impact |
| --- | --- | --- | --- | --- |
| Security-selection/preference | Missing full gate; historical market intake available | HM,HL | No full matching fundamentals, preference, terms/convention or market liquidity at May2025 | Full selection/sizing blocked; numerical holdings work only |
| Holdings and denominator | Available for2025-05-31 | N genInfo; fundInfo/netAssets; five exact-LEI rows | Historical fund report, not current trade inventory | Compute held exposure with matching30823830378.19 USD NAV |
| Mandate and limits | Missing active dated guidelines/caps | N establishes holdings only | Holding a note does not prove mandate eligibility or remaining capacity | No mandate-specific posture or headroom |
| Proposed position / pro forma | Not supplied; null | Current request | No requested trade | No numeric new size or pro forma allocation |
| Liquidity / exit | Missing executable depth/bid-offer/settlement/recall evidence | N valuation/lending flags; HM historical evaluations | Fair-value level2 and on-loan status do not prove an executable exit | Liquidity and scaling restricted |
| Downside / loss budget | Conditional sensitivities available; actual budget/recovery missing | Calculations C4–C8; analyst assumptions | No PD, recovery timing, costs, waterfall or cap | Quantify conditional NAV loss, not budget usage |
| Legal / refinancing | Selected older July2029 evidence only | H4,H4A,N maturities | Other series and2025 amendments/uses unverified | No larger-size or current compliance conclusion |

### Inherited definition limits — unchanged upstream distinctions

| Upstream distinction | Exact constraint carried forward | Source |
| --- | --- | --- |
| Price basis | “Keep5.950% in security cash flows. Do not improve apparent carry by using the issuer's hedge-adjusted cost as the coupon.” | HM CP-3-market-consumer.md |
| Convention cases | “No new pricing calculation. The actual CP-3D numbers above are adopted with their source date, convention and case labels. No A/B averaging, conversion to an executable quote or new factual default probability.” | HM CP-3-market-consumer.md |
| Missing selection | “No composite score, intra-issuer preference or numeric portfolio sizing is assigned at this intake.” | HM CP-3-market-consumer.md |

No formal upstream Definition Conflict Register was supplied. These literal
limitations are inherited; no replacement debt reconciliation is fabricated.

### T3C.2 — Portfolio Fit Register

| Name / Instrument | Fit Category | Evidence | Risk Mechanic | Why It Fits / Does Not Fit | Constraints / Notes | Source Trace |
| --- | --- | --- | --- | --- | --- | --- |
| ARCC five-note held group | Not assessable | Actual0.109532894% NAV exposure, but mandate/budget absent | Held exposure consumes risk without proving capacity | Historical exposure is measurable; implementation fitness unresolved | Role Watchlist / monitoring only; no mandate approval | N; C1–C4; GAP001–006 |
| July2029 US04010LBG77 | Not assessable | 10424576.41 USD value; selected older legal/pricing work | Identity continuity allows targeted review; unlike dates invalidate current compensation claims | Positive source binding, no proved RV/liquidity fit | Selected5.950% noteholder coupon; no extrapolation to other series | N1780; HM,H4 |

### T3C.3 — Position Sizing Posture Table

| Name / Instrument | Sizing Posture | Evidence | Reason | Key Risk | Implementation Note | Confidence | Source Trace |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ARCC group and selected July2029 note | Requires More Work | Held exposure and conditional losses known; selection, caps, depth and loss budget unavailable | Missing required gates prevent a supported Core/Starter or maintain/trim decision | Unmeasured exit cost and capacity; dated legal/fundamental perimeter | Monitor / Escalate; no trade/new numeric size; existing amounts describe source facts only | Insufficient Information | T3C.1; T3C.5–7; GAP001–006 |

### T3C.4 — Risk Budget Flags

| Flag | Evidence | Risk Mechanic | Why It Matters | Caution Level | Portfolio Impact | Source Trace |
| --- | --- | --- | --- | --- | --- | --- |
| F1 Capacity unmeasured | No fund issuer/sector/rating caps or loss budget | Positive exposure can consume an unknown limit | Small percentage does not establish spare risk budget | Not Assessable | No compliance/headroom/addition claim | N; GAP002,005 |
| F2 Dated issuer maturity grouping | 52.419866957% of held ARCC value matures2029 | Same issuer and clustered maturities can share funding stress | Grouped fund exposure needs issuer refinancing analysis | Medium; analyst attention, not a breach | Monitor issuer maturity/funding evidence; no claimed issuer-wide wall | N1453/1780/2561; C3 |
| F3 Exit and lending | Two notes have part on loan; no depth or recall details | Sale availability and execution can differ from marked value | Valuation observation does not settle stressed exit | Not Assessable | Obtain recall/settlement and trade depth before implementation | N1780/2561; F C.12; GAP004 |
| F4 Conditional downside | 40%-par scenario loss6.570576451 NAVbp | Common issuer impairment transmits across all five notes | Different maturities do not diversify issuer loss | Medium; scenario attention, not likelihood | Compare scenario loss against actual budget only when supplied | C5; GAP005 |
| F5 Date / legal mismatch | December2024 analytical inputs vs May2025 holdings | Unchecked changes can invalidate compensation/protection assumptions | New2030/2032 positions cannot inherit selected2029 terms | High; evidence constraint | No current preference, legal clearance or Core/Starter | HM,H4,N; GAP001,006 |

### T3C.5 — Concentration and Correlation Register

| Exposure Dimension | Current Exposure | Proposed / Pro Forma Exposure | Limit / Capacity | Evidence Status | Risk Mechanic | Portfolio Implication | Source Trace |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Issuer/group | ARCC legal issuer33762233.40 USD value;0.109532894% NAV; wider group null | null; not supplied | null; not supplied | Source Fact / Calculation; group mapping Not Provided | Five notes share the same reported issuer LEI | Aggregate exact issuer; no unsupported affiliate/control netting | N five exact-LEI rows; C1,C2 |
| Sector/subsector | ARCC selected BDC context; full-fund sector total null | null | null | HL historical context; numeric mapping Not Provided | Financial-company assets/funding can share factors beyond this issuer | No sector capacity or diversified-sector assertion | HL; GAP003 |
| Sponsor/ownership | Ownership/control exposure null; two Ares Strategic Income Fund rows excluded | null | null | Not Provided; N records different issuer LEI549300IANZJVZPTICV54 | Similar brand/name alone does not define a controlled risk group | Obtain actual group mapping rather than sum substring matches | N887/2092; GAP003 |
| Rating bucket | null; no dated security-rating map | null | null | Not Provided | Migration and mandate eligibility depend on actual ratings/rules | Fund name/holdings are not security-specific rating proof | GAP002,003 |
| Maturity year/wall | 2028 value1256309.72;2029 value17698117.83;2030 value4393034.75;2032 value10414771.10 USD | null | null | Source Fact / Calculation | 2029 is52.419866957% of this issuer holding's value | Do not call this the whole fund or issuer debt maturity wall | N maturityDt; C3 |
| Capital-structure layer | All five reported DBT; only selected older July2029 legal work admitted | null | null | Source Fact; full layer mapping Not Provided | Claim priority/security may change loss exposure | DBT is debt category, not proof all five are equally unsecured/currently pari passu | N; H4; GAP006 |
| Correlated holdings/common factor | Same legal issuer across five notes; all USD fixed coupon; full-fund correlation null | null | null | Source Fact / Analyst Inference | Common issuer deterioration and rates can move notes together | Different maturities are not independent issuer-risk bets; no numeric correlation coefficient | N; GAP003 |

### T3C.6 — Liquidity and Implementation Assessment

| Liquidity / Implementation Factor | Evidence | Risk Mechanic | Implementation Consequence | Constraint / Action | Source Trace |
| --- | --- | --- | --- | --- | --- |
| Trading depth / bid-ask | No dealer/venue/volume inputs; N level2 valuations only | Marks can differ from sale proceeds and trade size | Exit risk not assessable; no cost/depth estimate | Obtain matching executable observations and size/depth | N; GAP004 |
| Settlement / minimum size / operations | July2029 and March2029 partly on loan; recall/settlement/minimum lots not supplied | Recall and settlement can constrain sale availability | Do not treat all holdings as immediately deliverable | Obtain current operations and governing series terms | N1780/2561; F C.12; GAP004,006 |
| Exit route under stress | No stress-depth or dealer capacity evidence | Common impairment may reduce liquidity while marks fall | Scenario losses exclude execution friction | Do not claim a feasible stress exit | GAP004,005 |
| Ability to add / trim | No user trade size, mandate capacity or executable depth | Scaling can change price impact and risk-budget usage | No addition/trim quantity or order instruction | Requires More Work; Monitor / Escalate | T3C.1,3; GAP002,004,005 |

### T3C.7 — Downside Budget and Recovery Sensitivity

| Downside Scenario / Driver | Input Basis | Formula / Method | Result / Directional View | Portfolio Loss / Risk-Budget Implication | Status | Source Trace |
| --- | --- | --- | --- | --- | --- | --- |
| Price downside, assumed−10% | Existing group value33762233.40 USD; analyst shock | loss=value×0.10; loss/NAV×10000 | loss3376223.34 USD;1.095328938 NAVbp | Conditional marked loss, not source-observed move or budget utilization | Calculated | N; C4; no liquidity/cost effect |
| Recovery40% of par | Existing group par33773000 USD; analyst assumption | proceeds=par×0.40; loss=held value−proceeds | proceeds13509200 USD;loss20253033.40 USD;6.570576451 NAVbp | Not PD, expected loss, default forecast or legally supported recovery | Calculated | N; C5; GAP005,006 |
| Recovery60% of par | Same held group, analyst alternative | proceeds=par×0.60; loss=held value−proceeds | proceeds20263800 USD;loss13498433.40 USD;4.379219985 NAVbp | Sensitivity to assumption only; no budget cap provided | Calculated | N; C6; GAP005 |
| Selected July2029 at40% par | N1780 par10247000 USD;value10424576.41 USD | proceeds=par×0.40; loss=value−proceeds | proceeds4098800 USD;loss6325776.41 USD;2.052235667 NAVbp | Component of group scenario, not an additional loss to sum again | Calculated | N1780; C7 |
| Refinancing / maturity-wall downside | Two held2029 notes; no full issuer2025 funding plan | Directional shared-issuer funding channel only | Deteriorating access could affect grouped exposure; loss null | Cannot quantify refinancing loss or forced-sale impact from a maturity list | Directional Only | N; F2; GAP001,006 |
| Legal / priming / leakage downside | Only selected older July2029 note reviewed | No matching all-series2025 legal/waterfall analysis | Incremental legal loss null; no permission/compliance inference | Do not map arbitrary recovery assumption to actual priority | Not Calculable | H4; F5; GAP006 |

### T3C.8 — Monitoring Triggers

| Trigger ID | Indicator | Leading / Lagging | Threshold or Qualitative Signal | Linked Risk Flag | Portfolio Action | Source Trace | Limitation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-3B-MON-001 | New holdings/NAV/limit publication | Lagging holdings; leading capacity check | Issuer amount/identity changes or dated limits become available | F1,F2 | Monitor / Escalate: recompute matching exposure and compare only with actual limits | N; C1–3; GAP002,003 | Quantitative threshold not available in provided materials. Historical position may no longer exist |
| CP-3B-MON-002 | Executable bid-offer, depth and lending recall | Leading implementation | Actual evidence shows friction or inability to deliver contemplated trade | F3 | Monitor / Escalate: obtain operations/depth before any implementation decision | N lending; T3C.6 | Quantitative threshold not available in provided materials. No implied trim quantity |
| CP-3B-MON-003 | Dated loss budget and matching downside evidence | Leading risk control | Supplied limit would be exceeded by recalculated supported scenario loss | F1,F4 | Monitor / Escalate: compare at matched date; refer decision to portfolio review | C4–7; GAP005 | Quantitative threshold not available in provided materials. Assumptions are not factual recovery |
| CP-3B-MON-004 | New issuer funding/legal/selection evidence | Leading credit review | New instrument, amended protection, funding stress or changed selection conclusion | F2,F5 | Monitor / Escalate: targeted CP-3/CP-4 update, then affected portfolio calculation | HM,H4,N; GAP001,006 | Quantitative threshold not available in provided materials. No automatic trade |

### Overall portfolio fit view

Overall, ARCC's five reported LQD holdings are **Requires More Work** for
portfolio implementation. The sizing posture is driven by real held exposure
and measurable conditional losses alongside missing same-date selection,
mandate, depth and loss-budget evidence. Those gaps matter because known
marked value does not establish executable proceeds or available risk capacity.
The2029 grouping and common issuer risk merit monitoring; the top next action
is matching holdings/limits and implementation evidence, not a numeric addition.
CP-3B full gate remains blocked. The scoped holdings/exposure/sensitivity
functions are completed with limitations; no full CP-3B or CP-3 pass is asserted.

## Calculations

All amounts below are USD, not USDm. Exact Decimal source arithmetic, independent
pre-answer literal/Fraction checks in expectations.json. Percentage results are
rounded to nine decimal places only after division; NAVbp means loss/NAV×10000.
Fund netAssets=30,823,830,378.19 USD. Total assets34,826,064,750.43 less
liabilities4,002,234,372.24 equals that NAV; NAV is not summed debt holdings or
par. No portfolio-wide normalization, VaR or modeled correlation is performed.

| ID | Calculation / basis | Result | Definition / limit |
| --- | --- | --- | --- |
| C1 | Sum par five exact-LEI nodes; sum valUSD same nodes | par33773000 USD;value33762233.40 USD | Ares Strategic Income Fund excluded; lending not added again |
| C2 | 33762233.40 /30823830378.19×100 | 0.109532894% NAV | Source pctVal sum0.109532893819%; difference is reporting/rounding precision, not another exposure |
| C3 | 10424576.41+7273541.42; result/33762233.40×100 | 17698117.83 USD;52.419866957% of issuer holding value | Dated2029-held maturity subset; not whole issuer obligations |
| C4 | 33762233.40×0.10; loss/NAV×10000 | 3376223.34 USD loss;1.095328938 NAVbp | Analyst price shock, not historical movement |
| C5 | 33773000×0.40;33762233.40−13509200;loss/NAV×10000 | 13509200 USD proceeds;20253033.40 USD loss;6.570576451 NAVbp | Hypothetical recovery of par; no interest/cost/timing/default prediction |
| C6 | 33773000×0.60;33762233.40−20263800;loss/NAV×10000 | 20263800 USD proceeds;13498433.40 USD loss;4.379219985 NAVbp | Alternative assumption, not a more likely scenario |
| C7 | 10247000×0.40;10424576.41−4098800;loss/NAV×10000 | 4098800 USD proceeds;6325776.41 USD loss;2.052235667 NAVbp | Already inside C5; not additive to it |
| C8 | 10424576.41/NAV×100;1213674.2128+306062.353 | 0.033819860% NAV selected note;1519736.5658 USD group value on loan | Lending is an operational subset, not a new asset or loss |

No numeric proposed size, pro forma allocation, permitted headroom or percentage
of risk budget is calculated: all are null, not zero. No December2024 conditional
yield shock is reused as a May2025 price move. NPORT values are fund-accounting
observations, with no clean/dirty execution convention asserted here.

## Gaps

### T3C.9 — Gaps Ledger

| Gap ID | Missing Data | Why It Matters | Affected Sizing / Risk Budget / Trigger | Consequence for Confidence | Required Follow-Up Source |
| --- | --- | --- | --- | --- | --- |
| CP-3B-GAP-001 | Matching full fundamentals, security preference and market conventions | Old intake is not completed May2025 security selection | Full CP-3B input gate; MON004 | High impact; implementation unresolved | Same-date full issuer/security analysis and observed market basis |
| CP-3B-GAP-002 | Dated LQD mandate/issuer-sector-rating caps and any proposed trade | Holdings alone do not establish eligibility or capacity | All new sizing/pro forma/headroom; MON001 | High impact; no Core/Starter or numeric new size | Dated actual fund guidelines and requested trade, if any |
| CP-3B-GAP-003 | Whole-fund sector/rating/control/layer/correlation mapping | Five notes do not prove portfolio diversification or capacity | Concentration dimensions; MON001 | High impact to capacity view | Matching whole-portfolio mapping with definitions and relevant limits |
| CP-3B-GAP-004 | Executable depth/bid-offer, settlement/minimum lots and recall/stress exit | Marked amount may not equal accessible sale proceeds | Exit/scaling; MON002 | High impact; liquidity not assessable | Dated dealer/venue/operations evidence at actual contemplated size |
| CP-3B-GAP-005 | Actual loss budget, matching recovery/PD/timing/cost/downside support | Conditional arithmetic is not expected loss or risk-budget utilization | T3C.7; MON003 | High impact to budget conclusion | Portfolio risk policy and issuer/security-specific stress/waterfall evidence |
| CP-3B-GAP-006 | Complete2025 series terms, amendments, issuer funding/maturity uses and legal priority | Earlier selected-note work cannot clear other/current claims | Legal/refinancing sizing; MON004 | High impact; no current compliance/recovery conclusion | Governing dated documents, debt inventory and funded uses/access bridge |

Numeric-confidence/envelope and native runtime qualification remain unexecuted;
this is a scope limitation, not an invitation to fabricate a score or accepted head.

## Next module

CP-6 portfolio intake should consume the checked exact exposure,2029 subset,
conditional USD/NAVbp losses and implementation restrictions. It must not convert
an observed holding into approval to maintain/add or describe this as completed
full security selection. Confirm that the July2029 scenario is a component of the
group loss and that loaned securities are not double counted. Separate delivery
then copies this checked handoff and that actual consumption into the existing
Workflow HTML report design, with historical date/gaps visible. No second
analytical execution, Excel output or whole-pathway completion is required or
claimed by that presentation step.
