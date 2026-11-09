# Plan 2: Run Expectations and Acceptance

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

**Goal:** Before Start, tell the user what each module is expected to produce from the files and the
context they supplied, why, and what would improve it, and require them to accept the listed
limitations, so fewer runs are repeated. The user states the issue classification and the facility
terms in the context.

**Architecture:** One offline rule set in Python, inside the CP-OS launcher's existing review.
Expected outcomes come first from what the user **declared** in the context (legal documents,
management bridge, portfolio workbook, prior case, quotes, ratings, facility terms). A conservative
document-kind guess from each file's name and first pages only adds a `Check` when nothing supports a
declaration. The bridge returns the expectations; the app shows them first on the Review step. Start
requires a separate acceptance of the counted items, which is recorded in the run folder before any
provider call. No new orchestration layer and no model call before Start.

**Tech Stack:** Python 3.13 (stdlib, pydantic), Go, plain browser JavaScript; jsdom test-only.

**Delivery:** two PRs: Stage 1 (Tasks 1-5, Checkpoint A) and Stage 2 (Tasks 6-8, Checkpoint B).

**Shared rules:** the index, [`2026-11-08-run-expectations.md`](2026-11-08-run-expectations.md), holds the owner decisions, global constraints, the live-check method, the required outputs and the review record. They apply here unchanged. Review Focus numbers and task numbers are kept from the combined plan, so cross-references still resolve.

## Facts this plan builds on (verified 2026-11-08)

| Finding | Decision |
|---|---|
| No offline code classifies documents. `_issuer_files` skips hidden, `_` and `~$` files, then parses every file and refuses unreadable or textless ones (`cpos_launch.py:299-346`). `_pages` already yields per-page text: PDF pages, xlsx sheets, 12,000-character chunks for text and CSV, and 3,000-character rows for HTML. HTML page 1 begins "Visible text of `<file name>`" | Keep `pages[:3]` for the guess at no extra cost. The guess skips that HTML header line, so a file name is never read as cover text |
| The context already declares `attachments.legal_documents` (executed, draft or none; the form preselects executed), and booleans for `management_bridge`, `portfolio_workbook` and `prior_case` (`context.py:238-243`). The launcher never reads them; modules see them only inside the context file | The declarations drive the expected outcomes. The guess adds a `Check` only when a declaration has no supporting file. The legal-documents choice loses its preselected default |
| App runs send every file to every module (`owners/cpos.py:404`) and the whole context as source `context`. The review already lists ignored files and omitted sections (`bridge.py:283-285`) | Expectations inform; they never block a run or filter sources |
| Several outcomes cited in the first draft come from owner-path code that app runs never execute: `cp2h.py` "Rating register not found", `cp3_relative_value.py` (imported only by the owner path), `cp3d.py` and `cp1d.py`. On app runs each module is a model reading `instructions/<module>.md`, checked by `cpos_launch.checker` | Every rule is derived from the instruction text a module is actually sent, plus the launcher checker. A rule taken from owner code is labelled as such. Rules are labelled **per method**, **observed offline** or **observed live** |
| Only 4 retained runs are launcher runs with a context: `cpos-launch-live-001`, `cpos-launch-live-002`, `cpos-launch-cp2-reader-001` and `web-04cd…`. All are TDG as of 2024-09-30, Credit Snapshot, with at most CP-0, CP-1, CP-1A and CP-2. The other 17 runs with `workflow.json` are host or replay campaigns without a context | The back-test reports its true sample. It adds contexts reconstructed for campaign cases with real outcomes, labelled "reconstructed context": LMI intercreditor, ARCC executed indenture, TDG executed notes and Ford ratings. Live checks carry the proof |
| `READER_PERSONA` ("specialising in high yield credit and leveraged loans", `cpos_launch.py:214-223`) goes to every module; the methods sent are leveraged-finance framed; none mentions investment grade. The context file, which will include the classification, reaches every module | Investment grade gives one **information** item for the whole run ("methods and persona are written for high-yield and leveraged-loan credit"), not counted as a limitation. Whether the classification changes conclusions is tested live (A-ab), not asserted |
| The launcher omits `what-changed` in every pathway except Covenant & Refinancing (computed from `_layout`) | Structural omissions are information, not counted limitations, so acceptance does not fire on every run |
| `Run` has no run type (`contracts.py:83-96`); `_instructions` and `checker` see only `Run` and the layout | Pass the run type and legal-documents declaration from `prepare` into `_instructions`. Primary-only checks follow from Primary-only layout routes, which `checker` already receives. `Run` is unchanged |
| `review_id` already covers the context bytes, the job and every engine source file | Expectations are not added to `review_id` |
| 78 files in `cases/` carry `schema: context/1`, 35 of them named `context*.json`; `Contract` forbids unknown keys and requires declared ones; `_omit_absent_cutoff` (`context.py:82-89`) shows how an optional field keeps older files byte-identical | New fields are optional in the reader and omitted from the dump when empty, so fixtures, pins and goldens stay byte-identical. A file that uses a new field needs this version or later; the README says so |

