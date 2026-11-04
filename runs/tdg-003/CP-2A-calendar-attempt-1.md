# CP-2A — absorbed CP-2B historical event-calendar increment

## Request

Exercise the event/calendar scope left open by the actual static CP-2A screen.
Issuer **TransDigm Group Incorporated**, consolidated. Reference date
2024-11-07; selected historical horizon after that date through **2025-11-07**.
This is a 2026-11-04 reconstruction of annual-source schedules, **not** a current
calendar, point-in-time public-availability backtest or account of realised 2025
outcomes. Confidence is Medium for the selected source/date interpretation.

Six monitoring objects are identified: two hedge-transition clusters, one
facility expiry, one debt-payment window and two separate lease-payment windows.
The facility expiry merits the highest monitoring priority; the hedge transitions
need exposure/strike checks. Neither the scheduled date nor its priority states
the probability of default, an actual funding failure or a net interest shock.

## Sources

Actually consumed the annual `../tdg-002/CP-2-attempt-2.md`, prior static
`../tdg-002/CP-2A-attempt-1.md`, annual CP-1 and this run's CP-2E attempt 2.
Their exact identities, frozen instruction hash and method revisions are in
`CP-2A-calendar-verification.json`. The later December-quarter balance is not
the base of this calendar; the annual-only hedge/facility terms were checked
directly in the original source.

S1 = retained annual PDF,
`data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`,
SHA-256 `dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af`.
Balances/terms are at September 30, 2024. Signing date November 7, 2024 (PDF100)
is separate from that balance date, the retained file's later identity and our
execution date; no claim that these retained bytes were publicly accessible on
the signing date. One-based PDF130, 133 and 148 were rendered and visually
checked in this increment. PDF151 hedge terms were read again; prior CP-2E's
visual review remains bounded evidence, not a new independent visual audit.

Method selection: broader CP-2B REF steps/schema under the CP-2A skill supply
the event duties and stable projection. The narrower later static CP-2A runtime
does not implement this calendar. This is its explicit analytical-scope increment,
not a native-runtime or full source-pack acceptance claim.

## Findings

### T5.1 — event source register

All monetary/notional figures below are **USD millions**. Notional is not debt,
gross principal is not carrying value, and lease payments are not lease balances.

| Event ID | Source document | Description / category | Date/window | Evidence quality | Source reliability / limitation |
|---|---|---|---|---|---|
| E01 | S1 PDF151, swap rows 500/1,500 and collar row 1,100 | Two swaps expire; forward collar starts / hedge transition | 2025-03-31 | Explicit dated terms | Issuer annual disclosure; no proof of realised rollover or distinct covered exposures |
| E02 | S1 PDF130, trade-receivable securitization paragraphs; annual CP-1 | Facility contractual expiry / financing | 2025-07-11 | Explicit dated term | September gross borrowing 487 / carrying 486; commitment 650 is a different quantity; extension rights subject to conditions |
| E03 | S1 PDF151, swap/cap 700 rows and collar 500/1,338 rows | Swap and cap expire; two collars start / hedge transition | 2025-09-30 | Explicit dated terms | Separate instrument types/notionals; no sum treated as net coverage |
| E04 | S1 PDF133, debt repayment schedule, 2025 row | Long-term debt maturities excluding finance leases / debt service | FY2025 | Explicit fiscal window | 93 full-year scheduled principal; not all debt/obligations or the remaining amount after reference date |
| E05 | S1 PDF148, lease maturities, 2025 operating column | Operating lease payments / leases | FY2025 | Explicit fiscal window | 22 full-year cash-payment schedule; not operating lease liability 62 |
| E06 | S1 PDF148, lease maturities, 2025 finance column | Finance lease payments / leases | FY2025 | Explicit fiscal window | 20 full-year cash-payment schedule, including interest; not principal amortization or liability 262 |

### T5.2 — catalyst calendar

Precise dates are chronological. Fiscal windows are shown separately because
they overlap those dates; an order within the window is not supplied.

