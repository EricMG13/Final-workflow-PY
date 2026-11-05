# CP-0 — TransDigm Group Incorporated — source readiness handoff

## Request

Run `sol-fresh-tdg-complete-20261105`; issuer TDG; method ancestry DeployV-r14; module CP-0, attempt 1. Execution date: November 5, 2026. Retrospective annual base: September 30, 2024, with FY2022/FY2023/FY2024 duration comparatives. This is not current underwriting or a timely-availability backtest. Immediate consumer: CP-1 annual primary-statement extraction; also assess annual-base source sufficiency for CP-1A, CP-2 and Model. Selected eventual consumers are CP-4 legal/covenant interpretation and CP-6 committee challenge; neither is executed here.

**Overall: ready with limitations.** Required annual statement text is readable and located. Visual fidelity remains unverified. The executed September 19, 2024 indenture is admitted for its own instrument; it is not a complete facility/intercreditor package. Missing market, portfolio and capacity inputs restrict their specific consumers, not supported annual extraction. CP-0 performs no financial normalization, new financial dataset extraction, calculation, credit conclusion or legal interpretation.

## Sources

### Effective source set and exact identities — P1 / T1–T3

`list_sources` reanchored all supplied hashes below to the current tool inventory. No current upstream handoffs were supplied (`handoffs` is empty); no older handoff or other issuer is used. Hashes are tool-reported pinned identities, not a separate local rehash. One logical annual-report source has two representations, not two independent corroborating documents.

| Source key | SHA256 | Pages | Role / authority |
|---|---|---|---|
| S1-annual-report.pdf | dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af | 160 | Issuer annual Form 10-K PDF; primary annual accounting evidence |
| S1-text-aid.jsonl | 3ef306e99b330ddf535f096a1a507d9a8feadc559101e4b410d061dce67778db | 160 | Fresh pypdf layout text aid from S1; derivative representation, no separate authority |
| legal-text | cb2c0c77e7ec1f90e5a7117a5df7e16cd2556b02e7be7ca43fbf4d64ed585b05 | 37 | Full executed September 19, 2024 6.000% Senior Secured Notes due 2033 indenture, supplied as paginated text; instrument-specific legal evidence |
| CP-4-method | 8a3b12f3f37359463434177759febac1ffcf0f8c484aa0508eb7119f7b6548b2 | 4 | Methodology only |
| CP-4-REF_CP-4_STEPS | ef5eb569be59ec30dd3a66c1bcc81c5cc0bcc2e9d2ac3909b04caa23339b6b94 | 4 | Methodology only |
| CP-3-method | 7e85b2f545fffcb3ad17f4997e5c577ae9620d279f1ffe8e12aefa8ce38abcd1 | 5 | Methodology only |
| CP-3-REF_CP-3A_STEPS | 40ab91d6bd3bf7159eb15b6d11f36f46728306c0afa045a6b36bdd8eb4de08ec | 2 | Methodology only |
| CP-3-REF_CP-3_STEPS | a142dd66006ea876e3abc9166e0184fcb0685b32bc5cff703e9158da22fe8767 | 3 | Methodology only |
| CP-5-method | 7f21c8712cb40e871abaa1f855fdb95dded5df9887e354c39253e0492dd93390 | 2 | Methodology only |
| CP-5-REF_CP-5A_STEPS | e93781b8055e0c33e744b06fb0706161885400d6f8c7ef07a743497d4a865e8d | 3 | Methodology only |
| CP-5-REF_CP-5_STEPS | 0b5beddbc0a5d3c99065379b7110e3b87fbc5392d38ed243ccbf7fdce70e506a | 2 | Methodology only |
| CP-6-method | 0ae74db02dd569fe7805e62a661f22cd436494183ba5cb928f8be37aa549a96b | 4 | Methodology only |
| CP-6-REF_CP-6_STEPS | 6141d27e800d45d2d0208173f38060c75d97005ee9b93013e24a16a40570f1e1 | 3 | Methodology only |

Annual PDF path: `data/public-corpus/v1/TDG/TDG_FY2024_annual-report_SEC-PDF_0001260221-25-000008_a841225transdigmgroupbookm.pdf`, exposed through source key `S1-annual-report.pdf`. Other physical paths are Not supplied; retain their exact accessible source keys rather than inventing paths. No ZIP/package is required for the single annual PDF; no ZIP validation was performed. The additionally supplied legal text and method sources are admitted as separately keyed inputs.