### Outcome semantics

| Outcome | Given only when | Counted for acceptance |
|---|---|---|
| `Will refuse` | A declaration, context fact or structure says the module cannot run (e.g. legal documents declared `none` with CP-4 requested) | Yes |
| `Gap` | A context fact or declaration says an input is absent (e.g. no quotes or talk in the context and no quotes file recognised) | Yes |
| `Limited` | A context fact or declaration narrows the module (talk only, non-USD, Provisional legal review) | Yes |
| `Check` | Evidence is only a guess: a declaration has no supporting file, a document's status is unknown, or no file was recognised as needed | Yes, as "check before you start" |
| Information | Structural omissions, investment-grade method fit, inherited rows | No |
| `Ready` | Nothing above applies | No |

- **Inheritance:** a consumer inherits the milder of its producer's outcome and the edge's rule:
  block → `Will refuse`; restrict → `Limited`. Inherited rows are grouped under their producer and
  shown as information. `Check` never propagates.
- **"Run without <module>":** offered only for declaration-based `Will refuse`. It removes the
  module and, transitively, everything that requires it.
- **Wording rule:** every expectation reads as a forecast: "Expected from your declarations, files and
  context; CP-0 confirms during the run; the model may still find less." A guessed kind reads
  "Likely: credit agreement (found 'CREDIT AGREEMENT' on page 1)", never as fact. User-entered
  values are labelled "entered by user".

**Rejected:**
- Blocking Start for a missing file.
- A model call to classify files.
- A second checker beside CP-OS.
- A new schema version, or a required reader field.
- Inferring the classification from ratings.
- Checking user entries against each other or against the filings.
- Parsing documents or handoffs for values the user supplies.
- An expected-rating status.
- A reader refusal of talk on non-Primary runs. The form blanks hidden talk fields instead.
- Deleting the form's capability panel. Its rules and Python's now share the same declarations, so a
  parity test is well posed.

## Validation

| When | Command or action | Passes when |
|---|---|---|
| **Checkpoint A** (after Task 5) | Offline: back-test report. **Live: A-live** (and A-ab if the owner wants it) | Every disagreement explained or its rule fixed; the meaning of `Will refuse` set from A-live; required outputs present |
| **Checkpoint B** (after Task 8) | Offline: `validate.py full`, `validate.py browser`. **Live: B-live** | Live pass criteria and required outputs below; owner accepts the Context and Review screens |

Rewrite-tournament targets: `guess_kind`, `expectations` and the Review renderer.

## Live checks

| Check | Pathway and case | Cap (USD) | Passes when (besides required outputs) |
|---|---|---|---|
| **A-live** refusal through a pathway (A) | **Covenant & Refinancing** on TDG FY2024 public filings, "older source"; no legal files; legal documents declared `none` | 25 | Records whether CP-4 ends as an accepted Blocked handoff or stops the run, what downstream modules and the report then show, and what it cost; the `Will refuse` wording and "Run without" fix are set from it; forecast equals outcome for every module |
| **A-ab** classification A/B (A, optional) | **Credit Snapshot** on the same files, twice: investment grade, then high yield | 25 each | Conclusions unchanged, or the "information only" decision is revised |
| **B-live** Secondary through the app (B) | **Relative Value** on TDG FY2024, Secondary, high yield, one TDG notes facility row and one observed quote labelled "synthetic user entry", through the app UI with acceptance | 30 | Start without acceptance returns 400 with no claim and no ledger entry; each module's outcome equals its forecast or the rule is fixed; coupon and maturity are used only as "entered by user", never cited as filing evidence; CP-3 treats the row as terms, not talk; CP-1 chart values match retained `cpos-launch-cp2-reader-001` or the variance is recorded; the Library shows "with accepted limitations" |

Caps total USD 55, or USD 105 with A-ab.

## Review Focus

