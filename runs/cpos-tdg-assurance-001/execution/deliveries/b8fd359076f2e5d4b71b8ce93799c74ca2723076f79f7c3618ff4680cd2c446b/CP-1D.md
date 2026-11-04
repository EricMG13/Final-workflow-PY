# CP-1D — TDG earnings quality and absorbed adjusted-debt review

## Request

Challenge the actual issuer EBITDA bridge and identify debt-like obligations,
including CP-1E's absorbed responsibilities. Financial comparisons use FY2024
(2023-10-01–2024-09-30) and September 30, 2024 balances. The December quarter
and its comparator are separate recurrence evidence; they are not annual/LTM
denominators. USD millions unless noted. Execution: actual current-host-model
analysis with local tools and conversation context; no provider or owner runtime.

**Earnings-quality view: Medium confidence, source-limited.** The adjustments
are supported as reported entries, but their disclosure does not establish that
all should be accepted as sustainable credit earnings. Stock/deferred compensation
recurs, acquisition/refinancing categories repeat, and Other contains different
gains/costs. The negative quarterly Other adjustment must remain negative.
Quality-adjusted EBITDA is unresolved; no invented haircut produces a point value.

**Adjusted-debt view:** the stated carrying-debt/operating-lease/gross-pension
convention gives a known-item subtotal of 24,961. This is not a complete adjusted-
debt, covenant-debt or cash-availability conclusion. The material declared
distribution remains a separate cash commitment, and unresolved claims remain gaps.

## Sources

Actually consumed the annual `../tdg-002/CP-1-attempt-2.md`, quarterly
`CP-1-attempt-2.md`, actual `CP-1B-attempt-1.md` and CP-0 source map. Exact hashes
and selected source revisions are retained in `CP-1D-attempt-1-calculations.json`.
CP-1 owns reported amounts; CP-1B's transcription checks are inherited rather
than replaced by new canonical numbers.

| Evidence ID | Original source / located content |
|---|---|
| A | FY2024 annual PDF SHA-256 dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af; PDF 52–54 definitions and two issuer bridges, 141–142 segment/three-year bridge. |
| D | Same PDF 105/126–133: CP-1 carrying debt and principal/cost classification; securitization, finance leases and separate facility terms. |
| P | Same PDF 134–136 pension note. PDF 134 rendered and visually checked in source-preparation/pdf134-pension.png; U.S./non-U.S. columns, gross liabilities, assets and net amounts confirmed. |
| L | Same PDF 147–148: operating/finance lease liabilities and payments, inherited from CP-1. |
| Q | December 10-Q SHA-256 9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a; CP-1 source tables 66/69, text 639–641/661–664 and CP-1B validated signed adjustments. |
| C | CP-1/CP-1A distribution facts and CP-1B's actual 131/132 equivalents difference; declared, payable, single-event paid and full-quarter paid are distinct. |

Selected method: earnings-quality plus absorbed adjusted-debt analytical breadth
in `skills/cp-1d-earnings-quality/SKILL.md`, SHA-256
`9682b2da83fe7fd3288cae31fc5d1cf7f6d2daa3de2fac297637fe13d5e8e2ae`;
later adaptation `src/deploy_vii/methods/cp1d.md`, SHA-256
`47bc1422b52c5b66cf9a766ca0295c01c9292b2e7724aa9a4229514c1174e3da`.
Pure sums/quotients from `owners/cp1d.py` are reused, retaining exact arithmetic
and missingness. Its additional-financing bridge is a different analytical object.
Descriptive T1D/T1E numbering below follows the broader selected method, not the
later runtime's changed table meanings. CP-1E resolves to this artifact's debt phase.

## Findings

### T1D.1 — inherited signed adjustment register

