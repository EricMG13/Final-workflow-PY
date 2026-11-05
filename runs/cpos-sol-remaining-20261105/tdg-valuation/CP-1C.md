## Request

Valuation view: TDG (TransDigm Group Incorporated), as of 2025-09-30; historical execution 2026-11-05. Run `sol-remaining-tdg-valuation-20261105`, CP-1C, method version `deploy-v-r14`, public relative-value pathway. This is fresh provider-authored analysis of retained FY2025 primary captures and the supplied limited CP-1 valuation-input increment—not new web discovery, current underwriting, or a full CP-1 execution. Moog is the specified candidate; no FY2024 financial values are imported.

The deliverable establishes dated known-component arithmetic and two conditional individual-peer indications. It does not establish complete enterprise value, normalized comparable valuation, a sector distribution, recovery, debt coverage, a target price, or current security preference. Status: restricted historical valuation context; ready only for qualified consumption.

## Sources

Citation keys below identify the supplied captures and handoff, not original-file byte equivalence. All five pinned captures were read in full, as was the actual CP-1 Markdown supplied under its hash.

| Key | Source / pin | Pages and use |
|---|---|---|
| F | `filing-captures`, SHA256 `b81f0bc9b1c467086fc7a4c81f1bb40b8b0ae1198fa70b0b17c344902492d331` | pp1–8; Moog FY2025 10-K and TDG FY2025 10-K retained SEC passages |
| R | `receivables-supplement`, SHA256 `2bb2817184e33a56159d14de6c0719425a9f9f77663674a85bcac3ffa2ada467` | pp1–2; RPA, acquisition/perimeter, working capital and fixed assets |
| C | `retained-calculations`, SHA256 `f08e324d1c3b60ddd64459d264d18d4eabd8fb1fc626007e7b74f443d8e6be8d` | p1; existing Decimal-38 arithmetic, exact outputs, six-place display and missingness |
| M | `peer-method`, SHA256 `4bd3b130ce0b49571f7b4b97da25a42a81dbed80b03ea752552ea8ae90cd9f71` | pp1–3; selected method, consolidated register columns |
| S | `peer-steps`, SHA256 `fbbed9bac006c67a04397303c39c684046817cf491ebad6a4fa1302ecfbfd766` | pp1–3; steps 6A–6C, 16 dimensions, alignment, valuation and small-sample safeguards |
| P | Supplied actual CP-1 handoff, SHA256 `2d88e82cea96c83108b53a86dafa27056f35098c786419d25dba0280fe0735df` | FY2025 dated valuation-input increment, read-through dated 2026-11-04; limited located operands, not full acceptance |

F captures originate from Moog's `mog-20250927.htm` (SEC accession `000162828025054103`) and TDG's `tdg-20250930.htm` (SEC accession `000126022125000081`). P records failed direct downloads and selected browser passages, not comprehensive extraction. Embedded “today” labels belong to those retained captures, not this execution. No visual inspection or new exchange-tape verification is claimed.

M/S are the supplied selected method/REF evidence associated with the requested cp-os `b57a344` ancestry; this is not an independently inspected repository checkout. Current six-section, retained-arithmetic and missingness instructions govern over historical full-run/export language. Where M and S present different register layouts, the consolidated selected-method columns in M p1 are used below.

## Findings

### Valuation conclusion and strongest countercase

Moog's dated common equity is USD6,483.777030m. Adding borrowing principal and finance leases and deducting reported non-restricted cash produces a **known-components EV proxy of USD7,501.839030m**, not complete EV. Its individual proxy multiples are **1.943167x FY2025 revenue** and **15.358427x the precisely defined pretax-plus-interest-plus-D&A proxy**. Applying these separately to TDG FY2025 revenue and ordinary EBITDA produces **USD17,160.112063m** and **USD70,157.294567m**, respectively [F pp1–8; C p1]. These are conditional enterprise-value-context indications, not endpoints of a valuation range.

