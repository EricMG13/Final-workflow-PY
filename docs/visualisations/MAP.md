# Module chart and visualisation map

4 November 2026, CP-8 revised 5 November 2026 · 24 active canonical modules · 16 aliases · 91 visual specifications · separate delivery assembly. Planning catalogue, not a claim that these visuals are populated in current issuer runs.

## Scope and authority

Keep the approved Deploy VII design language and symbol-only branding. Reuse the existing chart engine, renderers, calculations and handoffs. CP-OS is the active end-to-end orchestrator under the current user instruction; the older catalog navigation-only label does not govern this app. CP-MEMO is replaced by the delivery assembly below and is not another analytical execution.

Selection follows METHODOLOGY-REVIEW.md: Deploy V ancestry and breadth, later documented corrections/additions and scope reductions. Existing design requirements, currently implemented views and proposed qualitative treatments are deliberately labelled separately. No analytics were run for this catalogue.

| Basis | Meaning |
| --- | --- |
| Design | Named Deploy VII design requirement; conditional on applicable pathway and adequate evidence. |
| Method content | Required module information; new chart/diagram treatment is a proposal unless a figure producer already exists. |
| Proposed | Proposed qualitative/cross-module presentation; may need additional handoff fields. |
| Operational | Current user workflow / operational or delivery view; not an additional analytical module. |

| Implementation state | Meaning |
| --- | --- |
| Figure producer | Registered figure adapter exists. It still needs qualified source-backed input; current narrative reports do not populate it. |
| Table/content only | Required content/tables exist; a new proposed visual treatment still needs presentation work. |
| Design gap | Design specifies this figure but a current bound producer was not found. |
| Unavailable frame | An unavailable/n/a frame exists; there is no populated chart to claim. |
| New view | New presentation/component or aggregation view. |
| Broader handoff needed | Current bounded owner/handoff does not establish the complete proposed visual. |

## Module overview

| Module | Role | Quantitative / named chart views | Qualitative / other views |
| --- | --- | --- | --- |
| CP-0 | Source readiness | No numerical chart required | Source, period and consumer coverage; Readiness and blocking gaps; Source chronology and supersession |
| CP-1 | Canonical data foundation | Total and net leverage; Interest coverage; Cash and accessible liquidity; Debt maturity wall; Revenue and adjusted EBITDA history; Debt ranking and cumulative leverage; EBITDA adjustment bridge | Financial statements and calculation lineage |
| CP-1A | Business transaction fact pack | Business mix and concentration | Issuer event history and transaction calendar; Ownership and control; Operating model and credit transmission; Governance, sponsor behaviour and capital allocation |
| CP-1B | Earnings delta | Prior versus current financial results; Margin and operating KPI changes; Changes and drivers | Earnings release, guidance and watch dates |
| CP-DR | Deep research | No numerical chart required | Research questions, answers and consumers; Source support and contradiction; Sourced sector/issuer catalysts; Peer/transaction research coverage |
| CP-1C | Peer benchmark | Issuer against peer range: percent metrics; Issuer against peer range: multiples; Valuation evidence and basis selection | Comparable universe and outliers |
| CP-1D | Earnings quality | Issuer-to-supported EBITDA; Cash conversion and leverage restatement | Add-back quality |
| CP-2 | Fundamental credit synthesizer | No numerical chart required | Thesis, strengths and weaknesses; Credit-risk transmission; Watch items and thesis invalidation |
| CP-2A | Downside pathway | Base/downside/stress comparison; First-break ranking and cushions | Stress assumptions and what breaks first |
| CP-2E | Macro fx hedging sensitivity | Rate shock before/after hedging; Currency shock exposure | Hedges and residual risk |
| CP-2G | Forward credit model | Forward debt, cash and credit metrics | Deleveraging and break-point timing; Assumption and scenario comparison |
| CP-2H | Ratings migration trigger | Rating-trigger headroom | Agency divergence and migration view; Published rating actions and projected triggers |
| CP-3 | Relative value security selection | Price, compensation and recovery case | Security comparison and preference; Instrument optionality and catalyst dates |
| CP-4 | Legal covenant interpreter | Covenant tests and headroom | Capacity, baskets and conditions; Entities, guarantees and structural subordination; Intercreditor ranking and control; Tests, cures, amendments and notice deadlines; Creditor protections and red flags |
| CP-4C | Restructuring fulcrum | Recovery by class and scenario; Value allocation: supplied scenario 1; Value allocation: supplied scenario 2; Value allocation: supplied scenario 3 | Fulcrum, attachment and plan treatment |
| CP-5 | Evidence trace validator | No numerical chart required | Material-claim support and gaps; Contradictions and lineage; Findings and remediation |
| CP-6 | Ic debate challenge | Portfolio limit headroom | Committee challenge and resolution; Action bias, conditions and monitoring; Catalysts and monitoring commitments |
| CP-8 | Deliverable comparison | No numerical chart required | Report section changes; Prior and current material changes; Regressions and recheck |
| CP-L10 | Financial change screen | Seven-topic financial change screen | Upgrade disposition and handoff |
| CP-MODEL | Model (HTML destination and calculation JSON) | Published model and calculation provenance | Shared chart collection and availability |
| CP-OS | Workflow orchestration and delivery completion | Budget and spend | End-to-end execution and delivery; Issuer, run, revision and file navigation |
| CP-2D | Liquidity cash flow bridge | Sources and uses / liquidity bridge; Cash runway and minimum liquidity | Maturities, uses and funding dates; Accessible versus restricted resources |
| CP-3D | Market implied risk | Yield against maturity; Market-implied versus fundamental risk | Trading technicals and quote evidence |
| CP-3C | Refinancing lme risk | Refinancing need by maturity; Refinancing burden and cost sensitivity | Refinancing and LME alternatives; Execution windows and decision deadlines |
| DELIVERY | Separate delivery assembly (CP-MEMO replacement) | No numerical chart required | Pathway composition and visual eligibility; Cross-module issuer event calendar; Export and source parity |

## Named design-figure register

| Figure | Owner | Display | Status | Destination |
| --- | --- | --- | --- | --- |
| S.1 | CP-1 | Total and net leverage | Figure producer | FP01 model strip; FP02 metric strip |
| S.2 | CP-1 | Interest coverage | Figure producer | FP01/FP02 strip |
| S.3 | CP-1 | Cash and accessible liquidity | Figure producer | FP01/FP02 strip |
| S.4 | CP-1 | Debt maturity wall | Figure producer | FP01 strip; FP04 maturity wall |
| S.5 | CP-1 | Revenue and adjusted EBITDA history | Figure producer | FP01 financials/credit metrics |
| S.6 | CP-1 | Debt ranking and cumulative leverage | Design gap | FP01 capital structure |
| EU.3 | CP-1 | EBITDA adjustment bridge | Design gap | FP02 EBITDA adjustments |
| EU.1 | CP-1B | Prior versus current financial results | Design gap | FP02 headline results |
| EU.2 | CP-1B | Margin and operating KPI changes | Design gap | FP02 KPI changes |
| RV.3a | CP-1C | Issuer against peer range: percent metrics | Figure producer | FP03 peer positioning |
| RV.3b | CP-1C | Issuer against peer range: multiples | Figure producer | FP03 peer positioning |
| CR.2 | CP-2D | Sources and uses / liquidity bridge | Figure producer | FP04/FP05 liquidity runway |
| DR.6 | CP-2H | Rating-trigger headroom | Unavailable frame | FP05 rating triggers |
| CR.3 | CP-3C | Refinancing need by maturity | Figure producer | FP04 funding gap; FP05 funding gap/LME |
| RV.1 | CP-3D | Yield against maturity | Design gap | FP03 yield against maturity |
| CR.1 | CP-4 | Covenant tests and headroom | Figure producer | FP04/FP05 covenant headroom |
| DR.2 | CP-4C | Recovery by class and scenario | Figure producer | FP05 recovery by class |
| DR.3 | CP-4C | Value allocation: supplied scenario 1 | Figure producer | FP05 value allocation/claims |
| DR.4 | CP-4C | Value allocation: supplied scenario 2 | Figure producer | FP05 value allocation/claims |
| DR.5 | CP-4C | Value allocation: supplied scenario 3 | Figure producer | FP05 value allocation/claims |
| PD.1 | CP-6 | Portfolio limit headroom | Design gap | FP06 Portfolio Fit; shared Fit destination |

RV.3 is split into percent and multiple panels (RV.3a/b). S.4, CR.1–CR.3 and other shared visuals reuse the same data identities across pathways, not fresh calculations. DR.3–DR.5 represent the valuation scenarios actually supplied, not a mandate to invent three cases. Market-against-fundamentals is a required section, but no RV.2 figure identifier was confirmed; no such ID is invented here.

## Detailed module catalogue

### CP-0 — Source readiness

Aliases: CP-PARSE. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Inventories and reads the source pack, adaptively parses what needs restructuring, freezes one effective source set, and establishes readiness plus the exact source-to-module map.

#### CP-0-V01 · Source, period and consumer coverage

| Field | Specification |
| --- | --- |
| Visual | Coverage matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Sources; Run readiness |
| Input / source registers | Source inventory, effective source hashes, issuer/perimeter/period coverage, source-to-module map (T1–T4, T6, T8; P3/P5). |
| Eligibility / gap / interpretation guard | Read/parsed is not verified; show excluded, stale, unreadable and absent separately. Count unique sources, not warning strings. |
| Delivery priority | First |

#### CP-0-V02 · Readiness and blocking gaps

| Field | Specification |
| --- | --- |
| Visual | Dependency/status map |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Overview; Sources |
| Input / source registers | T5/T7 readiness and gaps; selected downstream consumers and exact blocking reasons. |
| Eligibility / gap / interpretation guard | Use producer readiness states and word+shape; no financial score from module completion. |
| Delivery priority | First |

#### CP-0-V03 · Source chronology and supersession

| Field | Specification |
| --- | --- |
| Visual | Document timeline |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Sources; Calendar |
| Input / source registers | Document publication, reporting period, revision/amendment dates and authority. |
| Eligibility / gap / interpretation guard | Publication date, reporting period and import timestamp are different. Unknown dates stay unplaced. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp0.py; src/deploy_vii/methods/cp0.md.

### CP-1 — Canonical data foundation

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Builds the canonical financial data and KPI foundation used by downstream analysis.

#### CP-1-V01 · Total and net leverage · S.1

| Field | Specification |
| --- | --- |
| Visual | Line |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP01 model strip; FP02 metric strip |
| Input / source registers | CP-1 typed S.1 producer coordinates, debt/EBITDA basis, date/period and fact references. |
| Eligibility / gap / interpretation guard | Show only comparable periods and definitions; no interpolation across missing periods; exact amounts remain in the table. |
| Delivery priority | First |

