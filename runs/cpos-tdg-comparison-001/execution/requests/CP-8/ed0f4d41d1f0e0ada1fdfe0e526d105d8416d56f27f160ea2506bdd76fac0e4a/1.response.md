# CP-8 — TDG prior/current deliverable comparison through CP-OS

## Request

Compare the explicitly selected prior TDG five-section delivery with the current
TDG report-plus-Model delivery. Both have a historical financial base of
30 September2024. Current means the selected latest local TDG publication,
not current2026 issuer information. Actual current host model, with preceding
context and access to the pre-output check file. Not a blind, independent-context
or provider/native evaluation. No investment-decision history is required.

**Conclusion:** delivery coverage has expanded; the five narrative sections,
their156 core facts and the actual CP-1/CP-1A/CP-2 handoffs are unchanged.
The current bundle adds a populated historical HTML Model, charts and calculation
JSON. This establishes more visible analytical content and definitions, not an
improvement in the issuer between report versions or stronger fundamental
confidence. No new issuer-analysis repair is supported by this comparison.

## Sources

CP-OS supplied23 frozen files from two complete receipt-checked delivery bundles.
All23 were opened. Their staged bytes matched the actual request's source hashes.
Both main HTML payloads match their retained View/ReportView; the current Model
has its own consistent View/ReportView/calculation binding. Original deliveries
were read without modification. Prefixes P/C below mean these exact bundles:

| Bundle | Selected publication | Receipt SHA-256 | Main report SHA-256 |
|---|---|---|---|
| P — prior | runs/cpos-tdg-host-001/execution/deliveries/17e1d418be894f6aeff979f100e87460fc3f9d80ed4f22cb7114e4b1c5c8627d | 4216fe746df0e4d46ae384b7abb0f464f8e0b4adfcbc6d2638382da98d440344 | 128027b2625f5ab697c3141c9998f2be6f18ff03115fcddb41a7e682f31282b7 |
| C — current | runs/cpos-tdg-model-001/execution/deliveries/de1be08fb3a040d4e4f916cce017b1541b8eaaa8235b6fb50b7c4afb916a2bfc | 380a4e5f3835f21104eae5103f39a98d5ec08d5b2e082441d1ecc4d5fb9637d7 | cdb682b743990b0484bb51e895a1007973c746510079963f8fc57eb62c3a09b7 |

P/C copied CP-1 SHA301af0ee…, CP-1A SHA6f639631… and CP-2 SHA f50a11f5…
are byte-identical. `C/annual.md` is the same annual CP-1 handoff;
`C/current_synthesis.md` is the same CP-2 handoff. Those aliases are copies,
not new issuer evidence. The complete input hashes are retained in the CP-OS
request and eventual comparison-inputs.json. Original issuer references inside
the analytical handoffs remain their authority/limitation basis.

## Findings

### Seven requested comparison dimensions

| Dimension | Prior deliverable | Current deliverable | Explanation and material effect | Evidence |
|---|---|---|---|---|
| Values |156 delivered core facts from CP-1/CP-1A/CP-2; CP-MODEL blocked. No separately published Model numeric register. |Same156 core facts plus2,005 CP-MODEL representation facts, including81 annual numeric cells:74 known and7 missing. FY2024 operating EBIT plus D&A3,843, issuer ordinary EBITDA3,813 and issuer As Defined4,173 USDm remain separate. |Publication addition, not financial growth or a revision of historical figures. Missing prior publication is not a zero baseline; representation counts are not unique new issuer facts. The three earnings bases cannot be subtracted as a time-series change or treated as one definition. |P/C View core modules equal; C calculation.json values/FY2024 and model-view.json CP-MODEL history/ratios. |
| Periods |Main historical base2024-09-30; underlying annual FY2022–FY2024 history and separately dated subsequent events in unchanged core handoffs. |Same main financial date. Model annual windows retain exact October-to-September dates. Additional raw quarter tables retain2024-10-01–2024-12-28 versus2023-10-01–2023-12-30, with reported89/91-day durations; conditional annual planning windows remain separately labelled. |More period visibility without advancing the main assessment date. Added quarter evidence is later than the annual base and is not an equal-duration or newly normalized/LTM series. |P/C view.json run.as_of; C calculation.json start_date/end_date; C quarter.md context map lines41–43 and retained source tables. |
| Assumptions |The five-section CP-2 assessment does not contain a newly adopted conditional forecast or a new Model publication. Existing core assumptions/unknowns stay explicit. |The same CP-2 assessment, plus literal conditional CP-2G tables and unchanged forecast_exact.json. Reference/downside/upside drivers, exclusions, access/minimum-cash gaps and analyst watches remain stipulated/qualified. |Publishing the retained illustration is not a new source-supported central forecast or evidence that CP-2 adopted these extra scenarios in this run. No new paid or independent analytical execution occurred merely to render them. |P/C CP-2.md byte equality; C forecast.md T2H.3/T2H.7/T2H.9 and Gaps; forecast_exact.json SHA04907444…. |
| Conclusions |Medium fundamental confidence and CP-2 Ready with limitations. The annual operating case is counterbalanced by debt-supported shareholder allocation, cash-access and contractual-control uncertainty. |Identical CP-2 text and identical five narrative report blocks. The Model makes selected historical definitions/calculations visible; CP-MODEL is candidate, not native accepted. |No analytical upgrade, adverse issuer event or new security recommendation is established by this delivery revision. New output availability closes the named publication gap only. |P/C report-view.json blocks equal; P/C CP-2.md assessment line42, Critical restrictions lines155–156 and readiness line174; View module statuses. |
| Sources |Same checked annual CP-1, business/governance CP-1A and fundamental CP-2 handoffs copied into the delivery. |Those exact inputs remain; Model also copies the checked quarter handoff SHA8be815a5…, conditional forecast handoff SHA696d6c06… and exact forecast JSON SHA04907444…. Model sources have explicit handoff-line/hash citations. |Coverage and presentation expanded through additional retained analytical artifacts. An analytical handoff is not a new primary issuer filing, and duplicate source aliases do not add independent confirmation. Scope and dates remain those of each original handoff. |P/C copied-handoff hashes; C calculation.json inputs; C quarter.md,forecast.md,forecast_exact.json and model-view.json sources. |
| Limitations |No published Model/charts; the two inherited Critical contract/current-liquidity restrictions and other CP-1/CP-1A/CP-2 gaps remain. |The named Model/chart/JSON publication now exists. Core creditor restrictions remain unchanged. Seven annual numeric entries remain missing; quarter/source-unit and conditional forecast limitations persist. Native/provider/full-pathway acceptance remains unproven. |A delivered Model does not establish accessible liquidity, covenant/agency measures, complete claims, sustainable FCF or full current underwriting. Old workbook-export wording inside retained historical handoffs is superseded by the user's ingestion-only ruling, not a new work requirement. |P/C delivery.json cp_model_published; P/C CP-2 Gaps; C calculation.json missing amounts; quarter.md G1–G7; forecast.md T2H.9/Gaps; both current publication scope banners. |
| Output scope |Five populated narrative sections; no Model HTML, chart publication or calculation JSON in that bundle. |Those same five sections plus model.html,calculation.json,Model views and copied supporting handoffs/exact forecast. Three annual charts contain18 observations;51 raw handoff tables and two numeric tables are retained in CP-MODEL. |A material, bounded delivery gain: report-to-Model/JSON navigation and source-backed presentation are available. It does not qualify all pathways, formats, sources or native analytical runs. No Excel output is added. |P/C delivery.json file lists/scope; C model-report-view.json two blocks and three figures; C model-view.json53 tables; report.html Model/JSON destinations. |

