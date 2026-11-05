# Issuer Library Reader Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. `AGENTS.md` forbids subagents here, so run every task in this session. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the Issuer Library read as a credit-analysis product (summary first, charts, plain names) without changing what the analytical methods conclude.

**Architecture:** Methods and module boundaries stay. Each handoff stays the Markdown record and gains a short reader section and fixed chart tables, written by the module and checked in its existing repair loop. The app and report preview change presentation only; delivery never writes analysis.

**Tech Stack:** Python 3.13 (stdlib, pydantic), Go, plain browser JavaScript; jsdom and Playwright as test-only tools kept outside the repo's dependencies.

**Spec:** the Decisions section below. No separate spec file, per the one-record rule in `AGENTS.md`.

## Decisions

| Finding (measured 2026-11-05) | Decision |
|---|---|
| 0 of 15 narrative reports contain a figure; only the 3 HTML Model deliveries do | Launcher runs publish the CP-1 chart strip |
| `cpos_launch.py:247` omits every chart section | Emit chart routes when CP-1 is in the run |
| 16 app visuals are pinned to line numbers in retained files | Derive charts from fixed tables in any run |
| No table header recurs in every run of any module tested (sample mixes issuers and method versions) | Fix the headers of chart tables only |
| Findings sections hold 2,996 module codes, 1,159 table IDs and 3,383 short references across 116 handoffs | Show names for module codes; mute references; ban all three from new reader sections |
| 116 of 122 handoffs share the same six `##` sections | Old runs get a usable fallback without a rerun |
| CP-8's `run_comparison` (`owners/cpos.py`) already compares complete deliverables | CP-8 is the quality gate for the live proof |
| Only 8 of 41 retained runs have curated calls and visuals, and only those 8 are in the jsdom fixture | Unit tests use the fixture; the browser check walks every retained run |

**Rejected:** rebuilding modules around screens (breaks comparison with earlier runs and rewrites validated methods), and an AI summary at delivery (breaks "delivery must not invent").

**Surfaces.** *Reader surfaces* never show module codes: Library, Summary, Analysis sections except Technical audit, Calendar, Deliverables list, New run review. *Evidence surfaces* keep exact codes: Evidence tab, Technical audit, source inspector, Built from, Run activity, Help's visualisation coverage, Settings issues. URLs keep codes so existing deep links work.

## Global Constraints

- No subagents. No paid provider call except Task 10, after separate owner approval. Gates remove provider keys from their environment.
- `runs/` and `deliverables/` never change; a gate checks this. The live proof adds one new run folder and is excluded by name.
- No edits to `docs/reuse/selected-methods/**` or `prompts/**`. Reader rules live in the launcher's instructions.
- Expected values are hand-written, never produced by the code under test, and frozen before the code or paid run they check.
- Missing is never zero. `Not supplied: <reason>` stays a visible gap. No new score, rating or aggregate.
- New reader text comes from the module that did the analysis. Nothing downstream rewrites it.
- No new dependency. Excel stays input-only.
- Users are on Windows, so Edge and Chrome matter. Any result seen only on macOS says so.
- Work on `claude/reader-update`, branched from `main` after PR #2 and PR #3 merged. Approving this plan authorises local commits; pushing and each PR need the owner's go-ahead. One PR per phase, at most 800 changed lines excluding fixtures.
- Each checkpoint appends one short entry to `VERIFICATION.md`. No other review files.

## Validation Schedule

| When | Command or action | Passes when |
|---|---|---|
| Every task | The focused tests the task names | New test seen failing for the stated cause, then exit 0 |
| Every commit | `python3 apps/issuer-library/validate.py quick` | Exit 0 |
| **Checkpoint A** (after Task 5) | `validate.py full`, then `validate.py browser`, then Windows check | All exit 0; owner accepts screens |
| **Checkpoint B** (after Task 9) | Same, plus `validate.py suite --known <baseline failures>` once | No failure beyond the baseline; Windows smoke passes |
| **Checkpoint C** (after Task 10) | Frozen key and CP-8 comparison | The decision table in Task 10 |

