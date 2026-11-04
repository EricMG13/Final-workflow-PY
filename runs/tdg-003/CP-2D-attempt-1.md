# CP-2D — TDG observed quarterly cash update

## Request

Update historical liquidity reasoning from actual checked December-quarter
financial and earnings handoffs. Current-host-model analysis with local tools,
not isolated provider/API, annual runway-model execution or current 2026 advice.
Flow period: 2024-10-01–2024-12-28. Balances: 2024-12-28 and 2024-09-30;
comparative cash 2023-12-30 is a separate prior-year instant. USD millions.

## Sources

Actually consumed `CP-1-attempt-2.md` and `CP-1B-attempt-1.md`; exact path/hash
identities are retained in `CP-2D-attempt-1-calculations.json`. CP-1 supplies
original source/period/definition maps and statement rows. CP-1B supplies the
actual earnings/cash interpretation and 131/132 vested-equivalents disclosure
difference. The prior annual review `../tdg-002/CP-2D-attempt-1.md` supplies
context, not a substitute for the observed quarterly figures.

Selected analytical method remains the earlier review's Deploy V breadth plus
later CP-2D corrections. Its existing pure Decimal sum is reused for historical
reconciliation; the annual run-rate engine is not fed quarterly operands.
Original H4 SHA-256 is
`9bdfd29ebc3c57b72d506e7dff2a2ca2e3179035deb4941dcd026523a5b8595a`.

## Findings

| Actual quarter bridge | USD m | Source meaning |
|---|---:|---|
| September opening cash | 6,261 | CP-1 cash flows / original H4 table 14 row 52. |
| Operating cash | 752 | Row 28; includes interest, tax and working-capital effects. |
| Investing cash | (24) | Row 34; includes capex, acquisitions and other investing. |
| Financing cash | (4,516) | Row 49; distributions/repurchases, securitization and other financing. |
| FX effect | (14) | Row 50; separate translation effect. |
| December closing cash | 2,459 | Row 53; exact reconciliation, residual zero. |

The previous known-events-only uncertainty now has an actual quarterly cash
statement. CP-1B shows OCF increased 116 versus the prior fiscal first quarter,
while the cash balance fell sequentially by 3,802. The reported financing
outflow explains why improved historical earnings/operating cash can coexist
with a smaller cash buffer. This is cash-allocation evidence, not proof of an
operating collapse, a covenant breach or a future funding failure.

The quarter reports 4,396 dividend/equivalent cash payments and 316 repurchases.
Those are not the same scope as the October 18 distribution. The annual filing
identifies 4,216 dividends plus 132 equivalents; the interim narrative identifies
4,216 plus 131. Keep the disclosure difference unresolved. Do not force either
event total to match all-quarter cash payments or allocate an unsupported
residual. The actual quarterly statement governs the quarterly cash bridge.

The issuer reports December cash liquidity 3,308, comprising cash 2,459 and
revolver availability 849 (H4 table 61). Source narrative identifies 61 letters
of credit, not funded revolver debt. Preserve the disclosed availability rather
than infer a drawing from commitments. Cash/access restrictions and ongoing
borrowing conditions still require evidence. A reported liquidity measure does
not certify all resources as unrestricted or establish the minimum operating
cash requirement.

Securitization gross borrowing is 650/carrying 649 at December; the reported
quarter draw is rounded 163. The historical contractual expiry July 11, 2025
and extension conditions require a dated renewal/repayment assessment; this
filing does not show the later outcome. Other term loans/notes first mature in
November 2027 or later, but interim amortization and leases still matter.
The source expressly says no fiscal-Q1 term-loan payment was made due to timing;
do not substitute an assumed regular quarterly payment into this actual bridge.

The counterargument to liquidity concern is positive OCF and disclosed cash/
borrowing availability, alongside the earlier financing execution. It gains
weight if accessible cash, cash generation and facility access are sustained
after committed uses. It weakens if extraction continues, conversion deteriorates
or borrowing conditions constrain access. No source-supported monthly forecast,
current access certificate or complete forward cash-use schedule resolves that
comparison here. Liquidity risk level remains **Insufficient Information** for
forward sufficiency; numerical runway, funding gap and headroom remain absent.

## Calculations

Existing `cp2d._total` returns 2,459 for 6,261 + 752 − 24 − 4,516 − 14.
Independent integer arithmetic matches. The record pins both actual consumed
handoffs, exact quarter period, source inputs and zero residual. No quarter-to-
annual extrapolation, duplicate OCF-component subtraction or new production
formula was used.

## Gaps

- CP-1/CP-1B source, date, unit, note-coverage and external-version limits persist.
- Resolve the specific 131/132 equivalents disclosure difference before using
  the event as an exact disaggregated cash bridge.
- Obtain dated unrestricted/location cash, facility access conditions, minimum
  operating cash, covenant certificate and complete monthly cash-use forecast.
- Obtain operative debt/collateral documents and updated securitization renewal/
  repayment evidence; no current refinancing, legal-capacity or priority conclusion.
- Full LTM/seasonal stress and forward liquidity remain unproven. The CP-2A
  static stresses are hypothetical, not realized outcomes of this quarter.

## Next module

CP-3C can use the dated cash-allocation/facility questions with these limits.
CP-2G needs dated future cash/debt assumptions and a valid fiscal calendar.
Delivery may copy this historical bridge, attributed cash-liquidity measure and
limits. Actual delivery replaces CP-MEMO; no extra analytical memo is required.
This closes CP-1B's bounded consumption link; it does not complete forward
CP-2D, provider/runtime or pathway qualification.
