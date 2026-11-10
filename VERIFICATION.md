# Verification record

Keep one running record here. A pass applies only to the stated scope. Preserve
earlier run artifacts; record a new attempt when instructions or outputs change.

The [current remaining-module record](runs/cpos-sol-remaining-20261105/verification.json)
contains the settled CP-6 timeout cost, the corrected TDG annual publication, the
live CP-8 comparison and checks of the five broader report bundles. The older
entries below retain their historical case scope.

Older entries are in [docs/VERIFICATION-ARCHIVE.md](docs/VERIFICATION-ARCHIVE.md), verbatim and in their original order; new entries go here.

## 2026-11-10 — pr_size: an edited copy counts against the merge base when the base holds it (R-PRSIZE-1, branch `sb3-prsize`)

- **Rule:** in `tools/pr_size.py`, an `edited <path>` entry whose file exists at `git merge-base <base> HEAD` counts its numstat for merge-base...HEAD; one absent there counts its whole drift from the source revision, with the binary fallbacks as before. Plain copies keep the byte-identity check; fixtures, lockfiles and binaries stay excluded. The limit stays 800; `tools/copied-from.txt` stays the provenance record.
- **Reason:** counting every edited file by its drift from the source recounted history. A later PR touching `cpos_launch.py` would have recounted the ~720 lines already counted and reviewed in #53, whose own count was 797/800.
- **Key:** `SDD/prsize-key/scenarios.json` (sha256 `01ac9082...e8`), 19 scenarios replayed in `tests/test_pr_size.py`; 19/19 pass. Before the change 7 failed with the key's "today" numbers (65, 85, 0, 860, 861, 100, 10). `edited_setup` no longer puts a file at base (scenarios 3 and 4); scenario 17 covers the old shape.
- **Not verified:** a diverged base other than the one in scenario 19; the CI run itself.

## 2026-11-10 — Plan 3 Task 11a: pro forma instructions, checker and Primary default CP-1D (PR #53, branch `claude/sb3-plan-3-11a`)

- **Scope:** offline, synthetic. Instruction text, a structural checker and default modules in `src/deploy_workflow/owners/cpos_launch.py`; no model run, no delivery change (Task 11b).
- **Key:** `tests/fixtures/primary-pro-forma/checker-cases.json`, 80 cases, frozen before the code by a key writer who wrote no checker code (byte-identical to final-workflow `8d22e84c`); 80/80 pass with the exact issue-category set per case. Task 10's key still passes.
- **Gates at `7f6a39dd`:** quality_gate 0; focused tests 437 passed; `validate.py quick` 0 (python 1595 passed, browser tests 610); `validate.py browser` 0 (86 passed); pr_size 797/800.
- **Review:** `mx-precise` PASS (H0 M0 L2 I2). Lows parked for the next fix batch: fenced-code reading (as in Task 10) and `_pro_forma_table` duplicating `_register`'s loop.
- **Finding:** the issuer-library app passes `modules=job["modules"] or None`, so an app run with no module selection gets the Primary default (pathway modules plus CP-1D).
- **Not verified:** any model-written handoff against these instructions or the checker (live check C2, paid, waits for the owner); report delivery of the tables (Task 11b).

## 2026-11-09 — Plan 3 live checks C1 and C1n: CP-4 Provisional review and Blocked control (branch `claude/sb3-plan-3-141ce3`)

