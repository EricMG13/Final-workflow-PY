---
issuer_id: mattress-firm
module_id: CP-4
analysis_date: 2014-09-11
run_id: mattress-firm-2014-09-11-credit_snapshot-sol-medium
pathway: credit_snapshot
method_version: deploy-v-r14
artifact_filename: mattress-firm_CP-4_20140911.md
qa_status: Restricted
committee_status: Requires More Work
review_status: Provisional
confidence_band: Low
---

## Request
Interpret the available financing and covenant evidence for **Mattress Firm Holding Corp.**, as of **2014-09-11**, on the credit_snapshot pathway. Review the proposed financing rather than stopping solely because executed financing documents are absent. This is a **Provisional** assessment of marketing terms and historical filing descriptions, not legal advice, certification of enforceability, an exact capacity determination or an investment recommendation.

The current command authorizes provisional review despite upstream recommendations to defer the complete legal workflow. It does not cure the evidence gaps. Proposed terms, historical outstanding debt and illustrative borrowing-base data remain separate. No subsequent execution or closing after the as-of date is assumed.

## Sources
### Issuer sources relied upon
Provisional source perimeter. Exact names and transport hashes below identify the supplied sources; locators are tool pages, not necessarily printed pages. Only the specified pages were read for this module. No whole-filing, visual, speaker-note or external-source verification is claimed.

| Reference | Exact source name | Exact sha256 | Pages read and use |
| --- | --- | --- | --- |
| QJ | 10-q-quarter-ended-2014-07-29.htm.jsonl | fbf56cb7bfc37a040be57f9ac957ec88eefe9b00edd4be46da0db9295fdeab8e | 12–14: historical debt, amendment chronology, guarantees, security and qualitative compliance. Filed description, not a governing credit agreement. |
| LK | 2014-09-11-8k-item-7-01.htm.jsonl | ce052171e96a72fd90ffdafd421237ca2f87feb97eaa3f1a007130412e890cc3 | 1–2: expressly unnegotiated proposals, furnished presentation and non-GAAP limitations. |
| LP | 2014-09-11-ex99-1-public-lender-presentation.htm.jsonl | 857af871696fd07f0b75ccdcfc96f54478c74b4ad29182f70f5e712cd8cf5e0e | 5, 14–15, 20: proposed capitalization, indicative ABL/TLB terms and illustrative borrowing base. |

### Supplied handoffs, settings and lineage
| Input | Module | Exact sha256 | Re-anchor and treatment |
| --- | --- | --- | --- |
| Current source-readiness handoff | CP-0 | c759dc43c4b5f5ab2ab8dbad2f364fb5590ff0f2d1d24f35ce5b572cc0a55b80 | Mattress Firm Holding Corp.; as of 2014-09-11; credit_snapshot. Historical financial readiness with limitations; complete financing interpretation conditional on missing documents. Source identities match the current inventory. |
| Current financial-foundation handoff | CP-1 | 454fc3ca919f84e093f882b263b2f4eadfe3252a4fdf41a5762586825058fa1b | Same issuer/date/pathway. July debt USD301,860 thousand; LTM ended July 29, 2014 EBITDA USD128,127 thousand; adjusted EBITDA USD151,700 thousand; historical leverage 2.36x. Only debt is re-used numerically below; earnings are not contractual inputs. |
| User settings | Not an analytical module | bb8c7332f7352766b95fe66f1113bd386d45bc8d7cde006d983467f9aa1c1a60 | context p.1 read. USD convention and dated intent, not issuer evidence. Blank fields are not zero. The generic draft setting does not establish execution status. |

The selected-run identity is `mattress-firm-2014-09-11-credit_snapshot-sol-medium`. The two supplied handoffs have matching issuer, date, pathway and source hashes; neither supplies an independently emitted invocation digest, accepted-validation receipt or upstream run identifier. Matching transport identity is therefore confirmed; formal invocation acceptance is not certified. No CP-4C, CP-3C, CP-DR research/adoption rows or CP-1D handoff was supplied or used. No external research was used. Hilco is mentioned by management; its appraisal was not supplied or independently inspected.

Only the supplied source tools are available. The referenced runbooks, absorbed-phase companions, schema files, invocation helper and Python QA/scoring/headroom scripts are not accessible through those tools and were not represented as loaded or run. The supplied method text and its supplied covenant-method bundle were applied to the available evidence. This execution limitation prevents a claim of fully validated canonical completion, but does not prevent the specifically requested Provisional document review.

## Findings
### Reader summary
| Bottom line | Confidence | Main limitation |
| --- | --- | --- |
| Proposed financing offers liquidity-triggered ABL protection but weaker ongoing term-loan control and potential debt dilution; enforceable capacity and recovery control remain unverified. | Low | Provisional: unnegotiated marketing terms, absent governing agreements, compliance certificates, intercreditor agreement and final entity schedules. |

| Finding | Creditor impact | Confidence |
| --- | --- | --- |
| The proposed term loan has no financial covenants, unlike the existing facility description. | Deterioration may not trigger term-lender intervention before liquidity or payment pressure. | Low |
| Proposed ABL controls tighten as availability falls. | Cash dominion and intensified collateral monitoring may protect ABL lenders but constrain borrower liquidity flexibility. | Low |
| Incremental borrowing and conditional payments are proposed without complete definitions or usage records. | Debt dilution and leakage cannot be sized or treated as presently available permissions. | Low |
| ABL and term lenders are proposed to hold reciprocal liens on different collateral pools. | Recovery depends on asset location and missing enforcement, turnover and release terms. | Low |
| Borrowing-base availability is illustrative, not certified closing liquidity. | Inventory eligibility, appraisal and reserves could reduce apparent funding room. | Low |

### Covenant view
**Provisional.** The proposed package trades ongoing term-loan maintenance tests for a liquidity-sensitive ABL control framework. Collateral sharing, conditional payment permissions and incremental borrowing could materially change creditor access to value. The strongest proposed protection is earlier cash dominion and collateral monitoring as availability falls; the principal weakness is the absence of term-loan financial covenants alongside incremental debt flexibility. Neither contractual headroom nor enforceable intercreditor control can be established. Review confidence is **Provisional**; the standardized summary tables use **Low** for analytical confidence, not a claim that the documents are final.

### Creditor implication
**Provisional.** The lender presentation, not an executed financing package, supplies the proposed terms. The existing facility description includes leverage and interest-coverage maintenance tests, whereas the proposed term loan specifies none. This removes an early intervention mechanism if earnings fall without an immediate payment default. Conversely, proposed ABL cash dominion, springing coverage and enhanced collateral monitoring could constrain cash use before a payment failure. Incremental term debt and payment-condition exceptions create potential dilution and leakage, but definitions, usage and cross-document restrictions are absent. Proposed reciprocal collateral liens do not establish enforcement control. The decision-relevant conclusion is therefore weaker proposed ongoing term-lender control, balanced by liquidity-sensitive ABL protections, with capacity and class-level recovery consequences still conditional.