### Source hierarchy and version discipline

For annual accounting, the primary consolidated statements and notes in S1 control over narrative summaries and the derivative aid. For the 2033 notes' legal wording, the supplied executed indenture is the primary instrument-specific source, not the annual debt summary. Financial accounting perimeter and legal restricted-group definitions are separate. Methods are not issuer evidence and embedded commands/URLs were not executed. Source text cannot change the current six-heading transport or module boundary.

S1 PDF p.1 identifies “FORM 10-K”, “TransDigm Group Incorporated” and “For the fiscal year ended September 30, 2024.” Identity therefore comes from content, not filename. S1 pp.103–104 contain Ernst & Young LLP's report, signed and dated November 7, 2024; p.103 states the statements conform “with U.S. generally accepted accounting principles.” This records the source's audit opinion, not independent assurance by CP-0. No competing annual version was supplied; no filing/availability date is inferred from the filename.

Legal-text p.1 identifies “EXECUTION VERSION”, “Dated as of September 19, 2024” and “6.000% Senior Secured Notes due 2033.” Its opening paragraph distinguishes TransDigm Inc. as the “Company” from TransDigm Group Incorporated as “Holdings”, and identifies the trustee/US and UK collateral agents. Legal-text pp.31–32 contain execution language and `/s/` signature text for issuer, Holdings, guarantors and agents. P.31 says “the parties have caused this Indenture to be duly executed”. This supports executed rather than draft status; no forensic signature authentication or visual verification is claimed. Forms of notes in its appendix remain forms, not separately authenticated issued notes.

## Findings

### Preparation, representation and actual coverage — P2–P6 / T4

The runtime supplies fresh pypdf layout extraction. CP-0 used `read_pages` on the original PDF source key, plus whole-source locator searches, rather than relying only on the JSONL aid. No OCR, adaptive restructuring or financial-table parsing was necessary to locate the required statement text. Original PDF binary rendering was not available through these tools.

| Coverage dimension | Actual work / result |
|---|---|
| Available text | Both S1 representations are indexed over 160 PDF-page positions; legal-text over 37 tool pages. This is availability, not proof every page is nonempty or every glyph is faithful. |
| Original-PDF text actually read | S1 PDF pp.1–4, 50–51, 80, 101–116, 122–127, 131–134, 140–143, 146, 153–160. These cover front matter, mid-file narrative/exhibit samples, financial index/audit, every primary statement, policy/EPS/debt/segment notes, subsequent-event disclosures and end matter. |
| Searches across S1 | Primary-statement headings, fiscal-year policy, long-term debt, segments and subsequent-event terms; search excerpts supplement but do not equal full-page review. |
| Aid actually read | S1-text-aid.jsonl pp.105–106; the balance-sheet and income-statement text agrees with the corresponding original-PDF-key extraction. Both derive from the same PDF and are not independent evidence. |
| Legal text actually read | pp.1–3, 31–32, 36–37; searches located restricted payments at p.16 and consent amendments at p.26. Remaining clause text is available but not substantively reviewed by CP-0. |
| Methods actually read | CP-4-method pp.1–4 and CP-6-method pp.1–4 for routing context; other method identities inventoried, not substantively read. None supplies issuer facts. |
| Visual checks | None: visual tools are not supplied. No page image, table alignment, signatures or PDF/text fidelity visually checked. |
| Unreviewed content | All other pages beyond search excerpts; no claim of complete analytical or legal review. |

Extraction exceptions: S1 p.102 explicitly says “[THIS PAGE INTENTIONALLY LEFT BLANK]”; pp.157–158 also carry that label. S1 pp.156, 159–160 returned no text, with their visual content unresolved. These are outside the required statements and do not block CP-1. Dense tables, especially the stockholders' deficit multi-level headers on p.108, require row/column care; spacing collapses and joined words occur in extracted text elsewhere. No unusable required primary-statement page was encountered. No full-file extraction-integrity certification is made.

### Identity, consolidation, periods and units