- **Scope:** public proxy for a private primary deal, older source (2014), Mattress Firm Holding Corp. only; one live run per check; `sol-medium`, modules CP-0, CP-1, CP-4, cap USD 10 each; app runs through `apps/issuer-library/designs/live_check.py`. Keys frozen before the runs in `cases/live-mattress-firm-2014/{c1,c1n}/` (forecast by hand from `run_expectations.py` rules; literals from `cases/primary-proxy-mattress-firm-2014/expected.json`). Each run started only on the owner's go-ahead in the SB3 session.
- **C1** (build `aa433ad1`; run `web-8a674922fe6d56369000fc6e773b95f7`; USD 1.09882450): **criteria PASS** (required outputs: see the re-read below). CP-4 accepted, not Blocked; `DRAFT_LIMITATION` verbatim (CP-4.md:64); 18 of 24 keyed covenant terms match and are labelled Provisional; no document called executed. live_check exit 1 with 12 faults: 5 harness (status reader, flow_check rounding, rendered-text join), 2 product (390-px run-detail overflow, fixed by #50), 2 run Lows (CP-1 hand-rescaled ×1000 operands, values correct), 1 accepted forecast disagreement (CP-1 limited by CP-0), 2 aggregates.
- **C1n** (build `3c3b9254` = main `6522e5ed` + the case folders; run `web-f18789292a1712e2ebcb591a09816385`; USD 0.91672190): **criterion PASS** (required outputs: see the re-read below). CP-4.md:7 "Module Status: Blocked" with the method's Blocked message verbatim; the register lists only the two filings CP-4 read, with no legal or offering document, and nothing was invented. live_check exit 1 with 20 faults: 14 harness (status reader needs the exact phrase and misses same-line sentences, `handoff_outcome.py:89-90`; CP-1 status window `:95`; flow_check rounding beyond 6 dp, `flow_check.py:76`), 4 run Lows (hand rescaling and percent display, values correct), 2 aggregates. An accepted Blocked handoff that goes on to delivery is allowed, not a fault.
- **Assessment:** `mx-precise`, read-only, against the frozen keys; each harness fault has a probe. Lead ruling R-SB2-1e: after SB2's harness PR merges, both retained runs are re-read offline on copies (no provider call) and this record is updated. No paid rerun.
- **Re-read 2026-11-10 (ruling R-SB2-1e), offline on copies at `7d4e9979` (after #55, #56), no provider:** both runs now pass their required outputs up to the accepted CP-1 forecast disagreement (CP-0 rates CP-1 Ready with limitations) and run Lows. C1: CP-0 no longer a finding, CP-4 reads limited as forecast, 3.84 cleared; report numbers 11 and 83 cleared under the new cell-separated reading (probe `report_numbers_now.py`, file:// render, exit 0); the offline single-run browser walk on a C1 copy passes 72/72, with no 390-px overflow in chromium or firefox. Remaining: run Lows 10800 and 162600 (hand ×1000 rescaling). C1n: CP-4 reads will_refuse as forecast; the 12 long roundings and the two percent displays cleared; remaining run Lows 98400 and 116543. A full `live_check` rerun would still exit 1 on the CP-1 forecast item and the flow aggregate. Re-read by `mx-precise` with live_check's own functions; it confirms every claim in #56's notes.
- **Status:** C1 and C1n pass, with their actual scope; the remaining items are accepted (CP-1 forecast) or run Lows (values correct, arithmetic by hand instead of `calculate`).
- **Not verified:** the harness fixes themselves (SB2's PR); firefox rendering of the report numbers; the "New records" output (marked not applicable before Stage 2); term matches beyond the key's quoted text; that C1n should have stopped at CP-4 rather than deliver (the plan does not say).

## 2026-11-09 — Phase 0: network-path check (Task 0.1)

- **Scope:** one work PC; the company Python `C:\Program Files\Statestreet\Python313\pythonw.exe` with `-I -B -X utf8`; the check folder built by `apps/issuer-library/packaging/network_check.py` from PR 0-A (#4) head `d47bd306` (merged as `460b696f`), copied to the network share and opened by its UNC path. Real share and real work PC, not synthetic.
- **Result:** `PASS`, with `pydantic_core.__file__` starting with `\\` (owner's report in chat, 2026-11-09: "PASS from \\"). The compiled `pydantic_core` (`cp313-win_amd64`) loaded from the share, and uvicorn served a one-route FastAPI app whose `/health` answered over loopback.
- **Consequence:** Phase 2 follows spec §6.1 as designed. Task 2.3 (local-copy fallback) is not needed, and Owner decision 5 does not arise.
- **Deviation:** the folder packs 14 wheels, not the plan's 13. `opentelemetry-api` 1.45.2 was added because fastapi 0.162.0 imports it at import time (S0 ruling R1, confirmed by the lead's whole-branch review).
- **Reviews:** per-task `mx-precise`; lead's whole-branch review (`mx-architect`) APPROVE; its Low finding (a server-thread crash lost its cause under `pythonw`) was fixed test-first before the owner's run.
- **Not recorded:** the import and first-response times and the Python patch version from the result file (the owner reported the verdict only); the result file itself is not in the repository.

## 2026-11-08 — Plan 3 Task 9: Mattress Firm 2014 public proxy case and frozen key (branch `claude/plan-3-primary-transactions-ee0e14`)

Scope: `cases/primary-proxy-mattress-firm-2014/`, labelled "public proxy for a private primary deal; older source (2014)",
Mattress Firm Holding Corp. (CIK 1419852) only. No code changed; no module or provider run.
- Sources: 11 EDGAR documents from 6 accessions, fetched 2026-11-08 at ≤1 request/s under the owner-approved identity
  (not stored), byte-identical, sha256 in `manifest.json`. All 11 pass the launcher's `_issuer_files` reader. The CIM and
  Marketing Term Sheet are not public, and the case says so.
- Finding: accession 0001104659-14-064027 is the Back to Bed asset purchase 8-K, not a Sleep Train merger 8-K. It is kept
  under that label; the Sleep Train merger 8-K is not in the case.
- Contexts: pre-closing (Primary, draft, ABL and TLB rows as the presentation states them) and after-closing
  (Secondary, executed). Both pass `load_context`. The manifest gives each check's documents, modules and cap (C1, C1n,
  C2, C1r, C3).
- Frozen key `expected.json`: hand-written from the documents by a key-writer subagent that writes no Tasks 10-11 code;
  207 cites, each snippet found on its cited line. It holds 24 covenant terms, 19 add-backs, 27 executed terms, the
  expected base EBITDA (194.5 on stated Adjusted EBITDA; 164.2-166.0 on stated EBITDA), and C1n Blocked. Executed terms
  that differ from the presentation are recorded, not reconciled: soft call 12 months, not 6; ECF steps fixed at
  3.00x/2.75x; no MFN sunset clause found.
- Review: mx-precise found 1 High and 3 Medium (an "executed" rule that contradicted the APA, the free EDGAR lane in C1n,
  no expected base, C1r status). One fix round; the scoped re-review passed. Probes are scratch-only.
- Gates exit 0: `tools/quality_gate.py` (0 lines in scope); `validate.py quick` (node 354, python 610 passed).
Not verified: no module has consumed the case or key; whether a run can reach EDGAR (the free lane would change C1n);
the EBITDA-path base is a range, because the documents leave the acquired "EBITDA" definitions unstated.
Carried verbatim from final-workflow `8d22e84c` by PR 1-P (#31): the gate counts and "No code changed" above describe that repository, not this one.

## 2026-11-08 — Issuer Library: Library screening screen, offline: retained workspace; no provider called (branch `claude/library-screening-tests`)

Scope: the Library screening screen (L2, L3 tests, L4 docs and Help), macOS only, the 59 retained records; no provider call.
- Gates, exit 0: `python3 apps/issuer-library/validate.py quick` (node pass 357, python 610 passed; FW_PYTHON absolute); `uv run python tools/quality_gate.py` 0 findings.
- README "Run from source" block run as written with `--no-browser` and an isolated `--state-dir`: launch ticket exchange 303, `/` 200, `/api/workspace` 200, `/api/catalogue` served; stopped afterwards.
- Browser gate (L3 report): 131/133; the 2 failures are the fake-provider check, which also fails on origin/main `c9e8be31`. Not re-run.
- Whole-branch review (Opus, confidence-review and rewrite-tournament): approve; its one Low (an unreadable number bound kept after a panel rebuild) fixed in `b08558ee`. After rebasing onto `8f313722`, quick (node 358) and the quality gate exit 0 on both branch tips.
- Owner opened the app and accepted the Library screen on 2026-11-08 (Checkpoint L).
Not verified: Windows/Edge rendering; real screen readers; the weekly full suite; the browser gate after the rebase.

## 2026-11-08 — Issuer Library builds with Go 1.24 (branch `claude/intelligent-babbage-b0309i`)

Scope: owner requirement that the app build with Go 1.24; Linux amd64, Go 1.24.7 with `GOTOOLCHAIN=local`.
- `go.mod` 1.26.0 → 1.24.0. Only Go 1.25 additions were in use: `os.Root.MkdirAll` (4 calls in `jobs.go`),
  replaced by `mkdirAllIn`, which makes each component through the root; `sync.WaitGroup.Go` (7 test calls),
  replaced by the test helper `spawn`. README and the browser workflow's `GOTOOLCHAIN` now say 1.24.
- `go vet ./...` clean; `gofmt -l` empty; `go test -race -count=1 ./...` ok (48 s), including new tests for
  nested creation, existing directories, a file component, `..`/absolute/empty names and a symlink out of the root.
- The rebuilt binary served the copied workspace: Library, Reports, a report, New run with the context form,
  Run activity, Settings and a run Overview rendered with 0 console, page or HTTP faults (Chromium); an
  offline review of TDG FY2024 returned the 8-module Credit Snapshot plan. No provider call.
- Not verified: Windows build and Edge; packaging with `packaging/build.py`.

## 2026-11-08 — Issuer Library: Impeccable polish of the run lifecycle surfaces (branch `claude/app-sections-skill-use-d9996f`)

Scope: New run progress, Run activity and the run strip, after the critique fixes below (start `b8a3d391`); macOS only; a synthetic
scratch workspace (one budget stop in CP-1 after CP-0 accepted, one complete run) and jsdom fakes, no provider call.
- The module where a run stopped shows amber "Stopped here"; a stop between modules (`stopped_during: accepted`) keeps the accepted
  module ticked and reads "Stopped after <module> (n of N)."; the strip is hidden on that run's own Run activity and New run progress
  view (not a dismissal); Resume is the one primary action for a resumable run; the short run id badge with the full id in its title;
  "Run record · WEB-…" heading; the module sentence on its own line with a full stop; event dates only on the first row and when the
  day changes; no link after "0 saved outputs" or when no report exists; strip text up to 120ch, card radius, 24px action targets.
- Reviews: mx-precise on `4f9fd8a6` (one Medium: the stop-between-modules case above; one Low: a loose test, tightened); one fix
  round `15e0d9fd`; scoped mx-precise re-review of the fix PASS (its new test fails on `4f9fd8a6`, exit 1).
- Gates at `15e0d9fd`, exit 0: `node --test` over validate.py NODE_TESTS 353/353; the review's three probes; `tools/quality_gate.py
  --base 5740af30` 0 findings. No Python or Go file changed since the pytest/go run in the entry below. Impeccable detector: no finding
  on a line this pass changed. Browser check in the in-app pane at 1366×768 and 720×900.
Not verified: Windows/Edge rendering; a real engine run producing a stop between modules; real screen readers; the weekly full suite;
nothing pushed.

## 2026-11-08 — Issuer Library: fixes from the Impeccable critique of the new sections (branch `claude/app-sections-skill-use-d9996f`)

Scope: `apps/issuer-library` sections added after the 2026-11-06 layout pass (critique
`apps/issuer-library/.impeccable/critique/2026-11-08T11-36-19Z__web-index-html.md`, 22/40, 3 P1); start `5740af30`; macOS only;
retained workspace and jsdom fakes, no provider call.
- Cash flow grid: no "—" cell; every gap is n.a. with a reason ("printed as — in the source" / "the model's source table has no
  value for this period"); n.a./n.m. cells carry aria-labels; period-named "Why cells show n.a." lines; total rows; ratio tooltips at
  4 dp with ≈; labelled scroll region; 32px rows; the published model behind a closed disclosure. Built from gains Run, plain role
  words, "Matches publication" and a different-attempts note; candidate reports use the grey badge; "Analytical qualification: not run".
- Run lifecycle: a run-state strip on every screen (running / complete / stopped / failed / interrupted; amber only for the last three;
  View activity, View reports, Resume, Dismiss per viewer); the rail mark coloured by state and unaffected by Dismiss; a Report delivery
  progress step; plain state words and module names for codes.
- Resume and Run activity: a resumed run has its own cap (prefilled from the stopped run's recorded `progress.cap_usd`, never a draft
  value); not offered after a ruling stop; Run activity falls back to the retained record on a 404 ("No live progress is recorded for this
  run in this workspace."), shows the log in a labelled card with dated times and offers Resume; Recent runs newest first with id and
  start date (`jobView` gains `started_at`); browser and native notices name the issuer and the stop reason.
- Library, form, Help: runs newest first, "<shown> of <total> runs", groups open while searching without changing the remembered
  state; context form on the 11–14px ramp with a grey Default tag; Help entries for run notices, resuming and n.a./n.m.
- Answer keys: `designs/forecast-answer-key.json` and `designs/library-answer-key.json` updated by a separate oracle author from source
  bytes (`5b6d07a5`, `9066c7c0`, `aadab2eb`); implementers never edited them.
- Reviews: mx-precise per task; mx-adversary on Task 4 (one Medium: resume cap fell back to the draft budget, fixed); fix rounds:
  Task 3 one, Task 4 one, Task 5 one; mx-architect on the branch (two Mediums: Dismiss hid the rail mark, the retained view denied a
  recorded cost; one fix wave, re-review clean; confidence review and rewrite tournament included).
- Gates at `f3b9f9bd`, exit 0: `node --test` over validate.py NODE_TESTS 344/344; pytest over validate.py PYTHON_TESTS 607 passed;
  `go vet`, `go test`; `tools/quality_gate.py --base 5740af30` 0 findings. Impeccable detector 81 → 84 advisories (three literal colours:
  two in `web/context-embed.css`, which mirror screen.css tokens because the sandboxed form cannot read them, and one in `screen.css`,
  tokenised in this entry's commit). Browser check in the in-app pane at 1366 and 720 (32px rows, no page overflow, Built from, grey
  candidate badges, retained Run activity, "4 of 24 runs").
- Open for the owner: the server accepts a resume of a ruling stop (client refuses); quarter values present in `quarter.md` (capex,
  cash interest, cash taxes, Q1 closing cash and debt) show as n.a. in the grid; a retained web run's `progress.json` spend is not shown;
  `actions.js` reconnect `catch{}` is unlogged; the native toast keeps the PowerShell identity and has no click action; Ford Otosan and
  Ford Otomotiv Sanayi A.S. stay separate issuer IDs; the branch is 1,816 changed lines (658 without tests and keys), over the 800-line
  PR gate — split at PR time.
Not verified: Windows/Edge rendering and the native toast; live-job states (running, stop, finish notice, Resume) beyond jsdom; real
screen readers; the Playwright browser walk; the weekly full suite; nothing pushed.

## 2026-11-08 — Codex review of `ac22d9d7`: Quit race and handoff Excel reads (branch `claude/exciting-darwin-pb4frw`)

Scope: four review findings, each reproduced on main `9838968` before the fix; Linux, offline, no provider call.
- P1 Quit: `/api/quit` checked active runs under a read lock and never set `quitting`, so a Start could begin
  before the stop; a review in flight was not checked. Quit and the relaunch path now share `claimQuit`, which
  checks runs and reviews and sets `quitting` in one critical section. Quit with a run or review answers 409.
- P1 precision, P1 sparse scan, P2 source-id detection (`model/handoff.py`): workbook reads now reuse the
  preparation reader (`xlsx_content`): exact stored lexemes (`9007199254740993.25`, was `…994.0`), only stored
  cells (a 2-cell sheet with dimension `A1:XFD1048576` hung past 30 s, now immediate), formulas with
  `cache=[absent]` never 0, non-General number formats shown, its limitations on each sheet page. A workbook
  is recognised by content (ZIP with `xl/workbook.xml`), so source id `S1` reads; other ZIPs and text keep
  their prior handling. The reader's DTD/external-relationship refusals now apply here too.
- New tests fail on the old code for the reported reason and pass now: `TestQuitClaimsTheShutdownGuard…`;
  three in `tests/test_handoff_loop.py`.
- Gates: `tools/quality_gate.py` 0 findings; `go test -race` package ok; targeted pytest 1208 passed, 3 failed
  (`test_gate.py` ×2, `test_o5_done_when.py`), all three on main and in `tests/nightly-known-failures.txt`.
Not verified: Windows/macOS for the Go change; a model reading the new workbook page format live.

## 2026-11-08 — Sweep follow-ups R14, R15, R17 (branch `claude/sweep-followups`)

Scope: three register rows that predate the swept range, fixed on the owner's request from main `5740af30`; macOS;
fakes and injected faults, no provider call.
- R15 (money): a call whose post-reply redaction or pricing raised was neither settled nor released and vanished
  from `status.json` and `calls.jsonl` (counted as zero). Now settled as unknown at its full hold, recorded with a
  one-line stop message (traceback only in the call record), zero-cost replies keep a coherent `computed` row, and
  the `loop.py` sibling settles unknown and keeps the provider's class. App path: `spent_usd` 0.00007 → 5.73007.
  Reachable live only by injection; offline via a recording with an empty tool-call id.
- R14: the store's section parser numbers lines like delivery's `physical_lines` (form feed, U+0085, U+2028).
- R17: the New Run page's poll sends `notify=0`, so only the app-wide watcher speaks for the tab.
- Reviews: mx-precise per task, mx-adversary on R15 (one fix round), mx-architect on the branch (approve; two Lows
  fixed in a final batch). Probes r15-1/2b/3, review-f2*, review-ffinal-5, app-5, review-3a-5 exit 0.
- Gates on `922fb03b`, exit 0: `tools/quality_gate.py`; targeted pytest (13 files, 1066 passed); `validate.py full`;
  Go unchanged since `3fca4c08` (`go vet` darwin/windows, `go test -race` exit 0). 520 changed lines; one
  suppression removed, none added.
- Open for the owner: R18 (app spend for a hold left by a killed process); L8 (other unguarded `_named` sites).
Not verified: Windows/Edge; a real provider reply that triggers R15; the export mismatch of a scripted
`sent_usage` reply (L9); the browser walk and the weekly full suite (GitHub billing blocks CI).

## 2026-11-08 — Refactoring sweep of PRs #31-#43 (branch `claude/sweep-prepare-c802ee`)

Scope: changed code in `e1a24112..0619a9be`, start `0619a9be`; macOS only; fakes and retained data, no provider call.
- Fixed, each with a test that failed for its cause first: resume ran a retained prefix out of the fresh
  order and paid for a call before a stale refusal (`registry.plan`, `owners/cpos.py`); a wrong pin of a
  replayed module is refused before the next call; quarter bridge row matched like the annual operand and the
  quarter register checks repeats first; one notice per finished run (a poll that saw the finish counts, a
  tab that cannot notify does not, a failed-spawn retry keeps no stale mark); a cut event log's progress is
  marked incomplete; a failed event append is cut back; an unreadable retained record is named in the review;
  a refused second invocation logs no `stopped`.
- Reviews: mx-precise per task, mx-adversary on Tasks 1 and 3 (one fix round each), mx-architect on the branch
  (approve; confidence review and rewrite tournament included).
- Gates on `3c48e208`, exit 0: `tools/quality_gate.py`; targeted pytest (12 files, 760 passed); `go vet` (darwin,
  windows), gofmt, `go test -race`; `validate.py full`. Flow check: 1 fault each on `cpos-launch-live-002` and
  `cpos-sol-medium-20261105` (= calibration). Answer keys and `runs/`, `data/`, `cases/`, `deliverables/` unchanged;
  0 new suppressions; 590 changed lines.
- Open: owner decisions R10-R13, R16; predating rows R14, R15, R17; Lows L2-L4 (a timing-dependent missed
  notice, a refused quarter model on a repeated text row). Sweep files: `docs/sweeps/refactoring/` (contract, goal),
  register and probes in `artifacts/sweeps/refactoring/` (ignored).
Not verified: Windows/Edge (toast, truncate while the Go server reads the log, the rlimit test's skip); the
browser walk (no Playwright); the weekly full suite; a paid resume.

## 2026-11-08 — Phase 6: verification record split (branch `claude/verification-archive`)

Moved the sections dated before 2026-11-07, verbatim and in original order, to docs/VERIFICATION-ARCHIVE.md by `git mv`; 2026-11-07 entries stay here.
Proof, exit 0: `diff <(git show HEAD^2:VERIFICATION.md | tail -n +10) <(cat <(tail -n +12 VERIFICATION.md | sed '1,8d') <(tail -n +5 docs/VERIFICATION-ARCHIVE.md))` on the merge with main after #35-#42 (HEAD^2 = that main; the `sed` drops this entry).
Line counts: VERIFICATION.md 359 (with this entry), docs/VERIFICATION-ARCHIVE.md 5655.
Merged after #35-#42; their entries stay in this file.
Not verified: none beyond the gates.

## 2026-11-08 — Phase 5: LTM Adj EBITDA and quarter-end leverage (branch `claude/model-ltm`)

Scope: Tasks 9-10 and the end batch (da425880..853c9ee1), stacked on Phase 4; macOS only.
Phase diff: 760 changed lines (cap 800). **Deterministic retained-data** check: TDG
`runs/cpos-tdg-model-001` inputs and quarter handoff `runs/tdg-003`, no provider call.
- Answer key (checked by hand before dispatch): LTM 4,173 + 1,061 − 912 = 4,322; quarter secured
  20,192. The plan's "4.7x" is "4.67x" in the store's format (two places).
- Controller live check (real app, retained data): classifiable model Q1 FY2025 LTM 4,322, senior
  4.67x, FY2024 senior 4.80x; full TDG model Q1 FY2025 LTM 4,322, senior n.a. "the debt register has
  a row that cannot be classified", total/net leverage "needs quarter-end total carrying debt, which
  the model does not derive".
- Reviews: Task 9 mx-precise + mx-adversary, one fix round (required secured rows, LTM span, Total
  rows, one Net column, repeated bridge row, duplicate windows, operand reasons, hidden text),
  re-review pass; Task 10 mx-precise approve; end batch (LTM span 364-371; senior fallback text);
  phase mx-architect approve.
- Gates: `validate.py full` exit 0; `tools/quality_gate.py` exit 0; pytest 265 passed.
- Follow-ups on `claude/register-hardening` (owner asked to apply them): escaped pipes, subtotal and
  emphasised labels, an anchor without its table, label spacing, hidden text inside a table, the
  WINDOW_MISSING wording and the LTM start date.

Not verified: Windows/Edge rendering; any issuer other than TDG; a non-Q1 year-to-date window with
real data; in-app runs still publish no model (Decision 10); the weekly full suite.

## 2026-11-08 — Phase 4: derived rows in calculation.json (branch `claude/model-derived-rows`)

Scope: Tasks 7-8 (5139dc9f..60c101c7), the Low batch 33be4f6c and the end commit; macOS only.
Phase diff against origin/main: 652 changed lines (cap 800). **Deterministic retained-data**
check: TDG `runs/cpos-tdg-model-001` inputs, no provider call; not a live model run.
- Answer-key correction: the plan said FY2024 senior secured debt 13,932 and 3.34x. The register's
  8 secured rows (486+8642+2077+2727+1438+984+2180+1486) give 20,020 and 4.80x (20020/4173); the
  store derives the same total.
- Controller live check (real app, retained data): Forecast grid FY2024 revenue growth 20.58%, gross
  margin 58.84%, Adj EBITDA margin 52.56%, Adj EBITDA growth 22.92%, senior secured leverage 4.80x;
  FY2023 growth 21.29% / 28.31%; FY2022 growth n.a.; FY2022/23 senior n.a.
- Reviews: Task 7 mx-precise approve; Task 8 mx-precise + mx-adversary, one fix round, re-review
  approve; phase mx-architect approve (two Low, fixed in the end commit: register problems resolve
  in the store's order, a negative divisor reads "a divisor is zero or negative").
- Gates after the end commit: targeted pytest (241 passed) exit 0; `tools/quality_gate.py` exit 0;
  `validate.py full` exit 0 (node 275, python 526, go, ruff).
- Owner items (predate the change): an escaped `\|` in a register cell parses differently in the
  store; subtotal rows such as "Secured notes subtotal" are counted by both readers; `op_prefer`
  ignores a recorded unit (accepted, Decision 7).

Not verified: Windows/Edge rendering of the new cells; a 52/53-week issuer other than the
constructed periods; in-app runs still publish no model (Decision 10); the weekly full suite.

## 2026-11-08 — Resume a stopped run (branches claude/resume-core, claude/resume-run)

Scope: Tasks 4-6 of the deferred-features plan.
- Resume creates a new reviewed job; only cap and max turns may change. A stopped run's accepted
  modules are replayed without a call.
- Replayed bytes come from CP-OS's accepted record, `requests/<m>/<fp>/<n>.response.md`, with an
  issue-free review and a matching sha.
- A module is kept only while its sources (context included), upstream, instructions and model
  setting match and the current checker accepts it. The prefix ends at the first mismatch; the
  review names the reason.
- Resume copies only the job's listed regular files and never follows symlinks. Start recomputes the
  review id from the plan it will run, before any call. The stopped run's folders are never written.
- Reviews: mx-precise 1 Medium (sources the answer never saw); mx-adversary 3 Mediums (replay from
  the app's copy; instructions and model not pinned; Start re-reading after the id matched);
  re-review 1 Medium (an edited copy blocked Start). All fixed in 2 rounds.
- Probes exit 0: adv3-instructions, adv3-start-toctou(-sources), adv3-resume-id, adv3-context,
  adv3-stopped-run-untouched, p3-sources-changed, rr3-accepted-selection, rr3-start-record-window,
  rr3-checker-at-review, rr3-corrupt-record, rr3-copy-edges.
- Superseded by the design change: adv3-replay-bytes (the controller confirmed the replayed bytes
  equal the model's accepted answer, not the edit), rr3-copy-start, adv3-go's whole-tree-copy case,
  p3-copyfs-symlink.
- Not verified: a real paid resume; the Go-to-Python engine path end to end (the Go tests use
  fakeEngine); Windows.

## 2026-11-08 — Native Windows notice (branch `claude/native-toast`)

Scope: Task 3 of the deferred-features plan.
- Behaviour: when a run finishes, the server waits up to 75 s for a run-list poll that arrives after
  the finish, and shows a Windows toast only if none arrives. This gives exactly one notice whether a
  tab is watching, the tab is in the background, or no tab is open. The 75 s replaces the plan's 15 s,
  because Edge and Chrome slow a hidden tab's polling to about once a minute.
- How the toast is shown: PowerShell, located through `GetSystemDirectoryW`, runs a fixed script. The
  text reaches it only through environment variables. The child gets an allowlisted environment with
  no provider keys. A 20 s timeout applies, and any failure is logged and never affects the run. On
  other platforms nothing is launched.
- Reviews: mx-precise and mx-adversary each found two Medium issues: provider keys in the child
  process, global swaps in the tests that raced, a test that did not wait, and background tabs getting
  a double notice. All four were fixed in one round. The re-review passed.
- Probes exit 0: `adv2-env`, `adv2-race`, `adv2-tests-launch` (0 real launches), `adv2-injection`,
  `adv2-child`, `p2-case-a-window`.
- Not verified: the toast on real Windows; `GetSystemDirectoryW` at runtime; real hidden-tab
  throttling; a notice pending while the app quits; managed-machine policy (Constrained Language Mode,
  security alerts on PowerShell launches).

## 2026-11-08 — Run activity page (branch `claude/run-activity`)

Scope: Tasks 1-2 of `docs/superpowers/plans/2026-11-08-deferred-features.md`; macOS only, in-app browser pane.
- Page: `GET /api/runs/events?id=` serves a run's `events.jsonl`; the Run activity page lists the events,
  recorded spend and stop reason; a cut or oversize log shows its complete events and says the record is incomplete.
- Review: mx-precise approved; probe `p1-events.sh` exits 0.
- First paid live run, started by the owner on 2026-11-08: `web-625c3c5138d54dcbfb84b9bd963e48c3`, CP-0 + CP-1,
  sol-medium gpt-6.1-sol, cap USD 10, hold USD 5.73. Each module had one rejected draft, was repaired and accepted;
  the report was delivered; spend USD 0.58813770. Coverage entries: CP-0 18, CP-1 37; both modules recorded as
  `live-provider`. The front line "Source readiness: confidence Medium; …" leads the report. The app showed `● 0/2`,
  then `● 1/2` and the reload prompt. The Run activity page at this branch listed every event of that run.
- Not verified: Windows Edge; the look of `.activity-log`; a real 4 MiB log.

## 2026-11-07 — Phase 3 and branch end: identity, handoffs once, manifests once, workspace cache (branch `claude/system-design-remaining-calls-e06c23`)

Scope: Tasks 7-10 (commits ec18373f..3976be83), the end batch 9b3215fa and the final batch 398ae209;
macOS only. The live test used a copy of the retained app run `web-04cd5a…` (retained data, no
provider call).
- Payload probe `adv-security-handoff-hardlinks`: the workspace payload falls from 560 MB to 20.1 MB
  at 28 hardlinked runs.
- Cache live test (real app at 3976be83, in-app pane): `/api/workspace` 196,096 bytes; 82 ms, then
  5 and 11 ms from the cache; appending a run file gave one rerun (84 ms), then 4 ms. Overview
  renders through hydrate.
- Task reviews (Fable): Tasks 7, 8, 9, 10 Approved; Task 10 race probes `task10-races.go/.sh` exit 0.
- `validate.py` full exit 0 at 3976be83 (node 273, python 521, go test/vet incl. windows, amd64/arm64
  builds, ruff). The diff ec18373f..3976be83 is 800 lines, at the cap.
- End batch 9b3215fa: probes 0; quick 0; quality gate 0 (230 passed).
- Whole-branch Fable review (0c596eac..9b3215fa): Ready to merge. Its three Lows were fixed in
  398ae209 and the controller reran the probes (`branch-stop-reason-unknown-charge.py`,
  `branch-stop-in-delivery.sh`, `branch-double-gaps-heading.py`): 0, 0, 0.
- Final: `validate.py` full exit 0 at 398ae209 (node 275, python 523, go test/vet incl. windows,
  amd64/arm64 builds, ruff); `tools/quality_gate.py` exit 0.
- Owner items: `tests/test_retained_planning.py::test_issuer_identity_cannot_be_assembled_across_title_and_request`
  fails at base 0c596eac and is not in `tests/nightly-known-failures.txt`; `_literal_tables` is not
  fence-aware (pre-existing, cannot cause a false failure); Task 10 `clear()` waits behind an
  in-flight store run (latency only); Task 8/9 Info notes.
- Not verified: the browser gate (`FW_PLAYWRIGHT_PYTHON` unset); the
  workspace reload on Windows; any provider run.

## 2026-11-07 — Phase 2: delivery gaps, coverage record, front lines (branch `claude/system-design-remaining-calls-e06c23`)

Scope: Tasks 4-6 (commits 74c66963..ec18373f, 799 changed lines) and the banner fix a46f6976 that
the owner prompted ("Looks like wrong frontend"); macOS only.
- Live test (deterministic retained-data rebuild, not a model run): the handoffs CP-0, CP-1 and
  CP-1A of `runs/web-04cd5a5d02ea7d1dea714a8a6632cd21` rebuilt at ec18373f into a scratch copy with
  the launcher's front routes; `runs/` untouched. The coverage check passes (CP-0 14, CP-1 32, CP-1A
  22 entries). CP-1 limitations are 2 fixed plus 9 gap rows, matching the 9 data rows of its Gaps
  table (independent awk count). The first view came from a scratch static server, not the app;
  `#delivery-limits` had no class and rendered unstyled. a46f6976 gives it `class="banner"`
  (RED/GREEN test; quick 0; quality gate 0), then it was viewed in the real Issuer Library app.
- Reviews (Fable): Task 4 Approved (probe `task4-hostile-gaps.py` 0); Task 5 passed after 2 fix
  rounds (5 probes 0); Task 6 passed after 1 round (`task6-manifest-roundtrip.py` and `-v2` 0).
- `validate.py` full exit 0 at ec18373f (python 513, node 271, go, ruff).
- Finding: the in-app pane does not paint sandboxed iframes (srcdoc probe: sandbox, not painted;
  no sandbox, painted); the report frame is equally blank on main. The in-app report frame therefore
  still needs checking in Edge/Chrome on Windows.
- Owner item: `tests/test_retained_planning.py::test_issuer_identity_cannot_be_assembled_across_title_and_request`
  fails at HEAD with src reverted and at base 0c596eac, and is not in `tests/nightly-known-failures.txt`.
- Not verified: the report frame in the real app on Windows (Edge/Chrome); a model-written handoff
  through the new coverage check (only retained handoffs); `validate.py` full after a46f6976 (quick
  and quality gate only); the browser gate (`FW_PLAYWRIGHT_PYTHON` unset).

## 2026-11-07 — Phase 1: run event log and app run watcher (branch `claude/system-design-remaining-calls-e06c23`)

Scope: Tasks 1-3 and the cleanup (commits 7afa9551..74c66963), 940 changed lines, over the 800-line
PR cap (tests about 350); macOS only. Natural split for the owner: Task 1 | Tasks 2-3.
- Live test, SYNTHETIC: an event log written into a scratch workspace, read by the real Go server and
  the real UI in the in-app pane. Running showed title "● 1/2 · Issuer library · Issuer Library",
  rail "Run running, 1 of 2 modules" and "turn 1 of 24", "USD 0.26 of a USD 10 cap; the next call
  holds USD 5.73". A stop(budget) was seen by the 5 s watcher (title "!", "Run stopped").
  The real worker-to-events path is covered by fakes only. The notification was not exercised
  (pane permission "denied").
- The paid live CP-OS run (CP-0 and CP-1, cap USD 10) was denied by the permission classifier and
  was not run; it remains an owner decision. The review step (no model call) ran live: hold 5.73,
  provider_ready true.
- Reviews (Fable): Task 1 fixed once (event writes made fail-open; probe v2 0); Task 2 Approved;
  Task 3 fixed once (notification click with a draft open; probe 0); cleanup Approved (probe
  `cleanup-external-gate.sh` 0).
- Gates: `validate.py` full first failed on ruff only (RUF100 on `noqa` that `tools/quality_gate.py`
  requires; the two gates disagreed); after 74c66963 (ruff `external` codes, unused `on_start`
  removed) it exits 0. The first full run otherwise passed (node 271, python 507, go).
- Owner items: the paid live run; the 940-line size above.
- Not verified: the real worker writing events under a provider; the notification; the Windows UI;
  the browser gate (`FW_PLAYWRIGHT_PYTHON` unset).

## 2026-11-07 — First nightly run triaged (branch `claude/nightly-disk`)

Scope: nightly run 42351518717 on main 3bff5e8, its runner faults and its 94 failures not on
`tests/nightly-known-failures.txt`. Offline in this container; CI reruns only, no provider call.
- Runner: two shards' disks filled (each workflow store holds about 120 MB of issuer sources and
  pytest kept every `tmp_path`); one shard ended with exit -11 (no trace: its log is an artifact the
  proxy cannot fetch). Fix: a passing test's `tmp_path` is deleted, unused runner toolchains are
  dropped, 8 shards instead of 6, and each shard prints its log's last 400 lines to the job log.
  Module and session fixtures' directories stay (some are shared across modules). A
  `workflow_dispatch` with `tests` (and `ref`) reruns only those ids. The full-run fix itself is not
  yet proven: it needs the next full run.
- Triage: CI reruns of the 92 slow failures on this branch (42369485755) and at 5dd01ec, before
  the review fixes (42369487867). 89 fail at 5dd01ec with the same message, most of them fixtures
  whose publication is refused in the CP-OS and S1A suites; they go on the known list. One fast
  failure fails at 5dd01ec too (known list).
- Regressions from the review fixes, fixed: CP-2D's pinned-assumptions label now follows the
  analyst's stated limitations (S06-C02; T4 L2/L3); the CP-2E FY-header test passes the pack's
  currency; the CP-DR off byte-identity test undoes the deliberate S13-A04/C07 and S14-C04 CP-0
  sentences with their strip helpers, and run.json and the run tree then equal the unchanged
  checkpoint 65d1a180 fixture.
- Review (model matrix): a Sonnet review of each commit. It added the rerun-id guard; its module
  fixture cleanup was reverted because it deleted directories later modules reuse
  (`tests/cpdr_runs.py` `closed_run`, the session prompt pack). The second review confirmed.
- Checks (fast, `timeout 300`): `tests/test_nightly_tests.py` 10 passed;
  `tests/test_periods_currency_misc.py` passed; the three regression nodes 9 passed;
  `tests/test_method_cp2d.py` and `tests/test_connect_cp2d.py` 434 passed, 2 failed (known list);
  `cases/pins.py --check` 219 paths; quality gate 0 findings. Not run: the workflow YAML lint (the
  linter download was refused); the full suite (next scheduled run).
- Schedule (user ruling, 2026-11-07): weekly, Sunday 01:00 UTC, since a full run takes about 17
  runner-hours of this private repository's Actions minutes.

## 2026-11-07 — Confidence review of the whole app

Scope: 14 slices of the app at a313b50, each reviewed by a Sonnet agent and checked in the main
session. A patch was kept only when its new test failed on the a313b50 source and passed after.
Merged with main after `claude/review-fixes`, which had fixed several of the same defects; main's
versions were kept for the run-list order and review write timeout (`jobs.go`), the stray
`CP-1a.md` (`store.py`), the gate key list (`validate.py`), the `rv_quotes` exponent, the
calendar-quarter delta core (`earnings.py`, owner ruling: delta core only, B19 unchanged) and
R5b. `cpos_handoffs.py` was deleted on main, so its UTF-8 fix lapses. Fixes this entry adds:
- a stale status reply no longer overwrites another run's screen (`actions.js`);
- the budget's directory fsync goes through `platform_io` (`budget.py`); Windows refuses
  `os.open` on a directory, so a paid run would have stopped creating its budget (simulated);
- `search_source` matches on the page itself (U+0130, `handoff.py`);
- journal writes retry through `platform_io.replace` (`execution.py`);
- the CP-2 `**Key risks:**` line is kept among limitations (`handoff_delivery.py`);
- `_scale_of` keys on the resolved scale label (owner ruling, `report_view.py`), clearing the
  T4.9 `mixes amount units` refusal.
Rejected: joining split negatives `(1,234 )` (0 of 43,461 corpus lines; breaks the spacing
invariant); chart text at the handoff's precision (display-only; stops a retained delivery
verifying).
Open for the owner: a leftover `run.json.tmp` blocks a resume; `os.rename` at
`run_inputs.py:581`; `_stated` drops a cell's note; CP-1D reads `25bps` as 25; `.copilot-home`
depends on the launcher's working directory; an undecodable source leaves its module folder, so
a rerun says `cpos_live_already_started`; 25 of 27 retained deliveries do not verify under
current code (as at a313b50).
Checks after the merge: `tools/quality_gate.py` 0 findings in 10 changed files;
`cases/pins.py --check` matches 219 paths; 371 of 373 affected Python tests pass, and the 2
failures (`test_cp2e_refuses_the_fy_2025_header_under_fy_2026`, `test_no_hardcoded_period_left`)
fail on a clean main tree too; the nine web test files (191) and `go vet`/`go test` pass.
GitNexus: this repo is not indexed.
Not verified: real Windows; any provider; the whole suite; `test_financial_workflow.py` after the
merge (it passed 21 before it, agent-run, and exceeds the five-minute limit).

## 2026-11-07 — Fixes for the whole-app review findings (branch `claude/review-fixes`)

Scope: the 253 agreed findings of the whole-app review (`docs/review-handoff/` on
`claude/review-handoff`): 4 critical, 49 high, 94 medium, 106 low after the cross-review.
326 files against `claude/quality-gate` (src/deploy_workflow 95, src/deploy_vii 45,
apps/issuer-library 28, tests, five case oracles rebuilt by their own builders and re-pinned).
No change under runs/ or deliverables/. Offline only: no provider call, network fetch or key.
Method (user): a model matrix. Each batch was fixed by one model and reviewed by the other
(Opus/Sonnet). The reviewer confirmed or repaired each commit, ran a rewrite tournament and
adversarial tests, and committed separately. Every merge passed the changed-code gate
(`tools/quality_gate.py`, 0 findings at the end over 253 changed files) and targeted fast tests
only (each pytest call under `timeout 300`; no test_owner_*, nothing promoting CP-0/CP-1). Frozen
prompt digests: each deliberate wording change has a strip helper (`tests/prompts/s*_strip.py`),
and the digest failures equal main's 26 by name. The rule-list golden sha256 section was refreshed
after wave 1 and again at the end, each in its own commit. `cases/pins.py --check` matches 219
paths.

| Severity | Fixed | Partly fixed | Kept as is by user ruling | Already fixed by an earlier fix | Not a defect / not reachable |
|---|---|---|---|---|---|
| critical | 4 | 0 | 0 | 0 | 0 |
| high | 45 | 4 | 0 | 0 | 0 |
| medium | 91 | 2 | 0 | 1 | 0 |
| low | 94 | 3 | 4 | 2 | 3 |

User rulings (2026-11-07), applied through the same matrix with a review each:
- S12-A02: option B, fail closed. A positive `signed` amount on an outflow-linked line is refused.
  A printed magnitude uses `outflow_magnitude`. A refund is recorded as missing with its reason, and
  the coverage gate accepts that withheld line. `o2-synthetic` was corrected through its builder.
- S10-A05: a native CP-8 that CP-0 commands is recorded as refused (superseded, pointing to CP-OS
  `run_comparison`) and the run finishes with a verified receipt.
- S18-C03: a per-launch secret held in memory only. The one-time launch ticket expires after 120 s
  and is exchanged for a SameSite=Strict session cookie. Same-site and cross-site requests are
  refused. A relaunch asks an idle library to quit through an owner-only request file and then
  opens a fresh link; a busy library answers with what is running.
- S18-C08: a workspace switch is refused while a review is in flight.
- S08-C08: interest covers are n.m. when adjusted EBITDA is ≤ 0.
- S08-C09: an Insufficient Information preference has an empty ordering.
- S13-A07: the financial-synthesis scope is gated per dimension.
- S09-A08: a "Same definition" naming a document missing from the pack must be "Not determinable".
- S09-C04: the source-refusal wording is corrected.
- S09-A04 remainder: CP-4C picks the secured facility by T4.18 status. Its other upstream faults
  are typed issues. A hopeless facility issue is refused at begin (no model call); the verifier
  recomputes the reason from that snapshot's CP-1 head.
- CP-4 missing-document check: "set forth in", "specified in" and "ascribed to" also count as
  pointers, and memorandum and prospectus as document nouns.
- S04-C11: the Model rail highlight is fixed.
- CP-2E accepts "$m", "US$m" and "USDm" as millions, and refuses a unit statement that names a
  currency other than the run's reporting currency. CP-1D matches its Basis clause without regard
  to case, and its second-currency guard reads ISO 4217 codes only.
- Refund handling: `outflow_magnitude` is refused on a line whose label states an inflow (outside a
  "net of" clause), and an accounts row cannot contradict a withheld line.
- S14-A02: the read-window bound is confirmed, superseding the PF-R7 exemption (recorded in
  `cases/pilot-fixes/read-window.json`).
- S15-C05: splitlines numbering is canonical (documented in `preparation.text_content`).
- Kept as is: S03-C06, S05-C07, S13-C10 and the fail-closed confirmations.

Partly fixed: S07-A01 (strict xfail `test_a01_quarter_cp2a_swapped_metric_is_refused`), S11-A03,
S13-A03/C05, S01-A03, S06-A06, S07-C03, S05-C09, S09-C06. Also fixed: three defects reviewers found next to fixed findings
(non-UTF-8 lines in the source and financial servers, now one shared `workflow.read_line` that
the owner server also uses; lone surrogates in research manifests; the CP-4 stored claim
limitation).
Branch review (one final reviewer over the whole branch, report only): verdict merge, no blocker
or high finding; conflict resolutions coherent; every composed-prompt difference across the 12
step contracts maps to a named finding. Its low items were fixed through the matrix: comments
opened mid-line are hidden too, financial_workflow (and owner_workflow through it) uses the atomic
`workflow._put`, and the CP-4 context.py pin test is renamed to what it checks.
Known-failure list: 45 more base failures found during the waves and confirmed on
`claude/quality-gate` were added (`tests/model` ruling files, `tests/prompts` fence/compose,
coverage rule, prompt-set digest, the 26 frozen-message digest failures, one o2 citation test, the
financial-workflow full-component fixture and two research consumer-block stubs). The Issuer
Library launch secret and relaunch quit request also need Windows and browser acceptance: the
launch link and cookie in the report frames, the state-folder ACL check, the polling watcher,
port rebinding and the dialogs.
Not verified here (slow or not runnable in this container; the nightly run covers the pytest
ones): every `test_owner_*` suite, including those touched by replay reuse, owner rendering, CP-0
attachments and the shared `read_line`; test_run_pathway*, test_run_inputs, test_cp1_hybrid_offline,
test_financial_workflow and test_host_h1 as a whole; the Issuer Library jsdom suites and
browser_check; the Windows path of the S18-A07 worker lock (compiled and vetted only). Retained-data
checks were deterministic replays of retained outputs, not live runs.

## 2026-11-07 — Nightly full-suite run; gate fix for duplicate module names

Scope: `.github/workflows/nightly-tests.yml`, `tools/nightly_tests.py`,
`tests/test_nightly_tests.py`, `tests/nightly-known-failures.txt`, a docs/QUALITY-GATE.md section,
one AGENTS.md bullet, and a fix in `tools/quality_gate.py`. No analytical code changed.
Decision (user): while working, fast targeted tests only; the full suite, slow tests included,
runs nightly at 01:00 UTC in GitHub Actions (user chose Actions over a Claude cloud session and
UTC). Six pytest shards balanced by file size, `live`/`browser` excluded, provider keys removed,
300 minutes per shard; Go `vet` and `test -race`; a report job fails only on a failure missing
from the known list or an unfinished shard. The known list is seeded with the 24 base failures
documented in the review handoff; the first run will show any other pre-existing failure as new.
Gate fix: two changed files with one module name (two `builder/build.py`) made mypy exit 2, and
the gate raised before its per-file fallback; the fallback now runs first. Found by the S13 fix
review. `tests/test_quality_gate.py` gains the case: it raises GateError on the old gate and
passes on the new one.
Checks: `tests/test_nightly_tests.py` 9 passed and `tests/test_quality_gate.py` 8 passed (fast,
`timeout 300`); the workflow parses (jobs pytest, report, go; schedule `0 1 * * *`); the gate on
this change exits 0. Not verified: the workflow has not run. Scheduled runs start once it is on
`main`; its first run establishes the real known-failure list and duration.


## 2026-11-09 — Plan 2 Task 5b fix batch, browser side (SB2, branch `claude/sb2-plan-2-277424`)

Scope: `designs/browser_check.py`, `web/screen.css`, two test files. Task 5b's review-1 Important
findings (I1 per-run checks dropped; I2 "not exercisable" failing open on live runs) were fixed by
the WIP copied in #19/#25; a scoped mx-precise re-review approved both (probe
`task5b_live_not_exercisable_fails.py` exit 0; key `single-run-answer-key.json` byte-identical to
e84827cc). This PR fixes the S6 B.1 list's browser items: the Library's selected-run head at 390 px
(a 36-character run id and the nowrap Open run / Open report buttons gave scrollWidth 548; the head
now wraps), `chart_style` split into the default and `chart_style_single`, `single_main` closes the
browser in a `finally`, and a unit test of `not_exercisable`'s fail and skip branches.
Checks: CSS test red on the old rule, green after; probe `p390_library_overflow.py` 548 → 390 (exit
0) on a fresh fake-engine run; detail actions stay beside the title at 1280/1366/1536 (probe);
`validate.py browser` 86 passed, 0 failed; `validate.py quick` exit 0; offline rehearsal
(`live_check --case a-live --rehearse`, fake engine, no provider): both 390-px checks pass in both
engines; its remaining failures are the fake engine's handoffs stating no status ("unconfirmed",
lead ruling: leave). Not verified: the `finally` path with a raising `attempt`; any paid run.

