# Plan 4: Library Credit Data

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

**Goal:** Readers who only want reports can find them in the Issuer Library by credit and market
information. Each finished app run writes a `library.json` manifest pinning its credit and market
facts to exact lines of its handoffs and context snapshot; the screening ported in Plan 1 filters on
admitted values, links each to its pinned line, and never calculates a figure.

**Tech Stack:** Python 3.13 (stdlib), Go, plain browser JavaScript; jsdom test-only.

**Delivery:** one PR. It does not wait for Plan 3's live checks, except the pro forma basis, which
ships only after live check C2 passes.

**Depends on:** Plan 1 (the screening is already in the app); Plan 2 (classification, facilities and
quotes in the context, the context snapshot, `expectations.json`); Plan 3 for the pro forma keys only.

**Shared rules:** the index, [`2026-11-08-run-expectations.md`](2026-11-08-run-expectations.md), holds the owner decisions, global constraints, the live-check method, the required outputs and the review record. They apply here unchanged. Review Focus numbers and task numbers are kept from the combined plan, so cross-references still resolve.

## Facts this plan builds on (verified 2026-11-08)

| Finding | Decision |
|---|---|
| The app already admits per-run manifests `runs/<id>/library.json` under the approved example's rules and serves them at `/api/catalogue` (`discovery.go:45-130, 261-296`; `model.go`). Before Plan 1 the Library screen ignored them (`boot.js:11-15`); app runs write none. `store.py` only recognises the shape of `Chart data:` tables | The bridge writes the manifest for each finished app run (Task 12), and Task 13 extends Plan 1's ported screening for the new fields. `store.py` is unchanged for the library |
| CP-1's chart tables hold one row per period, with units fixed at x, US$m or % | Manifest metrics come from the last annual or LTM row. A non-USD issuer's monetary rows are `Not supplied` and write no metric; a rule says so |

**Source design (owner decision 7), ported by Plan 1:** `examples/issuer-library`, the user-approved screening
directory: "one local directory of issuer runs, searchable by identity, sector and credit metrics,
with completeness and links to the existing reports". It is ported, not rewritten:
- **Logic:** `logic.js` (`LibraryLogic`: `numberOf`, `hasReport`, `filterRuns`, `sortRuns`).
  - A blank never satisfies a bound.
  - Leverage filters by exact basis ("All bases · definitions differ").
  - Missing values sort last.
  - Nothing is calculated.
- **Screens:** `template.html`, `app.js` and `style.css`.
  - The screening panel: search; sector, workflow, completeness and deliverables; "Credit metrics &
    period" (leverage basis, financial period, leverage and coverage minimum and maximum).
  - The sortable results table: Issuer / run, Sector, Evidence date, Leverage, Coverage,
    Completeness, Deliverable.
  - The selected-run detail: each metric's value, unit, period, basis and pinned source; gaps;
    report history.
- **Tests:** `test_logic.cjs` and `test_dom.cjs` move with the code and keep passing.
- **Style:** the example used the deliverables' Direction C shell. In the app the composition is kept
  and restyled with the app's own tokens (`screen.css`); there is no second palette.

**Data path (already in the backend):**
- Go discovery admits `runs/<id>/library.json` (`issuer-library-run/1`) under the example's rules
  (`discovery.go:45-130, 261-296`):
  - Every metric is an exact value present in its pinned source line (path, sha256, line, quote).
  - Provenance is cited, calculated or synthetic.
  - Ratings are pinned the same way.
  - Completeness comes only from a five-stage checklist (sources, analysis, verification,
    downstream, delivery) whose done items carry verified evidence.
- `/api/catalogue` already serves these runs; the Library screen does not use them (`boot.js:11-15`).
- Retained curated runs are seeded from the example's catalogue (`sync_assets.py:18-20`). App runs
  write no manifest today, so they show nothing.

**What this plan adds to the example:**

