# CP-1A / CP-2C — targeted repair of attempt 1

Continue the original `CP-1A-instructions.md` request. Preserve the first three
output files unchanged:

- Markdown SHA-256: `bed151758ef5664bbd242f22ac830544348d62e6c63eee68dfc54399de256908`.
- Governance inputs: `7fc6417bea9417245c0c442f1b369506ab5609cb5adebac974b36d2a6e466bc9`.
- Calculation transcript: `efdf8e9361e72b7093930e3e172d39c99dd6dba8e383b8257ca2f12e3eea9fe0`.

Write the repaired complete answer and sidecars with `attempt-2` in their names.
Do not change the methodology or scorer to make the answer pass.

## Confirmed repair needs

1. **Quotes must be real evidence.** Only four of eleven governance-input
   citations match their declared source page under whitespace normalization.
   Five excerpts were reconstructed with ellipses/colon insertions: the FY2024
   dividend declaration, both FY2022 equity excerpts, CPI purchase/funding and
   the audit opinion. Two citations name PDF 115 but their verbatim text is on
   114: Raptor purchase/funding, and the generic existing-cash-funding sentence.
   Read the actual pages and replace each with an exact contiguous excerpt at
   its actual one-based PDF page. Use multiple exact quotes when needed; do not
   splice them into one quote. Recheck **all** JSON citations, not just these
   examples. Apply the same rule to quotes in Markdown, including the aftermarket
   passage where `[OEMs]` was substituted into quoted text. Paraphrases are allowed
   only when clearly identified as paraphrases and still tied to source evidence.
2. **Documented dividend funding was omitted.** PDF 131 records the September 19,
   2024 issuance of the 2033 notes and issuance/full draw of Tranche L, then states
   the proceeds of both issuances plus existing cash funded the $75 dividend
   declaration. PDF 29 supplies the declaration date and October cash payment;
   PDF 146 separates the dividend payable and equivalent payment. Read these
   together. Distinguish FY2024 declaration and debt financing from post-year-end
   cash distribution. Retain issuer-disclosed debt plus cash funding instead of
   saying the source is absent. Do not extend that funding statement to the
   November 2023 dividend. Update the transaction summary, timeline, governance
   JSON, capital-allocation mechanics, credit translation and relevant gaps.
   Precise proceeds tracing, legal capacity and forward liquidity remain limited.
3. **Separate fact categories.** The Product/pricing row currently combines
   Documentary Fact and Management Language; the method requires exactly one
   category per fact row. Split as needed. The proprietary-products percentage
   is introduced as an issuer estimate on PDF 4 and must remain qualified.
   Apply the same check to the other business mix, strategy and durability rows.
   Distinguish documented audit/disclosure actions from your interpretation that
   they are supportive. Do not silently convert an issuer characterization into
   independently established pricing power or future acquisition appetite.
4. **Use actual available history.** Add the relevant documented FY2024 financing
   and amendment events from the already-read PDF 127–132, cross-referencing the
   checked CP-1 debt register. Do not claim that all amendment history or source
   of funds is missing when the issuer describes it. Governing agreement terms
   and a complete creditor-treatment assessment remain unreviewed. Read the
   proxy incorporation/deferral passages on PDF 59–61 for the ownership/governance
   gap rather than citing the signature area as ownership evidence.
5. **Match the handoff to its recipient.** CP-3C owns refinancing/LME risk, CP-4
   legal/covenant interpretation, CP-6 investment-committee debate/challenge.
   The current handoffs mostly repeat generic business/liquidity context. Keep
   useful shared facts but state each actual analytical use and its specific
   limitation/evidence action. CP-2 and CP-MODEL remain fundamental-credit and
   publication consumers. Preserve all checked CP-1 values, periods, units and
   meanings. Call financing rows inflows/outflows rather than gross-principal
   figures when the source row is explicitly net proceeds.

## Verification and retained output

All eight governance judgments must remain traceable to the Markdown; update,
split or remove a judgment only if the source comparison justifies it. Do not
preserve a score target. Validate each input with `GovernanceItem` using JSON
validation, verify the exact quotes against their declared PDF pages, then run
the existing `governance_sponsor_score` on the repaired inputs. Record matched
quote counts, input hash, source-function hash and actual returned result in the
new transcript. A computed score or syntactically valid citation is not source
verification. Retain explicitly unscorable dimensions and limitations.

Own only `CP-1A-attempt-2.md`, `CP-1A-attempt-2-governance-inputs.json` and
`CP-1A-attempt-2-calculations.txt` under this run directory. Other agents share the
workspace; preserve their work and upstream artifacts. No product-code edits,
new agents, providers, credentials or unrelated framework work. Do not self-accept
the answer; independent review will follow the closed output.
