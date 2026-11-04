# CP-1 — targeted repair of attempt 1

Continue the same module under `CP-1-instructions.md`. Preserve attempt 1 and its
calculation transcript unchanged. Its completed handoff SHA-256 is
`38c22ba91b3d55a2a54461317bf09f092af8d84a72abd946e1d44dcb96c88a09`;
the transcript SHA-256 is
`d8dbe3f1d2b33bec52651a05d7e5469016d0414848127e96c8eac76a940ac626`.
Write the full repaired handoff as `CP-1-attempt-2.md`, with a new calculation
transcript `CP-1-attempt-2-calculations.txt`. Read and verify affected source
passages; this is a guided repair, not an independent blind rerun.

Independent source review found the primary statement transcriptions and the
retained principal equations substantially correct. Keep that work. Repair these
confirmed defects and unmet instructions:

1. **Revolver use is misclassified.** T4.18 and G5 infer a funded draw from
   commitment minus availability. PDF 45 explicitly identifies the difference as
   letters of credit outstanding. Read 45 alongside 132. Separate commitments,
   available borrowings, funded drawings and letters of credit; do not turn the
   arithmetic residual into funded debt. Preserve the exact reported maturity
   dates for revolver and notes from 45–46 instead of dropping them to year only.
2. **Opening equity is mislabeled.** The summary row `Opening TD Group deficit`
   uses total stockholders' deficit including noncontrolling interests. Relabel it
   to match the reported total, retaining the correct amounts and the complete
   equity transcription. Make source sign versus positive share-count magnitude
   explicit if a summary differs from the raw equity-column presentation. On the
   balance sheet, distinguish the common-stock carrying balance from par value per
   share and retain authorized share count and par-value terms in the source row.
3. **Available issuer earnings bridges are missing.** Read PDF 52–54. Retain both
   actual reconciliation tables (net income to EBITDA/EBITDA As Defined; operating
   cash to those measures), their comparative columns and applicable definitions
   and footnotes. Distinguish total versus current tax provision, reported
   interest versus interest excluding debt-cost amortization, and the issuer's
   working-capital adjustment. Do not fabricate an FY2022 column in those tables.
   Keep the three-year segment reconciliation on 142. Reconcile all with tools.
4. **The requested operating-expense aggregate is not retained.** The existing
   equations subtract the two expense lines, but never give the calculated
   aggregate for downstream use. Show each annual SG&A + intangible-amortization
   composition, positive expense magnitude and signed negative account form,
   source operands and zero reconciliation residual. This is calculated, not a
   newly reported subtotal. Include the appropriate mapping in T4.15. Do not map
   intangible amortization alone to a total-D&A account even conditionally: keep
   issuer-specific intangible detail and the separately supported total D&A.
5. **Financial interpretation is largely absent.** Provide the financial narrative
   required by the original prompt: operating performance, cash conversion and
   funding changes; explain what the evidence supports and what it cannot establish.
   Use source-backed comparisons and exact tool calculations, with no unsupported
   causal story or credit recommendation. This should be concise analytical prose,
   not another table summary or a claim that downstream analysis already ran.
6. **Traceability/verification is incomplete.** Give unambiguous references for
   every material numerical narrative claim and every calculation operand (table,
   row label and period can serve as a readable row ID; no UUIDs needed). Retain
   short exact source quotations for qualitative definitions and material facility
   terms. Reconcile the full operating/investing/financing line sums, comprehensive
   income and equity roll-forward columns, segment components and debt-maturity
   totals; do not only check headline totals. Include tools' arithmetic results in
   the new transcript. Identify T4.12, T4.13 and T4.19 by cross-reference to Gaps,
   Next module and Calculations rather than creating duplicate tables.

Update Sources, Gaps and consumer readiness only where the actual additional
review changes their scope. No new source file is authorized for this attempt;
use the same S1 PDF. Do not make unrelated changes or build any framework.
Ownership is only the two new attempt-2 output files. Other agents share the
workspace; do not revert or modify their work. No subagents, provider calls,
credential access or product-code changes.
