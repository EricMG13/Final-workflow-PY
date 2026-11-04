# CP-2D — TDG historical cash bridge and liquidity questions

## Request

Assess what the checked FY2024 handoffs establish about liquidity, and what is
still required for a twelve-month liquidity conclusion. Historical flows cover
October 1, 2023–September 30, 2024; opening forward balances are September 30,
2024. The prospective window is October 1, 2024–September 30, 2025. Amounts are
USD millions unless stated otherwise. This is fresh current-host-model work,
not an isolated model/API run or imported runtime acceptance.

**Liquidity risk level: Insufficient Information.** The historical cash bridge
reconciles, but available cash, complete future cash uses and minimum operating
cash are not established. September cash cannot stand in for liquidity after
the documented October distribution. Do not assign a numeric runway, funding
gap or adequate/tight/weak classification from this result. Confidence is Medium
for the bounded historical interpretation; forward sufficiency is unassessed.

## Sources

The exact upstream paths/hashes are retained in
`CP-2D-attempt-1-inputs.json`; all five were checked before calculation.

| Handoff | Actual content used |
|---|---|
| CP-0, `../tdg-001/CP-0.md` | Consolidated TD Group identity, USD, fiscal dates, PDF identity and extraction limitations. |
| CP-1, `CP-1-attempt-2.md` | T4.5 historical cash flows; T4.6 cash/debt; T4.18 principal, facility dates, letters of credit and reported availability; Gaps. |
| CP-1A, `CP-1A-attempt-3.md` | Dated financing/distribution actions; October payment; critical current-liquidity and executed-document gaps; no assumed sponsor support. |
| CP-2, `CP-2-attempt-2.md` | Demand/cost → operating cash → cash allocation → refinancing chain; counterargument and monitoring questions. |
| CP-2A, `CP-2A-attempt-1.md` | Actual combined stress: 20% issuer-EBITDA decline and 10% cash-interest increase; cash-after-capex proxy 929.60, leverage 7.45x and interest cover 2.62x. These are hypothetical static calculations, not future liquidity. |

One targeted source clarification used the retained PDF's page 133 text: the
93 FY2025 maturity amount is expressly **long-term debt excluding finance
leases**. It is not a comprehensive all-obligations cash-use schedule. The
securitization facility and leases require their own coverage. No new external
filing or current-market evidence was obtained.

Selected methodological sources:

- Later method `src/deploy_vii/methods/cp2d.md`, SHA-256
  `df8ec4b240315b7837144143b10b4861faf47826612d48f4be0e24f2ea5edcdd`.
- Existing pure calculator `src/deploy_workflow/owners/cp2d.py`, SHA-256
  `33efdce39210f5114abdbc629d69f21e3436e48dc2e5549406bb465fc4a0059a`.
- Deploy V-derived breadth in `skills/cp-2d-liquidity-cash-flow-bridge/references/REF_CP-2D_STEPS.md`,
  SHA-256 `84bdff527a5575b900fc94d2bf94eb433a508f8c2883ee84f40ca9dcf94ce595`.

Descriptive headings below avoid the incompatible older/later T2E numbering.
The later calculator contributes exact historical arithmetic and gap propagation;
the broader method retains access constraints, future uses, mitigants and causal
analysis. Its historical run-rate formula does not become an issuer forecast.

## Findings

### Historical sources and uses — reported and calculated

| Component | FY2024 amount | Basis and consequence |
|---|---:|---|
| Beginning cash | 3,472 | Reported CP-1 T4.5 / PDF 109. |
| Operating cash flow | 2,045 | Reported; already incorporates working capital, interest and taxes. |
| Investing cash flow | (2,441) | Reported; includes acquisition outflow (2,347), capex (165) and other investing 71. Acquisition spending is not an operating recurring-burn assumption. |
| Financing cash flow | 3,171 | Reported; includes debt financing, equity-option proceeds and distributions. |
| Exchange-rate effect | 14 | Reported cash translation effect, separate from operating cash. |
| Calculated closing cash | 6,261 | Existing calculator; exact match to reported cash. Residual 0. |
| Numeric debt financing cash-flow subtotal | 4,972 | Calculated from net note proceeds 7,373, note repayments (4,400), subordinated repayments (550), securitization proceeds 137, net term-loan proceeds 6,815 and term repayments (4,403). This is cash financing, not change in principal/carrying debt. |
| Historical movement excluding that debt subtotal and FX | (2,197) | Existing later formula: CFO + investing + financing − debt financing. Includes acquisitions and distributions. It is not sustainable burn or a future cash deficit. |