The large difference is economically informative, not competing arithmetic: Moog's proxy EBITDA/revenue is 12.652126%, versus TDG ordinary EBITDA/revenue of 51.726871% (new tool ratios; trace below). A revenue multiple imports Moog's lower earnings per sales dollar; an EBITDA multiple scales TDG's much higher reported earnings base. Different commercial/defense/industrial exposure, margins and earnings definitions prevent treating either result as normalized fair value. TDG reports 60.1% gross margin; Moog reports 27.4% [F p4, L590 and L699]. Gross margins corroborate material business-economics differences but do not themselves bridge EBITDA definitions.

**Strongest countercase:** Moog's lower-margin systems/industrial mix may make it a weak valuation anchor for TDG. If TDG's higher earnings conversion is durable and reflects differentiated aftermarket/product economics, the revenue transfer could materially understate economic value. Conversely, if TDG's margins or earnings quality deteriorate, transferring the same EBITDA multiple could overstate support. The retained pack does not quantify a matched aftermarket mix, pricing durability or normalized earnings bridge sufficient to decide between these cases. Consequently neither indication dominates, and averaging them would conceal rather than resolve the disagreement.

For creditors, deterioration in commercial demand or program execution would first affect volumes, mix or contract costs; earnings and cash conversion could then weaken, impairing refinancing confidence. Monitor margin persistence, working-capital absorption, RPA availability and earnings-definition bridges before attaching valuation support to credit decisions. These sources do not supply a forecast, stress magnitude or resulting liquidity headroom.

### T4.1 — peer scope

| Entity Name | Peer Category Label | Source of Selection | Dimensions Assessed | Strengths | Limitations | Data Availability | Evidence Quality Tier | Usable For | Exclusion Reason |
|---|---|---|---|---|---|---|---|---|---|
| Moog Inc. | Public Trading Comp | User-specified candidate; earlier candidate rationale only; FY2025 filing checks [P; F; R] | All 16 reviewed below, with unknowns retained | Aerospace/defense overlap; listed equity; near-matched fiscal dates | Broader industrial/systems mix; large margin difference; incomplete EV adjustments; stale market basis | Located FY2025 prices, shares, debt, leases, cash and earnings; no complete normalized EV | Tier 2 selection override; Tier 5 Public Sources financial evidence | Historical individual-peer conditional context | Excluded from current-date statistical admission; retained for requested historical illustration |

One specified public-company candidate, zero transaction comps, zero newly web-discovered candidates. Six-source-type discovery was not executed or needed for this supplied scope; no candidate-promotion or complete-universe claim follows. N=1 permits no sector average, median, quartiles, range, percentile, rank or outlier inference [S p2].

### Comparability dimensions

| Dimension | Evidence | Valuation consequence |
|---|---|---|
| Product/service similarity | Moog aerospace/defense and industrial segments [F pp3–4]; TDG aviation-heavy sales [F p4] | Relevant overlap, not product-level equivalence |
| Revenue model | Moog over-time contract receivables [R p1 L1446]; matched TDG revenue-model detail not retained | No recurring/aftermarket revenue equivalence assumed |
| End-market exposure | Moog Space and Defense, Military Aircraft, Commercial Aircraft, Industrial [F p3]; TDG non-aviation only 1.8% [F p4] | Industrial and defense mix limits direct transfer |
| Geography | TDG US/foreign sales disclosed [F p4 L2674–2676]; matching Moog geography not supplied | No geographic normalization |
| Customer type/concentration | Moog Boeing and Lockheed receivables disclosed [R p1 L1448]; comparable TDG concentration not supplied | Common aerospace exposure does not establish equal customer risk |
| Contract structure | Moog over-time production/contract estimates and progress billings [F pp1,5; R p1] | Contract execution and cash timing may differ; TDG matched bridge missing |
| Margin structure | Moog gross margin 27.4%; TDG 60.1% [F p4]; proxy earnings margins below | Material reason the two indications diverge |
| Capex intensity | Moog FY2025 capex USD144.731m [F p8 L1193]; comparable TDG input not supplied in P | No aligned reinvestment comparison or multiple adjustment |
| Working-capital dynamics | Moog unbilled receivables, inventories, advances and RPA [F pp1,8; R p1] | EBITDA not interchangeable with cash generation |
| Leverage/capital structure | Moog borrowings, finance leases and receivables funding [F pp2,5; R p1]; TDG full bridge not in increment | Cannot infer comparable leverage tolerance or debt coverage |
| Public vs private | Both public SEC registrants [F pp1,4] | Trading context possible, but only Moog dated equity assembled |
| Accounting standard | US GAAP framing in filings, ASC 842 leases [F p6; R p2]; P uses reported lines | No IFRS conversion required; economic-claims review remains incomplete |
| Fiscal-period alignment | Moog FY ended 2025-09-27; TDG 2025-09-30 [F pp1,6] | Same FY2025 cohort; three-day difference, no calendarization |
| Data availability | Located earnings, shares and funding passages [F pp1–8; P] | Sufficient known-components arithmetic, insufficient complete EV/normalization |
| Valuation relevance | Two dated common share prices and principal bridge [F pp1–2,5] | Positive individual multiples, not evidence of an appropriate TDG market multiple |
| Source provenance | Primary SEC-body captures, selected passages; download failures [P; F] | Better than unsourced multiples, weaker coverage than full-file verification |