**Windows check (owner, on a Windows machine):** extract `Issuer-Library-amd64.zip`, run `Smoke-test.ps1`, open the app in Edge, then open a TDG run, its Summary, one Analysis page and one report.

**Stop rules:** a failing gate stops the next task. Two failed fix rounds on one defect go to the owner with both outcomes. Never loosen a test to pass; where a task deliberately changes behaviour an old test pins, the task names that test and the new assertion.

**Baseline failures:** `validate.py suite` on merged `main` (`ab46df7`) gives the list Checkpoint B compares against. Shards change test order, so compare shard runs only.

## Review Focus

1. **A retained run with no reader section:** Summary still opens, shows each module's first finding, and states no bottom line was stored rather than promoting a finding to a call (Task 4).
2. **A non-USD issuer such as Erste:** monetary charts show gaps with the reason, never values labelled US$m (Task 8).
3. **A stopped run where only one module was accepted:** Summary shows that module alone and invents nothing for the rest (Task 9).
4. **Hostile or malformed reader text in a workspace file:** stays inert text; a malformed section leaves the handoff readable and is listed in Settings issues (Task 9).
5. **A small Windows window (1280×600, 1536×730):** bottom line, confidence and main limitation stay visible and unclipped, with no page overflow (Task 4).

---

## Phase 0: make validation repeatable

### Task 1: Validation command and browser check in the repo

The browser check lives only in this session's scratchpad, so it would be lost.

**Files:**
- Create: `apps/issuer-library/validate.py`, `apps/issuer-library/designs/browser_check.py`, `apps/issuer-library/designs/fake_engine/bridge.py`, `apps/issuer-library/designs/fake_engine/store.py`
- Modify: `VERIFICATION.md`

**Interfaces:**
- Produces: `python3 apps/issuer-library/validate.py {quick|full|browser|suite}`, printing `PASS|FAIL <gate>` per line and exiting non-zero on any failure. Reads `FW_PYTHON`, `ISSUER_LIBRARY_JSDOM` and `FW_PLAYWRIGHT_PYTHON`, and fails by name if one it needs is unset.

Gates:
- `quick`: `retained` (`git status --porcelain -- runs deliverables ':(exclude)runs/cpos-reader-live-*'` is empty), `fixture` (`python3 -B designs/build.py`), `node` (the four `.test.cjs` files), `python` (`tests/test_issuer_library_store.py tests/test_cpos_app.py tests/test_cpos_launch.py tests/test_cpos_handoffs.py tests/test_cpos_comparison.py tests/test_markdown_delivery.py tests/test_pathway_handoff_charts.py`).
- `full`: `quick`, then `go test -race ./...`, `go vet ./...`, `GOOS=windows GOARCH=amd64 go vet ./...`, `GOOS=windows GOARCH=amd64 go test -c -o <temp> .`, Windows amd64 and arm64 builds to a temp folder, and `ruff check` on the changed Python files.
- `suite`: every test outside `tests/test_method_*`, split by file into shards; passes when no failure is new and every shard ran.
- `browser`: build the binary to a temp folder, then run `browser_check.py chromium firefox` under `FW_PLAYWRIGHT_PYTHON`, including 1280×600 and 1536×730 overflow checks.

- [ ] **Step 1:** Copy the scratchpad `e2e/check.py` and `e2e/engine/*` to the new paths. Replace absolute paths with `Path(__file__).parents[3]`, the env vars above and `tempfile.mkdtemp()`.
- [ ] **Step 2:** Write `validate.py` with `subprocess`, removing `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY` from each child's environment.
- [ ] **Step 3:** Prove the guard fails: create `runs/_probe`, run `validate.py quick`. Expected: `FAIL retained`, exit 1. Delete the probe.
- [ ] **Step 4:** Run `quick`, `full`, `browser`. Expected on PR #2's head: Node 88 passed; Python gate 0 failures; browser 82 of 82 per browser.
- [ ] **Step 5:** Start `validate.py suite` on a clean checkout of merged `main` in the background; its `failures.txt` is the baseline.
- [ ] **Step 6:** Commit: `Add one command for the issuer library's validation gates`.