### Legal document register
**Provisional.** Document authority is based on located content, not filenames. No executed credit agreement, indenture, ICA or final offering memorandum was supplied. The lender presentation qualifies for provisional review, so the no-legal-or-offering-document blocking condition does not apply. Module Status: **Provisional review completed with limitations; full governing-document interpretation not completed**.

One or more legal documents in this run are drafts, not executed or filed instruments; their covenant terms may change before signing.

| Document | Kind | Status | Authority rank | Source |
| --- | --- | --- | --- | --- |
| Quarterly report for quarter ended July 29, 2014 | other | filed | not ranked | 10-q-quarter-ended-2014-07-29.htm.jsonl |
| Current report dated September 11, 2014, Item 7.01 | other | filed | not ranked | 2014-09-11-8k-item-7-01.htm.jsonl |
| Public lender presentation dated September 11, 2014 | lender presentation, term sheet or commitment letter | indicative | 6 | 2014-09-11-ex99-1-public-lender-presentation.htm.jsonl |

The current report is classified as a regulatory report; its Item 7.01 information and attached presentation are expressly furnished, not deemed filed. The indicative presentation is not thereby promoted to filed or executed contractual authority. The omitted Marketing Term Sheet is a separate missing document. Acquisition documentation identified upstream is not treated as governing financing evidence.

### Capital structure
**Provisional.** Existing balances are July historical amounts; proposed amounts are not funded balances. All amounts are USD, with units stated individually. The public parent is not assumed to guarantee either package.

| Claim / facility | Amount and date | Obligor / tenor | Security or guarantee evidence | Creditor implication and limitation |
| --- | --- | --- | --- | --- |
| Existing term loans | USD296,795 thousand, July 29, 2014 | Mattress Holding Corp.; January 2016 final maturity described | Filing describes substantially all borrower/subsidiary-guarantor assets and stock pledges; immediate-parent guarantee, exceptions | Existing covenant and security descriptions cannot establish clause-level enforcement or releases. QJ description. |
| Existing revolving facility | USD100.0 million commitment; no borrowings; USD1.6 million letters of credit; USD98.4 million availability, July 29, 2014 | Mattress Holding Corp.; January 2016 maturity after amendment | Same described existing security/guarantee package | Historical availability is not post-transaction borrowing capacity. |
| Existing equipment financing / other notes | USD5,065 thousand, July 29, 2014 | Subsidiary obligations; seller notes through fiscal 2014/fiscal 2016 and insurance financing in fiscal 2014 | Separate priority/security terms not supplied | Do not assign the bank security package or assume unsecured status. |
| Existing consolidated total | USD301,860 thousand, July 29, 2014; USD8,877 thousand current and USD292,983 thousand noncurrent | Consolidated public-company reporting, not restricted-group accounts | Includes the above debt; current maturities are not additional debt | Balance-sheet carrying-value basis; contractual Indebtedness may differ. |
| Proposed ABL | USD125 million commitment; USD42 million proposed draw; USD75 million incremental feature | Mattress Holding Corp.; 5 years | First lien on ABL collateral, second on term collateral; Holdco and wholly owned U.S. restricted subsidiaries subject to exceptions | Commitment, funded draw and incremental feature are different quantities; availability depends on collateral and conditions. |
| Proposed Term Loan B | USD720 million; incremental USD250 million plus other routes | Mattress Holding Corp.; 7 years; 1% annual amortization | First lien on specified term collateral, second on ABL collateral; Holdings and specified restricted subsidiaries, exceptions | No proposed financial covenants; potentially more debt sharing assets. Incremental usage and enforceability not established. |
| Proposed combined debt | USD767 million total; USD763 million secured; USD4 million other notes; includes USD1 million equipment financing | Management transaction case as of September 11, 2014 | Rounded capitalization, not legal claim register | Not comparable to July carrying debt without transaction/perimeter reconciliation; actual closing balances not supplied. |

### Definitions, permissions and lender-control assessment
**Provisional.** These are interpretations of attributed proposal text, not assertions of operative permissions. Appendix evidence entries provide exact pages and labels; section numbers cannot be invented for slides.

**Maintenance architecture.** The existing filing reports maximum leverage and minimum interest coverage tests, equity cures subject to restrictions and compliance at July 29, 2014. That does not quantify headroom. The proposed TLB states “Financial Covenants: None.” Its ABL companion instead proposes a 1.0x fixed-charge coverage test if Specified Excess Availability is below the greater of USD10 million and 10% of Maximum Borrowing Amount. The ABL test appears availability-triggered, not an ongoing consolidated term-loan leverage limit. Earnings deterioration could consequently reduce refinancing resilience without opening a term-lender maintenance-default remedy. Whether an ABL breach cross-defaults the TLB is not supplied.

**Liquidity controls.** Cash dominion is proposed below the greater of USD12.5 million and 12.5% of Maximum Borrowing Amount for 5 consecutive business days, or during a Specified Default. That is a different trigger from the coverage test; its duration condition must not be carried into the coverage test. Borrowing-base reporting becomes weekly during dominion/default; field exams and appraisals increase if availability falls below 15% of Maximum Borrowing Amount for 5 consecutive business days. Earlier monitoring and cash capture could protect ABL collateral while reducing operating discretion. Specified Default, dominion exit and remedy mechanics remain undefined.

**EBITDA and leverage definitions.** The term incremental ratio is stated as maximum closing Secured Net Leverage Ratio of 4.0x. Neither its debt/netting perimeter nor EBITDA/add-back rules is supplied. Public-company EBITDA, management pro forma synergies and new-store annualization are not contractual EBITDA. The LTM historical leverage supplied by the financial handoff cannot be subtracted from 4.0x to infer headroom: debt basis, secured versus total debt, netting, acquisitions and testing time differ. Customer-deposit and vendor funding identified upstream may matter economically even if a future debt definition excludes them; their actual contractual treatment is not supplied.

**Incremental and MFN.** The proposal describes USD250 million, plus voluntary prepayments and commitment reductions, plus unlimited additional amounts subject to the 4.0x test; it includes an Incremental Equivalent Debt option subject to conditions. Do not add these routes as independently usable capacity. MFN is described as 50 bps with an 18-month sunset, but covered debt, exclusions, maturity conditions and calculation details are absent. New secured claims could dilute existing lenders even before default. After the sunset, incremental pricing protection may disappear; the sunset alone does not permit priming or prove all equivalent debt is covered.

**Payments and leakage.** The ABL summary contemplates unlimited investments, debt repayments and restricted payments when Payment Conditions are met. There are alternative availability-only and coverage-plus-availability paths, together with no Event of Default. The first uses trailing-average and pro forma availability above the greater of USD20 million and 20% of Maximum Borrowing Amount; the second requires four-quarter pro forma 1.0x coverage and availability above the greater of USD15 million and 12.5% of Maximum Borrowing Amount. Restricted-payment parentheticals alter those parameters, but the first is textually ambiguous: “($20 million and $22.5 million for Restricted Payments)” does not cleanly state a replacement percentage. Do not repair that text by inference. Even a usable ABL permission would not establish TLB permission; its detailed negative covenants and baskets are omitted. There is no demonstrated unrestricted-subsidiary transfer, IP drop-down, dividend recap or non-pro-rata exchange capacity.