## 2026-11-09 — Plan 2: live-check status reader, lead rulings R-SB2-1/1a/1b (SB2, branch `claude/sb2-5b-status`)

Scope: `src/deploy_workflow/handoff_outcome.py`, `designs/live_check.py` (CP-0 reporting only),
answer-key tests and C1 fixtures. Cause: SB3's paid C1 run (`web-8a674922…`, sol-medium) read CP-4
as "unconfirmed": the reader knew only CP-0's READY/READY_WITH_LIMITATIONS/BLOCKED, while CP-4's
method has it write YAML `qa_status`/`committee_status` and a `Module Status:` line, and CP-0's
method a CONDITIONAL status. Lead rulings (answer keys, written by agents other than the
implementer): own YAML fields and the `Module Status:` line first, most severe wins; CP-0's table
only when the module states nothing; CONDITIONAL → will_refuse with no own handoff; CP-0 itself
"not testable", left out of the live check's faults and count.
Checks: answer-key tests red then green (80 targeted pass); C1 re-read offline on a copy (no
provider): CP-4 unconfirmed → limited (`qa_status: Restricted`), CP-1 limited, CP-0 not testable;
back-test changes only CP-0 rows (cpos-launch-live-001 not_reached → unconfirmed; web-04cd…
limited → unconfirmed, disagreed → not testable); `validate.py browser` 86/0; quick exit 0;
quality gate 0; two mx-precise reviews APPROVE. Not verified: a live run's handoffs beyond the C1
fixtures; combined markups on one `Module Status:` line (read unconfirmed; question with the lead).