---

## Phase 1: reader layer over retained runs (no paid calls, no method change)

### Task 2: Plain names in reader text

**Files:**
- Modify: `apps/issuer-library/web/screen.js:40-56` (`rich`, `aliases`), and the callers that render headings (`screen.js:134`, `views.js:199`); `apps/issuer-library/web/screen.css`
- Test: `apps/issuer-library/designs/design.test.cjs`

**Interfaces:**
- Produces: `exact(value) -> html` (today's `rich`); `rich(value) -> html` (`exact` plus names); `namedText(text) -> text`; `withCodes(fn)`, which makes `rich` behave as `exact` while `fn` runs, and is used by the inspector, Technical audit and other evidence surfaces.

Rules: match `\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])` so file names such as `CP-2-integrated.md` stay intact. Known code becomes `<abbr class="module-ref" title="CP-2G">Forward credit model</abbr>`. Unknown code stays as written. Build aliases from the existing map, the catalogue's `aliases` column, and `CP-MEMO` → `Credit memo`. Wrap table IDs (`\bT\d+[A-Z]?\.\d+\b`) and short references (`\b[FKCS]\d{1,4}\b`) in `<small class="ref">`, muted but unchanged.

- [ ] **Step 1: Write the failing test**

```js
test('Module codes read as names on reader surfaces and stay exact in evidence',()=>{
  const dom=fixture(),w=dom.window,text=h=>norm(JSDOM.fragment(h).textContent);
  assert.equal(text(w.eval(`rich("CP-2G's assumed 20% earnings reduction")`)),"Forward credit model's assumed 20% earnings reduction");
  assert.equal(JSDOM.fragment(w.eval(`rich("CP-2G")`)).querySelector('abbr').title,'CP-2G');
  assert.equal(text(w.eval(`rich("CP-2F and CP-PARSE")`)),'Rates, FX & hedging and Source readiness');
  assert.equal(text(w.eval(`rich("CP-XYZ note")`)),'CP-XYZ note');
  assert.equal(text(w.eval(`rich("see CP-2-integrated.md")`)),'see CP-2-integrated.md');
  assert.equal(text(w.eval(`withCodes(()=>rich("CP-2G"))`)),'CP-2G');
  dom.window.close();
});
```

- [ ] **Step 2:** Run `node --test --test-name-pattern="Module codes" apps/issuer-library/designs/design.test.cjs`. Expected: FAIL on the first assertion.
- [ ] **Step 3:** Implement the interfaces above and wrap evidence surfaces in `withCodes`.
- [ ] **Step 4:** Change `design.test.cjs:20` ("Every retained body block is reachable") to restore each `abbr` to its `title` before comparing. This is stricter: it proves only codes changed, and every retained character still appears.
- [ ] **Step 5:** Add a fixture test: for every output, every section except `audit` renders with no known module code outside an `abbr` title.
- [ ] **Step 6:** Add to the full workspace walk in `browser_check.py`: for every retained run, the first Analysis page's visible text has no known module code.
- [ ] **Step 7:** Run `validate.py quick` and `validate.py browser`. Expected: exit 0. Commit: `Show module names instead of codes in reader text`.

### Task 3: Navigation by credit question

**Files:**
- Modify: `apps/issuer-library/web/screen.js:30-36` (`groups`) and `:318` (page title); `apps/issuer-library/web/views.js:20` (subtitle), `:66` (`moduleHead`), `:305` (help), `:333` (tabs); `apps/issuer-library/web/actions.js:65` (review list)
- Test: `apps/issuer-library/designs/design.test.cjs`, `apps/issuer-library/web/new-run.test.cjs`

```js
const groups=[
  ['Business and evidence',[['CP-0','Source readiness'],['CP-1A','Business & governance'],['CP-DR','Research questions']]],
  ['Financial performance',[['CP-1','Financial foundation'],['CP-1B','Earnings changes'],['CP-L10','Financial change screen'],['CP-1D','Earnings quality'],['CP-1C','Peer benchmark']]],
  ['Liquidity and refinancing',[['CP-2D','Liquidity'],['CP-3C','Refinancing & LME']]],
  ['Outlook and downside',[['CP-2','Fundamental credit'],['CP-2A','Downside'],['CP-2G','Forward credit model'],['CP-2E','Rates, FX & hedging'],['CP-2H','Ratings & triggers']]],
  ['Capital structure and legal',[['CP-4','Legal & covenants'],['CP-4C','Recovery & fulcrum']]],
  ['Relative value',[['CP-3','Security selection'],['CP-3D','Market-implied risk']]],
  ['Decision and review',[['CP-6','Committee decision'],['CP-5','Evidence validation'],['CP-8','Deliverable comparison']]]
];
```

- [ ] **Step 1: Write the failing tests:** tabs read exactly `['Summary','Analysis','Calendar','Deliverables','Evidence']`; `.module-title` has no code in its text and carries it in `title`; the new-run review list has no code in its text; `/` search for `CP-2G` still finds "Forward credit model"; `#CP-2/...` deep links still open.
- [ ] **Step 2:** Run them. Expected: FAIL on the tab labels.
- [ ] **Step 3:** Change the files listed. Keep route IDs `W-Overview` and `CP-*`. Library's Contains-module filter shows names only.
- [ ] **Step 4:** Update tests that pinned the old `Modules` and `Overview` labels; assert the new labels, removing nothing else.
- [ ] **Step 5:** Run `validate.py quick`. Expected: exit 0. Commit: `Organise the app by credit question`.

### Task 4: Summary screen for any run

**Files:**
- Modify: `apps/issuer-library/web/views.js:311`, `apps/issuer-library/web/screen.css`
- Test: `apps/issuer-library/designs/design.test.cjs`, `apps/issuer-library/designs/browser_check.py`

**Interfaces:**
- Produces: `moduleSummary(outputId) -> {kind:'summary'|'call'|'finding', text, line, confidence?, limitation?} | null`; `firstFinding(outputId) -> {text, line} | null` (first text block after `Findings`, before `Calculations`); `summaryView(context) -> html`; `CALL_ORDER=['CP-6','CP-2','CP-3','CP-2D','CP-1','CP-0']`. Task 9 adds the `summary` kind.

Page, top to bottom:
1. **Lead band** (`.summary-lead`): first `summary` or pinned `call` in `CALL_ORDER`, then any other in `groups` order, naming its module and linking its source. A `finding` never leads. With none: `No bottom line is stored for this run. Read the findings below.` The band is never clamped.
2. **Charts:** this run's existing chart visuals (`paired`, `peers`, `bars`, `bridge`, `waterfall`, `paths`, `hedges`), at most four.
3. **One card per credit question** with outputs in this run; inside it, one `[data-module="<code>"]` entry per module: name, its summary, call or first finding, a source link. Clamp with CSS `-webkit-line-clamp:4`; the complete text stays in the DOM.
4. **Deliverables** built from this run.

Known limit: on old runs a first finding can open mid-argument, because those handoffs were not written for this view. New runs fix this through Task 7; old text is never rewritten.

- [ ] **Step 1: Write the failing tests** with these keys, hand-checked against `runs/tdg-002/CP-2-attempt-2.md:132` and `runs/tdg-002/CP-1A-attempt-3.md:62`:

```js
test('Summary leads with the stored call and never promotes a finding',()=>{
  const dom=fixture('W-Overview/overview?c=tdg-002'),d=dom.window.document;
  const band=norm(d.querySelector('.summary-lead').textContent);
  assert.ok(band.includes('Overall, TransDigm presents an established but not fully assessable business profile'));
  assert.ok(band.includes('Fundamental credit'));
  assert.ok(d.querySelector('.summary-lead [data-evidence$=":132"]'));
  assert.ok(norm(d.querySelector('[data-module="CP-1A"]').textContent).includes('Control rights, economic interest, shareholder concentration and private-equity sponsor status are therefore unestablished'));
  dom.window.close();
});
```

Also, on the uncurated workspace set up by the test at `design.test.cjs:682`: `.summary-lead` holds exactly the fallback sentence, has no `.call-quote`, and at least one card shows a first finding.
- [ ] **Step 2:** Run them. Expected: FAIL (`.summary-lead` is null).
- [ ] **Step 3:** Implement the interfaces and CSS.
- [ ] **Step 4:** Add a fixture test: each card's text is a block of its own handoff. Add to the full workspace walk in `browser_check.py`: Summary opens for every retained run with no console error and no known module code in its visible text.
- [ ] **Step 5:** Add to `browser_check.py`: at 1280×600 and 1536×730, `.summary-lead` is fully visible when scrolled to and the page has no horizontal overflow.
- [ ] **Step 6:** Run `validate.py quick` and `validate.py browser`. Expected: exit 0. Commit: `Open each run on a credit summary`.

### Task 5: Plain names in the report preview

**Files:**
- Modify: `apps/issuer-library/web/report-adapter.js`
- Test: `apps/issuer-library/web/report-renderer.test.cjs`

**Interfaces:**
- Produces: `MODULE_NAMES` in the adapter, and a text-node walk over `#view-root` that skips `#inspector`, reruns from the existing `MutationObserver`, and only writes when a code is present, so it cannot loop.

- [ ] **Step 1: Write the failing tests:** on a retained snapshot, `#view-root` text contains no known module code; `3.14x` and `Analyst Interpretation` remain; `#inspector` content keeps codes; `original.html` bytes are unchanged; `MODULE_NAMES` deep-equals the names in `screen.js`, so the two lists cannot drift.
- [ ] **Step 2:** Run them. Expected: FAIL on the first assertion.
- [ ] **Step 3:** Implement. Put each replaced code in the parent element's `title`.
- [ ] **Step 4:** Run `validate.py quick`. Expected: exit 0. Commit: `Show module names in the report preview`.

### Checkpoint A

- [ ] Run `validate.py full`, then `validate.py browser`. Expected: exit 0.
- [ ] Run confidence-review and rewrite-tournament (post-edit, inline) on `rich`, `summaryView` and the adapter's text walk. Repair confirmed defects with a test first.
- [ ] Rebuild the zips: copy `windows-amd64/` and `windows-arm64/` from the Codex tree's ignored `artifacts/issuer-library/` into this tree's, then run `PATH=/usr/local/go/bin:$PATH python3 -B packaging/build.py` from `apps/issuer-library`. Expected: it prints `Reusing the pinned Python engine` for both, so nothing downloads.
- [ ] Owner runs the Windows check. Until then, record the result as macOS only.
- [ ] Send the owner screenshots of Summary, an Analysis page and a report for TDG. Ask: can you find leverage, liquidity and the main limitation, and does anything read as an internal code?
- [ ] Append the `VERIFICATION.md` entry. Open the Phase 1 PR when the owner agrees.

---

## Phase 2: reader section and charts in new runs (offline, synthetic fixtures)

### Task 6: Reader section validator

**Files:**
- Create: `src/deploy_workflow/reader_summary.py`, `tests/test_reader_summary.py`

**Interfaces:**
- Produces: `reader_issues(text: str) -> tuple[str, ...]`, empty when valid, and the constants below.

```python
BOTTOM_LINE_WORDS, LIMITATION_WORDS, FINDING_WORDS, MAX_FINDINGS = 40, 30, 30, 5
CONFIDENCE = ("High", "Medium", "Low", "Not assessable")
```

Required section, one row in the first table, 1 to `MAX_FINDINGS` rows in the second:

```markdown
## Reader summary

| Bottom line | Confidence | Main limitation |
| --- | --- | --- |

| Finding | Creditor impact | Confidence |
| --- | --- | --- |
```

- [ ] **Step 1: Write the failing tests** as one `parametrize` over a hand-written valid handoff and these mutations, each asserting one issue naming the cause: section missing; bottom line of 41 words; six findings; `Moderate` confidence; empty limitation; `CP-2G`, `T4.3` or a 16-character hex string in the section; `3.1` where the rest of the handoff has only `3.14`; `3.14` where the rest has only `13.14`. The unchanged handoff returns `()`, and so does a `Not assessable` row with a limitation.
- [ ] **Step 2:** Run `pytest tests/test_reader_summary.py -q`. Expected: FAIL at import.
- [ ] **Step 3:** Implement with `re` only. Number tokens are `\d[\d,]*(?:\.\d+)?`, searched with digit boundaries in the handoff outside this section.
- [ ] **Step 4:** Run it. Expected: all pass. Commit: `Check the reader section of a handoff`.

### Task 7: Launcher asks for it and refuses without it

**Files:**
- Modify: `src/deploy_workflow/owners/cpos_launch.py` (`_instructions`, `checker`)
- Test: `tests/test_cpos_launch.py`, `tests/test_markdown_delivery.py`

**Interfaces:**
- Consumes: `reader_issues` from Task 6.
- Produces: `READER_SECTION_RULES`, a string added to the instructions after the rejection list. Its text must state: write this section after the analysis, immediately before `## Findings`; restate conclusions already in the handoff in plain language for a credit analyst; add no new fact, figure or conclusion; use no module codes, table IDs or hashes; every number must match the handoff exactly; the two table headers, the limits and the confidence words.

- [ ] **Step 1: Write the failing tests:** instructions contain `## Reader summary` and the method text is still verbatim with its sha256; `checker` returns an issue naming the reader section for a handoff without it; a valid handoff passes; `markdown_files` delivers a handoff with the section, and the bottom line appears unchanged in `report-view.json`.
- [ ] **Step 2:** Run them. Expected: FAIL on the instructions assertion.
- [ ] **Step 3:** Add the rules and extend `checker`. Update the existing synthetic handoffs in `tests/test_cpos_launch.py` and `tests/test_cpos_app.py`, adding the section and removing no assertion.
- [ ] **Step 4:** Run `validate.py quick`. Expected: exit 0. Commit: `Require a reader section from launcher runs`.

### Task 8: CP-1 chart strip from launcher runs

**Files:**
- Modify: `src/deploy_workflow/owners/cpos_launch.py:243-274` (`_layout`), `_instructions` (selector text), `checker`
- Test: `tests/test_cpos_launch.py:279`, `tests/test_pathway_handoff_charts.py`

**Interfaces:**
- Consumes: `STRIP_FIGURES` from `markdown_delivery`; `MarkdownRoute` with `kind="chart"`, `orientation="period-rows"`.
- Produces:

```python
CHART_TABLES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "S.1": ("Chart data: leverage", ("Total debt / EBITDA", "Net debt / EBITDA"), "x"),
    "S.2": ("Chart data: interest cover", ("EBITDA / cash interest",), "x"),
    "S.3": ("Chart data: liquidity", ("Cash", "Undrawn committed facilities"), "US$m"),
    "S.4": ("Chart data: debt maturities", ("Debt maturing",), "US$m"),
}
```

- Also produces: `chart_issues(text: str, route: MarkdownRoute) -> tuple[str, ...]`, called by `checker`.

Each table sits under its `### <heading>` inside `## Findings`, headed `| Period | <value columns> | Reporting unit | Basis and limitation |`. Value cells are plain numbers or `Not supplied: <reason>`. A non-USD or non-million issuer writes `Not supplied: reported in <unit>` in monetary cells.

- [ ] **Step 1: Write the failing tests** using a hand-written synthetic Northbridge handoff, labelled synthetic:

```python
strip = next(b for b in report.blocks if b.block_id == "model-chart-strip")  # credit_snapshot
figures = strip.figures
assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4"]
assert [m.value for m in figures[0].chart.marks] == [Decimal("4.20"), Decimal("3.85"), Decimal("3.60"), Decimal("3.25")]
assert [m.value for m in figures[3].chart.marks] == [Decimal(500), None, Decimal(1250)]
assert figures[3].chart.marks[1].ref_id.startswith("G")
```

Also: `3.85x` in a cell is refused; a numeric row with `EUR m` as its unit is refused by `chart_issues`; a blank basis is refused; one missing table is refused; the all-gaps non-USD handoff passes and its marks are all `None`; a run without CP-1 still lists the chart block in `omitted`; `yield-against-maturity` stays omitted.
- [ ] **Step 2:** Run them. Expected: FAIL because `_layout` emits no chart routes.
- [ ] **Step 3:** In `_layout`, for a chart block in `STRIP_FIGURES` other than `yield-against-maturity`, when CP-1 is in the run, emit one route per figure. Dedupe block IDs with `dict.fromkeys` in `_layout` and in `checker`'s `own` layout. Selector text states the exact table header. Change the scope sentence to: `The HTML Model and calculation JSON are not published by this launcher.`
- [ ] **Step 4:** Change `tests/test_cpos_launch.py:279` from `"maturity-wall" in prepared.omitted` to `not in`, and add `("maturity-wall", "CP-1", "Chart data: debt maturities", "chart")` to `COVENANT_ROUTES`. This is the requested behaviour change. Add a CP-1-less case that keeps the old assertion.
- [ ] **Step 5:** Run `validate.py quick`. Expected: exit 0. Commit: `Publish the CP-1 chart strip from launcher runs`.

### Task 9: App reads reader sections and chart tables from any run

**Files:**
- Modify: `apps/issuer-library/engine/store.py` (`collect_runs`; new `reader_fields`), `apps/issuer-library/web/views.js` (`moduleSummary`, `summaryView`), `apps/issuer-library/web/screen.js:188-199` (`renderContent`)
- Create: `apps/issuer-library/designs/reader-fixture/CP-1.md` (synthetic, labelled in its first line)
- Test: `tests/test_issuer_library_store.py`, `apps/issuer-library/designs/design.test.cjs`, `apps/issuer-library/designs/browser_check.py`, `apps/issuer-library/designs/fake_engine/bridge.py`

**Interfaces:**
- Produces: `reader_fields(sections) -> {"summary": {"bottomLine", "confidence", "limitation", "findings", "line"} | None, "charts": [{"figure", "title", "unit", "table": int, "columns": [int]}], "issue": str | None}`, merged into each output record and fail-open per output into the existing issues list.
- Uses: `comparisonChart(module, {kind:'bars', title, table, columns, unit})`, which already gives source links and shows `Not available` for gaps.

- [ ] **Step 1: Write the failing tests:** with the fixture, `reader_fields` returns the hand-written values; Summary's band shows its bottom line, confidence and limitation; chart labels and values match the fixture's table; a gap row shows `Not available`, not `0`; `<img onerror>` in a finding stays text; a malformed section returns `summary: None`, a named `issue`, and the handoff still renders; a stopped run with only CP-0 shows one card and no others.
- [ ] **Step 2:** Run them. Expected: FAIL (`reader_fields` missing).
- [ ] **Step 3:** Implement. An output with a reader summary opens on it. Keep all pinned curated views unchanged.
- [ ] **Step 4:** Extend `fake_engine/bridge.py` so a fake run writes the fixture, and add a browser check: New run → report shows four figures → Summary shows the bottom line. Label this flow synthetic in its output.
- [ ] **Step 5:** Run `validate.py quick` and `validate.py browser`. Expected: exit 0. Commit: `Show reader sections and chart tables for any run`.

### Checkpoint B

- [ ] Run `validate.py full` and `validate.py browser`. Expected: exit 0, and all retained runs still pass.
- [ ] Run once: `validate.py suite --known <baseline failures.txt>`. Expected: no failure beyond the baseline.
- [ ] Run confidence-review and rewrite-tournament (post-edit, inline) on `reader_issues`, `_layout`, `reader_fields` and `summaryView`. Repair confirmed defects with a test first.
- [ ] Rebuild the zips. Owner runs `Smoke-test.ps1` on Windows; it makes no model call.
- [ ] Append the `VERIFICATION.md` entry, labelled synthetic. Open the Phase 2 PR when the owner agrees.

---

## Phase 3: live proof (paid, separate owner approval)

### Task 10: One live comparison

**Files:**
- Create: `cases/reader/tdg-expected.json`
- New run folder: `runs/cpos-reader-live-001`
- Modify: `VERIFICATION.md`

- [ ] **Step 1: Freeze the key.** Read the chart values for the `credit_snapshot` case (as of 2024-09-30) from `runs/cpos-launch-live-002/source-text/TDG_2024-09-30_10-K_0001260221-24-000083_tdg-20240930.htm.jsonl`, not from any handoff. Record value, unit, period, page and whether each is stated or hand-calculated. Commit before any paid call.
- [ ] **Step 2: Locate the issuer folder.** Find the original TDG filing folder. It is correct only when an offline `prepare` over it gives the same source sha256 values as `runs/cpos-launch-live-002/workflow.json`.
- [ ] **Step 3: Ask the owner to approve**, with these details: that folder; modules CP-0, CP-1 and CP-1A; config `sol-medium` (gpt-6.1-sol, medium) and `runs/cpos-launch-live-002/context.json` for comparability; maximum USD 12 (that run's cap was USD 11.71, and it spent USD 0.93); plus one CP-8 comparison by `run_comparison` against that run's delivery, with its own stated maximum. The key comes only from the launching environment. Without a clear yes, stop here.
- [ ] **Step 4: Run through the app's New run** so the launcher and interface are both exercised. Do not retry automatically.
- [ ] **Step 5: Check:** every chart mark equals the frozen key or is a stated gap; Summary numbers match the handoff; record spend and repair rounds per module.
- [ ] **Step 6: Run the CP-8 comparison** and read its answer on values, periods, assumptions, conclusions, sources, limitations and output scope.
- [ ] **Step 7: Apply the decision table** and record the outcome. This case proves only this dated TDG scope, and the entry says so.

| Outcome (Checkpoint C) | Action |
|---|---|
| All checks pass and CP-8 finds no unexplained material change | Write the Phase 4 plan |
| Spend above USD 1.86 (2× the earlier run), or more than 2 repair rounds in a module | Simplify the reader rules, retest offline, ask before any rerun |
| CP-8 finds a lost value, conclusion or limitation | Stop. Move the reader section to a separate final turn in the module, retest offline, ask before any rerun |
| A chart cannot be filled because no module is responsible for that fact | Take the method-scope question to the owner, the one case for changing a module's responsibilities |

---

## Later (separate plan after Checkpoint C)

The next charts are S.5, CR.1 covenant headroom, CR.2 liquidity bridge, CR.3 refinancing need, and RV.1 yield. `MarkdownRoute.figure_id` allows only S.1 to S.4 and RV.1 today, so the CR figures need a wider route. Their shape depends on what Task 10 shows.

## Not in this plan

- Rewriting methods or module boundaries.
- Adding reader sections to old runs, which would need paid reruns and would alter retained evidence.
- Publishing the HTML Model from the launcher, resuming a stopped run from the app, or adding CI.

## Not verified by this plan until the named step

- **Windows behaviour:** Checkpoints A and B, run by the owner.
- **Live model compliance and cost with the new rules:** Task 10.
- **Whether analysts find this faster and clearer:** the owner's answers at Checkpoint A only; there is no wider user testing.
