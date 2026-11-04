# CP-2G — published historical forecast admission

## Request

Pass the actual S&P published case for Ford Otosan into CP-2H. Outdated as-of
2024-04-11, independent of TDG. Current host-model consumption; this does not
claim a new management/base/downside engine, a third forecast year or full
CP-2G runtime acceptance.

## Sources

Actually consumed `CP-1-selected-input.md`, SHA-256
`a9779359848e8e6c7fed50d4d01cb0c56e60b76b61643c4b00eedd6e429180af`,
and `financial-calculations.json`; opened the underlying selected S&P summary
rows. The source record is an agency forecast dated April 11, 2024, PDF page 7,
TRY millions except ratios. No TDG number or output is imported into this case.

## Findings

| Calendar year / status | S&P debt | S&P EBITDA | S&P FFO | Recomputed debt/EBITDA | Recomputed FFO/debt |
|---|---:|---:|---:|---:|---:|
| 2023 actual in agency report | 76,904 | 48,214 | 42,005 | 1.5951x | 54.6200% |
| 2024 agency forecast | 127,142 | 57,370 | 48,717 | 2.2162x | 38.3170% |
| 2025 agency forecast | 144,661 | 72,052 | 55,236 | 2.0077x | 38.1831% |

These are recomputations of displayed agency amounts; the source's rounded
ratios remain 1.6x/2.2x/2.0x and 54.6%/38.3%/38.2%. They are not new forecasts.
The published path increases adjusted debt faster than earnings initially,
then improves the leverage ratio as earnings grow. It does not show actual
debt repayment: forecast debt rises in both years. Neither ratio direction nor
an adequate-liquidity opinion proves current financing execution.

Definitions remain agency-specific. S&P's narrative debt includes deferred
consideration/pension adjustments and does not deduct available cash. Its
reported EBITDA interest-cover metric is different from EBITDA/cash-interest.
Fitch's net-leverage/FCF definitions cannot be obtained by substituting these
gross-debt/FOCF ratios. Exact adjustment reconciliation remains incomplete.

## Calculations

The retained financial record independently verifies all three leverage and
FFO/debt recomputations and source-rounded comparisons. The −1 / +1 TRY-million
display residuals stay attached. No source amount was changed or later-year
value fabricated, and no rough narrative FX/year label was used as a new driver.

## Gaps

No independent downside/upside numerical forecast or actual realised outcome.
The agency report is the forecast source, not an independently built CP-2G
model. Full issuer financial reconstruction, Fitch adjustment bridge, raw-PDF/
visual verification and the two source-display residuals remain open.

## Next module

CP-2H: actually consume this published case and both agency reports; identify
which conditions can be assessed and which metrics cannot be compared. Do not
apply Fitch's 2x net-leverage sensitivity to S&P's 2.2162x gross ratio. Preserve
the outdated case and provisional issue status in the next handoff and delivery.
