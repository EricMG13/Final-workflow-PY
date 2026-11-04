# CP-2A — Static downside screen

## Request

Use the accepted annual handoffs to identify what breaks first under bounded hypothetical annual stresses. This is fresh model analysis and direct use of existing pure calculation functions, not a forecast, full runtime execution or CP-2B event/calendar review. Base period is FY2024, October 1, 2023–September 30, 2024; closing balance amounts are September 30, 2024 instants. Currency and amounts are USD millions. Confidence is Medium, below High.

## Sources

| Input | Handoff evidence and contribution |
|---|---|
| CP-1 | `CP-1-attempt-2.md` SHA-256 `301af0eeed2d90edd2671ef0c71dc759e66c000b3722a0c4ceacfba6fb1332bb`; numerical operands, definitions, source references and limitations. Selected base values: EBITDA As Defined USD 4,173m (T4.10/T4.17, PDF 142); annual cash interest paid magnitude USD 1,158m (T4.5 supplemental cash-interest row, PDF 109); OCF less capex proxy USD 1,880m (T4.10/T4.5); carrying debt USD 24,880m (T4.10/T4.6 classification sum 24,296 + 98 + 486); reported closing cash USD 6,261m (T4.6). |
| CP-1A | `CP-1A-attempt-3.md` SHA-256 `6f63963177c2ea7d54bd043532e250e28625ea70c0ec229d63d55768c2c174fe`; contextual demand/channel, margin/cash conversion and documented debt-supported distribution evidence; critical gaps in current unrestricted cash/liquidity forecast, covenant certificate and executed debt/legal documents constrain inference. |
| CP-2 | `CP-2-attempt-2.md` SHA-256 `249d0cbdf1ba8159dcae68d4ff3241c73ea092ff66353c0c2eef08691e0afa57`; primary downside chain combines aircraft/airline/OEM demand pressure, potentially delayed defense demand, cost non-flex/pass-through, weaker operating cash, distribution/debt-service claims and FY2028–FY2029 refinancing concentration. These mechanisms inform scenario choices, not calibrated magnitudes. |
| Method/code | Selected method `src/deploy_vii/methods/cp2a.md`, imported revision `2c809379cbba508888b7fbe28ee14eac5a294bbf`, SHA-256 `28be81bfb97a83e739e4a514612a2db3bf12b72480128f54c66c33fc2ab06236`. Existing calculation functions in `src/deploy_workflow/owners/cp2a.py`, SHA-256 `b246e5bdcb4622511ac557d4bb3a5afd7aa2f22960f69e00ac4fba235a76b5fe`. Direct BaseOperands adaptation uses actual handoff values and keeps lineage here and in inputs JSON; no fabricated Fact records or source map, runtime, providers or code changes. |

## Findings

**T2B.1 Scenarios — analyst assumptions, not issuer forecasts or probability estimates.** Sizes are purposeful but not economically calibrated. The first isolates CP-2's demand/margin path; the second adds interest cost to reflect the debt-service/refinancing pathway. CP-1A's distribution evidence is contextual to cash allocation risk, not an additional modeled shock.

| Scenario | EBITDA As Defined decline | Cash interest increase | Rationale |
|---|---:|---:|---|
| Base (no stress) | 0% | 0% | Zero-shock control. |
| Demand and margin pressure | 10% | 0% | Illustrative demand/cost pressure from CP-2; CP-1A notes absent price/volume, cost-flex and pass-through data. |
| Demand, margin and interest pressure | 20% | 10% | Illustrative combined operating and interest pressure; the increment is an analyst overlay, not a rate forecast. |

**T2B.2 Base operands.** All flows are FY2024. EBITDA is issuer EBITDA As Defined, a non-GAAP measure, not ordinary EBITDA or operating cash. Interest is positive cash interest paid. “FCF” in the calculator means the OCF-less-capex cash-after-capex proxy, not issuer-defined FCF. Debt is a carrying-value classification sum including separate securitization, not gross principal. Cash is reported closing cash, not established unrestricted cash. Net debt (calculated) is USD 18,619m; it is mechanical and not a liquidity measure.

**T2B.3–T2B.4 Stressed flows and newly calculated ratios.** These are calculated values from the stated operands, not issuer-reported/covenant ratios. Rounded display does not affect exact comparison.

| Case | Stressed EBITDA As Defined (USD m) | Cash interest (USD m) | Cash-after-capex proxy (USD m) | Total carrying debt / EBITDA | Net carrying debt / EBITDA | EBITDA / cash interest | Proxy / carrying debt |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base | 4,173.00 | 1,158.00 | 1,880.00 | 5.96x | 4.46x | 3.60x | 7.56% |
| Demand and margin pressure | 3,755.70 | 1,158.00 | 1,462.70 | 6.62x | 4.96x | 3.24x | 5.88% |
| Demand, margin and interest pressure | 3,338.40 | 1,273.80 | 929.60 | 7.45x | 5.58x | 2.62x | 3.74% |

**T2B.5 Reconciliation.** The zero-shock control exactly retains the supplied E=4,173, I=1,158, proxy=1,880, D=24,880, C=6,261 and derived D−C=18,619 operands. CP-1 does not supply reported total/net leverage, interest coverage or FCF/debt ratios in this accepted handoff; reconciliation to reported ratios is absent. The ratios shown are independently calculated from known operands and do not fill that gap. The later runtime's nine-T4.10-fact offering and reported-ratio gate were not invoked under the specified direct-Markdown adaptation.