1. **Declaration drives:** legal documents declared `draft` and nothing recognised on pages 1-3: CP-4
   `Limited` (Provisional), plus a `Check` ("no draft recognised"). Never `Will refuse` (Task 3).
2. **Non-recognition stays a Check:** a 10-K whose exhibit index names the credit agreement, with legal
   documents declared `executed`: classed financial report; CP-4 `Check`; no "Run without" (Tasks 2, 3).
3. **False drafts:** an executed credit agreement whose page 1 has "PRELIMINARY STATEMENTS" is not
   marked draft; an unmarked EDGAR exhibit has `executed=None` and gives `Check` (Task 2).
4. **Amendment alone:** CP-4 `Limited` ("base agreement not recognised"), never `Ready` (Task 3).
5. **Non-USD issuer (Erste):** CP-2D `Limited`; CP-1 chart strip `Limited` (US$m only); no USD labels
   invented (Task 3).
6. **Investment grade:** one information item for the run; no per-module rows; not counted (Task 3).
7. **Acceptance does not fire on structure alone:** a clean Covenant & Refinancing run with everything
   declared and recognised counts 0 items; a Credit Snapshot whose only item is `what-changed`
   counts 0 (Tasks 3, 7).
8. **Older context:** loads with new fields not stated and dumps byte-identical; the form marks the
   classification to fix; a resume keeps the stopped run's context bytes and does not ask (Tasks 1, 6).
9. **Hidden fields:** switching Primary → Secondary in the form blanks talk fields before `build()`
   (Task 1).
10. **Hostile text:** file names and context text render inert on the Review step and in the library;
    a hostile URL hash value is ignored (Tasks 7, 14).
11. **Stale acceptance:** inputs changed after acceptance; Start refuses and asks for a new review (Task 6).

---

## Stage 1 (PR 1 of 2): context fields and rule set

### Task 1: Context fields, declarations and compatibility

**Files:** modify `docs/templates/context-form.html`, `docs/templates/README.md`,
`apps/issuer-library/web/context-embed.js`, `src/deploy_workflow/context.py`,
`tests/product/test_context.py`, `apps/issuer-library/web/context-embed.test.cjs`,
`apps/issuer-library/validate.py`; regenerate `apps/issuer-library/web/context-form.html` with
`packaging/sync_assets.py`.

- [ ] **Issue classification:**
  - A choice directly after Issuer ID: Required, nothing preselected, and visible (not moved into
    "Additional issuer details").
  - Cards: **Investment grade** and **High yield**. Help: "Classify by the debt this run analyses;
    for split-rated or unrated issuers use your firm's convention. The workflow's methods are
    written for high-yield and leveraged-loan credit."
- [ ] **Legal documents** declaration: required, with nothing preselected. Card text updated to the
      Provisional behaviour. Remove "CP-4 refuses them today" and "draft mode Planned".
- [ ] **Facilities** for every run type: required (at least one row) for Primary, optional
      otherwise. Each row gains optional **Coupon (%)**, **Margin (bps)** and **Maturity**. Spread
      talk, OID talk and tenor show for Primary only, and `build()` blanks them on other run types.
- [ ] **Reader:**
  - `Identity.issue_classification: Literal["", "investment_grade", "high_yield"] = ""`.
  - `DealTerm.coupon_pct` and `margin_bps` are plain non-negative numbers; `maturity` is a date.
  - Every row is validated for every run type: move the checks before the non-Primary return, and
    drop the Primary-only refusal.
  - Empty new fields are omitted on dump (`_omit_absent_cutoff` pattern).
- [ ] **Tests:**
  - An older file loads and dumps byte-identical.
  - Each valid value round-trips, and invalid values are refused.
  - A Secondary context with facility rows loads.
  - Review Focus 8-9.
  - The form/reader parity test covers the new fields.
  - `cases/PINS.json` is unchanged.
  - All tests are registered in `PYTHON_TESTS`.

### Task 2: Document-kind guess

**Files:** create `src/deploy_workflow/run_expectations.py`, `tests/test_run_expectations.py`,
`tests/fixtures/run-expectations/document-key.json`.

- [ ] **Hand-labelled key first:**
  - At least 20 real files, mostly from `runs/*/sources/` (the public corpus holds only 5 TDG
    files). These include the executed ARCC supplemental indenture, the TDG "EXECUTION VERSION"
    indenture lines, the Enel EMTN supplement, HTML filings and a non-English report.
  - Synthetic fixtures only for kinds no retained file has, labelled synthetic.
  - Adversarial entries: "PRELIMINARY STATEMENTS" in an executed agreement; an unmarked EDGAR
    exhibit; an amendment alone; an offering memorandum with audited financial pages; a combined
    PDF; a misleading file name; an empty page; an xlsx workbook.
