# CP-2A — real-issuer static downside screen

Use the accepted TDG Markdown handoffs to produce one bounded downside analysis.
This is fresh model analysis plus existing calculation functions, not execution
of the imported owner/runtime or a full forecast. No provider call is requested.

## Inputs and selected scope

- `CP-1-attempt-2.md` in this directory, SHA-256
  `301af0eeed2d90edd2671ef0c71dc759e66c000b3722a0c4ceacfba6fb1332bb`.
- `CP-1A-attempt-3.md`, SHA-256
  `6f63963177c2ea7d54bd043532e250e28625ea70c0ec229d63d55768c2c174fe`.
- `CP-2-attempt-2.md`, SHA-256
  `249d0cbdf1ba8159dcae68d4ff3241c73ea092ff66353c0c2eef08691e0afa57`.
- Read `src/deploy_vii/methods/cp2a.md`, SHA-256
  `28be81bfb97a83e739e4a514612a2db3bf12b72480128f54c66c33fc2ab06236`.
  The selected later method is a static annual stress, from imported revision
  `2c809379cbba508888b7fbe28ee14eac5a294bbf`.
- Reuse `src/deploy_workflow/owners/cp2a.py`, SHA-256
  `b246e5bdcb4622511ac557d4bb3a5afd7aa2f22960f69e00ac4fba235a76b5fe`.

The later runtime declares only CP-0/CP-1 inputs. For this Markdown workflow,
CP-2's actual risk synthesis and CP-1A context explicitly inform scenario
rationale; CP-1 supplies the numerical operands. Record what each contributed.
Do not open issuer sources, expected keys, synthetic cases or historical answers.

CP-2B resolves to CP-2A in the catalog, but Deploy V's CP-2B also had event-risk
and catalyst-calendar duties (T5.1–T5.7). Those are not performed by this static
screen and must not be claimed covered. Forward paths, liquidity, legal capacity
and the event/calendar work remain separate later checks.

## Preserve the base definitions

Use the FY2024 annual base, 2023-10-01 through 2024-09-30; closing balances are
September 30 instants. Read and verify these operands in the actual handoff:

| Calculator field | Exact analytical meaning | CP-1 source |
|---|---|---|
| `ebitda` | Issuer EBITDA As Defined, not ordinary EBITDA or operating cash | T4.10 / T4.17, total company FY2024 |
| `interest` | Positive magnitude of annual cash interest paid | T4.5 supplemental cash-interest row |
| `fcf` | Calculated operating cash less capex **proxy**, not issuer-defined FCF | T4.10, Operating cash less capex; T4.9 / calculation transcript |
| `total_debt` | Total debt **carrying value** including separate securitization | T4.10 classification sum with its operands; not gross principal |
| `cash` | Reported closing cash; not established unrestricted cash | T4.10 / T4.6 / T4.5 |

Use those meanings in every table and conclusion. The internal field `fcf`
does not rename the proxy; label all resulting flows and breakpoints accordingly.
Likewise leverage here uses carrying debt and issuer EBITDA As Defined; it is not
an issuer-reported or covenant leverage ratio. Do not silently treat all cash as
available: any ratio netting reported cash is a mechanical measure, not liquidity.

## Analysis and reuse

Select two or three purposeful scenarios and up to two analyst watch levels.
Use CP-2's actual downside mechanisms to explain the choices. Magnitudes and
watch levels are explicit hypothetical analyst assumptions, not issuer forecasts,
source facts, covenant limits or estimated event probabilities. Confidence stays
below High. Do not assume a generic stress is economically calibrated.

Retain the selected base, each operand's meaning/unit/period/upstream reference,
scenario choices, rationales and limits as `CP-2A-attempt-1-inputs.json`.
Then use Python (`PYTHONPATH=src .venv/bin/python`) and the existing functions:
`BaseOperands`, `stress`, `ThresholdSpec`, `break_points`, `rank`, `crossing`.
Read their interfaces; do not rewrite their formulas or add product code.

Execution adaptation: construct `BaseOperands` directly from the Markdown's
actual values, with lineage in the JSON/Markdown instead of fabricated typed
Fact records. Its pure functions do not need the runtime's `sources` map. These
are new **calculated** annual ratios from known operands, so do not claim a
reconciliation to reported ratios that CP-1 does not supply. The runtime's
nine-T4.10-fact offering and reported-ratio gate are not invoked by this direct
calculation; state that difference explicitly. Preserve every genuinely missing
operand as missing, and never invent reported ratios to satisfy that contract.

Calculate a zero-shock control plus the selected scenarios, the proxy-zero and
interest-coverage breakpoints, chosen watch breakpoints, their order and scenario
crossings. Retain exact calculation output and code/function identity in
`CP-2A-attempt-1-calculations.txt`. Show readable rounded ratios alongside exact
results; do not round before comparisons or ranking. Validate the control against
the supplied base, and check a zero-denominator boundary as a separately labelled
mechanical check, not an additional real-issuer analytical scenario.

Explain what the result establishes and what it cannot: debt/cash fixed at closing
balances; no tax shield or working-capital/capex response; a one-for-one assumed
earnings reduction in the cash-after-capex proxy; only incremental interest shock
deducted from that proxy (base OCF already includes base cash interest/tax/WC);
breakpoint ranking holds interest at base; scenario crossings use actual stressed
interest; no runway, covenant headroom, funding/refinancing execution or recovery.
Identify the earliest calculable watch/break without calling it default.

## Output and handoff

Write `CP-2A-attempt-1.md` with exactly the six headings Request, Sources,
Findings, Calculations, Gaps, Next module. Cover the selected T2B.1–T2B.9
responsibilities with compact tables and references. Explicitly show the absent
reported-ratio reconciliation rather than filling it with a calculated value.
Carry material CP-2/CP-1A critical gaps and CP-1 source/definition limits.
Name the usable findings and limitations for CP-2D, CP-2G, CP-3C and delivery.
This is an intermediate handoff, not final deliverable completion.

Before closing, check all six headings, definitions, base and instruction hashes,
reference existence, input/output consistency and missingness. Own only these
three attempt-1 files. You are not alone in the workspace; preserve other agents'
work and all earlier files. No provider calls, credentials, new agents or code
changes. Return closed hashes; independent verification follows.
