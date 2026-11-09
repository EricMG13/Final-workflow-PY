# Plan 1: Library Screening in the App

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Subagents are permitted for
> implementation, review and verification (`AGENTS.md`); expected values are never written by the
> agent that writes the code they check. Split on 2026-11-08 from the combined plan revised after
> its adversarial review.

**Goal:** The owner opens the Issuer Library app and its Library screen is the approved
`examples/issuer-library` screening design: search and filters, the sortable results table with
leverage, coverage and completeness, and the selected-run detail with its sources. It uses the
records the app already serves, it is tested at every level the app has, and the owner can use it now.

**Architecture:** Frontend only. The backend already serves records in the example's shape at
`/api/catalogue`. `boot.js` exposes them, the example's `LibraryLogic` is ported unchanged, and the
example's composition replaces the Library screen inside the app's rail and workspace, restyled with
the app's own tokens. No new endpoint, no manifest writer, no calculation, no provider call.

**Tech Stack:** plain browser JavaScript and CSS (`apps/issuer-library/web/`), Go only to build and
serve; jsdom and Playwright test-only.

**Delivery:** one PR, at most 800 changed lines excluding fixtures. No paid live check.

**Shared rules:** the index, [`2026-11-08-run-expectations.md`](2026-11-08-run-expectations.md),
holds the owner decisions, global constraints and review record. They apply here unchanged.

## Facts this plan builds on (verified 2026-11-08 on `main`, 089b554)

| Finding | Decision |
|---|---|
| `/api/catalogue` returns `real` (59 records), `sources`, `built_at`, `issues`, `workspace`, `live` and `policy_locked`. Each record has the example's fields: `id`, `issuer`, `name`, `title`, `sector`, `workflow`, `date`, `period`, `period_kind`, `metrics`, `completion`, `checkpoints`, `ratings`, `gaps`, `summary`, `artifacts` (with `available` and `href`), `handoff_href`. `illustrative` is empty | Port onto these records as served. No backend change. The example's Illustrative dataset switch is not ported: the app ships no fictional dataset (README, Discovery) |
| `boot.js:11-15` reads the catalogue but passes on only `workspace`, `policy_locked` and `issues`; the Library screen (`views.js:325-492`) lists store runs grouped by issuer and has no metrics | `boot.js` also exposes `catalogue.real` and `catalogue.sources` (e.g. `window.DESIGN_CATALOGUE`) |
| 44 records are the 44 run folders; each `id` equals a store run's `folder` (e.g. `ford-otosan-2024-001` ↔ store key `ford-otosan-2024`). 15 records are `delivery:<id>` rows for deliverables with no run folder: 12 are store reports and 3 (`tdg-model-1` to `-3`) are published models | Rows join store runs by `folder`, so a run row opens the run's Overview; a delivery row opens its report in Reports, or its model in Forecast. A record with no match keeps its row and shows no Overview link |
| An artifact's `href` is `/files/<folder>/report.html?sha256=…`; a store report's `href` is the same path with `&embedded=1` | Artifact → report by that path, so "Open report" opens inside the app beside its Built from list, not in a new tab |
| Only 4 retained records carry metrics (`ford-otosan-2024-001`, `tdg-002`, `tdg-003`, `tdg-guidance-001`); every `completion` is null | Most rows show "—" and "Not assessed". That is the truthful state; Plan 4 adds metrics for app runs. Help says so |
| Started without `ISSUER_LIBRARY_ENGINE_ROOT` and `ISSUER_LIBRARY_PYTHON`, a source build shows "The library could not read this workspace" (`/api/workspace` 503) | The owner's launch instructions set both (Task L4) |
| `main`'s `go.mod` says `go 1.26.0`; PR 53 moves it to 1.24 | Building from source needs Go 1.26, or PR 53 merged first. Task L4 states which |
| `designs/browser_check.py` `library_and_report` expects `#library-results .issuer-row`, one `a.run-link` per run folder and `.run-toggle` groups; `web/library-workspace.test.cjs` and `web/screens.test.cjs` test the current Library | These tests change with the screen; their run-coverage assertions are kept against the new rows |

## Decisions (owner may change before Task L2)

- **Replaced:** the issuer-grouped list, and its As of year, Available content and Contains module
  selects. **Kept:** the page actions (All reports, New run), the empty and unreadable-workspace
  states, and the filter state when the reader leaves the Library and returns.
- **Issuer navigator:** the example's All runs, Reports available and Issuers list sits at the left
  of the Library screen, where the module navigator sits on run screens.
- **Sources:** each metric's "View source" opens the Sources & definitions block, as in the example;
  "Open retained source" opens the pinned file through `/files/…`, which rechecks its hash. Opening
  the pinned line in the evidence inspector is Plan 4.
- **Not in this plan:** URL hash state for filters, coverage and hidden counts, and every
  credit-data filter (Plan 4).

## Tasks