## 2026-11-09 — Phase 2: work-PC package and package default workspace (S8, PRs 2-A and 2-B)

- **Scope:** Plan Tasks 2.1 (PR 2-A, `claude/s8-package-72303f`) and 2.2 (PR 2-B, `claude/s8-default-workspace`). Task 2.3 was skipped, because Phase 0 passed from `\\`. All checks ran on macOS with synthetic inputs. No provider was called, and no Windows step ran.
- **2.1 — what the package is now:** `build(target)` writes the following:
  - `target/Credit OS.cmd`. It is the only line naming the version, and it runs `"C:\Program Files\Statestreet\Python313\pythonw.exe" -I -B -X utf8 "%~dp0app\<version>\start.py"`. It gives a plain message when the company Python or the release is missing.
  - `target/default-workspace.json.example`.
  - The release `target/app/<YYYY.MM.DD>-<12 hex>/`.
- **2.1 — wheels and binaries:**
  - The wheels come from `uv export --locked --no-dev --no-emit-project`, 24 packages today: S0's 14, the Copilot SDK closure (6), pypdf, openpyxl, et-xmlfile and python-multipart.
  - Each wheel's URL and SHA-256 come from `uv.lock`. The SHA-256 must also be one of the export's hashes, and the download is checked against it.
  - The embeddable runtime, `._pth`, arm64 and the zip are gone. The package holds no `.exe` or `.dll`.