**Prepayments, default and amendments.** TLB proposals include 100% sweeps of asset sales, insurance proceeds and debt issuance, each subject to exceptions; a 50% excess-cash-flow sweep stepping to 25% and 0% at secured-net-leverage levels 0.50x and 0.75x below closing, respectively; 1% annual amortization; and a 101 soft call for 6 months. Sweeps can reduce claims but cannot be valued without exceptions, reinvestment rights, cash-flow definitions and closing leverage. The soft call is price protection, not collateral protection or a leverage test. Payment grace periods, cross-default/cross-acceleration thresholds, equity-cure limits, acceleration votes, sacred rights, collateral release consents and amendment thresholds are not supplied for the new financing. No benign inference is made.

### Structural-priority and intercreditor read-through
**Provisional.** Value location is only partially mapped. The borrower is Mattress Holding Corp.; the public reporting parent is Mattress Firm Holding Corp.; the existing immediate-parent guarantor is Mattress Holdco, Inc. The proposed ABL explicitly names Holdco, while the TLB calls its parent guarantor “Holdings” without a complete definition. Neither the degraded organizational-chart text nor consolidated assets identifies every restricted entity, excluded subsidiary or pledged asset. Proposed U.S. wholly owned restricted-subsidiary guarantees are meaningful coverage intent, but exceptions could leave operating value outside direct creditor reach. There are no entity-level assets, EBITDA or local-law/perfection schedules to size that exposure.

The ICA is absent. Every ICA-dependent conclusion is **[Insufficient Information]**, including standstill duration and expiry, enforcement control, turnover, purchase options, release authority, voting and treatment of proceeds. The slides propose reciprocal first/second liens by asset category, not contractual payment subordination. Structural subordination would instead arise from value in non-obligor entities; lien subordination concerns shared assets; payment subordination requires separate contractual language. The “pari passu” senior-debt ranking statement cannot override asset-specific priority or supply missing ICA rights. No recovery percentage or class preference is derived.

### Counterargument, downside sequence and monitoring
**Provisional.** The strongest contrary case is that the proposed ABL protections and TLB sweeps provide disciplined liquidity control despite no TLB maintenance test. The historical filing also reports compliance and substantial revolver availability. This case would win if negotiated documents preserve robust springing triggers, verified collateral availability, broad perfected guarantees, bounded incremental/leakage permissions, and effective lender release/amendment controls. Those protections could materially reduce concern; their omission from the pack is uncertainty, not proof of adverse terms.

The supported downside is conditional and time-aware: weaker inventory realization or receivable eligibility, higher reserves, or target-system integration problems first reduce the borrowing base; availability then contracts. If the proposed thresholds are adopted, monitoring intensifies and cash dominion can follow after the specified consecutive-business-day condition, constraining cash movement before the fixed-charge covenant potentially springs. In parallel, earnings deterioration need not breach a TLB maintenance covenant. A later payment/default event could expose reciprocal-lien enforcement frictions and any earlier debt dilution or asset leakage. Observable triggers are revised appraisals/reserves, eligibility exclusions, daily availability and its trailing average, dominion notices, incremental issuance, payment notices, amendments and final closing documents. No stress dollar loss or timing of default is asserted.

The most immediate pressure point to monitor is **borrowing-base quality**, not a calculable nearest covenant breach. The presentation expressly notes that Sleep Train does not track some ineligible inventory types and proposes a lower interim advance rate. Its use of illustrative NOLV makes apparent liquidity sensitive to documentation and systems as well as trading performance. No largest remaining basket can be ranked: only stated proposal envelopes, not usage-adjusted legal capacities, are available.

### Analytical appendix — complete canonical registers
**Provisional throughout.** Registers preserve missing information rather than substituting zero. E references below resolve to source-page text, not independently vaulted legal exhibits. Scores are analyst assessments of the stated proposal only, not script-derived confidence scores. All findings carry source evidence or an explicit gap reference.

#### Evidence and definition-conflict register
| Evidence | Source / locator | Located text or fact | Boundary |
| --- | --- | --- | --- |
| E1 | LK p.1, Item 7.01 | “proposed debt terms, which have not been negotiated and remain subject to change” | Controls proposal status; not operative rights. |
| E2 | QJ p.12, Note 4 | USD301,860 thousand total debt; USD296,795 thousand term loans; USD5,065 thousand equipment/other; no revolver borrowings | July carrying debt, not proposed commitments. |
| E3 | QJ p.13, Note 4 | February amendment; revolver January 2016; USD98.4 million availability; USD0.8 million quarterly installments | Filing summary, no underlying amendment supplied. |
| E4 | QJ p.14, Note 4 | Immediate-parent/subsidiary guarantees subject to exceptions; substantially all assets; leverage and coverage tests; restricted equity cure; compliant July 29 | No tested ratios, cure limits or contract clauses. |
| E5 | LP p.14, Summary Terms – ABL Revolver | USD125 million; USD75 million incremental; 1.0x springing coverage; cash dominion and monitoring triggers | Indicative; defined terms incomplete. |
| E6 | LP p.15, Payment Conditions continuation | Availability paths; 1.0x alternative coverage; no Event of Default; restricted-payment parentheticals | First restricted-payment parenthetical is ambiguous as extracted. |
| E7 | LP p.15, Summary Terms – Term Loan Facility | USD720 million; incremental USD250 million plus other routes; 4.0x secured net leverage; 50 bps MFN/18-month sunset; “Financial Covenants: None” | No ratio definitions or full negative covenants. |
| E8 | LP pp.14–15, Security / Guarantors / Ranking | Reciprocal collateral liens; U.S. restricted-subsidiary guarantees with exceptions | No executed security, schedules or ICA. |
| E9 | LP p.15, Mandatory Prepayments / Amortization / Optional Prepayments | 100% specified-event sweeps; 50% ECF with 25%/0% steps; 1% annual amortization; 101 soft call for 6 months | Exceptions and ECF definition absent. |
| E10 | LP p.20, Pro Forma Borrowing Base | USD86,436 thousand base; USD42,000 thousand loans; USD3,093 thousand LCs; USD41,343 thousand excess availability; estimated 65% NOLV | Illustrative July 1 combined case; actual appraisal absent. |
| E11 | LP p.5, Pro Forma Capitalization | USD767 million proposed debt, USD763 million secured, USD4 million other notes; ABL 42, TLB 720, equipment 1 | Rounded marketing amounts, not accounting closing balances. |
| E12 | LK p.2 | Target information generally internally prepared, mostly not GAAP; furnished information; prospective reconciliation impracticable | Management data cannot certify contractual denominator. |
| G1 | Source inventory and E1/E7 | Executed financing agreements, full term sheet, amendments and compliance certificates not supplied | Provisional legal and capacity limitations. |
| G2 | Source inventory and E8 | ICA, security/guarantee instruments and entity schedules not supplied | All ICA-dependent findings [Insufficient Information]. |
| G3 | E10 | Appraisal, certified base, current reserves/eligibility and closing cash not supplied | Actual availability/headroom not calculable. |
| G4 | Supplied CP-0 and CP-1 handoffs | No standalone restricted-group accounts, accepted invocation receipt or executable script environment | Formal completion and scope limitations. |
| D1 | QJ p.12; LP pp.5, 14–15 | USD301,860 thousand July carrying debt versus USD767 million proposed combined debt; USD125 million ABL commitment versus USD42 million proposed draw | Different dates, perimeters and roles, not a contradiction. No silent substitution. Gross-principal/issuance-cost delta and contractual debt basis not supplied. |
| D2 | LP pp.14, 20 | General inventory advance 90% of NOLV; Sleep Train interim advance 85% of NOLV; 65% NOLV illustrative | Specific transitional qualifier, not an error to average away. |
| D3 | QJ p.14; LP p.15 | Existing maintenance tests versus proposed TLB none | Different financing packages, not conflicting reports of the same contract. |

