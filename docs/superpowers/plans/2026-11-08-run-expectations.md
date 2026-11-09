# Beta V1 plans: index and shared rules

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

The combined plan "Run Expectations, Primary Transactions and Credit Filters" (merged in PR 52 and
revised after an adversarial review) held too many separate requirements. It is now split into five
plans, in the order they are to be done. Each plan is its own PR (Plan 2 is two), at most 800 changed lines
excluding fixtures, on its own branch from `main`, and each leaves `main` releasable.

| Order | Plan | What it delivers | Depends on | Paid live checks |
|---|---|---|---|---|
| 1 (now) | [Library screening in the app](2026-11-08-plan-1-library-screening.md) | The approved `examples/issuer-library` screening design wired into the app's Library, on the data the app already serves, tested and opened by the owner | Nothing | None |
| 2 | [Run expectations and acceptance](2026-11-08-plan-2-run-expectations.md) | Context fields and declarations, forecast module outcomes on the Review step, Start requires acceptance | Nothing | A-live, A-ab (optional), B-live |
| 3 | [Primary transactions](2026-11-08-plan-3-primary-transactions.md) | Provisional CP-4 review of drafts, pro forma capitalisation and leverage, public proxy case | Plan 2 (run type and declarations reach the launcher) | C1, C1n, C2, C1r, C3 |
| 4 | [Library credit data](2026-11-08-plan-4-library-credit-data.md) | A `library.json` manifest for every finished app run, and the credit, rating, facility and quote filters | Plan 1; Plan 2 (context fields, `expectations.json`); Plan 3 for the pro forma keys only | D-live (no provider cost) |
| 5 | [Beta V1 release](2026-11-08-plan-5-beta-release.md) | The release gate on the `main` commit to be released | Plans 1-4 | RC-live if code changed after C3 |

**Goal (unchanged):** fewer repeated runs, because the user knows before Start what each module is
expected to produce and accepts the listed limitations; Primary (new-issue) runs useful before
closing; and reports findable in the Issuer Library by credit and market information. Plan 1 comes
first because the owner needs to see and use the approved Library design in the app now.

**Beta V1 scope:** these plans are the final UX changes before the first beta release. Any other UX
change waits until after the beta. Nothing half-built is visible to a beta user. Plan 3 merges only
after C3 passes, so unproven method instructions never reach the beta.

## Owner decisions (2026-11-08)

1. Draft review on app runs: **yes**, as Provisional (Task 10).
2. Pro forma for Primary runs: **yes, with unrealised add-backs kept out of the base** and shown
   separately (Task 11).
3. Expected-rating status: **no**; ratings are user-entered.
4. Primary proof case: **no** retained or private case; public pre-closing filings serve as a
   labelled proxy (Task 9).
5. Live testing at each checkpoint of the applied changes: **yes**; each paid run still needs the
   owner's go-ahead at that checkpoint (Global Constraints).
6. User-entered values are used as entered; user-derived issues are the user's to resolve.
7. Library: **reuse the approved `examples/issuer-library` screening design and logic** in the app
   (Plans 1 and 4), not new filter code.
8. Split the combined plan into separate plans; the Library screening in the app comes first, so
   it is visible and usable now (2026-11-08).

## Facts shared by every plan (verified 2026-11-08)

| Finding | Decision |
|---|---|
| `tests/test_run_expectations.py` and `tests/product/test_context.py` are not in `validate.py`'s `PYTHON_TESTS` | Each task adds its tests there |
| A launcher run's delivery bundle must hold `report.html`, `view.json`, `report-view.json` and `delivery.json`, plus byte-identical copies of each handoff. When the HTML Model is published it adds `model.html`, `model-view.json`, `model-report-view.json` and `calculation.json` (`owners/cpos.py:648-691`). App runs drop CP-MODEL, and the retained web run records `cp_model_published: false` | Live checks require the report bundle. On app runs the HTML Model and `calculation.json` are recorded as **not published**, which is a known beta limitation; it is not a failure. Publishing them from app runs is an owner decision outside these UX changes |
| `designs/browser_check.py` already walks the library, reports, every section, deliveries and settings, fitted screens, chart style, the data-flow check and New run, and records every console, page, HTTP and exception fault in `faults.json`. `designs/flow_check.py` traces hashes and numbers from sources to handoffs, deliveries and the report | Every live run is followed by the browser walk over a workspace holding it, plus `flow_check`. Each phase extends the walk for its own screens; no new test tool |