### T4.2 — valuation alignment

AP1–AP11 follow S p2: borrower definition; peer definition; source period; currency; accounting basis; actual/pro forma; reported/adjusted; period length; source quality; normalization; resulting status. Rows explicitly address these checks rather than presuming equality.

| Metric | Borrower Value/Period | Peer Entity/Value/Period | AP1-AP11 | Comparability Status | Limitation Notes |
|---|---|---|---|---|---|
| Revenue | TDG USD8,831m / FY2025 ended Sep30 | Moog USD3,860.624m / FY2025 ended Sep27 | 1–2 consolidated net sales; 3 dates differ three days; 4 USD (thousands converted to millions); 5 US GAAP; 6 actual; 7 reported; 8 annual; 9 primary captures; 10 no normalization; 11 limited | Comparable with Limitations | Business mix differs; no calendarization [F pp1,4; P] |
| Ordinary EBITDA / reported-line proxy | TDG USD4,568m / FY2025 | Moog USD488.451m / FY2025 | 1 net income+tax+net interest+D&A; 2 pretax+expense-labelled interest+D&A; 3–4 FY2025/USDm; 5 underlying GAAP lines; 6 actual; 7 non-GAAP/proxy, not adjusted; 8 annual; 9 located filing lines; 10 interest-income bridge missing; 11 limited | Comparable with Limitations | Conditional transfer Provisional; not a normalized comparable valuation [F pp1,4,6,8] |
| EBITDA As Defined | TDG USD4,760m / FY2025 | Moog matched adjusted measure: Not supplied | 1 borrower includes additional adjustments; 2 matched peer definition missing; 3–9 annual FY2025 USD reported reconciliation available only for TDG; 10 no add-back harmonization; 11 not comparable | Not Comparable | Do not apply Moog proxy multiple to this metric [F p6] |
| EV numerator | TDG complete EV: Not supplied / Sep30 | Moog principal/finance-lease/cash proxy USD7,501.839030m / Sep27 | 1 borrower bridge absent; 2 known components only; 3 dated; 4 USDm; 5 borrowing GAAP reconciled; 6 actual historical; 7 principal convention, carrying sensitivity; 8 point-in-time; 9 selected captures; 10 economic adjustments incomplete; 11 insufficient | Insufficient Information | No direct borrower trading valuation or security conclusion |

## Calculations

### Equity and funding bridge

Moog source monetary statements are **USD thousands**, share counts are **actual shares**, and the two prices are **USD/share**, not thousands [F pp1–2]. Tool checks give Class A outstanding = 43,863,458 issued −15,013,457 treasury −425,148 SECT = 28,424,853; Class B = 7,416,255 issued −2,825,989 treasury −526,644 SECT −826,170 SERP = 3,237,452 [F pp1,7]. Do not add trust shares back. FY2025 basic/diluted weighted averages 31,680,280/32,082,601 are EPS denominators, not dated equity quantities [F pp1,7].