#### T4.2 — Controlling-document register
| Authority Rank | Document | Document Type | Version / Date | Status | Governing Role | Credit Relevance | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Public lender presentation | Lender presentation | September 11, 2014 | indicative | Proposal evidence only | Supports provisional mechanics, not enforceable rights | E1, E5–E11 |
| not ranked | Quarterly report | Regulatory filing | July 29, 2014 quarter | filed | Historical financial description | Debt/compliance baseline, not controlling agreement | E2–E4 |
| not ranked | Item 7.01 current report | Regulatory report | September 11, 2014 | filed; Item 7.01 furnished | Proposal-status disclosure | Explicitly prevents final-term assumption | E1, E12 |

#### T4.3 — Covenant-feature register
| Topic | Provision Summary | Source / Clause | Risk Mechanic | Credit Implication | Market Norm Assessment | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Maintenance | Existing leverage/coverage tests; proposed TLB none; ABL springing 1.0x | QJ Note 4 p.14; LP Financial Covenants pp.14–15 | Term lenders lose an ongoing earnings-based intervention trigger in proposed package | Negative — Covenant Erosion | No supported comparator | E4, E5, E7 |
| EBITDA | Contractual denominator/add-back rules not supplied | LP p.15 incremental summary; definitions absent | Cannot translate marketing synergies into legal borrowing room | Insufficient Information | No supported comparator | E7, E12, G1 |
| Incremental / MFN | USD250 million plus prepayments/reductions and 4.0x ratio route; 50 bps/18 months | LP p.15 Incremental Term Facility | Additional secured claims may dilute; later pricing protection expires if adopted | Negative — Leverage Increase | No supported comparator | E7 |
| RP / investments / junior debt | Conditional unlimited ABL permissions; TLB exceptions omitted | LP pp.14–15 Negative Covenants / Payment Conditions | Cash or value may leave creditor pool; all-facility constraints untested | Negative — Covenant Erosion | No supported comparator | E5–E7 |
| Asset sales / prepayment | 100% sweeps with exceptions; ECF steps | LP p.15 Mandatory Prepayments | Potential deleveraging offset by unknown carve-outs and reinvestment rights | Positive — Deleveraging | No supported comparator | E9, G1 |
| Guarantees / collateral | Reciprocal liens and restricted-subsidiary guarantees subject to exceptions | LP pp.14–15 Security / Guarantors | Access depends on entity and asset category | Insufficient Information | No supported comparator | E8, G2 |
| Default / remedies / amendments | New financing thresholds, voting, cures and releases absent | No clauses supplied | Cannot assess early acceleration, waiver or non-pro-rata amendment protection | Insufficient Information | No supported comparator | G1, G2 |
| Unrestricted subsidiaries / transfers | Designation, IP transfer and non-guarantor baskets absent | No clauses supplied | Potential structural leakage neither proved nor ruled out | Insufficient Information | No supported comparator | G1, G2 |

#### T4.9 — PD versus LGD translation
| Legal Topic | Supported Fact | Risk Mechanic | PD Effect | LGD / Recovery Effect | Monitoring Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| TLB maintenance | None proposed | No ongoing financial-test intervention | May defer covenant default but allow deterioration before lender action | Indirectly larger claims or lower residual value at eventual default | Final covenant architecture and cross-default terms | E7, G1 |
| ABL dominion | Availability/default triggered | Collections become controlled earlier | Reduced operating flexibility as collateral availability contracts | Cash capture may protect ABL pool | Daily availability; 5-business-day condition; dominion notices | E5 |
| Incremental debt / payments | Additional debt routes and conditional unlimited payments proposed | Claim dilution / cash removal | More fixed obligations or less cash cushion | More claims sharing value or less reachable value | Issuance, payment conditions and final baskets | E6, E7 |
| Collateral split | Reciprocal first/second liens proposed | Asset-specific access differs across classes | No direct quantified PD effect | Outcome depends on missing ICA and asset realization mix | Final ICA, releases and lien schedules | E8, G2 |

#### T4.10 — Comparative review
| Topic | Issuer Provision | Market / Third-Party Reference | Relative Assessment | Agreement / Discrepancy | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Covenant package | Indicative terms only | No supported comparative source provided | Market-norm and third-party covenant-review comparison is limited because no supported comparative source was provided. | No comparison asserted | Insufficient Information | G1; source inventory |

#### T4.11 — Covenant aggressiveness
| Area | Score 1–5 | Evidence | Risk Mechanic | Credit Implication | Confidence | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Maintenance architecture | 4 | No TLB financial covenants; springing ABL test | Weak term-level ongoing intervention | Negative — Covenant Erosion | Provisional | E5, E7 |
| Debt / lien incurrence | Not Scorable | Stated routes, definitions/usage absent | Potential dilution without measurable extent | Insufficient Information | Provisional | E7, G1 |
| RP / investment / leakage | Not Scorable | Conditional proposal and ambiguous text | Cannot size all-document leakage | Insufficient Information | Provisional | E6, G1 |
| EBITDA / add-backs | Not Scorable | Contract definition absent | Denominator inflation neither quantified nor established as legally allowed | Insufficient Information | Provisional | E7, E12, G1 |
| Collateral / guarantors | Not Scorable | Coverage intent; exceptions/schedules absent | Recovery reach unverified | Insufficient Information | Provisional | E8, G2 |
| Amendment / control | Not Scorable | No thresholds or sacred rights supplied | Consent erosion cannot be assessed | Insufficient Information | Provisional | G1, G2 |
| Overall | Not Scorable | Fewer than three areas support scoring | Do not extrapolate maintenance weakness into a complete package score | Insufficient Information | Provisional | E5–E9, G1, G2 |

Covenant Aggressiveness Score: **Not Scorable** overall; status **Provisional**. The maintenance-only score is an analyst application of the supplied rubric, not a market-relative judgment or a complete score.