## Shared names (2026-11-08)

Plans 2, 3 and 4 build on separate branches against these names. A worker who needs to change one
asks the coordinator first; the change lands here before it lands in code.

**Context fields** (Plan 2 Task 1; `context/1`, no new schema version):

| Field | Values | Notes |
|---|---|---|
| `identity.issue_classification` | `""`, `investment_grade`, `high_yield` | `""` = not stated; omitted on dump, so older files stay byte-identical |
| `deal_terms[]` (the form's Facilities) | existing `DealTerm` rows | Allowed on every run type; at least one row required on Primary only |
| `deal_terms[].coupon_pct`, `.margin_bps`, `.maturity` | plain non-negative numbers; `maturity` a date; `""` = not supplied | Optional, omitted on dump when `""` |
| `quotes[]` | existing `Quote` rows: `facility_id`, `kind` (`observed`, `indicative_talk`), `bid`, `ask`, `price`, `yield_pct`, `spread_bps`, `as_of`, `provider` | Unchanged; joined to a facility by `facility_id` |
| `attachments.legal_documents` | `executed`, `draft`, `none` | Unchanged in the reader; the form drops its preselected default |
| `run.run_type`, `run.case_kind`, `ratings[]` | unchanged | Private side means `run.case_kind == "private"` |

**Expectations and the Start receipt** (Plan 2 Tasks 3, 4 and 6):
- `review()` adds `issue_classification`, `documents`, `expectations`, `counted` and `without`.
  `runs/<id>/expectations.json` is a copy of exactly those five keys plus `review_id`, taken from
  the approved review, never recomputed:

  ```json
  {"review_id": "…", "issue_classification": "high_yield",
   "documents": [{"source": "<pinned source id>", "kind": "credit_agreement",
                  "signal": "found 'CREDIT AGREEMENT' on page 1", "executed": null, "period_end": null}],
   "expectations": [{"id": "CP-4:legal-none", "scope": "CP-4", "outcome": "will_refuse",
                     "reason": "…", "fix": "…", "basis": "…", "evidence": "per method",
                     "counted": true, "inherited_from": []}],
   "counted": ["CP-4:legal-none"],
   "without": {"CP-4": ["CP-4", "CP-6"]}}
  ```

  - `outcome`: `will_refuse`, `gap`, `limited`, `check`, `information`, `ready` (shown as
    Will refuse, Gap, Limited, Check, Information, Ready).
  - `id` is `<scope>:<rule key>`, `scope` a module id or `run`; an inherited row is
    `<consumer>:from:<producer>`. Ids are stable for the same inputs, so review and Start agree.
    An inherited row is one per consumer: its id is `<consumer>:from:<first producer in module order>` and `inherited_from` lists every producer whose outcome propagates to it.
  - `evidence`: `per method`, `observed offline`, `observed live`.
- The Start request gains `accept_limitations` (boolean). `start-authorization.md` keeps its lines
  and adds `accepted: <ids, comma-separated>` (or `accepted: none`), using the review's `counted`.
- The context snapshot is `runs/<id>/context.json`, byte-identical to the reviewed context (its
  sha256 equals the `context` source pin). Plan 4 pins identity, ratings and facilities to its lines.
- `expectations.json`, `context.json` and the receipt carry one `review_id` and exist before the
  first provider call.

**Run type and legal-documents declaration in the launcher** (Plan 2 Task 4; used by Plan 3):
- `prepare` reads `settings.run.run_type` and `settings.attachments.legal_documents` and passes them
  as keywords: `_instructions(run, module, routes, *, run_type, legal_documents)`. `Run` is unchanged.
- `checker(layout)` keeps its signature. The checker learns Provisional scope (Primary, or
  `legal_documents == "draft"`) from CP-4's instruction bytes: one module-level constant holds the
  fixed paragraph, `_instructions` writes it, and the checker tests that constant's bytes in
  `task.instructions`. A consumer (CP-3, CP-5, CP-6) is in scope when its upstream CP-4 handoff
  holds `DRAFT_LIMITATION` or the final offering memorandum reason. `_layout` still gets the two
  keywords, for Plan 3 Task 11's pro forma table routes. The legal document register stays out of
  the report; every CP-4 section routed to the report still says Provisional (coordinator
  ruling, 2026-11-08).

**`library.json` additions** (`issuer-library-run/1`; Plan 4 Task 12, admitted under the existing
rule: an exact value in its pinned quote):
- `run.classification`: `investment_grade` or `high_yield`, absent when not stated, with
  `run.classification_source` naming its context-snapshot line.
- `run.private_side`: `true` only when `case_kind` is `private`, with `run.private_side_source`;
  absent otherwise.
- `run.facilities`: `[{"facility_id": "…", "terms": {<DealTerm field>: Metric}, "quotes":
  [{"kind": "observed", "terms": {<Quote field>: Metric}}]}]`. Term keys are the context field
  names above; each Metric (`value`, `unit`, `period`, `basis`, `source`) has `provenance: "user"`.
- Metric `provenance` adds `user` to `cited`, `calculated`, `synthetic`.
- `run.metrics` keys: `leverage`, `net_leverage`, `coverage`, `cash`, `undrawn` (CP-1 chart rows,
  provenance `calculated`) and, on Primary runs, `leverage_pro_forma` and `leverage_as_marketed`,
  read from CP-2's `### Pro forma leverage` rows `Pro forma, excluding unrealised add-backs` and
  `As marketed` (Plan 3 Task 11 writes these labels).
- `run.gaps`: the reasons of the accepted `counted` items, plus "HTML Model not published by app runs".

**Out of scope (later plans):** files-first run check with pathway ratings, phased context stages,
context prefill from filings, post-run expected-versus-actual in Run activity, investment-grade
variants of the methods, credit metrics for runs that predate the fixed tables, pro forma interest
cover, saved named filter views.

## Global Constraints

- **Paid runs** happen only at the live checkpoints below. Each needs the owner's go-ahead at that
  checkpoint, stating config, modules and cap. The provider key comes only from the launching
  environment. There is no automatic paid retry: a failed live check goes to the repair loop in
  `docs/QUALITY-GATE.md`, and a rerun needs a new go-ahead. Offline gates run with keys removed.
  Results are labelled with their actual scope: issuer, date, older source, synthetic user entries,
  public proxy.
- **Read-only material:** the repository's `runs/`, `deliverables/`, `data/public-corpus/`, `cases/`
  fixtures, `docs/reuse/selected-methods/` and predecessor repositories are read, never written. A
  new case gets its own folder. The app writes only inside its own workspace.
- **Expected values** are hand-written and committed before the code or paid run they check, by
  someone other than the code's author. This covers document-kind keys, rating scale, rule outcomes,
  pro forma keys, live answer keys and library values. Accuracy on real and synthetic files is
  reported separately.
- **Missing is never zero.** "Not supplied", "not stated" and "Not recorded" stay visible. No new
  score or aggregate. A missing, negative-denominator or not-meaningful figure never satisfies a
  numeric filter.
- **Arithmetic:** new module arithmetic uses `calculate`. The library and delivery never calculate,
  convert currency or rescale units.
- **Other limits:** Excel stays input-only. No new dependency.
- **Branch and PRs:** one branch from `main` per plan, one PR per plan. Commit per task; push at
  each checkpoint.
- **Records:** one short `VERIFICATION.md` entry per checkpoint. No other review files.

## Validation shared by every plan

| When | Command or action | Passes when |
|---|---|---|
| Every task | Named focused tests, registered in `validate.py` `PYTHON_TESTS`, each under `timeout 300` | New test seen failing for the stated cause, then exit 0 |
| Every commit | `uv run python tools/quality_gate.py`, `python3 apps/issuer-library/validate.py quick` | Exit 0 |

Each plan names its own checkpoints. Before each checkpoint: confidence-review (doubts, causes,
adversarial cases, fixes) and rewrite-tournament in post-edit mode on the functions that plan lists.

**Stop rules:** a failing gate stops the next task in its plan. Two failed fix rounds on one defect
go to the owner with both outcomes. Never loosen a test to pass.

## Live checks: method and required outputs

**How every live check runs:**
- Each paid check runs a **whole pathway related to the change**, through the app as a beta user
  would: `apps/issuer-library/designs/live_check.py`, extended in Task 5 with `--case`, on the real
  engine.
- Exceptions: C1, C1n and C2 are single-module gates, because `AGENTS.md` requires changing one
  module at a time against its actual output. The pathway runs follow them.
- Config is sol-medium unless the owner names another. Each cap exceeds the per-call hold (USD 5.73
  on sol-medium).
- For scale: a CP-0 + CP-1 run spent USD 0.59, and a multi-module, multi-issuer campaign about
  USD 14-20.
- Every answer key is frozen before its run. Each run needs the owner's go-ahead at its checkpoint.

**Required outputs, checked after every live run:**

| Side | Output | Passes when |
|---|---|---|
| Backend | Run folder | `workflow.json`, `instructions/<module>.md` and an accepted `<module>.md` for every requested module, or a recorded stop reason; the completion receipt; spend within the cap in `status.json` and the event log |
| Backend | New records (Plans 2-3) | `expectations.json`, the context snapshot, and the Start receipt with the accepted item ids, all written before the first provider call, with one `review_id` across them |
| Backend | Delivery bundle | `report.html`, `view.json`, `report-view.json`, `delivery.json`, with delivered handoffs byte-identical to the accepted ones. HTML Model and `calculation.json`: recorded as published or as "not published by app runs" (known beta limitation) |
| Backend | Data flow | `flow_check` reports no fault: every upstream hash and text received, every source hash, every handoff number traced to what the module read, every report number found in a handoff |
| Frontend | New run | The walk completes: Context (new fields), Issuer folder & budget, Review (expected outcomes, acceptance), Progress, Open run; the Review's module list equals the run's |
| Frontend | Reading the run | `browser_check`'s real-workspace walk over a workspace holding the run: Library row, Overview, every module section renders, Reports opens the report, Built from hashes match, evidence inspector opens the cited line, Run activity lists events and spend, fitted screens, chart style |
| Frontend | Faults | `faults.json` holds no console, page, HTTP or exception fault outside the documented list, in Chromium and the walk's second engine |

Each plan lists its own checks and caps. Caps total USD 150 across Plans 2-4, or USD 200 with A-ab;
expected spend is far lower.

**EDGAR access:** granted on 2026-11-08 through the owner's personal environment `final-workflow`
(www.sec.gov, efts.sec.gov and data.sec.gov). Requests identify themselves as "final-workflow
research" with the owner's email, as EDGAR requires and as the owner authorised. They stay well
under EDGAR's 10 requests per second.

## Review record (2026-11-08)

Two independent reviewers checked the merged plan: one fact-checked its claims against the code, the
other attacked its design. Adopted: everything in the five plans that differs from the merged version. Rejected, with
reasons, under **Rejected** in Plans 2 and 3.

| Area | Correction adopted |
|---|---|
| Facts | 4 launcher runs, not 21; `store.py` parses no values; CP-3's parser and the `cp2h` refusal are owner-path only; `READER_PERSONA` is high-yield for every module; 78 context fixtures; `Run` has no run type |
| Outcomes | Declarations drive outcomes; non-recognition gives `Check` only; milder-of inheritance; `Check` never propagates; structural and investment-grade items are information, not counted |
| Primary | Provisional scope and propagation to report and downstream modules; final offering memorandum reason; ranks 2-5 as kinds; EBITDA ladder without double counting; structural checks instead of an equality; cash row, dates and FX rule; report table routes |
| Compatibility | Empty new fields omitted on dump; form blanks hidden talk; resume keeps context bytes; a context snapshot at Start |
| Library | Last annual or LTM row; negative leverage not meaningful; cash and undrawn filtered separately; latest run defined; rating-scale edge cases; private-side label; hash validation |
| Library | Owner chose the approved `examples/issuer-library` screening design and logic, fed by the existing manifest admission |
| Process | Live checkpoints A-live, A-ab, B-live, C1, C1n, C2, C1r, C3, D-live, each a related whole pathway except the single-module gates, with frontend and backend required outputs; beta V1 release gate; Phase 3 one module at a time; four PRs; tests registered in `PYTHON_TESTS` |
| Split (2026-11-08) | Owner asked for separate plans, the Library screening in the app first; content moved unchanged except where Plan 1 now does the port that Task 13 began with |
