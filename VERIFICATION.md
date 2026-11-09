# Verification record

Keep one running record here. A pass applies only to the stated scope. Preserve
earlier run artifacts; record a new attempt when instructions or outputs change.

The [current remaining-module record](runs/cpos-sol-remaining-20261105/verification.json)
contains the settled CP-6 timeout cost, the corrected TDG annual publication, the
live CP-8 comparison and checks of the five broader report bundles. The older
entries below retain their historical case scope.

Older entries are in [docs/VERIFICATION-ARCHIVE.md](docs/VERIFICATION-ARCHIVE.md), verbatim and in their original order; new entries go here.

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

