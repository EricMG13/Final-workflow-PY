# C1 forecast notes (hand-derived from run_expectations.py rules; not executed)

Ordered modules: CP-0, CP-1, CP-4 (registry order; CP-4 requires CP-0, CP-1, edge CP-1 restricted). Declarations: run_type primary, legal_documents draft, USD, valuation.peer_source none, no ratings, no quotes.

Counted items (2):
- cp4-declared-draft-none-recognised (CP-4, check, counted): fires when legal == draft and no file is guessed credit_agreement or indenture with executed False. The lender presentation is at most lender_presentation or information_memorandum, never an agreement kind; the 8-Ks, Ex 2.1 (title ASSET PURCHASE AGREEMENT, no credit-agreement or indenture line start) and the press release are unrecognised. No draft agreement is recognised, so it fires.
- cp4-declared-draft-or-primary-no-executed-agreement (CP-4, limited, counted): legal != none, legal == draft (and run is primary), and no executed agreement recognised (Ex 2.1 is not an agreement kind). Fires. Limited propagates, but CP-4 has no consumer among CP-0, CP-1, CP-4, so no inherited row.

CP-0 and CP-1: no rule fired, forecast Ready.

Checked and NOT triggered:
- cp4-declared-none: legal is draft, not none.
- cp4-declared-executed-none-recognised: legal is draft, not executed.
- cp4-only-amendment: no file is guessed amendment (Ex 2.1 has a line "Amendment and Waiver" in its contents list, which matches neither `amendment no. N` nor `<word> amendment to`).
- cp4-governing-terms-rest-on-final-om: needs secondary or research run type; this is primary.
- run-financials-management-claims and cp1-no-financial-report-recognised: the 10-K and both 10-Qs carry FORM 10-K / FORM 10-Q and ANNUAL/QUARTERLY REPORT PURSUANT on page 1 (3000-character page), so financial_report is present.
- chart-strip-usd, cp2d-non-usd: reporting currency USD (and CP-2D not in the run).
- investment-grade: issue_classification absent from this context.
- cp2-primary-no-cp1d (the Primary CP-2 rule): CP-2 is not in the requested modules, so it never applies; C2 (CP-2 with CP-1D) is a separate case.
- cp1c, cp2h, cp3, cp3d, portfolio-workbook rules: their modules are not in the run.
- Inheritance: none; CP-0 and CP-1 have no propagating outcome.
- without: {} (no declaration-based Will refuse).

Guess dependence (gaps, not values): the exact line structure convert_html gives page 1 was not reproduced; I read stripped HTML with python. The forecast holds for any reading in which the 10-K or either 10-Q is financial_report and no file is guessed credit_agreement or indenture. The presentation's kind (lender_presentation, information_memorandum or unrecognised) does not change any item.

Literals (3): Provisional; 720; 125. Basis: plan row C1 requires terms labelled Provisional and the main limitation naming Provisional. 720 (tlb.size) and 125 (abl.size) are the two stated facility sizes, also in the context's deal_terms. Not included: DRAFT_LIMITATION (verbatim in the CP-4 handoff per the plan, but whether the rendered report carries it is unestablished), the other 22 keyed terms (a run needs only 8 of 24, so none else is certain to appear), TBD (a run could word an unstated margin differently).

Context revision: the context differs from its source by the one added line `"issue_classification": "high_yield"` in identity (the earlier line only gains a comma), because the app form requires the classification; the value is a user entry (index Owner decision 6) for a USD 720m Term Loan B leveraged loan. The presentation states no rating (grep for rating/Moody/S&P finds none); it states "total leverage will be 3.3x" (presentation text line 133, pro forma). The only rule reading issue_classification is investment-grade (== investment_grade); high_yield fires nothing, so the forecast is unchanged.