- **Deviation 1, layout (lead accepted):** the plan says `start.py` adds `<release>/src`. The code's package contract fixes the layout instead:
  - `jobs.engine_root()` is the folder holding `src/`.
  - `server.WEB` is that folder's parent plus `web`.
  - So the release is `{start.py, lib/, web/, engine/{bridge.py, store.py, VERSION, src/, docs/, prompts/}}`, and `start.py` adds `lib/` and `engine/src`.
  - `VERSION` sits beside `src/`, which is where `app_version()` reads it; in the repository it is absent and gives `dev`.
- **Deviation 2, `bridge.py` (lead ruling R-S8-1):** the review/start worker runs `bridge.py` under `-I`. It now also puts the release's `lib/` on `sys.path` when that folder exists (one statement after line 24). `tools/copied-from.txt` marks the file `edited`.
- **Deviation 3, `load_config` (2.2):** the plan's `load_config(loc, defaults)` became `Locations.defaults`, because `server.py` calls `load_config(loc)`. The order is: policy (locked), then the user's file, then the package default (not locked), then `Documents/FinalWorkflow`. `--defaults` sets it, and `start.py` passes `<package root>/default-workspace.json`.
- **Deviation 4, hash source (2.1, controller ruling R2):** the plan asks for PyPI's digest and the export's hash. Both hashes come from `uv.lock`, so they are one trust anchor, not two: the lock's wheel hash must be among the export's hashes, and `runtime.download` checks the bytes against it. No PyPI JSON query is made (S0 ruling R2).
- **Checks on 2-A** (code head ce047cf8; the record commits are docs only):
  - `tests/test_packaging.py` and `tests/test_network_check.py`: 21 passed. The build is real: `uv export`, real wheel downloads and the SHA-256 checks.
  - The worker test resolves `pydantic`, `pydantic_core` and `copilot` from the release's `lib/` under `-I`. It failed before the `bridge.py` line, when they came from the venv.
  - Offline tests make each SHA-256 check raise: a lock hash missing from the export, an empty export hash set, wrong-tag wheels only (cp312, win32, cp313t, manylinux), served bytes that differ (nothing cached), and a tampered cache with bad bytes. A positive control passes.
  - quality_gate 0, pr_size 0 (690), validate quick 0 (610 browser / 1503 python passed), browser 0 (86/0).
  - An earlier run on ce047cf8, made while other sessions' suites held the load average near 100, exited 1 on both. `test_review_concurrent_starts_around_a_failed_spawn` got `{503: 5, 500: 3}` and passed 6 of 6 runs alone. The library walk logged two 404s from a stale `/api/runs/status` poll (`web/actions.js`), and `web/` and the server are not in this diff. The re-run above, at load average 4, passed both.
