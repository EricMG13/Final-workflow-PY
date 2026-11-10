# Verification record

Keep one running record here. A pass applies only to the stated scope. Preserve
earlier run artifacts; record a new attempt when instructions or outputs change.

The [current remaining-module record](runs/cpos-sol-remaining-20261105/verification.json)
contains the settled CP-6 timeout cost, the corrected TDG annual publication, the
live CP-8 comparison and checks of the five broader report bundles. The older
entries below retain their historical case scope.

Older entries are in [docs/VERIFICATION-ARCHIVE.md](docs/VERIFICATION-ARCHIVE.md), verbatim and in their original order; new entries go here.

## 2026-11-10 — CI flake on #82: failed-render retry test raced the first list render (SB2, branch `claude/sb2-flake82`)

- The flake: `test_a_failed_render_is_retried_on_the_next_refresh`, CI run 42788732481, attempt 1.
- Cause: a test race. NewRun returned before the first list render. On a slow runner that render hit the injected fault, so the poll interval was never created and the tick had nothing to retry.
- Key d2ddca8b (`test_a_failed_render_is_retried_when_the_first_list_reply_is_slow`) delays the first list reply by 1 s in the page and failed 5/5 runs before the fix. The fix: `failed_render_is_retried` waits for the first table before injecting the fault.
- The product gap, where a failed first render is never retried, is fixed in a separate PR.
- Not verified: the CI runner timing itself; only the 1 s delay key reproduces it locally.


## 2026-11-10 — #88 round 2: racy test reads converted to waits (SB2, branch `claude/sb2-flake82`)

- Answer keys (not edited): slow-reply mode `FW_SLOW_API_MS` (8825d76d), `test_review_shows_after_a_slow_review_reply`, `test_settings_shows_library_stopped_after_a_slow_quit_reply`, `test_a_failed_render_is_retried_when_the_first_list_reply_is_slow`.
- Reads converted in tests/test_issuer_library_app.py (the app is unchanged): review_sends_the_folder (2), only_an_explicitly_confirmed_start (2), a_lost_start_response (3), a_finished_run [complete][stopped] (2), a_failed_run_offers_nothing (1), a_missing_provider_key (1), launch() and its 4 users (the helper waits), a_list_refresh_keeps_the_focused_row (2 ticks), polling_stops_while_new_run_is_hidden (2), a_failed_list_fetch (1), the_list_error_shows_whichever_list_consumer_fires_first [x2] (1 each), the settings quit read (1). Mechanism: a page script counts replies the app has finished reading; the helper that performs the click or tick waits until every request sent to that path is answered, then the state asserted (review step, open-run, rebuilt table, "Library stopped") is read. No sleep, no longer timeout, no assertion weakened.
- Proof: before, `FW_SLOW_API_MS=300` and `=1500` each failed 17 of 66; after, both 0 failed. The two targeted keys (review reply 1000 ms, quit reply 1000 ms) pass without being edited. Default run 66 passed. 20 runs under `FW_SLOW_API_MS=1500 FW_CPU_THROTTLE=4` (off by default, CDP `Emulation.setCPUThrottlingRate`): 20/20 exit 0. A first 20-run pass found 8/20 failures (`test_loading_a_context_from_before_the_classification...`, a CSP refusal of `wait_for_function` in `ContextForm.load`) and 1/20 (`polling_stops...`, an unwaited late list reply); both fixed in the test file and the 20 runs repeated.
- Shared harness fix: `ContextForm.__init__` and `ContextForm.load` (tests/issuer_library_browser.py) now poll with `until`, not `wait_for_function`, whose string eval the form's CSP refuses once the first check is not yet true; the per-file workaround in the `form` fixture is removed. Proof: tests/test_issuer_library_context_embed.py under a 4x CPU throttle (out-of-repo pytest plugin) fails 3/3 with the old harness (a `cp -R`-style copy, CSP EvalError in `load`), and passes 20/20 with the new one.
- Not verified: CI runner timing itself (a 4x CPU throttle and a 1.5 s reply delay stand in for it); screen-only tests (open_store navigation) were not individually audited beyond passing under both delays; `open_app` called directly in test_the_preview_names_every_module is not slowed by the mode. Not verified in the harness fix: other callers of `until` timing beyond 10 s.

## 2026-11-10 — Context import load invariant: a loaded file keeps every value or is refused (PR B, branch `claude/sb2-context-invariant`)

- Scope: the context form (`docs/templates/context-form.html`, normative; `apps/issuer-library/web/context-form.html`, same edit byte for byte). One Mac, offline, real Chromium; no provider calls.
- After `fill(o); vis(); build()` the form compares the file with what `build()` writes, both ways: text trimmed at the ends, blank equals missing, everything else exact including type (booleans, numbers vs strings, null). Any difference refuses the load ("Not loaded. <file>: <path> ... Nothing was changed.", class `bad`, up to 10 paths then "and N more") and restores the form (`saveForm`/`restoreForm`). An exception in the trial also refuses visibly. `closedProblem`, `droppedProblem`, the row-cap note and the listed_equity note are deleted; an empty `run.pathway` no longer counts as touched, so `vis()` cannot throw and the load names `run.pathway`.
- Gates: roundtrip, embed, live_check and product/test_context tests, 496 passed (answer-key tests unedited, K1's 97 params green); lead probe pr87_roundtrip_hunt: every row OK except `instr_lf_interior` (refused, as ruled); ctxr_edges3 exit 0 (was 1); ctxr_all_contexts over 97 files exit 0 (94 server-accepted all loaded, 3 refused); ctxr_sync_reverts exit 0 (regenerated form equals the committed web form); quality gate exit 0 (after the key's comment wrap 78bab52e). Review follow-up: a container on one side against a blank, missing or scalar value on the other is now a difference (an empty `{}` or `[]` key no longer loads silently); the reviewer's probe prb_hunt shows every unknown-key, empty-container and missing-scenarios row refused.
- Not verified: a server-accepted file whose single-line text field, guarantor item or alias holds an interior line feed or carriage return cannot be loaded through the form, nor one with tenor or price talk on a non-Primary run (accepted limit; each is refused, the server accepts them); U+FEFF at the ends of a text value is trimmed like a space; duplicate JSON keys (predate this change, owner); a future form row cap below the server's `_MAX_*` would refuse server-valid files (no test pins the two); cases outside the 97 files; the in-app (embedded) load path beyond the roundtrip tests; browsers other than the Chromium the tests drive.