| Date/window | Event | Category | Credit relevance | Source |
|---|---|---|---|---|
| 2025-03-31 | E01: swaps 500 and 1,500 expire; collar 1,100 begins | Hedge transition | Change in protection form/strike/covered principal may alter cash interest; net effect unquantified | S1 PDF151, swap/collar tables |
| 2025-07-11 | E02: securitization facility expiry | Financing | Verify extension/repayment/access before relying on that source; no actual expiry failure inferred | S1 PDF130, facility term |
| 2025-09-30 | E03: swap 700 and cap 700 expire; collars 500 and 1,338 begin | Hedge transition | Protection and potential collar cash payments differ; overlap/exposure map needed | S1 PDF151, swap/cap/collar tables |
| FY2025; partly elapsed at reference date | E04: 93 scheduled debt principal | Debt service | Full fiscal-year amount excluding finance leases; remaining payment timing/amount not supplied here | S1 PDF133, 2025 row |
| FY2025; partly elapsed at reference date | E05: 22 operating lease payments | Leases | Separate cash use; do not add again to a cash measure already including those payments | S1 PDF148, 2025 operating column |
| FY2025; partly elapsed at reference date | E06: 20 finance lease payments | Leases | Principal/interest split needed for a debt/cash roll-forward; not another 20 of debt principal | S1 PDF148, 2025 finance column |

No fiscal-year event is converted to an assumed September 30 payment date. The
November reference date already falls within FY2025: the full-year amounts
cannot all be called future remaining obligations without a payment bridge.

### T5.3 — event-risk register

**Probability labels describe the disclosed scheduled event/window occurring,
not an adverse credit outcome.** All adverse outcomes remain conditional; their
probability is Unknown. Impact labels are analyst judgments of the conditional
monitoring relevance, not numeric loss estimates.

| Event | Description | Probability | Credit channel | Conditional impact | Affected metric | Direction / source |
|---|---|---|---|---|---|---|
| E01 | March protection transition | High | Cash interest / liquidity | Medium | Effective rate exposure and cash interest | Uncertain: rates, floors/ceilings and exposure linkage matter; S1 PDF151 |
| E02 | July facility expiry | High | Refinancing / liquidity | High | Usable availability and repayment funding | Negative if access ends without replacement; extension is a supported countercase, not an assured outcome; S1 PDF130 |
| E03 | September protection transition | High | Cash interest / liquidity | Medium | Effective coverage/strike cash flows | Uncertain; collars can pay or receive depending on rates; S1 PDF151 |
| E04 | Fiscal principal schedule | High | Debt service / liquidity | Medium | Principal cash uses and funded debt | Cash outflow if paid; not distress by itself; S1 PDF133 |
| E05 | Operating lease payments | High | Cash conversion / liquidity | Low | Operating cash and lease cash uses | Ordinary scheduled cash demand; not an incremental loss; S1 PDF148 |
| E06 | Finance lease payments | High | Debt service / liquidity | Low | Finance-lease cash, principal and interest | Ordinary scheduled payment; no principal-only inference; S1 PDF148 |

### T5.4 — ordinal probability / impact matrix

| Event | Description | Probability | Impact | P/I classification |
|---|---|---|---|---|
| E02 | Facility expiry | High | High | Critical monitoring cell |
| E01 | March hedges | High | Medium | High monitoring priority |
| E03 | September hedges | High | Medium | High monitoring priority |
| E04 | Fiscal principal | High | Medium | High monitoring priority |
| E05 | Operating leases | High | Low | Medium monitoring priority |
| E06 | Finance leases | High | Low | Medium monitoring priority |

| Scheduled-event probability ↓ / conditional impact → | High | Medium | Low | Unknown |
|---|---|---|---|---|
| High | E02 | E01, E03, E04 | E05, E06 | — |
| Medium | — | — | — | — |
| Low | — | — | — | — |
| Unknown | — | — | — | — |

