# CP-3C — actual historical ratings-to-funding consumption

## Request

Use the checked CP-2H handoff to examine the published funding case for Ford
Otosan. Outdated information as of April 11, 2024; not TDG or current underwriting.
This is a bounded CP-3C intake and funding calculation, not complete refinancing/
LME analysis or a legacy/provider run.

## Sources

Actually opened `CP-2H-attempt-2.md`, SHA-256
`4f390c0b0e36f2ea91f179ffd4d872d696635d1a06a2a3b3719590c496c74b72`,
the actual `CP-2G-published-forecast.md`, financial calculation record and S&P
source liquidity section, PDF pages 7–8. Exact hashes, source operands and helper
outputs are in `CP-3C-intake-calculations.json`. No other issuer's inputs are used.

Selected questions are CP-3C's source gate, liquidity/market-access and funding-
path intake. Existing `_total`, `_diff` and `_ratio` are reused; their arithmetic
does not prove complete maturity, legal-capacity or creditor-treatment analysis.

## Findings

CP-2H changes how the funding case is used: preliminary/expected ratings do not
establish completed bond proceeds. The agency's liquidity assessment assumes
bond placement; it also identifies a signed capex facility, whose permitted uses
and drawability still matter. Treating both as unrestricted settled cash would
overstate demonstrated access. Conversely, a conditional removal of funds is a
stress test, not evidence that financing actually failed.

The source's 2024 plan starts January 1, 2024; it is not twelve new months from
our April review date. In TRY **billions**, sources are cash 15.2 + cash FFO 63 +
planned bond proceeds 16 + capex-facility availability 15 = **109.2**. Uses are
short maturities 33.8 + working capital 8.6 + additional WC swings 2 + unstressed
reported capex 46.3 = **90.7**. This reconstructs approximately 1.2x using the
displayed rounded components, not the agency's undisclosed full working model.

| Conditional calculation | Sources / uses, TRY bn | Difference, TRY bn | Ratio |
|---|---|---:|---:|
| Published-plan component reproduction | 109.2 / 90.7 | 18.5 | 1.2040x |
| Remove planned bond | 93.2 / 90.7 | 2.5 | 1.0276x |
| Assume capex facility unavailable | 94.2 / 90.7 | 3.5 | 1.0386x |
| Remove both sources | 78.2 / 90.7 | (12.5) | 0.8622x |
| Add unstressed distribution overlay | 109.2 / 117.8 | (8.6) | 0.9270x |
| Illustrative 15% capex reduction | 109.2 / 83.755 | 25.445 | 1.3038x |

These are separately stipulated cases. The source's stress assessment excludes
committed dividends, while its unstressed plan has distributions. The overlay
exposes why those cash-use assumptions matter; it does not prove a real shortfall
or that all facility funds can finance dividends. The capex reduction is a stated
illustrative use of the source's mitigation estimate, not its reported 1.2x case.

Do not substitute the adjusted forecast table's FFO for the liquidity narrative's
cash-FFO input, or use Fitch's adjusted available cash in place of the S&P balance.
Likewise, S&P gross leverage cannot establish Fitch net-leverage headroom. The
agency divergence carries methodology/condition information, not a financing
guarantee or mechanically cheaper market price.

The causal risk is operating/currency or cash-access weakness during investment
and distributions → less usable funding → more dependence on execution and
cash-use flexibility. The contrary case is completed ordinary-course funding,
protected operating generation and feasible spending/distribution adjustment.
Verify final documents/actions, actual access and cash uses before deciding which
case applies. No realised failure, default or LME intent is inferred.

## Calculations

Two source totals, six ratios and six balances were independently checked using
Fractions/integer rounding; two missingness controls preserve gaps rather than
zero. The helper stores four-decimal ratios; source amounts remain approximate.
Currency units are TRY billions here versus TRY millions in the financial table;
no new FX conversion was applied. No source amount or residual was overwritten.

## Gaps

No complete executed maturity/credit/indenture/intercreditor package, facility
certificate, binding final bond terms, market quotes or current access/outcomes.
Exact legal capacity, full funding need, refinancing feasibility, creditor
priority/recovery and LME vulnerability score remain unassessed. This is genuine
downstream use of CP-2H within scope, not full CP-3C coverage.

## Next module

CP-4 needs operative documents for capacity/priority. CP-5/CP-5A should audit the
provisional ratings, unmatched definitions, conditional liquidity assumptions
and retained source-display residuals. CP-6 receives the source-based case and
countercase. Delivery may reproduce these checked handoffs with date, issuer,
conditions and units; actual deliverables replace CP-MEMO.