#### CP-1-V02 · Interest coverage · S.2

| Field | Specification |
| --- | --- |
| Visual | Line |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP01/FP02 strip |
| Input / source registers | Typed S.2; stated coverage definitions, debt-only/lease-inclusive series when supplied. |
| Eligibility / gap / interpretation guard | Never merge cash interest, total interest or lease-adjusted denominators. |
| Delivery priority | First |

#### CP-1-V03 · Cash and accessible liquidity · S.3

| Field | Specification |
| --- | --- |
| Visual | Line |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP01/FP02 strip |
| Input / source registers | Typed S.3; cash and total accessible-liquidity observations with accessibility restrictions. |
| Eligibility / gap / interpretation guard | Known cash is not automatically accessible cash. The current producer uses lines; the design is reused without inventing a revolver series. |
| Delivery priority | First |

#### CP-1-V04 · Debt maturity wall · S.4

| Field | Specification |
| --- | --- |
| Visual | Grouped columns |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP01 strip; FP04 maturity wall |
| Input / source registers | Typed S.4; T4.18 facilities/claim amounts, final maturities, currency and debt categories. |
| Eligibility / gap / interpretation guard | Keep principal versus carrying amount distinct; undrawn commitments are not funded maturities; undated facilities have a separate bucket. Reuse the same figure in FP04. |
| Delivery priority | First |

#### CP-1-V05 · Revenue and adjusted EBITDA history · S.5

| Field | Specification |
| --- | --- |
| Visual | Grouped columns |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP01 financials/credit metrics |
| Input / source registers | Typed S.5; cited revenue and the specified EBITDA measure by comparable period. |
| Eligibility / gap / interpretation guard | Maintain reported versus issuer-adjusted versus house-adjusted identities; no mixed-duration trend. Current binding places S.5 in FP01 only. |
| Delivery priority | First |

#### CP-1-V06 · Debt ranking and cumulative leverage · S.6

| Field | Specification |
| --- | --- |
| Visual | Debt stack |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP01 capital structure |
| Input / source registers | Facility balances, ranking/security, guarantor/obligor scope, common EBITDA denominator; EV only when supplied. |
| Eligibility / gap / interpretation guard | The SVG debt-stack primitive exists, but no S.6 producer is registered. Require legal rank and a positive denominator; EV is not a sourced fact merely because it is a chart marker. |
| Delivery priority | Next |

#### CP-1-V07 · EBITDA adjustment bridge · EU.3

| Field | Specification |
| --- | --- |
| Visual | Waterfall |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP02 EBITDA adjustments |
| Input / source registers | T4.17 bridge from reported measure to specified adjusted measure, signed adjustments and reconciliation. |
| Eligibility / gap / interpretation guard | EU.3 is a design requirement, not a current bound figure. Totals must reconcile; do not manufacture intermediate adjustments from endpoints. CP-1D supplies a separate challenge view. |
| Delivery priority | Next |

#### CP-1-V08 · Financial statements and calculation lineage

| Field | Specification |
| --- | --- |
| Visual | Period grid + reconciliation drill-down |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Model; financials |
| Input / source registers | T4.4–T4.6, T4.8–T4.10, T4.15–T4.19 and source/calculation trace. |
| Eligibility / gap / interpretation guard | Preserve instants versus durations, restatements, quantity family, scale and currency. Current S.1–S.5 consumer has a USD unit whitelist; qualify non-USD adapters instead of relabelling data. |
| Delivery priority | First |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp1.py; src/deploy_workflow/financial_series.py; src/deploy_vii/report_view.py.

### CP-1A — Business transaction fact pack

Aliases: CP-2C. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Establishes the business and transaction fact pack: what the issuer does and what deal is in front of you.

#### CP-1A-V01 · Issuer event history and transaction calendar

| Field | Specification |
| --- | --- |
| Visual | Timeline |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Overview; Calendar; Transactions |
| Input / source registers | events_timeline, transaction_summary; actual event date/precision/status, parties and cited handoff lines. |
| Eligibility / gap / interpretation guard | The event information is already required; the graphical timeline is new. Separate announced, completed, cancelled and subsequent events; never fold a later payment into an earlier financial period. |
| Delivery priority | First |

#### CP-1A-V02 · Ownership and control

| Field | Specification |
| --- | --- |
| Visual | Relationship diagram |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Company profile |
| Input / source registers | ownership_register; owner/class, economic interest, control rights, dates and evidence. |
| Eligibility / gap / interpretation guard | Undisclosed percentages stay unknown; ownership, legal control and guarantees use different labelled edges. No inferred sponsor willingness. |
| Delivery priority | Next |

#### CP-1A-V03 · Business mix and concentration

| Field | Specification |
| --- | --- |
| Visual | Horizontal bars + concentration table |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Company profile |
| Input / source registers | revenue_business_mix; aligned CP-1 T4.16 segment/end-market amounts or explicit sourced shares. |
| Eligibility / gap / interpretation guard | Do not force partial coverage to 100%; labels without quantities stay a qualitative map. Keep periods, currencies and consolidation boundaries aligned. |
| Delivery priority | Next |

#### CP-1A-V04 · Operating model and credit transmission

| Field | Specification |
| --- | --- |
| Visual | Driver-to-cash diagram |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Company and operating model |
| Input / source registers | operating_model and credit_translation: evidence → mechanism → credit implication. |
| Eligibility / gap / interpretation guard | Edges must be stated in the handoff and tagged Documentary Fact, Management Language, Analyst Interpretation or Insufficient Information. No weighted cash-flow arrows without amounts. |
| Delivery priority | Next |

#### CP-1A-V05 · Governance, sponsor behaviour and capital allocation

| Field | Specification |
| --- | --- |
| Visual | Evidence/behaviour matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Company profile; full analysis |
| Input / source registers | T2D.2–T2D.9, conflicts, documented actions and existing scoring outputs. |
| Eligibility / gap / interpretation guard | Use issuer actions and the recorded scoring method only; gaps are not adverse conclusions. Keep legal capacity, willingness and financing feasibility separate. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp1a.py; src/deploy_vii/methods/cp1a.md.

### CP-1B — Earnings delta

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Quantifies the earnings delta between reporting periods and explains what moved.

#### CP-1B-V01 · Prior versus current financial results · EU.1

| Field | Specification |
| --- | --- |
| Visual | Grouped columns + table toggle |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP02 headline results |
| Input / source registers | T1B.1 paired revenue, EBITDA, cash flow/capex, comparable perimeter and duration. |
| Eligibility / gap / interpretation guard | EU.1 has no bound figure producer. Pair only compatible quantities; margin belongs on a separate percent panel. One pair is a comparison, not a trend. |
| Delivery priority | First |

#### CP-1B-V02 · Margin and operating KPI changes · EU.2

| Field | Specification |
| --- | --- |
| Visual | Dumbbell/slope comparison |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP02 KPI changes |
| Input / source registers | T1B.1 margin plus sourced segment/KPI prior/current pairs where actually supplied. |
| Eligibility / gap / interpretation guard | EU.2 needs a producer/geometry adapter. Current paired tables do not prove a segment-level KPI series exists. Percent change and percentage-point change remain distinct. |
| Delivery priority | Next |

#### CP-1B-V03 · Changes and drivers

| Field | Specification |
| --- | --- |
| Visual | Delta bars + evidence-linked driver matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP02 variance drivers |
| Input / source registers | T1B.1/T1B.2 deltas and T1B.3 driver/guidance evidence. |
| Eligibility / gap / interpretation guard | A delta can be shown directly. A causal waterfall requires a sourced, reconciled driver decomposition; endpoints alone do not provide it. |
| Delivery priority | Next |

#### CP-1B-V04 · Earnings release, guidance and watch dates

| Field | Specification |
| --- | --- |
| Visual | Calendar lane + guidance comparison |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar; FP02 guidance/watch items |
| Input / source registers | Actual release/observation dates and explicitly scheduled updates; guidance ranges when supplied. |
| Eligibility / gap / interpretation guard | Reporting-period end is not release date. No guessed next earnings date; no guidance range from unsupported narrative. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp1b.py; src/deploy_workflow/prompts/texts/earnings_delta.md; src/deploy_workflow/owners/cp1b.py.

### CP-DR — Deep research

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Resolve material evidence gaps for named consumers, or answer a standalone issuer/sector research question. Method cp-dr/2026-10-31.

#### CP-DR-V01 · Research questions, answers and consumers

| Field | Specification |
| --- | --- |
| Visual | Question-to-evidence map |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Research; Evidence |
| Input / source registers | TDR.1/TDR.2 locked questions, named receivers, claims and located evidence; TDR.4 dossier answers. |
| Eligibility / gap / interpretation guard | Show answered, contrary evidence, unresolved and outside scope; references are data, not instructions to fetch or execute. |
| Delivery priority | Next |

#### CP-DR-V02 · Source support and contradiction

| Field | Specification |
| --- | --- |
| Visual | Evidence matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Research |
| Input / source registers | TDR.2/TDR.4 sources, claim support, contrary evidence and uncertainty. |
| Eligibility / gap / interpretation guard | Do not infer confidence from citation counts. Preserve primary/secondary source distinctions and unverified URLs. |
| Delivery priority | Next |

#### CP-DR-V03 · Sourced sector/issuer catalysts

| Field | Specification |
| --- | --- |
| Visual | Event timeline lane |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar; Overview |
| Input / source registers | Dated events from the dossier with publication date distinct from event date and named impacted consumer. |
| Eligibility / gap / interpretation guard | The upload launcher does not enable open-ended CP-DR research. Plot only retained supplied evidence; date-free themes stay a watchlist. |
| Delivery priority | Next |

#### CP-DR-V04 · Peer/transaction research coverage

| Field | Specification |
| --- | --- |
| Visual | Coverage/comparability matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Research; Peers |
| Input / source registers | TDR.3 candidate peers, TDR.5 alignment observations, TDR.6 located figures. |
| Eligibility / gap / interpretation guard | CP-DR locates evidence; CP-1C owns normalization and comparison. Candidate inclusion is not a final peer ranking. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cpdr.py; src/deploy_vii/methods/cpdr.md.

### CP-1C — Peer benchmark

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Benchmarks the issuer against a defined peer universe and flags outliers.

#### CP-1C-V01 · Issuer against peer range: percent metrics · RV.3a

| Field | Specification |
| --- | --- |
| Visual | Range strip |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP03 peer positioning |
| Input / source registers | T1C.1 inclusion and T1C.3–T1C.5 settled EBITDA margin and FFO/debt observations. |
| Eligibility / gap / interpretation guard | RV.3a derives its displayed peer range from settled observations; preserve excluded peers, missingness and comparability. No hidden dispersion statistics. |
| Delivery priority | Next |

