# CP-8 — prior/current deliverable comparison

Selected authority: the current user's clarification on2026-11-04. CP-8 compares
actual deliverables from prior runs with the latest selected current run.
The imported investment-decision post-mortem is superseded. Its source is
retained as evidence at docs/reuse/legacy-cp8-decision-ledger.md; external dated
investment decisions, later outcomes and a three-decision calibration population
are not prerequisites for this module.

1. Read the actual delivered artifacts and their retained data/handoffs. Identify
   issuer, run, financial dates, requested scope and exact input revisions. Verify
   integrity first. If comparable prior/current outputs are absent, state the gap.
2. Compare their values, definitions, periods, assumptions, conclusions, confidence,
   source support, limitations and delivered output scope. Cover all sections.
   Match by meaning; shifted row numbers and duplicate labels are not identities.
3. Explain each material difference: new-period/source information, analytical or
   methodological development, correction, presentation, unresolved or unmatched.
   Same-period report development is not issuer financial performance. A removed
   limitation is not automatically resolved. Preserve missing-versus-zero and all
   quantity, currency, period and source roles.
4. Identify material regressions, contradictions and open differences. Request
   only the precise repair justified by the comparison. CP-8 does not invent new
   underwriting, change historical outputs or replace the current analytical owner.
5. Write the current six-heading Markdown handoff with a concise prior/current/
   change/effect/evidence register and retained gaps. The responsible module
   actually consumes it; the separate delivery process constructs the corrected
   deliverable. Check the resulting output before declaring the loop passed.

CP-OS owns ordering/resume and invokes CP-8 when the prior and current deliverables
are available. Do not add a competing orchestrator or a new contract engine.
The existing decision-ledger Python owner/schema and its native route remain
legacy implementations; the actual model comparison must not be advertised as
qualification of that different runtime. Adapt that route within CP-OS integration.

Proof case: runs/tdg-run-comparison-001, comparing historical TDG snapshot2 to
snapshot6, with actual CP-2 consumption and targeted snapshot7 restoration.
