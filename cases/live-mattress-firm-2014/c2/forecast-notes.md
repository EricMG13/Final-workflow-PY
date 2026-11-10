# C2 forecast notes (hand-derived from run_expectations.py rules; not executed)

Ordered modules: CP-0, CP-1, CP-1A, CP-1D, CP-2 (registry plan(): round 1 CP-0; round 2 CP-1 and CP-1A; round 3 CP-1D, because CP-2 lists CP-1D as optional and it is selected, so CP-2 waits for it; round 4 CP-2). CP-2's required CP-0, CP-1, CP-1A are all requested, so plan() adds nothing. Declarations: run_type primary, legal_documents draft, USD, valuation.peer_source none, no ratings, no quotes, issue_classification high_yield. Same 8 documents and same context as C1.

Counted items: none. Forecast: CP-0, CP-1, CP-1A, CP-1D, CP-2 all Ready. modules {} , counted_total 0, without {}, accept_limitations false.

Checked and NOT triggered:
- cp2-primary-no-cp1d (CP-2): run is primary but CP-1D is in the ordered modules, so the condition (primary and CP-1D not ordered) is false.
- run-financials-management-claims and cp1-no-financial-report-recognised: the 10-K and both 10-Qs carry FORM 10-K / FORM 10-Q and ANNUAL/QUARTERLY REPORT PURSUANT on page 1, so financial_report is present (same reading as C1).
- chart-strip-usd, cp2d-non-usd: reporting currency USD (CP-2D not in the run).
- investment-grade: issue_classification is high_yield.
- All cp4-* rules: CP-4 is not in the run, so they never apply (they fire in C1 and C3, which run CP-4).
- cp1c, cp2h, cp3, cp3d, portfolio-workbook rules: their modules are not in the run.
- Inheritance: none; no module has a propagating outcome (will_refuse or limited).

Literals (3): 821; 767; 720. Basis, plan row C2: "Sources and uses and pro forma debt equal the key".
- 821: total uses 440 + 66 + 297 + 18 = 821 foots, so a run showing the Total uses row writes 821 (total sources is stated 821 although 18 + 42 + 720 + 40 = 820; a run may or may not carry that; the Total uses side alone makes 821 certain).
- 767: pro forma total debt (42 + 720 + 1 + 4 = 767, as stated). Certain whichever way a run words the adjustment column.
- 720: new Term Loan, in the S&U row and the pro forma debt row.
Not included: 466 (the stated adjustment does not foot: 42 + 720 - 297 = 465, so a run may write 465); 763 (no required secured-debt row in the Task 11 contract); 194.5 (base EBITDA depends on the run's starting definition: the key's 151.7 + 5.7 + 32.1 + 5.0 = 194.5 holds for Adjusted EBITDA start only; the key lists CP-1's own EBIT-plus-D&A start as a gap); 200/216/233 (which As marketed figure a run quotes is not fixed); 2014-07-29 (the Balance-sheet date line is not a table, and under the lead ruling only tables are routed to the report, so the date may not render); 18 and 42 (too short to prove anything). Each pro forma number is a plain number or `Not supplied: <reason>` per the cell rule; a run that wrote Not supplied for 767 would fail the plan row too.