This visualization is an ordinal triage grid. High/High makes E02 **Critical
monitoring priority**, never a high probability of default. Impact may change
with actual access/exposure/cash evidence. No numeric probability is assigned.

### T5.5 — ranked monitoring priorities

Frequencies and escalation conditions below are **analyst recommendations**,
not invented issuer reporting dates or contractual notice periods.

| Rank / event | Description | Priority | Frequency | Escalation condition | Responsible module |
|---|---|---|---|---|---|
| 1 / E02 | Facility expiry | Critical | Event-driven; monthly readiness review before expiry | No evidenced extension/replacement/repayment plan, or reported access weakens | CP-2D / CP-3C / CP-4 |
| 2 / E01 | March hedge transition | High | Event-driven; quarterly exposure refresh | Covered exposure/strike or settlement change raises unmitigated cash-interest burden | CP-2E / CP-2D |
| 3 / E03 | September hedge transition | High | Event-driven; quarterly exposure refresh | Overlap/strike/reset or uncovered principal creates cash pressure | CP-2E / CP-2D |
| 4 / E04 | Fiscal principal schedule | High | Quarterly cash-use reconciliation | Actual unpaid schedule/access cannot be reconciled to funded resources | CP-2D / CP-3C |
| 5 / E05 | Operating lease payments | Medium | Quarterly cash-use reconciliation | New leases, changed payments or duplicated cash-use assumptions | CP-2D |
| 6 / E06 | Finance lease payments | Medium | Quarterly cash/debt reconciliation | Principal/interest split absent or payments double counted against debt/OCF | CP-2D / CP-MODEL |

### T5.6 — watchlist and cross-module handoff

| Event | Description | Priority | Receiver | What to carry / when | Rationale |
|---|---|---|---|---|---|
| E02 | Facility expiry | Critical | CP-3C / CP-4 / CP-5 / CP-6 | Date, annual gross/carrying/commitment distinction and conditional extension; before reliance on facility access | Funding question and operative-document check, not an asserted failure |
| E01 | March hedge change | High | CP-2E / CP-2D / CP-6 | Separate swap expiries and collar start, with exposure/strike gap; at transition review | Cash-interest risk requires mapping, not a single permanent hedge ratio |
| E03 | September hedge change | High | CP-2E / CP-2D / CP-6 | Separate swap/cap and collar rows; at transition review | No duplicated notional or automatic net shock |
| E04 | Fiscal principal | High | CP-2D / CP-3C / CP-5 | Full-year 93 excludes finance leases; obtain remaining-period bridge before cash modeling | No full-year-as-remaining or debt/lease duplication |

CP-2D receives all six objects, including the Medium lease items, through this
actual Markdown. CP-3 cannot derive an RV label from these dates; CP-MODEL
receives a presentation projection only, not validated cash drivers.

### T5.7 — gaps, exclusions and limitations

| Gap / context | Affected scope | Downstream impact | Severity | Required action |
|---|---|---|---|---|
| No actual 2025 renewals, settlements or outcomes checked | All events | Historical schedule is not a current status report | Material | Obtain separate dated outcomes for an outcome review |
| No full exposure/reset/overlap map or current access/draw conditions | E01–03 | No quantified net rate effect or funding failure probability | Material | CP-2E exposure and CP-4/CP-3C access evidence |
| FY2025 windows partly elapsed; full-year cash not remaining need | E04–06 | No monthly runway or complete remaining funding total | Material | Payment bridge and principal/interest/cash-flow classification |
| Beyond-horizon FY2026–29 debt/lease and 2026–27 collar changes | Calendar extent | Important broader maturity context, outside selected dated horizon | Material | Extend horizon for refinancing review; preserve source windows |
| Undated operating/cost/ESG/rating and future distribution risks | Dated calendar | No invented calendar entry, earnings date, trigger probability or payment date | Material | Keep monitoring questions; admit a date only with evidence |
| October 2024 securitization draw and distribution already occurred before reference date | Context only | Not future catalysts; not added to September source balances | Material | Separate dated cash bridge; no look-ahead blend from December balances |
| Targeted six-object scope, source-version/coverage and operative-document limits | Whole increment | Not an exhaustive issuer event audit or native/full CP-2A acceptance | Material | Preserve scope; expand only with source-supported events |