#### T4.12 — Red flags and triggers
| Red Flag / Trigger | Provision or Signal | Why It Matters | PD / LGD / RV Impact | Monitoring Action | Evidence ID |
| --- | --- | --- | --- | --- | --- |
| Inventory eligibility / appraisal revision | Estimated NOLV; Sleep Train tracking limitations | Borrowing base can contract before earnings recover | PD: funding constraint; LGD: collateral realization uncertainty; no RV conclusion | Obtain appraisal and current certified base/reserves | E10 |
| Cash dominion condition | Greater of USD12.5 million / 12.5% threshold; 5 consecutive business days or Specified Default | Collection control can precede covenant intervention | PD: operational liquidity rigidity; LGD: possible cash protection | Track daily availability and dominion notice/exit | E5, G1 |
| Incremental or equivalent issuance | USD250 million plus other routes; MFN sunset | New claims can dilute or alter economics | LGD: more competing claims; PD: debt-service burden | Check final ratios, MFN scope and issuance documents | E7 |
| Payment / transfer | Conditional unlimited ABL permissions | Cash/value may exit; TLB constraint absent from summary | PD: reduced cushion; LGD: leakage if actually permitted | Inspect all-document capacity and trailing-average certificates | E6, E7 |
| Release / amendment / standstill | Missing operative instruments | Cannot know which class can stop value loss or control realization | LGD/control uncertainty, not assumed loss | Obtain ICA, sacred rights and release clauses before selection | G1, G2 |

#### T4.13 — Legal gaps ledger
| Gap | Missing Document / Clause / Schedule | Why It Matters | Impact on Output | Required Follow-Up |
| --- | --- | --- | --- | --- |
| G1: governing financing and tests | Existing restatement/amendments; proposed full term sheet/drafts/finals; certificates; definitions, baskets, defaults and amendments | Summaries omit conditions and interaction | Capacity, complete interpretation and overall score withheld | Obtain dated documents within evidence horizon and tested/usage certificates |
| G2: structure and control | ICA, guarantee/security instruments, entity/collateral schedules, perfection/release provisions | Recovery reach and enforcement cannot be proved | Structural rows qualified; ICA-dependent rows [Insufficient Information] | Obtain full instruments and legible entity map |
| G3: collateral availability | Appraisal; certified base; reserve/eligibility details; closing liquidity | Illustration is not cash or drawable availability | Actual headroom and nearest breach withheld | Obtain appraisal and dated certificates; verify Sleep Train eligibility |
| Comparison / transaction / lineage | No comparator, target diligence, restricted-group accounts or formal validation receipt | Limits benchmarking, denominators, entity scope and completion | No market-standard claim; no certified full-run acceptance | Obtain predecessor evidence; rerun formal checks when available |

#### T4D.1 — Structural source gate
| Source | Status | Authority Rank | Limitations | Module Status |
| --- | --- | --- | --- | --- |
| LP and QJ descriptions | indicative / filed, respectively | 6 / not ranked | No guarantee/security instruments, entity schedules or legible complete organizational relationships | Provisional structure review; not a completed enforceability map |

#### T4D.2 — Entity perimeter
| Entity | Role | Jurisdiction | Parent | Designation | Material Value Held | Inside Credit Group? | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mattress Firm Holding Corp. | Public consolidated reporting parent | Delaware, LK p.1 | Not supplied | Public parent; restricted designation not supplied | Consolidated amounts are not standalone assets | Guarantee/restricted status not established | E1, E2, G2 |
| Mattress Holdco, Inc. | Existing immediate-parent guarantor; proposed ABL guarantor | Not supplied | Exact intervening chain not supplied | TLB “Holdings” not fully defined | Standalone value not supplied | Existing guarantee described; proposed ABL included subject to terms | E4, E5, E8 |
| Mattress Holding Corp. | Existing/proposed borrower | Not supplied | Mattress Holdco, Inc. in existing description | Borrower; full restricted perimeter absent | Borrower assets not separately quantified | Named borrower; exceptions unresolved | E2, E4, E5, E7 |
| Wholly owned U.S. restricted subsidiaries | Proposed guarantor class | U.S.; specific jurisdictions not supplied | Direct/indirect subsidiaries; exact list absent | Restricted class, subject to exceptions | Entity-level assets/EBITDA not supplied | Proposed inclusion only; exceptions unverified | E8, G2 |

#### T4D.3 — Guarantee map
| Entity × Tranche | Guarantee Type | Direction | Release Trigger | Evidence ID |
| --- | --- | --- | --- | --- |
| Holdco / subsidiaries × existing bank facility | Guarantee described; exceptions | Upstream/parent and subsidiary support of borrower debt | Not supplied; no instrument | E4, G2 |
| Holdco / proposed restricted subsidiaries × ABL; Holdings / subsidiaries × TLB | Proposed guarantees; coverage exceptions | Support of Mattress Holding Corp. obligations | Not supplied; designation/disposal release rules not inferred | E8, G2 |
| Public parent × either proposed tranche | Not established | No guarantee inferred from consolidation | Not supplied | E1, E8, G2 |

#### T4D.4 — Security map
| Entity × Lien | Excluded Assets | Release Mechanic | Perfection Limit | Evidence ID |
| --- | --- | --- | --- | --- |
| ABL loan parties × first lien ABL collateral / second lien term collateral | Exceptions not listed; current-asset descriptions vary in breadth across slides | Not supplied | Perfection proposed, not verified; no filings/control agreements | E5, E8, E10, G2 |
| Term loan parties × first lien specified term assets / second lien ABL collateral | Exceptions not listed; guarantor/pledged-stock boundaries absent | Not supplied | No collateral schedules, local-law or perfection evidence | E7, E8, G2 |

#### T4D.5 — Structural recovery access
| Claim/Tranche | Obligor Entity | Reachable Value | Structural-Priority Label | Stranded Value Named | Recovery-Access Implication | Confidence | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ABL / TLB | Mattress Holding Corp. plus proposed guarantors | Described asset pools only; entity values not supplied | Reciprocal lien priority proposed; structural rank depends on non-obligors | No specific stranded asset demonstrated | Non-guarantor creditors may have direct access ahead of indirect residual claims if excluded entities hold value; extent unproved | Provisional | E8, G2 |
| Other notes | Subsidiaries not fully specified | Note-specific obligor assets not quantified | Security/payment rank not supplied | No specific stranded asset demonstrated | Cannot transfer bank guarantees or rank to seller/insurance notes | Provisional | E2, E4, G2 |

#### T4D.6 — Structural leakage routes
| Route | Entity Path | Enabling Provision (CP-4 ref) | Value Exposed | Severity 1–5 | Recovery/Priority Implication | Demonstrated vs Theoretical | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Payment-condition distribution / investment | Borrower/guarantor to recipient not identified | T4.3 payments; LP Payment Conditions | Amount not calculable; all-document constraints absent | Not scored: permission incomplete | Could remove cash or move value outside guarantor pool if finally permitted | Theoretical proposal; no use demonstrated | E6, E7, G1, G2 |

#### T4D.7 — Trapdoor / uptier vulnerability
| Vulnerability | Enabling Provision (CP-4 ref) | Affected Creditor Class | Demonstrated vs Theoretical | Structural Implication | Confidence | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Incremental dilution; no established uptier or IP-transfer route | T4.3 incremental; no non-pro-rata exchange/designation clauses supplied | Existing lenders under proposed package | Incremental intent documented; priming/uptier permission not demonstrated | New permitted secured debt may dilute; first-out priming and non-consensual subordination not inferred | Provisional | E7, G1, G2 |