## 2026-11-10 — A-live PR 1 (F1/F2/F4, Returns Blocked) (R-ALIVE-rulings.md, branch `claude/sb2-alive-forecast`)

Offline forecast change against the key written first by another agent (d01fe3a2, 8b901cb2; not edited): CP-5 inherits Returns Blocked from a Blocked CP-4 (forecast-only edge, registry untouched); counted Limited rules for CP-2D (legal documents `none`) and CP-3C (no step-up); the CP-4 wording and the on-screen label. Frozen-case change hand-derived: c1r counted_total 0 to 1 because of F4 alone (CP-3C, no step-up; CP-5 inherits it, uncounted); F2 cannot fire there because c1r's context declares legal_documents `executed`. Exhibit recognition (both credit-agreement exhibits are executed under the launcher's HTML reader) explains only why the review probe's CP-4 row for c1r was spurious. Scope: forecast rules only, one issuer/date (TDG FY2024, older public source); no live run. 25 red tests green; the five named test files 607 passed, 1 skipped (paid). Not verified: any live module behaviour; cpos_launch.py "Will refuse" docstring left as is.

## 2026-11-10 — Verification record: 2026-11-08 entries archived (SB3, branch `claude/sb3-verification-archive-2`)

- Moved verbatim on main 6ed04ff5 (part 2 of 2, after #85): the 271 lines of the fourteen 2026-11-08 entries, from "Plan 3 Task 9" to "Run activity page", with no other dates. They go to the top of docs/VERIFICATION-ARCHIVE.md, above the 2026-11-07 entries, so it stays newest first; the header line names the move.
- Proof: sha256 of the block `32ecc5b5…20c91f` before (VERIFICATION.md lines 100-370) and after (archive lines 5-275). The rest of VERIFICATION.md and the archive's previous body are identical (`diff`, exit 0). Combined line count is 6,822 before and after (apart from this entry and the header line).
- Not verified: none beyond these checks; documentation only.

## 2026-11-10 — Verification record: 2026-11-07 entries archived (SB3, branch `claude/sb3-verification-archive`)

- Moved verbatim on main 71d44bef: the 237 lines of the seven 2026-11-07 entries, from "Phase 3 and branch end" to "Nightly full-suite run", with no other dates. They go to the top of docs/VERIFICATION-ARCHIVE.md after its header, so it stays newest first; the header line names the move.
- The 2026-11-08 entries follow in a second PR, placed above these. One PR would have been 1,024 counted lines (pr_size counts a move twice), over the 800 limit.
- Proof: sha256 of the block `bd84b3bb…c528a7` before (VERIFICATION.md lines 364-600) and after (archive lines 5-241). The rest of VERIFICATION.md and the archive's previous body are identical (`diff`, exit 0). Combined line count is 6,815 before and after (apart from this entry and the header line).
- Not verified: none beyond these checks; documentation only.

## 2026-11-10 — Phase 1 checkpoint: full offline suite on main bc34228c, new failures classified (branch `claude/sb3-known-failures`)

- Scope: one Mac, offline, not run on the CI runner.
- Full offline suite on main bc34228c: 118 failures, 92 known, 26 new.
- Of the 26: 6 fail identically in an upstream clone at dd3dfa18 (class A, now listed in `tests/nightly-known-failures.txt`, causes A1-A5 as in the classification document); 20 depend on machine-local Deploy Workflow data and also fail upstream on this machine (not listed, since they skip on CI): C1 13 ids (live-run stores under `Deploy Workflow/artifacts/model-testing/cp1h-live-*`), C2 1 id (public corpus v1 miss count), C3 6 ids (corpus plus untracked `work/model-testing/mapping/output/*-report.md`).
- 0 caused by the Python build.
- Evidence: `.superpowers/checkpoint/new-failures/classification.md` and its `NN.wt.out` / `NN.upstream.out` files.
- Not verified: the CI runner; whether to list the class-C ids for local full runs (owner's call); A4's cause (not traced); A5 found by code reading, not bisected.

## 2026-11-10 — Plan 3 live check C2: Primary pro forma pathway, Mattress Firm pre-closing (SB3, branch `claude/sb3-c2-record`)

- **Scope:** public proxy for a private Primary deal, older source (2014), Mattress Firm Holding Corp. as of 2014-09-11 only. One live run: build `d52c4ef2`, `sol-medium`, modules CP-0 CP-1 CP-1A CP-1D CP-2, cap USD 15, launched only on the owner's go-ahead in the SB3 session. Run `web-f126f83e49773a9e5d16ee6af9284481`, USD 1.71466120, retained at `.superpowers/live/plan-3/c2-d52c4ef2/`. Key frozen before the run in `cases/live-mattress-firm-2014/c2/`.
- **Rehearsal, before the paid run:** fake engine with provider keys unset (rehearsal scope only, not model evidence), at `d52c4ef2` after #70. It reached delivery: 75 passed, 5 forecast faults, all because fake handoffs state no status. The delivered `pro-forma` block (`report-view.json` sha256 `1d8f32a8…`) equals the key's `cp2-full-valid` tables cell for cell. With `FAKE_MALFORMED=CP-2`, the checker's repair text read: `Pro forma rows wrong: Pro forma capitalisation: write exactly one `Cash` row.`
- **Result:** the run completed and wrote its report. live_check exited 1: 75 passed, 21 faults. Purpose by purpose:
  - **Pro forma capitalisation and leverage: PASS.** Pro forma total debt 767, TLB 720, ABL 42 and as-marketed 3.29x (LP 3.3x) reach the report byte-equal to the CP-2 handoff, labelled, with missing values kept missing. The balance-sheet date 2014-07-29 matches the key. Differences:
    - Equipment and other notes (1 + 4) were withheld as Not supplied: a run Low, a gap rather than an invention.
    - The key's 466 adjustment does not foot (302 + 466 = 768, against 767); it is what the source prints, so the key needs no change and keeps its note.
  - **Sources and uses: FAIL as delivered.** The table was not routed to the report. Total sources is 903, not 821, because `PRO_FORMA_CP1A` said to use the user-entered facility sizes, which put the 125 ABL commitment in place of the 42 draw. The model labelled the row "commitment, not draw" and logged the gap. Uses (821) equal the key.
  - Every module took one repair turn, all for the same instruction conflict: the view heading was placed before the reader summary's tables. None was a pro forma repair; all three pro forma checks passed on the first draft.
- **Faults (assessment by mx-precise, offline on a copy, no rerun; SDD `c2-assessment.md`):**
  - Forecast: CP-1 and CP-1A came out limited via CP-0. This is the accepted A-live F3 disagreement.
  - Forecast: CP-1D came out Restricted because its instructions name scripts the app does not expose. New; fixed by R-C2-3.
  - Untraced numbers (15), none unsourced or wrong:
    - 8 hand ×1000 rescales (run Lows; R-C2-7).
    - 2 conversions stated in the handoff but done with `calculate`, written in E-notation (R-C2-4).
    - 4 sums with a hand-scaled operand.
    - 1 unit divisor, 0.001.
    - "ASC 842", a standard's name.
  - Literal 821: present in the source and in the CP-1A handoff, but not in a routed section (R-C2-2).
- **Lead rulings R-C2-1 to R-C2-7:**
  - R-C2-1: funded amounts only, failing closed to Not supplied.
  - R-C2-2: route CP-1A Sources and uses as a tab of the pro-forma block.
  - R-C2-3: a missing script alone does not restrict a module.
  - R-C2-4: flow_check reads stated conversions and standards' names (SB2).
  - R-C2-5: each tab states its own unit.
  - R-C2-6: the view heading comes after the reader summary's tables.
  - R-C2-7: keep the source unit; convert with `calculate` and say so.
  - Key: literal 821 moves to the routed S&U tab; 466 already is what the source prints, so it is unchanged (controller ruling u7).
  - Plan 4 needs only the pro forma leverage rows, which passed.
- **Input differed from the frozen case (found afterwards):** the run's `intake/web-f126f83e…/context.json` has `deal_terms[0].instrument` `""` where `cases/live-mattress-firm-2014/c2/context.json` has `"ABL revolver"` (size 125 kept; Term loan B kept). live_check loads the case file through the app's context editor, so the app's import probably dropped it; it has not been traced. The model still identified the ABL from the documents. Reported to the lead.
- **Not verified:**
  - the rendered report in a browser: the block note "USD millions" over a thousands tab was read from `report-view.json` (R-C2-5);
  - the fixes above, live. Live proof rides on C1r, after R-C2-1/-2/-6/-7 merge;
  - the cause of the dropped instrument name.

## 2026-11-10 — pr_size: an edited copy counts against the merge base when the base holds it (R-PRSIZE-1, branch `sb3-prsize`)

- **Rule:** in `tools/pr_size.py`, an `edited <path>` entry whose file exists at `git merge-base <base> HEAD` counts its numstat for merge-base...HEAD; one absent there counts its whole drift from the source revision, with the binary fallbacks as before. Plain copies keep the byte-identity check; fixtures, lockfiles and binaries stay excluded. The limit stays 800; `tools/copied-from.txt` stays the provenance record.
- **Reason:** counting every edited file by its drift from the source recounted history. A later PR touching `cpos_launch.py` would have recounted the ~720 lines already counted and reviewed in #53, whose own count was 797/800.
- **Key:** `tests/fixtures/pr-size/scenarios.json` (sha256 `01ac9082...e8`), 19 scenarios replayed in `tests/test_pr_size.py`; 19/19 pass. Before the change 7 failed with the key's "today" numbers (65, 85, 0, 860, 861, 100, 10). `edited_setup` no longer puts a file at base (scenarios 3 and 4); scenario 17 covers the old shape.
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

## 2026-11-10 Plan 2 PR1: acceptance UI (branch `claude/sb2-acceptance-ui`, R-SB2-7)

Scope: Plan 2 Task 7 items 2 and 6 only. The Review step opens with `#expected-outcomes` (heading, caption, one `tr[data-id]` per expectation; "This run" first, then modules in run order, inherited rows under their producer, "Not counted" on uncounted rows, a "Why we expect this" disclosure) and, when `counted` is non-empty, `#run-accept` ("I accept these N items"). Start needs `#run-confirm` and, when N > 0, `#run-accept`; every reset clears both. The Start body carries `accept_limitations` when the review reply carries `counted`. `start_run` validates the optional key as a boolean (non-boolean: 400) with no other effect. `browser_check` ticks the box when shown; `live_check --accept-limitations` ticks it, and without the flag and N > 0 refuses before Start naming the flag and N.

Checks (exit codes): the four test files (new_run, jobs, live_check, app) 340 passed, 2 skipped, exit 0; the 27 new tests 3 times, 0 failures; `tools/pr_size.py` 479, exit 0; `tools/quality_gate.py --base <merge-base>` 0 findings, exit 0.

The browser walk goes through the real bridge review. Its review counts 4 items (`run:run-financials-management-claims`, `CP-1:cp1-no-financial-report-recognised`, `CP-4:cp4-declared-none`, `CP-3:cp3-no-quotes-no-talk`), so the walk exercises N > 0 ("Start stays disabled until the acceptance is ticked" passes in both walks).

Commit 841d1d00 re-anchored two browser_check review checks to the module list and the Source files disclosure, because the verbatim caption contains "CP-0" and the first disclosure is now a table row's. `validate.py browser` gives 88 passed, 0 failed, exit 0.

Info: without `--accept-limitations` and with counted items, live_check fails the walk with a RuntimeError before Start (recorded as an exception fault, exit 1), rather than a Refusal (exit 2). The box is never ticked.

Not verified: `validate.py` quick and browser (the controller runs them); a real bridge review reply; real-browser layout of the table.

## 2026-11-10 Run lock items 2 and 4: a stale liveness verdict never settles a live job; any spawn exception refuses; POSIX only for item 2 (branch `claude/sb2-run-lock-items24`)

Item 2 (pre-existing): `settle_job` no longer acts on `worker_alive`'s verdict. It takes the worker lock itself
(`dead_worker_proof`: `O_CREAT` open, `flock` LOCK_NB; a lock it cannot take means a worker, and a missing file is
created so no start can take the lock meanwhile), reads status.json under it, and before the write checks the held
inode is still the path's (`lstat` vs `fstat` dev/ino, `st_nlink`). Not proven: `WorkerMayStillRun`, which
`finish_job` answers by leaving the job active (`watch_worker` and `watch` keep polling) and adoption by watching it.
Call path kept: `settle_job` <- `finish_job` <- `watch_worker`. Windows: `worker_alive` is re-checked at settle, otherwise unchanged; item 2's race stays open there (`dead_worker_proof` holds nothing).
Fix round 1 (review M1, M2, L1): a missing run folder or an unopenable lock means nothing to settle (`nothing_to_settle`; the job is finished, status.json left as it is, the unopenable case logged); the lock is flocked on an `O_RDONLY` descriptor so a read-only lock file is still proven dead. On POSIX `launch_worker` unlinks `worker.lock` before `release_lock` on a failed start, which closes the window between the inode check and the write (precondition: the failed start's `failed` write fails and a settle is descheduled between `still_valid()` and `save_json`); Windows keeps release-then-remove and the window stays open there. The inode check (`still_the_path`) is covered by the re-staged M2 key test `test_a_settle_holding_the_inode_about_to_be_unlinked_never_marks_a_live_retry_interrupted`; the race test's `between_release_and_unlink` case also covers it (it fails under a `still_the_path` that is always True).
Batch (Low/Info, no review round): only a permanent lock-open error gives `nothing_to_settle` (ENOENT, ENOTDIR, EACCES, EPERM, EROFS, ELOOP, EISDIR, ENXIO, EOPNOTSUPP, a non-regular file); any other (EMFILE, ENFILE, ENOMEM, EIO) gives `None`, so a job whose lock holder outlives its worker stays active and a second Start answers 409 (`watch_worker` retries). Key `test_a_transient_lock_open_error_keeps_a_held_lock_job_active`: red on bed959a3 (job left active_jobs), green after; the file with `test_issuer_library_quit.py` 184 passed 2 skipped; the new and settle tests 20/20. Probes exit 0: i24rr_transient_open_error_finishes_held_lock, i24rr_emfile_live_descendant, i24rr_emfile_dead_worker, i24rr_settle_live_holder_planted, i24rr_unlink_first_two_instances, the other i24_* (run_folder_gone, lock_unwritable, residual_write_window, folder_gone, base_exception, created_lock) and `_v2` copies, all t7adv_*, t7rr_worker_alive_bounds, probe_stray_fork, probe_observe.
M1 end state, accepted: with the run folder present and the lock unopenable for a permanent reason (or a planted non-regular file) the job leaves active jobs, status.json stays `running`, the run list shows `running` and resume answers 409 until the lock is repaired and the app relaunched (`i24rr_unopenable_dead_job_running` exits 1 by design). Writing `interrupted` without lock proof would be unsafe; main did so.
`i24_held_stale_inode_settle.py` and `i24_settle_holds_unlinked_inode.py` now exit 1 by design (unlink-first removes the gap they stage); the `_v2` copies replace them (exit 0). Round key RED to GREEN: the fix-round-1 key tests red on fd568851, green on bed959a3.
Info: with unlink-first, a retry that coincides with another instance's settle holding the fresh inode answers 500 "Could not prepare the run lock ... Start can be tried again"; the next retry answers 202.
Item 4: `launch_worker` catches `Exception` (not `BaseException`) from `engine.start`, logs a warning with the job id and error
(traceback), and takes the OSError path: claim released, lock removed, status failed, 503 "no model call was made".
Key (eb5c9b69, another agent): 5 tests red before (2 settle-race, 3 spawn-exception), 161 passed 2 skipped after
for the file; the 5 tests 20/20. Probes exit 0: t7adv_settle_toctou_preexisting, t7adv_non_oserror_spawn,
t7adv_stale_inode_adoption/liveness, t7adv_save_failure_stray_fork, t7adv_one_worker_invariant,
t7adv_removal_path_swaps, t7rr_worker_alive_bounds, probe_stray_fork, probe_observe. t7rr_held_probe_lock_vs_removal
exits 1 (corrected 2026-11-10; the reason first stated here was wrong): it now fails at the probe's own lock attempt,
`fcntl.flock(fd, LOCK_EX | LOCK_NB)  # won: release_lock already ran` in `remove_after_a_probe_wins`, which raises
`BlockingIOError: [Errno 35] Resource temporarily unavailable` (the lock is not won after unlink-first). The test for
that case passes because settle re-verifies the inode and declines.
Not verified: Windows (item 2 open there); the browser and `validate.py` gates.

## 2026-11-10 Plan 2 Task 6a (start requires and records acceptance; branch `claude/sb2-task6-acceptance`)

Scope: `src/issuer_library/jobs.py` (`start_run`), `apps/issuer-library/engine/bridge.py` (`start`).
Change: `start_run` accepts `accept_limitations` (boolean only), reads `counted` inside `lib.lock` before
`start.claim`: missing or malformed gives 409 "Review this run again before starting"; non-empty without
acceptance gives 400 "Accept the listed limitations before starting". `bridge.start`, after the stale
re-check and before `run_live_handoffs`, adds `accepted: <ids>|none` to the receipt, writes
`runs/<id>/expectations.json` (six keys from the approved review) and `runs/<id>/context.json` (byte copy;
sha256 must equal the plan's `context` pin, else the stale error and the run folder `launch` just made is
removed). `launch` writes neither file. The receipt parser (`check_ruling`) reads only lifts/by/date/configs
lines, each exactly once; the extra line is ignored.
Checks (head after the lock-error follow-up): the four-file pytest (jobs, cpos_app, quit, app) is 333 passed, 2 skipped,
1 failed (exit 1) at that head: `test_a_lock_error_other_than_contention_keeps_the_job_watched` (fixed by ae367db2, passes now; see below); pr_size
exit 0 (501 of 800); quality_gate exit 0. The earlier 13 RED / 45 failures are resolved (key writer's follow-up commits).
Context-pin key test (7006eeed): `t6a_key_reaches_pin_check` path, the pin check is reached.
Lock-error follow-up (#73, lead 6a-extra): `dead_worker_proof` caught only BlockingIOError at its lock call, so ENOLCK
(a network share) escaped `settle_job` and killed the watch thread, leaving the job active with no watcher. Any other
OSError there now logs a warning (with the error text) and yields None ("cannot prove dead"), so the job stays watched;
open-error and BlockingIOError handling unchanged. RED: `pr73_settle_flock_error_strands_job.py` exit 1 and the key test
failed with `the watch thread died on a lock error: ["OSError(77, 'No locks available')"]`. GREEN: the probe exits 0
("watcher alive ... died: [] | active: False | status: interrupted"); at that head the key test got past that assertion but still
failed (later fixed by ae367db2): it never advances its FakeClock and `app.pause` is real sleep, so after the settle `finish_job` loops forever in
`notify.tab_watching` (finished == now, no tab poll) and `watcher.join(5)` leaves the thread alive. The test needs a
clock-advancing `app.pause` or `app.watched`; the implementer may not edit tests. Probes exit 0: i24rr_emfile_dead_worker,
i24rr_emfile_live_descendant, i24rr_settle_live_holder_planted, i24rr_transient_open_error_finishes_held_lock,
i24rr_unlink_first_two_instances, i24_held_stale_inode_settle_v2, i24_settle_holds_unlinked_inode_v2,
t6a_ctx_swap_after_launch, t6a_concurrent_starts.
Recorded for Phase 3 (lead, no action): a KeyboardInterrupt during start leaves the claim held until the next adopt;
Windows lock semantics are unverified, including a read-only lock file.
PR2 live_check guard (lead review of #74): `--accept-limitations` prints the N it accepts and raises `Refusal` (exit 2, before tick and Start) when it differs from the case's frozen `counted_total`; `attempt` re-raises a `Refusal`; without `--case` the N is printed but nothing is compared.
PR2 live_check, ruling: a paid `--accept-limitations` run without `--case` is refused in `live_check.parse` (exit 2, before any app start); with `--rehearse` the no-case path still prints and ticks.
PR2 live_check, rehearsal ruling: `stage2_faults` compares `runs/<id>/context.json` bytes with `intake/<id>/context.json` (the reviewed bytes) and its parsed JSON with the case context; with no intake context file the old byte comparison with the case file stays.
PR2 stacked (`claude/sb2-pr2-frozen-count`, key 3bb0fd37, R-SB2-6 M1+L1): with a case loaded `walk` refuses (`Refusal`, exit 2, before tick and Start) unless `counted_total` is `type(v) is int` and >= 0, and whenever the page's N (0 without a box) differs from it, with or without the flag; no case: unchanged. `attempt` docstring names the `ends_run` re-raise. Gates exit 0: live_check tests 3x (89 passed), probes pr2rr_null_frozen_count_ticks and pr2rr_flagless_zero_vs_frozen, live_check+jobs+cpos_app pytest (367 passed, 2 skipped), quality_gate --base e722502a (see commit).
Not verified: the browser UI sending `accept_limitations`; a real run's receipt.

## 2026-11-10 Task 7: run-lock after a failed spawn, three test flakes

Defect (Low, concurrency): `hold_worker_lock` flocks `worker.lock`; a child forked by another thread
while that fd is open inherits the locked file until exec, so after a failed spawn the next start's
`LOCK_NB` failed and answered 500 instead of 503. Fix: `launch_worker` removes `worker.lock` after
`release_lock` when `Engine.start` raised (`remove_failed_run_lock`: FileNotFoundError ignored, other
OSError logged). Answer key `test_a_stray_fork_holding_the_run_lock_does_not_turn_a_failed_spawn_retry_into_500`
red (503, 500) then green; `probe_stray_fork.py` and `probe_observe.py` exit 0; the existing `{503: 8}` test unchanged.
The lock removal does not create a second worker (item 2's settle race was open here and is closed by the items 2 and 4 entry above it): it happens only where no process was spawned (the failed spawn
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

## 2026-11-10 List-fetch flake: an injected list failure lasts until the test has seen it (test race, branch `claude/sb2-list-fetch-flake`)

Cause (CI timeout waiting for "Could not load recent runs"): the `listed()` route in `NewRun` aborted only the
first list request, then cleared `fail_list`. `window.__tick()` fires every captured interval in registration order,
and two consume `/api/runs/list`: the app-wide `watchRuns` (failure only `console.warn`, retried in 5 s) and the page
poll's `recent()` (the only writer of the error). Registration order depends on whether boot's `watchRuns()` or
`show()`'s `recent()` resolves first; when `watchRuns` came first it ate the single abort, `recent()` succeeded and the
error never appeared. A test race, product correct: a real `recent()` failure shows the error; `watchRuns` failures are
deliberately silent. Fix (tests only): `fail_list` aborts every list request until the test clears it, and
`test_a_failed_list_fetch_is_retried...` clears it after seeing the error, before its second tick; the other `fail_list`
user, the key test `test_the_list_error_shows_whichever_list_consumer_fires_first`, already clears it. No assertion changed.
Evidence: key test `[watch_first]` failed 3/3 on the old helper, then passed 10/10 (and `[poll_first]` 10/10); the two
`fail_list` tests 10/10; `tests/test_issuer_library_app.py` 56 passed.
Not verified: the CI runner's actual interleaving; only the two registration orders forced by the key test.

## 2026-11-10 App tests: read helpers wait for the render they read (test race, branch `claude/sb2-app-test-waits`)

Cause (CI `test_a_null_module_detail_does_not_break_the_row`, `IndexError` at `run.recent()[0]`, run 42770895261): `NewRun`
helpers read rendered DOM right after a fixed 50 ms `settle()`, before the `/api/runs/list|review|status` reply had
rendered; a slow runner read an empty `#recent-jobs`. A test race, product correct. Change (tests only, `tests/test_issuer_library_app.py`):
`NewRun.rendered()` wraps `page.wait_for_function` (10 s, fails naming the condition); `recent()` and `revisit()` wait for
`#recent-jobs` to hold a node (rows, the empty-list text or the load error), `stages()` for `#module-stages li`,
`progress()` for `#run-progress .summary-line`, `text(id)` for non-empty text. No test, expected value or `hold_replies` changed.
Evidence: the 7 forced-delay key tests (`hold_replies`, 1.5 s) failed 7/7 on the old helpers and pass now; the file passes 63/63, 5 runs.
Review fix (Medium): `test_a_failed_render_is_retried_on_the_next_refresh` read `#recent-jobs` after `tick()` while the boot table still satisfied the helper's wait; it now `until`-waits for the `Could not load` text before its asserts. It also waits for `#recent-jobs table` before the final `exists` assert after the second tick. Scratch copy outside the worktree with the reviewer's `delay_next` exactly as written (every list reply held 1.5 s): without the second wait exit 1 (`exists('#recent-jobs table')` false), with both waits exit 0 (the first wait alone, one-shot delay: exit 1 without, 0 with); real worktree 30/30 passes, file 63/63.
Not verified: the CI runner's own timing; reads after `tick()` of other changed (not first) renders, `hidden`/`disabled`/`exists` booleans and direct `page.evaluate` clicks are still unwaited.

## 2026-11-10 R-SB2-2a positive qualifier lists

`guess_kind`: the capitalised-word denylist `_QUALIFIER` is replaced by two positive lists in
`run_expectations.py`. Credit agreement: ABL, Term Loan, Revolving, Senior, Secured, Unsecured, First/Second/Third
Lien, Superpriority, Bridge, DIP, and `[ordinal] Amended and Restated`, in any combination, or `the|this` (optionally
`amended and restated`); `Credit Agreement Joinder` is excluded. Lender presentation: Public, Private, Bank,
Syndicate or none, plus `Lenders' Presentation`. Joinder In, Release From, Existing/Prior/Amended openers and
`Investor ...` no longer match; a 10-K cover with an `Investor Lender Presentation` line stays financial_report.
Answer key (c281e708, not edited): 27 tests red on the old rule, 201 passed in `test_run_expectations` after.
Probes `denylist_residue`, `adv_kinds`, `r2_qualifier_residue`, `r2_qualifier_admits_connectives`: exit 0.
Back-test (`expectations_backtest --out`) with origin/main's rule file vs this one on the same tree: identical.
Not verified: qualifiers on issuer titles outside the key (a new facility word needs adding to the list).

R-SB2-2a fix round 1 (review M1/M2/L1/I1): the `Amended and Restated` ordinal is a closed list (First to Tenth, 1st to
10th; fix round 2 corrects the numeric forms, which `.title()` had turned into `1St` and which now match as written,
`1st` or `1ST`), so `Existing/Prior/Proposed Amended and Restated ...` no longer match; facility words and `[ordinal] Amended and
Restated` combine in any order (`AMENDED AND RESTATED REVOLVING CREDIT AGREEMENT`, file name included); qualifier words are case-sensitive (Title or UPPER), so a lower-case line start
is no title; a credit-agreement or lender-presentation title line must end at the phrase (optional punctuation) or
continue only with `dated ...`, `among ...`, `by and among ...`, `between ...` or a bare date, so `Revolving Credit
Agreement borrowings were ...` is no title; that end rule applies to page title lines only (fix round 2): the file-name fallback keeps main's rule
(folder kept, no end rule; `abl-credit-agreement-executed.pdf` and `credit-agreement/exhibit.htm` stay credit agreements)
plus the date/exhibit prefix and the qualifier lists. Answer key (3cb7eefb, not edited): 15 fix1 tests red on 94b98f50, 230
passed in `test_run_expectations` after. Probes `r2a_ordinal_and_combinations`, `denylist_residue`, `adv_kinds`,
`r2_qualifier_residue`, `r2_qualifier_admits_connectives`, `r2a_info_residue`: exit 0. Back-test (`--out`) with
origin/main's rule file vs this one on the same tree: byte-identical.
Not verified: SUPERPRIORITY SECURED DEBTOR-IN-POSSESSION long form (I2, out of scope, stays unrecognised); titles with
other tails (e.g. `made as of`).

R-SB2-2a fix round 2 (re-review M/L): title end rule moved out of the patterns into `_hits(..., page=True)`, so the
file-name fallback is main's rule again (`2014-10-21-8k-credit-agreements.htm` and `...-credit-agreement-joinder.htm`
stay unrecognised); numeric ordinals match as written. Answer key (31d68dc4, not edited): 5 fix2 tests, 390 passed
across the four test files after. Back-test (`--out`) origin/main's rule file vs this one: byte-identical.
Not verified: titles `Amended And Restated Credit Agreement` and `CREDIT AGREEMENT (this "Agreement")` (closed lists, INFO).

R-SB2-2a fix 3 (restored narrowings, round-2 Lows): connectives in the qualifier match case-insensitively
(`Amended And Restated Credit Agreement`; ordinal list stays closed); title end rule accepts a `(this "...")` /
`(the "...")` defined-term tail (straight or curly quotes) before the recognised tails; `\b` restored on both
lender-presentation alternatives. Answer key (142ce81b, not edited): 5 fix3 tests red before, 397 passed after
across the four test files. Back-test (`--out`) origin/main's rule file vs this one: byte-identical (see below).
Not verified: defined-term tails other than `(this|the "...")`.

2026-11-10 Final status-reader batch (R-SB2-1l/1m/1n, blockquote fence, 1k case and heading), `handoff_outcome.py`. Every mention of the id is read and the worst class wins (own handoff and CP-0); an id-then-status match stops at `.`/`;` before a space or line end; CP-0 text is fence-filtered like own handoffs; `> ` prefixes are stripped before the fence rule and a fence opened in a quote ends at the first unquoted line; `Blocked: cp-4` and `## Blocked: CP-4` count (the status-colon-id form counts at line start only, so CP-6 in `Ready: CP-5. Blocked: CP-6.` is not_reached). Every status word in a mention's window is read and the worst wins (`CP-4 READY for drafting but BLOCKED for filing` is will_refuse). The reader is linear: the 1 MB timing tests in the key finish in under 1 s. Key (another agent's): `rf-` and `rf2-` cases in `tests/test_handoff_outcome_status.py`; 212 pass in that file after fix round 2 (the 12 `rf-` red before round 1, 6 `rf2-` red before round 2).
Final batch fix 2 (re-review H1): the mention window is read in a lookahead (`(?=(...))`) so only the id is consumed and a second mention of the same id inside the window is matched (`CP-4 READY ..., then CP-4 BLOCKED ...` is will_refuse, not ready); window bounds unchanged. Back-test output byte-identical to 3ec114cf.
R-SB2-1m refinement (reader frozen after this): a `.` ends the mention window's sentence only when followed by whitespace and an uppercase letter, or by the line's end, so `CP-4 (see sec. 3) BLOCKED pending data`, `no. 2`, `3.5x` and `e.g. the` no longer cut the window (will_refuse, as on main); `;` and line end unchanged. The window stops at the next module id in any letter case (`CP-4 READY, cp-5 BLOCKED` is CP-4 ready). Key (another agent's): 7 `rm-` cases red before, `tests/test_handoff_outcome_status.py` 227 pass after; the `rm-`/`rm1-` keys check the abbr-*/lower-cp rows (`probe_pr68_adv.py` prints them with exp=None and does not check them; it exits 0); pr65, 1j, rf, rf2, rf3 probes exit 0. Review L1: the window stop is a module id at a word boundary (`\b(?i:cp-)`), so `CP-4 READY over tcp-5 BLOCKED` stays will_refuse; `rm1-` cases red before, green after. The `\b` stop also closes the pre-existing `SCP-1 BLOCKED` false ready (probe row SCP-in-word). Linear (1 MB timing probes pass). Back-test output byte-identical to 6803f35d's. Known limits, not changed (end-of-phase list): negation inside a mention (`CP-4 READY, not BLOCKED` is will_refuse, conservative); `CP-4 and CP-5 BLOCKED` (CP-4 not read, never ready); `READY for drafting; BLOCKED for filing` (ready, as `;` ends the sentence).

## 2026-11-10 R-SB2-2c qualifier words, any ordinal, version and as-amended tails

`guess_kind` (`run_expectations.py`), lead ruling R-SB2-2c: the credit-agreement qualifier list also takes
DEBTOR-IN-POSSESSION, SYNDICATED and MULTICURRENCY (Title or UPPER, combining with the other words);
the ordinal before `Amended and Restated` is a closed grammar (First to Ninety-Ninth as words, hyphenated compounds
included, or digits; the digit suffix is checked against the number in the fix round below), so `Existing`, `Fiftyish`, `Thirdly` stay unrecognised; title lines may also end
with `(Execution Version)`, `(Conformed Copy)`, `- Execution Version` or `as amended ...`. INCREMENTAL, EXTENDED,
JOINDER and Existing/Prior/Amended openers are not added. Answer key (de400e69, not edited): 19 positive tests red
before (the 9 negatives green), all 28 green after; 425 passed, 1 skipped (paid) across the four target files.
Probes `main_vs_head` (differences listed in the PR), `r2a_rr_edges`, `r2a_rr3_narrowings`,
`r2a_rr2_name_and_title_parity`, `r2a_ordinal_and_combinations`, `denylist_residue`, `adv_kinds`,
`r2_qualifier_residue`, `r2_qualifier_admits_connectives`: exit 0. Back-test (`r2a_rr_backtest`) origin/main's rule file vs
this one: byte-identical.
Not verified: ordinals above Ninety-Ninth in words; tails other than the four listed.

Fix round (review M1 + L, key 8cf76486 not edited; 13 of 77 `fix1` tests red before, all green after): the `as amended`
tail is `as amended(?: and restated)?(?:\W*|\s+(?:through|by|to|on|as of|from time to time)\b.*)`, so body sentences
(`The Credit Agreement, as amended, contains ...`) are no title; a credit-agreement or lender-presentation title line
never begins (case-insensitively) with The/This/Our/Such/A/An/Under/Pursuant/In/As; numeric ordinals need the matching
suffix (1st, 22nd, 113th; not 0th, 11st, 1th, 12nd). The `the|this` lead-in stays: it still serves file names, which the
opener guard does not touch. Cost: bare `The Credit Agreement` / `This Amended and Restated Credit Agreement` title lines,
accepted on main, are unrecognised (fail-safe, by ruling). Back-test: byte-identical.
"This" amendment (lead, key 20fb148a not edited; 6 `r_sb2_2c_this_*` red before, green after): a line opening with "This" IS a credit-agreement title when a non-empty recognised tail follows "Credit Agreement" (the tails plus `is entered into as of ...` / `is made as of ...`, after an optional defined term); bare `This Credit Agreement`, a body sentence and every other opener stay not-a-title; lender presentations unchanged. As on main, `This Amended and Restated Credit Agreement` with a tail is a title. Back-test: byte-identical.
R-SB2-2d (lead, key 6f19d3c1/75a5d8dd not edited; 36 `r_sb2_2d_*` red before): the as-amended tail is closed. After `as amended` (optionally `and restated`) only punctuation/end, or `through|by|to|on|as of|from time to time ...` to line end, at most 80 characters, no comma except one date comma `<Month> <d>, <yyyy>` ending the tail; a "This" opener never takes an as-amended tail. Accepted limit: `This [qualifiers] Credit Agreement dated as of … requires …` stays a title — dated/among tails are open, as on main for the unqualified form.
Not verified: ordinals above Ninety-Ninth in words; tails other than the four listed.

## 2026-11-10 Plan 2 Task 6b (a resume's review names re-runs and shows retained outcomes, branch `claude/sb2-task6b-resume`)

- **Scope:** offline `bridge.review` only; no provider call. A resume's review gains `reruns` (every module the stopped run holds an accepted answer for that is not retained, with the bare `why`, "it follows <stop title>, which runs again", the record's own problem, or "added to this run" when the stopped run has no `instructions/<module>.md` for the stop module) and `retained_outcomes` (`handoff_outcome.actual_of` over the retained answer, with the retained CP-0 text). `expectations` and `counted` drop rows whose scope is a retained module; `without` is `without_for(ordered, remaining rows)`, so a retained module has no entry. A plain review carries both lists empty. The fake-engine bridge needed no edit: it returns the real review.
- **Key:** `d95aece9` and `47a520a2` (tests only). RED at `d95aece9`: 9 failures (`KeyError: 'reruns'`/`'retained_outcomes'`). GREEN: `tests/test_cpos_app.py` 65 passed; the four-file run 322 passed, 2 skipped; the 31 resume/6b tests pass 3 of 3.
- **R-SB2-6c:** a resume's `counted` is every id the plain review counts on a module that runs again, plus every counted propagating (will_refuse/limited) id on a retained module from which a module that runs again is reachable through the registry edges (`edges_for(ordered)`), through any number of retained middles; ids in the plain review's order, no duplicates. A retained module's own forecast row stays out of `expectations`; a retained gap does not propagate and is not counted; a retained root with no re-running consumer is not counted. Keys `489e021a`, `87a674e4`; lead's probe and the reviewer's chain probe run at the fix commit.
- **Not verified:** a real stopped run's review in the browser; the `instructions/` test for "added to this run" beyond the fixture; `expectations.json` keeps its six keys (PR2's key).

## 2026-11-10 flow_check units (A-live H1/H2 + R-C2-4) (branch `claude/sb2-flow-check-units`)
flow_check units (A-live H1/H2 + R-C2-4), `apps/issuer-library/designs/flow_check.py` only, key 018b7619 not edited: bps sourced by the exact percent/100 the module read; unit divisors (exactly 100/1000/10000/0.001, Decimal) after `/` or `÷` and the divisor operand of a `ratio` call; E-notation calculate results read exactly; ASC/ASU/IFRS/IAS/SFAS names. Hand rescales stay flagged. The `ratio 233.1 ÷ 1000` row was a key error: fixed by key commits 7bbf9036 and 06125824. Fix round 1 (review F1/F2/F3): a divisor must be the whole number (`/ 100.5m`, `/ 1000.25x`, `÷ 10000.7bn` stay flagged), a standard prefix needs same-line whitespace. Key row `Adjusted per ASC\n\n1234 total` was corrected to 5678 by f6e5a38d, because 1234 is in units_run's base source; the flow_check and report_text test files all pass (117). The reviewer's original probe has the same 1234 defect; its 5678 copy `fcu_probes_5678.py` and `fcu_reprobe.py` both exit 0. Not verified: live paid runs; conversions beyond the four shapes.

## 2026-11-10 Context import keeps the deal-term instrument (branch `claude/sb2-context-instrument`)
Context import keeps the deal-term instrument: `context-form.html` draws the deal instrument, rating agency and outlook and question focus module as text inputs with datalist suggestions (closed selects blanked unlisted values on load). Closed fields (run type, pathway, filing status, classification, listed equity, valuation bases, legal documents, management bridge and other attachment flags, quote kind, rating scope; a non-blank value outside the list) and tenor/price talk on a non-Primary run now refuse the whole load: `#loadmsg` is "Not loaded. ..." with class `bad`, naming path and value, nothing applied. Tenor/talk choice: refuse (smaller than keeping, which would need non-Primary editable talk fields). `live_check.fill_form` raises `Refusal` on a "Not loaded" or "unknown value" note before any Start; the Stage-2 content check compares non-blank leaves both ways (blank keys the form adds are not a fault). Keys cd6d341c, 6b87aab6, 3ce3f5f0 not edited. A blank quote kind or rating scope is not refused: the radio keeps its default and the load shows the note `unknown value "", default kept`. OPEN (lead review M2, 2026-11-10; fixed by the follow-up load-invariant PR): these load without a refusal. A row key missing from the file is never passed to setV, so the default stays with no note (quotes[i].kind becomes observed, ratings[i].scope becomes issuer); an extra row key the form does not know is dropped; a missing identity.listed_equity loads as No and a missing attachments flag stays unchecked, each with a note only. OPEN (lead review M1): a line feed inside a single-line text field is stripped silently; the follow-up PR refuses it.
Not verified: a live `fill_form` run against a real case; the UI by eye; the template carries the same field change; the release sync is replayed in a temp copy by the round-trip test and reproduces the web form byte for byte (`packaging/build.py` not run end to end).

## 2026-11-10 Correction: C1 and C1n instrument input
C1 and C1n each ran with `deal_terms[0].instrument` blank ('ABL revolver' in the frozen case) because the context form's closed instrument list blanked it on load. Their results stand. The input differed from the frozen case in that one value. 45 entered fields checked (read-only comparison of each retained intake context with its case file).

## 2026-11-10 D1 blocked/limited module status on report sections (branch `claude/sb2-d1-blocked-sections`)
- **Scope:** `src/deploy_workflow/markdown_delivery.py` only. A module whose own handoff reads will_refuse or limited through the frozen `handoff_outcome.own_status` puts `<module> Blocked|Restricted: <reason>` in the note of every table and prose block routed from it and after its sentence in the `delivery-limits` banner. The reason is the first bold-led line of the handoff's Request section, `**` removed; with none, the reader's own `how` string. No new slot; `handoff_outcome.py` and the key (`722026da`, `deaee6f3`) not edited.
- **Result:** `tests/test_delivery_blocked_sections.py` 10 red before, 14 passed after (A-live read in place, portable synthetic included). 14 delivery test files: 624 passed, 1 skipped (paid); the 2 failures in `tests/test_markdown_delivery_sections.py` (`..._carry_its_sentences_once`, `..._keep_route_order_in_the_note`) fail identically on the unmodified base. `tools/quality_gate.py` flags only 2 E501 lines in the key test (`:168`, `:169`), none in changed source; `tools/pr_size.py` 240 of 800.
- **Not verified:** chart blocks (strip/yield) carry no status note; the rendered note and banner by eye in a browser; handoffs with a Blocked status and no bold-led Request line (falls back to the reader's account, untested); `tests/test_owner_rendering.py` (collection fails on a missing `docs/OWNER-RENDERING-LEASE.md`, present on base too).