Reported repurchases and revolver repayment display a dash, **—**, in FY2024.
That spelling is retained in the inputs; no numeric repurchase surrogate was
supplied to the calculator. Its detailed financing-line reconciliation therefore
remains a gap, although reconciliation using the reported financing total passes.
Neither a dash nor letters of credit establishes a funded revolver balance.

### Beginning liquidity and accessibility

| Component at September 30, 2024 | Source-supported figure | Access status / credit implication |
|---|---:|---|
| Reported cash and equivalents | 6,261 | CP-1 T4.6 / PDF 105. Restricted/unrestricted decomposition and location/access package absent; cannot certify the full amount as usable. |
| Revolver commitment | 910 | CP-1 T4.18 / PDF 45, 132. Commitment is a contractual limit, not cash. |
| Reported borrowings available | 843 | Same references. Preserve this disclosed amount; ongoing borrowing conditions/covenant headroom remain unverified. |
| Letters of credit outstanding | 67 | Same references. Not funded borrowing; do not subtract an invented funded draw to recreate availability. |
| Funded revolver drawing | Not established | Existing calculator correctly refuses commitment-minus-draw recomputation with this missing operand. The separately reported 843 is still a usable disclosed fact. |
| Securitization | Gross drawn 487; carrying 486; commitment 650 | CP-1 T4.18 / PDF 130–131. Receivables-backed financing with collateral/borrowing conditions; it is not automatically extra unrestricted cash. |
| Other accessible committed resources | Not established | Sponsor support, asset-sale proceeds and an equity cure are not assumed. |
| Total accessible opening liquidity | Not Calculable | No sum equates reported cash plus nominal commitments to verified accessible liquidity. |

### Cash uses, working capital and timing

| Item | Evidence / timing | Cash mechanism and limitation |
|---|---|---|
| Interest and taxes | FY2024 cash interest 1,158 and net cash taxes 539, CP-1 T4.5 / PDF 109 | Historical payments explain cash conversion and are already in OCF; future schedules/rates/taxes are not supplied. Do not subtract them a second time from OCF. |
| Working capital | FY2024 receivables cash change (84), inventories (104), payables (11), CP-1 T4.5 | These reported cash effects consumed operating cash. They do not establish monthly seasonality, future release or recurring burn; tax/interest accrual changes must remain separately identified. |
| Capex | FY2024 (165), CP-1 T4.5 | Cash use after OCF; maintenance/growth split and deferral flexibility absent. No supported mandatory-capex forecast. |
| Long-term debt maturities | FY2025 93; FY2028 6,637; FY2029 4,768; CP-1 T4.18 / PDF 133 | Long-term-debt schedule excludes finance leases. Near-term amortization and later refinancing are different exposures; this is not the complete twelve-month obligation total. |
| Term-loan amortization | Aggregate quarterly principal payment 22 disclosed, CP-1 T4.18 / PDF 45 | No tranche-level annual allocation was supplied to the calculator. Do not add this aggregate again to a schedule that may already include it. |
| Securitization maturity | July 11, 2025; gross 487 at September close, CP-1 T4.18 | Falls inside the prospective window. Renewal/repayment depends on then-outstanding amounts and terms; October drawing changes the position. |
| Leases | CP-1 T4.18 lease supplement reports historical flows and aggregate future-payment measures | Timing-specific future operating/finance lease obligations are not fully available in the handoff; aggregate liability is not a one-year cash payment. |
| Distribution | October 2024 cash payment 4,216 plus equivalents 132, CP-1A transaction/timeline / PDF 146 | Known subsequent cash use; the funding debt was raised in September. Do not add that financing again in October or treat September cash as the post-payment balance. |
| Subsequent borrowing | October 2024 securitization draw 162.5, CP-1 T4.18 | Separate post-period inflow, with borrowing conditions; do not blend it into September figures or call a known-events-only calculation actual closing cash. |
| Other future uses | Acquisition commitments, restructuring/integration, pension and other committed outflows not comprehensively scheduled | Missing is not zero. Historical acquisitions/distributions cannot be blindly repeated or omitted from a forecast. |

### Prospective bridge and runway

Opening accessible liquidity; operating inflow; working-capital changes; interest;
taxes; mandatory capex; amortization/maturities; leases; distributions; other
committed uses; and committed inflows must each be dated and supported. The
known October events and historical maturities populate questions within this
bridge, but the other cells remain unresolved. **Ending accessible liquidity,
minimum-cash headroom, funding gap and months to empty are Not Calculable.**