| ID / period | Issuer description | Amount | Category / management rationale | Evidence |
|---|---|---:|---|---|
| A1 FY2024 | Acquisition transaction and integration-related expenses | 70 | Integration, relocation, transaction/valuation/due-diligence costs and inventory step-up amortization; not a homogeneous saving. | A PDF 53 footnote 1; CP-1 bridge. |
| A2 FY2024 | Non-cash stock and deferred compensation expense | 217 | Compensation under stock/deferred-compensation plans. | A PDF 53 footnote 2. |
| A3 FY2024 | Refinancing costs | 58 | Debt issuance, extinguishment, refinancing and amendments. | A PDF 53 footnote 3. |
| A4 FY2024 | Other, net | 15 | FX, payroll-withholding, pension/deferred-compensation and miscellaneous items; no component allocation accepted here. | A PDF 53 footnote 4. |
| Q1 current quarter | Acquisition transaction and integration-related expenses | 13 | Same disclosed broad category, source actions not a new run-rate saving claim. | Q table 66 row 10 / footnote 1. |
| Q2 current quarter | Non-cash stock and deferred compensation expense | 25 | Reported noncash category, not proof that economic compensation disappears. | Q table 66 row 11. |
| Q3 current quarter | Other, net | (64) | Signed negative adjustment; source footnote describes gains/costs. | Q table 66 row 12 / footnote 3. |

No quarterly refinancing row is invented. Ordinary versus adjusted annual/quarter
amounts remain those in CP-1; neither is relabelled as covenant EBITDA.

### T1D.2 — achievability and normalisation assessment

| ID | Evidence of action / realisation | Assessment and counterevidence | Accepted normalisation / limitation |
|---|---|---|---|
| A1 / Q1 | Completed acquisitions and booked expenses are documented; no quantified savings plan or realised run-rate bridge is supplied. | Historical expense recognition is supported. Some transaction-specific costs may end; broad repeated category does not prove that every component is non-recurring. | Unresolved component-level treatment; no fraction or saving invented. |
| A2 / Q2 | Recognised compensation and noncash source classification are documented. | Supported transcription; recurring economic compensation remains a cost to the business/owners. Noncash does not imply a non-recurring cost. | Challenged as a non-recurring normalisation; no blanket conversion into cash-generating capacity. |
| A3 | Actual debt issues/refinancings documented. | Historical action occurred. Individual transaction costs can end, but repeated funding activity requires a normalised financing-policy assessment. | Unresolved sustainable treatment; no assumed annual absence. |
| A4 / Q3 | Reported net row and footnote components exist; cash/noncash/recurring split is not quantified. | Heterogeneous category, including gains; removing all components as a positive cost add-back would be wrong. | Unresolved; preserve annual +15 and quarterly −64 independently. |

### T1D.3 — recurrence test

| Category | Named prior periods and current evidence | Verdict / creditor mechanism |
|---|---|---|
| Acquisition/integration | FY2022 18, FY2023 18, FY2024 70; quarter comparisons 2/13. | Aggregate category repeats. Continuing acquisition policy can make such spending part of sustained cash demand even when each deal is distinct. Component-level non-recurrence remains unproven. |
| Stock/deferred compensation | FY2022 184, FY2023 157, FY2024 217; quarter comparisons 51/25. | Recurring category; do not call the whole expense a one-off or equate exclusion with free cash. |
| Refinancing | FY2022 1, FY2023 56, FY2024 58. | Repeated transaction category. It is not proof of the exact cost of future refinancing, but contradicts an unqualified statement that funding costs never recur. |
| Other | FY2022 (13), FY2023 16, FY2024 15; quarter comparisons —/(64). | Sign and mix vary. Recurrence cannot be assigned uniformly to each component from an aggregate net row. Source dash remains a dash. |

### T1D.4 — issuer control bridge and unresolved quality bridge

