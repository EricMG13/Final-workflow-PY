# CP-8 — TDG prior-to-current deliverable comparison

## Request

Compare the delivered TDG snapshot2 with the latest selected delivered snapshot6.
The current user's CP-8 definition supersedes the imported investment-decision
post-mortem. Actual current host model with preceding context, sequential,
2026-11-04; no agents, provider calls or native acceptance. Both reports have a
historical 2024-09-30 financial base. “Current” means the selected latest local
report, not current2026 issuer information.

## Sources

Both complete delivery bundles passed their recorded file hashes before this
answer. `inputs.json` pins the report HTML, View, ReportView, copied handoffs,
issuer/run identities and as-of dates. The reports contain the actual delivered
content; handoffs explain lineage and retained restrictions, without becoming
unpublished report content by assumption.

- P: `deliverables/tdg-fy2024-snapshot-2/`, run
  `tdg-fy2024-manual-snapshot`; HTML SHA256
  `324952b09a08ac87c66708c1ed4b9dc4d33dce7567279ab942ae1233d80a8aa6`.
- C: `deliverables/tdg-fy2024-snapshot-6/`, run
  `tdg-fy2024-manual-snapshot-6`; HTML SHA256
  `6bc718146295fda0ffc4b850a5a5a7c55ccb84d3b7a642cb16c62f7192873081`.
- P2/C2: each bundle's copied `CP-2.md`; locators below are exact file lines.
  P1/C1 and P1A/C1A similarly mean copied CP-1/CP-1A handoffs. JSON module,
  table, row and field identities refer to that bundle's `view.json`.

Scope is all five report sections and the underlying delivered module tables.
No issuer/period merge, new credit analysis or external investment record is
needed. The earlier Berkshire source investigation is unused and is not CP-8 proof.

## Findings

The newer deliverable develops the analysis while preserving the annual facts
and Medium fundamental confidence. It adds dated quarter interpretation,
conditional scenarios, protection/ESG discussion and a qualified peer comparison.
That gives more specific tests of creditor cash protection, rather than evidence
that the issuer improved between these report versions. Three omissions need
targeted restoration: maturity concentration, the related-party/reporting gap and
the explicit severity of two inherited Critical evidence restrictions.

### All five report sections

| Section | Prior → current | Why / effect | Evidence |
|---|---|---|---|
| Key findings | Revised; one opening line in each | The business/distribution tension remains. Current adds conditional cover and assumptions; cash/access and refinancing sufficiency remain unassessed. | ReportView `key-findings`; P2 L35; C2 L42 |
| Company and operating model | Unchanged | Same two primary rows and five operating-model tab rows. No new operating-model or ownership proof. | Entire ReportView `company-operating-model` equal; CP-1A facts/tables/artifact equal |
| Strengths and weaknesses | Revised; seven → twelve prose lines, including thesis | Three strengths become five and three weaknesses become six. Themes are merged and added; ordinal row changes are not one-to-one analytical changes. Three prior creditor restrictions lose prominence. | ReportView `strengths-weaknesses`; P2 L37,L66–74; C2 L44,L67–82 |
| Company profile | Unchanged | Same two primary rows and four business-mix tab rows. Reported mix remains issuer-estimated historical context. | Entire ReportView `company-profile` equal; CP-1A artifact equal |
| Transaction summary | Unchanged | Same26 delivered prose lines. No new transaction funding, legal permission or execution conclusion follows from revision. | Entire ReportView `transaction-summary` equal; CP-1A artifact equal |

### Material analytical changes

| Item | Prior deliverable | Current deliverable | Classification / effect | Evidence |
|---|---|---|---|---|
| Annual financial base | FY2024/FY2023/FY2022 dashboard | Identical dashboard, including FY2024 cash6,261 and OCF-minus-capex1,880 USDm | Unchanged facts. A newly discussed peer ratio or scenario does not revise this historical base. | P1/C1 L246–256; `CP-1/evidence-trace`, all11 rows equal |
| Business and financing support | Aftermarket, multiple channels/defense and historical financing as three strengths | Replacement/channel breadth and observed cash/financing as two combined themes | Reframing/merging, not deletion of the defense or financing case. OCF remains a counterweight, not proof of available liquidity. | P2 L66–68; C2 L67–68 |
| Debt-supported extraction | A central weakness | Still central, with dated quarter cash-allocation context | Interpretation expanded. The source period and payment categories must remain separate; the repeated annual base is not a new balance-sheet observation. | P2 L72; C2 L76 and L54–59 |
| Forward sensitivity | Sustainable cash/forward resilience not established | Conditional FY2025 cover3.14x reference/2.28x downside,3x analyst watch; higher-margin countercase3.26x | New scenario coverage. These are assumptions and tested illustrations, not issuer plans, covenant tests or realized deterioration. | P2 L74; C2 L42,L70,L77–78; source CP-2G named in C2 |
| Rate and environmental exposure | No comparable delivered quantitative increment | Reported approximately77% fixed-rate gross debt; issuer approximately+30 USDm for+100bp; environmental liability41 versus44 | New dated source interpretation. No independently reconstructed net hedge adequacy or incremental environmental loss. | C2 L69,L80; cited CP-2E/CP-2F |
| Peer evidence | No delivered peer comparison | Reported operating/cash comparisons, strict sample limits and exact unlike fiscal ends | New coverage. CFO/sales and carrying-borrowing/CFO are specific reported definitions, not economic-debt ranking or normalized credit metrics. CW's February2025 filing precludes September2024 information availability. | C2 L72,L82; cited actual CP-1C/CP-2 peer consumer |
| Earnings/claims definitions | Sustainable FCF and broader obligations not settled | Quality earnings, carrying/gross/known-item obligations and cash-role limits made explicit | More precise uncertainty, not proof that a sustainable earnings number or complete claims inventory now exists. | P2 L74; C2 L79 and L46–52 |
| Confidence and status | Medium fundamental confidence; candidate analytical modules; Model blocked | Same | Added content does not upgrade assurance or establish Model/workbook/chart publication. | P2 L35; C2 L42; both Views' statuses and blocked CP-MODEL |
| Output scope | Five narrative sections | Same five narrative sections | No new workbook, charts, investment call or automated pathway.159→163 delivered facts measures representation only. | Both delivery manifests, Views and ReportViews |

