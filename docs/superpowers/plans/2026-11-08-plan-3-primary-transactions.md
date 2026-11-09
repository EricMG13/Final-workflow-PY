# Plan 3: Primary Transactions

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

**Goal:** Primary (new-issue) runs become useful before closing: CP-4 reviews draft and offering
documents as Provisional, and pro forma leverage keeps unrealised add-backs out of the base.

**Architecture:** Primary method changes are launcher instructions plus fixed handoff tables, checked
in each module's own repair loop, one module at a time against its actual output (`AGENTS.md`). The
selected method files are not edited, and each correction is recorded in `METHODOLOGY-REVIEW.md`.

**Tech Stack:** Python 3.13 (stdlib, pydantic).

**Delivery:** one PR. It merges only after C3 passes; without the live checks it is reported as
"instructions only, unproven" and does not merge.

**Depends on:** Plan 2, which passes the run type and the legal-documents declaration from `prepare`
into `_instructions`.

**Shared rules:** the index, [`2026-11-08-run-expectations.md`](2026-11-08-run-expectations.md), holds the owner decisions, global constraints, the live-check method, the required outputs and the review record. They apply here unchanged. Review Focus numbers and task numbers are kept from the combined plan, so cross-references still resolve.

## Facts this plan builds on (verified 2026-11-08)

| Finding | Decision |
|---|---|
| `Run` has no run type (`contracts.py:83-96`); `_instructions` and `checker` see only `Run` and the layout | Pass the run type and legal-documents declaration from `prepare` into `_instructions`. Primary-only checks follow from Primary-only layout routes, which `checker` already receives. `Run` is unchanged |
| No general per-module instruction mechanism exists beyond `OPENING`, `READER_STANDARD_MODULES` and route selectors. Chart routes accept only S.1–S.4 and RV.1 in x, US$m or % (`handoff_delivery.py:108-142`) | Add a per-module instruction mapping in the same style. New fixed tables get their own route and checker, copying the `chart_issues` pattern (plain numbers or `Not supplied:`) |

### Primary transactions

- **CP-4 Provisional scope:** Primary runs, or a declared `draft`. Elsewhere the method's Blocked
  message ("supply the executed document") stands.
- **Final offering memorandum:** after closing it is a summary, not the governing document. It gets
  its own reason, never "terms may change before signing".
- **Authority ranks** follow `REF_CP-4_STEPS.md:340-345`:
  1. Executed agreement or indenture.
  2. Intercreditor agreement.
  3. Compliance certificates.
  4. Offering memorandum.
  5. Covenant-review report.
  6. Lender presentation, term sheet or commitment letter.

  All are document kinds.
- **The Provisional label travels:**
  - Every CP-4 section routed to the report says "Provisional", and so does the Reader summary's main
    limitation.
  - In Provisional scope (Primary, or declared draft), CP-3, CP-5 and CP-6 label any term taken from
    a Provisional CP-4 handoff as Provisional.