- [ ] **`guess_kind(name, first_pages) -> Guess(kind, signal, executed, period_end)`:**
  - Kinds: `financial_report, earnings_release, credit_agreement, indenture, amendment,
    intercreditor, compliance_certificate, covenant_review, offering_memorandum, prospectus,
    lender_presentation, information_memorandum, term_sheet, commitment_letter, ratings,
    market_quotes, peer_data, management_bridge, portfolio, prior_decision, unrecognised`.
  - `executed` is `True`, `False` or `None`. "Preliminary Statements" is never a draft signal.
  - `period_end` is read from a financial report's cover where stated.
  - Cover phrases outrank later pages and names; ambiguity gives `unrecognised`.
- [ ] **Tests:** accuracy per kind, reported separately for real and synthetic files; Review Focus
      2-3; HTML header line skipped.

### Task 3: Rules and expected outcomes

**Files:** modify `src/deploy_workflow/run_expectations.py`, `tests/test_run_expectations.py`.

- [ ] **`Rule(scope, condition, outcome, reason, fix, basis, evidence)`:**
  - `scope` is a module or `run`.
  - `basis` cites the instruction text sent on app runs, or is labelled owner-path.
  - `evidence` is `per method`, `observed offline` or `observed live`.
- [ ] **Initial rules**, each verified against `instructions/<module>.md` text before it is written:

| Scope | When | Outcome |
|---|---|---|
| Run | Investment grade selected | Information |
| Run | Report section omitted by this pathway | Information |
| CP-1 | No file recognised as a financial report, earnings release or offering document with financial pages | Check |
| CP-1 chart strip | `reporting_currency` not USD | Limited (charts are US$m only) |
| CP-1C | `valuation.peer_source` is `none`, or `cp_dr_public` without CP-DR | Gap |
| CP-2D | `reporting_currency` not USD | Limited |
| CP-2H | No `ratings` in the context and no ratings file recognised | Gap (method: Insufficient Information) |
| CP-3 | Talk but no observed quote in the context or files | Limited |
| CP-3 | No quotes and no talk in the context, and no quotes file recognised | Gap |
| CP-3D | No quotes in the context and no quotes file recognised | Gap |
| CP-4 | Legal documents declared `none` | Will refuse (outcome text set from A-live) |
| CP-4 | Declared `executed`, none recognised as executed | Check |
| CP-4 | Declared `draft`, or Primary run, with no executed agreement recognised | Limited: Provisional |
| CP-4 | Only an amendment recognised | Limited: base agreement not recognised |
| CP-4 | Secondary or Research run whose governing terms rest on a final offering memorandum | Limited: summary, not the governing document |
| Run | No filed financial report recognised, lender presentation or information memorandum recognised | Check: financials are management claims |
| CP-2 | Primary without CP-1D in the modules | Gap: pro forma base row |
| Portfolio Decision | `portfolio_workbook` declared false | Gap |

- [ ] **`expectations(ordered, guesses, context, registry)`:** returns run-level items first, then
      modules in order, with inheritance and counting as in Outcome semantics. Context values are
      read as entered, and no rule compares one user entry with another.
- [ ] **Tests:** hand-written outcomes for Review Focus 1-7, plus one clean case per pathway per run
      type, labelled synthetic.

### Task 4: Launcher and bridge carry the expectations

**Files:** modify `src/deploy_workflow/owners/cpos_launch.py`, `apps/issuer-library/engine/bridge.py`,
`apps/issuer-library/designs/fake_engine/bridge.py`, `tests/test_cpos_launch.py`, `tests/test_cpos_app.py`.

- [ ] `_issuer_files` keeps `pages[:3]` per pinned source; nothing else changes in what is pinned or
      refused.
- [ ] `Prepared` gains defaulted `documents` and `expectations`. Only `prepare()` builds it.
- [ ] `review()` adds `issue_classification`, `documents`, `expectations`, `counted` (item ids), and
      `without` for each declaration-based `Will refuse`.
- [ ] Tests: output shape, unchanged refusals, `without` closure.

### Task 5: Live-check cases and back-test (Checkpoint A)