### Unresolved regressions to repair

| Finding | Actual prior/current comparison | Required targeted action |
|---|---|---|
| RC-1 — maturity concentration loses summary visibility | P2 L73 explicitly shows FY2028 principal6,637 and FY2029 principal4,768 USDm within24,319 total scheduled principal, excluding finance leases, at Sep30 2024. C2's weaknesses omit these figures. The unchanged11-row dashboard does not supply a maturity schedule. | Restore the prior dated maturity statement and financing implication. Do not label it a new forecast or current capacity assessment. |
| RC-2 — related-party/reporting restriction falls out of CP-2's gap list | P2's gap row names unassessed related-party activity and recurring lender reporting. C1A L142 retains it unchanged, but C2's13 gap rows do not explicitly carry it. | Restore this Material limitation and the existing source request. Omission supplies no evidence of resolution. |
| RC-3 — inherited Critical severities are less explicit | Prior CP-2 gap table labels legal-document and liquidity/covenant restrictions Critical; C1A L138–139 still does. C2 retains those subjects but its gap columns omit severity. | Carry the original Critical evidence-restriction labels visibly in the two current consequence cells. Do not infer a downgraded severity or an adverse issuer event. |

The strongest contrary reading is that the new synthesis is shorter on selected
old detail to accommodate broader analysis, and both underlying CP-1/CP-1A
handoffs remain intact. That explains the compression but does not establish
resolution. Restoring the three specific items improves creditor visibility
without rebuilding the report, rerunning unrelated modules or changing the
Medium core assessment.

## Calculations

Direct comparisons before this answer show byte-equal CP-1 and CP-1A module
facts/tables/artifact hashes, equal CP-MODEL blocked status, and exactly three
unchanged ReportView blocks. CP-2 is the changed producer. Its strengths3→5,
weaknesses3→6 and gap rows9→13 do not measure investment quality or gap closure.
Totals159→163 facts count delivered representation, not unique new issuer facts.
The annual1,880 USDm cash proxy is unchanged; no inter-period financial variance
or new scenario, return, probability, rating or confidence score is computed.
Semantic themes are compared explicitly because repeated Strengths/Weaknesses
labels and shifted ordinals cannot safely identify equivalent claims.

## Gaps

| Restriction | What remains true / required use |
|---|---|
| Current issuer evidence | These are historical report versions. Latest-local delivery is not complete2026 underwriting. |
| Later-period and scenario content | December-quarter observations, FY2025–FY2027 assumptions and differing peer dates remain separate from the shared September annual base. |
| Creditor inputs | Accessible cash, current covenant evidence, complete operative contracts, full maturity/uses plan, ownership and other inherited gaps remain unresolved in this delivered scope. Separate legal-case work is not automatically imported. |
| Missing publication | CP-MODEL remains blocked and the five-section report does not become a workbook/chart or completed full pathway. |
| Cause of revision | The retained C2 source lineage supports the stated analytical additions; report text alone does not establish any new issuer event or validate all upstream analysis again. |
| Native integration and assurance | Same-session comparison of actual retained deliverables; no isolated provider, general comparator implementation or native CP-OS invocation proof. |

## Next module

CP-2 should actually consume this comparison and repair RC-1/2/3 only, retaining
all other current analysis and explicit scope. The separate delivery process
should construct a new report from that repaired handoff with the unchanged
CP-1/CP-1A inputs. Keep snapshot2 and snapshot6 intact and compare the repaired
output against both. This proves CP-8's user-defined feedback function when the
consumer and populated output are checked; no investment-decision post-mortem
or three-decision calibration gate applies.