- **CP-1D:** Primary runs add it to the default modules. The review shows the extra module, and the
  user can remove it. CP-4 is told not to use CP-1D figures as covenant capacity (CP-1D's own rule).
- **Pro forma, by module and by dependency:**
  - CP-1A records **Sources and uses** as documented.
  - CP-2, which requires CP-0, CP-1 and CP-1A, writes **Pro forma capitalisation** from CP-1's debt
    register plus CP-1A's changes.
  - CP-2 also writes the **EBITDA ladder** and **Pro forma leverage**.
  - CP-1D supplies each add-back's verdict and the amount already in the LTM.
- **EBITDA ladder, written before any code:**
  - (a) Starting EBITDA: CP-1's cited figure, with its definition named (EBIT plus D&A, or the
    issuer's adjusted or "As Defined" figure).
  - (b) Documented acquisition or disposal pro forma adjustments, cited.
  - (c) Unrealised run-rate savings: run-rate claimed minus the amount already in the LTM, per CP-1D.
  - (d) Other management add-backs, by CP-1D verdict (Supported, Challenged, Rejected, Insufficient
    Information).
  - (e) The difference from management's quoted figure: a `calculate` result plus its explanation,
    or `Insufficient Information`.

  The base is (a)+(b). **As marketed** is management's figure as quoted. Nothing is plugged, and no
  haircut is invented.
- **Pro forma capitalisation:**
  - One balance-sheet date and one LTM period, both stated.
  - An explicit cash row: cash to balance sheet, fees and OID per sources and uses.
  - A column per currency; totals only with an FX rate cited from the documents.
  - The user's entered facility size is used and labelled. A different documented size is shown
    beside it and the difference logged, not resolved.
- **Report:** both pro forma tables get table routes on Primary runs through the existing dense-table
  renderer. They are not placed under the dated capital-structure block.

**Rejected:**
- One blended pro forma figure, an equality check forcing management's figure, or Python arithmetic
  on model-written numbers.

## Validation

| When | Command or action | Passes when |
|---|---|---|
| **Checkpoint C** (Tasks 9-11, one module at a time) | **Live: C1** and control C1n after Task 10; **C2** after Task 11; then the pathway runs **C1r** and **C3** | Live pass criteria and required outputs below. Without them, this plan is reported as "instructions only, unproven" and does not merge |

Rewrite-tournament targets: the CP-4 register check and the pro forma table checks.

## Live checks

| Check | Pathway and case | Cap (USD) | Passes when (besides required outputs) |
|---|---|---|---|
| **C1** CP-4 Provisional gate (C) | Mattress Firm pre-closing (Task 9); CP-0, CP-1, CP-4 | 10 | CP-4 does not stop at the gate; the register lists each document with status and authority rank; `DRAFT_LIMITATION` appears verbatim; at least 8 keyed terms match the key, each labelled Provisional; no document is called executed; the main limitation names Provisional |
| **C1n** control (C) | The same case without its lender presentation; CP-0, CP-1, CP-4 | 10 | Blocked, as forecast |
| **C2** pro forma gate (C) | Mattress Firm pre-closing; CP-0, CP-1, CP-1A, CP-1D, CP-2 | 15 | Sources and uses and pro forma debt equal the key; cash row, one balance-sheet date and one LTM period; base EBITDA equals the key with no double count; As marketed equals management's quoted figure, any difference explained, never plugged; CP-2's pro forma debt cites CP-1A's total |
| **C1r** after-closing control (C) | **Covenant & Refinancing** on Mattress Firm after closing: the executed Term Loan and ABL Credit Agreements, Secondary, "older source". Fallback: retained TDG executed notes (`runs/tdg-004`, read-only) | 30 | CP-4 Completed with no draft limitation; each C1 term marked TBD or indicative is compared with the executed term (e.g. margin "TBD" against LIBOR + 4.00-4.25%) |
| **C3** Primary through the app (C) | **Credit Snapshot plus CP-1D** on Mattress Firm pre-closing, Primary, through the app UI | 30 | The report shows both pro forma tables or an explicit gap; every report section drawing on CP-4 says Provisional; CP-6 never treats a draft term as executed; CP-5 flags claims that depend on drafts |

Caps total USD 95.

## Review Focus

12. **CP-4 register without the limitation:** a register lists a draft, term sheet or lender
    presentation and the answer lacks `DRAFT_LIMITATION`: repair requested (Task 10).
13. **Final offering memorandum on a Secondary run:** reason "summary, not the governing document";
    no "may change before signing" (Task 10).
14. **Pro forma ladder:** run-rate claimed 50, 20 already in the LTM, a Rejected add-back of 10, an
    acquired EBITDA of 40: base = (a) + 40; unrealised 30 shown; Rejected 10 shown; management's
    figure quoted; difference explained; nothing plugged (Task 11).
15. **Private deal, no filings:** the Reported row is `Not supplied: no filed financial statements`;
    the module is accepted, not looped to max turns (Task 11).
16. **Bases never blend:** a ladder row missing its source or definition, or a pro forma debt not citing
    CP-1A, is sent back for repair (Task 11).

---

## Tasks: one module at a time

### Task 9: Public proxy case

**Files:** create `cases/primary-proxy-<issuer>-<date>/` (sources, context, frozen key); add a dated
entry to `VERIFICATION.md`.

- [ ] **Confirm the case with the owner.** Recommended (screened 2026-11-08 from EDGAR): Mattress
      Firm Holding Corp. (CIK 1419852), an acquisition financing.
  - **Pre-closing:** the Public Lender Presentation of 11 September 2014 (8-K Item 7.01, Exhibit
    99.1, accession 0001104659-14-065798). It holds:
    - sources and uses of USD 821m, including Sleep Train at USD 440m and bolt-ons at USD 66m;
    - pro forma capitalisation from 1.9x to 3.5x total debt / Adjusted EBITDA;
    - acquired EBITDA (USD 32m and USD 5m), USD 17m of synergies (USD 12.5m of USD 20m expected
      within 18 months) and a USD 17m new-store adjustment;
    - a Pro Forma EBITDA reconciliation;
    - summary terms for a USD 720m Term Loan B: 7 years, margin and OID "TBD", 1.00% LIBOR floor,
      101 soft call for 6 months, 1% amortisation, excess-cash-flow sweep with step-downs, no
      financial covenants, USD 250m incremental plus unlimited at 4.0x secured net leverage, and
      50 bps MFN with an 18-month sunset.
  - **Financial base:** 10-K for the year ended 28 January 2014 (0001047469-14-003037); 10-Qs for
    29 April 2014 (0001104659-14-044836) and 29 July 2014 (0001558370-14-000163), the presentation's
    LTM basis.
  - **Context support:** Back to Bed asset purchase 8-K of 29 August 2014 (0001104659-14-064027;
    Item 1.01, the bolt-on Asset Purchase Agreement, not the Sleep Train merger agreement, which is
    not in the case; the lender presentation carries sources and uses and acquired EBITDA).
  - **After closing, for C1r:** 8-K of 21 October 2014 (0001104659-14-072654). Exhibit 10.1 is the
    ABL Credit Agreement and Exhibit 10.2 the Term Loan Credit Agreement, both dated 20 October
    2014; margin LIBOR + 4.00–4.25%, maturity 20 October 2021.

  The Confidential Information Memorandum and Marketing Term Sheet that the presentation refers to
  are not public, and the case says so.

  **Second case, without an acquisition (optional):** Everi Holdings' 2017 refinancing lender
  presentation (0001558370-17-002593), not yet screened in detail.
- [ ] Label the case "public proxy for a private primary deal", with issuer, date and "older source"
      where relevant.
- [ ] Hand-write the key before any run:
  - document kinds and expected outcomes;
  - sources and uses and pro forma debt as documented;
  - the EBITDA ladder inputs;
  - at least 8 covenant terms;
  - each add-back's claimed, realised and in-LTM amounts as the documents state them.

### Task 10: CP-4 Provisional review (then C1 and C1n)

**Files:** modify `src/deploy_workflow/owners/cpos_launch.py`, `tests/test_cpos_launch.py`,
`METHODOLOGY-REVIEW.md`.

- [ ] **Instruction text, in Provisional scope only:**
  - CP-4 gets an override paragraph placed with the transport overrides, before the method.
  - It requires a fixed `### Legal document register` (Document, Kind, Status, Authority rank,
    Source), Provisional confidence, `DRAFT_LIMITATION` verbatim, and "Provisional" in every
    routed section and in the main limitation.
  - It never calls a draft executed, and never uses CP-1D figures as capacity.
  - With no legal document at all, the Blocked message stands.
- [ ] **In Provisional scope (Primary, or declared draft; coordinator ruling 2026-11-08),** CP-3, CP-5
      and CP-6 are told to label terms taken from a Provisional CP-4 handoff as Provisional.
- [ ] **Checkers:**
  - The register is present in Provisional scope.
  - Any non-executed status, or no executed document recognised with any legal or offering document
    pinned, requires `DRAFT_LIMITATION` and "Provisional" in routed sections.
  - A consumer receiving a Provisional CP-4 handoff must say "Provisional".
- [ ] **`METHODOLOGY-REVIEW.md`:** record the source (the Deploy VII owner path's draft admission),
      the reason, and this repository's revision.
- [ ] **Tests:**
  - Review Focus 12-13.
  - An executed-only answer needs no limitation.
  - A Blocked answer with no legal documents passes.
  - Non-Primary runs without a draft declaration are unchanged.
- [ ] **Live:** C1, then control C1n.

### Task 11: Pro forma capitalisation and leverage (then C2)

**Files:** modify `src/deploy_workflow/owners/cpos_launch.py`, `src/deploy_workflow/handoff_delivery.py`
(table routes), `tests/test_cpos_launch.py`, `METHODOLOGY-REVIEW.md`.

- [ ] **Method source:** Deploy V r14's CP-1 pro forma reference if the owner supplies it; otherwise
      this instruction. Record either, with its revision.
- [ ] **Modules:** Primary default modules add CP-1D. An explicit module list is taken as given. The
      review names any absence (Task 3 rule).
- [ ] **Tables:**
  - CP-1A writes `Sources and uses` (as documented; user-entered sizes labelled; differences
    logged).
  - CP-1D's register adds `Amount already in LTM`.
  - CP-2 writes `Pro forma capitalisation`, `EBITDA ladder` and `Pro forma leverage` (Reported;
    Pro forma, excluding unrealised add-backs; As marketed), as designed in Decisions, using
    `calculate`.
- [ ] **Checkers:** structural only.
  - Fixed headers and rows in order.
  - Each cell a plain number or `Not supplied: <reason>`.
  - Citations present; definitions named.
  - CP-2's pro forma debt cites CP-1A's total.
  - A difference line is present.
  - No Python arithmetic on model numbers.
- [ ] **Delivery:** table routes for both pro forma tables on Primary runs, through the dense-table
      renderer; a delivery test from an actual handoff.
- [ ] **Tests:** Review Focus 14-16; non-Primary runs need none of the tables.
- [ ] **Live:** C2. Once Tasks 10 and 11 have both passed their gates, run the pathway checks **C1r**
      (Covenant & Refinancing, after closing) and **C3** (Credit Snapshot plus CP-1D, Primary, through
      the app). This plan merges only after both pass.

## Done when

**Primary runs:**
  - CP-4 reviews drafts and offering documents as Provisional, and the label reaches CP-3, CP-5,
    CP-6 and the report.
  - CP-2 reports the pro forma capitalisation, EBITDA ladder and leverage on three bases, with
    unrealised and unresolved add-backs shown and never counted.
  - C1, C1n, C1r, C2 and C3 have passed, with every required output, recorded with their actual
    scope.