| Addition | How |
|---|---|
| Classification, currency, private-side label | Run fields from the context snapshot |
| Lowest rating | Ratings pinned to context snapshot lines; the scale orders them |
| Net and total leverage, interest cover, cash, undrawn facilities | Metrics from the latest annual or LTM row of CP-1's chart tables |
| Pro forma leverage (excluding unrealised add-backs; as marketed) | Separate metric keys from CP-2's table, each with its own basis; never in the default Leverage column |
| Facilities and quotes as entered | A new `facilities` field, provenance `user`, matched within one facility |
| Accepted limitations | Gaps, from `expectations.json` |
| Issuer grouping, latest run by default, Overview and Reports routes, URL hash state | Existing app behaviour, kept |

## Validation

| When | Command or action | Passes when |
|---|---|---|
| **Checkpoint D** (after Task 14) | Offline: `validate.py full`, `validate.py browser`. **D-live** (no provider cost) | Exit 0; library values equal the hand key; required frontend outputs present; owner accepts the Library screen |

Rewrite-tournament targets: the credit-facts reader, the facility matcher and `filterRuns`.

## Live checks

| Check | Pathway and case | Cap (USD) | Passes when (besides required outputs) |
|---|---|---|---|
| **D-live** library (D) | No new run: the workspace holding the A, B and C runs and the retained runs with fixed chart tables, opened in the ported screening Library | 0 | Every live run's `library.json` is admitted with no rejection; each screened value equals a hand key from the actual handoff and context lines, including pro forma metrics and facilities and quotes as entered; the example's filters, sorting and run detail behave as specified, and their evidence links open the pinned line; coverage and hidden counts are right. Labelled "actual retained model output, downstream consumption" |

## Review Focus

17. **Missing is not a pass:** "Net leverage below 4x" excludes runs with no figure, `Not supplied` or
    a negative value, and says how many it hid (Task 13).
18. **Leverage basis:** the Leverage column and filter read only CP-1's chart metric and show its basis
    text. The pro forma keys never fill it. With "All bases" chosen, the panel says definitions
    differ, as in the example (Task 13).
19. **Latest run:** the latest as-of date among runs with a written report; a newer stopped run is
    shown but used only under "Any run" (Task 13).
20. **Ratings:** "(P)B2" and "B+(EXP)" place as B2 and B+ and keep their text; SD, RD and "/LD" place as
    D; NR, WD and WR are not on the scale; issuer scope by default; BBB- and Ba1 match "BB+/Ba1 or
    below" (Task 13).
21. **Facilities:** two facilities never combine to match one filter; talk 325-375 matches "350-400";
    a Secondary bond with bid 98.50 / ask 99.00 and no price matches "price 98.75-100" and not
    "above 99.50"; margin 375 matches a margin filter but not a margin-talk filter (Task 13).
22. **Context snapshot:** editing the intake context after a run does not change what the library
    shows for that run, because the manifest pins the run's own snapshot (Tasks 6, 12).
23. **Private-side material:** a run whose context `case_kind` is private carries a "Private-side"
    label in the library (Task 13).
24. **Manifest admission:** every live run's manifest is admitted with no "Run metadata rejected" gap;
    a manifest value absent from its pinned line is rejected by the existing rule (Task 12).

---

## Tasks

### Task 12: Run manifest for every finished app run

**Files:** modify `apps/issuer-library/engine/bridge.py`, `apps/issuer-library/model.go`,
`apps/issuer-library/discovery.go`, `apps/issuer-library/discovery_test.go`, `tests/test_cpos_app.py`;
create `tests/fixtures/library-manifest/` (hand-written expected manifests).

- [ ] Hand-write the expected manifests first: one synthetic run and one from the retained CP-1 chart
      handoff (`7f0578…`).