| Step | Source adjustment | Cumulative issuer EBITDA | Quality treatment / cumulative quality value |
|---|---:|---:|---|
| Ordinary issuer EBITDA | 3,813 | 3,813 | Reference base, not independently certified sustainable earnings. |
| Acquisition/integration | 70 | 3,883 | Unresolved; quality cumulative value unavailable. |
| Stock/deferred compensation | 217 | 4,100 | Recurring-cost challenge; cannot turn other unresolved items into zero. |
| Refinancing | 58 | 4,158 | Unresolved sustainable funding-cost treatment. |
| Other | 15 | 4,173 | Unresolved heterogeneous net item. |

The source bridge reconciles; a quality-adjusted point does not follow. Quarterly
control independently reconciles 1,087 + 13 + 25 − 64 = 1,061. Unresolved means
neither accepted nor rejected by default. No supposed Supported EBITDA is made
by starting at the already-adjusted 4,173 and adding the same 360 again.

### T1D.5 — annual cash-conversion test

| Basis / FY2024 | EBITDA | OCF | Calculated OCF / EBITDA | Explanation and creditor consequence |
|---|---:|---:|---:|---|
| Ordinary issuer EBITDA | 3,813 | 2,045 | 53.63% | Cash conversion is partial; OCF reflects interest, taxes, working capital and other source-bridged items. |
| Issuer EBITDA As Defined | 4,173 | 2,045 | 49.01% | Larger denominator lowers the mechanical quotient. The issuer's OCF-to-EBITDA bridge, not a generic add-back story, supplies the components. |
| Quality-adjusted EBITDA | Unresolved | 2,045 | Not Calculable | Missing resolved denominator; no zero replacement or invented haircut. |

This is an annual conversion comparison, not cash available for discretionary
use. Capex, acquisitions and distributions are separate after-OCF uses. Interest,
taxes and working capital are not deducted again from OCF.

### T1D.6 — annual-balance leverage sensitivity

| Calculated measure, September 30, 2024 | Ordinary EBITDA | Issuer As Defined | Quality-adjusted EBITDA | Meaning |
|---|---:|---:|---|---|
| Carrying debt 24,880 / annual EBITDA | 6.5250x | 5.9621x | Not Calculable | Definition sensitivity, not reported/covenant leverage. |
| Mechanical net carrying debt 18,619 / annual EBITDA | 4.8830x | 4.4618x | Not Calculable | Uses reported cash, not established unrestricted cash; known distributions matter. |

### T1D.7 — earnings-quality gaps

| Gap | Missing evidence | Affected conclusion / follow-up |
|---|---|---|
| Component-level normalisation | Cost detail, cash/noncash split, actual integration milestones and future recurrence support | Resolve A1/A3/A4 before publishing quality-adjusted EBITDA. |
| Compensation economics | Recurring cash/deferred settlement and dilution policy | Assess sustainable burden without assuming all noncash cost disappears. |
| Complete source and forward case | Supplemental note coverage, forecast, legal/covenant basis and current cash access | No full sustainable-earnings, current leverage or covenant-capacity conclusion. |

### T1E.1 — obligation inventory, annual balance basis

| Item | Reported amount / date | Category and disclosure quality | Evidence |
|---|---|---|---|
| Finance leases | 262 at 2024-09-30 | Already part of CP-1 debt-note carrying debt. | D/L, CP-1 lease/debt registers. |
| Operating leases | 62 at 2024-09-30 | Recognised lease liability outside the chosen funded-debt sum. | L PDF 148. |
| Securitization | Carrying 486; gross 487 | Already separately included in CP-1 24,880 debt classification. | D PDF 130–131. |
| Defined-benefit pensions | Gross recognised liabilities 19 = U.S. 3 + non-U.S. 16; separate non-U.S. asset 13; aggregate net deficit 6 | Visually checked pension note. Benefit obligations 180 and plan assets 174 are different gross quantities; do not add benefit obligations wholesale. | P PDF 134, current-year columns. |
| Government refundable advances | 17 | Already in debt-note carrying amount; conditional repayment, not a conventional note. | D CP-1 facility register. |
| Declared dividend payable | 4,216 at 2024-09-30 | Material shareholder cash commitment, separately identified from funded debt; equivalents require their own scope/amount. | C, CP-1 balance sheet and PDF 146. |
| Factoring / reverse factoring / supplier finance | No separately quantified additional obligation established in this review | Trade payables alone do not prove financing; not an assumed zero. | Targeted disclosure/document follow-up required. |
| Hybrids / preferred claims / earn-outs / puts / other quasi-debt | No complete quantified register established | No default multiple or guessed zero. | Acquisition/financing/contingency documents needed. |
| Guarantees / perimeter | Intragroup guarantees are not automatically extra consolidated principal | Full legal perimeter and external contingent claims not reviewed. | CP-4 required. |