### Workbook presentation projection

READY means a source-backed dated item is admitted for this **historical
presentation**, not current financing readiness or CP-MODEL publication. `as_of`
is this reconstruction's execution date; it is not a claim that 2025 lies ahead
today. Ranks reproduce the monitoring order, not calendar chronology.

<!-- table-id: cp2b.cp_model_catalysts -->

| rank | event_date_or_window | event | credit_relevance | status | source_id | source_locator | as_of |
|---|---|---|---|---|---|---|---|
| 1 | 2025-07-11 | Historical securitization expiry | Verify conditional access/extension; no actual failure inferred | READY | S1 | PDF130, Trade Receivable Securitization Facility, expiry paragraph | 2026-11-04 |
| 2 | 2025-03-31 | Historical swap expiry / collar start | Separate 500/1,500 swap notionals from 1,100 collar; no net coverage sum | READY | S1 | PDF151, swap rows 500/1,500 and collar row 1,100 | 2026-11-04 |
| 3 | 2025-09-30 | Historical swap/cap expiry / collars start | Retain separate instruments, strikes and unknown net cash effect | READY | S1 | PDF151, swap/cap 700 and collar 500/1,338 rows | 2026-11-04 |
| 4 | FY2025; remaining dates unspecified | Full-year scheduled debt principal 93 USD m, excluding finance leases | Not remaining cash need or complete obligations | READY | S1 | PDF133, Debt Repayment Schedule, 2025 row and excluding-finance-leases heading | 2026-11-04 |
| 5 | FY2025; remaining dates unspecified | Full-year operating lease payments 22 USD m | Keep distinct from lease liability and OCF already including payments | READY | S1 | PDF148, lease maturities, 2025 row, operating column | 2026-11-04 |
| 6 | FY2025; remaining dates unspecified | Full-year finance lease payments 20 USD m | Principal/interest split needed; not an extra principal-only debt amount | READY | S1 | PDF148, lease maturities, 2025 row, finance column | 2026-11-04 |

Overall: six selected objects, comprising two hedge transitions, one financing
expiry, one debt-service window and two lease windows. One Critical and three
High priorities concentrate in funding/cash-interest channels. The strongest
countercase is ordinary refinancing/extension, effective protection and operating
cash generation; it must be evidenced, not assumed. Based on available evidence,
these six objects represent the selected material source-scheduled credit
catalysts for TransDigm within the historical monitoring horizon; this is not an
exhaustive assertion about all future events or their actual outcomes.

## Calculations

No new issuer cash forecast or sensitivity. Date checks preserve three exact
dates and three fiscal windows; the six projection ranks are distinct and
contiguous. Source amounts/roles remain literal, including 487 gross versus 486
carrying and 650 commitment, 93 excluding finance leases, 22/20 lease payments,
and separate derivative notionals. No aggregate net-hedge amount, all-obligations
total, remaining cash-use figure or numeric adverse-event probability is created.

## Gaps

T5.7 remains operative. Prior CP-2A static assumptions and annual CP-1/CP-2
liquidity/legal/source limitations survive. Full CP-2A plus all event breadth,
native provider/owner execution, CP-MODEL publication, full orchestration and
checked final deliverables are not established merely by this increment.

## Next module

CP-2D must actually consume this exact response and explain the timing/funding
questions it adds, preserving historical status, full-year-versus-remaining scope,
derivative overlap and principal/lease distinctions. CP-3C/CP-4 need actual
access/operative evidence before conclusions. The separate delivery process may
use the projection and registers with these conditions; final deliverables,
not CP-MEMO or Markdown alone, remain the end condition.