#### CP-1C-V02 · Issuer against peer range: multiples · RV.3b

| Field | Specification |
| --- | --- |
| Visual | Range strip |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP03 peer positioning |
| Input / source registers | T1C.3–T1C.5 total leverage and coverage, with issuer/peer definitions. |
| Eligibility / gap / interpretation guard | RV.3b keeps multiples separate from percentages. Do not calendarise or FX-convert peers in the renderer. |
| Delivery priority | Next |

#### CP-1C-V03 · Comparable universe and outliers

| Field | Specification |
| --- | --- |
| Visual | Peer matrix + outlier strip |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Peers; full analysis |
| Input / source registers | T1C.1–T1C.8 inclusion, normalization, source tie-out and gap rows. |
| Eligibility / gap / interpretation guard | Partly comparable peers retain their caveats; show population size and omitted fields. No equal-sized bubbles suggesting unknown weights. |
| Delivery priority | Next |

#### CP-1C-V04 · Valuation evidence and basis selection

| Field | Specification |
| --- | --- |
| Visual | Comparable-value range + dated deal list |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Peers; valuation evidence |
| Input / source registers | T1C.9–T1C.11 public comps/precedents, date windows, metric definitions and selected basis. |
| Eligibility / gap / interpretation guard | No EV multiple if EV/EBITDA basis is missing; peers/precedents use their recorded 12/36-month eligibility rules. A valuation range is not a price target. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp1c.py; src/deploy_vii/methods/cp1c.md.

### CP-1D — Earnings quality

Aliases: CP-1E. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Challenges the adjusted-EBITDA bridge: tests each add-back for achievability and recurrence against evidence, reconciles adjusted EBITDA to cash, and restates leverage on the earnings the evidence supports.

#### CP-1D-V01 · Issuer-to-supported EBITDA

| Field | Specification |
| --- | --- |
| Visual | Adjustment waterfall |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP02 earnings quality |
| Input / source registers | T1D.1–T1D.4 add-backs, achievability/recurrence decisions, accepted/rejected amounts and reconciliation. |
| Eligibility / gap / interpretation guard | Proposed graphic over existing tables, not EU.3. Missing acceptance remains unassessed; do not treat non-cash as non-recurring automatically. |
| Delivery priority | Next |

#### CP-1D-V02 · Add-back quality

| Field | Specification |
| --- | --- |
| Visual | Recurrence × evidence matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Earnings quality |
| Input / source registers | T1D.1/T1D.2 assessment categories, rationale and evidence. |
| Eligibility / gap / interpretation guard | Display the actual categorical judgments; no invented quality score or probability. |
| Delivery priority | Next |

#### CP-1D-V03 · Cash conversion and leverage restatement

| Field | Specification |
| --- | --- |
| Visual | Grouped comparisons |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP02 restated leverage |
| Input / source registers | T1D.5–T1D.7/settled cash-conversion and leverage output with issuer/house basis labels. |
| Eligibility / gap / interpretation guard | Compare like units and periods; preserve reported CFO, proxy FCF and issuer-defined FCF distinctions. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp1d.py; src/deploy_vii/methods/cp1d.md.

### CP-2 — Fundamental credit synthesizer

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Synthesises the fundamental credit view from the canonical data and supporting registers.

#### CP-2-V01 · Thesis, strengths and weaknesses

| Field | Specification |
| --- | --- |
| Visual | Paired argument/evidence map |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP01 key findings/strengths; Analysis |
| Input / source registers | T2.7/T2.10 and key-findings/thesis/strengths/weaknesses registers. |
| Eligibility / gap / interpretation guard | Retain analyst interpretation and source links. Do not turn argument counts into a credit score. |
| Delivery priority | First |

#### CP-2-V02 · Credit-risk transmission

| Field | Specification |
| --- | --- |
| Visual | Driver → mechanism → creditor outcome map |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Overview; risk analysis |
| Input / source registers | T2.1/T2.11 assessments, named risks, explicit mechanisms and limitations. |
| Eligibility / gap / interpretation guard | Only stated causal links; use qualitative categories. Do not invent likelihood/impact coordinates for a heatmap. |
| Delivery priority | Next |

#### CP-2-V03 · Watch items and thesis invalidation

| Field | Specification |
| --- | --- |
| Visual | Trigger/monitoring matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Overview; Calendar watchlist |
| Input / source registers | T2.11/T2.12 watch metrics, thresholds/conditions and evidence gaps. |
| Eligibility / gap / interpretation guard | A threshold is a condition, not a dated event. Add to the calendar only if a review date is explicitly supplied. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2.py; src/deploy_vii/methods/cp2.md.

### CP-2A — Downside pathway

Aliases: CP-2B. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Builds the downside and stress pathway: what breaks first and how far it falls.

#### CP-2A-V01 · Base/downside/stress comparison

| Field | Specification |
| --- | --- |
| Visual | Grouped bars + scenario heatmap |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP05 downside stress |
| Input / source registers | T2B.1–T2B.5 selected base period, static shocks, EBITDA, cash interest and credit metrics. |
| Eligibility / gap / interpretation guard | This owner is a static single-period stress. Plot discrete computed cases; no invented time path, continuous response surface or mitigation. |
| Delivery priority | Next |

#### CP-2A-V02 · First-break ranking and cushions

| Field | Specification |
| --- | --- |
| Visual | Ranked threshold-distance view |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP05 break points |
| Input / source registers | T2B.6–T2B.8 break levels, required decline, outcome and ranking. |
| Eligibility / gap / interpretation guard | Keep legal covenants, analyst watch levels and rating triggers visibly distinct; do not add headrooms with different units. |
| Delivery priority | Next |

#### CP-2A-V03 · Stress assumptions and what breaks first

| Field | Specification |
| --- | --- |
| Visual | Scenario decision map |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Downside analysis |
| Input / source registers | Recorded scenario assumptions, test outcomes and explicit analytical explanation. |
| Eligibility / gap / interpretation guard | Branches describe computed conditions, not probabilities. No forecast date from a static stress. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2a.py; src/deploy_vii/methods/cp2a.md.

### CP-2E — Macro fx hedging sensitivity

Aliases: CP-2F. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Assesses macro, FX and hedging sensitivity of the credit.

#### CP-2E-V01 · Rate shock before/after hedging

| Field | Specification |
| --- | --- |
| Visual | Discrete sensitivity bars |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Module analysis |
| Input / source registers | Produced T2F.1–T2F.5 baseline, up to three upward rate shocks, interest/coverage/FCF and hedge effects. |
| Eligibility / gap / interpretation guard | Current method is a static upward parallel shock and requires the supported floor convention. Do not draw a symmetric tornado or negative-rate extrapolation. T2G.* remain registered but unproduced. |
| Delivery priority | Next |

#### CP-2E-V02 · Currency shock exposure

| Field | Specification |
| --- | --- |
| Visual | Discrete FX sensitivity comparison |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Module analysis |
| Input / source registers | T2F.4 specified currency moves, debt/EBITDA changes and leverage. |
| Eligibility / gap / interpretation guard | Keep transaction, translation and financing exposures distinct where supplied; no continuous surface or unsourced correlation. |
| Delivery priority | Next |

#### CP-2E-V03 · Hedges and residual risk

| Field | Specification |
| --- | --- |
| Visual | Exposure/hedge map + expiry lane |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Sensitivity; Calendar |
| Input / source registers | T2F.5 hedge terms and dated expiries/notionals if actually retained. |
| Eligibility / gap / interpretation guard | Notional is not effectiveness or fair value. No expiry chart without dates; broader hedge term data may require an input extension. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2e.py; src/deploy_vii/methods/cp2e.md.

### CP-2G — Forward credit model

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Builds the forward credit model: deleveraging path and forecast cases.

#### CP-2G-V01 · Forward debt, cash and credit metrics

| Field | Specification |
| --- | --- |
| Visual | Actual/forecast scenario lines |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP05 forward credit path |
| Input / source registers | T2H.2–T2H.6 annual base/downside operating, debt/cash and metrics. |
| Eligibility / gap / interpretation guard | Current model is three annual forecast years with documented no-new-borrowing/refinancing and other simplifications; do not add quarterly troughs or management mitigation. |
| Delivery priority | Next |

#### CP-2G-V02 · Deleveraging and break-point timing

| Field | Specification |
| --- | --- |
| Visual | Forecast-year milestone bands |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP05 forward breakpoints; Calendar |
| Input / source registers | T2H.7/T2H.8 first affected year, path and thresholds. |
| Eligibility / gap / interpretation guard | Fiscal-year bands are not exact calendar dates. Use a separate projected lane; no numeric probability. |
| Delivery priority | Next |

#### CP-2G-V03 · Assumption and scenario comparison

| Field | Specification |
| --- | --- |
| Visual | Driver matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Forecast analysis |
| Input / source registers | T2H.3 assumptions, CP-2A persistent shocks, repayment/distribution/minimum-liquidity choices. |
| Eligibility / gap / interpretation guard | Do not imply an assumption was issuer guidance or a scenario was an observed outcome. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2g.py; src/deploy_vii/methods/cp2g.md.

### CP-2H — Ratings migration trigger

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Maps rating migration risk, trigger headroom and agency divergence.

#### CP-2H-V01 · Rating-trigger headroom · DR.6

| Field | Specification |
| --- | --- |
| Visual | Bullet/threshold chart |
| Requirement basis | Design |
| Current implementation | Unavailable frame |
| Placement | FP05 rating triggers |
| Input / source registers | T2R.3–T2R.5 agency thresholds, direction, compatible metric basis and source. |
| Eligibility / gap / interpretation guard | DR.6 currently produces only an unavailable frame and explicitly expects a synthetic-source limitation. A real-source/agency-adjusted producer needs qualification; no rating probability is permitted. |
| Delivery priority | Next |

#### CP-2H-V02 · Agency divergence and migration view

| Field | Specification |
| --- | --- |
| Visual | Ordinal rating ladder + assessment matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Ratings analysis |
| Input / source registers | T2R.2/T2R.7/T2R.8 issuer/instrument rating, agency, outlook, as-of and stated migration view. |
| Eligibility / gap / interpretation guard | Rating notches are ordinal, not equal default-probability intervals. Withdrawn/unrated stay distinct; no unsupported rating history. |
| Delivery priority | Next |

#### CP-2H-V03 · Published rating actions and projected triggers

| Field | Specification |
| --- | --- |
| Visual | Ratings calendar lanes |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar |
| Input / source registers | Source-dated actions/reviews and T2R.6 forecast trigger year. |
| Eligibility / gap / interpretation guard | Separate observed action, scheduled review and modelled trigger. History is not currently produced; require an explicit historical handoff before drawing it. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2h.py; src/deploy_vii/methods/cp2h.md.