### T1E.2 — debt-like treatment and convention

| Item | Treatment / adjustment | Analytical convention, basis and counterevidence |
|---|---|---|
| Finance leases / securitization / advances | Increment 0 for these already-counted items | Inclusion in the reported carrying base is evidenced. Adding them again would double count; this zero is a known no-second-addition, not missing-data imputation. |
| Operating leases | Add 62 to the known subtotal | U.S. GAAP/ASC 842 lease presentation; add the recognised operating liability to the selected funded-debt base. It is already on the broader balance sheet, so this is a reclassification for analytical debt, not creation of a new accounting liability. No additional lease multiple. |
| Pensions | Add gross recognised liabilities 19; do not offset the separately reported 13 asset | Primary convention does not assume asset transferability between plans. Net consolidated deficit 6 is retained as a different measure. Expected FY2025 funding is stated not material (PDF 135), not zero; the liability is not an immediate contribution demand. |
| Declared distribution | Separate committed cash-use analysis; outside this stated funded-debt/lease/pension subtotal | It competes for cash and must not be ignored in net-debt/liquidity reasoning. Adding a payable and also deducting the same payment from cash would double count its impact. Legal/cash-equivalent scope needs resolution. |
| Unquantified categories | Remain unresolved | No confirmed absence, default amount or agency convention is invented. |

### T1E.3 — known-item adjusted-debt bridge

| Step | Increment | Cumulative known subtotal | Basis |
|---|---:|---:|---|
| CP-1 carrying debt | 24,880 | 24,880 | Long-term + current + separate securitization. |
| Operating lease liability | 62 | 24,942 | Stated analytical convention; already outside that debt sum. |
| Gross recognised pension liabilities | 19 | 24,961 | No offset of separate asset. |
| Already-counted finance leases/securitization/advances | 0 | 24,961 | No duplicate addition. |
| Other unresolved claims | Unquantified | Full total unavailable | Known subtotal is not a complete adjusted-debt conclusion. |

### T1E.4 — effect of the quantified subtotal

| Annual denominator | CP-1 carrying debt | Known adjusted subtotal | Delta | Creditor implication |
|---|---:|---:|---:|---|
| Ordinary EBITDA 3,813 | 6.5250x | 6.5463x | +0.0212x | Numerator convention changes the comparison; completeness and earnings-quality limits remain. |
| Issuer As Defined 4,173 | 5.9621x | 5.9815x | +0.0194x | Quantified lease/pension additions are small relative to the funded base; that does not bound unquantified claims or distribution effects. |
| Quality-adjusted EBITDA | Not Calculable | Not Calculable | Not Calculable | No resolved denominator or complete numerator. |

### T1E.5 — convention reconciliation

| Item | This analysis | Agency / alternative treatment | Status and reason |
|---|---|---|---|
| Lease liability | Add recognised operating lease liability only; retain finance leases already in debt | No issuer-specific agency adjustment or lease multiple supplied | CP-2H must supply applicable agency basis before claiming alignment/divergence. |
| Pension | Gross recognised liabilities without asset offset | Net accounting deficit 6 is an evidenced alternative quantity, not automatically an agency convention | Plan transfer/netting evidence is unreviewed; retain both measures and the stated primary basis. |
| Costs, cash and dividends | Keep carrying debt, cash accessibility and declared distribution separately defined | Gross-principal, restricted-cash, agency and covenant conventions may differ | No silent substitution; CP-4/CP-2H own their applicable legal/agency interpretations. |

