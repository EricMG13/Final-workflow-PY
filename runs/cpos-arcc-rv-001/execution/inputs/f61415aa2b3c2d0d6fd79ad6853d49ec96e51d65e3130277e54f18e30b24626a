# CP-0 — ARCC historical market-source admission

## Request

Admit the selected annual debt fair values, executed July 2029 terms and
same-date Treasury curve under `instructions.md`. Ready with Limitations for
historical evaluated-price/convention analysis. Actual current host model,
2026-11-04, with preceding context; no provider/native source qualification.

## Sources

- Existing `../arcc-2024-001/sources/ARCC-FY2024-10K.pdf`: original 320-page
  issuer PDF, SHA-256 `4483569e723b1a0c479d1ce45bcf64e11f6c82c98754bce1aa317641eb81e170`.
  Clean `annual-pages.txt` has 1-based page markers. Actual additional coverage:
  p94 terms/swaps, p95 priority, p290 valuation method, p291 fair-value table.
- Existing `../arcc-2024-001/sources/supplement-lines.txt` and exact legal web
  captures: executed May 13, 2024 first supplement for 5.950% July 2029 notes.
  L73–83 identity/coupon/payment dates/day count; L97–127 redemption formula.
  The original legal HTML raw request had returned 403; indexed text survives.
- `sources/treasury-2024.csv`: actual official Treasury download, exact URL,
  transport and hash in `sources/retrieval.json`; 250 historical observations.
  `treasury-web-capture.txt` retains the public body, header, selected date and
  description of indicative bid-side par-curve rates. Web-tool CSV parsing was
  unsupported; direct CSV retrieval succeeded, without bypass or credentials.

## Findings

| Check | Source-backed result / admission limit |
|---|---|
| Issuer/security | Ares Capital Corporation consolidated group. Supplement L73: CUSIP 04010L BG7, ISIN US04010LBG77, 5.950% Notes due July 15, 2029; 850 USDm principal. Not Ares Management or a facility/CLO claim. |
| Visual / text | Retained original p291 was rendered and viewed this run: 2024 and 2023 columns, principal versus carrying/fair values, source dashes and Level-2 footnote agree with text. Earlier run's p65/p274 checks remain their original scope. No all-page audit. |
| Valuation identity | Annual p290 says remaining payments are discounted at applicable current market rates, considering rating changes or market quotes if available; p291 footnote6 identifies Level2. No direct clean-price, bid/ask, intraday timestamp or executable-lot evidence. |
| Coupon identity | Annual p94 effective stated rate 6.040% includes swaps; the actual supplement sets noteholder coupon 5.950%. These describe different roles, not a conflict to average away. |
| Benchmark mapping | Official CSV selected Date 12/31/2024: 2 Yr4.25%, 3 Yr4.27%, 5 Yr4.38%, 7 Yr4.48%, 10 Yr4.58%. Header/row matching is explicit, not positional guessing across the website's extra empty columns. |
| Dates / freshness | ARCC values at Dec31 2024, annual audit February5 2025; Treasury row Dec31 2024. Outdated now, but same valuation vintage for this functional case. Not all evidence was available on Dec31. |
| Method applicability | Existing high-level bond helper supports regular coupon-date/zero-accrued cases only. Dated settlement must not be passed through that interface. Its low-level mathematical PV/yield functions can accept explicit scenario cash flows; convention/price ambiguity must remain visible. |

## Calculations

None: no yield/spread, credit inference or analyst convention is accepted merely
by this admission. Primary source identities and coverage are retained separately.

## Gaps

Exact issuer/dealer clean/dirty convention and timestamp, observed two-way market,
full legal terms for other notes, all make-whole future states, external corporate
peers/ratings, trade depth/flows, portfolio constraints and current data. These
limit the dependent conclusions, not the real source values that are available.

## Next module

CP-1 should extract literal principal/carrying/fair values and the actual July
2029 terms. CP-3D must preserve their distinct roles, disclose conditional pricing
assumptions and avoid treating this evaluated disclosure as an executable quote.