Retained multiplication evidence: A = 28,424,853 × USD204.64 = USD5,816,861,917.92; B = 3,237,452 × USD206.00 = USD666,915,112.00. Their sum divided by 1,000,000 is USD6,483.77702992m [C p1; F p2 L2349]. September 27 is the issuer's disclosed **as-of** price label, not proof of a Saturday exchange trade. Both filings became available after fiscal year-end; this is retrospective, not an executable September 2025 backtest [P]. Prices and financials are greater than twelve months old on 2026-11-05. C's native exclusion diagnostic used 2026-11-04; it was not rerun today. The later execution only increases staleness.

Full formula: **EV = common equity + debt + minority interests + preferred equity − cash/equivalents − eligible liquid available short-term investments** [S p2]. Complete EV is Not calculable because economic adjustments are not fully established. Chosen convention uses borrowing principal plus finance leases, excluding operating leases without a rent add-back. This is explicitly different from M's default balance-sheet carrying debt; that basis is shown separately.

| Component / basis | FY2025 amount, USDm | Reconciliation / treatment |
|---|---|---|
| Borrowing principal | 946.000 | 195 revolver +250 term +1 SECT facility +500 senior notes [F p5 L1671–1679] |
| Net borrowing carrying value | 945.686 | 1.563 current +944.123 long-term = principal less0.314 issuance costs [F pp1,5] |
| Borrowing fair value | 932.570 | Level 2 estimate; filing compares against946.000, not net945.686 [F pp5,7] |
| Finance leases | 134.075 | 14.920 current +119.155 long term; outside borrowing captions; add once [F p2] |
| Cash/equivalents | 62.013 | Deduct reported non-restricted cash; complete accessibility not established [F p1] |
| Restricted cash | 0.200 | Separate; not deducted [F p1] |
| Operating lease liabilities | 64.246 | Excluded by stated convention; earnings not rent-adjusted [F p2] |
| Principal known-components proxy | 7,501.83902992 | 6,483.77702992 +946 +134.075 −62.013 [C p1] |
| Carrying-basis proxy | 7,501.52502992 | Same bridge, borrowing945.686; difference −0.314 [C p1] |
| Fair-borrowing sensitivity | 7,488.40902992 | Same bridge, borrowing932.570; difference −13.430; finance leases unchanged [C p1] |
| Principal proxy plus RPA sensitivity | 7,626.83902992 | Add125.000 sold receivables; supplemental debt-like treatment only [C p1; R p1] |
| Preferred / minority market values | Not supplied | No separate retained equity amount; preferred authorized with conditional issuance language; no exact economic zero inferred [F pp1,3,7] |
| Eligible short-term investments | Not supplied | No established available corporate investment deduction; derivatives and pension/trust assets are not automatically cash [F pp4–7] |
| Other economic claims adjustment | Not calculable: classification/valuation review incomplete | Pension obligations157.218 and contingent consideration0.473 disclosed, but no complete adjustment established [F pp1,7] |

RPA proceeds are operating cash flows; USD125m is derecognized sold receivables, not GAAP borrowing. The subsidiary guarantees sold receivables and pledges assets; those assets are unavailable to other group creditors [R p1 L1436–1445]. Thus the sensitivity highlights funding dependence without silently reclassifying the sale. None of the debt-basis alternatives constitutes a peer distribution.

### Denominators and exact arithmetic provenance

Moog's **reported-line pretax-plus-interest-plus-D&A EBITDA proxy** = (312,648 +72,075 +94,013 +9,715)/1,000 = USD488.451m; revenue =3,860,624/1,000 = USD3,860.624m [F pp1,8; C p1]. D&A103,728 is independently corroborated in Note22 [F p3]. Segment operating profit449,606 excludes corporate items and is **not consolidated EBIT** [F p4]. No restructuring, impairment, stock-compensation or other add-backs are made; this proxy is neither adjusted nor covenant EBITDA.

TDG ordinary EBITDA =2,074 +555 +1,572 +367 = USD4,568m. EBITDA As Defined =4,568 +42 +157 +11 −18 = USD4,760m, retained separately and not used for transfer [F p6; C p1]. TDG uses interest expense-net, whereas Moog's line is expense-labelled; failure to find a separate interest-income passage does not establish zero interest income [F p4].

