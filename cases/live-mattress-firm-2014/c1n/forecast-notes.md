# C1n forecast notes (hand-derived from run_expectations.py rules; not executed)

Ordered modules: CP-0, CP-1, CP-4. Declarations: run_type primary, legal_documents none (context-c1n.json differs from context-pre-closing.json only in that value).

Counted items (1):
- cp4-declared-none (CP-4, will_refuse, counted): legal == none. No inherited rows: CP-4 has no consumer among CP-0, CP-1, CP-4.

without: {"CP-4": ["CP-4"]} (without_for: CP-4 itself; no ordered module requires CP-4).

CP-0, CP-1: Ready.

Checked and NOT triggered:
- cp4-declared-draft-none-recognised, cp4-declared-draft-or-primary-no-executed-agreement (the Primary/draft CP-4 rules), cp4-declared-executed-none-recognised, cp4-only-amendment, cp4-governing-terms-rest-on-final-om: all require legal != none (the last also secondary or research). Primary run type alone does not turn Blocked into Provisional in the forecast; the Provisional paragraph still reaches the CP-4 instruction (manifest note) but the forecast stays Will refuse.
- run-financials-management-claims, cp1-no-financial-report-recognised: three periodic reports are financial_report.
- chart-strip-usd, investment-grade, cp2-primary-no-cp1d (CP-2 absent): not applicable, as in C1.

Literals: empty list. A correct Blocked run may stop before a report is rendered, and its wording (Blocked, No executed governing document) is the module's, not frozen by the key. Nothing else is certain to appear; no value was guessed.

Context revision: the context differs from its source by the one added line `"issue_classification": "high_yield"` in identity (the earlier line only gains a comma), because the app form requires the classification; the value is a user entry (index Owner decision 6) for a USD 720m Term Loan B leveraged loan. The presentation states no rating (grep for rating/Moody/S&P finds none); it states "total leverage will be 3.3x" (presentation text line 133, pro forma). The only rule reading issue_classification is investment-grade (== investment_grade); high_yield fires nothing, so the forecast is unchanged.
