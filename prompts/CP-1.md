# CP-1 — targeted instruction amendments

Status: prepared for the next module execution; not connected to the imported
runtime and not tested by a fresh model run. Retain the selected CP-1 analytical
method. These amendments address the observed TDG `80aeb7a0e7` output; they do not
replace its financial definitions or remove substantive checks.

1. **Separate reported facts from calculations.** Preserve every source row's
   label, sign, unit, quantity type, entity, period and locator. Where the requested
   output needs an aggregate that is not printed, identify its definition and
   complete source components, then use a calculation tool. Show the formula,
   component references and result as calculated. Never invent a source-printed
   subtotal or replace missing components with zero.
2. **Reconcile the relevant expense block.** For a by-function income statement,
   distinguish cost of sales from the operating expenses below gross profit.
   Reconcile the complete intervening expense block to operating profit. For TDG
   FY2024 that block is selling/admin plus intangible amortisation; do not replace
   intangible amortisation with total D&A or assume that these two rows define
   another issuer's expense block. Retain unresolved differences explicitly.
3. **Treat instants as instants.** A balance-sheet date has no duration start;
   that is not a missing-date problem. Preserve exact source-supported start/end
   dates for flows. Keep monetary, share-count and per-share quantities distinct.
4. **Judge readiness for the requested use.** Explain which requested conclusions
   and calculations the evidence supports and which remain restricted. Group
   repeated consequences under their underlying issue, keeping the affected
   values, periods, recipients and source references. Do not silently dismiss an
   unknown issue as irrelevant, and do not require unrelated calculations for a
   bounded reported-fact summary. Identity, source-integrity and missing required
   operand problems still restrict every conclusion that depends on them.
5. **Write the Markdown handoff.** Include the reported tables, separately labelled
   calculation bridges, evidence-based interpretation and a short actionable gap
   list. Preserve the earlier method's analytical responsibilities. Internal
   hashes, aliases and schema repair text belong in the execution record. The
   handoff is an intermediate artifact for CP-OS and delivery, not the final report.