The existing function also computes an arithmetic monthly version of historical
movement excluding debt financing. It includes acquisition/distribution policy
and suppresses FX. It is retained in the calculation transcript solely to test
the reused code. It is not used as average recurring burn, runway or a forecast.
Minimum operating cash is missing rather than an assumed zero.

### Risk chain, counterargument and monitoring

CP-2A's actual combined scenario reduces the cash-after-capex proxy to 929.60;
its chosen 7x/3x watches are crossed. This identifies a question for liquidity:
would weaker operating cash arrive before committed payments or refinancing?
The static calculation holds debt/cash fixed, excludes dated obligations and
does not answer that question. Neither watch is a covenant/default trigger.

The issuer-specific chain is demand or cost pressure → weaker operating cash
and possible inventory/collection absorption → less cash after required capex
and distributions → greater reliance on accessible facilities and refinancing.
The disclosed October distribution is an immediate historical timing point;
the July 2025 securitization expiry sits inside the chosen horizon, while
FY2028–FY2029 maturities are a separate later concentration. No distress outcome
or probability follows from these facts alone.

The strongest counterargument is reported positive annual OCF, disclosed cash
and borrowing availability, and completed FY2024 refinancing. These could
provide meaningful capacity if cash is accessible, facilities remain drawable
and cash generation persists after committed uses. That case would gain support
from dated bank/access schedules, covenant certificates and a monthly cash
forecast reconciled to subsequent payments. Unknown access does not itself
prove restricted cash or a failed refinancing.

Monitor cash after distributions; borrowing availability and draw conditions;
receivables/inventory versus sales; cash-interest evolution; maintenance capex;
planned acquisitions/distributions; and facility renewal milestones. Quantified
operating triggers require supported assumptions. Reducing discretionary cash
uses may be a lever, but legal discretion, committed payments, sponsor support
and capex flexibility are not inferred.

## Calculations

`CP-2D-attempt-1-calculations.txt` retains actual `compose_bridge` output; inputs
and definitions are in `CP-2D-attempt-1-inputs.json`. Integer/Fraction checks
independent of the production helper verified cash 6,261, residual 0, numeric
debt cash-flow subtotal 4,972 and historical ex-debt movement (2,197), plus the
exact September 30, 2025 horizon. Missing CFO propagates a gap. Missing funded
draw, facility terms and minimum cash retain gaps. The calculator's raw
principal/carrying-debt shares are not used as reconciled maturity percentages.
No production code, source file or accepted upstream answer was changed.

## Gaps

| Missing evidence / restriction | Affected conclusion and targeted follow-up |
|---|---|
| Accessible cash, restrictions and location; current revolver conditions/covenant certificate | Opening usable liquidity and headroom. Obtain dated cash/access schedules and governing conditions; retain the reported 843 separately. |
| Full dated cash-use forecast, minimum operating cash, seasonal WC and maintenance capex | Forward bridge/runway/funding gap. Reconcile monthly forecast to known October payment/draw and complete obligations. |
| Facility-specific amortization; variable government repayment and lease schedules; current securitization position | Complete maturity cash total. Reconcile long-term schedule, leases and separate facilities without duplication. |
| Executed legal/collateral documents and current refinancing plan | Capacity, restrictions, security/priority and execution conclusions remain CP-4/CP-3C work. |
| Post-period quarterly filings not yet through the CP-0/CP-1 analytical loop | Existing prepared HTML is not accepted quarterly financial evidence. Extend the source/data loop before claiming updated actual liquidity. |
| CP-0/CP-1 rotated-page, visual and external-version limitations; CP-1A ownership/control and reporting gaps | Retain upstream limits; no unsupported new source, owner or sponsor inference. |

## Next module

**CP-3C:** use the actual dated maturity/distribution questions and the distinction
between disclosed availability and accessible liquidity. Historical financing
execution is evidence, not proof of future refinancing; legal/LME conclusions
need operative documents. **CP-2G:** retain the exact fiscal-year boundary and
known subsequent-event timing; do not use the (2,197) historical proxy as a
recurring annual forecast or infer a complete debt/cash roll-forward.
**CP-1 extension:** process the retained interim filings and supply dated cash,
debt, facility and actual cash-flow changes. **Delivery:** historical cash bridge
and limitations can be copied now; forward liquidity remains explicitly absent.

Result: bounded historical calculation and liquidity reasoning completed with
limitations; full CP-2D remains unproven. Downstream consumption is still required.