- **Checks on 2-B** (head c6661237):
  - `tests/test_issuer_library_settings.py` plus the server, launch and quit suites: 99 passed, 2 skipped (the skips were already there).
  - quality_gate 0, pr_size 0 (113), validate quick 0 (610 browser / 1503 python passed), browser 0 (86/0).
- **Reviews:** `mx-precise` per task: both spec ✅ and quality Approved.
  - 2.1's two Lows were fixed in c2865d92: `build.py` loaded `runtime.py` with a lasting `sys.path` change, and the launcher echoes dropped their quotes.
  - Probes `t21_hash_probe.py` (tampered cache, hash missing from the export, version mismatch) and `t21_wheel_contents_probe.py` exit 0.
  - `task-2.2-save-after-default.py` exits 0: a saved user choice wins over the package default, unlocked.
  - The lead's scoped `mx-precise` review of #51 at 72ccb532 found one Medium: neither SHA-256 check was tested, so deleting either survived mutation. It was fixed test-first in ce047cf8. The lead's probes on ce047cf8 all exit 0:
    - `mutants.sh`: 7 of 7 killed, both hash checks among them.
    - `supply_chain_probe.py`.
    - `build_and_inspect.py`: nothing in `lib/` shares a top-level name with `engine/src` or the stdlib.
    - `isolation_probe.sh`: under `-I`, `start.py` and `bridge.py` ignore a planted `PYTHONPATH` and user site.