C p1 retains formula outputs separately from display in its `values` and `display_6dp` registers. Its unchanged production context was Decimal38, half-even. All 21 results have independently been host-verified against frozen source-literal Fraction expectations; those expectations are not supplied here. This provider checked the operands against F/R/P and **reuses existing deterministic results**, not model-produced multiplication or a claimed new oracle run.

Unrounded transfer trace, all absolute quantities USDm:

- Revenue multiple =7,501.83902992 /3,860.624 = `1.9431674853391576076820741931874225514`; × TDG8,831 = `17160.112063030100833440397200038128551` [C p1].
- EBITDA-proxy multiple =7,501.83902992 /488.451 = `15.358427006844084667653459610073477176`; × TDG4,568 = `70157.294567263778761841003498815643740` [C p1].
- New Decimal38 tool checks: share sums above; Moog FY2025 proxy margin488.451/3,860.624 = `0.12652125666731595721313445702041949695`; TDG ordinary margin4,568/8,831 = `0.51726871249009172234175065111538897067`. These new checks are separate from C's 21 keys. Ratios are fractions; displayed percentages merely move the decimal point. Computation precision is not valuation precision.

### T4.8 — public trading comps

Absolute values USDm; EV-labelled columns contain the explicitly conditional proxy.

| Entity | Mkt Cap | Date | EV | EV/Revenue | EV/EBITDA | Period | Metric Def | Comp Status | Source |
|---|---|---|---|---|---|---|---|---|---|
| Moog Inc. | 6,483.777030 | 2025-09-27 issuer as-of label; stale at execution | 7,501.839030 known-components proxy; complete EV Not calculable: adjustments incomplete | 1.943167x proxy | 15.358427x proxy | FY2025 ended2025-09-27 | Principal borrowings +finance leases −reported non-restricted cash; pretax+expense-labelled interest+D&A | Comparable with Limitations | F pp1–8; R p1; C p1 |

### T4.9 — transaction comps

| Txn Name | Date | Type | Buyer/Seller | TV | TV/Revenue | TV/EBITDA | Period | Metric Def | Comp Status | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| No qualifying transaction comparable supplied | Not supplied | Not supplied | Not supplied | Not supplied | Not calculable: no supported TV and denominator | Not calculable: no supported TV and denominator | Not supplied | Contemporaneous transaction EV and earnings not established | Insufficient Information | P; F; R; no qualifying transaction case |

R p1 discloses Moog's COTSWORKS acquisition purchase price, but calls its FY2025 sales/results immaterial and supplies no matched transaction EV/earnings case. Acquisition consideration is not silently promoted into a transaction comparable.

### T4.10 — conditional indications

All implied amounts USDm. Each trading row is a separate point illustration. Low/Median/High are Not calculable because N=1; there is no sector or blended range.

| Method | Multiple Source/Value | Borrower Metric/Period | Implied EV/Low/Median/High | Calc Status | Limitations |
|---|---|---|---|---|---|
| EV/Revenue | Moog principal proxy /FY2025 sales; 1.943167x [C p1] | TDG net sales8,831 /FY2025 ended2025-09-30 [F p4] | Conditional point17,160.112063; Low/Median/High Not calculable: N=1 | Provisional | Stale individual proxy; mix/margin differences; incomplete EV |
| EV/EBITDA | Moog principal proxy /reported-line EBITDA proxy; 15.358427x [C p1] | TDG ordinary EBITDA4,568 /FY2025 ended2025-09-30 [F p6] | Conditional point70,157.294567; Low/Median/High Not calculable: N=1 | Provisional | Interest-net mismatch and business economics unnormalized; not applied to EBITDA As Defined |
| TV/Revenue | Not supplied: no supported transaction multiple | TDG net sales8,831 /FY2025 ended2025-09-30 | Not calculable: transaction inputs missing; Low/Median/High likewise missing | Insufficient Information | No transaction evidence; no zero substituted |
| TV/EBITDA | Not supplied: no supported transaction multiple | TDG ordinary EBITDA4,568 /FY2025 ended2025-09-30 | Not calculable: transaction inputs missing; Low/Median/High likewise missing | Insufficient Information | No contemporaneous transaction EBITDA/TV; no trading blend |

### Valuation calculation controls