### CP-3 — Relative value security selection

Aliases: CP-3A, CP-3B. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Determines relative value and security selection across the capital structure.

#### CP-3-V01 · Security comparison and preference

| Field | Specification |
| --- | --- |
| Visual | Instrument decision matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP01 relative value; FP03 instrument decision |
| Input / source registers | T3.1/T3.3/T3.5/T3.7/T3.9 market evidence, instrument terms, risks and recorded preference. |
| Eligibility / gap / interpretation guard | Separate loan/HY conventions and observed/indicative quotes. No invented total-return forecast or numeric preference score. |
| Delivery priority | Next |

#### CP-3-V02 · Price, compensation and recovery case

| Field | Specification |
| --- | --- |
| Visual | Scenario/compensation comparison |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Relative value |
| Input / source registers | CP-3 price and valuation judgments with CP-4C recoveries and CP-3D market terms when selected. |
| Eligibility / gap / interpretation guard | Use only producer-defined comparable measures; keep estimated recovery and contractual claim separate. No legal seniority inferred from quoted yield. |
| Delivery priority | Next |

#### CP-3-V03 · Instrument optionality and catalyst dates

| Field | Specification |
| --- | --- |
| Visual | Instrument event lane |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar; instrument detail |
| Input / source registers | Sourced maturity, call/put, coupon/reset and offer deadlines with security identity. |
| Eligibility / gap / interpretation guard | Do not create coupon schedules or option-exercise assumptions in delivery. Unknown dates remain unplaced. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp3.py; src/deploy_vii/methods/cp3.md.

### CP-4 — Legal covenant interpreter

Aliases: CP-4A, CP-4B, CP-4D. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Interprets the legal and covenant package and what it actually permits.

#### CP-4-V01 · Covenant tests and headroom · CR.1

| Field | Specification |
| --- | --- |
| Visual | Bullet chart |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP04/FP05 covenant headroom |
| Input / source registers | T4.9 settled threshold/current/headroom and comparison text; T4C.6–T4C.8 definitions/binding. |
| Eligibility / gap / interpretation guard | Current CR.1 accepts the defined ceiling/floor forms; preserve quantity/strictness and metric identity. A chart does not issue a legal compliance opinion. |
| Delivery priority | First |

#### CP-4-V02 · Capacity, baskets and conditions

| Field | Specification |
| --- | --- |
| Visual | Capacity/conditions matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP04 capacity |
| Input / source registers | T4.10, T4D.6, T4F.3 headroom trace and governing definitions. |
| Eligibility / gap / interpretation guard | Do not add overlapping/shared baskets. Separate legal capacity from cash availability and documentary facts from interpretation. |
| Delivery priority | Next |

#### CP-4-V03 · Entities, guarantees and structural subordination

| Field | Specification |
| --- | --- |
| Visual | Legal relationship map |
| Requirement basis | Method content |
| Current implementation | Broader handoff needed |
| Placement | Documents and structure; recovery intake |
| Input / source registers | T4D.2 governing entities; broader CP-4B handoff for obligors, guarantees, collateral and structural claims. |
| Eligibility / gap / interpretation guard | Current narrow registers alone do not establish a complete entity/security graph. Require explicit edges, applicable document and jurisdiction. |
| Delivery priority | Next |

#### CP-4-V04 · Intercreditor ranking and control

| Field | Specification |
| --- | --- |
| Visual | Priority/control matrix + diagram |
| Requirement basis | Method content |
| Current implementation | Broader handoff needed |
| Placement | Legal analysis; restructuring |
| Input / source registers | Broader CP-4D executed ICA handoff: claim pools, payment/security ranks, enforcement, standstill and releases. |
| Eligibility / gap / interpretation guard | Economic ranking and enforcement control are different; no numerical recovery without CP-4C inputs. This alias duty is broader than the current settled slice. |
| Delivery priority | Next |

#### CP-4-V05 · Tests, cures, amendments and notice deadlines

| Field | Specification |
| --- | --- |
| Visual | Legal calendar lane |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Calendar; Legal |
| Input / source registers | T4D.3 dates/amendments, executed terms and explicit test/notice/cure triggers. |
| Eligibility / gap / interpretation guard | Plot fixed deadlines only when the source or legal module establishes the triggering date and calculation. Otherwise display the relative condition. |
| Delivery priority | Next |

#### CP-4-V06 · Creditor protections and red flags

| Field | Specification |
| --- | --- |
| Visual | Evidence/status matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP04 red flags/protection |
| Input / source registers | T4.11/T4.13, T4F.4 scoring basis and facility/document coverage. |
| Eligibility / gap / interpretation guard | Use only the recorded protection method; no radar chart implying undisclosed weights or complete coverage. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp4.py; src/deploy_vii/methods/cp4.md.

### CP-4C — Restructuring fulcrum

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Models the restructuring scenario, fulcrum security and plan recovery.

#### CP-4C-V01 · Recovery by class and scenario · DR.2

| Field | Specification |
| --- | --- |
| Visual | Grouped recovery columns |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP05 recovery by class |
| Input / source registers | T4E.5 class/scenario recovery and claim identity, linked T4E.2–T4E.4/T4E.9. |
| Eligibility / gap / interpretation guard | Cap only as the owner computes; preserve entity/collateral pools and legal limitations. Do not turn the single-EV slice into a complete multi-entity waterfall. |
| Delivery priority | Next |

#### CP-4C-V02 · Value allocation: supplied scenario 1 · DR.3

| Field | Specification |
| --- | --- |
| Visual | Waterfall |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP05 value allocation/claims |
| Input / source registers | T4E.3/T4E.4/T4E.9 valuation row 1, costs, available value and distributions. |
| Eligibility / gap / interpretation guard | Scenario identity comes from its source row. The current producer maps up to three rows in order; do not invent absent downside/stress cases or assume a legal pool order. |
| Delivery priority | Next |

#### CP-4C-V03 · Value allocation: supplied scenario 2 · DR.4

| Field | Specification |
| --- | --- |
| Visual | Waterfall |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP05 value allocation/claims |
| Input / source registers | T4E.3/T4E.4/T4E.9 valuation row 2, costs, available value and distributions. |
| Eligibility / gap / interpretation guard | Scenario identity comes from its source row. The current producer maps up to three rows in order; do not invent absent downside/stress cases or assume a legal pool order. |
| Delivery priority | Next |

#### CP-4C-V04 · Value allocation: supplied scenario 3 · DR.5

| Field | Specification |
| --- | --- |
| Visual | Waterfall |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP05 value allocation/claims |
| Input / source registers | T4E.3/T4E.4/T4E.9 valuation row 3, costs, available value and distributions. |
| Eligibility / gap / interpretation guard | Scenario identity comes from its source row. The current producer maps up to three rows in order; do not invent absent downside/stress cases or assume a legal pool order. |
| Delivery priority | Next |

#### CP-4C-V05 · Fulcrum, attachment and plan treatment

| Field | Specification |
| --- | --- |
| Visual | Claim-ranking/attachment map |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Restructuring analysis |
| Input / source registers | T4E.2/T4E.6–T4E.8 claim balances, attachment/detachment, fulcrum and plan treatment. |
| Eligibility / gap / interpretation guard | No double-counting guarantees; different pools may have different marginal rank. Conditional plan terms are not realised recoveries. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp4c.py; src/deploy_vii/methods/cp4c.md.

### CP-5 — Evidence trace validator

Aliases: CP-5A. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Validates the evidence trace behind every material claim in the run.

#### CP-5-V01 · Material-claim support and gaps

| Field | Specification |
| --- | --- |
| Visual | Evidence coverage matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Evidence; Overview |
| Input / source registers | T5.1–T5.9 and T5B.1–T5B.8 evaluated set, citations, resolutions and support verdicts. |
| Eligibility / gap / interpretation guard | Denominator is the explicit evaluated/required set. Unassessed differs from unsupported. A support count is not a financial completeness or credit score. |
| Delivery priority | Next |

#### CP-5-V02 · Contradictions and lineage

| Field | Specification |
| --- | --- |
| Visual | Support/contradiction graph |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Evidence inspector |
| Input / source registers | Claim/source IDs, cross-module contradictions, exact source versions and derived-fact identities. |
| Eligibility / gap / interpretation guard | Use labelled edges for support, contradiction and unresolved. No automatic causal or confidence weight based on edge count. |
| Delivery priority | Next |

#### CP-5-V03 · Findings and remediation

| Field | Specification |
| --- | --- |
| Visual | Issue/status matrix with counts |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Run readiness; Evidence |
| Input / source registers | Findings, severity, affected consumer, repair action, status and evidence pins. |
| Eligibility / gap / interpretation guard | Group repeated consequences by root cause; keep critical unresolved issues visible. Do not inflate counts with repeated warning text. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp5.py; src/deploy_vii/methods/cp5.md.

### CP-6 — Ic debate challenge

Aliases: CP-6A. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Runs the investment-committee debate and challenge, producing an action bias.

#### CP-6-V01 · Committee challenge and resolution

| Field | Specification |
| --- | --- |
| Visual | Thesis → challenge → response → resolution map |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP01 committee challenge; FP06 thesis/catalysts |
| Input / source registers | T6A.4/T6A.6/T6A.7, committee_challenge and final bias. |
| Eligibility / gap / interpretation guard | Use the actual chair/analyst conclusions; no simulated votes, inferred agreement or averaged confidence score. |
| Delivery priority | Next |

#### CP-6-V02 · Action bias, conditions and monitoring

| Field | Specification |
| --- | --- |
| Visual | Decision/conditions matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Call band; portfolio decision |
| Input / source registers | T6-FINAL, unresolved risks, evidence weighting, monitoring actions and CP-2 thesis references. |
| Eligibility / gap / interpretation guard | Recommendation and sizing remain the module/user decision; diagramming is not trade execution. No completion from a generated memo alone. |
| Delivery priority | Next |

#### CP-6-V03 · Portfolio limit headroom · PD.1

| Field | Specification |
| --- | --- |
| Visual | Exposure bars with limit ticks |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP06 Portfolio Fit; shared Fit destination |
| Input / source registers | Selected portfolio inputs/evaluation results: current/proposed exposure, NAV denominator, applicable limits and instrument eligibility. |
| Eligibility / gap / interpretation guard | PD.1 has no current bound figure producer. Shared portfolio evaluation provides values; CP-6 owns interpretation, delivery renders. CP-6A portfolio-debate tables are registered but not bound by current CP-6. No new analytical owner or invented holdings. |
| Delivery priority | Next |

#### CP-6-V04 · Catalysts and monitoring commitments