S1 p.3: “References to ‘fiscal year’ mean the year ending or ended September 30”; FY2024 is expressly “October 1, 2023 to September 30, 2024.” Use annual durations FY2024, FY2023 and FY2022, not calendar years or quarters. S1 p.3 includes wholly-owned and majority-owned subsidiaries with controlling interests. Note 1, p.110, says statements “include the accounts of TD Group and subsidiaries” and “Intercompany balances and transactions have been eliminated.” Preserve noncontrolling-interest lines; do not relabel these as issuer-only or restricted-group statements. Note 1 also says prior-year presentation reclassifications were made, “none of which are material”; extract the comparative columns as presented in this supplied report.

The balance sheet covers **instants September 30, 2024 and September 30, 2023**. Income, comprehensive income, stockholders' deficit changes and cash flows cover **annual durations ended September 30, 2024, 2023 and 2022**. The equity rollforward also has an opening September 30, 2021 balance; that is not an additional annual income-statement period. A September 30, 2022 balance sheet is not supplied among the primary balance sheets.

Unit evidence: p.105 says “Amounts in millions, except share amounts”; p.106 says “Amounts in millions, except per share amounts”; pp.107 and 109 say “Amounts in millions”; p.108 says “Amounts in millions, except share amounts.” Money is U.S. dollars: statements use dollar signs, and Note 1 p.114 expressly describes translation into “U.S. dollars”. Do not scale raw shares on pp.105/108 as money. Preserve dollar-per-share EPS/dividend data on p.106; weighted-average share quantities there are in millions, explained by Note 4 p.122, “in millions, except per share data”. Distinguish weighted-average common shares from total shares including participating vested options under the two-class method. Source dashes and parentheses must be retained until CP-1 explicitly interprets their presentation; missing quantities are not invented zeros.

### Master Index — P6 / T4 and T7

All S1 locators below are one-based **PDF pages**, not printed page numbers. Required pages were opened directly; the table records the printed labels to avoid confusing the main table of contents with physical page offsets. Accessible links use the supplied source key.