### Task L1: Port the logic unchanged

**Files:** create `apps/issuer-library/web/screening.js` (from `examples/issuer-library/logic.js`) and
`apps/issuer-library/web/screening.test.cjs` (from `examples/issuer-library/test_logic.cjs`); modify
`web/boot.js`, `web/index.html` (load order) and `validate.py` (`NODE_TESTS`).

- [ ] Copy `LibraryLogic` byte-for-byte apart from the file header; the example's logic tests pass
      against the app copy unchanged.
- [ ] `boot.js` exposes the catalogue's `real` and `sources`; an unreadable catalogue leaves them
      empty and the existing problem banner stands.

### Task L2: The Library screen

**Files:** modify `web/views.js` (`libraryView` and its helpers), `web/screen.js` (events),
`web/screen.css`.

- [ ] **Screening panel:** search; Sector, Workflow, Completeness and Deliverables; the "Credit
      metrics & period" disclosure with Leverage basis ("All bases · definitions differ"), Financial
      period, and Leverage and Coverage minimum and maximum; Reset filters. The filter help text
      says numeric filters exclude unavailable values.
- [ ] **Results table:** Issuer / run, Sector, Evidence date, Leverage, Coverage, Completeness,
      Deliverable; sortable by the example's keys with `aria-sort`; missing values sort last; the
      count reads "N of M runs · K issuers"; the example's empty state with Reset.
- [ ] **Selected-run detail:** name, id and title; summary; Scope & open questions (gaps); dated
      ratings; the completeness box ("Not assessed" wording from the example); the six-metric grid
      with value, unit, period and basis; Deliverables & revision history; Sources & definitions
      with path, line and quote. Actions: Open run (Overview), Open report (in-app Reports), or Open
      primary handoff.
- [ ] **Style:** the example's composition with the app's tokens from `screen.css`; no second palette,
      no new font or asset. Narrow screens stack panel, table (horizontal scroll) and detail.
- [ ] All text goes through `textContent` or `esc`; nothing from a record is parsed as HTML.

### Task L3: Tests

**Files:** create `web/screening-dom.test.cjs` (from `examples/issuer-library/test_dom.cjs`); modify
`web/library-workspace.test.cjs`, `web/screens.test.cjs`, `designs/browser_check.py`.

- [ ] Hand-written expectations first, by someone other than the code's author, from
      `examples/issuer-library/catalog.json` and the served records: the four runs with metrics,
      their leverage and coverage values and bases, and the row (59) and issuer counts.
- [ ] jsdom: each filter, a blank bound never matching, the basis filter, sorting with missing last,
      selection and detail, Reset, keyboard operation of the sort buttons and issuer choices, labels,
      hostile record text rendered inert, the empty and unreadable states.
- [ ] Browser walk (`browser_check` real workspace, Chromium and the walk's second engine): the
      Library lists every run folder and delivery row; a filter and a sort change the rows; a row's
      detail opens; Open run reaches the Overview; Open report opens the in-app report; fitted
      screens at 1366×768 and 390×844; no console, page, HTTP or exception fault.
- [ ] `validate.py quick` and `validate.py browser` pass; `uv run python tools/quality_gate.py` passes.

### Task L4: Open it for the owner (Checkpoint L)

**Files:** modify `apps/issuer-library/README.md`, Help in `web/views.js`,
`examples/issuer-library/README.md`, `VERIFICATION.md`.

- [ ] README "Run from source" block, tested as written: build with the Go version `go.mod` names,
      then

      ```sh
      cd apps/issuer-library
      ISSUER_LIBRARY_PYTHON="$(cd ../.. && pwd)/.venv/bin/python" \
      ISSUER_LIBRARY_ENGINE_ROOT="$PWD/engine" \
      go run . --workspace "$(cd ../.. && pwd)"
      ```

      after `uv sync` at the repository root. It opens the browser on the signed-in Library. The Windows
      package needs neither variable.
- [ ] Help describes the screening controls, that missing values never match, and that most
      retained runs have no recorded metrics or completeness yet.
- [ ] The example's README says its screening now lives in the app's Library; the example stays as
      the approved reference and its tests keep running.
- [ ] Screenshots at 1440×900 (desktop) and 390×844 (phone), deviceScaleFactor 2, sent to the owner
      with the launch steps.
- [ ] **Checkpoint L:** offline gates above, confidence-review and rewrite-tournament (post-edit) on
      `libraryView`, the row and detail renderers and the store join; one `VERIFICATION.md` entry
      labelled "offline: retained workspace; no provider called"; **the owner opens the app and
      accepts the Library screen.**

## Done when

- The app's Library screen is the example's screening design, on the served records, inside the
  app's rail; every run folder and delivery row is listed and reachable.
- Run rows open their Overview and reports open inside the app.
- The node, jsdom and browser tests above pass, with no fault.
- The owner has launched it, used it and accepted it.
