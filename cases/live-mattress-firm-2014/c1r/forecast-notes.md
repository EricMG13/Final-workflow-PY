# C1r forecast notes (hand-derived from run_expectations.py rules; not executed)

Ordered modules: CP-0, CP-1, CP-1A, CP-2, CP-4, CP-2D, CP-3C, CP-5. Requested = the covenant_refinancing preset (src/deploy_vii/contracts.py _PRESETS; the app form lists the same) without CP-MODEL. plan(): R1 CP-0; R2 CP-1, CP-1A; R3 CP-2 (needs 0, 1, 1A) and CP-4 (needs 0, 1; optional CP-1D not selected); R4 CP-2D (needs CP-2); R5 CP-3C (needs CP-2D, and optional CP-1A, CP-4 selected); R6 CP-5 (fan-in over all). This equals the A-live order (cases/live-tdg-fy2024/a-live). Declarations: run_type secondary, legal_documents executed, USD, no deal terms, no quotes, no ratings, peer_source none, issue_classification high_yield (Revision 1 line).

Counted items: none. Forecast: CP-0, CP-1, CP-1A, CP-2, CP-4, CP-2D, CP-3C, CP-5 all Ready. modules {}, counted_total 0, without {}, accept_limitations false.

Recognition (current rules, after #59 / R-SB2-2): Exhibits 10.1 and 10.2 page 1 by hand: the title lines are "ABL CREDIT AGREEMENT" and "TERM LOAN CREDIT AGREEMENT". The credit_agreement line rule now allows up to two capitalised qualifiers (_QUALIFIER) before "credit agreement"; "ABL " and "TERM LOAN " are not in the excluded connectives/determiners, so both lines match and each file is credit_agreement. "Execution Version" is a line matching EXECUTION_MARK and no line on page 1 starts with "draft" or contains "subject to completion" or "not for execution", so executed is True for both. Hence executed_agreement is true. The 8-K stays unrecognised: its page 1 (about the first 3,000 characters) has only "The ABL Credit Agreement is ..." (the determiner "The" is excluded as a qualifier, and the pre-existing "the " lead-in is not followed by "credit agreement"); the lines "ABL Credit Agreement dated as of ..." fall far beyond page 1; the file-name fallback strips the date, leaving "8K CREDIT AGREEMENTS", where "8K" cannot be a qualifier (must start with a capital letter), so nothing matches. No other kind phrase matches page 1 of any file.

History: the first frozen forecast (edef5b76) was cp4-declared-executed-none-recognised on CP-4, outcome check, counted_total 1, accept_limitations true. It followed a recognition defect in guess_kind (title rule anchored at line start, no room for "ABL" or "TERM LOAN"; the file-name fallback ran the same anchored rule on a dated name), so neither executed exhibit was recognised although both are executed credit agreements. #59 (lead ruling R-SB2-2) fixed that. Old forecast: CP-4 check (1 counted item). New forecast: no item, CP-4 Ready, counted_total 0, accept_limitations false. Only the recognition changed; no literal changed.

Frozen before any paid run: this key (as revised here) was written before any paid or live run of C1r; the original froze in commit edef5b76 and this revision follows the recognition fix only.

Checked and NOT triggered:
- cp4-declared-draft-none-recognised: legal is executed, not draft.
- cp4-declared-executed-none-recognised: an executed credit agreement is recognised (above), so executed_agreement is true.
- cp4-declared-draft-or-primary-no-executed-agreement: legal is not draft and run_type is secondary, so the clause (draft or primary) is false (and an executed agreement is now recognised).
- cp4-declared-none: legal is executed.
- cp4-only-amendment: no file is guessed amendment (no page-1 line starts "amendment no." or "<word> amendment to").
- cp4-governing-terms-rest-on-final-om: an agreement kind is now recognised, and no file is guessed offering_memorandum or prospectus (no such line start on any page 1).
- run-financials-management-claims and cp1-no-financial-report-recognised: 10-K and both 10-Qs carry FORM 10-K / FORM 10-Q on page 1, so financial_report is present.
- chart-strip-usd, cp2d-non-usd: USD. investment-grade: high_yield.
- cp2-primary-no-cp1d: run is secondary.
- cp1c, cp2h, cp3, cp3d, portfolio-workbook rules: CP-1C, CP-2H, CP-3 (CP-3C is a different id), CP-3D are not in the run; pathway is not portfolio_decision.
- Inheritance: none; no module has an item, so nothing propagates.

Plan row C1r also requires CP-4 "Completed with no draft limitation" and each TBD/indicative C1 term compared with the executed term; those are run outputs, not forecast items. With an executed agreement recognised, the forecast raises no Provisional or draft limitation for CP-4.

Literals (1): 4.25. Basis: the executed Term Loan margin is LIBOR + 4.25% for the first six months and 4.00% to 4.25% by total net leverage thereafter (key c1r_executed_terms tlb.margin; 8-K line 44 "varies from 4.00% to 4.25%"); the plan row requires the margin to be compared with the TBD, so the report states it, and 4.25 is the figure the source writes in every reading. Not included: 4.00 (a run could write the lower step as 4.0% or 4%), TBD (a run could word the unstated margin differently), 720/125 (the plan row does not require the facility sizes in the report), maturity and call dates (could be worded as dates or months), the 12-month soft call (the digits are in everything), and "Provisional" or "DRAFT_LIMITATION" (their absence is the requirement; a substring literal cannot test absence, so the "no draft limitation" check is left to the reviewer).

Context revision: context.json differs from context-after-closing.json by the one added line `"issue_classification": "high_yield"` in identity (the earlier line gains a comma), placed as in c1; only investment-grade reads it and high_yield fires nothing.