| Field | Specification |
| --- | --- |
| Visual | Decision/watch calendar lane |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar; Decision |
| Input / source registers | Explicit decision dates, assigned review dates, catalyst conditions and sources. |
| Eligibility / gap / interpretation guard | Undated conditions stay a watchlist. A user-entered reminder is labelled separately from a sourced issuer event. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp6.py; src/deploy_vii/methods/cp6.md.

### CP-8 — Deliverable comparison

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Compares deliverables from prior runs with the latest current run and explains material changes and unresolved differences.

#### CP-8-V01 · Report section changes

| Field | Specification |
| --- | --- |
| Visual | Section change strip |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Comparison |
| Input / source registers | All five report sections table: section, prior → current, why/effect and evidence. |
| Eligibility / gap / interpretation guard | Show Unchanged and Revised in the handoff’s words. A revised report section is not an issuer change. |
| Delivery priority | Next |

#### CP-8-V02 · Prior and current material changes

| Field | Specification |
| --- | --- |
| Visual | Prior/current comparison rows |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Comparison |
| Input / source registers | Material analytical changes table: item, prior deliverable, current deliverable, classification/effect and evidence. |
| Eligibility / gap / interpretation guard | Keep values, periods, assumptions and sources as the handoff states them. Added content does not upgrade assurance or show the issuer improved. |
| Delivery priority | Next |

#### CP-8-V03 · Regressions and recheck

| Field | Specification |
| --- | --- |
| Visual | Regression list with recheck status |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Comparison |
| Input / source registers | Unresolved regressions table, the CP-8 recheck table and the prior, current and repaired report identities. |
| Eligibility / gap / interpretation guard | A closed request applies to that delivery revision. It does not resolve the underlying creditor evidence gap. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methods/cp8.md; runs/tdg-run-comparison-001/CP-8.md; runs/tdg-run-comparison-001/CP-8-recheck.md.

### CP-L10 — Financial change screen

Aliases: CP-L20, CP-L23, CP-L30, CP-L40. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Runs a bounded LITE screening synthesis for CP-1, CP-1B.

#### CP-L10-V01 · Seven-topic financial change screen

| Field | Specification |
| --- | --- |
| Visual | Materiality matrix + paired deltas |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Screening; change analysis |
| Input / source registers | TL10.1–TL10.5: EBITDA, FCF, cash, total/net debt, leverage and coverage for two quarters in one fiscal year. |
| Eligibility / gap / interpretation guard | Display exact current policy materiality and denominator-zero handling; no cross-issuer rank or invented multi-year history. Other Lite table families stay registered but unproduced. |
| Delivery priority | Next |

#### CP-L10-V02 · Upgrade disposition and handoff

| Field | Specification |
| --- | --- |
| Visual | Topic → full-owner routing map |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Screening; Run planning |
| Input / source registers | Material/Watch judgments, ranked items, next owner and explicit credit transmission. |
| Eligibility / gap / interpretation guard | This is a bounded change screen, not a full credit/recovery/legal recommendation; show unsupported topics and unresolved downstream consumption. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cpl10.py; src/deploy_vii/methods/cpl10.md.

### CP-MODEL — Model (HTML destination and calculation JSON)

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Publication role: Model HTML destination and calculation JSON; reuse analytical figures. A workbook is not a guaranteed output of the current core contract.

#### CP-MODEL-V01 · Published model and calculation provenance

| Field | Specification |
| --- | --- |
| Visual | Financial period grid + lineage inspector |
| Requirement basis | Operational |
| Current implementation | Table/content only |
| Placement | Model; Reports |
| Input / source registers | Accepted/restricted CP-1 facts, model destination, calculation JSON, publication/source hashes. |
| Eligibility / gap / interpretation guard | Reuse the existing Model destination and chart data; do not rerun analytics solely for delivery. Current core publication is HTML/calculation JSON, not a workbook. |
| Delivery priority | First |

#### CP-MODEL-V02 · Shared chart collection and availability

| Field | Specification |
| --- | --- |
| Visual | Chart index with table/source drill-down |
| Requirement basis | Operational |
| Current implementation | New view |
| Placement | Overview; Model; Files |
| Input / source registers | Eligible figures S.1–S.6 and other selected-owner outputs, state, limitation and exact data revision. |
| Eligibility / gap / interpretation guard | CP-MODEL publishes, it does not own every analytical chart. One source series is reused across destinations; no duplicate calculations. |
| Delivery priority | First |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp_model.py.

### CP-OS — Workflow orchestration and delivery completion

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Active role override: orchestrates analytical modules, handoffs, bounded execution and separate delivery; do not inherit the older registry’s navigation-only restriction.

#### CP-OS-V01 · End-to-end execution and delivery

| Field | Specification |
| --- | --- |
| Visual | Dependency/status view + execution timeline |
| Requirement basis | Operational |
| Current implementation | New view |
| Placement | Run progress |
| Input / source registers | Actual module states, source/handoff/delivery verification, selected plan and recorded timestamps. |
| Eligibility / gap / interpretation guard | User instruction makes CP-OS the active orchestrator despite the older catalog label. This view observes that orchestrator; it is not a competing runner. Sequence-only data uses ordinal steps, not invented elapsed-time bars. |
| Delivery priority | First |

#### CP-OS-V02 · Budget and spend

| Field | Specification |
| --- | --- |
| Visual | Spend-to-cap bar + event ledger |
| Requirement basis | Operational |
| Current implementation | Table/content only |
| Placement | Run progress; Review |
| Input / source registers | Approved cap, actual recorded provider costs, bounded retries and unknown/pending costs. |
| Eligibility / gap / interpretation guard | Unknown cost is not zero. Keep workflow completion, budget progress and credit assessment separate; approval precedes Start. |
| Delivery priority | First |

#### CP-OS-V03 · Issuer, run, revision and file navigation

| Field | Specification |
| --- | --- |
| Visual | Persistent selectors + file/document workspace |
| Requirement basis | Operational |
| Current implementation | New view |
| Placement | App shell; Overview/Reports/Sources/Files |
| Input / source registers | Verified issuer/run identity, dates, artifact lineage, source/analysis/export file roles and revision relationships. |
| Eligibility / gap / interpretation guard | Do not merge unrelated delivery records into one revision chain without evidence. Maintain issuer/run/as-of context when moving between visuals and files. |
| Delivery priority | First |

Source anchors: src/deploy_vii/methodology.json; apps/issuer-library/jobs.go; src/deploy_workflow/cpos_status.py.

### CP-2D — Liquidity cash flow bridge

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Builds the near-term liquidity bridge and cash runway.

#### CP-2D-V01 · Sources and uses / liquidity bridge · CR.2

| Field | Specification |
| --- | --- |
| Visual | Waterfall |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP04/FP05 liquidity runway |
| Input / source registers | T2E.1/T2E.3 settled bridge points and accessible liquidity components. |
| Eligibility / gap / interpretation guard | Use the module’s signed values and timing; preserve restricted/trapped cash and uncertain facility access. The chart never recomputes a bridge. |
| Delivery priority | First |

#### CP-2D-V02 · Cash runway and minimum liquidity

| Field | Specification |
| --- | --- |
| Visual | Period line/step view |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Liquidity; Overview |
| Input / source registers | T2E.2/T2E.3 liquidity position/runway and any supplied observation periods/minimum. |
| Eligibility / gap / interpretation guard | No monthly path from an annual total. Cash runway is conditional on the stated operating-inflow and mandatory-use assumptions. |
| Delivery priority | Next |

#### CP-2D-V03 · Maturities, uses and funding dates

| Field | Specification |
| --- | --- |
| Visual | Financing calendar lane |
| Requirement basis | Method content |
| Current implementation | New view |
| Placement | Calendar; liquidity |
| Input / source registers | T2E.4 maturities, dated obligations and T2E.5 funding-gap windows. |
| Eligibility / gap / interpretation guard | Maturity is not a refinancing commitment. Avoid double-counting the same facility from CP-1 and CP-3C. |
| Delivery priority | Next |

#### CP-2D-V04 · Accessible versus restricted resources

| Field | Specification |
| --- | --- |
| Visual | Liquidity-access matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Liquidity |
| Input / source registers | T2E.1/T2E.2 source amount, currency, jurisdiction/entity, availability and restrictions where provided. |
| Eligibility / gap / interpretation guard | No gross cash-to-accessible-cash assumption; never aggregate currencies without a supplied conversion. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp2d.py; src/deploy_vii/methods/cp2d.md.

### CP-3D — Market implied risk

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Assesses market-implied credit risk and trading technicals.

#### CP-3D-V01 · Yield against maturity · RV.1

| Field | Specification |
| --- | --- |
| Visual | Numeric-x scatter/curve |
| Requirement basis | Design |
| Current implementation | Design gap |
| Placement | FP03 yield against maturity |
| Input / source registers | T3E.* compatible instrument yield/spread, maturity, quote date and source class. |
| Eligibility / gap / interpretation guard | RV.1 needs a bound producer and numeric-maturity geometry; the generic categorical line renderer is not an equivalent scatter plot. Do not mix YTM, discount margin and spread on one scale. |
| Delivery priority | Next |

#### CP-3D-V02 · Market-implied versus fundamental risk

| Field | Specification |
| --- | --- |
| Visual | Assumption/result comparison |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP03 market against fundamentals |
| Input / source registers | T3E.1–T3E.9 stated recovery/horizon assumptions, market inputs and computed implied-risk outputs. |
| Eligibility / gap / interpretation guard | Label model-implied under stated assumptions; not an objective default forecast or a CP-2H migration probability. Respect observed/indicative and stale quote states. |
| Delivery priority | Next |

#### CP-3D-V03 · Trading technicals and quote evidence

| Field | Specification |
| --- | --- |
| Visual | Quote/technicals matrix; history only if supplied |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Market analysis |
| Input / source registers | T3E.2–T3E.10 bid/offer, time, source and technical assessments. |
| Eligibility / gap / interpretation guard | A single quote does not make a historical trend. No fabricated price series or interpolation through stale observations. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp3d.py; src/deploy_vii/methods/cp3d.md.

### CP-3C — Refinancing lme risk

Aliases: none. Same owner and execution; aliases do not generate duplicate charts or a second module run.

Registered purpose: Assesses refinancing and liability-management risk before or during distress.

#### CP-3C-V01 · Refinancing need by maturity · CR.3

| Field | Specification |
| --- | --- |
| Visual | Grouped columns |
| Requirement basis | Design |
| Current implementation | Figure producer |
| Placement | FP04 funding gap; FP05 funding gap/LME |
| Input / source registers | T3D.1 settled maturity/funding-need points and supplied resources. |
| Eligibility / gap / interpretation guard | CR.3 needs exact maturity and funding basis. No committed refinancing from a suggested path; no double-counting shared resources. |
| Delivery priority | First |