- **Known, not fixed here:**
  - A `%` or `^` in the share path breaks `Credit OS.cmd`, because `call` re-parses the line (marked `ponytail:`). Dropping `call` would put the version on a line without the plan's pinned pythonw command.
  - The version is stamped from HEAD, but the build copies the working tree, so two builds from a dirty tree share one version. The lead carries this to Phase 3, where S9's runner version rule needs clean release builds.
  - `lib/` comes before `engine/src` and the stdlib on `sys.path`, so a future wheel could shadow one of their modules. There is no collision today.
  - Repo-mode `smoke_test.py` fails at the catalogue `issues` list on unchanged main too, because this worktree lacks `deliverables/tdg-model-*`.
  - `apps/issuer-library/README.md` is copied into each release and still describes `Issuer Library.cmd`, the zip, arm64 and a package without the Copilot SDK. It is fixed by S8's PR 2-C after #51.
- **Ledger:**
  - Task 2.1: `agent=mx-feature fix-rounds=1 gates-first-pass=y`. The round fixed the lead review's Medium; the Lows were batched.
  - Task 2.2: `agent=mx-feature fix-rounds=0 gates-first-pass=y`.
- **Not verified:**
  - Windows-only, for the owner: `Credit OS.cmd` under cmd.exe; a start from a UNC share; a full import of pydantic and the Copilot SDK from `lib/` in the server and the worker (macOS checks resolution only, because `pydantic_core` is `win_amd64`); `Smoke-test.ps1`; `smoke_test.py` in release mode; a UNC package default on a work PC.
  - The full weekly suite.

## 2026-11-10 — Plan 2: C1 live-check harness faults, lead rulings R-SB2-1a(3)/1c/1d (SB2, branch `claude/sb2-c1-harness-a`)