**Files:** modify `apps/issuer-library/designs/live_check.py` and its tests; create
`tools/expectations_backtest.py` and `cases/live-tdg-fy2024/`, with sources referenced read-only
from `data/public-corpus/v1/TDG`; add a dated entry to `VERIFICATION.md`.

- [ ] **`live_check.py --case DIR`:**
  - The case folder holds a context, a source list, the modules, a frozen answer key and the
    expected outcomes.
  - It runs a whole pathway through the app UI, then checks every required output (Live
    checkpoints): run folder, delivery bundle, `flow_check`, and `browser_check`'s
    real-workspace walk over a workspace holding the run.
  - `--accept-limitations` drives the acceptance step once Stage 2 exists.
  - With `--rehearse` it runs free on the fake engine, and its scope string says so.
- [ ] **Back-test:**
  - Covers the 4 launcher runs, plus the reconstructed-context campaign cases, labelled.
  - Reports per rule: agreed, disagreed or not testable, with issuer and date. Labelled
    "deterministic retained-data report".
- [ ] **Checkpoint A:** offline gates, then **A-live** (and **A-ab** if wanted) on the owner's go-ahead.
      Set `Will refuse` wording and the rule labels from the results.

## Stage 2 (PR 2 of 2): acceptance and the Review screen

### Task 6: Start requires and records acceptance

**Files:** modify `apps/issuer-library/jobs.go`, `apps/issuer-library/jobs_test.go`,
`apps/issuer-library/engine/bridge.py`, `tests/test_cpos_app.py`.

- [ ] **Go side:**
  - `startRun`'s request struct gains `accept_limitations` (unknown fields are refused).
  - When `review.json` counts any items and acceptance is false: answer 400, with no claim made.
- [ ] **`bridge.start`:**
  - Records the accepted item ids in the existing `start-authorization.md` receipt.
  - Copies `expectations.json` from the approved review (never recomputed) into the run folder.
  - Snapshots the context into the run folder before any provider call.
- [ ] **Resume:**
  - Keeps the stopped run's context bytes and needs no new classification.
  - The review states which retained answers re-run and why. Adding CP-1D is one reason.
  - Retained modules show their actual outcome, not a forecast.
- [ ] **Tests:** Review Focus 11 and 22; zero counted items works with the old request; files exist
      before the worker's first call.

### Task 7: Review step shows expectations first

**Files:** modify `apps/issuer-library/web/actions.js`, `apps/issuer-library/web/screen.css`,
`apps/issuer-library/web/new-run.test.cjs`.

- [ ] The context summary line and Review header show the classification ("Investment grade", "High
      yield" or "Not stated").
- [ ] An "Expected outcomes" table opens the Review step:
  - **This run** items come first.
  - Each module row shows its outcome, reason and fix, with a "Why we expect this" disclosure
    giving the basis and evidence label.
  - Inherited rows sit under their producer, and information rows are visibly not counted.
- [ ] "Files recognised" lists each file's likely kind, draft or executed where marked, and its signal,
      or "Not recognised".
- [ ] **Run without <module>** fills Advanced → Modules with `without` and returns to Issuer folder &
      budget.
- [ ] Extra modules (CP-1D on Primary) are named with their reason.
- [ ] "I accept these N items" appears only when N > 0. Start needs both ticks.
- [ ] All text goes through `textContent`. Tests: rendering, gating, inert text, Review Focus 7.

### Task 8: Help, README and Checkpoint B

**Files:** modify `apps/issuer-library/README.md`, Help in `apps/issuer-library/web/views.js`,
`VERIFICATION.md`.

- [ ] Describe the declarations, outcomes as forecasts, counted items, acceptance and the context
      snapshot.
- [ ] Extend `browser_check`'s New run walk: the new context fields, the expected-outcomes table, the
      acceptance gating and "Run without". Rehearse it on the fake engine.
- [ ] Checkpoint B: offline gates, then **B-live** on the owner's go-ahead.

## Done when

- **Context form:** the issuer identity section requires investment grade or high yield, and legal
  documents are declared. Every run type can record facilities, and older context files load and
  dump unchanged.
- **Review step:** lists forecast outcomes driven by declarations, with reasons and fixes.
  Structural and method-fit notes are shown but not counted.
- **Start:** cannot proceed past counted items without the separate acceptance. Every started run
  holds `expectations.json`, its context snapshot and the accepted item ids.
- A-live (and A-ab if wanted) and B-live have passed, with every required output, recorded with
  their actual scope.