#### CP-3C-V02 · Refinancing burden and cost sensitivity

| Field | Specification |
| --- | --- |
| Visual | Discrete cost comparison |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | Refinancing analysis |
| Input / source registers | T3D.2/T3D.3 burden/cost outputs and explicit stress assumptions. |
| Eligibility / gap / interpretation guard | Scenario financing costs are not executable quotes; preserve currency, call costs, fees and missing terms. |
| Delivery priority | Next |

#### CP-3C-V03 · Refinancing and LME alternatives

| Field | Specification |
| --- | --- |
| Visual | Path/conditions matrix |
| Requirement basis | Method content |
| Current implementation | Table/content only |
| Placement | FP04 refinancing paths/LME |
| Input / source registers | T3D.4–T3D.7 creditor position, LME capacity, paths and judgments; CP-4 legal conditions. |
| Eligibility / gap / interpretation guard | Legal capacity, demonstrated willingness and market feasibility are separate. Do not convert possible paths into dated commitments. |
| Delivery priority | Next |

#### CP-3C-V04 · Execution windows and decision deadlines

| Field | Specification |
| --- | --- |
| Visual | Refinancing calendar lane |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Calendar |
| Input / source registers | Source-dated maturities/call windows, explicit deadlines and analyst review milestones. |
| Eligibility / gap / interpretation guard | Show analyst milestones separately from contractual deadlines; preserve contingent triggers. |
| Delivery priority | Next |

Source anchors: src/deploy_vii/methodology.json; src/deploy_vii/bindings/cp3c.py; src/deploy_vii/methods/cp3c.md.

### DELIVERY — Separate delivery assembly (CP-MEMO replacement)

#### DELIVERY-V01 · Pathway composition and visual eligibility

| Field | Specification |
| --- | --- |
| Visual | Six pathway front pages + availability index |
| Requirement basis | Operational |
| Current implementation | Table/content only |
| Placement | Reports |
| Input / source registers | Selected handoffs, preset blocks, registered figure producers and explicit gaps. |
| Eligibility / gap / interpretation guard | Separate delivery replaces CP-MEMO; no extra memo analytical run. Existing six retained snapshots have only five narrative blocks and zero charts, not proof of populated visual delivery. |
| Delivery priority | First |

#### DELIVERY-V02 · Cross-module issuer event calendar

| Field | Specification |
| --- | --- |
| Visual | Lane timeline + accessible event table |
| Requirement basis | Proposed |
| Current implementation | New view |
| Placement | Overview; Calendar |
| Input / source registers | EVT-01–EVT-09 event contributions from selected dated handoffs; see event contract. |
| Eligibility / gap / interpretation guard | Aggregate already produced evidence; no new analysis, guessed dates or duplicate event counting. Keep scenario and historical/planned lanes distinct. |
| Delivery priority | First |

#### DELIVERY-V03 · Export and source parity

| Field | Specification |
| --- | --- |
| Visual | Figure/table/source manifest |
| Requirement basis | Operational |
| Current implementation | New view |
| Placement | Reports; Files |
| Input / source registers | Exact chart points/table values, source pins, periods, units, basis, limitations and available export formats. |
| Eligibility / gap / interpretation guard | Standalone HTML embeds charts/fonts/symbol offline. Preserve archived originals and verify each new chart against its handoff; do not claim unsupported exports. |
| Delivery priority | First |

Source anchors: src/deploy_workflow/handoff_delivery.py; src/deploy_vii/render.py; src/deploy_vii/report_view.py.

## Alias coverage and separate duties

| Alias | Canonical owner | Display consequence |
| --- | --- | --- |
| CP-PARSE | CP-0 | Same CP-0 views; no additional execution or duplicate graph. |
| CP-2C | CP-1A | Same CP-1A views; no additional execution or duplicate graph. |
| CP-1E | CP-1D | Same CP-1D views; no additional execution or duplicate graph. |
| CP-2B | CP-2A | Same CP-2A views; no additional execution or duplicate graph. |
| CP-2F | CP-2E | Same CP-2E views; no additional execution or duplicate graph. |
| CP-3A | CP-3 | Same CP-3 views; no additional execution or duplicate graph. |
| CP-3B | CP-3 | Same CP-3 views; no additional execution or duplicate graph. |
| CP-4A | CP-4 | Same CP-4 views; no additional execution or duplicate graph. |
| CP-4B | CP-4 | Same CP-4 views; no additional execution or duplicate graph. |
| CP-4D | CP-4 | Same CP-4 views; no additional execution or duplicate graph. |
| CP-5A | CP-5 | Same CP-5 views; no additional execution or duplicate graph. |
| CP-6A | CP-6 | Same CP-6 views; no additional execution or duplicate graph. |
| CP-L20 | CP-L10 | Same CP-L10 views; no additional execution or duplicate graph. |
| CP-L23 | CP-L10 | Same CP-L10 views; no additional execution or duplicate graph. |
| CP-L30 | CP-L10 | Same CP-L10 views; no additional execution or duplicate graph. |
| CP-L40 | CP-L10 | Same CP-L10 views; no additional execution or duplicate graph. |

Preserve broader alias duties explicitly: CP-4A = covenant/capacity conditions; CP-4B = entities/guarantees/structural subordination; CP-4D = intercreditor ranking/enforcement/control. Current bounded CP-4 tables do not prove all three duties. CP-3A/3B require their instrument/recovery distinctions; CP-6A portfolio debate is broader than the currently bound CP-6 challenge. CP-L20/L23/L30/L40 remain aliases of the bounded CP-L10 change screen, not proof that every historical Lite table is produced.

## Shared event calendar and timeline

Required information already exists in some module registers, notably CP-1A events_timeline. The shared graphical calendar is a proposed delivery view over those handoffs. Default to the selected issuer/run/as-of; optionally compare verified runs while retaining their dates and source identities. Use historical, scheduled/conditional and projected lanes with a readable table/list twin.

| Lane | Event family | Owner(s) | Input anchors | What may appear |
| --- | --- | --- | --- | --- |
| EVT-01 | Corporate and ownership | CP-1A | events_timeline; transaction_summary; ownership_register | M&A, disposals, ownership changes, distributions, announced versus completed actions. |
| EVT-02 | Financial reporting and guidance | CP-0 / CP-1B / CP-DR | Source inventory; T1B.3 guidance; retained research | Publication/release dates and explicitly announced future reporting dates; period end is a different field. |
| EVT-03 | Debt and instrument terms | CP-1 / CP-2D / CP-3 | T4.18; T2E.4; sourced instrument terms | Maturities; coupon/call/put/reset dates only where explicitly provided by the responsible module. |
| EVT-04 | Legal and covenant events | CP-4 | T4D.3; governing document/clauses | Testing dates, amendments, notices, cure/standstill conditions and deadlines with established anchors. |
| EVT-05 | Ratings and agency events | CP-2H | T2R.2/T2R.3 and source-dated agency actions | Known rating/outlook actions and scheduled reviews; full rating history needs additional handoff data. |
| EVT-06 | Refinancing and LME | CP-3C | T3D.1/T3D.6/T3D.7 plus CP-4 legal terms | Sourced deadlines and explicit execution windows; possible routes stay conditional. |
| EVT-07 | Catalysts and monitoring | CP-DR / CP-2 / CP-6 | Dossier; T2.11; T6A.7/final monitoring conditions | Source-dated catalysts, explicit review dates and user reminders, each carrying its own provenance. |
| EVT-08 | Report versions compared | CP-8 | Prior and current report identities | Financial base and report dates; historical report versions stay separate from current issuer information. |
| EVT-09 | Projected breakpoints | CP-2G / CP-2H | T2H.7/T2H.8; T2R.6 | Forecast fiscal-year intervals in a visibly projected lane; no exact day or probability inferred. |

### Event data contract

| Group | Fields |
| --- | --- |
| Identity | event_id; issuer_id; run_id; owning_module; source_event_id; related facility/security/entity IDs |
| Display | title; event_type; lane; short creditor implication copied from the handoff; module/document links |
| Dates | event_date or start/end; original_date_text; precision (time/day/month/quarter/year/unknown); timezone only for a known timestamp; reporting_period separately |
| Evidence | source path/ID; document version/hash; locator/quote; handoff/fact reference; source publication date; source as-of |
| State | completed/announced/scheduled/conditional/cancelled/superseded/unknown; actual versus forecast; user reminder versus sourced event |
| Qualification | date confidence only if supplied; dependency/trigger; scenario ID; limitation; conflict/supersedes links; recorded confirmation status |

### Timeline behaviour and date rules

- Each event opens its source inspector and responsible module; allow filtering by owner, event type, facility/entity, status and actual/planned/projected. Preserve issuer/run/revision context.
- Use the report’s as-of as the main vertical marker. Publication time, event time, reporting period and ingestion time stay separate. A computer-today marker, if offered, is separately labelled.
- Exact day/time = milestone; month/quarter/year = interval with precision label; duration = span only when both ends exist. Unknown dates stay in the Undated/conditional list, not on an invented day.
- Legal notice/cure/standstill dates require an established triggering event and a deadline already determined by the legal owner. A delivery-only calendar must not interpret clauses or invent a deadline.
- Fiscal-year forecast breakpoints occupy a projected band. Static CP-2A scenarios have no time axis. Rating outlook is not a scheduled rating action.
- Merge duplicate contributions only with established event identity. Show conflicting dates as a conflict, and keep cancelled/superseded events inspectable.
- User-created review reminders are separately labelled. Optional calendar export is a future feature and never writes to a user/external calendar automatically.
- Operational CP-OS execution belongs to Run progress, not the issuer-credit calendar. Keep publication dates/candidate revisions accessible so stale documents remain obvious.

## Cross-cutting data, visual and accessibility rules