### All five narrative sections

| Section | Actual prior/current comparison | Consequence |
|---|---|---|
| Key findings |Exactly equal ReportView block |Same Medium annual fundamental assessment and explicit cash/contract restrictions. |
| Company and operating model |Exactly equal block, including operating-model tab |No new business, ownership or operating-model conclusion. |
| Strengths and weaknesses |Exactly equal block and prose lines |Same operating support, distribution/refinancing concern and evidence limits; no lost or newly resolved prior thesis item. |
| Company profile |Exactly equal block and business-mix tab |Historical reported profile/mix unchanged; no new economic inference. |
| Transaction summary |Exactly equal block and dated transaction prose |No additional funding feasibility, legal permission or transaction execution finding. |

The strongest contrary interpretation is that the richer Model now reveals
meaningful figures that the earlier five-section summary did not show. That is
correct as a change in delivered visibility. It does not overcome the exact
equality of the existing core facts/analysis or establish a later-period change
in the issuer. The new ordinary/operating/As Defined earnings presentation
improves definition visibility while preserving uncertainty about quality and
permitted creditor uses.

No material narrative visibility regression was found in this pair: all five
blocks are equal. This finding applies to these selected publications; it does
not undo earlier CP-8 findings on other versions or certify every future revision.

## Calculations

Compared all23 actual input files against the request's frozen hashes; compared
the three core handoffs byte-for-byte, their156 View facts and all five structured
narrative ReportView blocks. The latter blocks are exactly equal, including tabs,
rows, prose and references. Compared publication inventories and CP-MODEL status
blocked versus candidate; inspected81 annual numeric cells, their periods, source
references and distinct definitions, plus the three chart specifications and
additional raw-source/forecast content. Seven annual values remain missing,
including FY2022 source/balance-dependent entries; none is filled with zero.

Counts describe output coverage only. No new issuer-financial arithmetic,
performance variance, return, probability, covenant test or confidence score
was calculated. Earlier independent source/Fraction verification of the81 Model
cells remains the calculation-quality evidence; this comparison is not a second
financial model or a new independent validation of every issuer assertion.

## Gaps

| Restriction | Continuing consequence / next evidence action |
|---|---|
| Historical and mixed dated scope |Shared annual financial base remains2024-09-30; extra quarter/conditional records do not make it current2026 underwriting. Keep their dates and assumptions. |
| Core creditor evidence |Executed terms, current unrestricted cash, covenant/access evidence, forecast and other inherited gaps remain. A publication addition supplies none of these missing inputs. |
| Conditional forecast completeness |Retained scenario outputs remain conditional; missing source-backed cash drivers, later-year assumptions, intra-year troughs and funding feasibility are not resolved by rendering. |
| Numeric definitions and missing observations |Carry debt is a book borrowing measure; mechanical net debt does not certify cash access. Operating and issuer earnings bases are separate. Retain all seven numeric gaps. |
| Qualification |Actual same-host comparison and source/instruction check, not independent-context/provider/native acceptance or a full-pathway proof. No investment-decision outcomes are required for this user-defined function. |

## Next module

Separate delivery should now read this actual CP-8 response and publish its seven
comparison dimensions, source bindings and full continuing gaps. CP-OS must
verify the populated output before recording completion. No upstream analytical
rerun or correction of the unchanged CP-2 assessment is justified by this pair.
Preserve both original publications. Continue remaining module/pathway work
under the active objective; do not equate this scoped comparison with completion
of the entire system.