- [ ] After delivery, `bridge.start` writes `runs/<id>/library.json`:
  - **Identity:** identity and sector pinned to context-snapshot lines; date = as-of; currency;
    classification; the private-side flag from `case_kind`.
  - **Chart metrics:** `leverage`, `net_leverage`, `coverage`, `cash` and `undrawn`, from the latest
    annual or LTM row of CP-1's chart tables.
    - Each is pinned to its row's line, with provenance `calculated`.
    - Its basis is the row's "Basis and limitation", its unit the Reporting unit, its period the Period.
  - **Pro forma metrics:** on Primary runs, `leverage_pro_forma` and `leverage_as_marketed`, from
    CP-2's Pro forma leverage rows.
  - **No metric written:** for a `Not supplied` cell, a negative value or a missing table. The run then
    shows Not recorded.
  - **Ratings and facilities:** pinned to context-snapshot lines, with provenance `user`.
  - **Gaps:** the accepted limitations' reasons, plus "HTML Model not published by app runs".
  - **Checklist:**
    - sources: the pinned sources in `workflow.json`;
    - analysis: one item per requested module, done when accepted;
    - verification: the launcher's completion receipt;
    - downstream: delivered copies byte-identical per `delivery.json`;
    - delivery: the verified `report.html`.

    Each done item cites its evidence.
- [ ] **Admission:** `model.go` and `discovery.go` gain `classification`, `private_side`, `facilities`
      and provenance `user`, under the same rule (exact value in the pinned quote). Nothing else in
      admission changes.
- [ ] **Failure isolation:** a manifest failure never changes the run's outcome. It becomes a
      Settings issue, and the run shows Not recorded.
- [ ] **Tests:**
  - Hand-written manifests are admitted unchanged.
  - A changed value or line is rejected (existing rule).
  - A Primary run.
  - A run with no chart table.
  - Review Focus 22 and 24.

### Task 13: Extend the ported screening with credit and market data

**Files:**
- Modify `apps/issuer-library/web/screening.js` (Plan 1's port), `web/views.js`, `web/screen.js`,
  `web/screen.css`, their tests, and `designs/browser_check.py`.
- Create `tests/fixtures/library-credit/rating-scale.json`.

- [ ] **Rating scale (hand-written fixture):**
  - S&P/Fitch `AAA`…`D` and Moody's `Aaa`…`C`, notch-aligned.
  - Bottom-of-scale equivalences marked approximate.
  - `(P)` and `(EXP)` read through, with their text kept.
  - SD, RD and `/LD` map to D. NR, WD and WR are off the scale.
- [ ] **Extend `filterRuns`** only for this plan's additions:
  - classification, currency and lowest rating (issuer scope by default);
  - the pro forma metric keys;
  - facility and quote filters matched within one facility: single values inside the filter, talk
    and bid-ask by overlap;
  - accepted limitations;
  - latest run per issuer (default) or any run.
- [ ] **Library screen:** new columns and detail rows for the additions. Each figure shows value,
      unit, period and basis; its pinned line opens in the evidence inspector.
- [ ] **Coverage and hidden counts** per filter ("Coverage recorded for 3 of 44 runs · 12 hidden · Show
      them"). The filter state lives in the URL hash, which accepts only known controls and values.
- [ ] **Tests:** all text through `textContent`. The example's tests, plus Review Focus 17-21 and 23,
      keyboard and screen-reader labels, and narrow screens.
- [ ] **Browser walk:** extend `browser_check`'s real-workspace walk to the screening panel, each filter
      group, sorting, the run detail and hash restore.

### Task 14: Help, README and Checkpoint D

**Files:** modify Help in `apps/issuer-library/web/views.js`, `apps/issuer-library/README.md`,
`VERIFICATION.md`. (The example's README was updated by Plan 1.)

- [ ] **Help and README** explain:
  - each figure's pinned line;
  - the leverage bases, and why unrealised add-backs stay out of the base;
  - that missing values never match;
  - the latest-run rule;
  - that user values show as entered;
  - that completeness comes from the verified checklist.
- [ ] **Checkpoint D:** offline gates and **D-live**.

## Done when

**Library:** the ported screening carries the credit and market data.
  - Every finished app run writes a manifest that discovery admits.
  - It filters by classification, rating, leverage on a chosen basis, interest cover, cash, undrawn
    facilities, currency, completeness and the facility and quote terms.
  - Each figure links to its pinned line, user values show as entered, and missing values never match.
  - D-live has passed.