- Required means required for a selected pathway/module and eligible evidence. It does not require every run to populate every visual, and it authorizes no new analytical execution.
- Basis D (Design) identifies a named normative figure. M (Method content) identifies an existing required output; a new graphical treatment of that output is still a proposal. P (Proposed) and O (Operational) are explicit design recommendations/current user workflow needs, not inherited analytical instructions.
- Implementation states describe reusable code, not issuer acceptance: Figure producer = registered adapter exists; Table/content only = information is rendered but the proposed graphic is not; Design gap = specified figure lacks a producer; Unavailable frame = explicit n/a only; New view = new presentation work; Broader handoff needed = current slice does not supply the full required content.
- Every plotted value keeps its exact fact identity, period/duration, perimeter, quantity family, currency/scale, basis, source hash/locator and calculation lineage. Delivery must not invent analysis, normalize a ratio, calculate a new legal deadline or silently convert currency.
- Each quantitative chart has a matching table twin and keyboard-focusable marks that open evidence. Use cited/calculated/synthetic provenance where declared; otherwise Not classified beside Source. A gap without a producer gap ID states its reason without inventing a G-number.
- Missing, zero, not applicable, not meaningful, stale, not run, outside pathway, blocked and unassessed remain distinct. Selected but unavailable important charts show a reason and required input/action; charts outside the pathway do not pretend to be missing.
- Historical actuals, issuer guidance, analyst assumptions, model forecasts and fictional synthetic fixtures are different states. Forecast scenarios are not automatically synthetic data. Dashed/hatch/word treatments supplement colour.
- Use separate panels for amounts, multiples, percentages and percentage points. No mixed bases on an axis, no misleading categorical spacing for numeric maturities, no smooth line through unobserved periods, and no decorative dashboard chart without a defined question.
- Qualitative diagrams show supported relationships and categorical judgments. No probability, heat intensity, edge weight, sentiment or credit score is inferred from prose, source counts or document/module completion.
- Timelines retain date precision. Month/quarter/year become labelled intervals; unknown dates remain in an Undated list; relative/conditional deadlines stay relative until the responsible module supplies the anchored result. Do not use the computer date as the report as-of.
- Deduplicate shared events by issuer, underlying action and source identity, not by title alone. Conflicting dates remain a conflict; superseded/cancelled events remain inspectable. One maturity appears once with linked module assessments.
- Run progress/budget timelines are operational views separate from the issuer event calendar. Charts, source documents and exports keep persistent issuer/run/as-of/revision context and deep links back to the evidence.
- Print/export must preserve labels, gap notes, units, table twins and source identity. Use the existing offline SVG/HTML renderer and embedded fonts/symbol; no external chart/CDN dependency. Keep dense numerical tables wide and cap individual narrative text rather than comparison containers.

## Implementation gaps and reuse order

| Area | Items | Required treatment |
| --- | --- | --- |
| Existing figures to reconnect | S.1–S.5; RV.3a/b; CR.1–CR.3; DR.2–DR.5 | Reuse selected fact adapters; prove each populated figure from actual retained handoffs. Existing fixture success is not real-issuer qualification. |
| Named design figures without a producer | S.6; EU.1–EU.3; RV.1; PD.1 | Existing primitives cover much geometry. Add typed adapters and the missing numeric-x/dumbbell treatment where needed; do not substitute a visually similar but semantically wrong plot. |
| Rating frame | DR.6 | Current implementation is unavailable-only and synthetic-source-specific. A real agency-derived headroom display needs a separately qualified producer and compatible definitions; probabilities remain prohibited. |
| Qualitative visual components | Timeline/calendar, entity/control map, argument/lineage graph, evidence/condition matrix | Build reusable offline semantic HTML/SVG presentations. Keep sources and categorical qualification visible; do not add a second analytical or orchestration layer. |
| Important capability limits | CP-1 non-USD chart whitelist; CP-1B limited KPI pairs; CP-2A static period; CP-2E restricted shocks; CP-2G annual/no refinancing; CP-2H no rating history; CP-8 one retained report pair; broader CP-4 alias duties | Surface these limits in eligibility decisions. Missing data/unsupported scope require an explicit gap or targeted repair, not inferred visual values. |
| Currently loaded reports | Six retained narrative snapshots; five blocks each; zero chart figures | The old handoff_delivery SECTIONS scope excludes graphics and records CP-MODEL unpublished. New visual delivery must use a new verified revision; preserve those archived originals. |

| Phase | Scope |
| --- | --- |
| 1 — Restore existing quantitative views | Reconnect the implemented figure producers and numerical tables with retained handoff evidence; preserve all input qualifications and chart/table parity. |
| 2 — Make navigation and events useful | Persistent issuer/run/revision context; in-app source/file viewing; CP-1A event timeline and shared event table with explicit date precision. |
| 3 — Complete named design gaps | S.6, EU.1–EU.3, RV.1 and PD.1 once their typed inputs/calculation contracts are qualified; handle DR.6 as a separate restriction. |
| 4 — Add qualitative views | Entity/ownership/control maps, evidence and argument maps, scenario/monitoring matrices and conditional calendar lanes; keep prose available. |
| 5 — Qualify each owner end to end | For one module at a time, compare the actual retained output with instructions and issuer evidence, then prove downstream delivery. An older/alternative issuer may establish bounded function with issuer/date labels. |

## Acceptance checks for each delivered visual

- Trace each displayed mark/node/event to the selected retained handoff and source, preserving original value, unit, date, perimeter, definition and limitation. Cross-check against independent expected values, not the chart’s own calculation.
- Quantitative mark labels and table-twin cells must match. Test missing/zero/not-meaningful values, negative signs, incompatible units, stale inputs, revised sources and duplicated events.
- Qualitative maps must preserve actor/relationship direction, stated control versus ownership, interpretation versus fact and unresolved conflicts. No extra conclusion may appear in a diagram.
- Test issuer/run/file/revision navigation, source opening, keyboard focus/return and HTML export offline at 1280, 1366, 1440 and 1500px, including the 1350/1351 navigation boundary.
- The calendar must pass exact/partial/unknown/conditional date cases, fiscal versus calendar periods, cancellation/supersession and same-title/different-event cases.
- A populated figure from synthetic fixtures is component proof only. Complete module acceptance requires the actual retained response, downstream consumption and checked deliverables for the labelled issuer/date scope.
- If required handoff content is absent, retain the explicit gap or request targeted repair through CP-OS. Never run a competing workflow or silently invent replacements to populate a chart.

## Source revision record

Catalogue date: 4 November 2026. Worktree base commit 1a21c6cf4c52402c726b3098700f9fadd271bf49. The inspected tree has uncommitted session work, so the content hashes below, not that base alone, identify this mapping’s source revisions. Analytical scope selections retain the imported correction chain documented in METHODOLOGY-REVIEW.md. Historical review/approval text is evidence, not new authorization.