#### T4D.8 — Structural gaps
| Gap | Missing Document/Schedule/Provision | Why It Matters | Impact on Output | Required Follow-Up |
| --- | --- | --- | --- | --- |
| G2: incomplete restricted-group and collateral map | Entity designations, guarantor exceptions, pledges, releases, perfection and entity value | Cannot locate value or establish claim reach | No quantified guarantee coverage, stranded value or structural priority conclusion | Obtain legal schedules and restricted-group accounts; verify TLB Holdings definition |

#### T4F.1 — Intercreditor controlling documents
| Document | Parties | Date | Governing Law | Status | Source / Locator | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| ICA not supplied | [Insufficient Information] | [Insufficient Information] | [Insufficient Information] | [Insufficient Information] | Source inventory; LP pp.14–15 describes only reciprocal liens | G2, E8 |

#### T4F.2 — Creditor classes and rank
| Creditor Class | Rank | Security Interest | Enforcement Rights | Voting Weight | Evidence ID |
| --- | --- | --- | --- | --- | --- |
| ABL lenders | First on ABL assets / second on term assets proposed; ICA rank [Insufficient Information] | Proposed reciprocal liens only | [Insufficient Information] — no ICA clause | [Insufficient Information] — no votes supplied | E8, G2 |
| TLB lenders | First on term assets / second on ABL assets proposed; ICA rank [Insufficient Information] | Proposed reciprocal liens only | [Insufficient Information] — no ICA clause | [Insufficient Information] — no votes supplied | E8, G2 |

#### T4F.3 — Standstill and enforcement
| Provision | Standstill Period | Trigger | Who Controls Enforcement | Creditor Class Affected | Risk Mechanic | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Insufficient Information] — no ICA supplied | [Insufficient Information] — days/months and expiry absent | [Insufficient Information] | [Insufficient Information] | ABL and TLB; contractual restrictions [Insufficient Information] | Delay, control and expiry mechanics cannot be established | Do not assume collateral priority conveys immediate enforcement control | G2 |

#### T4F.4 — Turnover, release and purchase
| Provision | Turnover Obligation | Release Authority | Purchase Option | Conditions | Countervailing Evidence | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| [Insufficient Information] — no ICA supplied | [Insufficient Information] | [Insufficient Information] | [Insufficient Information] | [Insufficient Information] | Reciprocal lien proposal does not answer proceeds-turnover or release-consent rights | E8, G2 |

#### T4F.5 — Recovery control
| Creditor Class | Realised-Recovery Mechanic | Control Weakness | Severity | Risk Mechanic | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| ABL / TLB | [Insufficient Information] — no agreed enforcement, proceeds or release rules | [Insufficient Information] — control cannot be assigned | Not scored: ICA absent | Asset realization timing and release authority could affect outcomes, but contractual allocation is unexamined | No recovery percentage or security-selection preference | G2, E8 |

#### T4F.6 — Intercreditor gaps
| Gap | Missing Data | Why It Matters | Impact on Output | Required Follow-Up |
| --- | --- | --- | --- | --- |
| G2: ICA absent | Signed/draft ICA, joinders and amendments; standstill, expiry, turnover, releases, purchase options and voting clauses | Lien rank alone does not establish control | Every ICA-dependent row [Insufficient Information] | Obtain complete dated ICA; re-read against collateral/entity map before recovery work |

#### T4C.2 — Capacity source authority
| Authority Rank | Source | Source Type | Version / Date | Status | Controls Legal Formula / Financial Input / Usage | Credit Relevance | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | LP | Lender presentation | September 11, 2014 | indicative | Proposal formula fragments only; no certified usage | No effective capacity inferred | E5–E11 |
| not ranked | QJ; CP-1 supplied handoff | Filing / financial foundation | July 29, 2014 historical base | filed / supplied | Historical financial input, not covenant usage | Consolidated financial ratios are not tested legal ratios | E2–E4, G1, G4 |

#### T4C.3 — Definitions and ratios
| Definition / Ratio | Source / Clause | Formula / Definition Summary | Required Inputs | Capacity Effect | Risk Mechanic | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Borrowing Base | LP p.14 Borrowing Base; p.20 qualification | 100% Qualified Cash + 85% eligible AR + 90% eligible credit-card AR + 90% eligible-inventory NOLV, less reserves; Sleep Train interim inventory qualifier | Eligibility, appraised NOLV, reserves, qualified-cash rules | Constrains ABL drawings independently of commitment | Collateral revaluation can remove liquidity | Do not treat commitment as drawable cash | E5, E10, G3 |
| Maximum Borrowing Amount / Specified Excess Availability | LP p.14 | MBA = lesser of base and facility size; SEA = Excess Availability plus limited over-base adjustment capped at 2.5% of commitments | Operative definitions, dated base, loans, LCs and adjustments | Sets dominion, test and payment thresholds | Different from generic undrawn commitment | Actual thresholds/headroom not calculable | E5, G1, G3 |
| Secured Net Leverage / FCCR / ECF | LP pp.14–15 | Named ratios/measure only; numerator, denominator, netting and adjustments not supplied | Contract definitions, tested accounts and usage | Determines debt, sweep and payment flexibility | Marketing earnings can diverge materially from legal tests | No covenant EBITDA, ratio debt or sweep calculation | E6, E7, E9, E12, G1 |

#### T4C.4 — Tests and headroom
| Test | Test Type | Threshold | Current Basis | Formula | Headroom | Status | Limitation | Risk Mechanic | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Existing leverage / interest coverage | Maximum / minimum ratio, respectively | Not supplied | Filing says compliant July 29, 2014 | Governing formulas not supplied | Not calculable: tests/definitions missing | Qualitative compliance only | Certificate and amendments absent | Compliance is not quantified cushion | No nearest existing breach established | E4, G1 |
| Proposed ABL FCCR | Springing minimum ratio | 1.0x if SEA below greater of USD10 million and 10% MBA | No actual tested FCCR/SEA | Actual legal FCCR minus 1.0x, if springing test applies | Not calculable: definitions and actual test inputs missing | Provisional proposal | Illustration not test certificate | Availability contraction can activate earnings constraint | Monitor both liquidity and coverage | E5, G1, G3 |
| Proposed incremental leverage | Maximum ratio | 4.0x maximum closing Secured Net Leverage Ratio | No contractual ratio supplied | 4.0x minus legally defined tested ratio | Not calculable: legal debt/EBITDA/netting and usage absent | Provisional incurrence condition | Historical 2.36x is not comparable | Ratio flexibility can permit more claims | No maximum additional debt calculated | E7, G1 |