**T2B.6–T2B.8 Breakpoints, rank and scenario comparison.** Breakpoint declines hold cash interest at the FY2024 base. Exact fractions control ordering; percentages below are rounded for display. “Crossed” compares each scenario's actual stressed metric, including its stressed interest, to each breakpoint level.

| ID | Break definition or watch | Required EBITDA decline | Order | 10% / 0% | 20% / 10% |
|---|---|---:|---:|---|---|
| b03 | 7.0x total carrying-debt / EBITDA analyst watch | 14.8266% | 1 | Not crossed (6.62x) | Crossed (7.45x) |
| b04 | 3.0x EBITDA / cash-interest analyst watch | 16.7505% | 2 | Not crossed (3.24x) | Crossed (2.62x) |
| b01 | Cash-after-capex proxy at/below zero | 45.0515% | 3 | Not crossed (USD 1,462.70m) | Not crossed (USD 929.60m) |
| b02 | EBITDA no longer covers base cash interest (1.0x) | 72.2502% | 4 | Not crossed (3.24x) | Not crossed (2.62x) |

The earliest calculable watch is b03 at a 14.8266% assumed EBITDA decline with interest held at base. This is an analyst watch threshold, not a covenant, default point or probability. Scenario crossings are separate: the combined scenario crosses both chosen watch levels while remaining above zero proxy and above 1.0x interest coverage. Exact outputs, formulas and control checks are in `CP-2A-attempt-1-calculations.txt`.

**T2B.9 Own limitations and coverage.** Debt/cash remain fixed at closing balances; no tax shield or working-capital/capex response is modeled. Assumed EBITDA reduction lowers the cash-after-capex proxy one-for-one. Only incremental interest shock is deducted from that proxy because base OCF already includes base cash interest, tax and working-capital effects. Breakpoints hold interest at base; scenario crossings use actual stressed interest. There is no runway, covenant headroom, funding/refinancing execution, recovery or default analysis. Liquidity, maturities and forward balance-sheet paths remain CP-2D/CP-2G/CP-3C work. Although CP-2B resolves to CP-2A in the catalog, this module does not cover Deploy V CP-2B event-risk/catalyst-calendar duties T5.1–T5.7.

A separately labeled mechanical zero-denominator check (not an issuer scenario) returns interest coverage as not calculable when cash interest is zero; this is recorded in the transcript. CP-1 source limitations remain: PDF 156 supplemental table not reviewed, incomplete visual/glyph verification for some pages, and external authenticity/version comparison not performed. CP-1A's critical executed-document and current liquidity/covenant gaps remain unresolved; price/volume, cost pass-through, acquisition pro forma, maintenance capex and current liquidity are not supplied. Missing evidence is not treated as adverse fact.

## Calculations

See `CP-2A-attempt-1-calculations.txt` for the exact Decimal outputs, rational breakpoint fractions, ranking and crossings, function identities, zero-shock operand validation and separately labeled zero-denominator boundary check. Python execution used `PYTHONPATH=src .venv/bin/python`; no calculation formula was rewritten. Ratios are mechanical newly calculated annual ratios, not reconciled issuer metrics or covenant tests.

## Gaps

| Gap | Effect on this screen / next evidence |
|---|---|
| No reported ratios in accepted CP-1 handoff | T2B.5 reported-ratio reconciliation cannot be performed; no calculated value substitutes for a reported ratio. |
| No current unrestricted-cash schedule, covenant certificate or liquidity forecast (CP-1A Critical) | Closing cash cannot establish available liquidity, headroom, runway or distribution capacity. Obtain current package. |
| Executed debt/indenture/collateral documents not reviewed (CP-1A Critical) | No legal capacity, collateral, priority or creditor-treatment conclusion; CP-4/CP-3C must examine documents. |
| No quantified demand, price/volume, backlog, margin pass-through or working-capital response; no maintenance/growth capex split | Hypothetical operating shocks are not calibrated; proxy is not sustainable FCF. Obtain current operating and capex evidence if sensitivity calibration is needed. |
| No pro forma acquisition earnings/financing bridge; no current maturity/refinancing execution path | No transaction-adjusted leverage or refinancing outcome; forward path remains separate. |
| CP-1 source limitations and CP-1A ownership/control, lender-reporting and related-party gaps | Limits current credit and governance interpretation as carried in CP-2; preserve rather than infer missing facts. |

## Next module

- **CP-2D:** may use the static proxy stress and earliest watch as inputs/questions only; it must add current liquidity, obligations, availability and runway evidence. This screen does not calculate liquidity.
- **CP-2G:** may use the shocked earnings/interest rows as starting sensitivities; it must build a forward debt/cash path from supported dated flows. Closing debt/cash were fixed here.
- **CP-3C:** may use the combined operating/interest mechanism and watch crossings to frame refinancing/LME review. No event-risk calendar, legal terms, current maturity execution or refinancing outcome is established here.
- **Delivery:** may carry the base values, meanings, periods, units, source references, calculated ratios and assumptions with explicit missing-ratio reconciliation and limitations. These are intermediate handoff results; final deliverables must be populated from actual module handoffs and checked against them.