### T1E.6 — adjusted-debt gaps

| Gap | Missing data / why it matters | Output effect and follow-up |
|---|---|---|
| Full obligation register | Factoring/reverse factoring, hybrids, earn-outs/puts and external contingent claims not comprehensively quantified | Full adjusted debt unavailable; obtain the relevant schedules and agreements. |
| Plan/lease convention and updates | Plan-level funding/netting/transfer facts and current lease/pension changes | Annual known subtotal only; no current cash funding or agency-debt claim. |
| Distribution and cash access | Annual/interim 132/131 equivalents difference, exact paid/unpaid scope and unrestricted cash | Preserve conflicting event amounts; no unsupported payment residual or post-payment cash estimate. |
| Agency/covenant definitions | Actual issuer-specific agency and legal basis | No covenant headroom, rating-agency leverage or basket/capacity conclusion. |

### Credit read-through, contrary evidence and monitoring

The issuer reports real historical earnings and positive OCF, with both EBITDA
bridges reconciling. That is the strongest counterweight to treating all
adjustments as fictitious. It does not prove that repeated expenses cease or
that an adjusted earnings measure pays interest, capex and distributions.
The quarter's improved earnings alongside a smaller cash buffer reinforces
CP-1B's cash-allocation point rather than contradicting the statements.

A downside chain would be weaker aviation demand/margins while integration,
compensation and financing demands persist → lower conversion → less available
cash after obligations and distributions → greater refinancing/access dependence.
No specific stress size or default outcome is inferred. Evidence of realised
savings, recurring-cost discipline, stable conversion, current access and policy
restraint would strengthen the creditor case; further extraction or unresolved
adjustment growth would weaken it. Monitor signed adjustment composition,
recurrence, cash settlements, declared/paid distributions, lease/pension funding
and facility renewals. Numeric triggers require supported forward assumptions.

## Calculations

Existing `cp1d._sum` and `_quotient` produced the annual/quarterly bridge controls,
known debt subtotal and eight stated annual ratios. Independent integers and
Fraction arithmetic matched, with quotient difference below 1e-35. Exact results,
input hashes, method/code hashes and visual-source identity are retained in
`CP-1D-attempt-1-calculations.json`. Display ratios are rounded only after checks.

The actual `_bridge_amount('-64')` refusal confirms that the later financing-case
grammar does not accept this issuer's signed adjustment. Its `_totals` starts at
already-adjusted EBITDA. The 4,533 double-counting illustration is a scope
diagnostic from that formula, not an executed or accepted owner result. Reusing
the generic sums/quotients preserves the actual issuer question without a fake
Saving/Cost bridge or falsified LTM label. No production code was changed.

## Gaps

All inherited annual/quarterly CP-0/CP-1/CP-1B restrictions persist, including
incomplete note/visual/external-version coverage and the distribution discrepancy.
The specific earnings/debt gaps are retained in T1D.7/T1E.6. No unknown becomes
zero, accepted normalisation or a complete adjusted-debt total. Source-limited
register completion and alias routing do not establish full module/alias coverage.

## Next module

CP-2: consume the recurrence, signed-adjustment, cash-conversion and obligation
findings with their actual definitions and source limits. CP-2G must not fill a
forecast with an unresolved quality number or treat the known debt subtotal as
complete. CP-2H should reconcile actual agency conventions when supplied; CP-4
owns covenant/legal capacity. Delivery may publish the checked historical
comparisons and clearly limited known-item subtotal. Actual deliverables replace
CP-MEMO. Downstream consumption is still required to close this bounded loop.