| Consumer / content | Source page link | Printed locator / use |
|---|---|---|
| CP-1 financial index | [S1 p.101](S1-annual-report.pdf#page=101) | Printed 99; index for Item 8 / Item 15 financials |
| CP-1 audit report | [S1 pp.103–104](S1-annual-report.pdf#page=103) | F-1–F-2; opinion, scope, signature/date |
| CP-1 balance sheets | [S1 p.105](S1-annual-report.pdf#page=105) | F-3; 2024/2023 instants; money versus raw shares |
| CP-1 income statements | [S1 p.106](S1-annual-report.pdf#page=106) | F-4; FY2024/FY2023/FY2022; per-share exceptions |
| CP-1 comprehensive income | [S1 p.107](S1-annual-report.pdf#page=107) | F-5; three annual duration columns |
| CP-1 stockholders' deficit changes | [S1 p.108](S1-annual-report.pdf#page=108) | F-6; three annual rollforwards, raw-share columns |
| CP-1 cash flows | [S1 p.109](S1-annual-report.pdf#page=109) | F-7; three annual columns and supplemental disclosures |
| CP-1 period / entity policy | [S1 p.3](S1-annual-report.pdf#page=3), [pp.110–114](S1-annual-report.pdf#page=110) | Printed 1 and F-8–F-12; FY definition, consolidation, GAAP, translation, EPS policy |
| CP-1 explanatory-note set | [S1 pp.110–153](S1-annual-report.pdf#page=110) | F-8–F-51, per index p.101; not all read by CP-0 |
| CP-1 EPS and receivables | [S1 p.122](S1-annual-report.pdf#page=122) | F-20; Notes 4–5; participating securities and unit clarification |
| CP-1 balance-sheet explanations | [S1 pp.123–127](S1-annual-report.pdf#page=123) | F-21–F-25; Notes 6–10, inventory, PP&E, intangibles, accruals and comparative debt gross/net presentations |
| CP-1 / CP-2 debt and maturity context | [S1 pp.126–133](S1-annual-report.pdf#page=126) | Note 10, F-24–F-31; read any unexamined pages before use; no capacity conclusion here |
| CP-1A business and acquisitions | [S1 p.4](S1-annual-report.pdf#page=4), [pp.114–116](S1-annual-report.pdf#page=114) | Business introduction and Note 2 opening; remaining acquisition-note pages require consumer review |
| CP-1A / CP-2 segments and reported non-GAAP bridge | [S1 pp.140–143](S1-annual-report.pdf#page=140) | Note 15, F-38–F-41; keep EBITDA As Defined separate from GAAP and covenant definitions |
| CP-1 / CP-2 dated subsequent events | [S1 p.131](S1-annual-report.pdf#page=131), [p.146](S1-annual-report.pdf#page=146) | F-29 / F-44; October 2024 securitization draw and dividend payments, outside base period |
| CP-1 supplementary schedule | [S1 p.154](S1-annual-report.pdf#page=154) | F-52; valuation/qualifying accounts, not another primary statement |
| CP-4 legal document identity | legal-text p.1, opening paragraph / execution cover | September 19, 2024 indenture; 2033 secured notes; tool pages are not original legal PDF pages |
| CP-4 legal navigation | legal-text p.1 contents; p.16 §4.07; p.26 §9.02; pp.31–32 signatures; pp.32–37 appendix/forms | Contents supplies original internal section/page references; CP-4 must read operative clauses and cross-referenced definitions, not rely on contents or forms |

S1 p.141 warns: “EBITDA As Defined is not a measurement of financial performance under U.S. GAAP.” Its reported bridge is available for later extraction, not proof of a legal EBITDA definition. S1 p.131 and legal-text p.32 differ in purchase-agreement date references: the annual narrative describes entering a purchase agreement on September 19, whereas the indenture appendix defines the initial Purchase Agreement as dated September 5, 2024 (L2482). Preserve both roles/dates for CP-1A/CP-4; do not silently rewrite either. The indenture date and Issue Date are September 19 in the legal text; no issuer identity or annual-period ambiguity results.

### Consumer readiness — T5–T6

| Analytical lane | Source sufficiency status | Permitted scope and boundary |
|---|---|---|
| CP-1 annual statements | Ready with limitations | All required statements and comparative columns readable; inherit visual-fidelity and extraction cautions. No quarterly model. |
| CP-1A annual business / historical transactions | Ready with limitations | Annual business, segments, acquisitions and financing/distribution disclosures available. Read full relevant sections before fact-pack completion. No new deal brief is supplied. |
| CP-2 annual fundamental synthesis | Ready with limitations for annual source foundation | S1 supports an annual evidence base after canonical CP-1 extraction; CP-2 itself is not executed or certified. Current liquidity, forecasts, ratings and current-market conclusions need additional inputs. |
| Model | Ready with limitations — source sufficiency only | Annual financial display can be sourced after downstream extraction/validation. No Model/report/charts/calculation JSON generated here and no completed delivery claim. |
| CP-4 legal | Ready with limitations for 2033 indenture reading | Full executed indenture is supplied, not missing; operative interpretation belongs to CP-4 after required financial handoff. Other facilities, intercreditor/security documents and capacity-use evidence are not supplied as standalone operative sources. No whole-package opinion or exact capacity certification. |
| CP-3 / CP-3D market and security selection | Blocked for priced conclusions | Current/historical-as-of pricing runs, spreads/yields and peer-market evidence Not supplied. Annual accounting and indenture do not establish cheapness. |
| CP-3C refinancing | Ready with limitations for historical documentary context only | Annual debt history and maturities available; no live refinancing execution, market access or current facility-status conclusion. |
| CP-6 committee / portfolio decision | Blocked for decision-ready completion at this gate | Completed current analytical handoffs and market/portfolio inputs Not supplied. Annual extraction may proceed; no committee clearance, mandate compliance or sizing inferred. |

## Calculations

Not applicable to CP-0

## Gaps

### Issues ledger — P7 / T5

| Gap ID | Limitation / missing evidence | Affected work | Action / gating consequence |
|---|---|---|---|
| G01 | No visual tools; original PDF visual fidelity unverified | CP-1 table alignment, signs, raw-share headers; legal signature appearance | Retain text-only qualification; visually reconcile if rendering becomes available. Does not block readable annual extraction. |
| G02 | Empty extracted S1 pp.156, 159–160; no full-file glyph-integrity review | End matter and any future claim of complete extraction fidelity | Inspect original rendered pages if end matter becomes relevant; do not characterize empty text as verified blank images. Required financial pages are usable. |
| G03 | Annual notes and narrative not fully read; dense multi-level tables need careful assignment | CP-1 notes, CP-1A business/deals, CP-2 synthesis | Consumers read their required pages, including unexamined Note 2/10 continuations, with page-level evidence. Do not inherit a complete analytical-review claim. |
| G04 | No December quarter or other quarterly case supplied; primary 2022 balance sheet absent | Quarterly/LTM modelling or three-year balance-sheet panel | Request only if that work is selected; extract supplied 2024/2023 instants and three annual duration columns now. |
| G05 | Other controlling credit-facility amendments, operative ICA/security documents, certificates, basket elections/usage and current restricted-group evidence Not supplied | CP-4 whole-package interpretation, perfection, intercreditor control and numerical capacity | Read supplied full 2033 indenture first; identify exact cross-reference/input requests. Do not treat indenture references as standalone ICA evidence or use accounting EBITDA as legal capacity. |
| G06 | Market quotes, peers, rating updates and live facility status Not supplied | CP-3/CP-3D, CP-3C live refinancing, CP-6 priced decision | Obtain dated instrument-specific inputs for the intended measurement date; no current-market or complete-pathway conclusion. |
| G07 | Forecasts, stress assumptions, cash accessibility and forward funding inputs Not supplied | CP-2A/CP-2D/CP-2G, recovery and forward liquidity work | Request targeted evidence if selected. Missing is not zero, adverse evidence or proof cash is accessible. |
| G08 | Portfolio vehicle, mandate, holdings, constraints and investment clearance Not supplied | CP-6 portfolio implementation and sizing | Obtain matching dated portfolio inputs; no compliance breach, constraint headroom or investment clearance inferred. |
| G09 | No accepted CP-1/CP-2/CP-3 or other downstream handoffs yet | Dependent analysis and committee execution | Produce and host-review one module at a time; these are unexecuted modules, not missing annual source blockers. |
| G10 | Purchase-agreement date wording differs between annual narrative and indenture appendix | CP-1A transaction chronology / CP-4 date-specific references | Preserve September 19 narrative and September 5 defined agreement date with separate citations; seek agreement if resolving execution chronology is material. |

## Next module

### Ordered consumer commands and inherited limitations — P8 / T8

1. **After host evidence review, run CP-1** using the exact S1 PDF path in Sources / source key `S1-annual-report.pdf` and pinned hash. Read p.3, pp.101 and 103–114, then p.122 and relevant explanatory notes via the Master Index. Extract the five primary statements on PDF pp.105–109 with their supplied comparative columns. Preserve FY2024/FY2023/FY2022 durations, 2024/2023 balance-sheet instants, U.S. dollar millions, raw-share exceptions and per-share data. Read no more than eight pages per tool request. Retain exact page references, dashes, signs, NCI and GAAP versus non-GAAP labels. Do not invent a 2022 balance sheet or December quarter. Keep October 2024 subsequent events separately dated, not blended into September 30 balances or FY cash flows.
2. **Then CP-1A and CP-2, as selected by the existing workflow**, consume the accepted CP-1 handoff plus annual business/acquisition/debt/segment content. Their source foundation is ready with limitations, not their unperformed analyses. Broader gaps remain targeted to their affected outputs.
3. **CP-4 uses the full supplied `legal-text` indenture** under its exact pinned hash and the accepted financial handoff. Read all operative relevant definitions, clauses and cross-references, using tool page plus section/line locators. Its text-page pagination must not be presented as original-PDF pagination. Review gaps G05 and G10; legal text already supplied must not be requested again as if absent. Accounting definitions remain distinct from legal definitions.
4. **CP-6 remains a later committee consumer**, not the next executable source-extraction step. Consume accepted analytical handoffs when present, retain absent market/portfolio/forecast/capacity limitations and do not manufacture a complete-pathway claim. CP-3C owns refinancing, CP-4 legal and CP-6 committee roles; historical imported labels do not redefine those roles.

This Markdown is the intermediate CP-0 handoff for automated checks followed by host source/instruction review. P1 inventory/identity, P2 triage, P3 execution (source-tool reads), P4 quality, P5 active representation, P6 locators, P7 issues and P8 package status are recorded above; T1 input gate, T2 effective set, T3 hierarchy, T4 mapping, T5 gaps, T6 evidence/readiness, T7 Master Index and T8 ordered commands are likewise explicit. No source reattachment is necessary: the next consumer can read the pinned keys and mapped pages directly. Existing report/Model/charts/calculation-JSON delivery is unchanged; CP-0 neither regenerates analysis for delivery nor claims that those deliverables or the complete pathway have been completed.