Not re-audited since this catalogue date: merging the launcher (PR #1) and joining the app changed `apps/issuer-library/jobs.go`, `src/deploy_vii/methodology.json`, `src/deploy_vii/registry.py`, `src/deploy_vii/report_view.py`, `src/deploy_workflow/handoff_delivery.py`, `src/deploy_workflow/owners/cpos.py` and `src/deploy_vii/methods/{cp0,cp2d,cp3,cp6}.md`. Their rows below still show the revisions this map was audited against.

| Source snapshot | SHA-256 |
| --- | --- |
| src/deploy_workflow/financial_series.py | c313d06cd3eb7a81d8cae4adcdeee248057bdc499df008b2072c85103ade021f |
| src/deploy_workflow/liquidity_series.py | 0fc78b5f4117d218b188a9635d3f22e8adddc3e66ca658117cac6c8e905f5707 |
| src/deploy_workflow/owners/cp8.py | 21c84ea849976f8c88e545e547ae749a22bd32e62abbb4b168ab8187439c5b6d |
| src/deploy_workflow/owners/cp2h.py | e13c1e1abe984d9f7d926408ce9cc0bce8ed55786470743186a50d12aef7e4ad |
| src/deploy_workflow/prompts/texts/earnings_delta.md | da1ba968192f15b507cca455bda7fba9e5280364134d8e7b4acafd7c8be629f2 |
| apps/issuer-library/jobs.go | 4457bf2006bab7be4fb07e5658c6cf71f2722a2b0c162abd4dad0f95fb83d336 |
| src/deploy_workflow/cpos_status.py | 9a32f9de65f131a328a098d42d6b0246e2c53f36e2fb4ff86c8d07780853c4d3 |
| METHODOLOGY-REVIEW.md | 4ce8ec949ebe0023e40c41b5b3bc916a30c642985cf050834fe889d63d7031a7 |
| AGENTS.md | fb690d4ff4bae921dcfc825db0fc6e2ec5259b44fe105aa98815455389034da2 |
| src/deploy_vii/methodology.json | aea67de94e90d2c5ce513c5898d9b7afdd10c849a082bb1f61a31bb07baf347e |
| src/deploy_vii/registry.py | 19ec267dff71aa89cbfdfbece02e1a44f6800306572e15f16029d3bd23dc880a |
| src/deploy_vii/report_view.py | 004db5dee5662f4b1618e5510fe1bcc876f44557902c4d1b63185b5816c0d967 |
| src/deploy_vii/charts.py | a1805bca3e9bc6aa21383be158cc677b3ea6fbe2b95b8882ac045bfbe985e591 |
| src/deploy_vii/distressed_figures.py | d074e7d5bc1c7a8e95899c6c57f798ab94c45ace34e345ba574a3dcc6459639f |
| src/deploy_vii/render.py | 58f1b503f0a40efc5895c1612eaa707b74a056af2c41f5a82cebd5aae7dc9730 |
| src/deploy_vii/inputs/portfolio.py | ed239e92269fb550601e76ccaf84aaf05b739428a265781cb07dacc7ffbbe048 |
| src/deploy_workflow/handoff_delivery.py | c5aef342cfaf2e14c0431157ef814fe6ba19621fab1fea47e80b0e19e43bf227 |
| src/deploy_workflow/restructuring_series.py | 40ff6cdea8083c8880f1dc8b2418c27884fa7e1548e987055938331e1a1a9c6c |
| src/deploy_vii/methods/cp0.md | 68b7bf93b09625ff5ce7f7e4d0930ed27f09959da587509eba96b06ce9ef2a6f |
| src/deploy_vii/methods/cp1a.md | 075ade1573851dba48e763edacdbe76d3d0ff240302c5e58d7cb5671ae2e3929 |
| src/deploy_vii/methods/cpdr.md | 9cf2bf6dac6a8dac039e0d63a2d5cb6aee444284ec14af7e6cac29c16fce86ec |
| src/deploy_vii/methods/cp1c.md | 8836094d4ce388c36941d8a1c7e34f6e01e53121e127c3c2c5c077af89a0d1b0 |
| src/deploy_vii/methods/cp1d.md | 47bc1422b52c5b66cf9a766ca0295c01c9292b2e7724aa9a4229514c1174e3da |
| src/deploy_vii/methods/cp2.md | 9ddd2ab22b5aeab99054cf82ebfb7f03ef49422678be08374566b96dc18dcbd1 |
| src/deploy_vii/methods/cp2a.md | 28be81bfb97a83e739e4a514612a2db3bf12b72480128f54c66c33fc2ab06236 |
| src/deploy_vii/methods/cp2e.md | f257dc2c8f7884a7a3eb720cdee9292e391d93e0e6301d0a09865588d07ea99b |
| src/deploy_vii/methods/cp2g.md | 684374859fd13fe2cfd262dcbbf041f78370367215bc0a0a371752bc78beb63a |
| src/deploy_vii/methods/cp2h.md | f221e63327c3a72e5c8e8fbcd937b39124e6d12df8f709673eb0e7112d26d8de |
| src/deploy_vii/methods/cp3.md | 6009dcca0feac906bcb8a612a36e16b81552c68aadc280aa25e41af15a1c5bfb |
| src/deploy_vii/methods/cp4.md | 493f57fd0f4176c757cc310fcaa8809433c7aa6f0c3bee73519edc44effc1118 |
| src/deploy_vii/methods/cp4c.md | 5d8f43c53a062b875430d4eef5cfc806d9b32d4a2ebfc595b82e951837218432 |
| src/deploy_vii/methods/cp5.md | 81cf6bea9b56ad63fd9cc38c32bf4cef9b9c1e48b750f8c803cb4d8874d64d67 |
| src/deploy_vii/methods/cp6.md | 324595e417e5bf903a27040220e87d1221f9f6d89245cb62f73b9b0ad2182c5d |
| src/deploy_vii/methods/cp8.md | 51aeabbb16f5fabde66f46937f5a3ad0a3e149b3b102843918e3cb2486cc10ed |
| src/deploy_vii/methods/cpl10.md | ee50144d149a9898b1452ffee8a215bc6d04f77ffe335f8f7c6d6ca1ddcf781e |
| src/deploy_vii/methods/cp2d.md | df8ec4b240315b7837144143b10b4861faf47826612d48f4be0e24f2ea5edcdd |
| src/deploy_vii/methods/cp3d.md | 2c70e59915af2c167915fb05ccca4019b70486688abfb52683fd1e665f259e15 |
| src/deploy_vii/methods/cp3c.md | b66438b5b6e17d8e8e21814c488e7a75f73c87544ee79bce5d338626f488de72 |
| src/deploy_workflow/owners/cp1a.py | 25e0918995eb887da6ea487a0d9463ccac3a29887c83f818ce038397cf9ee4b2 |
| src/deploy_workflow/owners/cp1b.py | db6d9307bb2f39abab7809a1a1660db0a9b2ec01a3523936d912500dd78b982d |
| src/deploy_workflow/owners/cpdr.py | c9e840d14b4235f58e93d3306698ec2d39c9e2152a0cde5a295fe009bb5b4336 |
| src/deploy_workflow/owners/cp1c.py | 85e0b29bc0320f48ce724278b543f1d7425856b66b6f8bb4238cdc572a96cf33 |
| src/deploy_workflow/owners/cp1d.py | f9544b356fd0b7b54fe2d4230958b349092e462c0a3c581b32968b081ab783fb |
| src/deploy_workflow/owners/cp2.py | 902dea0e690a9054b06e064d1b3636367a6a8c02ff75d5ae9c746bf4fdf085e2 |
| src/deploy_workflow/owners/cp2a.py | b246e5bdcb4622511ac557d4bb3a5afd7aa2f22960f69e00ac4fba235a76b5fe |
| src/deploy_workflow/owners/cp2e.py | b5d87f314e733f7e642fa525340c5201a468e65f5958971858b8f60bfd01b85d |
| src/deploy_workflow/owners/cp2g.py | a17cd2e788a936a3cc911c4e9ee5ebb923c3d20fd82d552befd0fe3f0fa8aed2 |
| src/deploy_workflow/owners/cp3.py | 73c5629977cd39ee48cb49f2c851df6177f59a616deb7bc4cc0ae9dac3f4d39e |
| src/deploy_workflow/owners/cp4.py | 4b7746e5af316f6321c7f0c002d35d3280858c19f59fb1d14be0da06c9a10f6a |
| src/deploy_workflow/owners/cp4c.py | d6c14206bc3437e0e51e764719070871a0fce96f13112a2221a6ff40f109ed97 |
| src/deploy_workflow/owners/cp5.py | 8de8e36d045aed056c372e13891722db348a44f5acdca3fdd56e5b379402a93b |
| src/deploy_workflow/owners/cp6.py | 3212ec05142d5c62e749aca5edf2d83c22b5902d33c7e55cb343c66535fd489d |
| src/deploy_workflow/owners/cpl10.py | 18ccda2b51554188483554e69b07dbbb75f65108beb2ec6613367ba05b16990e |
| src/deploy_workflow/owners/cpos.py | b9e918663aa8c418701aa6b468b9f6e06aad00bf70b2090e799af6207d74ce02 |
| src/deploy_workflow/owners/cp2d.py | 33efdce39210f5114abdbc629d69f21e3436e48dc2e5549406bb465fc4a0059a |
| src/deploy_workflow/owners/cp3d.py | 50a541d29c3b2ed73d506c587ec054bfd4e8b30655260a2cf3d0a129499228bc |
| src/deploy_workflow/owners/cp3c.py | c9d2c18c275d5b83b4fb56a2d406873f53f44810cd24661acf8e0e09eb751fd3 |
| src/deploy_vii/bindings/__init__.py | 6b2c8cc47d32212b3b236ece8df0abbfd6774d22db767cb6f7ea483841b9a7fc |
| src/deploy_vii/bindings/cp0.py | c7361b92bda4ce2fcd6a8d8ce4b6ded0cd4a6e306a34a03043266a40efaa3fce |
| src/deploy_vii/bindings/cp1.py | f1d39b51f487a5a960f742007b836fab2fbd0cd00ec509ae7b0a8880d3f0c8d1 |
| src/deploy_vii/bindings/cp1a.py | dfa4ea9a4194adcfc269c4612b6c20b022fd1894e455199bc26774e8cb09231c |
| src/deploy_vii/bindings/cp1b.py | 906d1df2643623f53db096dad415a8377573b07293b90aaa00203f496d837a28 |
| src/deploy_vii/bindings/cp1c.py | e8dd8a3d86b15f86286929dd5e570885fe03f070709441a2d37334227f82744b |
| src/deploy_vii/bindings/cp1d.py | 6c4ed5765d4b04fa293f0f5210f2bda1ede8e4a71dcfc7770f491383c63cb3ce |
| src/deploy_vii/bindings/cp2.py | cff3050de05b40d6b3ac9cd3ec657008cfa4e6311b915873deec7c5b5d3fbeab |
| src/deploy_vii/bindings/cp2a.py | 684e54b11c460d2baacbdea164fbc2d07572b904888ddeee061f8d761d1b6bc0 |
| src/deploy_vii/bindings/cp2d.py | d23ccb5370201f84e633fa1930178dee52c79526fb290272b6881344bdeb35a0 |
| src/deploy_vii/bindings/cp2e.py | 73764a89c152df56b0f0377e5c05ed93f2784c71773b52c4c49362becfa5b5b4 |
| src/deploy_vii/bindings/cp2g.py | 93d1894d0e86d948dd79933b6e6d203f5b1321ce36ca8cf1409a974bd908da76 |
| src/deploy_vii/bindings/cp2h.py | cdcca645a068399dc87052a4494bf41bfe3a13834f22780f38b2049f79a85673 |
| src/deploy_vii/bindings/cp3.py | b4ac94ee6c689e4f18b52b9568a3ae483b6042ea76d19dc6f0a20c3c36d572ee |
| src/deploy_vii/bindings/cp3c.py | fdd5a117e8a7a5a763a201f707500ebf96320d629674853b70f4b12f053b8dd3 |
| src/deploy_vii/bindings/cp3d.py | ec9800f8804c3b202ac37e8b16a58f150803b455cc5471c3dafc120c874c7579 |
| src/deploy_vii/bindings/cp4.py | 484448f5fbbc81995efa9e8f3e5f1b636c01bbc9d16234a5be44107b6baa7f97 |
| src/deploy_vii/bindings/cp4c.py | 30561f81360077889b81993b0b1ea9d8e97f8a84fcb6f94695cc92695501dec2 |
| src/deploy_vii/bindings/cp5.py | 5ea9091ba41d911a88bdd282ef21c1f7dbc380eae06a8534b95901273bd45c20 |
| src/deploy_vii/bindings/cp6.py | d39cac90b76a902d41824130a3ff01f3e86e3ae3646b49b0aa1ce9e886366db9 |
| src/deploy_vii/bindings/cp8.py | 48e82f4586f20879d377dda19faf0fa9f92c138feeb45af3d5f75c81f637c005 |
| src/deploy_vii/bindings/cp_model.py | 4f455b8b2ea3e1a0da1491cc9b7c138f0e23809205dd5e344c8d0a5e0ac09716 |
| src/deploy_vii/bindings/cpdr.py | e9486d074ef14c987d70db2fda556a34dc129352d139b6d8681624e8fb22de9a |
| src/deploy_vii/bindings/cpl10.py | 347a7b0b1764cba8968c2fb6533726be84e9f08a11c07cc7b7ce2e0ee2d2fb4b |
| src/deploy_vii/bindings/shipped.py | 8cd0dbc9b7fb8428cd604c30f86d640b66da91a87506ff1a201a41a26790d3fe |
| DEPLOY VII reference / docs/decisions/0004-design-system-frontend.md | 2d39d55ac9e79938012509485ba16ca21a0fdf2f8e5498c82a29d805dedfef7d |
| DEPLOY VII reference / design/reference/README.md | b060f68759a0e9d7bf0eed834e9d8390e8ad1940afa8537f4885aa2b6771b193 |
| DEPLOY VII reference / design/reference/rbot-design-system.dc.html | 765d190eafae9658371395062c734b6954c7fcb2896458768ab81be0f5716a96 |
| DEPLOY VII reference / design/reference/rbot-fp-01-credit-snapshot.dc.html | a279fc907774025a67e082dcca0a38b014f2093b2415106f5d47733fbbe44f8c |
| DEPLOY VII reference / design/reference/rbot-fp-02-earnings-update.dc.html | 94aa74be2525a9b87c7563543d115cda5bfe52f8a6dd79f03c13ad516c99d3d2 |
| DEPLOY VII reference / design/reference/rbot-fp-03-relative-value.dc.html | 89a15ee632ba4082a60ea8a895a6a9b0471e643e13e657782bdcf80e429d9a4f |
| DEPLOY VII reference / design/reference/rbot-fp-04-covenant-refinancing.dc.html | 57f921b3b4c1ed53ab3c5cd39295dd5bd9f29b46d4b5978f3974cab1f78169ad |
| DEPLOY VII reference / design/reference/rbot-fp-05-distressed-restructuring.dc.html | cae34879e839be531affa30bf5f513ecfb748c1c75a874b70c179c7734984f18 |
| DEPLOY VII reference / design/reference/rbot-fp-06-portfolio-decision.dc.html | 10d49a0cb2f6da34a30e286a9caf3ec4695e15e7909fc246df399380c4d29271 |