The following are **exactly C's 21 retained result keys**, displayed as six-place decimal strings. First two rows are USD; monetary rows ending `_usdm` are USD millions; the two multiple rows are dimensionless x. Signs in sensitivity rows denote changes from the principal proxy. Source operands and unrounded outputs remain in the trace above and C p1.

| Metric | Value (6dp) |
|---|---|
| class_a_equity_usd | 5816861917.920000 |
| class_b_equity_usd | 666915112.000000 |
| market_cap_usdm | 6483.777030 |
| borrowing_carrying_usdm | 945.686000 |
| finance_lease_usdm | 134.075000 |
| borrowing_principal_usdm | 946.000000 |
| proxy_principal_usdm | 7501.839030 |
| proxy_carrying_usdm | 7501.525030 |
| proxy_fair_debt_usdm | 7488.409030 |
| debt_fair_sensitivity_usdm | -13.430000 |
| net_carrying_sensitivity_usdm | -0.314000 |
| proxy_plus_rpa_usdm | 7626.839030 |
| moog_ebitda_proxy_usdm | 488.451000 |
| moog_revenue_usdm | 3860.624000 |
| ev_proxy_revenue | 1.943167 |
| ev_proxy_ebitda_proxy | 15.358427 |
| tdg_ordinary_ebitda_usdm | 4568.000000 |
| tdg_as_defined_usdm | 4760.000000 |
| tdg_revenue_usdm | 8831.000000 |
| tdg_revenue_indication_usdm | 17160.112063 |
| tdg_ebitda_indication_usdm | 70157.294567 |

## Gaps

### T4.11 — gaps

| Gap | Affected Metric/Section | Affected Peer(s) | Downstream Impact | Severity | Action |
|---|---|---|---|---|---|
| Preferred/minority values, eligible investments and economic claims not fully established | Complete EV; T4.8/T4.10 | Moog; TDG bridge also not supplied | Positive bridge remains conditional, not complete EV | High | Obtain full capitalization, cash-accessibility and economic-claims review |
| Expense-labelled versus net-interest definition; no normalized add-back bridge | EBITDA transfer | Moog /TDG | Provisional only; no normalized valuation | High | Locate interest-income and matched earnings reconciliations |
| Stale dated prices/financials; filings available only retrospectively | Current admission and tradeability | Moog /TDG | Cannot use as current valuation or September2025 backtest | High | Refresh market basis and aligned financial cohort before current use |
| Single scoped candidate; no complete discovery/distribution | Peer statistics/outliers | Moog | No ranking, sector statistics, range or discovery-completion claim | High | Separately expand and verify peer universe; FY2024 three-peer work is a later test |
| No qualifying transaction case | T4.9; two methods in T4.10 | Transaction peers not supplied | Both transaction indications remain missing | High | Obtain dated TV, perimeter and contemporaneous denominators |
| Business-model, margin, geography and contract matching incomplete | Transfer relevance | Moog /TDG | No supported premium/discount or choice between indications | High | Establish product/aftermarket, concentration and normalized-margin bridges |
| Limited CP-1 increment and selected source captures only | Coverage and underwriting readiness | Both issuers | Not full CP-1 acceptance or full CP-1C benchmarking | High | Obtain broader accepted financial foundation for underwriting consumers |

## Next module

CP-2 may consume the two historical conditional points, the funding-basis sensitivities, the definition differences and the countercase as **restricted valuation context**, preserving source dates, units, provenance and missing adjustments. It must not interpret either point as complete EV, collateral value, debt coverage, recovery, target price, current recommendation or proof of leverage capacity. It must not average the points, treat sensitivities as a range, or infer sector statistics from N=1. TDG EBITDA As Defined remains separate from the ordinary EBITDA transfer.

Before decision use, CP-2 needs fresh aligned evidence, a full capitalization/economic-claims bridge and earnings-quality work; subsequent events must remain dated and separate from FY2025. This handoff does not claim CP-2 has executed or consumed it. The separate existing delivery process should preserve this model-authored reasoning, figures, definitions, complete tables and restrictions in HTML without an analytical rerun, workbook, new engine or competing controller; no HTML delivery is claimed here.