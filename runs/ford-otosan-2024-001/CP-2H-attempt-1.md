# CP-2H — Ford Otosan historical ratings functional case

## Request

Assess Ford Otomotiv Sanayi A.S. using two reports dated **April 11, 2024**.
This evidence is outdated; it establishes neither current ratings nor TDG
conclusions. Actual host-model analysis with tools/context, no paid provider or
full imported-owner execution. The input forecast is an agency-published case,
not our independent three-year model.

**View:** agency divergence is explainable, while exact trigger headroom cannot
be created by comparing unlike ratios. Confidence is Medium for this historical
interpretation. Rating conditions remain conditional agency opinions.

## Sources

Actually consumed this case's CP-0, selected CP-1, published-forecast handoff and
retained S&P/Fitch bodies. Exact hashes and unchanged arithmetic identities are
in `CP-2H-calculations.json`. `instructions.md` was frozen before these outputs.
No TDG input was reused. The broader CP-2H skill/REF steps supply the ten register
meanings; later helpers supply arithmetic, not authority to omit definitions.

S = [S&P April 11 report](https://www.fordotosan.com.tr/documents/Documents/Diger_Duyurular/sp-rating.pdf),
12 PDF pages. F = [Fitch April 11 report](https://www.fordotosan.com.tr/documents/Documents/Diger_Duyurular/fitch-publishes-ford-otosans-bb-idr-outlook-stable-rates-proposed-eurobond-bbexp.pdf),
13 pages. Both are agency-authored copies publicly hosted by the issuer. Page
numbers below are one-based. Exact retrieved text is retained; raw PDF bytes and
successful visual verification are not claimed.

## Findings

### T2R.1 — dated rating posture

| Agency / entity | Issuer rating / outlook | Proposed unsecured issue | Date / source |
|---|---|---|---|
| S&P / Ford Otomotiv | BB− **preliminary**, Positive | BB− preliminary | 2024-04-11; S 1, 11 |
| Fitch / same company | BB+, Stable | BB+(EXP), RR4 | 2024-04-11; F 1, 7; committee date April 4 is distinct |

The proposed bond's final identity/terms and rating were not yet established in
these source states. Neither provisional issue rating is treated as final.

### T2R.2 — applicable historical criteria

| Agency | Report-cited framework / date | Applicability and limit |
|---|---|---|
| S&P | Corporate January 7, 2024; sector April 4, 2024; ratios/adjustments April 1, 2019; group/country/T&C frameworks | S 10 explicitly lists the applicable framework. Report interpretation, not reconstruction of every criteria body. |
| Fitch | Corporate November 3, 2023; parent/subsidiary June 16, 2023; country ceiling July 24, 2023 | F 8–9. Historical application; no assertion these are current today. |

### T2R.3 — metric bridge

| Agency metric | Admitted input / treatment | Prevented substitution |
|---|---|---|
| S&P adjusted gross debt/EBITDA | Actual published-forecast handoff; source adjustment basis retained | Not Fitch net leverage or reported covenant net debt. |
| Fitch net leverage / FCF margin | F-specific definitions and approximate narrative | No reconstructed numeric path; S&P FOCF is not substituted. |
| Earnings geography | S distinguishes production/earnings location from export sales | Export share does not satisfy outside-country earnings conditions. |

The financial handoffs preserve displayed residuals and distinguish cash
interest from the denominator of reported interest coverage. Unlike labels and
adjustments are reasons to qualify comparison, not silently select one number.

### T2R.4 — trigger headroom

| Agency / direction | Published condition / locator | Evidence-aligned result |
|---|---|---|
| Fitch negative | Net leverage above 2x by 2025; F 6 | Narrative around 2x gives approximately zero central distance only. Exact headroom and strict crossing remain indeterminate. |
| Fitch negative | EBITDA margin below 6%, or FCF margin below 1%, with sustained conditions; F 5 | No aligned exact series/window; not calculable. |
| Fitch positive | FCF margin above 4% sustained, net cash or stronger parent/support factors; F 5 | Possible factors, not an automatic Boolean rating rule. |
| S&P positive | Outside-country earnings above 30% plus continuing tests/liquidity/metrics; S 5–6 | Its approximate EBITDA-location estimate implies a 15% outside proxy, about 15 pp from the condition. **Proxy only:** trigger earnings definition and other conditions are not fully bridged. |

S&P's stated forecasts and its 3.5x reported-net-leverage loan covenant are not
invented agency thresholds. No 3.5x-minus-adjusted-gross-ratio headroom is shown.

### T2R.5 — qualitative modifiers and contrary evidence

| Factor | Direction / assessment | Source |
|---|---|---|
| Sovereign/T&C resilience and non-domestic earnings | Central to S&P's conditional upside and downside | S 1–2, 5–6 |
| Contractual operating protection / investment cycle | Supports Fitch's case; capex and distributions still absorb funds | F 1–4 |
| Market execution and cash access | Successful funding is assumed in the source case, not demonstrated by a provisional rating | S 5, 7–8; F 1, 6 |

The countercase to pressure is protected operating cash generation and a
successful investment ramp. It wins only with realised accessible funds and
continued contractual/operating performance; neither agency opinion guarantees it.

### T2R.6 — transition cases and timing

| Case | Classification / catalyst | Timing and limit |
|---|---|---|
| Published case | S&P supportive posture / Fitch within current published range | Historical opinions; no forecast of an unchanged rating. |
| Adverse operating/access or T&C case | Negative pressure; test failure is a conditional escalation | Event-driven; Fitch leverage condition names 2025. No actual breach asserted. |
| Stronger overseas earnings/support case | Supportive, subject to the agency's other conditions | Sustainability is not a supplied number of quarters; no automatic notch. |

No independently calculated numeric downside/upside series was supplied for
this case. Scenario labels are causal conditions, not probability estimates.

### T2R.7 — agency divergence

| Difference | Evidence-based explanation | Unresolved point |
|---|---|---|
| BB+ versus preliminary BB−: two ordinal symbol steps | Same entity/date; differing country/T&C and group-support treatment | Not a two-notch error, probability, average or pricing opportunity. |
| Stable versus Positive | Different source frameworks and conditional catalysts | Not contradictory predictions of the same mechanical test. |

Fitch applies a Romanian country-ceiling framework; S&P's country/T&C test
constrains the result despite its standalone assessment. This helps explain the
divergence without claiming a complete numerical attribution of every rating step.

### T2R.8 — instrument and notching implications

| Proposed instrument | Source treatment | Limitation |
|---|---|---|
| Unsecured bond | S&P aligns preliminary issue/issuer ratings and does not apply recovery analysis; Fitch supplies expected rating/RR4 | S 9; F 7. No recovery percentage inferred from a label, no final ISIN assumed, no legal priority or final action established. |

### T2R.9 — monitoring handoff

| Monitor | Observable trigger / horizon | Receiver |
|---|---|---|
| Bond completion / final documents | Actual closing and final agency actions | CP-3C/CP-4 before treating proposed funding as available. |
| Net leverage and conversion | Aligned Fitch metric by 2025; cash uses versus the source plan | CP-2G/CP-3C; no gross/net substitution. |
| Earnings location / T&C / support | Actual overseas ramp, stress-test evidence or parent/country action | CP-2/CP-6; no invented review date. |

### T2R.10 — gaps

| Gap | Effect / required follow-up |
|---|---|
| Exact Fitch adjustment path and sustained windows | True numeric headroom not supplied; obtain aligned observations/terms, not proxy ratios. |
| Independent model and full criteria reconstruction | Published-forecast/source case only; no full owner/provider qualification. |
| Original files, visual audit, source-display residuals | Retained text/cell scope only; preserve financial −1/+1 residuals. |
| Later actions, executed terms and current access | Outdated functional case, not current underwriting or a completed TDG pathway. |

## Calculations

Existing Decimal helpers calculate the explicitly approximate central distance,
the conditional geography proxy and two-step ordinal comparison. Six synthetic
signed/equality tests, two missingness/timing tests and four range/duration tests
also passed with independent expectations. These controls prove calculator
behavior, not issuer forecasts. Repeated observations without a source-defined
window and different cases at one date do not prove a sustained agency trigger.

## Gaps

T2R.10 and every qualifier above remain. The real source-based response covers
ratings, definitions, conditions, divergence and monitoring; synthetic controls
do not upgrade its economic or execution scope. No source or agency conclusion
was invented to fill a calculation cell.

## Next module

CP-3C must actually open this response and published forecast, preserve the
provisional funding conditions, and test the source's cash-use assumptions.
CP-4 needs executed terms; CP-6 receives the strongest contrary case and genuine
agency differences. Delivery reads these actual handoffs. CP-MEMO is replaced
by the actual deliverables, not another analytical run.