#### T4C.5 — Capacity register
| Capacity Type | Basket / Test | Formula | Conditions | Current Input | Usage | Estimated Capacity | Remaining Capacity | Status | Severity | Risk Mechanic | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Incremental term debt | Stated USD250 million plus prepayments/reductions and ratio route | Fixed stated amount plus other described routes; interaction not supplied | 4.0x route, MFN and equivalent-debt conditions incomplete | Legal definitions/accounts not supplied | Not supplied | Not calculable: indicative amount is not usable capacity | Not calculable: usage absent | Provisional; independently usable routes not established | Potentially material; amount unresolved | More competing claims | No total basket sum or zero-usage assumption | E7, G1 |
| Incremental ABL | Stated USD75 million | Incremental same-term proposal | Documentation/commitments/base conditions absent | Actual base not supplied | Not supplied | Not calculable: conditions incomplete | Not calculable: usage absent | Provisional | Potential dilution and liquidity dependence | Additional commitments need not equal additional availability | No drawable incremental amount inferred | E5, G1, G3 |
| Payments / investments / junior debt | Conditional unlimited ABL exceptions; TLB details missing | Availability alternatives plus no default; no dollar ceiling stated in summary | All-document permissions and payment conditions | Actual trailing SEA/FCCR not supplied | Not supplied | Not calculable: formula and complete restrictions missing | Not calculable: usage absent | Provisional | Potential value leakage | Availability tests can allow cash removal before later deterioration | No effective unlimited capacity conclusion | E6, E7, G1 |
| Fixed / grower / builder / transfers | Complete baskets not supplied | Not supplied | Not supplied | Not supplied | Not supplied | Not calculable: documents absent | Not calculable: documents/usage absent | Explicit gap | Unranked | Cannot distinguish permitted from prohibited pathways | No largest remaining basket or aggregated capacity | G1, G2 |

#### T4C.6 — Debt, liens and priming
| Route | Supported Legal Capacity | Current Calculation Status | Priming / Dilution Mechanic | PD Effect | LGD / Recovery Effect | RV / Security Selection Effect | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Proposed incremental / equivalent debt | Indicative routes only; no operative permission established | Not calculable: definitions, usage and conditions absent | More secured claims could dilute; superpriority/first-out priming not proved | Greater service burden if incurred | More claims against same pools | No preference without final rank/control terms | E7, G1, G2 |

#### T4C.7 — Leakage pathways
| Leakage Route | Supported Fact | Formula / Basket | Usage / Remaining Capacity | Restricted-Group / Collateral Impact | Severity | Credit Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Distribution / investment / debt repayment | ABL conditional exceptions described; no transfer exercised or TLB permission demonstrated | Payment Conditions; first RP parenthetical ambiguous | Not supplied / Not calculable: usage and all-document conditions absent | Cash may leave or value move beyond creditor reach if permitted | Potentially material, not quantified | Monitor final baskets and transaction certificates, not the word unlimited alone | E5–E7, G1, G2 |

#### T4C.8 — EBITDA capacity inflation
| Add-Back / Definition Feature | Source / Clause | Cap / Condition | Calculation Status | Capacity Inflation Mechanic | PD / LGD / RV Implication | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Acquisition synergies / new-store annualization versus legal EBITDA | LP p.5 marketing earnings; LK p.2 disclaimer; contractual definition absent | Legal caps, realization periods and certification not supplied | Not calculable: no contractual bridge | If admitted, non-realized earnings could lower ratio debt burden and expand permissions; admission is not established | PD: earnings execution risk; LGD: possible extra claims; no RV conclusion | E7, E11, E12, G1 |
| Non-debt operating funding | CP-1 non-debt funding review; legal debt definition absent | Treatment of deposits/vendor funding not supplied | Not calculable: classification and covenant perimeter absent | Funding obligations may remain economically relevant outside future debt tests | Liquidity can reverse despite apparently stable legal debt ratio | G1, G4 |

#### T4C.9 — Downstream flags
| Flag | Supported Fact | Creditor Risk | Severity | Confidence | Downstream Module | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- |
| Do not import marketing capacity | Unnegotiated terms; no definitions/usage | False headroom and legal permission inference | Critical evidence restriction | Provisional | CP-4C / CP-3 / CP-2 | E1, G1 |
| Do not assume control from liens | Reciprocal liens proposed; ICA absent | Unsupported class recovery preference | Critical evidence restriction | Provisional | CP-4C / CP-3A | E8, G2 |
| Do not equate illustration to liquidity | Estimated NOLV and eligibility limitations | Funding room overstated | High monitoring priority | Provisional | CP-2D / CP-3C / CP-4C | E10, G3 |

#### T4C.11 — Capacity risk priorities
| Priority | Capacity Item | Severity | Confidence | Primary Risk Mechanic | PD Effect | LGD / Recovery Effect | Monitoring Action | Evidence ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| First | ABL collateral/availability | High | Provisional | Appraisal/eligibility/reserves can remove borrowing room | Liquidity restriction and springing control/test risk | Collateral uncertainty and cash capture | Obtain appraisal/current certified base and daily SEA | E5, E10, G3 |
| Second | Incremental and leakage routes | Potentially material; extent unresolved | Provisional | More claims or less retained value | Debt service/cash-buffer pressure | Dilution/leakage | Obtain final definitions, all-facility restrictions and usage ledger | E6, E7, G1 |
| Third | Enforcement and release authority | Critical evidence restriction | Provisional | Lien allocation without agreed control terms | Default management cannot be mapped | Class realization/control uncertainty | Obtain ICA and guarantee/security release clauses | E8, G2 |

#### T4C.12 — Capacity gaps
| Gap | Missing Data | Why It Matters | Impact on Output | Required Follow-Up |
| --- | --- | --- | --- | --- |
| G1: formula and usage | Covenant debt/EBITDA/FCCR/ECF; basket mechanics; usage; ratio certificates; RP clarification | Neither a stated envelope nor historical EBITDA proves remaining capacity | Headroom, basket ranking, additional debt and leakage amounts Not calculable | Obtain full agreements, marketing term sheet, dated certificates and transaction history |
| G3: current availability | Eligibility, reserves, appraisal, actual loans/LCs/qualified cash and trailing SEA | Illustrated excess availability is not current legal SEA | No nearest pressure-point amount, coverage-test activation or cash-dominion distance | Obtain borrowing-base certificate, daily availability series and final definitions |

#### Verification and execution limitations
Provisional verification uses PASS/FAIL/NA descriptively; no unavailable script output is claimed. All required canonical registers are represented with their specified columns and at least one body row. Evidence gaps deliberately prevent full-run qualification; placeholders were not replaced with invented legal terms to pass a mechanical check.

