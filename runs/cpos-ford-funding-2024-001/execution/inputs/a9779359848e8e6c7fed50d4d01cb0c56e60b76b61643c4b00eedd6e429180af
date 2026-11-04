# CP-1 — selected historical agency financial input

## Request

Admit financial operands for Ford Otomotiv Sanayi A.S., using the April 11, 2024
S&P report. Historical functional case, explicitly outdated; separate from TDG.
This host-model extraction covers selected agency-reported rows, not full issuer
accounts, full CP-1 or an isolated provider/runtime run.

## Sources

Actual CP-0 source admission and the retained S&P body in
`sources/fitch-and-metrics.json`, PDF page 7, forecast summary. Source columns
2023a/2024f/2025f, text lines 260–262; amounts TRY millions. Exact row locators,
capture hashes, source literals and calculations are in `financial-calculations.json`.
S&P adjusts all figures unless explicitly labelled reported.

## Findings

| Metric | 2023 actual | 2024 agency forecast | 2025 agency forecast |
|---|---:|---:|---:|
| Revenue | 411,906 | 742,742 | 1,056,981 |
| Reported EBITDA | 50,082 | 64,619 | 82,445 |
| Capitalised development adjustment, signed | (1,932) | (7,249) | (10,393) |
| Disposal adjustment | 65 | -- | -- |
| S&P adjusted EBITDA | 48,214 | 57,370 | 72,052 |
| Cash interest, signed | (4,505) | (8,310) | (11,596) |
| Cash tax, signed | (1,704) | (343) | (5,220) |
| FFO | 42,005 | 48,717 | 55,236 |
| Capex | 30,128 | 38,989 | 52,010 |
| FOCF | 16,425 | 8,611 | 8,834 |
| Dividends | 18,424 | 27,087 | 30,378 |
| DCF | (1,999) | (18,475) | (21,544) |
| S&P adjusted debt | 76,904 | 127,142 | 144,661 |
| Source debt/EBITDA | 1.6x | 2.2x | 2.0x |
| Source FFO/debt | 54.6% | 38.3% | 38.2% |
| Source EBITDA margin | 11.7% | 7.7% | 6.8% |
| Source EBITDA interest coverage | 8.2x | 6.7x | 6.1x |

Reported and adjusted earnings are different. Debt/FFO/margin ratios recomputed
from displayed source amounts round to the reported one-decimal values. EBITDA
interest coverage is not recomputed from cash interest: that would substitute a
different denominator. All currency amounts retain TRY-million units.

## Calculations

The unchanged Decimal quotient helper and independent Fractions check nine
ratios, nine displayed roundings and three FFO identities: 21 checks. The source
display leaves residual −1 in the 2023 known-numeric EBITDA adjustment subtotal
and +1 in the 2024 FOCF-minus-dividend-to-DCF comparison, TRY millions. Preserve
both source figures and residuals. Their cause has not been conclusively resolved;
no zero plug or source correction is made. Source `--` remains null; a subtotal
of identified numeric entries does not establish a missing adjustment as zero.

## Gaps

No independent issuer-account reconstruction or complete S&P adjustment audit.
Original PDF bytes and successful visual cell audit are absent; exact retrieved
text/locators survive. The two displayed residuals remain explicit. Forecasts
are attributed historical opinions, not realised outcomes or current guidance.

## Next module

CP-2G should actually consume these adjusted values and source ratios as a
published case, keeping financial definitions and residuals. CP-2H must not apply
Fitch's net leverage threshold to S&P's adjusted gross debt ratio. This selected
input is usable within scope; it is not full CP-1 acceptance or final delivery.