Scope: `handoff_outcome.py`, `designs/flow_check.py`, `designs/live_check.py` (`REPORT_TEXT_JS`),
answer-key tests. Cause: SB3's paid C1 run (`web-8a674922…`, sol-medium) re-read offline: CP-1's
`calculate` result 3.835 did not cover the 3.84 its handoff printed; the report text ran table
cells together ("September 11, 2014Rounded", "-83,297Not calculable"), so 11 and 83 were flagged.
Rulings (keys by agents other than the implementer): a calculate result's printed roundings are
evidence once its operands are; report text keeps cell/block separators; `Module Status:` strips
repeat (combined markups, `*` runs, `> `, any-case label); fenced examples never count;
front-matter values in any case, quoted or with `# comment`; BOM ignored.
Checks: keys red then green; offline re-read on a copy (no provider): C1 flow faults 10800 and
162600 only (out of scope), CP-4 limited, CP-1 limited (forecast ready: a real disagreement);
back-test output unchanged; `validate.py` quick exit 0, browser 86/0; quality gate 0; mx-precise
review APPROVE (Low: O(n²) strip loop on a 1 MB line). Not verified: a live run after this change.
Lead review of #55 (Medium): the fence rule toggled on any line starting with three backticks, so
inline triple-backtick text, `~~~` fences and longer fences misread. Fixed per CommonMark (R-SB2-1h):
opening needs indent <= 3 and 3+ same chars (no backtick in a backtick fence's info), closing needs
same char, run >= opening, only whitespace after; unclosed runs to the end. probe_inline_triple exit 0.

## 2026-11-10 — Plan 2: C1n live-check harness faults, lead rulings R-SB2-1e/1f (SB2, branch `claude/sb2-c1-harness-b`)

Scope: `handoff_outcome.py`, `designs/flow_check.py`, answer-key tests and C1n fixtures. Cause:
SB3's paid C1n run (`web-f1878929…`, sol-medium) re-read offline: CP-4's `**Module Status: Blocked.
CP-4 Blocked. …**` and CP-1's CP-0 row (status beyond 70 characters) read unconfirmed; 12 CP-1
numbers rounding `calculate` results to 8–19 places and 28.5301% / 8.2832% (×100 of ratios) were
flagged as untraced. Rulings (keys by an agent other than the implementer): a status phrase then
`.` or line end counts, longest first; a CP-0 row whose first cell is the module id is read whole,
most severe wins; calculate roundings to every place are evidence; ×100 only for figures marked
`%` / percent / per cent / pct; no other scaling; operands must still be evidence.
Checks: keys red (22) then green (175 targeted pass); offline re-read on copies (no provider): C1n
flow faults 116543 and 98400 only (operand 98400 not evidence: laundering guard), CP-4 will_refuse,
CP-1 limited (forecast ready: a real disagreement); C1 unchanged from the previous section;
back-test output byte-identical to main; `validate.py` quick exit 0, browser 86/0; quality gate 0;
mx-precise review APPROVE (Low: a backtick-wrapped value followed by text reads unconfirmed).
Not verified: a live run after this change; a CP-0 row with CONDITIONAL beside
READY_WITH_LIMITATIONS (reads unconfirmed; question with the lead).
R-SB2-1j (branch claude/sb2-c1-harness-b): a CP-0 row is a module's only when its first cell is the id alone or id + (colon | whitespace-dash) + label; `CP-4.1`, `CP-4a`, `CP-40`, `CP-4-1`, `CP-4 (draft)` are not CP-4's and never reach the 70-character window.
RED 9 failed in test_handoff_outcome_status.py, GREEN 210 passed across the four target files; probe_inline_triple exit 0; probe_status deviates only on the corrected 'CP-4.1 not CP-4' expectation (not_reached) and R-SB2-1i (deferred).
R-SB2-1j fix round 2 (#56 re-review): Medium `| **`CP-4`** — Legal | CONDITIONAL |` lost its row (inner backtick); Lows `| - CP-4.1 |` / `| 1. CP-4.1 |` read as CP-4 via the prose window, docstring said "begins with". Fix: drop `*`/backticks and a leading list marker from the first cell; prose id not followed by `.digit` or `-digit`; docstring states the 1j rule.
RED 3 failed (test_1j2 noown cases), GREEN 238 passed across the four target files; probe_1j_rows exit 0.

## 2026-11-10 — Plan 2: guess_kind recognises executed credit agreements, lead ruling R-SB2-2 (SB2, branch `claude/sb2-guess-kind`)

Scope: `src/deploy_workflow/run_expectations.py` only (answer-key tests in 22b96bb3, written by another
agent). Cause: SB3's C1r rehearsal gave CP-4 `check` (`cp4-declared-executed-none-recognised`) though
the run holds Ex 10.1 "ABL CREDIT AGREEMENT" and Ex 10.2 "TERM LOAN CREDIT AGREEMENT": the
credit-agreement title rule was anchored at line start with no room for a qualifier, and the file-name
fallback ran the same anchored rule on `2014-10-21-ex10-1-abl-credit-agreement`.
Change: the rule accepts up to two capitalised qualifiers (not after `the`/`this`, not `form`, not
`amendment`); the file-name fallback upper-cases the name and drops a leading date and `exNN-N`
prefix. A sentence mentioning one, an amendment title and `FORM OF CREDIT AGREEMENT` are unchanged.
Checks: answer-key tests 11 failed on the old rule, then 120 passed with `test_expectations_backtest.py`
(exit 0). Back-test (`tools/expectations_backtest.py`) output byte-identical to origin/main's. In the
Mattress Firm case folder only the two exhibits change: `unrecognised`/None to `credit_agreement`/True;
the other nine files are unchanged. Gates: quality gate exit 1 on one finding in the answer-key file
(`tests/test_run_expectations.py:449` E501, not editable here), none in `run_expectations.py`;
`tools/pr_size.py` exit 1 with counted lines 0 and "copy mismatch" for `run_expectations.py` and
the test file, which `tools/copied-from.txt` lists as byte-identical copies (needs an `edited`
entry; outside this brief). Not verified: other issuers' title wording beyond the two exhibits; a
title-case sentence opener such as "Revolving credit agreement ..." as a page-1 line.

R-SB2-2 part 2 (lender presentation): `Public Lender Presentation September 11, 2014` and
`2014-09-11-ex99-1-public-lender-presentation.htm` were `unrecognised` for the same two causes (title
rule anchored at line start; dated/exhibit-prefixed name). The qualifier of the credit-agreement rule
is now one shared `_QUALIFIER` used by it and the lender-presentation rule; no other rule changes.
Checks: 3 new answer-key tests red on the old rule, then 143 passed (`test_run_expectations`,
`test_expectations_backtest`, `test_pr_size`). Mattress Firm folder: only the lender presentation
changes (`unrecognised` to `lender_presentation`); the credit agreements stay `credit_agreement`/True.
Back-test on origin/main with this rule file: output byte-identical to origin/main's. `tools/copied-from.txt`:
both `run_expectations` files moved to `edited`; `pr_size` 212 of 800, exit 0. Quality gate: 0 findings
against the merge base (exit 0); against `origin/main` it reports `apps/issuer-library/packaging/runtime.py`
because this branch predates PR #51 (that file is main's, not changed here). Not verified: other issuers'
lender-presentation titles; a title-case sentence opener such as "Public lender presentation ..." in a body.

R-SB2-2 fix 1 (review M1/L1): `_QUALIFIER` admitted connectives and determiners, so `JOINDER TO CREDIT
AGREEMENT`, `TERMINATION OF ...` and `Each/Our ... Credit Agreement contains` became credit agreements; the lender rule
also gained an unasked `the|this` lead-in. Now `_QUALIFIER` excludes to/of/and/under/for/with/each/our/such/any; `the|this` stays on the credit-agreement rule only.
Reviewer probe `r2_qualifier_admits_connectives.py`: 10 of 10 misclassified before, 0 after (exit 0).

2026-11-10 live_check free port (B.1 fourth PR, cherry-pick of fc08893a onto main cabbe619, no conflicts): `live_check.py` has no fixed `PORT`; `run_walk` starts the server with `bc.serve_free` and passes `args.port` to the walks; per-engine launch failures are recorded as `{name}-single-run` faults. The test `test_the_server_is_started_on_a_free_port_not_a_fixed_one` no longer binds port 53920 (its `serve` fake still fails on any fixed-port call; assertions unchanged). Tests: `tests/test_issuer_library_live_check.py` 54 passed (exit 0); `tools/quality_gate.py` exit 0; `tools/pr_size.py` exit 0. Not verified: a real browser launch failure per engine; `validate.py quick` and `browser` (run by the controller); any live server on a free port.

2026-11-10 Handoff outcome batch (R-SB2-1g/1i/1k and the reader Lows), `handoff_outcome.py`. CP-0 words are
now classed per module (own handoff or not) and the worst class wins; the row and the prose are both read
(`CP-4 BLOCKED:` plus `| CP-4 | READY |` is will_refuse); `Blocked: CP-1, CP-4` counts for each id listed
(1j boundary). Lows: text after a backticked `Module Status` value; the markup strip is one linear pass (a 1 MB
line is ~0.06 s); front matter is not scanned for fences; lines split on `\n`/`\r\n` only. The blockquote
fence case did NOT hold (a fence inside a quote was read as text); fixed in the final reader batch below. Key (another agent's): 13 `b1-` cases red before, `tests/test_handoff_outcome_status.py`
134 passed after; with flow_check, backtest and live_check tests 258 passed; lead probe `probe_1j_rows.py` exit 0.
Back-test output byte-identical to the parent's. Offline re-read of copies of retained C1 and C1n handoffs
(`actual_of`, old vs new, per module and refused flag): no change (C1 CP-4 limited, CP-1 limited, C1n CP-4
will_refuse). Not verified: `outcome_faults` itself re-run (it only forwards `actual_of`); a live run.
Batch review fix 1: the `Blocked: CP-1, CP-4` form is read in CP-0 prose only, not in a module's own handoff (`Not blocked: CP-4.` there no longer gives will_refuse); probe `hb_own_listed_case.py` exit 1 before, 0 after.
R-SB2-1k refinement: the `Blocked: CP-1, CP-4` form counts only when the status word starts the line (list/markup characters only), is not negated (`Not blocked:`, `No longer blocked:`, `Unblocked:`), and the ids stop at the first word that is not an id or `,` `&` `/` `and`; 7 `b1k2-` cases red before, 157 passed after; probes `hb_cp0_status_owned_by_prior_id.py`, `hb_own_listed_case.py`, `probe_1j_rows.py` exit 0.

## 2026-11-10 Task 7: run-lock after a failed spawn, three test flakes

Defect (Low, concurrency): `hold_worker_lock` flocks `worker.lock`; a child forked by another thread
while that fd is open inherits the locked file until exec, so after a failed spawn the next start's
`LOCK_NB` failed and answered 500 instead of 503. Fix: `launch_worker` removes `worker.lock` after
`release_lock` when `Engine.start` raised (`remove_failed_run_lock`: FileNotFoundError ignored, other
OSError logged). Answer key `test_a_stray_fork_holding_the_run_lock_does_not_turn_a_failed_spawn_retry_into_500`
red (503, 500) then green; `probe_stray_fork.py` and `probe_observe.py` exit 0; the existing `{503: 8}` test unchanged.
The lock removal does not create a second worker (item 2's settle race remains open for the next PR): it happens only where no process was spawned (the failed spawn
and the status-save failure, both before any worker exists), so no worker holds the old inode. The
cross-instance guard is `start.claim`, held from before `hold_worker_lock` until after the unlink
(`launch_worker` is the only caller of `hold_worker_lock`), not `lib.lock`; the next start's `O_CREAT`
makes a fresh inode and locks that; the stray fork holds only the unlinked old one and is not a worker.
`worker_alive` never judges a job dead from an unlinked inode: after a won flock, `st_nlink == 0` means a
failed start removed the file, so it reopens the path and rechecks (3 tries, then OSError; a missing path
is "not alive" as before). A live worker's inode is linked, so its lock is never won on a dead one.
Success path unchanged (the lock stays for the worker's life).
Fold-in key tests (save-failure stray fork, stale-inode adoption/watch_worker) red on the pre-fix code, green after; t7adv_stale_inode_adoption/liveness/save_failure_stray_fork exit 1 before, 0 after; items 2/4 probes unchanged (exit 1).
Flakes (tests only, no sleeps): new_run progress/stages tests wait for `.summary-line` / `#module-stages li`
before indexing; `test_a_failed_list_fetch_is_retried...` waited a fixed 50 ms after each tick, too short
under load for the list fetch, so each tick now waits for the text or table it asserts. 20/20 passes each.
Sweep (CI 42746147348, `...same_hint[interrupted]`): `open_row` clicked `b[0]` of `#recent-jobs tbody th button` 50 ms after the
visit, before the list fetch had drawn it (`Cannot read properties of undefined (reading 'click')`); it now waits for the row, `launched`
waits for the first status draw, two other list/timer reads wait too. Forced red (list delayed 400 ms) then green; 10/10 file passes.
Not verified: other platforms' (Windows) lock-removal order; a worker started on a path where Popen succeeded then failed later.

2026-11-10 Final status-reader batch (R-SB2-1l/1m/1n, blockquote fence, 1k case and heading), `handoff_outcome.py`. Every mention of the id is read and the worst class wins (own handoff and CP-0); an id-then-status match stops at `.`/`;` before a space or line end; CP-0 text is fence-filtered like own handoffs; `> ` prefixes are stripped before the fence rule and a fence opened in a quote ends at the first unquoted line; `Blocked: cp-4` and `## Blocked: CP-4` count (the status-colon-id form counts at line start only, so CP-6 in `Ready: CP-5. Blocked: CP-6.` is not_reached). Every status word in a mention's window is read and the worst wins (`CP-4 READY for drafting but BLOCKED for filing` is will_refuse). The reader is linear: the 1 MB timing tests in the key finish in under 1 s. Key (another agent's): `rf-` and `rf2-` cases in `tests/test_handoff_outcome_status.py`; 212 pass in that file after fix round 2 (the 12 `rf-` red before round 1, 6 `rf2-` red before round 2).
Final batch fix 2 (re-review H1): the mention window is read in a lookahead (`(?=(...))`) so only the id is consumed and a second mention of the same id inside the window is matched (`CP-4 READY ..., then CP-4 BLOCKED ...` is will_refuse, not ready); window bounds unchanged. Back-test output byte-identical to 3ec114cf.