| Register family / check | Present / columns / minimum rows | Figure lineage or explicit gap | Evidence sufficiency / unsupported-conclusion check |
| --- | --- | --- | --- |
| T4.2, T4.3, T4.9–T4.13 | PASS, each named register represented | PASS: E references or G gaps | FAIL for complete governing-document analysis; proposal limits retained |
| T4D.1–T4D.8 | PASS, each named register represented | PASS: E8 / G2 and related evidence | FAIL for complete entity/guarantee/perfection mapping; no recovery estimate |
| T4F.1 | PASS | PASS: missing instrument explicit | FAIL for controlling-document sufficiency |
| T4F.2 | PASS | PASS: proposal distinguished from ICA gap | FAIL for operative rank/control/voting findings |
| T4F.3 | PASS | PASS: duration/trigger/expiry missing explicitly | FAIL for standstill/enforcement findings |
| T4F.4 | PASS | PASS: turnover/release/purchase gaps explicit | FAIL for provision-level ICA findings |
| T4F.5 | PASS | PASS: control gap explicit | FAIL for realized-recovery mechanics; no percentages inferred |
| T4F.6 | PASS | PASS: follow-up stated | PASS for gap disclosure only |
| T4C.2–T4C.9, T4C.11–T4C.12 | PASS, each named register represented | PASS: monetary proposal roles and missing usage explicit | FAIL for exact contractual capacity; no substitute historical/marketing ratio |
| Invocation, confidence, completeness and validate_handoff scripts | Not run: tools not available | Not supplied: digest, script-derived score and validator findings | FAIL for formal automated acceptance; no invented numerical confidence score |
| Headroom script | NA to quantified output: no complete legal input set; execution tool absent | Not calculable quantities retained | No script-owned capacity value authored |

## Calculations
### Provisional calculation trace
Only the following new arithmetic was performed, using the supplied Decimal-38 kernel. No contractual headroom, basket total, additional-debt limit, stress result or recovery percentage was calculated. No missing input was treated as zero.

| Calculation | Period / perimeter / quantity | Exact signed operands | Result | Source and limitation |
| --- | --- | --- | --- | --- |
| Historical debt classification check | July 29, 2014; public parent consolidated; USD thousands, carrying debt | 8,877 + 292,983 | 301,860 | QJ p.12, Note 4; equals printed total. Current maturities are included, not incremental. Gross-principal/issuance-cost delta not supplied. |
| Proposed debt component check | September 11, 2014 marketing combined case; USD millions, proposed debt | 42 + 720 + 1 + 4 | 767 | LP p.5; ABL draw, TLB, equipment, other notes. Rounded source inputs; not closing carrying debt or contractual Indebtedness. |
| Illustrative excess-availability check | Pro forma as of July 1, 2014; combined marketing base; USD thousands | 86,436 − 42,000 − 3,093 | 41,343 | LP p.20; base less proposed loans and LCs. Reproduces printed illustration, not certified SEA, covenant headroom or actual liquidity. |

LP p.20 prints total liquidity USD41,343 thousand with cash shown as zero in that illustration. This is a source-specific assumption only, not an inference that actual closing cash is zero. LP p.5 separately prints rounded excess/financial quantities on a different presentation basis; its USD42 million draw is not the USD125 million commitment. The slide's USD41 million headline is rounded, not a competing exact amount. No calculation bridges these illustrations to actual September liquidity.

### Provisional withheld calculations
- Maximum-ratio headroom: Not calculable because contractual secured debt, netting, EBITDA and testing conventions are missing.
- Minimum-ratio headroom: Not calculable because contractual fixed-charge inputs and actual springing-test status are missing.
- Fixed/grower/builder capacities and total leakage: Not calculable because legal conditions, independent usability and documented usage are missing.
- Cash-dominion distance and actual borrowing capacity: Not calculable because current certified base, reserves, eligibility, SEA adjustments and trailing availability are missing.
- PD/LGD magnitudes and recoveries: Not estimated; legal mechanics and asset values are incomplete.

## Gaps
### Provisional material questions and bounded evidence requests
These are requests for factual predecessor evidence, not self-dependencies or evidence of an initiated external research job. Only supplied-source tools are available; no external EDGAR acquisition or control-brief file was executed. The EDGAR lane would require fetching and retaining the actual exhibits, not relying on an unfetched search hit. Documents executed after the as-of date must remain subsequent events, not silently cure historical uncertainty.

| Priority / question | Missing predecessor evidence | Why material / affected conclusion | Bounded request and consumer |
| --- | --- | --- | --- |
| Critical: What actually governs existing debt? | Base agreement, November 2012 restatement, February 2014 amendment, other applicable amendments/waivers, July compliance certificate | Existing thresholds, permitted acquisitions, cures and debt basis cannot be construed from Note 4 | Collect actual dated Ex-10.x agreements/amendments and certificate effective by September 11, 2014; consumer CP-4 |
| Critical: What is proposed in full? | Dated Marketing Term Sheet and any available draft financing documents, definitions, baskets and schedules | LP explicitly omits conditions; RP wording ambiguous; negative-covenant interaction unresolved | Obtain the term sheet/drafts circulated for this financing; clarify RP parentheticals, incremental/MFN scope, defaults, sweeps, amendments and releases; consumer CP-4 |
| Critical: Who controls collateral? | ICA, security/guarantee instruments, lien/perfection evidence, release/voting clauses | Every enforcement/turnover/standstill finding is unresolved | Obtain actual dated instruments and amendments; require exact clause references; consumers CP-4, then CP-4C/CP-3A |
| High: Which entities and value are covered? | Legible organizational chart, restricted/unrestricted/guarantor schedules, excluded subsidiaries, standalone/restricted accounts | Consolidated reporting cannot prove direct recovery reach | Obtain entity names, jurisdictions, parentage, designations and asset/EBITDA location; consumer CP-4 |
| High: How much ABL availability is real? | Hilco appraisal, dated borrowing-base certificate, reserves, eligibility and daily/trailing availability | Illustration uses estimated NOLV and target tracking exceptions | Verify current collateral and certified SEA under the proposed definitions; consumers CP-4 and liquidity analysis |
| Medium: What is the complete financial/transaction bridge? | Target GAAP/cash-flow support, synergy realization/caps, actual closing cash/debt, debt-ledger residual identified upstream | Marketing adjusted earnings and historical carrying values are not a legal ratio book | Preserve upstream historical base; obtain factual reconciliation before any capacity model; consumers CP-1 and CP-4 |
| Execution restriction: Can formal acceptance be verified? | Invocation digest/lineage receipt, mandatory companion files and script-enabled environment | Cannot claim required helper/script execution or validated completion | Supply prepared invocation/companions and run validators; consumer CP-4; no fabricated score or validator output |

No supported market comparator or third-party covenant-review report is supplied. No market-standard, unusually weak or unusually strong relative conclusion is made. No actual asset transfer, distribution, priming transaction or default is demonstrated by the reviewed materials. Potential routes remain conditional proposal mechanics, not allegations of conduct.

## Next module
**Provisional handoff only.** Return to the source-collection/financial predecessors for the bounded evidence requests above, then rerun CP-4 against the same dated anchor or explicitly identify subsequent documents. Preserve both supplied handoff hashes and the three issuer-source identities in this artifact.

CP-4C / CP-3A may receive the qualitative proposed collateral split and explicit ICA gap, but must not derive recoveries, enforcement rights or a security preference from it. CP-2D / CP-3C may use the distinction between historical liquidity and the illustrative base, not the illustration as certified cash availability. No other selected module must wait for unrequested work; this restriction applies to conclusions dependent on missing legal evidence.

CP-4 Provisional review completed with limitations. Covenant Aggressiveness: Not Scorable overall. Governing-document legal completion, exact capacity, intercreditor control and formal automated acceptance remain unresolved. This Markdown is the single analytical handoff; it is not a representation that the full executed-document workflow has passed QA.